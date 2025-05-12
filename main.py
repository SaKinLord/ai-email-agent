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
from datetime import datetime, timezone
import tempfile # Added for GCF model loading
import functions_framework

# --- Third-party Imports ---
import pandas as pd
import joblib
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
    PRIORITY_CRITICAL, PRIORITY_HIGH # Keep constants if needed elsewhere
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
        query = database_utils.db.collection(ACTION_REQUESTS_COLLECTION)\
                  .where('status', '==', 'pending')\
                  .limit(10)
        results = query.stream()

        for doc in results:
            request_id = doc.id
            request_data = doc.to_dict()
            email_id = request_data.get('email_id') # Original email ID (might be None)
            action = request_data.get('action')
            params = request_data.get('params', {}) # Get the params dictionary
            logging.info(f"Processing action '{action}' (Request ID: {request_id}, Orig Email ID: {email_id})")

            # Allow actions without email_id like 'send_draft' if params are sufficient
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
                
                else:
                    logging.warning(f"Unsupported action '{action}' requested (Request ID: {request_id}).")
                    error_message = f"Unsupported action type: {action}"

            except HttpError as error:
                logging.error(f"HttpError performing action '{action}' (Request ID: {request_id}): {error}", exc_info=True)
                error_message = f"API Error: {error.resp.status} - {error.content.decode()}"
            except Exception as e:
                logging.error(f"Unexpected error performing action '{action}' (Request ID: {request_id}): {e}", exc_info=True)
                error_message = f"Unexpected Error: {type(e).__name__}"

            # Update status in Firestore
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