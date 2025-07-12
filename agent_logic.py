# -*- coding: utf-8 -*-
"""
Created on Thu Apr 10 06:47:01 2025

@author: merto

Combined and updated agent_logic.py incorporating memory system enhancements.
Now includes explainable reasoning system for transparent decision-making.
"""

# agent_logic.py

# --- Standard Library Imports ---
import os
import base64
import email
import json
import re
import time
import sys
import logging
import binascii
import database_utils
from datetime import datetime
from collections import Counter # Added for prepare_email_batch_overview
from datetime import datetime, timedelta, timezone
# --- Third-party Imports ---
from googleapiclient.discovery import build as build_service
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.auth.exceptions import RefreshError
from bs4 import BeautifulSoup
import anthropic
from google.cloud import storage # Needed for token handling
from google.cloud import firestore # Needed for agenda synthesis queries
from google.cloud.firestore_v1.base_query import FieldFilter # Modern Firestore query syntax
from agent_memory import AgentMemory # Import the new memory system (already present in 'original')
from email.mime.text import MIMEText
from reasoning_engine import ExplainableReasoningEngine, ClassificationResult  # Import the new reasoning system

# --- Constants ---
# (Defined globally here as they are used within these functions)
PRIORITY_CRITICAL = "CRITICAL"
PRIORITY_HIGH = "HIGH"
PRIORITY_MEDIUM = "MEDIUM"
PRIORITY_LOW = "LOW"
MAX_RETRIES = 3
RETRY_DELAY_SECONDS = 5
# Firestore constants might be needed if functions query directly, but mostly passed now
# EMAILS_COLLECTION = "emails"
# FEEDBACK_COLLECTION = "feedback"
# STATE_COLLECTION = "agent_state"
# --- Constants for Calendar ---
CALENDAR_SCOPES = ['https://www.googleapis.com/auth/calendar.events']
CALENDAR_TOKEN_GCS_PATH_ENV = 'CALENDAR_TOKEN_GCS_PATH' # New Env Var Name
DEFAULT_CALENDAR_TOKEN_FILENAME = 'calendar_token.json'

# --- Agent Action Types Constant (already present in 'original') ---
AGENT_ACTION_TYPES = {
    "SUMMARIZE": "summarize",
    "ARCHIVE": "archive",
    "REPLY": "reply",
    "FOLLOW_UP": "follow_up",
    "CATEGORIZE": "categorize",
    "ANALYZE": "analyze"
}

# ML Filenames are loaded from config in main.py and passed if needed,
# but loading happens in main.py now.

# --- Function Definitions ---

def load_config(filepath="config.json"):
    """
    Loads configuration from a JSON file and validates required keys for the MODERN app structure.
    """
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            config_data = json.load(f)
        logging.info(f"Configuration loaded successfully from {filepath}")
        
        
        required_keys = [
            'llm_settings', 
            'autonomous_tasks', 
            'integrations', 
            'reasoning', 
            'agenda_synthesis'
        ]
        

        missing_keys = [key for key in required_keys if key not in config_data]
        if missing_keys:
            logging.error(f"Configuration file '{filepath}' is missing required modern top-level keys: {missing_keys}")
            return None # Return None instead of exiting for library use
        
        logging.info("Modern configuration keys validated successfully.")
        return config_data
        
    except FileNotFoundError:
        logging.error(f"Configuration file not found at {filepath}")
        return None
    except json.JSONDecodeError as e:
        logging.error(f"Could not parse configuration file {filepath}. Invalid JSON: {e}")
        return None
    except Exception as e:
        logging.error(f"An unexpected error occurred loading configuration: {e}", exc_info=True)
        return None

# --- NEW CENTRALIZED AUTHENTICATION FUNCTIONS ---
def authenticate_gmail(*args, **kwargs):
    """
    Get authenticated Gmail service using environment-appropriate auth system.
    Uses auth_utils.py in Streamlit environment, falls back to legacy GCS auth in Cloud Functions.
    """
    try:
        # Try Streamlit-based authentication first
        from auth_utils import get_authenticated_services
        gmail_service, _ = get_authenticated_services()
        logging.info("Using Streamlit-based authentication")
        return gmail_service
    except Exception as e:
        logging.warning(f"Streamlit auth not available: {e}")
        
        # Fall back to legacy GCS authentication for Cloud Functions
        if args or kwargs:
            logging.info("Using legacy GCS authentication for Cloud Function environment")
            return authenticate_gmail_legacy(*args, **kwargs)
        else:
            logging.error("No authentication parameters provided for legacy authentication")
            return None

def get_calendar_service(*args, **kwargs):
    """
    Get authenticated Calendar service using environment-appropriate auth system.
    Uses auth_utils.py in Streamlit environment, falls back to legacy GCS auth in Cloud Functions.
    """
    try:
        # Try Streamlit-based authentication first
        from auth_utils import get_authenticated_services
        _, calendar_service = get_authenticated_services()
        logging.info("Using Streamlit-based calendar authentication")
        return calendar_service
    except Exception as e:
        logging.warning(f"Streamlit calendar auth not available: {e}")
        
        # Fall back to legacy GCS authentication for Cloud Functions
        if args or kwargs:
            logging.info("Using legacy GCS calendar authentication for Cloud Function environment")
            return get_calendar_service_legacy(*args, **kwargs)
        else:
            logging.error("No calendar authentication parameters provided for legacy authentication")
            return None

# --- LEGACY AUTHENTICATION FUNCTIONS (kept for compatibility) ---
def authenticate_gmail_legacy(token_gcs_bucket, token_gcs_path, credentials_path, scopes, storage_client_instance=None):
    """Handles Gmail Auth, reading/writing token from GCS, includes local interactive flow."""
    creds = None
    token_blob = None
    service = None # Initialize service to None

    # Use passed GCS client or create a new one
    storage_client = storage_client_instance or storage.Client()
    if not storage_client:
         logging.error("Failed to get GCS client instance.")
         return None

    # Check if credentials file exists
    if not os.path.exists(credentials_path):
        logging.error(f"Gmail credentials file not found at: {credentials_path}")
        return None

    # Get GCS blob reference
    try:
        bucket = storage_client.bucket(token_gcs_bucket)
        token_blob = bucket.blob(token_gcs_path)
    except Exception as e:
        logging.error(f"Failed to get GCS blob reference gs://{token_gcs_bucket}/{token_gcs_path}: {e}", exc_info=True)
        return None

    # --- Try block for loading/refreshing/generating token ---
    try:
        # 1. Try loading token from GCS
        if token_blob.exists(storage_client):
            logging.info(f"Attempting to load token from GCS: gs://{token_gcs_bucket}/{token_gcs_path}")
            try:
                token_json = token_blob.download_as_string(client=storage_client)
                creds_data = json.loads(token_json)
                required_keys = ['token', 'refresh_token', 'client_id', 'client_secret']
                if all(key in creds_data for key in required_keys):
                     creds = Credentials.from_authorized_user_info(creds_data, scopes)
                     logging.info("Credentials loaded successfully from GCS token.")
                else:
                     logging.warning(f"Token file from GCS is missing required keys.")
                     creds = None
            except Exception as e:
                logging.warning(f"Could not load or parse token from GCS: {e}. Will attempt re-authentication.")
                creds = None
        else:
             logging.info(f"Token file not found in GCS. Need to authenticate.")
             creds = None # Explicitly set creds to None if file not found

        # 2. Validate or Refresh/Re-authenticate
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                # --- Refresh Logic ---
                logging.info("Refreshing expired Gmail token...")
                try:
                    authed_session = Request()
                    creds.refresh(authed_session)
                    logging.info("Token refreshed successfully.")
                    # Save refreshed token back to GCS
                    try:
                        creds_json_to_save = creds.to_json()
                        token_blob.upload_from_string(creds_json_to_save, content_type='application/json', client=storage_client)
                        logging.info(f"Refreshed credentials saved back to GCS.")
                    except Exception as e_save:
                        logging.error(f"Could not save refreshed token file back to GCS: {e_save}", exc_info=True)
                        # Continue, but token might not persist for next run
                except RefreshError as e:
                    logging.error(f"Gmail authentication token has expired or been revoked: {e}")
                    # Delete the invalid token from GCS to force re-authentication
                    try:
                        if token_blob.exists(storage_client):
                            token_blob.delete(client=storage_client)
                            logging.info("Invalid Gmail token deleted from GCS - re-authentication required")
                    except Exception as delete_error:
                        logging.warning(f"Could not delete invalid Gmail token from GCS: {delete_error}")
                    return None # Fail in non-interactive or local if refresh fails
                except Exception as e:
                    logging.error(f"An unexpected error occurred during Gmail token refresh: {e}", exc_info=True)
                    return None # Fail
            else:
                # --- Generate NEW Token via Interactive Flow (ONLY if creds is None initially) ---
                # This block should ONLY run when executed locally via main.py's __main__
                # because the GCF environment should error out above if refresh fails.
                logging.info("No valid credentials found, attempting interactive authentication flow...")
                try:
                    flow = InstalledAppFlow.from_client_secrets_file(credentials_path, scopes)
                    # This *should* open a browser window when run locally
                    creds = flow.run_local_server(port=0)
                except FileNotFoundError:
                     logging.error(f"Credentials file not found at {credentials_path} during flow.")
                     return None
                except Exception as e:
                     # Catch potential errors if browser cannot be opened etc.
                     logging.error(f"Interactive authentication flow failed: {e}", exc_info=True)
                     logging.error("Ensure you are running this script in an environment where a browser can be opened.")
                     return None

                # --- If flow succeeds, save the NEW credentials to GCS ---
                if creds:
                    try:
                        creds_json_to_save = creds.to_json()
                        token_blob.upload_from_string(creds_json_to_save, content_type='application/json', client=storage_client)
                        logging.info(f"NEW credentials saved to GCS: gs://{token_gcs_bucket}/{token_gcs_path}")
                    except Exception as e_save:
                        logging.error(f"Could not save NEW token file to GCS: {e_save}", exc_info=True)
                        logging.warning("Proceeding with obtained credentials, but failed to save token to GCS.")
                else:
                     logging.error("Interactive authentication flow seemed to succeed but resulted in no credentials.")
                     return None

        # 3. Build the service if creds are valid
        if creds and creds.valid:
            try:
                service = build('gmail', 'v1', credentials=creds)
                logging.info("Gmail API service created successfully.")
                return service
            except HttpError as error:
                logging.error(f'An error occurred building the Gmail service: {error}')
                return None
            except Exception as e:
                logging.error(f'An unexpected error occurred building the service: {e}', exc_info=True)
                return None
        else:
            # This case should ideally be caught earlier, but handle defensively
            logging.error("Reached end of authentication logic without valid credentials.")
            return None

    # --- Except block for the main try ---
    # This catches errors during the initial GCS check or other unexpected issues
    except Exception as e:
        logging.error(f"Unexpected error during authentication process: {e}", exc_info=True)
        return None
    

# --- get_unread_email_ids (No changes needed from previous version) ---
def get_unread_email_ids(service, user_id='me', max_results=20, label_ids=None):
    """Lists the user's message IDs, with retries for transient errors."""
    if label_ids is None: label_ids = ['INBOX', 'UNREAD'] # Default if not passed
    # ... (rest of the function with retry logic as before) ...
    for attempt in range(MAX_RETRIES):
        try:
            response = service.users().messages().list(userId=user_id,
                                                      labelIds=label_ids,
                                                      maxResults=max_results).execute()
            messages = []
            if 'messages' in response:
                messages.extend(response['messages'])
            logging.info(f"Found {len(messages)} emails matching labels {label_ids}.")
            return [msg['id'] for msg in messages] # Success, return IDs
        # ... (Error handling with retries as before) ...
        except HttpError as error:
            logging.error(f'An HTTP error occurred fetching email list: {error}')
            if hasattr(error, 'resp') and error.resp.status >= 500 and attempt < MAX_RETRIES - 1:
                logging.warning(f"Attempt {attempt + 1}/{MAX_RETRIES} failed. Retrying in {RETRY_DELAY_SECONDS}s...")
                time.sleep(RETRY_DELAY_SECONDS)
                continue
            else:
                logging.error("Non-retryable HTTP error or max retries reached.")
                return []
        except RefreshError as e:
             logging.error(f"Token refresh required during API call: {e}. Authentication might be needed.")
             return []
        except Exception as e:
            logging.error(f'An unexpected error occurred fetching email list: {e}', exc_info=True)
            return []
    logging.error("Max retries reached for fetching email list.")
    return []


# --- get_email_details (No changes needed from previous version) ---
def get_email_details(service, message_id, user_id='me'):
    """Gets the full details of a specific email message, with retries."""
    # ... (function with retry logic as before) ...
    for attempt in range(MAX_RETRIES):
        try:
            message = service.users().messages().get(userId=user_id, id=message_id, format='full').execute()
            return message # Success
        # ... (Error handling with retries as before) ...
        except HttpError as error:
            logging.error(f'An HTTP error occurred fetching email {message_id}: {error}')
            if hasattr(error, 'resp') and error.resp.status >= 500 and attempt < MAX_RETRIES - 1:
                logging.warning(f"Attempt {attempt + 1}/{MAX_RETRIES} failed. Retrying in {RETRY_DELAY_SECONDS}s...")
                time.sleep(RETRY_DELAY_SECONDS)
                continue
            else:
                logging.error(f"Non-retryable HTTP error or max retries reached for email {message_id}.")
                return None
        except RefreshError as e:
             logging.error(f"Token refresh required fetching email {message_id}: {e}. Authentication might be needed.")
             return None
        except Exception as e:
            logging.error(f'An unexpected error occurred fetching email {message_id}: {e}', exc_info=True)
            return None
    logging.error(f"Max retries reached fetching email {message_id}.")
    return None


# --- parse_email_content (No changes needed from previous version) ---
def parse_email_content(message):
    """Parses the email message object, handling potential decoding errors."""
    # ... (function logic as before, including decode_payload, process_part, HTML fallback) ...
    if not message: return None
    payload = message.get('payload', {})
    headers = payload.get('headers', [])
    parts = payload.get('parts', [])
    
    # Extract labelIds for status determination
    label_ids = message.get('labelIds', [])
    
    email_data = {
        'id': message.get('id'), 'threadId': message.get('threadId'),
        'snippet': message.get('snippet'), 'subject': '', 'sender': '',
        'date': '', 'body_text': '', 'body_html': '',
        # Add missing frontend fields
        'labels': label_ids,
        'isRead': 'UNREAD' not in label_ids,
        'isStarred': 'STARRED' in label_ids,
        'isArchived': 'INBOX' not in label_ids,
    }
    for header in headers:
        name = header.get('name', '').lower()
        if name == 'subject': email_data['subject'] = header.get('value', '')
        elif name == 'from': email_data['sender'] = header.get('value', '')
        elif name == 'date': email_data['date'] = header.get('value', '')

    def decode_payload(data):
        if not data: return ""
        try:
            decoded_bytes = base64.urlsafe_b64decode(data)
            try: return decoded_bytes.decode('utf-8')
            except UnicodeDecodeError:
                try: return decoded_bytes.decode('latin-1')
                except UnicodeDecodeError:
                    logging.warning(f"Could not decode body part using utf-8 or latin-1 for email {email_data.get('id')}. Replacing errors.", exc_info=False)
                    return decoded_bytes.decode('utf-8', errors='replace')
        except (binascii.Error, TypeError) as e:
            logging.error(f"Base64 decoding error for email {email_data.get('id')}: {e}")
            return ""

    def process_part(part):
        mime_type = part.get('mimeType', '')
        body = part.get('body', {})
        data = body.get('data')
        text = decode_payload(data)
        if mime_type == 'text/plain': email_data['body_text'] += text + "\n"
        elif mime_type == 'text/html': email_data['body_html'] += text + "\n"

    if parts:
        for part in parts:
            if part.get('parts'):
                for sub_part in part.get('parts'): process_part(sub_part)
            else: process_part(part)
    else: process_part(payload)

    if not email_data['body_text'].strip() and email_data['body_html'].strip():
        logging.info(f"No plain text body found for email {email_data.get('id')}, attempting HTML parsing.")
        try:
            soup = BeautifulSoup(email_data['body_html'], 'html.parser')
            email_data['body_text'] = soup.get_text(separator='\n', strip=True)
        except Exception as e:
            logging.error(f"Error parsing HTML for text fallback in email {email_data.get('id')}: {e}", exc_info=True)
            email_data['body_text'] = "[Could not parse HTML content]"

    email_data['body_text'] = email_data['body_text'].strip()
    email_data['body_html'] = email_data['body_html'].strip()
    
    # Map content field for frontend compatibility
    email_data['content'] = email_data['body_text']
    
    return email_data

def _extract_email_address(sender_string: str) -> str | None:
    """
    Extracts the email address from a sender string.
    Handles formats like "Display Name <email@example.com>" or just "email@example.com".
    Returns the email address in lowercase or None if not found.
    """
    if not isinstance(sender_string, str):
        return None
    # Regex to find an email address pattern
    match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', sender_string)
    if match:
        return match.group(0).lower()
    # Fallback for cases where the string might just be an email without <>
    # or if the regex fails for some unusual but valid sender strings.
    # This is a basic fallback; more sophisticated parsing might be needed for edge cases.
    cleaned_sender = sender_string.strip().lower()
    if '@' in cleaned_sender and '.' in cleaned_sender.split('@')[-1]: # Basic check
        return cleaned_sender
    logging.debug(f"Could not extract a standard email address from: '{sender_string}'")
    return None # Return None if no clear email address is found


# --- NEW FUNCTION: get_context_for_analysis ---
def get_context_for_analysis(llm_client, email_body, user_context=None, memory=None):
    """
    Generate context information for email analysis that can be passed to the LLM.
    This enhances the agent's understanding by providing user-specific context.

    Args:
        llm_client: The LLM client
        email_body: Text of the email to analyze
        user_context: Optional user context dictionary
        memory: Optional memory system instance

    Returns:
        dict: Context information for analysis
    """
    context = {
        "user_preferences": {},
        "known_senders": {},
        "recent_interactions": [],
        "time_context": datetime.now().strftime("%Y-%m-%d %H:%M")
    }

    # Add user preferences if available
    if user_context and "user_preferences" in user_context:
        context["user_preferences"] = user_context["user_preferences"]
    elif memory:
        context["user_preferences"] = memory.get_user_preferences()

    # Add known senders context if available
    if memory and hasattr(memory, "user_profile"):
        # Extract list of important senders
        email_prefs = memory.user_profile.get("email_preferences", {})
        important_senders = email_prefs.get("important_senders", [])
        filtered_domains = email_prefs.get("filtered_domains", [])

        if important_senders:
            context["known_senders"]["important"] = important_senders
        if filtered_domains:
            context["known_senders"]["filtered"] = filtered_domains

    # Get patterns and topics if needed (for more complex analysis)
    # This would be used for enhanced versions of analysis

    return context

# --- REPLACED FUNCTION: analyze_email_with_context (replaces analyze_email_with_llm) ---
def analyze_email_with_context(llm_client, email_data, config, memory=None):
    """
    Enhanced version of analyze_email_with_llm that includes contextual information
    from the agent's memory system.

    Args:
        llm_client: The LLM client
        email_data: Dictionary with email data
        config: Configuration dictionary
        memory: Optional memory system instance

    Returns:
        dict: Analysis results with LLM's assessment
    """
    if not llm_client:
        logging.error("LLM client not provided to analyze_email_with_context.")
        return None

    email_text = email_data.get('body_text', '')
    if not email_text or email_text.isspace():
        logging.debug("Email body is empty, skipping analysis.")
        return None

    # Get settings from config dict
    model_name = config['llm']['model_name']
    max_input_chars = config['llm']['analysis_max_input_chars']
    max_tokens = config['llm']['analysis_max_tokens']
    temperature = config['llm']['analysis_temperature']

    truncated_text = email_text[:max_input_chars]
    if len(email_text) > max_input_chars:
        logging.warning(f"Email text truncated to {max_input_chars} chars for analysis.")

    # Get user context for enhanced analysis
    # Pass llm_client and email_text to get_context_for_analysis
    user_context = get_context_for_analysis(llm_client, email_text, memory=memory)
    sender = email_data.get('sender', 'Unknown')
    subject = email_data.get('subject', 'No Subject')

    # Enhanced system prompt with context awareness
    system_prompt = """You are an intelligent email analysis agent that helps users manage their inbox efficiently.

Your task is to analyze the provided email and output a single, valid JSON object with these fields:
1. "urgency_score": An integer from 1 (very low) to 5 (very high).
2. "purpose": A string matching one of these exact categories: "promotion", "transactional", "social", "alert", "personal", "forum_digest", "action_required", "information".
3. "response_needed": A boolean indicating if the email likely requires a response.
4. "estimated_time": An integer representing the estimated minutes needed to properly address this email.

Classify the primary purpose of the following email. Use ONLY one of the following categories:

- **promotion**: For marketing messages, newsletters, sales offers, product announcements, or discounts.
  - Good Example: "Weekly Digest", "25% Off Sale", "New Product Launch"
  - Bad Example: An invoice for a product (this is 'transactional'), a security alert (this is 'alert').

- **transactional**: For automated receipts, invoices, shipping notifications, or purchase confirmations.
  - Good Example: "Your order has shipped!", "Your receipt from ExampleCorp"
  - Bad Example: A marketing email offering a discount on a future purchase (this is 'promotion').

- **social**: For notifications from social media platforms like LinkedIn, Facebook, Twitter, etc.
  - Good Example: "You have a new connection request on LinkedIn", "Someone mentioned you on Twitter"
  - Bad Example: An email from a person's social media account (e.g., from john.doe@facebook.com) that is a direct personal message (this is 'personal').

- **alert**: For security warnings, account activity notifications, or system alerts.
  - Good Example: "Security Alert: New sign-in to your account", "Your storage is almost full"
  - Bad Example: A promotional offer from a security company (this is 'promotion').

- **personal**: For direct, person-to-person conversations that are not related to business or automated systems.
  - Good Example: "Re: Weekend plans", "Catching up"
  - Bad Example: A mass newsletter sent from a person's name (this is 'promotion').

- **forum_digest**: For summaries or digests from online forums, mailing lists, or groups like Quora, Reddit, or Google Groups.
  - Good Example: "Quora Digest: Questions you might be interested in"
  - Bad Example: A direct notification about a reply to your specific post (this could be 'social' or 'personal').

- **action_required**: For emails that explicitly require the user to perform a specific action, often with a deadline. This is a high-signal category.
  - Good Example: "URGENT: Action Required - Complete Your Registration", "Please approve this request"
  - Bad Example: A newsletter with a "Read More" link (this is 'promotion').

- **information**: A general category for informational content that doesn't fit elsewhere and doesn't require a specific action.
  - Good Example: "Company policy update", "Your weekly project status report"
  - Bad Example: An urgent request to fix a server (this is 'action_required').

When determining urgency and purpose, consider:
- Sender: Emails from the user's important contacts should be prioritized
- Content: Look for explicit requests, questions, deadlines, or important information
- Subject: Pay attention to urgent keywords or explicit requests
- Context: Use the user's preferences and history to make better judgments

Output ONLY the JSON object with no introductory or explanatory text."""

    # Enhanced user prompt with more context
    user_prompt = f"""Analyze the following email based on the system instructions.

Email Information:
- From: {sender}
- Subject: {subject}
- User Context: {json.dumps(user_context)}

Email Content:
---
{truncated_text}
---

Output ONLY the JSON object. JSON Output:"""

    # Rest of the function remains similar to the existing analyze_email_with_llm
    # but expects the enhanced JSON response with additional fields

    analysis_result = None
    for attempt in range(MAX_RETRIES):
        try:
            logging.info(f"Requesting enhanced analysis from Anthropic Claude ({model_name})... Attempt {attempt + 1}/{MAX_RETRIES}")
            message = llm_client.messages.create(
                model=model_name, system=system_prompt,
                messages=[{"role": "user", "content": [{"type": "text", "text": user_prompt}]}],
                max_tokens=max_tokens, temperature=temperature,
            )

            # Parsing Logic (similar to existing function)
            if message and message.content and len(message.content) > 0:
                raw_text = message.content[0].text.strip()
                # Markdown fence cleaning logic
                cleaned_json_text = raw_text
                if raw_text.startswith("```") and raw_text.endswith("```"):
                     lines = raw_text.splitlines()
                     if len(lines) > 2: cleaned_json_text = "\n".join(lines[1:-1]).strip()
                     else:
                         match = re.search(r'```(?:json)?\s*(\{.*\})\s*```', raw_text, re.DOTALL)
                         if match: cleaned_json_text = match.group(1).strip()
                         else: cleaned_json_text = raw_text.removeprefix("```json").removeprefix("```").removesuffix("```").strip()

                try:
                    analysis_data = json.loads(cleaned_json_text)
                    # Validate the required fields
                    if (isinstance(analysis_data.get('urgency_score'), int) and
                        isinstance(analysis_data.get('purpose'), str) and
                        isinstance(analysis_data.get('response_needed'), bool) and
                        isinstance(analysis_data.get('estimated_time'), int)):
                        analysis_result = analysis_data
                        logging.info(f"Enhanced LLM Analysis Received: {analysis_result}")
                        return analysis_result
                    else:
                        logging.warning(f"Enhanced LLM analysis JSON has incorrect types or missing fields. Cleaned Text: {cleaned_json_text}")
                        # Try to salvage what we can
                        if isinstance(analysis_data.get('urgency_score'), int) and isinstance(analysis_data.get('purpose'), str):
                            partial_result = {
                                'urgency_score': analysis_data.get('urgency_score'),
                                'purpose': analysis_data.get('purpose'),
                                'response_needed': False,  # Default values
                                'estimated_time': 5
                            }
                            logging.info(f"Salvaged partial analysis: {partial_result}")
                            return partial_result
                        return None
                except json.JSONDecodeError:
                    logging.warning(f"Enhanced LLM analysis response was not valid JSON. Cleaned Text: {cleaned_json_text}")
                    return None
            else:
                 logging.warning("Anthropic analysis response or content block is missing/empty.")
                 return None

        # Error handling - same as existing function
        except anthropic.APIConnectionError as e:
             logging.error(f"Anthropic API Connection Error during analysis: {e}")
             if attempt < MAX_RETRIES - 1: time.sleep(RETRY_DELAY_SECONDS); continue
             else: logging.error("Max retries reached for API connection error."); return None
        except anthropic.RateLimitError as e:
             logging.error(f"Anthropic Rate Limit Error during analysis: {e}"); return None
        except anthropic.APIStatusError as e:
             logging.error(f"Anthropic API Status Error during analysis: status_code={e.status_code}, response={e.response}")
             if e.status_code >= 500 and attempt < MAX_RETRIES - 1: time.sleep(RETRY_DELAY_SECONDS); continue
             else: logging.error(f"Non-retryable status ({e.status_code}) or max retries reached."); return None
        except Exception as e:
            logging.error(f"An unexpected error occurred during Anthropic analysis: {type(e).__name__}: {e}", exc_info=True)
            return None

    logging.error("Max retries reached for Enhanced LLM analysis.")
    return None



def summarize_email_with_memory(llm_client, email_data, config, memory=None, summary_type="standard"):
    """
    Enhanced version of summarize_email_with_llm that considers user's preferences
    and history from the memory system, supports different summary types, and cleans the output.

    Args:
        llm_client: The LLM client
        email_data: Dictionary with email data
        config: Configuration dictionary
        memory: Optional memory system instance
        summary_type: Type of summary to generate ("standard", "brief", "detailed", "action_focused")

    Returns:
        str: The generated and cleaned summary, or an error message.
    """
    if not llm_client: return "Summarization unavailable: LLM client not provided."

    email_text = email_data.get('body_text', '')
    if not email_text or email_text.isspace(): return "Summarization unavailable: Email body empty."

    # Get settings from config dict
    model_name = config['llm']['model_name']
    max_input_chars = config['llm']['summary_max_input_chars']
    max_tokens = config['llm']['summary_max_tokens']
    temperature = config['llm']['summary_temperature']

    truncated_text = email_text[:max_input_chars]
    if len(email_text) > max_input_chars:
        logging.warning(f"Email text truncated to {max_input_chars} chars for summarization.")

    # Get context from memory if available
    user_context = None
    if memory:
        # Pass llm_client and email_text to get_context_for_analysis
        user_context = get_context_for_analysis(llm_client, email_text, memory=memory)

    # Select the appropriate system prompt based on summary type
    if summary_type == "brief":
        system_prompt = """You are a helpful assistant that creates extremely concise email summaries in 1-2 sentences, focusing only on the most critical information. Provide just the key points without any introductory phrases. Output ONLY the summary text."""
    elif summary_type == "detailed":
        system_prompt = """You are a helpful assistant that creates comprehensive email summaries, providing all relevant details and context. Include main points, requests, deadlines, and any important background information, organized in bullet points for readability. Output ONLY the summary text itself."""
    elif summary_type == "action_focused":
        system_prompt = """You are a helpful assistant that summarizes emails with a focus on required actions. Your summary should prioritize: 1) What action is needed, 2) When it must be completed, 3) Who else is involved. Format as action-oriented bullet points. Output ONLY the summary text itself."""
    else:  # standard
        system_prompt = """You are a helpful assistant that summarizes emails concisely in 2-3 bullet points, focusing on key information and action items. Provide only the final summary text itself, without any introductory phrases like 'Here is the summary:' or any concluding remarks. Output ONLY the summary text."""

    # Enhanced user prompt with more context
    sender = email_data.get('sender', 'Unknown')
    subject = email_data.get('subject', 'No Subject')

    user_prompt = f"""Please summarize the following email according to the system instructions:

Email Information:
- From: {sender}
- Subject: {subject}
{f'- User Context: {json.dumps(user_context)}' if user_context else ''}

Email Content:
---
{truncated_text}
---

Output ONLY the summary text. Summary:""" # Emphasize ONLY the summary text

    # Rest of the function similar to existing summarize_email_with_llm
    summary = f"Error: Summarization failed after {MAX_RETRIES} attempts."
    for attempt in range(MAX_RETRIES):
        try:
            logging.info(f"Requesting {summary_type} summary from Anthropic Claude ({model_name})... Attempt {attempt + 1}/{MAX_RETRIES}")
            message = llm_client.messages.create(
                model=model_name, system=system_prompt,
                messages=[{"role": "user", "content": [{"type": "text", "text": user_prompt}]}],
                max_tokens=max_tokens, temperature=temperature,
            )

            # Parsing Logic
            if message and message.content and len(message.content) > 0:
                 summary_text = message.content[0].text.strip()
                 if summary_text:
                     # --- ADDED POST-PROCESSING ---
                     # Remove common introductory phrases (case-insensitive)
                     phrases_to_remove = [
                         r"^\s*Here'?s?\s+a\s+summary.*?:",  # Matches "Here's a summary...", "Here is a summary..." etc.
                         r"^\s*Summary:",
                         r"^\s*Okay,\s+here'?s?\s+the\s+summary:",
                         r"^\s*Here'?s?\s+the\s+key\s+points.*?:", # Matches "Here's the key points...", "Here are the key points..."
                         r"^\s*Here'?s?\s+the\s+key\s+action\s+items.*?:", # Matches "Here's the key action items...", "Here are the key action items..."
                         # Add more general patterns if needed
                     ]
                     cleaned_summary = summary_text
                     for phrase_pattern in phrases_to_remove:
                         # Use re.sub for case-insensitive replacement at the beginning of the string/line
                         cleaned_summary = re.sub(phrase_pattern, '', cleaned_summary, count=1, flags=re.IGNORECASE | re.MULTILINE).strip()

                     # Remove leading/trailing list markers if they are the only thing left after cleaning
                     cleaned_summary = cleaned_summary.strip('*-• ') # Added bullet point

                     # Use the cleaned summary if it's not empty, otherwise keep original LLM output
                     summary = cleaned_summary if cleaned_summary else summary_text
                     # --- END POST-PROCESSING ---

                     logging.info(f"{summary_type} summary parsed and cleaned successfully.")
                     return summary # Success
                 else:
                     logging.warning("LLM returned an empty summary string.")
                     summary = "Error: Summarization returned empty content."
                     # Let loop continue or error out naturally
            else:
                 logging.warning("Anthropic summary response or content block is missing/empty.")
                 summary = "Error: Summarization response missing content."
                 # Let loop continue or error out naturally

        # Error handling - same as existing function
        except anthropic.APIConnectionError as e:
             logging.error(f"Anthropic API Connection Error during summarization: {e}")
             if attempt < MAX_RETRIES - 1: time.sleep(RETRY_DELAY_SECONDS); continue
             else: summary = f"Error: API Connection Error during summarization ({e})"
        except anthropic.RateLimitError as e:
             logging.error(f"Anthropic Rate Limit Error during summarization: {e}")
             summary = f"Error: Rate Limit Error during summarization ({e})"; break
        except anthropic.APIStatusError as e:
             logging.error(f"Anthropic API Status Error during summarization: status_code={e.status_code}, response={e.response}")
             if e.status_code >= 500 and attempt < MAX_RETRIES - 1: time.sleep(RETRY_DELAY_SECONDS); continue
             else: summary = f"Error: API Status Error during summarization ({e.status_code})"; break
        except Exception as e:
            logging.error(f"An unexpected error occurred during Anthropic summarization: {type(e).__name__}: {e}", exc_info=True)
            summary = f"Error: Unexpected error during summarization ({type(e).__name__})"; break

    return summary


# --- REPLACED FUNCTION: classify_and_get_analysis_with_memory (replaces classify_and_get_analysis) ---
def classify_email_with_reasoning(parsed_email, llm_client, feedback_history, ml_pipeline, ml_label_encoder, config,
                                 memory=None, user_important_senders=None):
    """
    NEW: Enhanced classification function using explainable reasoning engine.
    Provides transparent, step-by-step reasoning for all decisions.
    
    Args:
        parsed_email: Dictionary with email data
        llm_client: The LLM client
        feedback_history: Dictionary of sender->priority mappings from user feedback
        ml_pipeline: Trained ML pipeline (if available)
        ml_label_encoder: ML label encoder (if available)
        config: Configuration dictionary
        memory: Optional memory system instance
        user_important_senders: List of user-defined important senders
        
    Returns:
        ClassificationResult: Complete result with reasoning chain and confidence
    """
    logging.info("Using new explainable reasoning engine for email classification")
    
    # Initialize reasoning engine
    reasoning_engine = ExplainableReasoningEngine(config)
    
    # Perform classification with full reasoning
    result = reasoning_engine.classify_email_with_reasoning(
        email_data=parsed_email,
        llm_client=llm_client,
        feedback_history=feedback_history,
        ml_pipeline=ml_pipeline,
        ml_label_encoder=ml_label_encoder,
        memory=memory,
        user_important_senders=user_important_senders
    )
    
    # Log the reasoning for debugging
    logging.info(f"Classification Result: {result.priority} (confidence: {result.confidence:.1f}%)")
    logging.info(f"Decision method: {result.metadata.get('decision_method')}")
    logging.info(f"Reasoning steps: {len(result.reasoning_chain)}")
    
    return result


def classify_and_get_analysis_with_memory(parsed_email, llm_client, feedback_history, ml_pipeline, ml_label_encoder, config,
                                          memory=None, user_important_senders=None):
    """
    Enhanced version of classify_and_get_analysis that utilizes the memory system
    for improved classification and analysis. This integrates all user preferences
    and learning from the memory system.

    Args are the same as the original function plus:
        memory: Optional memory system instance

    Returns:
        tuple: (priority_string, enhanced_analysis_dict or None)
    """
    # Initialize if None is passed
    if user_important_senders is None:
       user_important_senders = []

    # Get important senders from memory if available
    if memory and not user_important_senders:
        user_prefs = memory.get_user_preferences()
        user_important_senders = user_prefs.get("email_preferences", {}).get("important_senders", [])

    # The rest of the function follows a similar flow to the original
    # but uses analyze_email_with_context instead of analyze_email_with_llm

    enhanced_analysis_result = None
    if not parsed_email:
        return PRIORITY_MEDIUM, None

    sender = parsed_email.get('sender', '').lower()
    subject = parsed_email.get('subject', '').lower()
    email_body = parsed_email.get('body_text', '')

    # Extract sender key using helper (same as original)
    sender_key = sender # Default to full sender
    match = re.search(r'<(.+?)>', sender)
    if match:
        sender_key = match.group(1).lower()
    else:
         sender_key = sender.split('@')[0] if '@' in sender else sender
         sender_key = re.sub(r'[^\w\s.-]', '', sender_key).strip().lower()

    # === 1. Check Feedback History === (same as original)
    if sender_key and sender_key in feedback_history:
        corrected_priority = feedback_history[sender_key]
        logging.info(f"Feedback Match: Using corrected priority for sender key '{sender_key}' -> {corrected_priority}")
        return corrected_priority, None

    # === 2. Attempt ML Model Prediction === (similar to original)
    ml_predicted_priority = None
    if ml_pipeline and ml_label_encoder:
        logging.info("No feedback match. Performing enhanced LLM analysis for ML features...")

        # Use the enhanced analysis function
        enhanced_analysis_result = analyze_email_with_context(llm_client, parsed_email, config, memory)

        prediction_data = parsed_email.copy()
        if enhanced_analysis_result:
             prediction_data['llm_urgency'] = enhanced_analysis_result.get('urgency_score')
             prediction_data['llm_purpose'] = enhanced_analysis_result.get('purpose')
             # Add the new fields to prediction data
             prediction_data['llm_response_needed'] = enhanced_analysis_result.get('response_needed', False)
             prediction_data['llm_estimated_time'] = enhanced_analysis_result.get('estimated_time', 5)
        else:
             prediction_data['llm_urgency'] = 0
             prediction_data['llm_purpose'] = "Unknown"
             prediction_data['llm_response_needed'] = False
             prediction_data['llm_estimated_time'] = 5

        # Import predict_priority if not already imported globally
        # Ensure ml_utils.py is available in the environment
        try:
            from ml_utils import predict_priority
            ml_predicted_priority = predict_priority(
                prediction_data, ml_pipeline, ml_label_encoder
            )
        except ImportError:
            logging.error("Could not import 'predict_priority' from 'ml_utils'. ML prediction skipped.")
            ml_predicted_priority = None
        except Exception as ml_err:
            logging.error(f"Error during ML prediction: {ml_err}", exc_info=True)
            ml_predicted_priority = None


        if ml_predicted_priority:
            logging.info(f"ML Model Prediction Used -> {ml_predicted_priority}")
            # Don't return yet, check critical sender rules first
            # return ml_predicted_priority, enhanced_analysis_result # Old logic
        else:
            logging.warning("ML prediction failed or returned None. Falling back to rules/LLM logic.")
    else:
        # Only log warning if ML files were expected but not loaded (same as original)
        if os.path.exists(config['ml']['pipeline_filename']) or os.path.exists(config['ml']['label_encoder_filename']):
             logging.warning("ML model files exist but pipeline/encoder objects not loaded. Proceeding with rules/LLM logic.")
        else:
             logging.info("ML model not trained/loaded. Proceeding with rules/LLM logic.")


    # === 3. Fallback to Rules / LLM Analysis === (similar to original)
    # --- *** CRITICAL SENDER CHECK (USER + CONFIG + MEMORY) - ENHANCED *** ---
    # Combine config list and user list (remove duplicates and ensure lowercase)
    config_important_senders = [s.lower() for s in config['classification']['important_senders']]
    all_important_senders = set(config_important_senders + [s.lower() for s in user_important_senders])
    logging.debug(f"Checking against {len(all_important_senders)} unique important senders (config + user).")

    raw_sender = parsed_email.get('sender', '').lower()
    for imp_sender in all_important_senders:
         # Check if it's a domain (@domain.com) or a specific address
         is_domain_rule = imp_sender.startswith("@")
         match_found = False
         if is_domain_rule:
             # Extract sender's domain if possible
             sender_domain_match = re.search(r'@([\w.-]+)', raw_sender)
             if sender_domain_match:
                 sender_domain = "@" + sender_domain_match.group(1)
                 if sender_domain == imp_sender:
                     match_found = True
         elif imp_sender in raw_sender: # Check if the specific address is part of the 'From' header
              match_found = True

         if match_found:
             source = "User Pref" if imp_sender in [s.lower() for s in user_important_senders] else "Config" # Ensure comparison list is lowercased
             logging.info(f"Rule Match ({source}): Sender '{imp_sender}' -> {PRIORITY_CRITICAL}")
             # If a critical sender matches, this overrides everything else
             # Perform analysis if not already done (e.g., if ML failed early)
             if enhanced_analysis_result is None:
                 enhanced_analysis_result = analyze_email_with_context(llm_client, parsed_email, config, memory)
             return PRIORITY_CRITICAL, enhanced_analysis_result # Return immediately
    # --- *** END CRITICAL SENDER CHECK *** ---

    # --- If ML predicted something AND it wasn't overridden by critical sender, return ML result ---
    if ml_predicted_priority:
         logging.info(f"Returning ML prediction ({ml_predicted_priority}) as no critical sender rule matched.")
         # We already have enhanced_analysis_result from the ML step
         return ml_predicted_priority, enhanced_analysis_result
    # --- End ML Result Return ---

    # Use enhanced analysis if not already done (e.g., ML was skipped or failed before analysis)
    if enhanced_analysis_result is None:
         logging.info("Performing enhanced LLM analysis for fallback rules...")
         enhanced_analysis_result = analyze_email_with_context(llm_client, parsed_email, config, memory)

    # Use rules from config (same as original)
    sender_keywords_low = config['classification']['sender_keywords_low']
    subject_keywords_low = config['classification']['subject_keywords_low']
    subject_keywords_high = config['classification']['subject_keywords_high']

    raw_subject = parsed_email.get('subject', '').lower()

    # Combine low priority checks (same as original)
    low_prio_keywords = sender_keywords_low + subject_keywords_low
    for keyword in low_prio_keywords:
         if keyword in raw_sender or keyword in raw_subject:
             logging.info(f"Fallback Rule Match: Low priority keyword '{keyword}' -> {PRIORITY_LOW}")
             return PRIORITY_LOW, enhanced_analysis_result

    # Check high priority subject keywords (same as original)
    rule_suggests_high = any(keyword in raw_subject for keyword in subject_keywords_high)
    if rule_suggests_high:
         logging.info(f"Fallback Rule Match: Subject keyword suggests HIGH.")

    # Enhanced decision logic using additional fields from enhanced analysis
    if enhanced_analysis_result:
        urgency = enhanced_analysis_result.get('urgency_score', 0)
        purpose = enhanced_analysis_result.get('purpose', 'Other').lower()
        response_needed = enhanced_analysis_result.get('response_needed', False)
        estimated_time = enhanced_analysis_result.get('estimated_time', 5)

        # CRITICAL if high urgency and response needed and takes time
        if urgency >= 5 and response_needed and estimated_time > 10:
            logging.info(f"Enhanced Analysis: Very high urgency ({urgency}), response needed, est. time {estimated_time}min -> {PRIORITY_CRITICAL}")
            return PRIORITY_CRITICAL, enhanced_analysis_result

        # HIGH if good urgency and response needed or action request
        if urgency >= 4 or (response_needed and purpose in ["action request", "question"]):
            logging.info(f"Enhanced Analysis: High urgency ({urgency}), response_needed={response_needed}, purpose='{purpose}' -> {PRIORITY_HIGH}")
            return PRIORITY_HIGH, enhanced_analysis_result

        # MEDIUM if moderate urgency or meeting or might need response
        if urgency >= 3 or purpose in ["action request", "question", "meeting invite"] or response_needed:
             logging.info(f"Enhanced Analysis: Medium urgency ({urgency}), purpose '{purpose}', response_needed={response_needed} -> {PRIORITY_MEDIUM}")
             return PRIORITY_MEDIUM, enhanced_analysis_result

        # If none of the above, default to LOW based on analysis
        logging.info(f"Enhanced Analysis: Low urgency {urgency}, Purpose '{purpose}', response_needed={response_needed} -> {PRIORITY_LOW}")
        return PRIORITY_LOW, enhanced_analysis_result

    # Final Fallback based only on rules if Enhanced LLM analysis failed completely
    logging.warning("Enhanced LLM analysis failed or returned None. Falling back purely on keyword rules.")
    if rule_suggests_high:
        logging.info(f"Final Fallback (No LLM): Rule keyword matched -> Defaulting to {PRIORITY_HIGH}")
        return PRIORITY_HIGH, None # No analysis result available
    else:
        logging.info(f"Final Fallback (No LLM): No strong signal -> Defaulting to {PRIORITY_MEDIUM}")
        return PRIORITY_MEDIUM, None # No analysis result available


# --- Additional New Functions for Enhanced Agent Capabilities ---

def suggest_email_actions(llm_client, email_data, analysis_result, config, memory=None):
    """
    New function to suggest potential actions for an email based on its content and analysis.

    Args:
        llm_client: The LLM client
        email_data: Dictionary with email data
        analysis_result: The analysis result from analyze_email_with_context
        config: Configuration dictionary
        memory: Optional memory system instance

    Returns:
        list: A list of suggested actions with reasoning
    """
    if not llm_client or not email_data or not analysis_result:
        logging.warning("Cannot suggest actions: Missing LLM client, email data, or analysis result.")
        return []

    # Get settings from config
    model_name = config['llm']['model_name']
    max_tokens = config['llm'].get('action_suggestion_max_tokens', 1024) # Increased default from 250 to 1024
    temperature = 0.5  # Lower temperature for more predictable outputs

    # Prepare context
    email_text = email_data.get('body_text', '')
    sender = email_data.get('sender', 'Unknown')
    subject = email_data.get('subject', 'No Subject')

    # Truncate email text if needed
    max_context_chars = 2000  # Shorter than full analysis to save tokens
    truncated_text = email_text[:max_context_chars]
    if len(email_text) > max_context_chars:
        logging.warning(f"Email text truncated to {max_context_chars} chars for action suggestion.")

    # Get additional context from memory if available
    user_context = None
    if memory:
        # Pass llm_client and email_text to get_context_for_analysis
        user_context = get_context_for_analysis(llm_client, email_text, memory=memory)

    # System prompt with optimized reasoning constraint
    system_prompt = """You are an intelligent email assistant that suggests actions for emails.
For each email, analyze its content and purpose to suggest 1-3 specific actions the user might want to take.

Your response must be a single, valid JSON object with an "actions" array. Each action in the array should be an object with:
1. "type": One of ["reply", "archive", "forward", "schedule", "delegate", "read_later", "follow_up"]
2. "description": A brief description of the specific action (e.g., "Reply confirming receipt", "Archive as no action needed")
3. "reasoning": A VERY BRIEF explanation (max 15 words) why this action is appropriate based on the email content/analysis.

Focus on practical, specific actions based on email content. Don't suggest generic actions that would apply to any email.
Output ONLY the JSON object with no introductory or explanatory text."""

    # User prompt
    user_prompt = f"""Suggest appropriate actions for this email:

Email Information:
- From: {sender}
- Subject: {subject}
- Urgency Score: {analysis_result.get('urgency_score', 'Unknown')}
- Purpose: {analysis_result.get('purpose', 'Unknown')}
- Response Needed: {analysis_result.get('response_needed', False)}
{f'- User Context: {json.dumps(user_context)}' if user_context else ''}

Email Content (truncated):
---
{truncated_text}
---

Suggest 1-3 appropriate actions as a JSON object with an "actions" array. Output ONLY the JSON object:"""

    # Retry loop for robust LLM interaction
    for attempt in range(MAX_RETRIES):
        try:
            logging.info(f"Requesting action suggestions from Anthropic Claude ({model_name}). Max tokens: {max_tokens}. Attempt {attempt + 1}/{MAX_RETRIES}")
            message = llm_client.messages.create(
                model=model_name,
                system=system_prompt,
                messages=[{"role": "user", "content": [{"type": "text", "text": user_prompt}]}],
                max_tokens=max_tokens,
                temperature=temperature
            )

            # Parse the response
            if message and message.content and len(message.content) > 0:
                raw_text = message.content[0].text.strip()

                # Clean up the JSON text (same logic as analysis)
                cleaned_json_text = raw_text
                if raw_text.startswith("```") and raw_text.endswith("```"):
                    lines = raw_text.splitlines()
                    if len(lines) > 2:
                        cleaned_json_text = "\n".join(lines[1:-1]).strip()
                    else:
                        match = re.search(r'```(?:json)?\s*(\{.*\})\s*```', raw_text, re.DOTALL)
                        if match:
                            cleaned_json_text = match.group(1).strip()
                        else:
                            cleaned_json_text = raw_text.removeprefix("```json").removeprefix("```").removesuffix("```").strip()

                try:
                    # Parse the JSON
                    suggestion_data = json.loads(cleaned_json_text)
                    if "actions" in suggestion_data and isinstance(suggestion_data["actions"], list):
                        # Basic validation of action structure
                        valid_actions = []
                        for action in suggestion_data["actions"]:
                            if isinstance(action, dict) and \
                               "type" in action and isinstance(action["type"], str) and \
                               "description" in action and isinstance(action["description"], str) and \
                               "reasoning" in action and isinstance(action["reasoning"], str):
                               valid_actions.append(action)
                            else:
                                logging.warning(f"Skipping invalid action structure in suggestions: {action}")
                        logging.info(f"Successfully generated {len(valid_actions)} valid action suggestions")
                        return valid_actions
                    else:
                        logging.warning(f"Action suggestions missing 'actions' array or wrong format. Cleaned Text: {cleaned_json_text}")
                        # Continue to retry instead of returning immediately
                        continue
                except json.JSONDecodeError:
                    logging.warning(f"JSON parsing error on attempt {attempt + 1}/{MAX_RETRIES}: {cleaned_json_text}")
                    # Continue to retry instead of returning immediately
                    continue
            else:
                logging.warning(f"Empty or missing response from Anthropic for action suggestions on attempt {attempt + 1}/{MAX_RETRIES}")
                # Continue to retry instead of returning immediately
                continue

        except anthropic.APIConnectionError as e:
            logging.error(f"Anthropic API Connection Error during action suggestion on attempt {attempt + 1}/{MAX_RETRIES}: {e}")
            if attempt < MAX_RETRIES - 1:
                continue
        except anthropic.RateLimitError as e:
            logging.error(f"Anthropic Rate Limit Error during action suggestion on attempt {attempt + 1}/{MAX_RETRIES}: {e}")
            if attempt < MAX_RETRIES - 1:
                continue
        except anthropic.APIStatusError as e:
            logging.error(f"Anthropic API Status Error during action suggestion on attempt {attempt + 1}/{MAX_RETRIES}: status_code={e.status_code}, response={e.response}")
            if attempt < MAX_RETRIES - 1:
                continue
        except Exception as e:
            logging.error(f"Error generating action suggestions on attempt {attempt + 1}/{MAX_RETRIES}: {type(e).__name__}: {e}", exc_info=True)
            if attempt < MAX_RETRIES - 1:
                continue

    # Return empty list only after all retries have been exhausted
    logging.error(f"Failed to generate action suggestions after {MAX_RETRIES} attempts")
    return []


def generate_email_response(llm_client, email_data, response_type, config, memory=None):
    """
    Generate a draft email response using the LLM.

    Args:
        llm_client: The LLM client
        email_data: Dictionary with email data
        response_type: Type of response to generate ("polite_decline", "accept", "request_info", "acknowledge", "follow_up", etc.)
        config: Configuration dictionary
        memory: Optional memory system instance

    Returns:
        str: The generated email response or an error message
    """
    if not llm_client or not email_data:
        return "Error: Cannot generate response without email data or LLM client."

    # Get email details
    email_text = email_data.get('body_text', '')
    sender = email_data.get('sender', 'Unknown')
    subject = email_data.get('subject', 'No Subject')

    if not email_text or email_text.isspace():
        return "Error: Cannot generate response for empty email content."

    # Get settings from config
    model_name = config['llm']['model_name']
    max_input_chars = min(config['llm']['summary_max_input_chars'], 3000)  # Limit context size
    # Allow more tokens for response generation than summarization
    max_tokens = config['llm'].get('response_max_tokens', config['llm']['summary_max_tokens'] * 2)
    temperature = config['llm'].get('response_temperature', 0.7) # Slightly higher temperature

    truncated_text = email_text[:max_input_chars]
    if len(email_text) > max_input_chars:
        logging.warning(f"Email text truncated to {max_input_chars} chars for response generation.")

    # System prompt based on response type
    system_prompts = {
        "polite_decline": """You are an assistant that helps draft polite and professional email declines.
Your response should be courteous, clear about the decline, and concise. Maintain a professional tone while being respectful of the recipient's time and request. Do not add placeholders like [Your Name].""",

        "accept": """You are an assistant that helps draft positive and professional email acceptances.
Your response should be enthusiastic but professional, clear about accepting the request/invitation, and include any relevant details or questions needed for next steps. Do not add placeholders like [Your Name].""",

        "request_info": """You are an assistant that helps draft emails requesting additional information.
Your response should be specific about what information is needed and why, polite in tone, and make it easy for the recipient to provide the requested details. Do not add placeholders like [Your Name].""",

        "acknowledge": """You are an assistant that helps draft brief email acknowledgments.
Your response should confirm receipt, indicate any next steps or timeframe for a more detailed response if applicable, and be concise. Do not add placeholders like [Your Name].""",

        "follow_up": """You are an assistant that helps draft polite follow-up emails.
Your response should reference the previous communication, politely request an update, and make it easy for the recipient to respond. Do not add placeholders like [Your Name]."""
    }

    system_prompt = system_prompts.get(response_type, """You are an assistant that helps draft professional email responses.
Your response should be clear, concise, and appropriate to the context of the original email. Do not add placeholders like [Your Name].""")

    # User prompt
    user_prompt = f"""Draft a '{response_type}' email response to the following message.

Original Email:
From: {sender}
Subject: {subject}
---
{truncated_text}
---

Please write a complete email response text that could be sent with minimal editing. Format as plain text with an appropriate greeting (e.g., "Hi [Sender Name]," or "Dear [Sender Name],") and sign-off (e.g., "Best regards," or "Thanks,"). Do NOT include placeholders like "[Your Name]" in the sign-off.

Response Draft:"""

    # Call the LLM
    try:
        logging.info(f"Requesting email response draft ({response_type}) from Anthropic Claude ({model_name})...")
        message = llm_client.messages.create(
            model=model_name,
            system=system_prompt,
            messages=[{"role": "user", "content": [{"type": "text", "text": user_prompt}]}],
            max_tokens=max_tokens,
            temperature=temperature
        )

        if message and message.content and len(message.content) > 0:
            response_text = message.content[0].text.strip()
            if response_text:
                logging.info(f"Generated {response_type} email response successfully")
                # Basic check to remove common placeholder if LLM ignores instruction
                response_text = response_text.replace("[Your Name]", "").strip()
                return response_text
            else:
                logging.warning("LLM generated an empty response string.")
                return "Error: Generated empty response"
        else:
            logging.warning("No response content received from LLM for email draft.")
            return "Error: No response received from LLM"
    except anthropic.APIConnectionError as e:
         logging.error(f"Anthropic API Connection Error during response generation: {e}")
         return f"Error: API Connection Error ({e})"
    except anthropic.RateLimitError as e:
         logging.error(f"Anthropic Rate Limit Error during response generation: {e}")
         return f"Error: Rate Limit Error ({e})"
    except anthropic.APIStatusError as e:
         logging.error(f"Anthropic API Status Error during response generation: status_code={e.status_code}, response={e.response}")
         return f"Error: API Status Error ({e.status_code})"
    except Exception as e:
        logging.error(f"Error generating email response: {type(e).__name__}: {e}", exc_info=True)
        return f"Error: Failed to generate response: {type(e).__name__}"


def prepare_email_batch_overview(llm_client, email_batch, config, memory=None):
    """
    Generate a summarized overview of a batch of emails, highlighting patterns and priorities.

    Args:
        llm_client: The LLM client
        email_batch: List of email data dictionaries (should include 'priority' and 'llm_purpose')
        config: Configuration dictionary
        memory: Optional memory system instance

    Returns:
        str: A summarized overview of the batch or an error message
    """
    if not llm_client:
        return "Error: LLM client not provided for batch overview."
    if not email_batch:
        return "No emails to analyze in this batch."

    # Get settings from config
    model_name = config['llm']['model_name']
    max_tokens = config['llm'].get('batch_overview_max_tokens', 300) # Allow config override
    temperature = config['llm'].get('batch_overview_temperature', 0.7)

    # Prepare batch information
    batch_size = len(email_batch)
    # Use Counter for breakdowns
    priorities = Counter([e.get('priority', 'Unknown') for e in email_batch])
    # Use the enhanced analysis purpose if available
    purposes = Counter([e.get('llm_purpose', 'Unknown') for e in email_batch if e.get('llm_purpose')]) # Count only if purpose exists

    # Create a concise representation of each email (limit context size)
    email_summaries = []
    max_sample_emails = 10 # Limit number of samples sent to LLM
    for i, email in enumerate(email_batch[:max_sample_emails], 1):
        sender = email.get('sender', 'Unknown')
        # Clean sender for brevity
        sender_match = re.search(r'([^<]+)<', sender)
        sender_name = sender_match.group(1).strip() if sender_match else sender.split('@')[0]

        subject = email.get('subject', 'No Subject')
        priority = email.get('priority', 'Unknown')
        purpose = email.get('llm_purpose', 'N/A') # Use N/A if purpose missing

        email_summaries.append(f"- Email {i}: From '{sender_name}', Subject: '{subject[:50]}...', Priority: {priority}, Purpose: {purpose}")

    all_summaries = "\n".join(email_summaries)
    if batch_size > max_sample_emails:
        all_summaries += f"\n... (and {batch_size - max_sample_emails} more emails)"

    # System prompt
    system_prompt = """You are an email batch analysis assistant. You provide concise, insightful overviews of email batches.
Highlight key patterns, identify the most important emails needing attention (mentioning priority/purpose), and suggest an efficient processing approach.
Be practical, specific, and brief (around 150-200 words)."""

    # User prompt
    user_prompt = f"""Analyze this batch of {batch_size} recent emails:

Batch Statistics:
- Total emails: {batch_size}
- Priority breakdown: {json.dumps(dict(priorities))}
- Purpose breakdown (if available): {json.dumps(dict(purposes))}

Sample of emails (up to {max_sample_emails}):
{all_summaries}

Provide a brief analysis (max 200 words) highlighting:
1. Key patterns or themes observed in the batch.
2. Which emails (by priority/purpose/sender) likely need the most urgent attention.
3. A suggested approach or order to efficiently handle this batch."""

    # Call the LLM
    try:
        logging.info(f"Requesting batch overview from Anthropic Claude ({model_name})...")
        message = llm_client.messages.create(
            model=model_name,
            system=system_prompt,
            messages=[{"role": "user", "content": [{"type": "text", "text": user_prompt}]}],
            max_tokens=max_tokens,
            temperature=temperature
        )

        if message and message.content and len(message.content) > 0:
            overview_text = message.content[0].text.strip()
            if overview_text:
                logging.info(f"Generated batch overview successfully")
                return overview_text
            else:
                logging.warning("LLM generated an empty batch overview.")
                return "Error: Generated empty batch overview"
        else:
            logging.warning("No response content received from LLM for batch overview.")
            return "Error: No response received from LLM for batch overview"
    except anthropic.APIConnectionError as e:
         logging.error(f"Anthropic API Connection Error during batch overview: {e}")
         return f"Error: API Connection Error ({e})"
    except anthropic.RateLimitError as e:
         logging.error(f"Anthropic Rate Limit Error during batch overview: {e}")
         return f"Error: Rate Limit Error ({e})"
    except anthropic.APIStatusError as e:
         logging.error(f"Anthropic API Status Error during batch overview: status_code={e.status_code}, response={e.response}")
         return f"Error: API Status Error ({e.status_code})"
    except Exception as e:
        logging.error(f"Error generating batch overview: {type(e).__name__}: {e}", exc_info=True)
        return f"Error: Failed to generate batch overview: {type(e).__name__}"


def process_email_with_memory(email_data, llm_client, config, memory=None, feedback_history=None, ml_pipeline=None, ml_label_encoder=None):
    """
    Process a single email with the full agent capabilities, integrating memory and enhanced analysis.

    This is a higher-level function that combines all the enhanced capabilities to process
    an email completely, including classification, analysis, summarization, and action suggestions.

    Args:
        email_data: Dictionary with email data (parsed from parse_email_content)
        llm_client: The LLM client
        config: Configuration dictionary
        memory: Optional memory system instance
        feedback_history: Optional feedback history dictionary
        ml_pipeline: Optional ML pipeline for classification
        ml_label_encoder: Optional label encoder for ML classification

    Returns:
        dict: Complete processed email data with all enhancements added as new keys.
              Returns None if initial email_data is invalid.
    """
    if not email_data or not isinstance(email_data, dict):
        logging.error("Invalid email_data provided to process_email_with_memory.")
        return None

    processed_data = email_data.copy() # Work on a copy

    # Get user important senders from memory if available
    user_important_senders = []
    if memory:
        try:
            user_prefs = memory.get_user_preferences()
            user_important_senders = user_prefs.get("email_preferences", {}).get("important_senders", [])
        except Exception as e:
            logging.error(f"Failed to get user preferences from memory: {e}", exc_info=True)
            user_important_senders = [] # Default to empty list on error

    # 1. Classify and get enhanced analysis (with optional reasoning system)
    current_feedback = feedback_history if isinstance(feedback_history, dict) else {}
    
    # Check if reasoning system should be used
    use_reasoning = config.get('reasoning', {}).get('enabled', False)
    
    if use_reasoning:
        try:
            # Import here to avoid circular imports
            from reasoning_integration import process_email_with_enhanced_reasoning
            
            priority, analysis_result, reasoning_result = process_email_with_enhanced_reasoning(
                parsed_email=processed_data,
                llm_client=llm_client,
                feedback_history=current_feedback,
                ml_pipeline=ml_pipeline,
                ml_label_encoder=ml_label_encoder,
                config=config,
                memory=memory,
                user_important_senders=user_important_senders,
                use_reasoning_engine=True
            )
            
            # Store reasoning result for UI display
            if reasoning_result:
                processed_data['reasoning_result'] = {
                    'priority': reasoning_result.priority,
                    'confidence': reasoning_result.confidence,
                    'explanation': reasoning_result.explanation,
                    'decision_factors': reasoning_result.decision_factors,
                    'reasoning_chain': [
                        {
                            'step_type': step.step_type,
                            'description': step.description,
                            'weight': step.weight,
                            'confidence': step.confidence,
                            'result': step.result if isinstance(step.result, (str, int, float, bool, type(None))) else str(step.result)
                        }
                        for step in reasoning_result.reasoning_chain
                    ],
                    'metadata': reasoning_result.metadata
                }
                logging.info(f"Reasoning result stored for email {processed_data.get('id')}: {reasoning_result.priority} (confidence: {reasoning_result.confidence:.1f}%)")
                
        except Exception as e:
            logging.error(f"Reasoning system failed, falling back to legacy classification: {e}")
            # Fall back to legacy system
            priority, analysis_result = classify_and_get_analysis_with_memory(
                parsed_email=processed_data,
                llm_client=llm_client,
                feedback_history=current_feedback,
                ml_pipeline=ml_pipeline,
                ml_label_encoder=ml_label_encoder,
                config=config,
                memory=memory,
                user_important_senders=user_important_senders
            )
    else:
        # Use legacy classification system
        priority, analysis_result = classify_and_get_analysis_with_memory(
            parsed_email=processed_data,
            llm_client=llm_client,
            feedback_history=current_feedback,
            ml_pipeline=ml_pipeline,
            ml_label_encoder=ml_label_encoder,
            config=config,
            memory=memory,
            user_important_senders=user_important_senders
        )
    processed_data['priority'] = priority # Always add priority
    
    # Ensure we always have analysis_result, even if rule-based shortcuts were taken
    if not analysis_result or not isinstance(analysis_result, dict):
        logging.info(f"No analysis result available for email {processed_data.get('id')}, performing explicit AI analysis...")
        try:
            analysis_result = analyze_email_with_context(llm_client, processed_data, config, memory)
            if analysis_result:
                logging.debug(f"Successfully obtained analysis result for email {processed_data.get('id')}: {analysis_result}")
            else:
                logging.warning(f"AI analysis failed for email {processed_data.get('id')}, using defaults")
        except Exception as e:
            logging.error(f"Error during explicit AI analysis for email {processed_data.get('id')}: {e}", exc_info=True)
            analysis_result = None
    
    # Store analysis results (now guaranteed to have been attempted)
    if analysis_result and isinstance(analysis_result, dict):
        # Store the complete AI analysis result
        processed_data['ai_analysis'] = analysis_result
        
        # Also store individual fields for backward compatibility
        processed_data['llm_urgency'] = analysis_result.get('urgency_score')
        processed_data['llm_purpose'] = analysis_result.get('purpose')
        processed_data['response_needed'] = analysis_result.get('response_needed', False)
        processed_data['estimated_time'] = analysis_result.get('estimated_time', 5)
        logging.debug(f"Email {processed_data.get('id')} analysis result added: {analysis_result}")
    else:
        # Even after explicit attempt, analysis failed - use defaults
        processed_data['ai_analysis'] = None
        processed_data['llm_urgency'] = None
        processed_data['llm_purpose'] = None
        processed_data['response_needed'] = False
        processed_data['estimated_time'] = 5
        logging.warning(f"Email {processed_data.get('id')} analysis completely failed, using defaults.")


    # 2. Generate summary for high priority emails
    summary_result = None
    summary_type_used = None
    # Only generate summaries for CRITICAL or HIGH priority emails
    if priority in [PRIORITY_CRITICAL, PRIORITY_HIGH]:
        logging.info(f"Priority is {priority}. Generating summary with memory for email {processed_data.get('id')}...")

        # --- REFINED Summary Type Selection ---
        summary_type = "standard" # Default to standard summary
        if analysis_result and analysis_result.get('purpose', '').lower() == "action request":
            summary_type = "action_focused" # Use action_focused only for action requests
            logging.info(f"Purpose is 'Action Request', selecting '{summary_type}' summary type.")
        else:
            logging.info(f"Purpose is not 'Action Request' or analysis missing, selecting '{summary_type}' summary type.")
        # --- END REFINED Selection ---

        # Call the summarization function
        summary_result = summarize_email_with_memory(
            llm_client=llm_client,
            email_data=processed_data,
            config=config,
            memory=memory,
            summary_type=summary_type # Use the selected type
        )
        summary_type_used = summary_type
        logging.debug(f"Email {processed_data.get('id')} summary generated (type: {summary_type}): {str(summary_result)[:100]}...")

    # Add summary results (even if None or generated for lower priorities in future)
    processed_data['summary'] = summary_result
    processed_data['summary_type'] = summary_type_used
    # --- END MODIFIED SECTION ---


    # 3. Generate action suggestions (only if analysis was successful)
    action_suggestions = [] # Default to empty list
    if analysis_result:
        logging.info(f"Generating action suggestions for email {processed_data.get('id')}...")
        action_suggestions = suggest_email_actions(
            llm_client=llm_client,
            email_data=processed_data,
            analysis_result=analysis_result, # Pass the dict here
            config=config,
            memory=memory
        )
        logging.debug(f"Email {processed_data.get('id')} action suggestions: {action_suggestions}")

    processed_data['action_suggestions'] = action_suggestions

    # 4. Generate proactive insights if reasoning system is enabled
    if use_reasoning and 'reasoning_result' in processed_data:
        try:
            from reasoning_integration import create_proactive_insights, get_autonomous_action_recommendations
            
            # Convert reasoning dict back to object for insights generation
            reasoning_result_dict = processed_data['reasoning_result']
            
            # Generate insights
            insights = create_proactive_insights(processed_data, None, memory)  # We pass None since we have dict format
            processed_data['insights'] = insights
            logging.info(f"Generated {len(insights.get('suggestions', []))} proactive insights for email {processed_data.get('id')}")
            
            # Generate autonomous action recommendations
            # Note: We'd need to reconstruct the ClassificationResult object here, but for now we'll use a simpler approach
            processed_data['autonomous_recommendations'] = []  # Placeholder for now
            
        except Exception as e:
            logging.warning(f"Failed to generate proactive insights: {e}")
            processed_data['insights'] = {'suggestions': [], 'patterns': [], 'actions': []}

    logging.info(f"Finished processing email {processed_data.get('id')}. Priority: {priority}, Actions: {len(action_suggestions)}")
    return processed_data

def save_calendar_token_to_gcs(creds, storage_client_instance, bucket_name, blob_name):
    """Saves calendar credentials token to GCS."""
    if not storage_client_instance or not bucket_name or not blob_name:
        logging.error("Missing GCS client, bucket, or blob name for saving calendar token.")
        return False
    try:
        creds_dict = {
            'token': creds.token,
            'refresh_token': creds.refresh_token,
            'token_uri': creds.token_uri,
            'client_id': creds.client_id,
            'client_secret': creds.client_secret,
            'scopes': creds.scopes
        }
        bucket = storage_client_instance.bucket(bucket_name)
        blob = bucket.blob(blob_name)
        blob.upload_from_string(json.dumps(creds_dict), content_type='application/json')
        logging.info(f"Calendar token saved successfully to gs://{bucket_name}/{blob_name}")
        return True
    except Exception as e:
        logging.error(f"Failed to save calendar token to GCS: {e}", exc_info=True)
        return False

def load_calendar_token_from_gcs(storage_client_instance, bucket_name, blob_name):
    """Loads calendar credentials token from GCS."""
    if not storage_client_instance or not bucket_name or not blob_name:
        logging.error("Missing GCS client, bucket, or blob name for loading calendar token.")
        return None
    try:
        bucket = storage_client_instance.bucket(bucket_name)
        blob = bucket.blob(blob_name)
        if not blob.exists():
            logging.info(f"Calendar token file not found at gs://{bucket_name}/{blob_name}")
            return None
        token_data = json.loads(blob.download_as_string())
        creds = Credentials.from_authorized_user_info(token_data, CALENDAR_SCOPES)
        logging.info(f"Calendar token loaded successfully from gs://{bucket_name}/{blob_name}")
        return creds
    except Exception as e:
        logging.error(f"Failed to load calendar token from GCS: {e}", exc_info=True)
        return None

def authenticate_calendar(credentials_path, storage_client_instance, token_gcs_bucket):
    """Handles OAuth 2.0 flow specifically for Google Calendar API."""
    creds = None
    calendar_token_gcs_path = os.environ.get(CALENDAR_TOKEN_GCS_PATH_ENV, DEFAULT_CALENDAR_TOKEN_FILENAME)

    # Try loading existing token from GCS
    creds = load_calendar_token_from_gcs(storage_client_instance, token_gcs_bucket, calendar_token_gcs_path)

    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            logging.info("Calendar credentials expired, attempting refresh...")
            try:
                creds.refresh(Request()) # Request() needs: from google.auth.transport.requests import Request
                logging.info("Calendar credentials refreshed successfully.")
                # Save the refreshed token back to GCS
                save_calendar_token_to_gcs(creds, storage_client_instance, token_gcs_bucket, calendar_token_gcs_path)
            except RefreshError as e:
                logging.error(f"Calendar authentication token has expired or been revoked: {e}")
                # Delete the invalid token from GCS to force re-authentication
                try:
                    bucket = storage_client_instance.bucket(token_gcs_bucket)
                    token_blob = bucket.blob(calendar_token_gcs_path)
                    if token_blob.exists():
                        token_blob.delete()
                        logging.info("Invalid Calendar token deleted from GCS - re-authentication required")
                except Exception as delete_error:
                    logging.warning(f"Could not delete invalid Calendar token from GCS: {delete_error}")
                creds = None # Force re-auth if refresh fails
            except Exception as e:
                logging.error(f"An unexpected error occurred during Calendar token refresh: {e}", exc_info=True)
                creds = None # Force re-auth if refresh fails
        else:
            # Initiate the OAuth flow (this part needs user interaction, tricky in GCF background)
            # This function is better suited for being called from the Streamlit UI context
            logging.info("No valid calendar credentials found or refresh failed. Manual authentication required.")
            # In a UI context, you would run the flow here:
            # flow = InstalledAppFlow.from_client_secrets_file(credentials_path, CALENDAR_SCOPES)
            # creds = flow.run_local_server(port=0) # Or other flow methods
            # save_calendar_token_to_gcs(creds, storage_client_instance, token_gcs_bucket, calendar_token_gcs_path)
            return None # Indicate that auth is needed

    # Build the Calendar service
    try:
        service = build_service('calendar', 'v3', credentials=creds)
        logging.info("Google Calendar service client created successfully.")
        return service
    except Exception as e:
        logging.error(f"Failed to build Google Calendar service: {e}", exc_info=True)
        return None

def get_calendar_service_legacy(storage_client_instance, token_gcs_bucket, credentials_path):
    """Gets an authenticated Google Calendar service client, returns None if auth needed."""
    creds = None
    calendar_token_gcs_path = os.environ.get(CALENDAR_TOKEN_GCS_PATH_ENV, DEFAULT_CALENDAR_TOKEN_FILENAME)
    creds = load_calendar_token_from_gcs(storage_client_instance, token_gcs_bucket, calendar_token_gcs_path)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            logging.info("Calendar token expired, attempting refresh...")
            try:
                # Need Request object from google.auth.transport.requests
                from google.auth.transport.requests import Request
                creds.refresh(Request())
                logging.info("Calendar token refreshed.")
                save_calendar_token_to_gcs(creds, storage_client_instance, token_gcs_bucket, calendar_token_gcs_path)
            except RefreshError as e:
                logging.error(f"Calendar authentication token has expired or been revoked: {e}")
                # Delete the invalid token from GCS to force re-authentication
                try:
                    bucket = storage_client_instance.bucket(token_gcs_bucket)
                    token_blob = bucket.blob(calendar_token_gcs_path)
                    if token_blob.exists():
                        token_blob.delete()
                        logging.info("Invalid Calendar token deleted from GCS - re-authentication required")
                except Exception as delete_error:
                    logging.warning(f"Could not delete invalid Calendar token from GCS: {delete_error}")
                return None # Refresh failed, needs re-auth
            except Exception as e:
                logging.error(f"An unexpected error occurred during Calendar token refresh: {e}", exc_info=True)
                return None # Refresh failed, needs re-auth
        else:
            logging.info("No valid calendar credentials found in GCS.")
            return None # No valid token

    # Build and return the service
    try:
        service = build_service('calendar', 'v3', credentials=creds)
        logging.info("Google Calendar service client retrieved.")
        return service
    except Exception as e:
        logging.error(f"Failed to build Google Calendar service from loaded creds: {e}", exc_info=True)
        return None

# --- Add this function to create events ---
def create_calendar_event(calendar_service, start_time, end_time, summary, description, recurrence_rule=None):
    """
    Creates an event on the user's primary Google Calendar.

    Args:
        calendar_service: Authenticated Google Calendar service object.
        start_time (datetime): Event start time (timezone-aware recommended).
        end_time (datetime): Event end time (timezone-aware recommended).
        summary (str): Event title.
        description (str): Event description.
        recurrence_rule (str, optional): RRULE string (e.g., 'RRULE:FREQ=DAILY;INTERVAL=1'). Defaults to None.

    Returns:
        dict: The created event object from the API, or None on failure.
    """
    # --- MODIFICATION START ---
    # Ensure start_time and end_time are timezone-aware (assume UTC if naive)
    # This helps ensure isoformat() includes timezone info, but API needs explicit field too
    if start_time.tzinfo is None:
        start_time = start_time.replace(tzinfo=timezone.utc)
    if end_time.tzinfo is None:
        end_time = end_time.replace(tzinfo=timezone.utc)

    event = {
        'summary': summary,
        'description': description,
        'start': {
            'dateTime': start_time.isoformat(),
            'timeZone': 'UTC',  # Explicitly specify the timezone for the API
        },
        'end': {
            'dateTime': end_time.isoformat(),
            'timeZone': 'UTC',  # Explicitly specify the timezone for the API
        },
        # Add reminders if desired (API structure)
        # 'reminders': {
        #     'useDefault': False,
        #     'overrides': [
        #         {'method': 'popup', 'minutes': 15},
        #     ],
        # },
    }
    if recurrence_rule:
        event['recurrence'] = [recurrence_rule]

    try:
        # Added more detailed logging including the times being sent
        logging.info(f"Creating calendar event: {summary} from {start_time.isoformat()} to {end_time.isoformat()} (UTC)")
        created_event = calendar_service.events().insert(calendarId='primary', body=event).execute()
        logging.info(f"Event created successfully: {created_event.get('htmlLink')}")
        return created_event
    except HttpError as error:
        logging.error(f"HttpError creating calendar event: {error}", exc_info=True)
        # Log the request body that failed (helps debugging)
        logging.error(f"Failed event body: {json.dumps(event)}")
        return None
    except Exception as e:
        logging.error(f"Unexpected error creating calendar event: {e}", exc_info=True)
        return None

def list_sent_emails(service, days_ago=14, max_results=50):
    """Lists message IDs of emails sent by the user within the last 'days_ago'."""
    if not service:
        logging.error("Gmail service not available for listing sent emails.")
        return []

    try:
        # Calculate cutoff date/time
        cutoff_timestamp = int((datetime.now(timezone.utc) - timedelta(days=days_ago)).timestamp())
        query = f'label:sent after:{cutoff_timestamp}'
        logging.info(f"Querying sent emails with: {query}")

        response = service.users().messages().list(
            userId='me',
            labelIds=['SENT'], # Explicitly use SENT label
            q=query,          # Use query for time filtering
            maxResults=max_results
        ).execute()

        messages = response.get('messages', [])
        logging.info(f"Found {len(messages)} sent emails within the last {days_ago} days (max {max_results}).")
        return messages # Returns list of {'id': '...', 'threadId': '...'}

    except HttpError as error:
        logging.error(f"HttpError listing sent emails: {error}", exc_info=True)
        return []
    except Exception as e:
        logging.error(f"Unexpected error listing sent emails: {e}", exc_info=True)
        return []

def check_thread_for_reply(service, thread_id, original_message_id):
    """
    Checks if a thread contains messages after the original sent message.

    Args:
        service: Authenticated Gmail service client.
        thread_id (str): The ID of the thread to check.
        original_message_id (str): The ID of the user's sent message in the thread.

    Returns:
        bool: True if a reply exists after the original message, False otherwise.
    """
    if not service or not thread_id or not original_message_id:
        return False # Cannot check without required info

    try:
        thread = service.users().threads().get(userId='me', id=thread_id, format='metadata').execute()
        messages = thread.get('messages', [])

        if len(messages) <= 1:
            return False # Only the original message exists

        original_message_found = False
        for message in messages:
            if message['id'] == original_message_id:
                original_message_found = True
            elif original_message_found:
                # Found a message *after* the original one in the thread list
                # Basic check: assume any subsequent message is a reply for simplicity
                # More robust check could involve looking at 'From' header != user's email
                logging.debug(f"Reply found in thread {thread_id} after message {original_message_id}")
                return True

        # If loop finishes and no message was found after the original
        return False

    except HttpError as error:
        # Handle specific errors like thread not found (404) gracefully
        if error.resp.status == 404:
            logging.warning(f"Thread {thread_id} not found while checking for reply.")
        else:
            logging.error(f"HttpError checking thread {thread_id} for reply: {error}", exc_info=True)
        return False # Assume no reply on error
    except Exception as e:
        logging.error(f"Unexpected error checking thread {thread_id} for reply: {e}", exc_info=True)
        return False # Assume no reply on error


# --- ADD THE NEW REVISION FUNCTION ---
def revise_email_draft(llm_client, original_draft, revision_instruction, original_email_data, config, memory=None):
    """
    Revises an existing email draft based on user instructions using the LLM.

    Args:
        llm_client: The LLM client.
        original_draft (str): The text of the draft to be revised.
        revision_instruction (str): The user's request for changes (e.g., "make it shorter").
        original_email_data (dict): Dictionary containing details of the original email being replied to.
        config (dict): Configuration dictionary.
        memory: Optional memory system instance.

    Returns:
        str: The revised email draft text or an error message.
    """
    if not llm_client:
        return "Error: LLM client not available for revision."
    if not original_draft:
        return "Error: No original draft provided for revision."
    if not revision_instruction:
        return "Error: No revision instruction provided."
    if not original_email_data:
        logging.warning("Revising draft without original email context. Quality may be reduced.")
        original_email_data = {} # Use empty dict if missing
    
    # Add the logging statement right here
    logging.debug(f"revise_email_draft received original_draft:\n---\n{original_draft}\n---\nInstruction: '{revision_instruction}'")
    
    # Get settings from config
    model_name = config['llm']['model_name']
    # Use response tokens/temp, maybe allow slightly more for revision?
    max_tokens = config['llm'].get('response_max_tokens', config['llm']['summary_max_tokens'] * 2)
    temperature = config['llm'].get('response_temperature', 0.7) # Keep same temp as drafting

    # Prepare context from original email
    sender = original_email_data.get('sender', 'Unknown')
    subject = original_email_data.get('subject', 'No Subject')
    original_body_snippet = (original_email_data.get('body_text', '')[:500] + '...') if original_email_data.get('body_text') else '[Original Body Unavailable]'

    # System prompt for revision task
    system_prompt = """You are an assistant that revises email drafts based on user instructions.
Your output MUST be plain text suitable for an email body. Do NOT include any HTML, Markdown, or other markup language unless the user explicitly asks you to generate markup.

Focus ONLY on applying the requested textual changes to the provided draft while maintaining a professional and appropriate tone for the context.
The 'Current Draft' provided to you might sometimes be an explanatory message from me (the assistant) rather than a user's email. In all cases, strictly apply the revision instruction to the 'Current Draft' text as provided.
Pay close attention to positional instructions (e.g., 'first sentence', 'second paragraph'). If an instruction is ambiguous, try your best to interpret the user's likely intent.

If a revision instruction is impossible for a text-based model to perform in plain text (e.g., asking to change colors, font styles, or play sounds) or is clearly nonsensical, you MUST politely state that you cannot perform that type of action on text and ask if there's a different way you can help revise the draft. Do NOT attempt to represent such requests with markup.

Otherwise,output ONLY the complete revised plain text email draft. Do not include explanations, apologies, or introductory phrases like "Here is the revised draft:".
Do not add placeholders like [Your Name] unless specifically asked."""



    # User prompt including original context, draft, and instruction
    user_prompt = f"""Please revise the following email draft based on my instruction.

Original Email Context (for reference):
- From: {sender}
- Subject: {subject}
- Body Snippet: {original_body_snippet}

Current Draft:
---
{original_draft}
---

My Revision Instruction: "{revision_instruction}"

Output ONLY the revised email draft text:"""

    # Call the LLM
    try:
        logging.info(f"Requesting email draft revision from Anthropic Claude ({model_name}). Instruction: '{revision_instruction}'")
        message = llm_client.messages.create(
            model=model_name,
            system=system_prompt,
            messages=[{"role": "user", "content": [{"type": "text", "text": user_prompt}]}],
            max_tokens=max_tokens,
            temperature=temperature
        )

        if message and message.content and len(message.content) > 0:
            revised_text = message.content[0].text.strip()
            if revised_text:
                logging.info("Successfully generated revised draft.")
                # Basic check to remove common placeholder if LLM ignores instruction
                revised_text = revised_text.replace("[Your Name]", "").strip()
                
                # --- HTML STRIPPING LOGIC (YOUR OPTION 1) ---
                if revised_text and ("<" in revised_text and ">" in revised_text): # Basic check for HTML
                    try:
                        from bs4 import BeautifulSoup # Ensure import is available
                        soup = BeautifulSoup(revised_text, "html.parser")
                        plain_text_revision = soup.get_text(separator="\n").strip()
                        if plain_text_revision != revised_text: 
                            logging.info("Stripped HTML from LLM revision output. Original: '%s', Stripped: '%s'", revised_text[:100], plain_text_revision[:100])
                            revised_text = plain_text_revision
                        elif not plain_text_revision.strip() and revised_text.strip(): 
                            logging.info("LLM revision was only markup. Treating as no valid text change. Original was: '%s'", revised_text[:100])
                            # If it was only markup, and stripping made it empty,
                            # we want the LLM to have ideally produced the apology.
                            # If it didn't, and just produced markup, revised_text will become empty.
                            # The UI layer will then show an empty draft, which is not ideal.
                            # Let's consider what to do if revised_text becomes empty *after stripping markup only*.
                            # For now, we'll let it be empty. The prompt should prevent this.
                            revised_text = plain_text_revision # which is empty or whitespace
                    except ImportError:
                        logging.warning("BeautifulSoup4 is not installed. Cannot strip HTML from revision. pip install beautifulsoup4")
                    except Exception as e_strip:
                        logging.error(f"Error stripping HTML from revision: {e_strip}", exc_info=True)
                # --- END HTML STRIPPING LOGIC ---
        
                return revised_text # This should be the final return for a successful-looking response
            else:
                logging.warning("LLM generated an empty revision string.")
                return "Error: Generated empty revision."
        else:
            logging.warning("No response content received from LLM for draft revision.")
            return "Error: No response received from LLM for revision."

    # --- Keep standard error handling ---
    except anthropic.APIConnectionError as e:
         logging.error(f"Anthropic API Connection Error during revision: {e}")
         return f"Error: API Connection Error ({e})"
    except anthropic.RateLimitError as e:
         logging.error(f"Anthropic Rate Limit Error during revision: {e}")
         return f"Error: Rate Limit Error ({e})"
    except anthropic.APIStatusError as e:
         logging.error(f"Anthropic API Status Error during revision: status_code={e.status_code}, response={e.response}")
         return f"Error: API Status Error ({e.status_code})"
    except Exception as e:
        logging.error(f"Error revising email draft: {type(e).__name__}: {e}", exc_info=True)
        return f"Error: Failed to revise draft: {type(e).__name__}"


def mark_emails_as_read(gmail_service, email_ids):
    """
    Mark a list of emails as read by removing the UNREAD label.
    
    Args:
        gmail_service: Authenticated Gmail API service instance
        email_ids: List of email IDs to mark as read
        
    Returns:
        Dict with success count and any errors
    """
    if not gmail_service:
        logging.error("Gmail service not provided for mark_emails_as_read")
        return {"success_count": 0, "errors": ["Gmail service not available"]}
    
    if not email_ids or not isinstance(email_ids, list):
        logging.warning("No email IDs provided to mark as read")
        return {"success_count": 0, "errors": ["No email IDs provided"]}
    
    success_count = 0
    errors = []
    
    for email_id in email_ids:
        try:
            # Remove UNREAD label to mark as read
            modify_body = {'removeLabelIds': ['UNREAD']}
            gmail_service.users().messages().modify(
                userId='me', 
                id=email_id, 
                body=modify_body
            ).execute()
            
            success_count += 1
            logging.info(f"Successfully marked email {email_id} as read")
            
        except HttpError as error:
            error_msg = f"Gmail API error for email {email_id}: {error.resp.status} - {error.content.decode()}"
            logging.error(error_msg, exc_info=True)
            errors.append(error_msg)
            
        except Exception as e:
            error_msg = f"Unexpected error marking email {email_id} as read: {str(e)}"
            logging.error(error_msg, exc_info=True)
            errors.append(error_msg)
    
    logging.info(f"mark_emails_as_read completed: {success_count} successful, {len(errors)} errors")
    
    return {
        "success_count": success_count,
        "errors": errors
    }


# --- New Email Action Functions ---

def archive_email(gmail_service, email_id):
    """
    Archive an email by removing it from INBOX.
    
    Args:
        gmail_service: Authenticated Gmail API service instance
        email_id: Email ID to archive
        
    Returns:
        Dict with success status and any error message
    """
    if not gmail_service:
        return {"success": False, "error": "Gmail service not available"}
    
    try:
        # Remove INBOX label to archive
        modify_body = {'removeLabelIds': ['INBOX']}
        gmail_service.users().messages().modify(
            userId='me', 
            id=email_id, 
            body=modify_body
        ).execute()
        
        logging.info(f"Successfully archived email {email_id}")
        return {"success": True, "error": None}
        
    except Exception as e:
        error_msg = f"Failed to archive email {email_id}: {e}"
        logging.error(error_msg, exc_info=True)
        return {"success": False, "error": error_msg}


def apply_label_to_email(gmail_service, email_id, label_name):
    """
    Apply a label to an email, creating the label if it doesn't exist.
    
    Args:
        gmail_service: Authenticated Gmail API service instance
        email_id: Email ID to label
        label_name: Name of the label to apply
        
    Returns:
        Dict with success status and any error message
    """
    if not gmail_service:
        return {"success": False, "error": "Gmail service not available"}
    
    try:
        # First, get or create the label
        label_id = get_or_create_label_id(gmail_service, label_name)
        if not label_id:
            return {"success": False, "error": f"Failed to get or create label: {label_name}"}
        
        # Apply the label
        modify_body = {'addLabelIds': [label_id]}
        gmail_service.users().messages().modify(
            userId='me', 
            id=email_id, 
            body=modify_body
        ).execute()
        
        logging.info(f"Successfully applied label '{label_name}' to email {email_id}")
        return {"success": True, "error": None}
        
    except Exception as e:
        error_msg = f"Failed to apply label '{label_name}' to email {email_id}: {e}"
        logging.error(error_msg, exc_info=True)
        return {"success": False, "error": error_msg}


def get_or_create_label_id(gmail_service, label_name):
    """
    Get the ID of a Gmail label, creating it if it doesn't exist.
    
    Args:
        gmail_service: Authenticated Gmail API service instance
        label_name: Name of the label
        
    Returns:
        str: Label ID, or None if failed
    """
    try:
        # Get existing labels
        results = gmail_service.users().labels().list(userId='me').execute()
        labels = results.get('labels', [])
        
        # Check if label already exists
        for label in labels:
            if label['name'] == label_name:
                return label['id']
        
        # Create new label
        label_object = {
            'name': label_name,
            'messageListVisibility': 'show',
            'labelListVisibility': 'labelShow'
        }
        
        created_label = gmail_service.users().labels().create(
            userId='me', 
            body=label_object
        ).execute()
        
        logging.info(f"Created new label: {label_name} with ID: {created_label['id']}")
        return created_label['id']
        
    except Exception as e:
        logging.error(f"Failed to get or create label '{label_name}': {e}", exc_info=True)
        return None


def mark_email_as_important(gmail_service, email_id):
    """
    Mark an email as important by adding the IMPORTANT label.
    
    Args:
        gmail_service: Authenticated Gmail API service instance
        email_id: Email ID to mark as important
        
    Returns:
        Dict with success status and any error message
    """
    if not gmail_service:
        return {"success": False, "error": "Gmail service not available"}
    
    try:
        # Add IMPORTANT label
        modify_body = {'addLabelIds': ['IMPORTANT']}
        gmail_service.users().messages().modify(
            userId='me', 
            id=email_id, 
            body=modify_body
        ).execute()
        
        logging.info(f"Successfully marked email {email_id} as important")
        return {"success": True, "error": None}
        
    except Exception as e:
        error_msg = f"Failed to mark email {email_id} as important: {e}"
        logging.error(error_msg, exc_info=True)
        return {"success": False, "error": error_msg}


def create_reply_draft(gmail_service, original_email_id, reply_content, reply_type="reply"):
    """
    Create a reply draft for an email.
    
    Args:
        gmail_service: Authenticated Gmail API service instance
        original_email_id: ID of the email being replied to
        reply_content: Content of the reply
        reply_type: "reply" or "reply_all"
        
    Returns:
        Dict with success status, draft ID, and any error message
    """
    if not gmail_service:
        return {"success": False, "error": "Gmail service not available", "draft_id": None}
    
    try:
        # Get the original email to extract headers
        original_email = gmail_service.users().messages().get(
            userId='me', 
            id=original_email_id,
            format='full'
        ).execute()
        
        # Extract headers
        headers = {}
        if 'payload' in original_email and 'headers' in original_email['payload']:
            for header in original_email['payload']['headers']:
                headers[header['name'].lower()] = header['value']
        
        # Create reply headers
        to_email = headers.get('from', '')
        subject = headers.get('subject', '')
        if not subject.lower().startswith('re:'):
            subject = f"Re: {subject}"
        
        # For reply_all, include CC recipients
        cc_emails = ""
        if reply_type == "reply_all":
            cc_list = []
            if 'cc' in headers:
                cc_list.append(headers['cc'])
            if 'to' in headers and headers['to'] != headers.get('from', ''):
                cc_list.append(headers['to'])
            cc_emails = ", ".join(cc_list)
        
        # Create the reply message
        reply_message = f"""To: {to_email}
Subject: {subject}
In-Reply-To: {headers.get('message-id', '')}
References: {headers.get('references', '')} {headers.get('message-id', '')}"""
        
        if cc_emails:
            reply_message += f"\nCc: {cc_emails}"
        
        reply_message += f"""

{reply_content}

---
This reply was created using Maia AI Assistant
"""
        
        # Create draft
        draft_body = {
            'message': {
                'threadId': original_email.get('threadId'),
                'raw': base64.urlsafe_b64encode(reply_message.encode()).decode()
            }
        }
        
        import base64
        draft = gmail_service.users().drafts().create(
            userId='me',
            body=draft_body
        ).execute()
        
        logging.info(f"Successfully created reply draft {draft['id']} for email {original_email_id}")
        return {"success": True, "error": None, "draft_id": draft['id']}
        
    except Exception as e:
        error_msg = f"Failed to create reply draft for email {original_email_id}: {e}"
        logging.error(error_msg, exc_info=True)
        return {"success": False, "error": error_msg, "draft_id": None}


def create_forward_draft(gmail_service, original_email_id, forward_to, forward_content, additional_message=""):
    """
    Create a forward draft for an email.
    
    Args:
        gmail_service: Authenticated Gmail API service instance
        original_email_id: ID of the email being forwarded
        forward_to: Email address to forward to
        forward_content: Original email content
        additional_message: Optional message to add before forwarded content
        
    Returns:
        Dict with success status, draft ID, and any error message
    """
    if not gmail_service:
        return {"success": False, "error": "Gmail service not available", "draft_id": None}
    
    try:
        # Get the original email
        original_email = gmail_service.users().messages().get(
            userId='me', 
            id=original_email_id,
            format='full'
        ).execute()
        
        # Extract headers
        headers = {}
        if 'payload' in original_email and 'headers' in original_email['payload']:
            for header in original_email['payload']['headers']:
                headers[header['name'].lower()] = header['value']
        
        subject = headers.get('subject', '')
        if not subject.lower().startswith('fwd:'):
            subject = f"Fwd: {subject}"
        
        # Create forward message
        forward_message = f"""To: {forward_to}
Subject: {subject}

{additional_message}

---------- Forwarded message ---------
From: {headers.get('from', 'Unknown')}
Date: {headers.get('date', 'Unknown')}
Subject: {headers.get('subject', 'Unknown')}
To: {headers.get('to', 'Unknown')}

{forward_content}

---
This forward was created using Maia AI Assistant
"""
        
        # Create draft
        import base64
        draft_body = {
            'message': {
                'raw': base64.urlsafe_b64encode(forward_message.encode()).decode()
            }
        }
        
        draft = gmail_service.users().drafts().create(
            userId='me',
            body=draft_body
        ).execute()
        
        logging.info(f"Successfully created forward draft {draft['id']} for email {original_email_id}")
        return {"success": True, "error": None, "draft_id": draft['id']}
        
    except Exception as e:
        error_msg = f"Failed to create forward draft for email {original_email_id}: {e}"
        logging.error(error_msg, exc_info=True)
        return {"success": False, "error": error_msg, "draft_id": None}


# === PHASE 9: AGENDA SYNTHESIS ENGINE ===

def get_calendar_events_for_date(calendar_service, target_date=None):
    """
    Retrieve calendar events for a specific date.
    
    Args:
        calendar_service: Authenticated Google Calendar service
        target_date: Date to retrieve events for (datetime.date). If None, uses today.
        
    Returns:
        List of calendar events for the specified date
    """
    if not calendar_service:
        logging.warning("Calendar service not available for event retrieval")
        return []
    
    try:
        if target_date is None:
            target_date = datetime.now().date()
        
        # Convert to datetime with timezone
        start_of_day = datetime.combine(target_date, datetime.min.time()).replace(tzinfo=timezone.utc)
        end_of_day = datetime.combine(target_date, datetime.max.time()).replace(tzinfo=timezone.utc)
        
        # Call the Calendar API
        events_result = calendar_service.events().list(
            calendarId='primary',
            timeMin=start_of_day.isoformat(),
            timeMax=end_of_day.isoformat(),
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        
        events = events_result.get('items', [])
        
        # Format events for agenda synthesis
        formatted_events = []
        for event in events:
            start = event['start'].get('dateTime', event['start'].get('date'))
            end = event['end'].get('dateTime', event['end'].get('date'))
            
            # Parse start time for display
            if 'T' in str(start):  # DateTime format
                start_dt = datetime.fromisoformat(start.replace('Z', '+00:00'))
                time_str = start_dt.strftime('%I:%M %p')
            else:  # All-day event
                time_str = 'All Day'
            
            formatted_events.append({
                'title': event.get('summary', 'No Title'),
                'time': time_str,
                'start_raw': start,
                'end_raw': end,
                'description': event.get('description', ''),
                'location': event.get('location', ''),
                'attendees': [attendee.get('email', '') for attendee in event.get('attendees', [])]
            })
        
        logging.info(f"Retrieved {len(formatted_events)} calendar events for {target_date}")
        return formatted_events
        
    except HttpError as error:
        logging.error(f"Calendar API error: {error}")
        return []
    except Exception as e:
        logging.error(f"Error retrieving calendar events: {e}", exc_info=True)
        return []


def build_daily_agenda(user_id: str, llm_manager: object):
    """
    Main orchestration function for building a personalized daily agenda.
    Synthesizes data from emails, tasks, and calendar events.
    
    Args:
        user_id: User identifier for personalized data retrieval
        llm_manager: Initialized HybridLLMManager instance with API keys
        
    Returns:
        Dict containing synthesized agenda data or error information
    """
    try:
        logging.info(f"Building daily agenda for user: {user_id}")
        
        # Load configuration
        with open('config.json', 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        # === 1. Fetch Critical Emails ===
        from database_utils import get_db
        
        # Get critical/high priority emails from last 24 hours
        yesterday = datetime.now(timezone.utc) - timedelta(days=1)
        
        emails_query = (get_db().collection('emails')
                       .where(filter=FieldFilter('priority', 'in', ['CRITICAL', 'HIGH']))
                       .where(filter=FieldFilter('timestamp', '>=', yesterday))
                       .order_by('timestamp', direction=firestore.Query.DESCENDING)
                       .limit(5))
        
        critical_emails = []
        for doc in emails_query.stream():
            email_data = doc.to_dict()
            critical_emails.append({
                'id': doc.id,
                'subject': email_data.get('subject', 'No Subject'),
                'sender': email_data.get('sender', 'Unknown'),
                'priority': email_data.get('priority', 'MEDIUM'),
                'timestamp': email_data.get('timestamp'),
                'body_snippet': email_data.get('body_text', '')[:200] + '...' if email_data.get('body_text') else ''
            })
        
        logging.info(f"Found {len(critical_emails)} critical/high priority emails")
        
        # === 2. Fetch Urgent Tasks ===
        from task_utils import get_tasks_for_user
        
        all_tasks = get_tasks_for_user(user_id)
        urgent_tasks = []
        today = datetime.now().date()
        
        for task in all_tasks:
            if task.get('status') != 'completed':
                deadline_str = task.get('deadline')
                is_urgent = False
                
                if deadline_str:
                    try:
                        # Parse deadline (assuming ISO format)
                        if isinstance(deadline_str, str):
                            deadline = datetime.fromisoformat(deadline_str.replace('Z', '+00:00')).date()
                        else:
                            deadline = deadline_str.date() if hasattr(deadline_str, 'date') else deadline_str
                        
                        # Mark as urgent if overdue or due today
                        if deadline <= today:
                            is_urgent = True
                    except (ValueError, AttributeError):
                        logging.warning(f"Could not parse deadline for task: {deadline_str}")
                
                # Also include tasks marked as high priority regardless of deadline
                if task.get('priority') == 'high' or is_urgent:
                    urgent_tasks.append({
                        'id': task.get('id'),
                        'description': task.get('task_description', 'No Description'),
                        'deadline': deadline_str,
                        'priority': task.get('priority', 'medium'),
                        'is_overdue': is_urgent and deadline < today if deadline_str else False,
                        'stakeholders': task.get('stakeholders', [])
                    })
        
        logging.info(f"Found {len(urgent_tasks)} urgent tasks")
        
        # === 3. Fetch Today's Calendar Events ===
        try:
            # Initialize storage client for calendar authentication
            from google.cloud import storage
            storage_client = storage.Client()
            
            # Get environment variables for calendar token
            token_gcs_bucket = os.environ.get('TOKEN_GCS_BUCKET', config.get('gcs', {}).get('bucket_name', ''))
            credentials_path = config.get('gmail', {}).get('credentials_path', 'credentials.json')
            
            if token_gcs_bucket:
                calendar_service = get_calendar_service(storage_client, token_gcs_bucket, credentials_path)
                if calendar_service:
                    calendar_events = get_calendar_events_for_date(calendar_service)
                else:
                    logging.warning("Calendar service unavailable - authentication required")
                    calendar_events = []
            else:
                logging.warning("GCS bucket name not configured - calendar events unavailable")
                calendar_events = []
        except Exception as calendar_error:
            logging.warning(f"Could not retrieve calendar events: {calendar_error}")
            calendar_events = []
        
        logging.info(f"Found {len(calendar_events)} calendar events")
        
        # === 4. Synthesize with AI ===
        try:
            # Use the injected LLM manager (no more ghost instance creation!)
            agenda_summary = llm_manager.synthesize_agenda_summary(
                emails=critical_emails,
                tasks=urgent_tasks, 
                events=calendar_events
            )
            
            if agenda_summary:
                logging.info("Successfully synthesized daily agenda")
                return {
                    'status': 'success',
                    'agenda': agenda_summary,
                    'raw_data': {
                        'emails_count': len(critical_emails),
                        'tasks_count': len(urgent_tasks),
                        'events_count': len(calendar_events)
                    }
                }
            else:
                logging.error("AI synthesis returned empty result")
                return {
                    'status': 'error',
                    'message': 'AI synthesis failed to generate agenda',
                    'raw_data': {
                        'emails_count': len(critical_emails),
                        'tasks_count': len(urgent_tasks),
                        'events_count': len(calendar_events)
                    }
                }
                
        except Exception as synthesis_error:
            logging.error(f"Error during AI synthesis: {synthesis_error}", exc_info=True)
            return {
                'status': 'error',
                'message': f'Synthesis error: {str(synthesis_error)}',
                'raw_data': {
                    'emails_count': len(critical_emails),
                    'tasks_count': len(urgent_tasks),
                    'events_count': len(calendar_events)
                }
            }
        
    except Exception as e:
        logging.error(f"Error building daily agenda: {e}", exc_info=True)
        return {
            'status': 'error',
            'message': f'Failed to build agenda: {str(e)}',
            'raw_data': {'emails_count': 0, 'tasks_count': 0, 'events_count': 0}
        }





