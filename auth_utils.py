# auth_utils.py - NEW AND ROBUST VERSION

import os
import json
import logging
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from google.cloud import storage
from google.auth.exceptions import RefreshError

# Streamlit import - only used in UI environment
try:
    import streamlit as st
    from google_auth_oauthlib.flow import InstalledAppFlow
    STREAMLIT_AVAILABLE = True
except ImportError:
    STREAMLIT_AVAILABLE = False

# --- Constants ---
SCOPES = ['https://www.googleapis.com/auth/gmail.modify', 'https://www.googleapis.com/auth/calendar.events.readonly']
CREDENTIALS_PATH = 'credentials.json'
TOKEN_GCS_BUCKET = os.environ.get('TOKEN_GCS_BUCKET')
TOKEN_GCS_PATH = 'token.json'

# --- Global clients (cached for performance) ---
storage_client = None

def _get_storage_client():
    """Initializes and returns a GCS client, caching it globally."""
    global storage_client
    if storage_client is None:
        storage_client = storage.Client()
    return storage_client

def _load_token_from_gcs():
    """Loads the token from Google Cloud Storage and validates scopes."""
    if not TOKEN_GCS_BUCKET:
        logging.warning("GCS_BUCKET_NAME environment variable not set. Cannot load token from GCS.")
        return None
    try:
        client = _get_storage_client()
        bucket = client.bucket(TOKEN_GCS_BUCKET)
        blob = bucket.blob(TOKEN_GCS_PATH)
        if blob.exists():
            token_str = blob.download_as_string()
            creds_data = json.loads(token_str)
            
            # CRITICAL: Check if the existing token has the correct scopes
            existing_scopes = set(creds_data.get('scopes', []))
            required_scopes = set(SCOPES)
            
            if existing_scopes != required_scopes:
                logging.warning(f"Token scope mismatch detected!")
                logging.warning(f"  Required scopes: {sorted(required_scopes)}")
                logging.warning(f"  Existing scopes: {sorted(existing_scopes)}")
                logging.warning(f"  Deleting invalid token to force re-authentication...")
                
                # Delete the invalid token
                blob.delete()
                logging.info(f"Invalid token deleted from gs://{TOKEN_GCS_BUCKET}/{TOKEN_GCS_PATH}")
                return None
            
            return Credentials.from_authorized_user_info(creds_data, SCOPES)
        else:
            logging.info(f"Token file not found at gs://{TOKEN_GCS_BUCKET}/{TOKEN_GCS_PATH}")
            return None
    except Exception as e:
        logging.error(f"Failed to load token from GCS: {e}", exc_info=True)
        return None

def _save_token_to_gcs(creds):
    """Saves the token to Google Cloud Storage with scope information."""
    if not TOKEN_GCS_BUCKET:
        logging.error("GCS_BUCKET_NAME environment variable not set. Cannot save token to GCS.")
        return
    try:
        client = _get_storage_client()
        bucket = client.bucket(TOKEN_GCS_BUCKET)
        blob = bucket.blob(TOKEN_GCS_PATH)
        
        # Ensure the token includes our unified scopes
        token_data = json.loads(creds.to_json())
        token_data['scopes'] = SCOPES  # Force our unified scopes
        
        blob.upload_from_string(json.dumps(token_data), content_type='application/json')
        logging.info(f"Token successfully saved to gs://{TOKEN_GCS_BUCKET}/{TOKEN_GCS_PATH}")
        logging.info(f"Saved with unified scopes: {SCOPES}")
    except Exception as e:
        logging.error(f"Failed to save token to GCS: {e}", exc_info=True)

def get_authenticated_services():
    """
    The single, unified function to get authenticated Google services.
    It handles token loading, refreshing, and saving in a non-interactive way suitable for both local and cloud environments.
    
    Returns:
        A tuple of (gmail_service, calendar_service). Returns (None, None) on failure.
    """
    creds = None
    
    # 1. Try to load token from GCS
    creds = _load_token_from_gcs()

    # 2. If token is loaded but expired, try to refresh it
    if creds and creds.expired and creds.refresh_token:
        logging.info("Credentials have expired. Attempting to refresh...")
        try:
            creds.refresh(Request())
            logging.info("Credentials refreshed successfully.")
            _save_token_to_gcs(creds) # Save the new, refreshed token
        except RefreshError as e:
            error_msg = str(e).lower()
            if 'invalid_scope' in error_msg:
                logging.error(f"Scope mismatch during token refresh. Deleting token to force re-authentication. Error: {e}")
                # Delete the invalid token from GCS
                try:
                    client = _get_storage_client()
                    bucket = client.bucket(TOKEN_GCS_BUCKET)
                    blob = bucket.blob(TOKEN_GCS_PATH)
                    if blob.exists():
                        blob.delete()
                        logging.info("Invalid scope token deleted from GCS")
                except Exception as delete_error:
                    logging.error(f"Failed to delete invalid token: {delete_error}")
            else:
                logging.error(f"Failed to refresh token. It may have been revoked. Re-authentication is required. Error: {e}")
            # In a server environment, we can't do more. We must fail.
            return None, None
        except Exception as e:
            logging.error(f"An unexpected error occurred during token refresh: {e}", exc_info=True)
            return None, None

    # 3. If there are no valid credentials at this point, we cannot proceed.
    if not creds or not creds.valid:
        logging.error("No valid credentials available. Cannot create API services. Please run the local authentication flow.")
        return None, None

    # 4. If we have valid credentials, build the services
    try:
        gmail_service = build('gmail', 'v1', credentials=creds)
        calendar_service = build('calendar', 'v3', credentials=creds)
        logging.info("Gmail and Calendar services created successfully.")
        return gmail_service, calendar_service
    except Exception as e:
        logging.error(f"Failed to build Google API services: {e}", exc_info=True)
        return None, None

def require_authentication():
    """
    Streamlit UI authentication function.
    Returns True if authenticated, False if authentication UI should be shown.
    """
    if not STREAMLIT_AVAILABLE:
        logging.error("Streamlit not available - cannot use require_authentication in non-UI environment")
        return False
    
    # Initialize session state
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False

    if not st.session_state.authenticated:
        st.title("🤖 Maia - Your Intelligent Email Assistant")
        st.markdown("---")
        
        # Check if we already have valid tokens
        gmail_service, calendar_service = get_authenticated_services()
        if gmail_service and calendar_service:
            st.session_state.authenticated = True
            st.rerun()
            return True
        
        # Show authentication UI
        st.markdown("### 🔐 Authentication Required")
        st.info("Please authenticate with Google to access your emails and calendar.")
        
        if st.button("🚀 Sign in with Google to Start"):
            try:
                # The interactive flow for the UI
                flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_PATH, SCOPES)
                creds = flow.run_local_server(port=0)
                
                if creds:
                    # Save the newly obtained token to GCS for the Cloud Function to use
                    _save_token_to_gcs(creds)
                    st.session_state.authenticated = True
                    st.success("Authentication successful! Redirecting...")
                    st.rerun() # Rerun the app to show the main dashboard
                else:
                    st.error("Authentication failed. Please try again.")
            except Exception as e:
                st.error(f"Authentication error: {str(e)}")
                logging.error(f"Authentication error: {e}", exc_info=True)
        
        # Stop the app from rendering further until authenticated
        return False

    # If we are here, it means we are authenticated.
    # Verify that services are still available
    gmail_service, calendar_service = get_authenticated_services()
    if not gmail_service:
        st.error("Failed to get authenticated services even after login. Please try signing in again.")
        st.session_state.authenticated = False
        st.rerun()
        return False

    return True