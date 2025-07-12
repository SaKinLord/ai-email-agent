# -*- coding: utf-8 -*-
"""
Created on Fri Apr 18 11:07:10 2025

@author: merto
"""

# main.py
from dotenv import load_dotenv
load_dotenv()
# --- Standard Library Imports ---
import os
import sys
import logging
import json
import time
from datetime import timedelta
from datetime import datetime, timezone
import tempfile # Added for GCF model loading
import functions_framework
import base64
import re
from email.utils import parsedate_to_datetime

# --- Third-party Imports ---
import pandas as pd
import joblib
from google.cloud.firestore_v1.base_query import FieldFilter
from googleapiclient.errors import HttpError # Import HttpError
from google.cloud import firestore
from google.cloud import storage

# --- NEW: Import unified authentication system ---
from auth_utils import get_authenticated_services
from google.cloud import secretmanager
from googleapiclient.discovery import build
import anthropic
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception
from google.api_core import exceptions as google_exceptions

# --- Local Imports ---
import database_utils # Import the module directly
from agent_logic import (
    load_config, get_unread_email_ids,
    get_email_details, parse_email_content,
    process_email_with_memory,
    PRIORITY_CRITICAL, PRIORITY_HIGH, 
    prepare_email_batch_overview, 
    list_sent_emails,             
    check_thread_for_reply,       
    _extract_email_address,
    analyze_email_with_context        
)

# --- Enhanced Reasoning System Imports ---
from reasoning_integration import (
    process_email_with_enhanced_reasoning,
    create_proactive_insights,
    get_autonomous_action_recommendations
)
from hybrid_llm_system import create_hybrid_llm_manager

# Import database functions needed here
from database_utils import (
    is_email_processed, add_processed_email,
    get_todays_high_priority_emails, add_feedback,
    get_feedback_history, check_existing_feedback,
    get_feedback_count, write_retrain_state_to_firestore,
    read_user_preferences,
    request_email_action,
    update_action_request_status, # Added Firestore state write
    initialize_firestore, # Added for lazy initialization
    get_db # Add get_db import
)
ACTION_REQUESTS_COLLECTION = "action_requests" # Define constant locally
from ml_utils import (
    build_and_train_pipeline,
    predict_priority,
    extract_domain # Import helper needed for data prep
)

from agent_memory import AgentMemory
from email.mime.text import MIMEText
from task_utils import save_task_to_firestore

# --- Logging Setup ---
log_format = '%(asctime)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s'
logging.basicConfig(level=logging.INFO, format=log_format, stream=sys.stdout, force=True)

# --- Firestore Collection Names ---
EMAILS_COLLECTION = "emails"
FEEDBACK_COLLECTION = "feedback"
STATE_COLLECTION = "agent_state"
ACTION_LOG_COLLECTION = "action_log"

# --- Global variables for Caching Clients/Config (initialized in handler) ---
# db is now managed by database_utils.py
storage_client = None
secret_client = None
config = None
llm_client_gcf = None
hybrid_llm_manager = None  # Enhanced hybrid LLM manager

# --- GCS Bucket/Object Names (Get from Env Vars) ---
#GCS_BUCKET_NAME = os.environ.get('GCS_BUCKET_NAME') # Bucket for token, state
TOKEN_GCS_BUCKET = os.environ.get('TOKEN_GCS_BUCKET')
#STATE_GCS_PATH = os.environ.get('STATE_GCS_PATH', 'retrain_state.json')
ANTHROPIC_SECRET_NAME = os.environ.get('ANTHROPIC_SECRET_NAME')
OPENAI_SECRET_NAME = os.environ.get('OPENAI_SECRET_NAME')
# --- NEW Env Vars for ML Models ---
MODEL_GCS_BUCKET = os.environ.get('MODEL_GCS_BUCKET')
MODEL_GCS_PATH_PREFIX = os.environ.get('MODEL_GCS_PATH_PREFIX', 'ml_models/')

# --- NEW: Constants for Autonomous Tasks ---
DAILY_SUMMARY_ACTION_TYPE = "send_daily_summary_email"
AUTO_ARCHIVE_CHECK_INTERVAL_MINUTES = 60
DAILY_SUMMARY_CHECK_INTERVAL_MINUTES = 60
FOLLOW_UP_CHECK_INTERVAL_MINUTES = 60
RE_EVAL_UNKNOWN_INTERVAL_MINUTES = 1440 # Once a day (24 * 60)

# === Intelligent Retry Condition Functions ===

def is_retryable_gmail_error(exception):
    """
    Return True if the Gmail API exception is a transient error that should be retried, False otherwise.
    
    This function implements intelligent retry logic for Gmail API:
    - Retry on server errors (5xx) from Gmail API
    - Do NOT retry on client errors (4xx) like authentication failures, quota exceeded
    - Retry on network timeouts and connection issues
    - Do NOT retry on quota/rate limit errors that need different handling
    
    Args:
        exception: The exception that was raised
        
    Returns:
        bool: True if the error should be retried, False if it should fail immediately
    """
    # Check for Google API HTTP errors
    if isinstance(exception, HttpError):
        status_code = exception.resp.status
        # Retry on server errors (500-599), fail immediately on client errors (400-499)
        if 400 <= status_code < 500:
            return False  # Client error - don't retry (auth, quota, etc.)
        elif status_code >= 500:
            return True   # Server error - retry
    
    # Check for Google Cloud exceptions
    if hasattr(exception, '__class__') and 'google' in str(exception.__class__):
        # For google.api_core.exceptions, check if it's a server error
        if hasattr(exception, 'code'):
            # Google Cloud error codes follow HTTP status codes
            code = exception.code
            if 400 <= code < 500:
                return False  # Client error
            elif code >= 500:
                return True   # Server error
    
    # For generic network errors and timeouts, retry
    if isinstance(exception, (TimeoutError, ConnectionError, OSError)):
        return True
    
    # For other exceptions, don't retry by default (they might be programming errors)
    return False

def get_user_friendly_gmail_error_message(exception):
    """
    Generate user-friendly error messages for non-retryable Gmail API errors.
    
    Args:
        exception: The exception that was raised
        
    Returns:
        str: User-friendly error message
    """
    if isinstance(exception, HttpError):
        status_code = exception.resp.status
        if status_code == 401:
            return "Authentication Error: Please check your Gmail API credentials. They appear to be invalid or expired."
        elif status_code == 403:
            return "Permission Error: Your Gmail API credentials don't have permission to access this resource. Please check your OAuth scopes."
        elif status_code == 429:
            return "Rate Limit Error: Gmail API rate limit exceeded. Please wait a moment and try again."
        elif status_code == 404:
            return "Resource Not Found: The requested Gmail resource (email, label, etc.) was not found."
        elif 400 <= status_code < 500:
            return f"Gmail API Client Error ({status_code}): {str(exception)}"
    
    # Check for Google Cloud exceptions
    if hasattr(exception, '__class__') and 'google' in str(exception.__class__):
        if hasattr(exception, 'code'):
            code = exception.code
            if code == 401:
                return "Authentication Error: Google Cloud credentials are invalid or expired."
            elif code == 403:
                return "Permission Error: Insufficient permissions for Google Cloud resources."
            elif code == 429:
                return "Rate Limit Error: Google Cloud API rate limit exceeded."
    
    # Generic error message for other cases
    return f"Gmail API Error: {str(exception)}"

# === Helper Functions for GCS State/Token ===
# (Keep read_json_from_gcs, write_json_to_gcs, read_retrain_state_from_gcs, write_retrain_state_to_gcs as before)
def read_json_from_gcs(bucket_name, blob_name):
    if not storage_client:
        logging.error("GCS client not available for read.")
        return None
    if not bucket_name:
        logging.error("GCS bucket name not provided for read.")
        return None
    try:
        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob(blob_name)
        if not blob.exists(storage_client):
            logging.info(f"JSON file not found at gs://{bucket_name}/{blob_name}")
            return None # Return None, not empty dict, to distinguish missing file
        logging.info(f"Reading JSON from gs://{bucket_name}/{blob_name}")
        return json.loads(blob.download_as_string(client=storage_client))
    except Exception as e:
        logging.error(f"Failed to read JSON from gs://{bucket_name}/{blob_name}: {e}", exc_info=True)
        return None

def write_json_to_gcs(bucket_name, blob_name, data):
    if not storage_client:
        logging.error("GCS client not available for write.")
        return False
    if not bucket_name:
        logging.error("GCS bucket name not provided for write.")
        return False
    try:
        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob(blob_name)
        blob.upload_from_string(json.dumps(data, indent=2), content_type='application/json', client=storage_client)
        logging.info(f"Written JSON to gs://{bucket_name}/{blob_name}")
        return True
    except Exception as e:
        logging.error(f"Failed to write JSON to gs://{bucket_name}/{blob_name}: {e}", exc_info=True)
        return False

def read_retrain_state_from_gcs():
    """Reads the retraining state from the GCS bucket dedicated to models/state."""
    if not MODEL_GCS_BUCKET:
        logging.error("MODEL_GCS_BUCKET environment variable is not set. Cannot read retrain state.")
        return {'last_feedback_count': 0, 'last_updated_utc': None}

    state_file_path = "retrain_state.json"
    state = read_json_from_gcs(MODEL_GCS_BUCKET, state_file_path)
    
    if not state:
        logging.info(f"Retrain state file not found or empty at gs://{MODEL_GCS_BUCKET}/{state_file_path}. Defaulting state.")
        return {'last_feedback_count': 0, 'last_updated_utc': None}
        
    if 'last_feedback_count' not in state:
        logging.warning(f"Key 'last_feedback_count' missing in retrain state file. Defaulting count to 0.")
        state['last_feedback_count'] = 0
        
    if 'last_updated_utc' not in state:
        state['last_updated_utc'] = None
        
    logging.info(f"Read GCS retrain state: {state}")
    return state

def write_retrain_state_to_gcs(count):
    """Writes the retraining state to the GCS bucket dedicated to models/state."""
    if not MODEL_GCS_BUCKET:
        logging.error("MODEL_GCS_BUCKET environment variable is not set. Cannot write retrain state.")
        return False
        
    state_file_path = "retrain_state.json"
    state = {
        'last_feedback_count': count,
        'last_updated_utc': datetime.now(timezone.utc).isoformat()
    }
    return write_json_to_gcs(MODEL_GCS_BUCKET, state_file_path, state)


# === Helper Function for Secret Manager ===
# (Keep get_secret as before)
def get_secret(secret_version_name):
    global secret_client
    if not secret_client:
        logging.error("Secret Manager client not available (get_secret).")
        return None
    if not secret_version_name:
        logging.error("Secret version name environment variable not set.")
        return None
    try:
        logging.info(f"Accessing secret: {secret_version_name}")
        response = secret_client.access_secret_version(name=secret_version_name)
        secret_value = response.payload.data.decode("UTF-8")
        logging.info("Secret accessed successfully.")
        # --- REMOVE Temporary Debug Log Here (if added previously) ---
        # logging.info(f"Retrieved Anthropic key. Type: {type(secret_value)}, Length: {len(secret_value) if secret_value else 0}")
        # --- End Temporary Debug Log ---
        return secret_value
    except Exception as e:
        logging.error(f"Failed to access secret {secret_version_name}: {e}", exc_info=True)
        return None

# --- NEW: Helper to check if task should run based on interval ---
def should_run_task(task_name, interval_minutes, memory_instance):
    """Checks if a task should run based on its last run time stored in user profile."""
    now = datetime.now(timezone.utc)
    task_last_run_key = f"autonomous_tasks.{task_name}.last_run_utc"
    last_run_iso = memory_instance.user_profile.get("autonomous_tasks", {}).get(task_name, {}).get("last_run_utc")

    if last_run_iso:
        try:
            last_run_dt = datetime.fromisoformat(last_run_iso)
            if (now - last_run_dt) < timedelta(minutes=interval_minutes):
                logging.info(f"Task '{task_name}' ran recently ({last_run_dt.isoformat()}). Skipping.")
                return False
        except ValueError:
            logging.warning(f"Could not parse last_run_iso for task '{task_name}': {last_run_iso}")
    
    logging.info(f"Task '{task_name}' is due to run.")
    return True

def update_task_last_run(task_name, memory_instance):
    """Updates the last run time for a task in user profile."""
    now_iso = datetime.now(timezone.utc).isoformat()
    update_path = f"autonomous_tasks.{task_name}.last_run_utc"
    memory_instance.save_profile_updates({update_path: now_iso})
    logging.info(f"Updated last_run_utc for task '{task_name}' to {now_iso}")

@retry(
    retry=retry_if_exception(is_retryable_gmail_error),  # Only retry on transient errors
    stop=stop_after_attempt(3),  # Try a total of 3 times
    wait=wait_exponential(multiplier=1, min=2, max=10)  # Wait 2s, then 4s, etc.
)
def _gmail_archive_email(gmail_service, email_id):
    """
    Archive an email with automatic retry mechanism.
    
    This function includes automatic retries with exponential backoff for increased
    reliability when dealing with transient network errors or temporary Gmail API
    unavailability.
    """
    modify_body = {'removeLabelIds': ['INBOX']}
    return gmail_service.users().messages().modify(userId='me', id=email_id, body=modify_body).execute()

@retry(
    retry=retry_if_exception(is_retryable_gmail_error),  # Only retry on transient errors
    stop=stop_after_attempt(3),  # Try a total of 3 times
    wait=wait_exponential(multiplier=1, min=2, max=10)  # Wait 2s, then 4s, etc.
)
def _gmail_send_message(gmail_service, send_body):
    """
    Send an email message with automatic retry mechanism.
    
    This function includes automatic retries with exponential backoff for increased
    reliability when dealing with transient network errors or temporary Gmail API
    unavailability.
    """
    return gmail_service.users().messages().send(userId='me', body=send_body).execute()

@retry(
    retry=retry_if_exception(is_retryable_gmail_error),  # Only retry on transient errors
    stop=stop_after_attempt(3),  # Try a total of 3 times
    wait=wait_exponential(multiplier=1, min=2, max=10)  # Wait 2s, then 4s, etc.
)
def _gmail_apply_labels(gmail_service, email_id, label_ids):
    """
    Apply labels to an email with automatic retry mechanism.
    
    This function includes automatic retries with exponential backoff for increased
    reliability when dealing with transient network errors or temporary Gmail API
    unavailability.
    """
    modify_body = {'addLabelIds': label_ids}
    return gmail_service.users().messages().modify(userId='me', id=email_id, body=modify_body).execute()

@retry(
    retry=retry_if_exception(is_retryable_gmail_error),  # Only retry on transient errors
    stop=stop_after_attempt(3),  # Try a total of 3 times
    wait=wait_exponential(multiplier=1, min=2, max=10)  # Wait 2s, then 4s, etc.
)
def _gmail_get_user_profile(gmail_service):
    """
    Get user profile with automatic retry mechanism.
    
    This function includes automatic retries with exponential backoff for increased
    reliability when dealing with transient network errors or temporary Gmail API
    unavailability.
    """
    return gmail_service.users().getProfile(userId='me').execute()

@retry(
    retry=retry_if_exception(is_retryable_gmail_error),  # Only retry on transient errors
    stop=stop_after_attempt(3),  # Try a total of 3 times
    wait=wait_exponential(multiplier=1, min=2, max=10)  # Wait 2s, then 4s, etc.
)
def get_or_create_label_ids(gmail_service, label_names_to_ensure):
    """
    Ensures labels exist in Gmail, creates them if not with automatic retry mechanism.
    
    This function includes automatic retries with exponential backoff for increased
    reliability when dealing with transient network errors or temporary Gmail API
    unavailability.
    
    Returns a list of label IDs corresponding to the input names.
    """
    if not gmail_service or not label_names_to_ensure:
        return []

    existing_labels_map = {}
    try:
        results = gmail_service.users().labels().list(userId='me').execute()
        labels = results.get('labels', [])
        for label in labels:
            existing_labels_map[label['name']] = label['id']
    except Exception as e:
        # Check if this is a non-retryable error
        if not is_retryable_gmail_error(e):
            user_message = get_user_friendly_gmail_error_message(e)
            logging.error(f"Gmail labels list failed with non-retryable error: {user_message}")
            return [] # Return empty on error, so we don't try to apply non-existent labels
        else:
            # For retryable errors, re-raise to trigger retry mechanism
            logging.error(f"Could not list existing Gmail labels (will retry): {e}")
            raise e

    label_ids_to_apply = []
    for label_name in label_names_to_ensure:
        if label_name in existing_labels_map:
            label_ids_to_apply.append(existing_labels_map[label_name])
        else:
            # Label does not exist, create it
            logging.info(f"Label '{label_name}' not found. Attempting to create it.")
            label_body = {
                'name': label_name,
                'labelListVisibility': 'labelShow',    # Or 'labelHide'
                'messageListVisibility': 'show'        # Or 'hide'
            }
            # Handle nested labels: Gmail API creates parent labels automatically if they don't exist
            # when you provide a path-like name (e.g., "Maia/Priority/Medium")
            try:
                created_label = gmail_service.users().labels().create(userId='me', body=label_body).execute()
                logging.info(f"Successfully created label '{label_name}' with ID '{created_label['id']}'.")
                label_ids_to_apply.append(created_label['id'])
                existing_labels_map[label_name] = created_label['id'] # Add to map for this session
            except HttpError as e_create:
                logging.error(f"HttpError creating label '{label_name}': {e_create}", exc_info=True)
                # If creation fails, we can't apply it. Optionally, retry or just skip.
            except Exception as e_create_unexpected:
                logging.error(f"Unexpected error creating label '{label_name}': {e_create_unexpected}", exc_info=True)
    
    return label_ids_to_apply

# --- NEW: Autonomous Archiving Function ---
def run_autonomous_archiving_task(gmail_service, db_param, config):
    """
    Execute autonomous archiving of low-priority emails based on configuration.
    
    This function queries Firestore for emails that meet the auto-archiving criteria
    and automatically archives them using the Gmail API.
    
    Args:
        gmail_service: Authenticated Gmail API service instance
        db_param: Firestore database client (parameter for backward compatibility)
        config: Configuration dictionary loaded from config.json
    """
    try:
        # Import the database getter function
        from database_utils import get_db
        
        # Load auto-archive configuration
        auto_archive_config = config.get('autonomous_tasks', {}).get('auto_archive', {})
        
        # Check if auto-archiving is enabled
        if not auto_archive_config.get('enabled', False):
            logging.info("Auto-archiving is disabled in configuration. Skipping autonomous archiving task.")
            return
        
        confidence_threshold = auto_archive_config.get('confidence_threshold', 0.95)
        purposes_to_archive = auto_archive_config.get('purposes_to_archive', [])
        
        logging.info(f"Starting autonomous archiving task with confidence threshold: {confidence_threshold}")
        logging.info(f"Purposes eligible for archiving: {purposes_to_archive}")
        
        if not purposes_to_archive:
            logging.info("No purposes configured for auto-archiving. Skipping task.")
            return
        
        # Query Firestore for emails that meet archiving criteria
        try:
            db = get_db()
            if db is None:
                logging.error("Failed to initialize Firestore database for archiving task")
                return
            emails_collection = db.collection(EMAILS_COLLECTION)
        except Exception as e:
            logging.error(f"Database initialization failed in archiving task: {e}")
            return
        
        # Build the query with multiple filters
        query = emails_collection.where(filter=FieldFilter('is_archived', '==', False))
        query = query.where(filter=FieldFilter('llm_purpose', 'in', purposes_to_archive))
        query = query.where(filter=FieldFilter('llm_purpose_confidence', '>=', confidence_threshold))
        
        # Execute the query
        emails_to_archive = query.stream()
        emails_processed = 0
        
        for email_doc in emails_to_archive:
            try:
                email_data = email_doc.to_dict()
                email_id = email_data.get('id')
                subject = email_data.get('subject', '[No Subject]')
                purpose = email_data.get('llm_purpose')
                confidence = email_data.get('llm_purpose_confidence', 0)
                
                if not email_id:
                    logging.warning(f"Email document {email_doc.id} missing 'id' field. Skipping.")
                    continue
                
                # Archive the email using Gmail API
                logging.info(f"Auto-archiving email ID {email_id} (Subject: '{subject}') with purpose '{purpose}' and confidence {confidence:.1%}")
                
                result = _gmail_archive_email(gmail_service, email_id)
                
                if result:
                    # Update the email document in Firestore to mark as archived
                    email_doc.reference.update({'is_archived': True})
                    
                    # Log the autonomous action to action_log collection
                    try:
                        action_log_doc = {
                            "timestamp": firestore.SERVER_TIMESTAMP,
                            "action_type": "auto_archive",
                            "email_id": email_id,
                            "email_subject": subject,
                            "reason": f"Classified as '{purpose}' with {confidence:.0%} confidence."
                        }
                        db = get_db()
                        if db is not None:
                            db.collection(ACTION_LOG_COLLECTION).add(action_log_doc)
                        else:
                            logging.error("Database not available for action logging")
                        logging.info(f"Logged autonomous action for email ID {email_id}")
                    except Exception as e_log:
                        logging.error(f"Failed to log autonomous action for email ID {email_id}: {e_log}")
                    
                    # Broadcast autonomous action executed event via WebSocket
                    try:
                        from websocket_events import broadcast_autonomous_action_executed
                        action_details = f"Auto-archived email '{subject}' classified as '{purpose}' with {confidence:.0%} confidence"
                        
                        # Try to get user_id from email_data, fallback to 'default_user' if not available
                        user_id = email_data.get('user_id', 'default_user')
                        
                        broadcast_autonomous_action_executed(
                            user_id=user_id,
                            email_id=email_id,
                            action='archive',
                            details=action_details
                        )
                        logging.info(f"Broadcasted autonomous action event for email ID {email_id}")
                    except Exception as e_broadcast:
                        logging.error(f"Failed to broadcast autonomous action for email ID {email_id}: {e_broadcast}")
                    
                    emails_processed += 1
                    logging.info(f"Successfully auto-archived email ID {email_id}")
                else:
                    logging.error(f"Failed to archive email ID {email_id} - Gmail API returned no result")
                    
            except Exception as e_email:
                logging.error(f"Error processing email {email_doc.id} for auto-archiving: {e_email}", exc_info=True)
                continue
        
        if emails_processed > 0:
            logging.info(f"Autonomous archiving task completed. Successfully archived {emails_processed} emails.")
        else:
            logging.info("No emails met the criteria for auto-archiving.")
            
    except Exception as e:
        logging.error(f"Error in autonomous archiving task: {e}", exc_info=True)

# --- NEW: Autonomous Meeting Preparation Function ---
def run_autonomous_meeting_prep_task(gmail_service, db, config):
    """
    Execute autonomous meeting preparation by detecting meeting invitations 
    and creating draft calendar events.
    
    This function queries Firestore for emails that might contain meeting invitations,
    analyzes them using LLM for event details extraction, and creates draft calendar events.
    
    Args:
        gmail_service: Authenticated Gmail API service instance
        db: Firestore database client
        config: Configuration dictionary loaded from config.json
    """
    try:
        # Load auto-meeting-prep configuration
        meeting_prep_config = config.get('autonomous_tasks', {}).get('auto_meeting_prep', {})
        
        # Check if auto-meeting-prep is enabled
        if not meeting_prep_config.get('enabled', False):
            logging.info("Auto-meeting-prep is disabled in configuration. Skipping autonomous meeting preparation task.")
            return
        
        confidence_threshold = meeting_prep_config.get('confidence_threshold', 0.90)
        
        logging.info(f"Starting autonomous meeting preparation task with confidence threshold: {confidence_threshold}")
        
        # Ensure database is initialized
        try:
            db = get_db()
            if db is None:
                logging.error("Failed to initialize Firestore database for meeting preparation task")
                return
            emails_collection = db.collection(EMAILS_COLLECTION)
        except Exception as e:
            logging.error(f"Database initialization failed in meeting preparation task: {e}")
            return
        
        # Build query for potential meeting invitation emails
        # Look for high priority emails with action_required purpose or specific subject patterns
        query = emails_collection.where(filter=FieldFilter('meeting_processed', '==', False))
        query = query.where(filter=FieldFilter('priority', 'in', ['CRITICAL', 'HIGH']))
        
        # Execute the query
        candidate_emails = query.stream()
        meetings_processed = 0
        
        for email_doc in candidate_emails:
            try:
                email_data = email_doc.to_dict()
                email_id = email_data.get('id')
                subject = email_data.get('subject', '[No Subject]')
                body_text = email_data.get('body_text', email_data.get('body_snippet', ''))
                sender = email_data.get('sender', 'Unknown Sender')
                llm_purpose = email_data.get('llm_purpose', '')
                
                if not email_id:
                    logging.warning(f"Email document {email_doc.id} missing 'id' field. Skipping.")
                    continue
                
                # Detect if email contains meeting invitation
                is_meeting_invitation = detect_meeting_invitation(subject, body_text, llm_purpose)
                
                if is_meeting_invitation:
                    logging.info(f"Meeting invitation detected in email ID {email_id} (Subject: '{subject}')")
                    
                    # Extract event details using LLM
                    try:
                        event_details = extract_event_details_with_llm(subject, body_text, llm_client_gcf, config)
                        
                        if event_details and event_details.get('confidence', 0) >= confidence_threshold:
                            # Create calendar service
                            calendar_service = create_calendar_service(gmail_service)
                            
                            if calendar_service:
                                # Create draft calendar event
                                event_result = create_draft_calendar_event(calendar_service, event_details, email_data)
                                
                                if event_result:
                                    # Log the autonomous action
                                    try:
                                        action_log_doc = {
                                            "timestamp": firestore.SERVER_TIMESTAMP,
                                            "action_type": "auto_calendar_draft",
                                            "email_id": email_id,
                                            "email_subject": subject,
                                            "reason": f"Meeting invitation detected in email from {sender}.",
                                            "event_summary": event_details.get('summary', 'Meeting'),
                                            "event_id": event_result.get('id', '')
                                        }
                                        db = get_db()
                                        if db is not None:
                                            db.collection(ACTION_LOG_COLLECTION).add(action_log_doc)
                                        else:
                                            logging.error("Database not available for action logging")
                                        logging.info(f"Logged autonomous meeting prep action for email ID {email_id}")
                                    except Exception as e_log:
                                        logging.error(f"Failed to log autonomous meeting prep action for email ID {email_id}: {e_log}")
                                    
                                    # Mark email as processed
                                    email_doc.reference.update({'meeting_processed': True})
                                    meetings_processed += 1
                                    logging.info(f"Successfully created draft calendar event for email ID {email_id}")
                                else:
                                    logging.error(f"Failed to create calendar event for email ID {email_id}")
                            else:
                                logging.warning(f"Calendar service not available for email ID {email_id}")
                        else:
                            logging.info(f"Event details extraction did not meet confidence threshold for email ID {email_id}")
                            # Mark as processed to avoid re-processing
                            email_doc.reference.update({'meeting_processed': True})
                    except Exception as e_extract:
                        logging.error(f"Error extracting event details for email ID {email_id}: {e_extract}")
                        # Mark as processed to avoid re-processing failed extractions
                        email_doc.reference.update({'meeting_processed': True})
                else:
                    # Not a meeting invitation, mark as processed to avoid re-checking
                    email_doc.reference.update({'meeting_processed': True})
                    
            except Exception as e_email:
                logging.error(f"Error processing email {email_doc.id} for meeting preparation: {e_email}", exc_info=True)
                continue
        
        if meetings_processed > 0:
            logging.info(f"Autonomous meeting preparation task completed. Successfully processed {meetings_processed} meeting invitations.")
        else:
            logging.info("No meeting invitations found or processed.")
            
    except Exception as e:
        logging.error(f"Error in autonomous meeting preparation task: {e}", exc_info=True)

def detect_meeting_invitation(subject, body_text, llm_purpose):
    """
    Detect if an email contains a meeting invitation using heuristics.
    
    Args:
        subject: Email subject line
        body_text: Email body content
        llm_purpose: LLM-determined purpose of the email
        
    Returns:
        bool: True if the email likely contains a meeting invitation
    """
    # Check if LLM already identified this as action-required
    if llm_purpose and 'action' in llm_purpose.lower():
        
        # Check subject line for meeting-related keywords
        subject_lower = subject.lower()
        meeting_subject_keywords = [
            'invitation:', 'invite:', 'meeting:', 'call:', 'conference:',
            'zoom', 'teams', 'meet', 'calendar', 'schedule', 'appointment'
        ]
        
        has_meeting_subject = any(keyword in subject_lower for keyword in meeting_subject_keywords)
        
        # Check body for meeting-related content
        body_lower = body_text.lower()
        meeting_body_keywords = [
            'when:', 'where:', 'attendees:', 'join the meeting', 'meeting link',
            'calendar invite', 'add to calendar', 'meeting details', 'zoom.us',
            'teams.microsoft.com', 'meet.google.com', '.ics'
        ]
        
        has_meeting_body = any(keyword in body_lower for keyword in meeting_body_keywords)
        
        # Return True if we find meeting indicators in subject OR body
        return has_meeting_subject or has_meeting_body
    
    return False

def extract_event_details_with_llm(subject, body_text, llm_client, config):
    """
    Use LLM to extract structured event details from email content.
    
    Args:
        subject: Email subject line
        body_text: Email body content
        llm_client: Anthropic LLM client
        config: Configuration dictionary
        
    Returns:
        dict: Extracted event details with confidence score
    """
    try:
        # Prepare extraction prompt
        extraction_prompt = f"""Please analyze this email and extract meeting/event details if present. 
        Return a JSON object with the following structure:
        {{
            "summary": "Meeting title/subject",
            "start_time": "ISO 8601 datetime or null",
            "end_time": "ISO 8601 datetime or null", 
            "location": "Meeting location or null",
            "description": "Meeting description",
            "attendees": ["email1@example.com", "email2@example.com"],
            "confidence": 0.95
        }}
        
        Only extract details if this is clearly a meeting invitation. Set confidence to 0 if not a meeting.
        
        Email Subject: {subject}
        Email Body: {body_text[:2000]}"""  # Limit body text to avoid token limits
        
        # Call LLM for extraction
        response = llm_client.messages.create(
            model=config.get('llm', {}).get('model_name', 'claude-3-haiku-20240307'),
            max_tokens=300,
            temperature=0.3,
            messages=[{
                "role": "user",
                "content": extraction_prompt
            }]
        )
        
        # Parse JSON response
        response_text = response.content[0].text.strip()
        
        # Extract JSON from response (handle cases where LLM adds extra text)
        json_start = response_text.find('{')
        json_end = response_text.rfind('}') + 1
        
        if json_start >= 0 and json_end > json_start:
            json_str = response_text[json_start:json_end]
            event_details = json.loads(json_str)
            
            # Validate required fields
            if event_details.get('confidence', 0) > 0:
                return event_details
        
        return None
        
    except Exception as e:
        logging.error(f"Error extracting event details with LLM: {e}")
        return None

def create_calendar_service(gmail_service):
    """
    Create Google Calendar API service using the same credentials as Gmail.
    
    Args:
        gmail_service: Authenticated Gmail API service instance
        
    Returns:
        Google Calendar API service instance or None
    """
    try:
        # Use the same credentials from gmail_service for calendar
        credentials = gmail_service._http.credentials
        calendar_service = build('calendar', 'v3', credentials=credentials)
        return calendar_service
    except Exception as e:
        logging.error(f"Error creating calendar service: {e}")
        return None

def create_draft_calendar_event(calendar_service, event_details, email_data):
    """
    Create a draft calendar event using the Calendar API.
    
    Args:
        calendar_service: Google Calendar API service instance
        event_details: Extracted event details dictionary
        email_data: Original email data for reference
        
    Returns:
        Created event dictionary or None
    """
    try:
        # Prepare event body
        event_body = {
            'summary': f"[DRAFT by Maia] {event_details.get('summary', 'Meeting')}",
            'description': f"Auto-created by Maia from email.\n\nOriginal email subject: {email_data.get('subject', '')}\n\n{event_details.get('description', '')}",
            'start': {},
            'end': {},
            'attendees': []
        }
        
        # Handle start/end times
        start_time = event_details.get('start_time')
        end_time = event_details.get('end_time')
        
        if start_time:
            try:
                # Parse ISO datetime or create placeholder
                start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                event_body['start'] = {
                    'dateTime': start_dt.isoformat(),
                    'timeZone': 'UTC'
                }
                
                if end_time:
                    end_dt = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
                else:
                    # Default to 1 hour meeting
                    end_dt = start_dt + timedelta(hours=1)
                
                event_body['end'] = {
                    'dateTime': end_dt.isoformat(),
                    'timeZone': 'UTC'
                }
            except Exception as e_time:
                logging.warning(f"Error parsing meeting times: {e_time}. Creating all-day placeholder.")
                # Create all-day placeholder for today
                today = datetime.now().date()
                event_body['start'] = {'date': today.isoformat()}
                event_body['end'] = {'date': (today + timedelta(days=1)).isoformat()}
        else:
            # No time specified, create all-day placeholder for today
            today = datetime.now().date()
            event_body['start'] = {'date': today.isoformat()}
            event_body['end'] = {'date': (today + timedelta(days=1)).isoformat()}
        
        # Add location if available
        location = event_details.get('location')
        if location:
            event_body['location'] = location
        
        # Add attendees if available
        attendees = event_details.get('attendees', [])
        if attendees:
            event_body['attendees'] = [{'email': email} for email in attendees if '@' in email]
        
        # Create the event (without sending notifications)
        event_result = calendar_service.events().insert(
            calendarId='primary',
            body=event_body,
            sendNotifications=False
        ).execute()
        
        logging.info(f"Created draft calendar event: {event_result.get('id', 'unknown')}")
        return event_result
        
    except Exception as e:
        logging.error(f"Error creating calendar event: {e}")
        return None

# --- NEW: Orchestration function for autonomous tasks ---
def execute_autonomous_tasks(user_id, memory_instance, gmail_service, llm_client, config, db_client):
    logging.info(f"--- Executing Autonomous Tasks for user {user_id} ---")

    # 1) Verify that memory and user_profile exist
    if not memory_instance or not memory_instance.user_profile:
        logging.error(f"Cannot execute autonomous tasks: Memory or user profile not available for {user_id}.")
        return

    profile = memory_instance.user_profile

    # +++ DEBUG: Serialize and log the entire profile object +++
    try:
        profile_serializable = json.loads(json.dumps(profile, default=str))
        logging.info(f"GCF DEBUG: Full user_profile loaded for {user_id}: {json.dumps(profile_serializable, indent=2)}")
    except Exception as e_dump:
        logging.error(f"GCF DEBUG: Could not serialize and dump full profile: {e_dump}")
        logging.info(f"GCF DEBUG: Raw profile object (might be complex): {profile}")

    agent_prefs = profile.get("agent_preferences", {})
    logging.info(f"GCF DEBUG: Extracted agent_prefs: {json.dumps(agent_prefs, indent=2)}")
    autonomous_settings = profile.get("autonomous_settings", {})

    # We’ll use this flag to know if autonomous mode was truly enabled for this run
    autonomous_mode_run = False

    is_auton_enabled_in_gcf = agent_prefs.get("autonomous_mode_enabled", False)
    logging.info(f"GCF DEBUG: Value of 'autonomous_mode_enabled' from loaded agent_prefs: {is_auton_enabled_in_gcf}")

    if not is_auton_enabled_in_gcf:
        logging.info(f"Autonomous mode disabled for user {user_id}. Skipping tasks.")
        return
    else:
        # If autonomous_mode_enabled is true, mark it so we can generate a summary at the end
        autonomous_mode_run = True

    # --- 1. Auto-Archiving ---
    archived_count = 0  # Will track how many emails we queued for archiving
    if agent_prefs.get("allow_auto_archiving", False) and \
       autonomous_settings.get("auto_archive", {}).get("enabled", False) and \
       should_run_task("auto_archive", AUTO_ARCHIVE_CHECK_INTERVAL_MINUTES, memory_instance):

        logging.info(f"Running Auto-Archive task for user {user_id}...")
        archive_settings = autonomous_settings.get("auto_archive", {})
        excluded_senders = {s.lower() for s in archive_settings.get("excluded_senders", [])}

        # Find emails older than N days (default 7) with low priority or “Promotion” purpose
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=archive_settings.get("archive_after_days", 7))

        base_query = db_client.collection(EMAILS_COLLECTION).where(filter=FieldFilter("user_id", "==", user_id))
        q_low_prio = base_query.where(filter=FieldFilter("priority", "==", "LOW")) \
                       .where(filter=FieldFilter("processed_timestamp", "<", cutoff_date)) \
                       .limit(50)
        q_promo = base_query.where(filter=FieldFilter("llm_purpose", "==", "promotion")) \
                      .where(filter=FieldFilter("processed_timestamp", "<", cutoff_date)) \
                      .limit(50)

        email_ids_to_check = set()
        try:
            for doc in q_low_prio.stream():
                email_ids_to_check.add(doc.id)
            for doc in q_promo.stream():
                email_ids_to_check.add(doc.id)
            # You could add more queries here for other criteria (e.g., “Notifications”)
        except Exception as e:
            logging.error(f"Error querying emails for auto-archiving: {e}", exc_info=True)

        # Process up to 20 IDs in this run
        for email_id in list(email_ids_to_check)[:20]:
            try:
                email_doc = db_client.collection(EMAILS_COLLECTION).document(email_id).get()
                if not email_doc.exists:
                    continue

                email_data = email_doc.to_dict()
                sender = email_data.get("sender", "").lower()
                sender_email_part = _extract_email_address(sender)

                # Skip excluded senders or domains
                if sender_email_part and sender_email_part in excluded_senders:
                    continue
                if any(excl in sender for excl in excluded_senders if excl.startswith('@')):
                    continue

                # Request “archive” action in Firestore; if that succeeds, increment counter
                if database_utils.request_email_action(email_id, "archive"):
                    archived_count += 1
            except Exception as e_arc:
                logging.error(f"Error processing email {email_id} for auto-archive: {e_arc}", exc_info=True)

        logging.info(f"Auto-Archive: Queued {archived_count} emails for archiving for user {user_id}.")
        # Update last run timestamp even if count is zero
        update_task_last_run("auto_archive", memory_instance)

    # --- 2. Daily Summary ---
    daily_summary_queued = False  # Will track whether we queued a daily summary email
    if autonomous_settings.get("daily_summary", {}).get("enabled", False) and \
       should_run_task("daily_summary", DAILY_SUMMARY_CHECK_INTERVAL_MINUTES, memory_instance):

        summary_settings = autonomous_settings.get("daily_summary", {})
        summary_time_str = summary_settings.get("time", "08:00")  # e.g. “08:00”
        summary_content_prefs = summary_settings.get("content", ["High priority emails"])

        # Because Cloud Functions run in UTC, compare against UTC hour.
        now_utc = datetime.now(timezone.utc)
        try:
            summary_hour, summary_minute = map(int, summary_time_str.split(':'))
            if now_utc.hour == summary_hour:
                logging.info(f"Running Daily Summary task for user {user_id}...")

                emails_for_summary_df = pd.DataFrame()

                if "High priority emails" in summary_content_prefs:
                    cutoff_24h = datetime.now(timezone.utc) - timedelta(days=1)
                    query_hp = db_client.collection(EMAILS_COLLECTION) \
                        .where(filter=FieldFilter("user_id", "==", user_id)) \
                        .where(filter=FieldFilter("priority", "in", [PRIORITY_CRITICAL, PRIORITY_HIGH])) \
                        .where(filter=FieldFilter("processed_timestamp", ">=", cutoff_24h)) \
                        .order_by("processed_timestamp", direction=firestore.Query.DESCENDING) \
                        .limit(10)

                    summary_emails_list = [doc.to_dict() for doc in query_hp.stream()]
                    if summary_emails_list:
                        emails_for_summary_df = pd.DataFrame(summary_emails_list)

                if not emails_for_summary_df.empty:
                    summary_text = prepare_email_batch_overview(
                        llm_client,
                        emails_for_summary_df.to_dict(orient='records'),
                        config,
                        memory_instance
                    )
                    user_email = profile.get("email")

                    # Fallback: If profile did not contain an email, fetch via Gmail API
                    if not user_email and gmail_service:
                        try:
                            user_profile_gmail = _gmail_get_user_profile(gmail_service)
                            user_email = user_profile_gmail.get('emailAddress')
                        except Exception as e_get_email:
                            logging.error(f"Could not get user's email for daily summary: {e_get_email}", exc_info=True)

                    if user_email and summary_text and not summary_text.startswith("Error:"):
                        email_subject = f"Maia Daily Email Summary - {datetime.now().strftime('%Y-%m-%d')}"
                        action_params = {
                            "to": user_email,
                            "subject": email_subject,
                            "body": summary_text,
                            "is_html": False
                        }
                        if database_utils.request_email_action(email_id=None, action_type="send_draft", params=action_params):
                            logging.info(f"Daily summary queued for sending to {user_email}.")
                            daily_summary_queued = True
                            update_task_last_run("daily_summary", memory_instance)
                        else:
                            logging.error(f"Failed to queue daily summary for user {user_id}.")
                    elif not user_email:
                        logging.error(f"Cannot send daily summary for {user_id}: User email not found in profile.")
                    else:
                        logging.warning(f"Daily summary generation failed or the summary text was empty for user {user_id}.")
                else:
                    logging.info(f"No relevant emails found for daily summary for user {user_id}.")
                    update_task_last_run("daily_summary", memory_instance)
            else:
                logging.debug(f"Not time for daily summary for {user_id}. Current UTC hour: {now_utc.hour}, Configured: {summary_hour}")
        except ValueError:
            logging.error(f"Invalid time format for daily_summary for user {user_id}: {summary_time_str}", exc_info=True)
        except Exception as e_sum:
            logging.error(f"Error during daily summary task for {user_id}: {e_sum}", exc_info=True)

    # --- 3. Follow-up Reminders ---
    found_follow_ups = 0  # Will count how many new follow-up tasks we created
    if autonomous_settings.get("follow_up", {}).get("enabled", False) and \
       should_run_task("follow_up_check", FOLLOW_UP_CHECK_INTERVAL_MINUTES, memory_instance):

        logging.info(f"Running Follow-up Reminder task for user {user_id}...")
        follow_up_settings = autonomous_settings.get("follow_up", {})
        remind_days = follow_up_settings.get("remind_days", 3)
        priority_only = follow_up_settings.get("priority_only", True)

        if not gmail_service:
            logging.warning(f"Cannot check follow-ups for {user_id}: Gmail service not available in GCF context.")
        else:
            try:
                sent_messages = list_sent_emails(
                    gmail_service,
                    days_ago=remind_days + 15,
                    max_results=50
                )

                for message_info in sent_messages:
                    thread_id = message_info.get('threadId')
                    message_id = message_info.get('id')
                    if not thread_id or not message_id:
                        continue

                    task_exists_query = db_client.collection("user_tasks") \
                                     .where(filter=firestore.FieldFilter("user_id", "==", user_id)) \
                                     .where(filter=firestore.FieldFilter("task_type", "==", "follow_up_needed")) \
                                     .where(filter=firestore.FieldFilter("related_email_id", "==", message_id)) \
                                     .limit(1).stream()
                    if next(task_exists_query, None):
                        logging.debug(f"Follow-up task already exists for sent email {message_id}. Skipping.")
                        continue

                    has_reply = check_thread_for_reply(gmail_service, thread_id, message_id)
                    if not has_reply:
                        msg_details = get_email_details(gmail_service, message_id)
                        if msg_details:
                            parsed_sent_email = parse_email_content(msg_details)
                            sent_date_str = parsed_sent_email.get('date')
                            sent_dt = None
                            try:
                                from dateutil import parser
                                sent_dt = parser.parse(sent_date_str)
                                if sent_dt.tzinfo is None:
                                    sent_dt = sent_dt.replace(tzinfo=timezone.utc)
                            except Exception:
                                pass

                            if sent_dt and (datetime.now(timezone.utc) - sent_dt).days >= remind_days:
                                # If priority_only is True, you could check an original email priority here.
                                # For now, we create a follow-up task regardless.
                                recipient = next(
                                    (h['value'] for h in msg_details['payload']['headers'] if h['name'].lower() == 'to'),
                                    '[No Recipient]'
                                )
                                task_data = {
                                    "user_id": user_id,
                                    "task_type": "follow_up_needed",
                                    "related_email_id": message_id,
                                    "subject": parsed_sent_email.get('subject', '[No Subject]'),
                                    "recipient": recipient,
                                    "sent_date": sent_dt,
                                    "status": "pending",
                                    "created_at": firestore.SERVER_TIMESTAMP
                                }
                                db_client.collection("user_tasks").add(task_data)
                                found_follow_ups += 1
                                logging.info(f"Created follow-up task for sent email {message_id} to {recipient}.")
                                if found_follow_ups >= 5:
                                    break
            except Exception as e_fup:
                logging.error(f"Error during follow-up check for {user_id}: {e_fup}", exc_info=True)

        logging.info(f"Follow-up Check: Created {found_follow_ups} new follow-up tasks for user {user_id}.")
        update_task_last_run("follow_up_check", memory_instance)

    # --- 4. Auto-Categorization/Priority Labels ---
    # (Handled inside the main email processing loop, so not repeated here.)

    # --- 5. Re-evaluate Unknown Email Purposes ---
    reclassified_count = 0  # Will count how many “Unknown” emails got reclassified
    RE_EVAL_UNKNOWN_INTERVAL_MINUTES = 1440
    if agent_prefs.get("allow_auto_reclassification", False) and \
       should_run_task("re_evaluate_unknowns", RE_EVAL_UNKNOWN_INTERVAL_MINUTES, memory_instance):

        logging.info(f"Running Re-evaluate Unknown Purposes task for user {user_id}...")
        try:
            unknown_emails_query = db_client.collection(EMAILS_COLLECTION) \
                .where(filter=FieldFilter("user_id", "==", user_id)) \
                .where(filter=FieldFilter("llm_purpose", "==", "Unknown")) \
                .limit(20)


            for doc_snapshot in unknown_emails_query.stream():
                email_id = doc_snapshot.id
                email_data = doc_snapshot.to_dict()
                email_data['id'] = email_id

                logging.debug(f"Re-evaluating email {email_id} with unknown purpose.")
                new_analysis = analyze_email_with_context(llm_client, email_data, config, memory_instance)

                if new_analysis and new_analysis.get("purpose") and new_analysis.get("purpose") != "Unknown":
                    update_fields = {
                        "llm_purpose": new_analysis.get("purpose"),
                        "llm_urgency": new_analysis.get("urgency_score"),
                        "response_needed": new_analysis.get("response_needed"),
                        "estimated_time": new_analysis.get("estimated_time"),
                        "last_reclassified_utc": firestore.SERVER_TIMESTAMP
                    }
                    db_client.collection(EMAILS_COLLECTION).document(email_id).update(update_fields)
                    reclassified_count += 1
                    logging.info(f"Re-classified email {email_id} to purpose: {new_analysis.get('purpose')}")
                else:
                    logging.debug(f"Could not re-classify email {email_id}; LLM still returned Unknown or failed.")

            logging.info(f"Re-evaluate Unknowns: Re-classified {reclassified_count} emails for user {user_id}.")
            update_task_last_run("re_evaluate_unknowns", memory_instance)
        except Exception as e_reval:
            logging.error(f"Error during re-evaluation of unknown purposes for {user_id}: {e_reval}", exc_info=True)

    # --- FINAL SUMMARY: Which autonomous actions ran this GCF execution? ---
    if autonomous_mode_run:
        actions_taken_summary = []

        if archived_count > 0:
            actions_taken_summary.append(f"Auto-Archive: Queued {archived_count} emails.")
        if daily_summary_queued:
            actions_taken_summary.append("Daily Summary: Queued for sending.")
        if found_follow_ups > 0:
            actions_taken_summary.append(f"Follow-up Check: Created {found_follow_ups} new tasks.")
        if reclassified_count > 0:
            actions_taken_summary.append(f"Re-evaluate Unknowns: Re-classified {reclassified_count} emails.")

        if actions_taken_summary:
            summary_message = (
                f"Autonomous actions for user {user_id} this run: "
                + "; ".join(actions_taken_summary)
            )
            logging.info(summary_message)

            # Optionally save this summary back into the user's profile in Firestore
            try:
                memory_instance.save_profile_updates({
                    "last_autonomous_run_summary": summary_message,
                    "last_autonomous_run_timestamp_utc": datetime.now(timezone.utc).isoformat()
                })
            except Exception as e_save:
                logging.error(f"Could not save last autonomous run summary to memory: {e_save}", exc_info=True)
        else:
            no_action_msg = "No specific autonomous actions taken in this run."
            logging.info(f"Autonomous mode was enabled for user {user_id}, but {no_action_msg}")
            try:
                memory_instance.save_profile_updates({
                    "last_autonomous_run_summary": no_action_msg,
                    "last_autonomous_run_timestamp_utc": datetime.now(timezone.utc).isoformat()
                })
            except Exception as e_save2:
                logging.error(f"Could not save no-action summary to memory: {e_save2}", exc_info=True)

    logging.info(f"--- Finished Autonomous Tasks for user {user_id} ---")
    
# === *** IMPLEMENTATION of Training Data Fetching *** ===
def fetch_and_prepare_training_data(db_client):
    """
    Fetches feedback and corresponding email data from Firestore, prepares
    it into a DataFrame suitable for ML model retraining.

    Args:
        db_client: Initialized Firestore client instance.

    Returns:
        pandas.DataFrame: DataFrame with columns required for training
                          ('text_features', 'llm_purpose', 'sender_domain',
                           'llm_urgency', 'corrected_priority'), or None if
                           no data or an error occurs.
    """
    logging.info("--- Starting fetch_and_prepare_training_data ---")
    if not db_client:
        logging.error("Firestore client not provided.")
        return None

    try:
        # 1. Query Feedback collection, get latest feedback per email_id
        logging.info("Querying feedback collection (ordered by timestamp desc)...")
        feedback_query = db_client.collection(FEEDBACK_COLLECTION).order_by(
            'feedback_timestamp', direction=firestore.Query.DESCENDING
        ).stream()

        latest_feedback = {}  # email_id -> corrected_priority
        email_ids_with_feedback = set()
        feedback_count = 0
        for doc in feedback_query:
            feedback_count += 1
            data = doc.to_dict()
            email_id = data.get('email_id')
            corrected_priority = data.get('corrected_priority')

            # Store only the first (latest) feedback encountered for this email_id
            if email_id and corrected_priority and email_id not in latest_feedback:
                latest_feedback[email_id] = corrected_priority
                email_ids_with_feedback.add(email_id)

        if not email_ids_with_feedback:
            logging.info(f"No feedback entries found ({feedback_count} total docs scanned). Cannot train.")
            return None
        logging.info(f"Found latest feedback for {len(email_ids_with_feedback)} unique emails from {feedback_count} total feedback docs.")
    
        # 2. Query corresponding emails from Emails collection using batches
        logging.info("Fetching corresponding email data...")
        email_docs_data = {}  # email_id -> email_data_dict
        email_id_list = list(email_ids_with_feedback) # Convert set to list
        batch_size = 10 # Keep reduced size for now
    
        # --- Add Logging for the *full* list ---
        logging.info(f"Created email_id_list for fetching. Type: {type(email_id_list)}, Count: {len(email_id_list)}")
        # Log first few elements safely for inspection, avoiding overly long logs
        logging.info(f"First few email_ids in list: {email_id_list[:10]}")
        # --- End Logging for the full list ---
    
        # +++ START TEMPORARY DEBUG: Try getting a SINGLE document +++
        single_doc_fetch_success = False
        if email_id_list:
            test_id = email_id_list[0]
            
            try:
                doc_ref = db_client.collection(EMAILS_COLLECTION).document(test_id)
                doc_snapshot = doc_ref.get()
                if doc_snapshot.exists:
                    logging.info(f"--- DEBUG: Successfully got document {test_id}. Adding to email_docs_data.")
                    # Store the data for the rest of the function to potentially use
                    email_docs_data[test_id] = doc_snapshot.to_dict()
                    single_doc_fetch_success = True
                else:
                    logging.warning(f"--- DEBUG: Document {test_id} does not exist (but was expected based on feedback).")
            except Exception as e_get:
                logging.error(f"--- DEBUG: FAILED to get single document {test_id}: {e_get}", exc_info=True)
                # For this test, let's allow execution to continue even if single get fails
                # to see if subsequent code works with potentially empty email_docs_data
        else:
            logging.warning("--- DEBUG: email_id_list is empty, cannot test single document fetch. ---")
        # +++ END TEMPORARY DEBUG +++
    
        # --- Comment out or skip the batch processing loop for this test ---
        
        logging.info("--- DEBUG: Restoring batch processing loop ---")
        # Remove the block comment markers /* and */
        # --- *** NEW FETCHING STRATEGY: Individual GET calls *** ---
        logging.info("--- Starting individual document fetching loop ---")
        fetched_count = 0
        failed_fetch_count = 0
        for email_id in email_id_list:
            if not isinstance(email_id, str) or not email_id: # Basic validation
                 logging.warning(f"Invalid email_id found in list: {email_id}. Skipping.")
                 failed_fetch_count +=1
                 continue
            try:
                # logging.debug(f"Attempting to fetch document: {email_id}") # Optional: more verbose logging
                doc_ref = db_client.collection(EMAILS_COLLECTION).document(email_id)
                doc_snapshot = doc_ref.get()
                if doc_snapshot.exists:
                    email_docs_data[email_id] = doc_snapshot.to_dict()
                    fetched_count += 1
                    # Optional: Log progress periodically
                    # if fetched_count % 20 == 0:
                    #    logging.info(f"Fetched {fetched_count}/{len(email_id_list)} email documents...")
                else:
                    logging.warning(f"Document {email_id} not found in emails collection (but was expected from feedback).")
                    failed_fetch_count += 1
            except Exception as e_get:
                logging.error(f"Failed to fetch document {email_id}: {e_get}", exc_info=True)
                failed_fetch_count += 1
                # Decide whether to continue or break? Let's continue for now.
    
        logging.info(f"--- Finished individual document fetching. Successfully fetched: {fetched_count}, Failed/Not Found: {failed_fetch_count} ---")
        # --- *** END OF NEW FETCHING STRATEGY *** ---
        
        # --- End comment out ---
    
    
        
    
        # 3. Combine data, perform feature engineering, handle missing values
        logging.info("Combining feedback and email data, preparing features...")
        training_list = []
        missing_email_data_count = 0
        # This loop will now only run for IDs where data was actually fetched (potentially only 1 from the debug step)
        for email_id, corrected_priority in latest_feedback.items():
            if email_id in email_docs_data:
                # ... (rest of the data combination logic remains the same) ...
    
                email_data = email_docs_data[email_id]
                subject = email_data.get('subject', '')
                body = email_data.get('body_text', '')
                text_features = (subject if isinstance(subject, str) else '') + " " + (body if isinstance(body, str) else '')
                sender = email_data.get('sender', '')
                sender_domain = extract_domain(sender)
                llm_urgency_raw = email_data.get('llm_urgency')
                llm_urgency = 0
                if llm_urgency_raw is not None:
                    try:
                        llm_urgency = int(llm_urgency_raw)
                    except (ValueError, TypeError):
                        logging.warning(f"Could not convert llm_urgency '{llm_urgency_raw}' to int for email {email_id}. Using default 0.")
                        llm_urgency = 0
                else:
                    llm_urgency = 0
    
                llm_purpose_raw = email_data.get('llm_purpose')
                llm_purpose = llm_purpose_raw if llm_purpose_raw else "Unknown"
    
                training_list.append({
                    'text_features': text_features.strip(),
                    'llm_purpose': llm_purpose,
                    'sender_domain': sender_domain,
                    'llm_urgency': llm_urgency,
                    'corrected_priority': corrected_priority
                })
            else:
                # This log might appear more often now since we skipped batching
                # Only log if we expected data based on the single fetch test
                # if email_id == (email_id_list[0] if email_id_list else None) and not single_doc_fetch_success:
                     # No need for this specific warning now, handled by the DEBUG logs
                     pass
                # else:
                     # Normal case if we only fetched one doc
                     # logging.debug(f"Skipping feedback for email_id {email_id} as its data was not fetched in this debug run.")
                     missing_email_data_count += 1
    
    
        if missing_email_data_count > 0 and len(email_docs_data) < len(latest_feedback):
             logging.info(f"Skipped combining data for {missing_email_data_count} feedback entries (expected in DEBUG mode).")

        # 4. Create DataFrame
        if not training_list:
            logging.error("No training samples could be prepared after merging feedback and email data. Cannot train.")
            return None

        training_df = pd.DataFrame(training_list)
        logging.info(f"Successfully prepared training DataFrame with {len(training_df)} samples.")

        # Optional: Log info for debugging
        logging.debug(f"Training DataFrame Info:\n{training_df.info()}")
        logging.debug(f"Training DataFrame Head:\n{training_df.head()}")
        logging.debug(f"Value counts for 'corrected_priority':\n{training_df['corrected_priority'].value_counts()}")

        return training_df

    except Exception as e:
        logging.error(f"An unexpected error occurred during fetch_and_prepare_training_data: {e}", exc_info=True)
        return None
# === *** END of Training Data Fetching Implementation *** ===

# --- NEW: Function to Process Action Requests ---
@retry(
    retry=retry_if_exception(is_retryable_gmail_error),  # Only retry on transient errors
    stop=stop_after_attempt(3),  # Try a total of 3 times
    wait=wait_exponential(multiplier=1, min=2, max=10)  # Wait 2s, then 4s, etc.
)
def process_action_requests(gmail_service):
    """
    Queries Firestore for pending actions and attempts to execute them with automatic retry mechanism.
    
    This function includes automatic retries with exponential backoff for increased
    reliability when dealing with transient network errors or temporary Gmail API
    unavailability.
    """
    if not database_utils.db:
        logging.error("Firestore client not available, cannot process action requests.")
        return 0
    if not gmail_service:
        logging.error("Gmail service not available, cannot process action requests.")
        return 0
    processed_count = 0
    logging.info("--- Checking for pending action requests ---")
    try:
        db = database_utils.get_db()
        if db is None:
            logging.error("Failed to initialize Firestore database for action requests processing")
            return 0
        query = (db.collection(ACTION_REQUESTS_COLLECTION)
                 .where(filter=FieldFilter('status', '==', 'pending'))
                 .limit(10))
        results = query.stream()
        for doc in results:
            request_id = doc.id
            request_data = doc.to_dict()
            email_id = request_data.get('email_id')
            action = request_data.get('action')
            params = request_data.get('params', {})
            logging.info(f"Processing action '{action}' (Request ID: {request_id}, Orig Email ID: {email_id})")
            
            if not action:
                logging.warning(f"Skipping invalid action request {request_id}: Missing action.")
                update_action_request_status(request_id, "failed", "Missing action in request.")
                continue
            
            success = False
            error_message = ""
            
            try:
                if action == "archive":
                    if not email_id:
                         error_message = "Missing email_id for archive action."
                         logging.warning(f"Cannot archive for request {request_id}: {error_message}")
                    else:
                        _gmail_archive_email(gmail_service, email_id)
                        logging.info(f"Successfully archived email {email_id}.")
                        success = True
                
                elif action == "send_draft":
                    to_recipient = params.get("to")
                    subject = params.get("subject")
                    body = params.get("body")
                    is_html = params.get("is_html", False) 

                    if not to_recipient or not subject or not body:
                        error_message = "Missing 'to', 'subject', or 'body' in params for send_draft."
                        logging.warning(f"Cannot send draft for request {request_id}: {error_message}")
                    else:
                        message = MIMEText(body, 'html' if is_html else 'plain')
                        message['to'] = to_recipient
                        message['subject'] = subject
                        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
                        send_body = {'raw': raw_message}
                        _gmail_send_message(gmail_service, send_body)
                        logging.info(f"Successfully sent email draft (Request ID: {request_id}) to {to_recipient}.")
                        success = True
                
                elif action == "apply_label":
                    label_names_from_params = params.get("labels_to_add", []) # These are names like "Maia/Priority/Medium"
                    if not email_id:
                        error_message = "Missing email_id for apply_label action."
                        logging.warning(f"Cannot apply label for request {request_id}: {error_message}")
                    elif not label_names_from_params or not isinstance(label_names_from_params, list):
                        error_message = "Missing or invalid 'labels_to_add' (names) in params for apply_label."
                        logging.warning(f"Cannot apply label for request {request_id}: {error_message}")
                    else:
                        actual_label_ids_to_apply = get_or_create_label_ids(gmail_service, label_names_from_params)
                        
                        if actual_label_ids_to_apply: # Check if we got any valid IDs back
                            _gmail_apply_labels(gmail_service, email_id, actual_label_ids_to_apply)
                            logging.info(f"Successfully applied/ensured labels (IDs: {actual_label_ids_to_apply}) to email {email_id} for names {label_names_from_params}.")
                            success = True
                        elif label_names_from_params: # Had names, but couldn't get/create IDs
                            error_message = f"Failed to get or create one or more specified labels: {label_names_from_params}."
                            logging.error(f"For request {request_id}, email {email_id}: {error_message}")
                        else: # No label names were provided in the first place (already caught, but defensive)
                            error_message = "No label names provided to apply."
                            logging.warning(f"For request {request_id}, email {email_id}: {error_message}")
                
                else:
                    logging.warning(f"Unsupported action '{action}' requested (Request ID: {request_id}).")
                    error_message = f"Unsupported action type: {action}"
            
            except HttpError as error:
                logging.error(f"HttpError performing action '{action}' (Request ID: {request_id}): {error}", exc_info=True)
                error_message = f"API Error: {error.resp.status} - {error.content.decode()}"
            except Exception as e:
                logging.error(f"Unexpected error performing action '{action}' (Request ID: {request_id}): {e}", exc_info=True)
                error_message = f"Unexpected Error: {type(e).__name__}"
            
            update_action_request_status(request_id, "completed" if success else "failed", error_message)
            processed_count += 1
            
        logging.info(f"--- Finished processing action requests. Processed {processed_count} requests this run. ---")
        return processed_count
    except Exception as e:
        logging.error(f"Error querying action requests: {e}", exc_info=True)
        return 0


# === Main GCF Handler ===
@functions_framework.http
def process_emails_gcf(request):
    """
    Google Cloud Function entry point. Processes emails, handles retraining, and logs reports.
    Triggered by HTTP request (e.g., from Cloud Scheduler).
    """
    # Initialize Firestore client first (lazy initialization)
    initialize_firestore()
    
    # +++ VERY FIRST LOG LINE +++
    logging.critical("--- process_emails_gcf function STARTING EXECUTION (Revision XYZ) ---")
    # +++ END VERY FIRST LOG LINE +++
    global storage_client, secret_client, config, llm_client_gcf
    function_start_time = time.time()
    logging.info("Cloud Function triggered.")

    # --- Initialize Clients and Config (Cached across warm instances) ---
    try:
        if config is None:
            config = load_config("config.json")
            if not config: raise ValueError("Failed to load configuration.")
            logging.info("Configuration loaded inside handler.")
        # Firestore client is now initialized via initialize_firestore() call above
        # --- ADD MEMORY INITIALIZATION ---
        try:
            db = database_utils.get_db()
            if db is None:
                logging.critical("Failed to get Firestore database client for AgentMemory")
                return "Error: Database initialization failed", 500
            # Note: user_id will be updated after Gmail authentication
            memory_instance = AgentMemory(db_client=db, user_id="default_user") # Temporary, will be updated after auth
            logging.info("AgentMemory initialized inside handler.")
        except Exception as e_mem:
            logging.critical(f"Failed to initialize AgentMemory: {e_mem}", exc_info=True)
            return f"Error: AgentMemory init failed: {e_mem}", 500
        # --- END MEMORY INITIALIZATION ---
        if storage_client is None:
            storage_client = storage.Client()
            logging.info("GCS client initialized inside handler.")
            
            # --- Initialize state file if it doesn't exist ---
            try:
                state = read_retrain_state_from_gcs()
                if state is None:  # File doesn't exist
                    logging.info("No retrain state found. Initializing with current feedback count.")
                    try:
                        current_count = get_feedback_count()
                        if write_retrain_state_to_gcs(current_count):
                            logging.info(f"Initialized retrain state with count: {current_count}")
                    except Exception as e:
                        logging.error(f"Failed to initialize retrain state: {e}")
            except Exception as e:
                logging.error(f"Error checking/initializing retrain state: {e}")
            
        if secret_client is None:
            secret_client = secretmanager.SecretManagerServiceClient()
            logging.info("Secret Manager client initialized inside handler.")
        if llm_client_gcf is None:
            if not ANTHROPIC_SECRET_NAME: raise ValueError("ANTHROPIC_SECRET_NAME env var not set.")
            anthropic_key = get_secret(ANTHROPIC_SECRET_NAME) # Use helper
            if not anthropic_key: raise ValueError("Failed to get Anthropic API Key from Secret Manager.")
            llm_client_gcf = anthropic.Anthropic(api_key=anthropic_key)
            logging.info(f"Anthropic client initialized inside handler for model: {config['llm_settings']['model']}")
            
        # Initialize hybrid LLM manager if enabled
        global hybrid_llm_manager
        if hybrid_llm_manager is None and config.get('reasoning', {}).get('hybrid_llm', False):
            try:
                # Optionally fetch OpenAI key if configured
                openai_key = None
                if OPENAI_SECRET_NAME:
                    try:
                        openai_key = get_secret(OPENAI_SECRET_NAME)
                        logging.info("OpenAI API key fetched successfully")
                    except Exception as e:
                        logging.warning(f"Failed to fetch OpenAI key from Secret Manager: {e}")
                
                # Pass the API keys to avoid environment variable lookup
                hybrid_llm_manager = create_hybrid_llm_manager(
                    config=config,
                    openai_api_key=openai_key,
                    anthropic_api_key=anthropic_key
                )
                logging.info("Hybrid LLM manager initialized successfully")
            except Exception as e:
                logging.warning(f"Failed to initialize hybrid LLM manager: {e}. Will use standard Anthropic client.")
    except Exception as e:
        logging.critical(f"Failed during initialization or config loading: {e}", exc_info=True)
        return f"Error: Initialization/Config failed: {e}", 500

    # --- Check Required Environment Variables ---
    if not TOKEN_GCS_BUCKET: return "Error: TOKEN_GCS_BUCKET env var missing", 500
    if not MODEL_GCS_BUCKET: return "Error: MODEL_GCS_BUCKET env var missing", 500
    if not ANTHROPIC_SECRET_NAME: return "Error: ANTHROPIC_SECRET_NAME env var missing", 500
    # MODEL env vars checked later during loading/saving

    # --- Get ML Filenames from Config ---
    # These are the BASE filenames used for constructing GCS paths and local temp paths
    ml_settings = config.get('ml_settings', {})
    local_pipeline_filename = ml_settings.get('pipeline_filename', 'ml_models/pipeline.joblib')
    local_label_encoder_filename = ml_settings.get('label_encoder_filename', 'ml_models/label_encoder.joblib')

    # --- Retraining Check and Execution Logic ---
    retraining_needed = False
    new_feedback_trigger_met = False
    current_feedback_count = 0
    last_feedback_count = 0
    
    # --- Add Log Point 1 ---
    logging.info("DEBUG: Checking if retraining is enabled in config...")
    if config.get('retraining', {}).get('enabled', False):
        # --- Add Log Point 2 ---
        logging.info("DEBUG: Retraining is enabled. Proceeding with check.")
        trigger_count = config['retraining'].get('trigger_feedback_count', 10)
        try:
            # --- Add Log Point 3 ---
            logging.info("DEBUG: Calling get_feedback_count()...")
            current_feedback_count = get_feedback_count() # From database_utils
            # --- Add Log Point 4 ---
            logging.info(f"DEBUG: get_feedback_count() returned: {current_feedback_count}")
    
            # --- Add Log Point 5 ---
            logging.info("DEBUG: Calling read_retrain_state_from_gcs()...")
            state_gcs = read_retrain_state_from_gcs() # Read GCS state
             # --- Add Log Point 6 ---
            logging.info(f"DEBUG: read_retrain_state_from_gcs() returned: {state_gcs}")
    
            last_feedback_count = state_gcs.get('last_feedback_count', 0) if state_gcs else 0 # Handle None case
    
            # --- Add Log Point 7 ---
            logging.info(f"DEBUG: Values before comparison: current_feedback_count={current_feedback_count}, last_feedback_count={last_feedback_count}, trigger_count={trigger_count}")
    
            new_feedback_count = current_feedback_count - last_feedback_count
            logging.info(f"Retraining Check: Current Feedback={current_feedback_count}, Last Recorded={last_feedback_count}, New={new_feedback_count}, Trigger Threshold={trigger_count}") # Keep original log
    
            if new_feedback_count >= trigger_count:
                 # --- Add Log Point 8 ---
                logging.info(f"DEBUG: Threshold met ({new_feedback_count} >= {trigger_count}). Setting retraining_needed=True.")
                retraining_needed = True
                new_feedback_trigger_met = True
            else:
                 # --- Add Log Point 9 ---
                logging.info(f"DEBUG: Threshold NOT met ({new_feedback_count} < {trigger_count}). Skipping.")
                logging.info("New feedback count below trigger threshold. Skipping automatic retraining.") # Keep original log
        except Exception as e:
            # --- Add Log Point 10 ---
            logging.error(f"DEBUG: Error during retraining check process: {e}", exc_info=True)
            logging.error(f"Error during retraining check: {e}", exc_info=True) # Keep original log
            logging.warning("Proceeding without retraining due to check error.")
            retraining_needed = False
    else:
        # --- Add Log Point 11 ---
        logging.info("DEBUG: Retraining is disabled in config (config value: {}).".format(config.get('retraining', {}).get('enabled')))
        logging.info("Automatic retraining is disabled in config.") # Keep original log
    
    # --- Retraining Execution Block ---
    logging.info(f"DEBUG: Checking retraining_needed flag. Value: {retraining_needed}")
    if retraining_needed:
        logging.info("--- Attempting ML Model Retraining ---")
        # Check necessary env vars for model saving
        if not MODEL_GCS_BUCKET or not MODEL_GCS_PATH_PREFIX:
             logging.error("MODEL_GCS_BUCKET or MODEL_GCS_PATH_PREFIX env vars not set. Cannot perform retraining.")
        else:
            # *** CALL THE IMPLEMENTED FUNCTION ***
            # Pass the initialized Firestore client
            training_df = fetch_and_prepare_training_data(database_utils.db)

            # --- Add Minimum Sample Check ---
            MIN_SAMPLES_FOR_TRAINING = 5 # Set a reasonable minimum
            if training_df is not None and not training_df.empty and len(training_df) >= MIN_SAMPLES_FOR_TRAINING:
                logging.info(f"Training DataFrame has {len(training_df)} samples (>= {MIN_SAMPLES_FOR_TRAINING}). Proceeding with training.")
                # --- The rest of the training call logic goes inside this if block ---
                logging.info(f"Successfully fetched/prepared training data with {len(training_df)} records.")
                # Construct full GCS blob names for models
                pipeline_blob_name = os.path.join(MODEL_GCS_PATH_PREFIX, local_pipeline_filename)
                encoder_blob_name = os.path.join(MODEL_GCS_PATH_PREFIX, local_label_encoder_filename)
            
                # Call the training function, passing GCS details
                trained_pipeline, trained_encoder = build_and_train_pipeline(
                    training_df=training_df,
                    storage_client=storage_client,
                    bucket_name=MODEL_GCS_BUCKET,
                    pipeline_blob_name=pipeline_blob_name,
                    encoder_blob_name=encoder_blob_name,
                    local_pipeline_filename=local_pipeline_filename, # Pass base names for temp local save
                    local_encoder_filename=local_label_encoder_filename
                )

                if trained_pipeline and trained_encoder:
                    logging.info("Retraining and model upload to GCS successful.")
                    # --- UPDATE STATE FILE HERE ---
                    if write_retrain_state_to_gcs(current_feedback_count):
                        logging.info(f"Successfully updated GCS retrain state with count: {current_feedback_count}")
                    else:
                        logging.error("Failed to update GCS retrain state after successful retraining.")
                    retraining_needed = False
                else:
                    logging.error("Retraining function failed or did not return models. State not updated.")
                    retraining_needed = False
                # --- End of the training call logic ---
            elif training_df is not None: # Check if DF exists but is too small
                 logging.warning(f"Training DataFrame has only {len(training_df)} samples, which is less than the required minimum of {MIN_SAMPLES_FOR_TRAINING}. Skipping training for this run.")
                 retraining_needed = False # Skip training
            else: # Handle case where training_df is None
                logging.error("Failed to fetch or prepare training data (DataFrame is None). Skipping retraining for this run.")
                retraining_needed = False # Skip training
            # --- End Minimum Sample Check ---
                
    # --- End Retraining Execution Block ---
    
    # --- *** REMOVE SEPARATE USER PREFERENCES FETCH *** ---
    # user_prefs = read_user_preferences() # Fetch once per run
    # user_important_senders_list = user_prefs.get("user_important_senders", [])
    # logging.info(f"Fetched {len(user_important_senders_list)} user-defined important senders for this run.")
    # --- *** END REMOVE SEPARATE USER PREFERENCES FETCH *** ---

    logging.info("Initialization, config loading, and retraining check/execution complete.")

    # --- Authenticate Gmail ---
    logging.info("Authenticating Google Services using modern, unified auth_utils...")
    try:
        # This single line now handles everything
        gmail_service, _ = get_authenticated_services() # We only need gmail_service here
        
        if not gmail_service:
            # This error will now only be raised if the modern auth truly fails
            raise RuntimeError("Gmail authentication failed: get_authenticated_services returned None.")
        
        logging.info("Gmail authentication successful.")
        
        # Extract authenticated user's email address for proper user_id association
        try:
            user_profile = _gmail_get_user_profile(gmail_service)
            authenticated_user_email = user_profile.get('emailAddress')
            if not authenticated_user_email:
                logging.error("Could not extract user email from Gmail profile")
                authenticated_user_email = "unknown_user"  # Fallback - indicates authentication issue
            logging.info(f"Authenticated user email: {authenticated_user_email}")
            
            # Update memory instance with correct user_id
            if memory_instance:
                memory_instance.user_id = authenticated_user_email
                logging.info(f"Updated memory instance user_id to: {authenticated_user_email}")
        except Exception as e:
            logging.error(f"Failed to get user profile: {e}")
            authenticated_user_email = "unknown_user"  # Fallback - indicates profile fetch failure

    except Exception as e:
        logging.critical(f"Failed during unified Gmail Authentication: {e}", exc_info=True)
        return "Error: Gmail Auth Failed", 500
        
        # --- *** PROCESS ACTION REQUESTS (Before processing new emails) *** ---
        process_action_requests(gmail_service)
        # --- *** END PROCESS ACTION REQUESTS *** ---
        
        # --- *** NEW: EXECUTE AUTONOMOUS TASKS *** ---
        if memory_instance and gmail_service and llm_client_gcf and config and database_utils.db:
            try:
                logging.info("Executing autonomous tasks...")
                execute_autonomous_tasks(
                    user_id=authenticated_user_email, 
                    memory_instance=memory_instance,
                    gmail_service=gmail_service,
                    llm_client=llm_client_gcf,
                    config=config,
                    db_client=database_utils.db
                )
                logging.info("Autonomous tasks completed successfully.")
            except Exception as e_auto:
                logging.error(f"Error during execute_autonomous_tasks: {e_auto}", exc_info=True)
        else:
            logging.warning("Skipping autonomous tasks due to missing dependencies (memory, gmail, llm, config, or db).")
        # --- *** END NEW: EXECUTE AUTONOMOUS TASKS *** ---
        
    except Exception as e:
        logging.critical(f"Failed during Gmail Authentication: {e}", exc_info=True)
        return "Error: Gmail Auth Failed", 500
        

    # --- Load ML Model from GCS ---
    # (Keep model loading logic as implemented previously)
    ml_pipeline = None
    ml_label_encoder = None
    logging.info("Loading ML model components from GCS...")
    # Check MODEL env vars needed for loading
    if not MODEL_GCS_BUCKET:
        logging.warning("MODEL_GCS_BUCKET env var not set. Cannot load ML models from GCS.")
    else:
        # Construct full GCS blob names for models
        pipeline_blob_name = os.path.join(MODEL_GCS_PATH_PREFIX, local_pipeline_filename)
        encoder_blob_name = os.path.join(MODEL_GCS_PATH_PREFIX, local_label_encoder_filename)
        try:
            # Use temp dir for downloading models in GCF
            with tempfile.TemporaryDirectory() as tmpdir:
                local_pipeline_path = os.path.join(tmpdir, local_pipeline_filename)
                local_encoder_path = os.path.join(tmpdir, local_label_encoder_filename)

                bucket = storage_client.bucket(MODEL_GCS_BUCKET)
                pipeline_blob = bucket.blob(pipeline_blob_name)
                encoder_blob = bucket.blob(encoder_blob_name)

                # Check if BOTH files exist in GCS before attempting download
                pipeline_exists = pipeline_blob.exists(storage_client)
                encoder_exists = encoder_blob.exists(storage_client)

                if pipeline_exists and encoder_exists:
                    logging.info(f"Downloading models from gs://{MODEL_GCS_BUCKET}/{pipeline_blob_name} and .../{encoder_blob_name} to {tmpdir}")
                    pipeline_blob.download_to_filename(local_pipeline_path, client=storage_client)
                    encoder_blob.download_to_filename(local_encoder_path, client=storage_client)

                    ml_pipeline = joblib.load(local_pipeline_path)
                    ml_label_encoder = joblib.load(local_encoder_path)
                    logging.info("ML pipeline and label encoder loaded successfully from GCS.")
                else:
                    logging.warning(f"ML model files not found in GCS (Pipeline exists: {pipeline_exists}, Encoder exists: {encoder_exists}) at gs://{MODEL_GCS_BUCKET}/{pipeline_blob_name} and .../{encoder_blob_name}. Proceeding without ML classification. A model may need to be trained first.")

        except Exception as e:
            logging.error(f"Error downloading or loading ML components from GCS: {e}", exc_info=True)
            # Continue without ML model if loading fails, reset to None
            ml_pipeline = None
            ml_label_encoder = None
    # --- End ML Model Loading ---

    # Get feedback history for email classification (do this *after* potential retraining)
    feedback_history = get_feedback_history()

    # --- Fetch Emails ---
    logging.info("Fetching emails...")
    email_ids = [] # Initialize
    try:
        email_ids = get_unread_email_ids(
            gmail_service, # Use the authenticated service
            max_results=config['gmail']['fetch_max_results'],
            label_ids=config['gmail']['fetch_labels']
        )
        logging.info(f"Fetched {len(email_ids)} unread email IDs from Gmail: {email_ids}") # Log the actual list
    except Exception as e:
        logging.error(f"Failed to fetch email IDs: {e}", exc_info=True)
        # Exit if fetching fails
        return "Error: Failed to fetch email IDs", 500
    # --- End Fetch Emails ---


    # --- Process Emails Loop ---
    new_emails_processed_count = 0
    if not email_ids:
        logging.info("No emails found matching criteria.")
    else:
        logging.info(f"\nFound {len(email_ids)} emails. Checking against database...")
        for email_id in email_ids:
            try:
                # Check if already processed
                if is_email_processed(email_id):
                    # logging.debug(f"  Email ID {email_id} already processed. Skipping.") # Optional debug log
                    continue

                # Fetch details
                logging.info(f"  New email found ({email_id}). Fetching details...")
                email_details = get_email_details(gmail_service, email_id)
                if not email_details:
                    logging.warning(f"Could not fetch details for email {email_id}. Skipping.")
                    continue

                # Parse content
                parsed_email = parse_email_content(email_details)
                if not parsed_email:
                    logging.warning(f"Could not parse content for email {email_id}. Skipping.")
                    continue
                logging.info(f"  Email Parsed ({email_id}). Subject: {parsed_email.get('subject', '[No Subject]')}")

                # Process with memory (classification, summary, etc.)
                logging.info(f"  Attempting processing with memory for email {email_id}...")
                processed_email_data = process_email_with_memory(
                    email_data=parsed_email,
                    llm_client=llm_client_gcf,
                    config=config,
                    memory=memory_instance,
                    feedback_history=feedback_history,
                    ml_pipeline=ml_pipeline,
                    ml_label_encoder=ml_label_encoder
                )

                if not processed_email_data:
                    logging.error(f"process_email_with_memory returned None for email {email_id}. Skipping save.")
                    continue

                # Add authenticated user_id to email data before saving
                processed_email_data['user_id'] = authenticated_user_email
                
                # Log results
                logging.info(f"  Processing Result for {email_id}: Priority='{processed_email_data.get('priority')}', Summary='{str(processed_email_data.get('summary'))[:100]}...', LLM Purpose='{processed_email_data.get('llm_purpose')}', User ID='{authenticated_user_email}'")

                # --- *** NEW: AUTO-CATEGORIZATION *** ---
                if memory_instance and memory_instance.user_profile.get("agent_preferences", {}).get("allow_auto_categorization", False):
                    labels_to_add = []
                    priority_label = processed_email_data.get('priority')
                    purpose_label = processed_email_data.get('llm_purpose')

                    if priority_label and priority_label != 'N/A':
                        labels_to_add.append(f"Maia/Priority/{priority_label.capitalize()}")
                    if purpose_label and purpose_label != 'Unknown':
                        # Sanitize purpose for label (e.g., "Action Request" -> "Action-Request")
                        sanitized_purpose = purpose_label.replace(" ", "-")
                        labels_to_add.append(f"Maia/Purpose/{sanitized_purpose.capitalize()}")
                    
                    if labels_to_add:
                        logging.info(f"Auto-categorization: Requesting to apply labels {labels_to_add} to email {email_id}")
                        database_utils.request_email_action(email_id, "apply_label", params={"labels_to_add": labels_to_add})
                # --- *** END NEW: AUTO-CATEGORIZATION *** ---

                # --- *** NEW: AUTONOMOUS TASK EXTRACTION *** ---
                auto_task_config = config.get("autonomous_tasks", {}).get("auto_task_creation", {})
                if auto_task_config.get("enabled", False) and hybrid_llm_manager:
                    try:
                        # Extract tasks from the processed email
                        email_body = parsed_email.get('body', '')
                        email_subject = parsed_email.get('subject', '')
                        
                        if email_body and email_subject:
                            logging.info(f"Attempting autonomous task extraction for email {email_id}")
                            extracted_tasks = hybrid_llm_manager.extract_tasks_from_email(email_body, email_subject)
                            
                            if extracted_tasks and len(extracted_tasks) > 0:
                                tasks_saved = 0
                                
                                for task in extracted_tasks:
                                    try:
                                        # Add creation_method field to track autonomous creation
                                        task_data = {
                                            'task_description': task.get('task_description', ''),
                                            'deadline': task.get('deadline'),
                                            'stakeholders': task.get('stakeholders', []),
                                            'creation_method': 'autonomous'
                                        }
                                        
                                        task_id = save_task_to_firestore(task_data, authenticated_user_email, email_id)
                                        tasks_saved += 1
                                        logging.info(f"Autonomously saved task: '{task_data['task_description']}' (ID: {task_id})")
                                        
                                    except Exception as e_task:
                                        logging.error(f"Failed to save individual task from email {email_id}: {e_task}")
                                
                                if tasks_saved > 0:
                                    logging.info(f"Autonomously detected and saved {tasks_saved} tasks from email ID: {email_id}")
                                    
                                    # Log autonomous action for transparency
                                    try:
                                        action_log = {
                                            'timestamp': datetime.now(timezone.utc),
                                            'action_type': 'auto_task_creation',
                                            'email_id': email_id,
                                            'email_subject': email_subject[:100],  # Truncate for logging
                                            'tasks_created': tasks_saved,
                                            'reasoning': f"AI detected {tasks_saved} actionable tasks in email content",
                                            'confidence': 'high'  # Task extraction indicates high confidence
                                        }
                                        db = database_utils.get_db()
                                        if db is not None:
                                            db.collection(ACTION_LOG_COLLECTION).add(action_log)
                                        else:
                                            logging.error("Database not available for action logging")
                                        logging.info(f"Logged autonomous task creation action for email ID {email_id}")
                                    except Exception as e_log:
                                        logging.error(f"Failed to log autonomous task creation action for email ID {email_id}: {e_log}")
                                    
                                    # Broadcast autonomous action executed event via WebSocket
                                    try:
                                        from websocket_events import broadcast_autonomous_action_executed
                                        action_details = f"Auto-created {tasks_saved} task(s) from email '{email_subject}' - AI detected actionable items"
                                        
                                        broadcast_autonomous_action_executed(
                                            user_id=authenticated_user_email,
                                            email_id=email_id,
                                            action='task_creation',
                                            details=action_details
                                        )
                                        logging.info(f"Broadcasted autonomous task creation event for email ID {email_id}")
                                    except Exception as e_broadcast:
                                        logging.error(f"Failed to broadcast autonomous task creation for email ID {email_id}: {e_broadcast}")
                            else:
                                logging.debug(f"No tasks detected in email {email_id}")
                    except Exception as e_extract:
                        logging.error(f"Error during autonomous task extraction for email {email_id}: {e_extract}")
                # --- *** END NEW: AUTONOMOUS TASK EXTRACTION *** ---

                # --- *** NEW: AUTONOMOUS ACTION EVALUATION *** ---
                # Evaluate if autonomous actions should be taken based on classification confidence
                autonomous_config = config.get("autonomous_tasks", {})
                if autonomous_config.get("auto_archive", {}).get("enabled", False):
                    try:
                        auto_archive_threshold = autonomous_config.get("auto_archive", {}).get("confidence_threshold", 0.95)
                        email_purpose = processed_email_data.get('llm_purpose', '').lower()
                        purpose_confidence = processed_email_data.get('llm_purpose_confidence', 0.0)
                        email_priority = processed_email_data.get('priority', '')
                        
                        # Define purposes eligible for auto-archiving
                        archivable_purposes = ['newsletter', 'promotion', 'social', 'notification', 'marketing']
                        
                        # Check if email meets auto-archive criteria
                        if (email_purpose in archivable_purposes and 
                            purpose_confidence >= auto_archive_threshold and 
                            email_priority in ['LOW', 'MEDIUM']):
                            
                            logging.info(f"Auto-archiving email {email_id} immediately: Purpose '{email_purpose}' with {purpose_confidence:.1%} confidence")
                            
                            # Archive the email using Gmail API
                            archive_result = _gmail_archive_email(gmail_service, email_id)
                            
                            if archive_result:
                                # Update the processed email data to mark as archived
                                processed_email_data['is_archived'] = True
                                
                                # Log the autonomous action
                                try:
                                    action_log_doc = {
                                        "timestamp": firestore.SERVER_TIMESTAMP,
                                        "action_type": "auto_archive_immediate",
                                        "email_id": email_id,
                                        "email_subject": processed_email_data.get('subject', ''),
                                        "reason": f"Immediate auto-archive: '{email_purpose}' with {purpose_confidence:.0%} confidence"
                                    }
                                    db = database_utils.get_db()
                                    if db is not None:
                                        db.collection(ACTION_LOG_COLLECTION).add(action_log_doc)
                                    logging.info(f"Logged immediate autonomous archive action for email ID {email_id}")
                                except Exception as e_log:
                                    logging.error(f"Failed to log immediate autonomous action for email ID {email_id}: {e_log}")
                                
                                # Broadcast autonomous action executed event via WebSocket
                                try:
                                    from websocket_events import broadcast_autonomous_action_executed
                                    action_details = f"Immediately auto-archived email '{processed_email_data.get('subject', '')}' classified as '{email_purpose}' with {purpose_confidence:.0%} confidence"
                                    
                                    broadcast_autonomous_action_executed(
                                        user_id=authenticated_user_email,
                                        email_id=email_id,
                                        action='archive',
                                        details=action_details
                                    )
                                    logging.info(f"Broadcasted immediate autonomous action event for email ID {email_id}")
                                except Exception as e_broadcast:
                                    logging.error(f"Failed to broadcast immediate autonomous action for email ID {email_id}: {e_broadcast}")
                                
                                logging.info(f"Successfully auto-archived email ID {email_id} immediately after processing")
                            else:
                                logging.error(f"Failed to immediately auto-archive email ID {email_id}")
                    except Exception as e_auto_action:
                        logging.error(f"Error during immediate autonomous action evaluation for email {email_id}: {e_auto_action}")
                # --- *** END NEW: AUTONOMOUS ACTION EVALUATION *** ---

                # Database Saving
                if add_processed_email(processed_email_data):
                    logging.info(f"  Email {email_id} processed and saved to Firestore.")
                    new_emails_processed_count += 1
                else:
                    logging.error(f"Failed to save email {email_id} to Firestore.")

            except Exception as e:
                logging.error(f"!! Critical error processing email ID {email_id}: {e}", exc_info=True)
                logging.error(f"!! Skipping to next email due to unexpected error.")
                continue # Continue to the next email_id

        logging.info(f"\nFinished processing batch. Processed {new_emails_processed_count} new emails.")
        # --- End Process Emails Loop ---
        
    # --- *** NEW: FINAL ACTION REQUESTS PROCESSING *** ---
    if gmail_service:
        try:
            logging.info("Processing final action requests...")
            process_action_requests(gmail_service)
            logging.info("Final action requests processed successfully.")
        except Exception as e_final:
            logging.error(f"Error during final action requests processing: {e_final}", exc_info=True)
    else:
        logging.warning("Gmail service not available, cannot process final action requests.")
    # --- *** END NEW: FINAL ACTION REQUESTS PROCESSING *** ---

    # --- Report Generation (Log Only) ---
    # (Keep report generation loop as implemented previously)
    logging.info("\n\n--- AI Email Agent Report (Today's High Priority) ---")
    try:
        # Uses database_utils function which uses the shared 'db' client
        todays_high_priority = get_todays_high_priority_emails()
        if todays_high_priority:
            logging.info(f"\nFound {len(todays_high_priority)} CRITICAL/HIGH priority emails processed today:")
            for i, email in enumerate(todays_high_priority, 1):
                # Log essential info for report
                logging.info(f"  {i}. Prio: {email.get('priority')}, Subject: {email.get('subject', '[No Subject]')}, From: {email.get('sender')}")
                # Log summary if available and not an error
                summary_report = email.get('summary') # Get raw summary
                if summary_report and not str(summary_report).startswith("Error:"):
                     logging.info(f"     Summary: {str(summary_report)[:150]}...") # Log truncated summary
                elif summary_report:
                     logging.info(f"     Summary: [Not generated or error: {str(summary_report)[:50]}...]")
                else:
                     logging.info(f"     Summary: [N/A]")

        else:
            logging.info("\nNo new CRITICAL/HIGH priority emails processed today.")
        logging.info("\n--- End of Report ---")
    except Exception as e:
         logging.error(f"Failed to generate report: {e}", exc_info=True)
    # --- End Report Generation ---

    # --- *** NEW: AUTONOMOUS TASKS *** ---
    logging.info("--- Starting Autonomous Tasks ---")
    try:
        if gmail_service:
            run_autonomous_archiving_task(gmail_service, database_utils.db, config)
            run_autonomous_meeting_prep_task(gmail_service, database_utils.db, config)
        else:
            logging.warning("Gmail service not available, cannot run autonomous tasks.")
    except Exception as e_autonomous:
        logging.error(f"Error during autonomous tasks execution: {e_autonomous}", exc_info=True)
    logging.info("--- Autonomous Tasks Complete ---")
    # --- *** END AUTONOMOUS TASKS *** ---

    # --- Update final success message ---
    function_end_time = time.time()
    logging.info(f"Cloud Function execution finished successfully in {function_end_time - function_start_time:.2f} seconds.")
    return "Success", 200

# Example addition to main.py for local run
if __name__ == '__main__':
    print("Running locally to re-authenticate...")
    logging.basicConfig(level=logging.INFO, format=log_format)
    cfg = load_config()
    if cfg:
         try:
             print("Authenticating using modern, unified auth_utils...")
             
             # Use the modern authentication system
             gmail_service, _ = get_authenticated_services()
             
             if gmail_service:
                 print("Authentication successful! Modern auth_utils working correctly.")
             else:
                 print("Authentication failed: get_authenticated_services returned None.")
         except Exception as e:
             print(f"Local auth error: {e}")
    else:
         print("Failed to load config.")