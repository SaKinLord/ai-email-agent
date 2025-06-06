# -*- coding: utf-8 -*-
"""
Created on Fri Apr 18 11:07:10 2025

@author: merto
"""

# main.py

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

# --- Third-party Imports ---
import pandas as pd
import joblib
from google.cloud.firestore_v1.base_query import FieldFilter
from googleapiclient.errors import HttpError # Import HttpError
from google.cloud import firestore
from google.cloud import storage
from google.cloud import secretmanager
import anthropic
from google.api_core import exceptions as google_exceptions

# --- Local Imports ---
import database_utils # Import the module directly
from agent_logic import (
    load_config, authenticate_gmail, get_unread_email_ids,
    get_email_details, parse_email_content,
    process_email_with_memory,
    PRIORITY_CRITICAL, PRIORITY_HIGH, 
    prepare_email_batch_overview, 
    list_sent_emails,             
    check_thread_for_reply,       
    _extract_email_address,
    analyze_email_with_context        
)

# Import database functions needed here
from database_utils import (
    is_email_processed, add_processed_email,
    get_todays_high_priority_emails, add_feedback,
    get_feedback_history, check_existing_feedback,
    get_feedback_count, write_retrain_state_to_firestore,
    read_user_preferences,
    request_email_action,
    update_action_request_status # Added Firestore state write
)
ACTION_REQUESTS_COLLECTION = "action_requests" # Define constant locally
from ml_utils import (
    build_and_train_pipeline,
    predict_priority,
    extract_domain # Import helper needed for data prep
)

from agent_memory import AgentMemory
from email.mime.text import MIMEText

# --- Logging Setup ---
log_format = '%(asctime)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s'
logging.basicConfig(level=logging.INFO, format=log_format, stream=sys.stdout, force=True)

# --- Firestore Collection Names ---
EMAILS_COLLECTION = "emails"
FEEDBACK_COLLECTION = "feedback"
STATE_COLLECTION = "agent_state"

# --- Global variables for Caching Clients/Config (initialized in handler) ---
db = None
storage_client = None
secret_client = None
config = None
llm_client_gcf = None

# --- GCS Bucket/Object Names (Get from Env Vars) ---
GCS_BUCKET_NAME = os.environ.get('GCS_BUCKET_NAME') # Bucket for token, state
TOKEN_GCS_PATH = os.environ.get('TOKEN_GCS_PATH', 'gmail_token.json')
STATE_GCS_PATH = os.environ.get('STATE_GCS_PATH', 'retrain_state.json')
ANTHROPIC_SECRET_NAME = os.environ.get('ANTHROPIC_SECRET_NAME')
# --- NEW Env Vars for ML Models ---
MODEL_GCS_BUCKET = os.environ.get('MODEL_GCS_BUCKET') # Separate or same bucket for models
MODEL_GCS_PATH_PREFIX = os.environ.get('MODEL_GCS_PATH_PREFIX', 'ml_models/') # e.g., 'ml_models/'

# --- NEW: Constants for Autonomous Tasks ---
DAILY_SUMMARY_ACTION_TYPE = "send_daily_summary_email"
AUTO_ARCHIVE_CHECK_INTERVAL_MINUTES = 60
DAILY_SUMMARY_CHECK_INTERVAL_MINUTES = 60
FOLLOW_UP_CHECK_INTERVAL_MINUTES = 60
RE_EVAL_UNKNOWN_INTERVAL_MINUTES = 1440 # Once a day (24 * 60)

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
    # Uses the general GCS bucket defined by GCS_BUCKET_NAME
    if not GCS_BUCKET_NAME:
        logging.error("GCS_BUCKET_NAME not set, cannot read retrain state.")
        return {'last_feedback_count': 0, 'last_updated_utc': None} # Add default for last_updated_utc
    state = read_json_from_gcs(GCS_BUCKET_NAME, STATE_GCS_PATH)
    # Default to 0 if file is missing (None) or key is missing
    if not state: # Handles if file doesn't exist or read_json_from_gcs returns None
        logging.info(f"Retrain state file not found or empty at gs://{GCS_BUCKET_NAME}/{STATE_GCS_PATH}. Defaulting state.")
        return {'last_feedback_count': 0, 'last_updated_utc': None}
    if 'last_feedback_count' not in state: # Handle if key is missing in existing file
        logging.warning(f"Key 'last_feedback_count' missing in retrain state file. Defaulting count to 0.")
        state['last_feedback_count'] = 0
    if 'last_updated_utc' not in state: # Add default for new key
        state['last_updated_utc'] = None
    logging.info(f"Read GCS retrain state: {state}")
    return state

def write_retrain_state_to_gcs(count): # 'count' here is the new total feedback count
    # Uses the general GCS bucket defined by GCS_BUCKET_NAME
    if not GCS_BUCKET_NAME:
        logging.error("GCS_BUCKET_NAME not set, cannot write retrain state.")
        return False
    state = {
        'last_feedback_count': count,
        'last_updated_utc': datetime.now(timezone.utc).isoformat() # ISO format is good for timestamps
    }
    return write_json_to_gcs(GCS_BUCKET_NAME, STATE_GCS_PATH, state)


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

def get_or_create_label_ids(gmail_service, label_names_to_ensure):
    """
    Ensures labels exist in Gmail, creates them if not.
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
        logging.error(f"Could not list existing Gmail labels: {e}", exc_info=True)
        return [] # Return empty on error, so we don't try to apply non-existent labels

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
        q_promo = base_query.where(filter=FieldFilter("llm_purpose", "==", "Promotion")) \
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
                            user_profile_gmail = gmail_service.users().getProfile(userId='me').execute()
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
def process_action_requests(gmail_service):
    """Queries Firestore for pending actions and attempts to execute them."""
    if not database_utils.db:
        logging.error("Firestore client not available, cannot process action requests.")
        return 0
    if not gmail_service:
        logging.error("Gmail service not available, cannot process action requests.")
        return 0
    processed_count = 0
    logging.info("--- Checking for pending action requests ---")
    try:
        query = (database_utils.db.collection(ACTION_REQUESTS_COLLECTION)
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
                        modify_body = {'removeLabelIds': ['INBOX']}
                        gmail_service.users().messages().modify(userId='me', id=email_id, body=modify_body).execute()
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
                        gmail_service.users().messages().send(userId='me', body=send_body).execute()
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
                            modify_body = {'addLabelIds': actual_label_ids_to_apply}
                            gmail_service.users().messages().modify(userId='me', id=email_id, body=modify_body).execute()
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
    # +++ VERY FIRST LOG LINE +++
    logging.critical("--- process_emails_gcf function STARTING EXECUTION (Revision XYZ) ---")
    # +++ END VERY FIRST LOG LINE +++
    global db, storage_client, secret_client, config, llm_client_gcf
    function_start_time = time.time()
    logging.info("Cloud Function triggered.")

    # --- Initialize Clients and Config (Cached across warm instances) ---
    try:
        if config is None:
            config = load_config("config.json")
            if not config: raise ValueError("Failed to load configuration.")
            logging.info("Configuration loaded inside handler.")
        if db is None:
            db = firestore.Client()
            database_utils.db = db # Pass the initialized client to the utils module
            logging.info("Firestore client initialized inside handler.")
        # --- ADD MEMORY INITIALIZATION ---
        try:
            memory_instance = AgentMemory(db_client=db, user_id="default_user") # Assuming default_user for background task
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
            logging.info(f"Anthropic client initialized inside handler for model: {config['llm']['model_name']}")
    except Exception as e:
        logging.critical(f"Failed during initialization or config loading: {e}", exc_info=True)
        return f"Error: Initialization/Config failed: {e}", 500

    # --- Check Required Environment Variables ---
    if not GCS_BUCKET_NAME: return "Error: GCS_BUCKET_NAME env var missing", 500
    if not ANTHROPIC_SECRET_NAME: return "Error: ANTHROPIC_SECRET_NAME env var missing", 500
    # MODEL env vars checked later during loading/saving

    # --- Get ML Filenames from Config ---
    # These are the BASE filenames used for constructing GCS paths and local temp paths
    local_pipeline_filename = config['ml']['pipeline_filename']
    local_label_encoder_filename = config['ml']['label_encoder_filename']

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
            training_df = fetch_and_prepare_training_data(db)

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
    logging.info("Authenticating with Gmail...")
    gmail_service = None
    try:
        if not config: raise ValueError("Config not loaded before Gmail Auth.")
        if not GCS_BUCKET_NAME or not TOKEN_GCS_PATH:
            raise ValueError("GCS Bucket/Path env vars for token missing.")

        # Pass the global storage_client instance to avoid re-initialization
        gmail_service = authenticate_gmail(
            token_gcs_bucket=GCS_BUCKET_NAME,
            token_gcs_path=TOKEN_GCS_PATH,
            credentials_path=config['gmail']['credentials_path'],
            scopes=config['gmail']['scopes'],
            storage_client_instance=storage_client # Pass existing client
        )
        if not gmail_service:
            raise RuntimeError("Gmail authentication failed.")
        logging.info("Gmail authentication successful.")
        
        # --- *** PROCESS ACTION REQUESTS (Before processing new emails) *** ---
        process_action_requests(gmail_service)
        # --- *** END PROCESS ACTION REQUESTS *** ---
        
        # --- *** NEW: EXECUTE AUTONOMOUS TASKS *** ---
        if memory_instance and gmail_service and llm_client_gcf and config and db:
            try:
                logging.info("Executing autonomous tasks...")
                execute_autonomous_tasks(
                    user_id="default_user", 
                    memory_instance=memory_instance,
                    gmail_service=gmail_service,
                    llm_client=llm_client_gcf,
                    config=config,
                    db_client=db
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

                # Log results
                logging.info(f"  Processing Result for {email_id}: Priority='{processed_email_data.get('priority')}', Summary='{str(processed_email_data.get('summary'))[:100]}...', LLM Purpose='{processed_email_data.get('llm_purpose')}'")

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
         # Initialize GCS client locally (ensure ADC or key file is set up)
         try:
             gcs_client = storage.Client()
             print("Authenticating...")
             # Use GCS bucket/path from environment or config for consistency
             bucket = os.environ.get('GCS_BUCKET_NAME', 'ai-email-agent-state') # Replace if needed
             token_path_gcs = os.environ.get('TOKEN_GCS_PATH', 'gmail_token.json')
             service = authenticate_gmail(
                 token_gcs_bucket=bucket,
                 token_gcs_path=token_path_gcs,
                 credentials_path=cfg['gmail']['credentials_path'],
                 scopes=cfg['gmail']['scopes'],
                 storage_client_instance=gcs_client
             )
             if service:
                 print("Authentication successful! New token saved to GCS.")
             else:
                 print("Authentication failed.")
         except Exception as e:
             print(f"Local auth error: {e}")
    else:
         print("Failed to load config.")