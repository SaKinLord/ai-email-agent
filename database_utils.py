# -*- coding: utf-8 -*-
"""
Created on Thu Apr 10 06:47:01 2025

@author: merto
"""

# -*- coding: utf-8 -*-
"""
Database utilities for the AI Email Agent, using Google Cloud Firestore.
"""

# --- Standard Library Imports ---
import os
import re
import logging
from datetime import datetime, date, timezone # Import timezone

# --- Third-party Imports ---
from google.cloud import firestore # Import Firestore library
from google.api_core import exceptions as google_exceptions # Import exceptions
from google.cloud.firestore_v1.base_query import FieldFilter # Add this import for new query syntax

# --- Constants for Collection Names ---
EMAILS_COLLECTION = "emails"
FEEDBACK_COLLECTION = "feedback"
STATE_COLLECTION = "agent_state"
ACTION_REQUESTS_COLLECTION = "action_requests" # New collection name

# --- Firestore Client Initialization ---
db = None # Initialize as None

try:
    # Attempt to initialize. This might fail if run outside GCP environment without ADC/Key
    db = firestore.Client()
    logging.info("Firestore client initialized successfully in database_utils.")
except Exception as e:
    # Log error but allow script to potentially continue if db is checked later
    logging.error(f"Failed to initialize Firestore client globally in database_utils: {e}", exc_info=True)

# --- Helper Function ---
def _get_sender_key(sender):
    """Extracts the core email address from a sender string."""
    if not isinstance(sender, str):
        return None
    match = re.search(r'<(.+?)>', sender)
    if match:
        return match.group(1).lower()
    # Fallback: attempt to clean and use the whole string if no brackets
    sender_clean = sender.strip().lower()
    # Basic email format check (optional, but helpful)
    if '@' in sender_clean and '.' in sender_clean.split('@')[-1]:
        return sender_clean
    logging.warning(f"Could not extract valid email key from sender: {sender}")
    return None # Return None if extraction fails

# --- Firestore Functions ---

# initialize_database is no longer needed for Firestore

# connect_db is replaced by the global `db` client initialization

def is_email_processed(email_id):
    """Checks if an email document exists in the Firestore 'emails' collection."""
    if not db:
        logging.error("Firestore client not available in is_email_processed.")
        return True # Assume processed if DB fails to prevent loops

    if not email_id:
        logging.warning("is_email_processed called with empty email_id.")
        return False

    try:
        email_ref = db.collection(EMAILS_COLLECTION).document(email_id)
        doc_snapshot = email_ref.get()
        return doc_snapshot.exists
    except google_exceptions.GoogleAPICallError as e:
        logging.error(f"Firestore API error checking email {email_id}: {e}", exc_info=True)
        return True # Err on the side of caution
    except Exception as e:
        logging.error(f"Unexpected error checking if email {email_id} is processed: {e}", exc_info=True)
        return True # Err on the side of caution

def add_processed_email(email_data):
    """Adds a processed email's details as a document to Firestore."""
    if not db:
        logging.error("Firestore client not available in add_processed_email.")
        return False

    email_id = email_data.get('id')
    if not email_id:
        logging.error("Cannot add email to Firestore: Missing 'id'.")
        return False

    try:
        email_ref = db.collection(EMAILS_COLLECTION).document(email_id)

        # Prepare data, converting Python datetime if necessary
        data_to_set = {
            'thread_id': email_data.get('threadId'),
            'sender': email_data.get('sender'),
            'subject': email_data.get('subject'),
            'received_date_str': email_data.get('date'), # Keep original string if needed
            'priority': email_data.get('priority'),
            'summary': email_data.get('summary'),
            'llm_urgency': email_data.get('llm_urgency'),
            'llm_purpose': email_data.get('llm_purpose'),
            'body_text': email_data.get('body_text'),
            # Store processed timestamp as Firestore Timestamp
            'processed_timestamp': firestore.SERVER_TIMESTAMP # Use server time
        }
        # Remove keys with None values to keep documents cleaner (optional)
        data_to_set = {k: v for k, v in data_to_set.items() if v is not None}

        email_ref.set(data_to_set) # Use set() which creates or overwrites
        logging.info(f"Email {email_id} data set in Firestore.")
        return True
    except google_exceptions.GoogleAPICallError as e:
        logging.error(f"Firestore API error adding email {email_id}: {e}", exc_info=True)
        return False
    except Exception as e:
        logging.error(f"Unexpected error adding email {email_id} to Firestore: {e}", exc_info=True)
        return False

def add_feedback(email_id, original_priority, corrected_priority):
    """Logs user feedback as a document in Firestore."""
    if not db:
        logging.error("Firestore client not available in add_feedback.")
        return False

    if not email_id or not corrected_priority:
        logging.error("Cannot add feedback: Missing email_id or corrected_priority.")
        return False

    try:
        # --- Get sender info from the email document for denormalization ---
        sender = None
        sender_key = None
        email_ref = db.collection(EMAILS_COLLECTION).document(email_id)
        email_doc = email_ref.get()
        if email_doc.exists:
            sender = email_doc.get('sender')
            sender_key = _get_sender_key(sender) # Use helper to get consistent key
        else:
            logging.warning(f"Cannot find email document {email_id} when adding feedback. Sender key will be missing.")
        # --- End sender info retrieval ---

        feedback_ref = db.collection(FEEDBACK_COLLECTION).document() # Auto-generate feedback ID

        data_to_set = {
            'email_id': email_id,
            'original_priority': original_priority,
            'corrected_priority': corrected_priority,
            'feedback_timestamp': firestore.SERVER_TIMESTAMP,
            'sender_key': sender_key # Denormalize the key for easier history query
        }
        feedback_ref.set(data_to_set)
        logging.info(f"Feedback logged for email {email_id}: Corrected priority set to {corrected_priority}.")
        return True
    # Note: Firestore set() overwrites, so update logic isn't strictly needed unless
    # you want to prevent multiple feedback docs per email_id using email_id as doc ID.
    # Using auto-generated ID allows multiple feedback entries per email if needed later.
    except google_exceptions.GoogleAPICallError as e:
        logging.error(f"Firestore API error adding feedback for {email_id}: {e}", exc_info=True)
        return False
    except Exception as e:
        logging.error(f"Unexpected error adding feedback for {email_id}: {e}", exc_info=True)
        return False

def check_existing_feedback(email_id):
    """Checks if feedback exists for a given email_id in Firestore."""
    if not db:
        logging.error("Firestore client not available in check_existing_feedback.")
        return None

    if not email_id:
        logging.warning("check_existing_feedback called with empty email_id.")
        return None

    try:
        feedback_query = db.collection(FEEDBACK_COLLECTION).where(
            filter=FieldFilter('email_id', '==', email_id)
        ).limit(1).stream()
        for doc in feedback_query: # Check if the stream yields any document
            return doc.get('corrected_priority')
        return None # No documents found
    except google_exceptions.GoogleAPICallError as e:
        logging.error(f"Firestore API error checking feedback for {email_id}: {e}", exc_info=True)
        return None
    except Exception as e:
        logging.error(f"Unexpected error checking feedback for {email_id}: {e}", exc_info=True)
        return None

def get_feedback_count():
    """Counts the total number of documents in the feedback collection."""
    if not db:
        logging.error("Firestore client not available in get_feedback_count.")
        return 0

    try:
        # Firestore doesn't have a direct COUNT(*) aggregate.
        # We need to stream documents and count, which can be inefficient for large collections.
        # For small numbers of feedback (< few thousand), this is acceptable.
        # For very large scale, maintain a counter document (more complex).
        feedback_query = db.collection(FEEDBACK_COLLECTION).stream()
        count = sum(1 for _ in feedback_query) # Efficient way to count items in an iterator
        return count
    except google_exceptions.GoogleAPICallError as e:
        logging.error(f"Firestore API error counting feedback: {e}", exc_info=True)
        return 0
    except Exception as e:
        logging.error(f"Unexpected error counting feedback: {e}", exc_info=True)
        return 0

def get_feedback_history():
    """
    Retrieves the latest corrected priority for each sender_key based on feedback.
    Uses the denormalized sender_key field in the feedback documents.
    Returns a dictionary: {'sender_key@domain.com': 'CorrectedPriority'}
    """
    feedback_map = {}
    if not db:
        logging.error("Firestore client not available in get_feedback_history.")
        return feedback_map

    try:
        # Query all feedback, ordered by timestamp descending
        feedback_query = db.collection(FEEDBACK_COLLECTION).order_by(
            'feedback_timestamp', direction=firestore.Query.DESCENDING
        ).stream()

        processed_senders = set()
        for doc in feedback_query:
            data = doc.to_dict()
            sender_key = data.get('sender_key')
            corrected_priority = data.get('corrected_priority')

            # Only store the first (latest) feedback encountered for this sender
            if sender_key and corrected_priority and sender_key not in processed_senders:
                feedback_map[sender_key] = corrected_priority
                processed_senders.add(sender_key)

        logging.info(f"Built feedback history map for {len(feedback_map)} senders.")
        return feedback_map

    except google_exceptions.GoogleAPICallError as e:
        logging.error(f"Firestore API error retrieving feedback history: {e}", exc_info=True)
        return {}
    except Exception as e:
        logging.error(f"Unexpected error retrieving feedback history: {e}", exc_info=True)
        return {}

def get_todays_high_priority_emails(db_client=None): # db_client param is not used, uses global db
    emails = []
    if not db: # Checks global db
        logging.error("Firestore client not available in get_todays_high_priority_emails.")
        return emails # Returns empty list

    # Define constants locally
    PRIORITY_CRITICAL = "CRITICAL"
    PRIORITY_HIGH = "HIGH"

    try:
        today_utc = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        query = db.collection(EMAILS_COLLECTION)\
                  .where(filter=FieldFilter('processed_timestamp', '>=', today_utc))\
                  .where(filter=FieldFilter('priority', 'in', [PRIORITY_CRITICAL, PRIORITY_HIGH]))\
                  .order_by('processed_timestamp', direction=firestore.Query.DESCENDING)

        results = query.stream()
        for doc in results:
            email_data = doc.to_dict()
            email_data['email_id'] = doc.id 
            emails.append(email_data)

    except google_exceptions.FailedPrecondition as e:
         # This specific exception often indicates a missing index
         logging.error(f"Firestore query failed, likely requires an index: {e}", exc_info=True)
         logging.error("Please check the error message for a link to create the necessary composite index in the Google Cloud Console.")
    except google_exceptions.GoogleAPICallError as e:
        logging.error(f"Firestore API error retrieving today's high priority emails: {e}", exc_info=True)
    except Exception as e:
        logging.error(f"Unexpected error retrieving today's high priority emails: {e}", exc_info=True)

    return emails # Return list of dictionaries

# --- Functions for Retraining State ---

def read_retrain_state_from_firestore():
    """Reads the last feedback count from Firestore."""
    if not db: return {"last_feedback_count": 0} # Default if DB fails
    try:
        doc_ref = db.collection(STATE_COLLECTION).document("retraining_state")
        doc = doc_ref.get()
        if doc.exists:
            state = doc.to_dict()
            if "last_feedback_count" in state and isinstance(state["last_feedback_count"], int):
                 logging.info(f"Read last feedback count ({state['last_feedback_count']}) from Firestore state.")
                 return state
            else:
                 logging.warning("Invalid format in Firestore retraining state document. Resetting.")
                 return {"last_feedback_count": 0}
        else:
            logging.info("Retraining state document not found in Firestore. Assuming initial state.")
            return {"last_feedback_count": 0}
    except Exception as e:
        logging.error(f"Error reading retraining state from Firestore: {e}", exc_info=True)
        return {"last_feedback_count": 0}

def write_retrain_state_to_firestore(count):
    """Writes the current feedback count to Firestore."""
    if not db: return False
    try:
        doc_ref = db.collection(STATE_COLLECTION).document("retraining_state")
        state = {"last_feedback_count": count, "last_updated": firestore.SERVER_TIMESTAMP}
        doc_ref.set(state) # set() creates or overwrites
        logging.info(f"Updated retraining state in Firestore with count: {count}")
        return True
    except Exception as e:
        logging.error(f"Error writing retraining state to Firestore: {e}", exc_info=True)
        return False

# --- Functions for User Preferences ---

def read_user_preferences():
    """Reads user preferences from the 'retraining_state' document."""
    prefs = {"user_important_senders": []} # Default empty list
    if not db:
        logging.error("Firestore client not available in read_user_preferences.")
        return prefs

    try:
        doc_ref = db.collection(STATE_COLLECTION).document("retraining_state")
        doc = doc_ref.get()
        if doc.exists:
            state_data = doc.to_dict()
            # Check if the field exists and is a list
            if "user_important_senders" in state_data and isinstance(state_data["user_important_senders"], list):
                prefs["user_important_senders"] = state_data["user_important_senders"]
                logging.info(f"Read {len(prefs['user_important_senders'])} user-defined important senders from Firestore state.")
            else:
                logging.info("Field 'user_important_senders' not found or not a list in Firestore state. Using default empty list.")
        else:
            logging.info("Retraining state document not found in Firestore. Using default empty list for important senders.")
        return prefs
    except Exception as e:
        logging.error(f"Error reading user preferences from Firestore: {e}", exc_info=True)
        return {"user_important_senders": []} # Return default on error

def write_user_preferences(preferences_dict):
    """Writes user preferences to the 'retraining_state' document.
       Uses merge=True to avoid overwriting other state fields.
    """
    if not db:
        logging.error("Firestore client not available in write_user_preferences.")
        return False
    if not isinstance(preferences_dict, dict):
         logging.error("Invalid preferences_dict provided to write_user_preferences.")
         return False

    try:
        doc_ref = db.collection(STATE_COLLECTION).document("retraining_state")
        # Add/update a timestamp for when preferences were last saved
        preferences_dict['preferences_last_updated'] = firestore.SERVER_TIMESTAMP
        doc_ref.set(preferences_dict, merge=True) # Use merge=True!
        logging.info(f"Updated user preferences in Firestore state: {preferences_dict.keys()}")
        return True
    except Exception as e:
        logging.error(f"Error writing user preferences to Firestore: {e}", exc_info=True)
        return False

# --- NEW Function for Action Requests ---
def request_email_action(email_id, action_type, params=None): # Added params=None
    """Creates a document in the action_requests collection."""
    if not db:
        logging.error("Firestore client not available in request_email_action.")
        return False
    # Allow email_id to be None for actions not tied to a specific incoming email (like composing new)
    # if not email_id or not action_type:
    if not action_type: # Only action_type is strictly required now
        logging.error("Missing action_type for request_email_action.")
        return False

    try:
        action_ref = db.collection(ACTION_REQUESTS_COLLECTION).document() # Auto-generate ID
        data_to_set = {
            'email_id': email_id, # Can be None
            'action': action_type,
            'status': 'pending',
            'requested_at': firestore.SERVER_TIMESTAMP,
            'processed_at': None,
            'result_message': None,
            'params': params if params else {} # Store the parameters dictionary
        }
        action_ref.set(data_to_set)
        logging.info(f"Action request '{action_type}' submitted (Email ID: {email_id}).")
        return True
    except Exception as e:
        logging.error(f"Error submitting action request (Email ID: {email_id}, Action: {action_type}): {e}", exc_info=True)
        return False

def update_action_request_status(doc_id, status, message=""):
    """Updates the status and result message of an action request."""
    if not db:
        logging.error("Firestore client not available in update_action_request_status.")
        return False
    try:
        action_ref = db.collection(ACTION_REQUESTS_COLLECTION).document(doc_id)
        action_ref.update({
            'status': status,
            'result_message': message,
            'processed_at': firestore.SERVER_TIMESTAMP
        })
        logging.info(f"Updated status of action request {doc_id} to '{status}'.")
        return True
    except Exception as e:
        logging.error(f"Error updating status for action request {doc_id}: {e}", exc_info=True)
        return False
# --- End Action Request Functions ---