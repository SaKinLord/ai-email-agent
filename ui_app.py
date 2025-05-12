# -*- coding: utf-8 -*-
"""
Updated UI App for AI Email Agent with dark theme and enhanced capabilities
Includes all improvements suggested in feedback
"""
from dotenv import load_dotenv
# Load environment variables from .env file
load_dotenv()
import streamlit as st
import pyperclip
# --- REMOVED dark_theme import ---

# --- SET PAGE CONFIG FIRST ---
st.set_page_config(
    layout="wide",
    page_title="Maia - Your Email Agent",
    page_icon="✉️",
    initial_sidebar_state="collapsed"
)

# --- COPIED FROM dark_theme.py: Color constants ---
PRIMARY_COLOR = "#0078ff"  # Bright blue
SECONDARY_COLOR = "#0d47a1"  # Darker blue
BG_COLOR = "#0f1116"  # Very dark blue-black
CARD_BG_COLOR = "#1a1c23"  # Slightly lighter than bg
TEXT_COLOR = "#e0e0e0"  # Light gray for text
ACCENT_COLOR = "#3da5f4"  # Light blue for accents
SUCCESS_COLOR = "#00c853"  # Green for success messages
WARNING_COLOR = "#ffc107"  # Yellow/amber for warnings
ERROR_COLOR = "#f44336"  # Red for errors
MUTED_COLOR = "#8d8d8d"  # Gray for less important text

# --- COPIED FROM dark_theme.py: Agent appearance ---
AGENT_NAME = "Maia"
AGENT_TAGLINE = "Your intelligent email assistant"
AGENT_AVATAR = "https://api.dicebear.com/6.x/bottts/svg?seed=Maia&backgroundColor=0066cc" # Note: uses a fixed color, not PRIMARY_COLOR
USER_AVATAR = "https://api.dicebear.com/6.x/initials/svg?seed=User"

# --- COPIED FROM dark_theme.py: UI text constants ---
GREETING_MESSAGES = [
    "Hello! I'm Maia, your email assistant.",
    "Good to see you! How can I help with your emails today?",
    "Hi there! Ready to manage your inbox?",
    "Welcome back! Let's tackle your emails together."
]

THINKING_PHRASES = [
    "Analyzing your emails...",
    "Processing your request...",
    "Thinking...",
    "Working on that for you...",
    "Searching through your emails..."
]

# --- COPIED FROM dark_theme.py: CSS Styles ---
def get_css():
    """Returns the CSS for dark theme styling"""
    # Using PRIMARY_COLOR, SECONDARY_COLOR etc. directly as they are now global in this file
    return f"""
    <style>
    /* Base app styling */
    .stApp {{
        background-color: {BG_COLOR};
    }}

    /* Text styling */
    p, span, label, div, h1, h2, h3, h4, h5, h6, li {{
        color: {TEXT_COLOR} !important;
    }}

    h1 {{
        font-weight: 700;
        font-size: 2rem;
    }}

    h2 {{
        font-weight: 600;
        font-size: 1.5rem;
        margin-top: 1rem;
    }}

    h3 {{
        font-weight: 600;
        font-size: 1.2rem;
    }}

    /* Card styling */
    .card {{
        background-color: {CARD_BG_COLOR};
        border-radius: 10px;
        padding: 1.5rem;
        margin-bottom: 1rem;
        border: 1px solid rgba(255, 255, 255, 0.1);
    }}

    /* Button styling */
    .stButton>button {{
        background-color: {PRIMARY_COLOR};
        color: white !important;
        border-radius: 20px;
        padding: 0.5rem 1.2rem;
        border: none;
        font-weight: 500;
        transition: all 0.2s ease;
    }}

    .stButton>button:hover {{
        background-color: {ACCENT_COLOR};
        transform: translateY(-2px);
        box-shadow: 0 4px 8px rgba(0, 0, 0, 0.2);
    }}

    /* Data editor styling */
    .stDataFrame {{
        background-color: {CARD_BG_COLOR};
        border-radius: 10px;
        border: 1px solid rgba(255, 255, 255, 0.1);
    }}

    .stDataFrame th {{
        background-color: {SECONDARY_COLOR};
        color: white !important;
        font-weight: 600;
    }}

    .stDataFrame td {{
        color: {TEXT_COLOR} !important;
    }}

    /* Tab styling */
    .stTabs [data-baseweb="tab-list"] {{
        gap: 2rem;
    }}

    .stTabs [data-baseweb="tab"] {{
        height: 2.5rem;
        white-space: nowrap;
        font-size: 1rem;
        color: {TEXT_COLOR};
        border-radius: 4px 4px 0 0;
    }}

    .stTabs [aria-selected="true"] {{
        background-color: rgba(255, 255, 255, 0.05);
        color: {PRIMARY_COLOR} !important;
        font-weight: 600;
        border-bottom: 2px solid {PRIMARY_COLOR};
    }}

    /* Chat message styling */
    .chat-message {{
        padding: 1rem;
        border-radius: 0.8rem;
        margin-bottom: 1rem;
        display: flex;
        flex-direction: row;
        align-items: flex-start;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2);
        animation: fadeIn 0.5s;
    }}

    @keyframes fadeIn {{
        from {{ opacity: 0; transform: translateY(10px); }}
        to {{ opacity: 1; transform: translateY(0); }}
    }}

    .chat-message.user {{
        background-color: {CARD_BG_COLOR};
        border-left: 3px solid {TEXT_COLOR};
        margin-left: 2rem;
        margin-right: 0.5rem;
    }}

    .chat-message.assistant {{
        background-color: {SECONDARY_COLOR}; /* Using SECONDARY_COLOR for assistant */
        border-left: 3px solid {PRIMARY_COLOR};
        margin-right: 2rem;
        margin-left: 0.5rem;
    }}

    .chat-message .avatar {{
        width: 35px;
        height: 35px;
        border-radius: 50%;
        object-fit: cover;
        margin-right: 1rem;
    }}

    .chat-message .message {{
        flex-grow: 1;
        color: {TEXT_COLOR} !important;
    }}

    /* Input area */
    .stTextInput input {{
        background-color: {CARD_BG_COLOR};
        color: {TEXT_COLOR};
        border: 1px solid rgba(255, 255, 255, 0.2);
        padding: 0.5rem 1rem;
    }}

    /* Metric styling */
    .stMetric label {{
        color: {MUTED_COLOR} !important;
    }}

    .stMetric .css-s70wba, .stMetric .css-17a7n6g {{ /* These specific CSS classes might change with Streamlit versions */
        color: {TEXT_COLOR} !important;
    }}

    /* Info/warning/error message styling */
    .stAlert {{
        background-color: {CARD_BG_COLOR};
        color: {TEXT_COLOR};
        border-left-width: 4px;
    }}

    /* Widget container styling */
    .stWidgetCallout {{ /* This class might be for st.expander or similar */
        background-color: {CARD_BG_COLOR};
    }}

    /* ===== ENHANCED SUGGESTION CARD STYLING (from dark_theme.py) ===== */
    @keyframes fadeOut {{
        from {{ opacity: 1; transform: translateY(0); }}
        to {{ opacity: 0; transform: translateY(-10px); }}
    }}

    @keyframes slideIn {{
        from {{ transform: translateX(-20px); opacity: 0; }}
        to {{ transform: translateX(0); opacity: 1; }}
    }}

    @keyframes pulseHighlight {{
        0% {{ box-shadow: 0 0 0 rgba(255, 75, 75, 0); }} /* Assuming ERROR_COLOR is reddish */
        50% {{ box-shadow: 0 0 10px rgba(255, 75, 75, 0.5); }}
        100% {{ box-shadow: 0 0 0 rgba(255, 75, 75, 0); }}
    }}

    .suggestion-card {{
        background-color: {CARD_BG_COLOR};
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 10px;
        padding: 1.25rem;
        margin-bottom: 1.25rem;
        box-shadow: 0 4px 8px rgba(0, 0, 0, 0.2);
        animation: fadeIn 0.5s ease-out;
        transition: all 0.3s ease;
    }}

    .suggestion-card.priority-critical {{
        animation: fadeIn 0.5s ease-out, pulseHighlight 2s infinite;
    }}

    .suggestion-card.priority-high {{
        animation: slideIn 0.4s ease-out;
    }}

    .suggestion-card h4 {{ /* This was h3 in enhanced_proactive_agent, but h4 in dark_theme */
        font-size: 1.25rem;
        font-weight: 600;
        letter-spacing: 0.01rem;
        margin-top: 0;
        margin-bottom: 0.75rem;
        color: {TEXT_COLOR} !important;
    }}

    .suggestion-card p {{
        font-size: 0.95rem;
        line-height: 1.5;
        margin-bottom: 15px;
        color: {MUTED_COLOR} !important;
    }}

    .priority-indicator {{
        display: inline-block;
        width: 8px;
        height: 8px;
        border-radius: 50%;
        margin-right: 6px;
    }}

    .priority-critical .priority-indicator {{ background-color: {ERROR_COLOR}; }}
    .priority-high .priority-indicator {{ background-color: {WARNING_COLOR}; }}
    .priority-medium .priority-indicator {{ background-color: {PRIMARY_COLOR}; }}
    .priority-low .priority-indicator {{ background-color: {MUTED_COLOR}; }}

    .suggestion-card .button-container {{
        display: flex;
        gap: 10px;
        margin-top: 1rem;
    }}

    .suggestion-card .stButton>button {{
        font-weight: 500;
        padding: 0.4rem 1rem;
        border-radius: 20px;
        transition: all 0.2s ease;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
    }}

    .suggestion-card .stButton>button:hover {{
        transform: translateY(-2px);
        box-shadow: 0 4px 8px rgba(0, 0, 0, 0.2);
    }}

    .suggestion-card.dismissing {{
        animation: fadeOut 0.3s ease-in forwards;
    }}

    .suggestion-card:hover {{
        transform: translateY(-2px);
        box-shadow: 0 6px 12px rgba(0, 0, 0, 0.3);
    }}

    .quick-action-btn {{
        background-color: rgba(255, 255, 255, 0.1);
        color: {PRIMARY_COLOR};
        border: 1px solid {PRIMARY_COLOR};
        border-radius: 20px;
        padding: 0.5rem 1rem;
        font-size: 0.9rem;
        cursor: pointer;
        transition: all 0.2s;
        display: flex;
        align-items: center;
        justify-content: center;
    }}

    .quick-action-btn:hover {{
        background-color: {PRIMARY_COLOR}33; /* Assuming PRIMARY_COLOR is hex */
    }}

    .suggestion-count {{
        display: inline-block;
        background-color: rgba(255, 255, 255, 0.1);
        border-radius: 12px;
        padding: 0.1rem 0.5rem;
        font-size: 0.8rem;
        margin-left: 0.5rem;
    }}

    .success-text {{ color: {SUCCESS_COLOR} !important; }}
    .email-count {{ color: {SUCCESS_COLOR} !important; font-weight: 500; }}

    footer {{
        color: {MUTED_COLOR};
        font-size: 0.8rem;
        text-align: center;
        margin-top: 2rem;
        padding-top: 1rem;
        border-top: 1px solid rgba(255, 255, 255, 0.05);
    }}

    .stChatInput {{
        background-color: {CARD_BG_COLOR};
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 20px;
    }}
    </style>
    """
# --- END COPIED CSS ---

st.markdown(get_css(), unsafe_allow_html=True) # Apply the CSS
# Now import everything else
import pandas as pd
import joblib
from google.cloud import firestore
from google.cloud import storage
from google.cloud import secretmanager
import os
import logging
from datetime import datetime, timezone, timedelta
import time
import json
import re
import sys
import random

from googleapiclient.errors import HttpError
from googleapiclient.discovery import build as build_service # Add this
from google.oauth2.credentials import Credentials # Add this
from google.auth.transport.requests import Request # Add this
import tempfile
import functions_framework
import html
from google_auth_oauthlib.flow import InstalledAppFlow
from urllib.parse import quote
import database_utils
from database_utils import request_email_action
import plotly.express as px
import anthropic
from google.api_core import exceptions as google_exceptions
from agent_memory import AgentMemory
from enhanced_proactive_agent import ProactiveAgent
from agent_logic import (
    load_config, authenticate_gmail, get_unread_email_ids,
    get_email_details, parse_email_content,
    # PRIORITY_CRITICAL, PRIORITY_HIGH, # Defined locally now
    process_email_with_memory,
    suggest_email_actions,
    generate_email_response, revise_email_draft, # Added revise_email_draft
    summarize_email_with_memory,
    analyze_email_with_context,
    authenticate_calendar,
    get_calendar_service,
    save_calendar_token_to_gcs,
    CALENDAR_SCOPES,
    CALENDAR_TOKEN_GCS_PATH_ENV,
    DEFAULT_CALENDAR_TOKEN_FILENAME
)



# --- Define constants directly instead of importing from dark_theme ---
# AGENT_COLOR = "#0078ff" # Replaced by PRIMARY_COLOR
# AGENT_SECONDARY_COLOR = "#0d47a1" # Replaced by SECONDARY_COLOR
PRIORITY_CRITICAL = "CRITICAL" # Keep these specific priority constants
PRIORITY_HIGH = "HIGH"
PRIORITY_MEDIUM = "MEDIUM"
PRIORITY_LOW = "LOW"

# Add a key for storing suggestions
SUGGESTIONS_STATE_KEY = "current_suggestions_list"
LAST_DF_HASH_KEY = "last_email_df_hash" # To detect data changes


# Chart colors for visualization (using the new color constants)
PRIORITY_COLORS_CHART = { # Renamed to avoid conflict if PRIORITY_COLORS was used elsewhere
    'CRITICAL': ERROR_COLOR,
    'HIGH': WARNING_COLOR,
    'MEDIUM': SUCCESS_COLOR, # Or another distinct color like ACCENT_COLOR
    'LOW': PRIMARY_COLOR,    # Or MUTED_COLOR
    'N/A': MUTED_COLOR
}

PURPOSE_COLORS_CHART = { # Renamed
    'Action Request': WARNING_COLOR,
    'Question': ERROR_COLOR,
    'Information': SUCCESS_COLOR,
    'Meeting Invite': PRIMARY_COLOR,
    'Promotion': ACCENT_COLOR, # Example, choose distinct colors
    'Social': "#00cccc",          # Teal (can be defined as a constant too)
    'Notification': WARNING_COLOR, # Or a lighter yellow
    'Unknown': MUTED_COLOR
}

# --- Basic Logging Setup ---
log_format = '%(asctime)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s'
# logging.basicConfig(level=logging.DEBUG, format=log_format, stream=sys.stdout, force=True) # Already set
# Ensure logging level is appropriate
logger = logging.getLogger()
logger.setLevel(logging.DEBUG) # Set to INFO or DEBUG as needed

# --- Firestore Collection Names ---
EMAILS_COLLECTION = "emails"
FEEDBACK_COLLECTION = "feedback"
STATE_COLLECTION = "agent_state"
ACTION_REQUESTS_COLLECTION = "action_requests"

# --- Constants ---
PRIORITY_OPTIONS = ["CRITICAL", "HIGH", "MEDIUM", "LOW"]
DISPLAY_OPTIONS = ["N/A"] + PRIORITY_OPTIONS
PURPOSE_OPTIONS = ["Action Request", "Information", "Question", "Meeting Invite", "Promotion", "Social", "Notification", "Unknown"]
EDITOR_STATE_KEY = "email_editor"
ORIGINAL_DF_KEY = "original_emails_df"
CHAT_HISTORY_KEY = "chat_messages"
USER_PROFILE_KEY = "user_profile"
INSIGHTS_KEY = "email_insights"
PROCESSED_FEEDBACK_INDICES_KEY = "processed_feedback_indices_session"
PENDING_FEEDBACK_KEY = "pending_feedback_list"
FEEDBACK_SUCCESS_INFO_KEY = "feedback_success_info"
LAST_QUERY_KEY = "last_query"
INITIAL_RUN_KEY = "initial_run_occurred"
ANIMATION_STATE_KEY = "animation_state"
CURRENT_TAB_KEY = "current_tab"

# --- Helper Functions ---
def get_time_based_greeting():
    """Return a greeting based on time of day"""
    hour = datetime.now().hour
    if hour < 12:
        return "Good morning!"
    elif hour < 17:
        return "Good afternoon!"
    else:
        return "Good evening!"

def get_random_greeting():
    """Return a random greeting from the list"""
    return random.choice(GREETING_MESSAGES)

def get_random_thinking():
    """Return a random thinking phrase"""
    return random.choice(THINKING_PHRASES)

AFFIRMATIVE_RESPONSES = {"yes", "yep", "ok", "okay", "sure", "please", "do it", "analyze it", "i would like", "yes i would like", 'summarize', 'summarize it'}
def is_affirmative(query):
    """Checks if a query is a likely affirmative response."""
    return query.strip().lower() in AFFIRMATIVE_RESPONSES

# --- NEW Helper Function for Gmail Compose URL ---
def _create_gmail_compose_link(recipient, subject, body):
    """Creates a URL to open Gmail compose window with pre-filled fields."""
    if not recipient: return None

    base_url = "https://mail.google.com/mail/?view=cm&fs=1"

    # Prepare subject (handle Re: prefix)
    subject_prefix = "Re: "
    if isinstance(subject, str) and subject.lower().startswith("re:"):
         subject_prefix = ""
    elif subject is None:
        subject = ""
    full_subject = f"{subject_prefix}{subject}"

    # URL Encode parameters
    encoded_to = quote(recipient)
    encoded_su = quote(full_subject)
    encoded_body = quote(body if body else "")

    # Construct the final URL
    compose_url = f"{base_url}&to={encoded_to}&su={encoded_su}&body={encoded_body}"
    return compose_url

# --- Initialize session state variables ---
if PROCESSED_FEEDBACK_INDICES_KEY not in st.session_state:
    st.session_state[PROCESSED_FEEDBACK_INDICES_KEY] = set()
    
if PENDING_FEEDBACK_KEY not in st.session_state:
    st.session_state[PENDING_FEEDBACK_KEY] = []
    
if FEEDBACK_SUCCESS_INFO_KEY not in st.session_state:
    st.session_state[FEEDBACK_SUCCESS_INFO_KEY] = None
    
if CHAT_HISTORY_KEY not in st.session_state:
    welcome_message = f"{get_time_based_greeting()} {get_random_greeting()}"
    st.session_state[CHAT_HISTORY_KEY] = [
        {
            "role": "assistant", 
            "content": welcome_message,
            "context": {"hint": "greeting_help_displayed", "data": None}
        }
    ]
    
if ORIGINAL_DF_KEY not in st.session_state:
    st.session_state[ORIGINAL_DF_KEY] = pd.DataFrame()
    
if LAST_QUERY_KEY not in st.session_state:
    st.session_state[LAST_QUERY_KEY] = ""
    
#if INITIAL_RUN_KEY not in st.session_state:
    #st.session_state[INITIAL_RUN_KEY] = False
    
if ANIMATION_STATE_KEY not in st.session_state:
    st.session_state[ANIMATION_STATE_KEY] = {"is_typing": False, "current_text": ""}
    
if USER_PROFILE_KEY not in st.session_state:
    st.session_state[USER_PROFILE_KEY] = {
        "first_seen": datetime.now(),
        "last_active": datetime.now(),
        "total_interactions": 0,
        "feedback_given": 0,
        "preferences": {}
    }
    
if "dismissed_suggestions" not in st.session_state:
    st.session_state.dismissed_suggestions = set()

if CURRENT_TAB_KEY not in st.session_state:
    st.session_state[CURRENT_TAB_KEY] = 0
    
# --- Additional session state vars for agent context and modes ---
if "conversation_context" not in st.session_state:
    st.session_state["conversation_context"] = {
        "last_topics": [],
        "email_context": None,
        "current_task": None
    }

if "autonomous_mode" not in st.session_state:
    st.session_state["autonomous_mode"] = False

if "agent_thinking" not in st.session_state:
    st.session_state["agent_thinking"] = False

if "drafts" not in st.session_state:
    st.session_state["drafts"] = []

# Add a URL parameter handler for reset
reset_param = st.query_params.get("reset", False)
if str(reset_param).lower() == "true": # Daha sağlam kontrol
    st.info("Resetting application state based on URL parameter...")
    reset_occurred = False
    # Clear relevant state
    if "dismissed_suggestions" in st.session_state:
        st.session_state.dismissed_suggestions = set()
        reset_occurred = True
    # --- DİKKAT: Sabit isimlerini kontrol edin! ---
    if SUGGESTIONS_STATE_KEY in st.session_state: # Kodunuzda tanımlı olan sabit
        del st.session_state[SUGGESTIONS_STATE_KEY]
        reset_occurred = True
    if LAST_DF_HASH_KEY in st.session_state: # Kodunuzda tanımlı olan sabit
        del st.session_state[LAST_DF_HASH_KEY]
        reset_occurred = True

    if reset_occurred:
        st.success("State reset completed via URL parameter.")
        # İsteğe bağlı: Sayfanın yeniden yüklenmesini tetikleyebilirsiniz
        # st.experimental_rerun()
    else:
         st.warning("Reset requested via URL, but no relevant state found to clear.")
# --- Firestore Client Initialization ---
@st.cache_resource
def get_firestore_client():
    # ... (implementation as before) ...
    try:
        db_client = firestore.Client()
        logging.info("Firestore client initialized successfully.")
        return db_client
    except Exception as e:
        logging.critical(f"Failed to initialize Firestore client: {e}", exc_info=True)
        st.error(f"Fatal Error: Could not connect to Firestore database. Please check credentials and configuration. Error: {e}")
        return None # Return None on failure

db = get_firestore_client()
if db is None:
    st.stop()
# --- Add global or cached storage client for UI context if needed ---
@st.cache_resource
def get_gcs_client_ui():
    try:
        client = storage.Client()
        logging.info("GCS client initialized for UI.")
        return client
    except Exception as e:
        logging.error(f"Failed to initialize GCS client for UI: {e}", exc_info=True)
        st.error("Could not connect to Google Cloud Storage.")
        return None

gcs_client_ui = get_gcs_client_ui()
# --- Make sure gcs_client_ui is checked ---
if gcs_client_ui is None:
    # Decide how to handle this - maybe stop or disable GCS features?
    logging.warning("GCS Client for UI failed to initialize. GCS-dependent features may fail.")
    # st.stop() # Or just let it continue with warnings

# --- Initialize the memory and proactive agent systems ---
@st.cache_resource
def initialize_agent_memory(_db_client=None, user_id="default_user"):
    """Initialize and return the agent memory system"""
    try:
        memory = AgentMemory(db_client=_db_client, user_id=user_id)
        logging.info("Agent memory system initialized successfully")
        return memory
    except Exception as e:
        logging.error(f"Failed to initialize agent memory: {e}", exc_info=True)
        st.warning("Could not initialize full agent memory. Using basic instance.")
        return AgentMemory(db_client=None, user_id=user_id)

@st.cache_resource
def initialize_proactive_agent(_db_client=None, _memory=None, user_id="default_user", _llm_client=None, _config=None, _gmail_service=None): 
    """Initialize and return the proactive agent system"""
    try:
        # Pass the new arguments to the ProactiveAgent constructor
        agent = ProactiveAgent(db_client=_db_client, memory=_memory, user_id=user_id, llm_client=_llm_client, config=_config, gmail_service=_gmail_service)
        logging.info("Proactive agent initialized successfully")
        return agent
    except Exception as e:
        logging.error(f"Failed to initialize proactive agent: {e}", exc_info=True)
        st.warning("Could not initialize full proactive agent. Using basic instance.")
        # Return a basic agent instance, passing dependencies if safe
        return ProactiveAgent(db_client=None, memory=_memory, user_id=user_id, llm_client=_llm_client, config=_config)


# --- Load UI Config ---
@st.cache_data
def load_ui_config(filepath="config.json"):
    # ... (implementation as before) ...
    try:
        with open(filepath, 'r') as f:
            config_data = json.load(f)
        # Basic validation
        if not isinstance(config_data, dict) or 'llm' not in config_data:
             raise ValueError("Config file is missing or invalid.")
        return config_data
    except Exception as e:
        logging.error(f"Failed to load config.json for UI: {e}")
        st.error(f"Error loading configuration file ({filepath}). Some features might not work. Error: {e}")
        return None # Return None on failure

ui_config = load_ui_config()
if ui_config is None:
    st.stop() # Stop if config loading failed

# --- Initialize LLM Client (Add this section if not already present) ---
@st.cache_resource
def initialize_llm_client(config):
    """Initializes the LLM client based on config."""
    try:
        if config['llm']['provider'] == 'anthropic':
            api_key = os.environ.get(config['llm']['api_key_env_var'])
            if not api_key:
                # Try fetching from secrets if running in GCF/Cloud Run context (optional)
                try:
                    from google.cloud import secretmanager
                    secret_client = secretmanager.SecretManagerServiceClient()
                    secret_name = os.environ.get('ANTHROPIC_SECRET_NAME') # Use env var for secret name
                    if secret_name:
                        response = secret_client.access_secret_version(name=secret_name)
                        api_key = response.payload.data.decode("UTF-8")
                        logging.info("Fetched Anthropic key from Secret Manager.")
                    else:
                         raise ValueError(f"Environment variable '{config['llm']['api_key_env_var']}' not set, and ANTHROPIC_SECRET_NAME not set for fallback.")
                except Exception as secret_err:
                     logging.error(f"Failed to get API key from env var or secrets: {secret_err}")
                     raise ValueError(f"Anthropic API key not found. Set {config['llm']['api_key_env_var']} environment variable or configure secrets.")

            client = anthropic.Anthropic(api_key=api_key)
            logging.info(f"Anthropic client initialized for model: {config['llm']['model_name']}")
            return client
        else:
            raise ValueError(f"Unsupported LLM provider: {config['llm']['provider']}")
    except Exception as e:
        logging.critical(f"Failed to initialize LLM client: {e}", exc_info=True)
        st.error(f"Fatal Error: Could not initialize the Language Model client. Please check API keys and configuration. Error: {e}")
        return None

llm_client = initialize_llm_client(ui_config)
if llm_client is None:
    st.stop() # Stop if LLM client fails

# --- Add/Modify Gmail Service Initialization for UI ---
@st.cache_resource(ttl=3600) # Cache for an hour, or adjust as needed
def get_gmail_service_ui(config, _gcs_client):
    """Authenticates and returns the Gmail service for the UI."""
    if not config or not _gcs_client:
        st.error("Cannot authenticate Gmail: Missing configuration or GCS client.")
        return None

    # Get GCS bucket/path details (ensure these env vars are set)
    token_gcs_bucket = os.environ.get('GCS_BUCKET_NAME')
    token_gcs_path = os.environ.get('TOKEN_GCS_PATH', 'gmail_token.json') # Default from config?

    if not token_gcs_bucket:
        st.error("GCS_BUCKET_NAME environment variable not set for Gmail token.")
        return None

    logging.info("UI: Attempting to authenticate Gmail service...")
    try:
        service = authenticate_gmail(
            token_gcs_bucket=token_gcs_bucket,
            token_gcs_path=token_gcs_path,
            credentials_path=config['gmail']['credentials_path'],
            scopes=config['gmail']['scopes'],
            storage_client_instance=_gcs_client
        )
        if service:
            logging.info("UI: Gmail authentication successful.")
            return service
        else:
            # This indicates auth failed, likely needs interactive flow
            # In a real UI, you might redirect to an auth page or show a button
            st.warning("Gmail authentication failed. Please ensure you have authenticated via the backend or CLI first.")
            logging.error("UI: Gmail authentication returned None.")
            return None
    except Exception as e:
        st.error(f"Error during Gmail authentication: {e}")
        logging.error(f"UI: Gmail authentication error: {e}", exc_info=True)
        return None

# --- Initialize Gmail Service ---
# This needs to happen after config and gcs_client_ui are initialized
gmail_service_ui = None
if ui_config and gcs_client_ui:
    gmail_service_ui = get_gmail_service_ui(ui_config, gcs_client_ui)
# We might not want to st.stop() here, allow app to run with limited features
if gmail_service_ui is None:
     st.warning("Could not initialize Gmail connection. Features requiring Gmail access (like follow-up checks) will be unavailable.", icon="⚠️")

# --- Initialize Memory and Agent (Pass dependencies) ---
memory = initialize_agent_memory(_db_client=db, user_id="default_user")
proactive_agent = initialize_proactive_agent(
    _db_client=db,
    _memory=memory,
    user_id="default_user",
    _llm_client=llm_client,
    _config=ui_config,
    _gmail_service=gmail_service_ui
)

# --- Helper Functions ---
def _get_sender_key(sender):
    if not isinstance(sender, str): return None
    match = re.search(r'<(.+?)>', sender)
    if match: return match.group(1).lower()
    sender_clean = sender.strip().lower()
    if '@' in sender_clean and '.' in sender_clean.split('@')[-1]: return sender_clean
    logging.warning(f"Could not extract valid email key from sender: {sender}")
    return None

def _extract_email_address(sender_string):
    if not isinstance(sender_string, str): return None
    match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', sender_string)
    if match: return match.group(0)
    # If no standard email found, return the original string cleaned a bit
    # This might handle cases where the sender is just a name
    return re.sub(r'[<>"]', '', sender_string).strip() if sender_string else None

def display_chat_message(role, content, animation=False):
    """Display a chat message with avatar and styling"""
    # Uses AGENT_AVATAR, USER_AVATAR defined above
    display_content = str(content) if content else ""
    avatar_url = USER_AVATAR if role == "user" else AGENT_AVATAR
    message_class = "user" if role == "user" else "assistant"

    if animation and role == "assistant":
        st.session_state[ANIMATION_STATE_KEY]["is_typing"] = True
        st.session_state[ANIMATION_STATE_KEY]["current_text"] = ""
        placeholder = st.empty()
        full_text = display_content
        current_display_text = ""
        for i in range(min(50, len(full_text))):
            current_display_text = full_text[:i+1]
            placeholder.markdown(f"""
            <div class="chat-message {message_class}">
                <img src="{avatar_url}" class="avatar">
                <div class="message">{current_display_text}▌</div>
            </div>
            """, unsafe_allow_html=True)
            time.sleep(0.02)
        placeholder.markdown(f"""
        <div class="chat-message {message_class}">
            <img src="{avatar_url}" class="avatar">
            <div class="message">{display_content}</div>
        </div>
        """, unsafe_allow_html=True)
        st.session_state[ANIMATION_STATE_KEY]["is_typing"] = False
    else:
        st.markdown(f"""
        <div class="chat-message {message_class}">
            <img src="{avatar_url}" class="avatar">
            <div class="message">{display_content}</div>
        </div>
        """, unsafe_allow_html=True)

def display_agent_header():
    """Display agent header with logo and tagline"""
    # Uses AGENT_AVATAR, AGENT_NAME, AGENT_TAGLINE, PRIMARY_COLOR defined above
    col1, col2 = st.columns([1, 5])
    with col1:
        st.image(AGENT_AVATAR, width=80)
    with col2:
        st.markdown(f"<h1 style='color:{PRIMARY_COLOR};margin-bottom:0;'>{AGENT_NAME}</h1>", unsafe_allow_html=True)
        st.markdown(f"<p style='color:rgba(255,255,255,0.7);margin-top:0;'>{AGENT_TAGLINE}</p>", unsafe_allow_html=True)

# --- Feedback Submission Function ---
def submit_feedback_to_firestore(email_id, original_priority, corrected_priority=None, corrected_purpose=None, sender=None, feedback_type="priority"):
    """Submit feedback to Firestore with enhanced support for purpose corrections"""
    logging.info(f"Attempting to submit {feedback_type} feedback for Email ID: {email_id}")
    if not db:
        logging.error("Firestore client not available in submit_feedback_to_firestore.")
        return False
    
    # Validate input data
    if not email_id:
        logging.warning(f"Invalid feedback input: missing email_id")
        return False
        
    # Different validation based on feedback type
    if feedback_type == "priority":
        if not corrected_priority or corrected_priority == "N/A":
            logging.warning(f"Invalid priority feedback: corrected_priority={corrected_priority}")
            return False
        if corrected_priority not in PRIORITY_OPTIONS:
            logging.error(f"Corrected priority '{corrected_priority}' is not a valid option.")
            return False
    elif feedback_type == "purpose":
        if not corrected_purpose or corrected_purpose == "Unknown":
            logging.warning(f"Invalid purpose feedback: corrected_purpose={corrected_purpose}")
            return False
    
    try:
        sender_key = _get_sender_key(sender) if sender else None
        feedback_ref = db.collection(FEEDBACK_COLLECTION).document()
        
        # Base feedback data
        data_to_set = {
            'email_id': email_id,
            'original_priority': original_priority,
            'feedback_timestamp': firestore.SERVER_TIMESTAMP,
            'sender_key': sender_key,
            'source': 'UI',
            'feedback_type': feedback_type
        }
        
        # Add specific feedback fields based on type
        if feedback_type == "priority" and corrected_priority:
            data_to_set['corrected_priority'] = corrected_priority
        
        if feedback_type == "purpose" and corrected_purpose:
            data_to_set['corrected_purpose'] = corrected_purpose
        
        feedback_ref.set(data_to_set)
        logging.info(f"Firestore set() called for {feedback_type} feedback on {email_id}.")
        
        # Update user profile stats
        if USER_PROFILE_KEY in st.session_state:
            st.session_state[USER_PROFILE_KEY]["feedback_given"] += 1
        
        return True
    except Exception as e:
        logging.error(f"Error submitting feedback for {email_id}: {e}", exc_info=True)
        return False

# --- Data Fetching Function ---
@st.cache_data(ttl=60)
def fetch_recent_emails(limit=50):
    if not db: return pd.DataFrame()
    emails_list = []
    try:
        logging.info(f"Fetching up to {limit} recent emails from Firestore...")
        query = db.collection(EMAILS_COLLECTION)\
                  .order_by('processed_timestamp', direction=firestore.Query.DESCENDING)\
                  .limit(limit)
        results = query.stream()
        for doc in results:
            email_data = doc.to_dict()
            email_data['id'] = doc.id
            ts = email_data.get('processed_timestamp')
            processed_at_str = 'N/A'
            if ts and isinstance(ts, datetime):
                 if ts.tzinfo is None: ts = ts.replace(tzinfo=timezone.utc)
                 try: processed_at_str = ts.astimezone().strftime('%Y-%m-%d %H:%M')
                 except Exception: processed_at_str = ts.strftime('%Y-%m-%d %H:%M UTC')
            summary_text = email_data.get('summary', '')
            summary_display = "N/A" if summary_text is None or summary_text == "" or str(summary_text).startswith("Error:") else summary_text
            purpose = email_data.get('llm_purpose', 'Unknown')
            emails_list.append({
                'Email ID': email_data['id'], 'Processed At': processed_at_str,
                'Agent Priority': email_data.get('priority', 'N/A'), 'Sender': email_data.get('sender', 'N/A'),
                'Subject': email_data.get('subject', 'N/A'), 'Summary': summary_display,
                'Your Correction': "N/A", 'Purpose': purpose
            })
        logging.info(f"Fetched {len(emails_list)} emails.")
        if not emails_list: return pd.DataFrame()
        df = pd.DataFrame(emails_list)
        display_columns = ['Email ID', 'Processed At', 'Agent Priority', 'Sender', 'Subject', 'Summary', 'Your Correction', 'Purpose']
        df = df.reindex(columns=display_columns)
        return df
    except Exception as e:
        logging.error(f"Error fetching emails from Firestore: {e}", exc_info=True)
        return pd.DataFrame()

@st.cache_data(ttl=60)
def fetch_emails_by_purpose(purpose_type, limit=20):
    """Fetch emails filtered by purpose"""
    if not db: return pd.DataFrame()
    
    try:
        logging.info(f"Fetching up to {limit} emails with purpose: {purpose_type}")
        
        # Query with filter
        query = db.collection(EMAILS_COLLECTION)
        
        # Add purpose filter if specified
        if purpose_type and purpose_type != "All":
            query = query.where('llm_purpose', '==', purpose_type)
        
        # Order and limit
        query = query.order_by('processed_timestamp', direction=firestore.Query.DESCENDING).limit(limit)
        
        # Process results
        results = query.stream()
        emails_list = []
        
        for doc in results:
            email_data = doc.to_dict()
            email_data['id'] = doc.id
            
            # Format timestamp
            ts = email_data.get('processed_timestamp')
            processed_at_str = 'N/A'
            if ts and isinstance(ts, datetime):
                if ts.tzinfo is None: 
                    ts = ts.replace(tzinfo=timezone.utc)
                try: 
                    processed_at_str = ts.astimezone().strftime('%Y-%m-%d %H:%M')
                except Exception: 
                    processed_at_str = ts.strftime('%Y-%m-%d %H:%M UTC')
            
            # Format summary
            summary_text = email_data.get('summary', '')
            summary_display = "N/A" if summary_text is None or summary_text == "" or str(summary_text).startswith("Error:") else summary_text
            
            # Build email entry
            emails_list.append({
                'Email ID': email_data['id'],
                'Processed At': processed_at_str,
                'Priority': email_data.get('priority', 'N/A'),
                'Sender': email_data.get('sender', 'N/A'),
                'Subject': email_data.get('subject', 'N/A'),
                'Summary': summary_display,
                'Purpose': email_data.get('llm_purpose', 'Unknown')
            })
        
        if not emails_list: return pd.DataFrame()
        
        df = pd.DataFrame(emails_list)
        return df
        
    except Exception as e:
        logging.error(f"Error fetching emails by purpose: {e}", exc_info=True)
        return pd.DataFrame()

# --- Function to get Agent State ---
@st.cache_data(ttl=60)
def get_agent_state():
    state_data = {"last_feedback_count": 0, "last_updated": "N/A"}
    if not db: return state_data
    try:
        doc_ref = db.collection(STATE_COLLECTION).document("retraining_state")
        doc = doc_ref.get()
        if doc.exists:
            data = doc.to_dict()
            state_data["last_feedback_count"] = data.get("last_feedback_count", 0)
            ts = data.get("last_updated")
            if ts and isinstance(ts, datetime):
                 if ts.tzinfo is None: ts = ts.replace(tzinfo=timezone.utc)
                 try: state_data["last_updated"] = ts.astimezone().strftime('%Y-%m-%d %H:%M:%S %Z')
                 except Exception: state_data["last_updated"] = ts.strftime('%Y-%m-%d %H:%M:%S UTC')
            elif isinstance(ts, str):
                 try: dt_obj = datetime.fromisoformat(ts.replace('Z', '+00:00')); state_data["last_updated"] = dt_obj.astimezone().strftime('%Y-%m-%d %H:%M:%S %Z')
                 except ValueError: state_data["last_updated"] = ts
            else: state_data["last_updated"] = "Never Retrained"
        else:
            logging.info("UI: Retraining state document not found in Firestore.")
            state_data["last_updated"] = "Never Retrained"
    except Exception as e:
        logging.error(f"Error fetching agent state from Firestore: {e}", exc_info=True)
    return state_data

# --- Editor Callback Function ---
def handle_editor_changes():
    """Enhanced callback to handle both priority and purpose changes"""
    logging.info("handle_editor_changes callback triggered.")
    if EDITOR_STATE_KEY not in st.session_state: return
    if ORIGINAL_DF_KEY not in st.session_state: return
    
    editor_state = st.session_state[EDITOR_STATE_KEY]
    original_df = st.session_state[ORIGINAL_DF_KEY]
    
    if "edited_rows" not in editor_state or not editor_state["edited_rows"]: return
    
    edited_rows_dict = editor_state["edited_rows"]
    logging.info(f"Editor state contains {len(edited_rows_dict)} edited row(s).")
    
    if PENDING_FEEDBACK_KEY not in st.session_state: 
        st.session_state[PENDING_FEEDBACK_KEY] = []
    
    processed_indices_this_session = st.session_state.get(PROCESSED_FEEDBACK_INDICES_KEY, set())
    items_added_to_pending = 0
    
    # Loop through all edited rows
    for row_index, edited_columns in edited_rows_dict.items():
        row_index_int = int(row_index)
        
        # Check for priority changes
        if "Your Correction" in edited_columns:
            corrected_priority = edited_columns["Your Correction"]
            
            if row_index_int not in processed_indices_this_session and corrected_priority not in [None, "N/A"]:
                try:
                    original_row = original_df.iloc[row_index_int]
                    st.session_state[PENDING_FEEDBACK_KEY].append({
                        "row_index": row_index_int,
                        "email_id": original_row['Email ID'],
                        "original_priority": original_row['Agent Priority'],
                        "corrected_priority": corrected_priority,
                        "sender": original_row['Sender'],
                        "feedback_type": "priority"
                    })
                    items_added_to_pending += 1
                except IndexError: 
                    logging.error(f"Could not find original row data for edited index {row_index} in callback.")
                except Exception as e: 
                    logging.error(f"Unexpected error preparing priority feedback for index {row_index}: {e}", exc_info=True)
        
        # Check for purpose changes
        if "Purpose" in edited_columns:
            corrected_purpose = edited_columns["Purpose"]
            
            try:
                original_row = original_df.iloc[row_index_int]
                original_purpose = original_row['Purpose']
                
                # Only add feedback if the purpose was actually changed
                if corrected_purpose != original_purpose and corrected_purpose != "Unknown":
                    st.session_state[PENDING_FEEDBACK_KEY].append({
                        "row_index": row_index_int,
                        "email_id": original_row['Email ID'],
                        "original_priority": original_row['Agent Priority'],
                        "corrected_purpose": corrected_purpose,
                        "sender": original_row['Sender'],
                        "feedback_type": "purpose"
                    })
                    items_added_to_pending += 1
            except IndexError: 
                logging.error(f"Could not find original row data for edited index {row_index} in callback.")
            except Exception as e: 
                logging.error(f"Unexpected error preparing purpose feedback for index {row_index}: {e}", exc_info=True)
    
    logging.info(f"Callback finished. Added {items_added_to_pending} items to pending feedback list.")
    
    # Add a message to the chat about feedback
    if items_added_to_pending > 0:
        feedback_message = {
            "role": "assistant",
            "content": f"I noticed you provided feedback on {items_added_to_pending} email{'s' if items_added_to_pending > 1 else ''}. Thanks for helping me learn! I'll adjust my classification for similar emails in the future.",
            "context": {"hint": "feedback_received", "data": None}
        }
        st.session_state[CHAT_HISTORY_KEY].append(feedback_message)
        
        # Remember current tab for after rerun
        st.session_state[CURRENT_TAB_KEY] = 1  # Tab index for Email Feedback

# --- Helper Functions for Email Analysis ---
def analyze_email_patterns(email_df):
    """Analyze email patterns to generate insights"""
    if email_df.empty:
        return None
    
    insights = {}
    
    # Frequency analysis by sender
    if 'Sender' in email_df.columns:
        sender_counts = {}
        domain_counts = {}
        
        for sender in email_df['Sender']:
            if not sender in sender_counts:
                sender_counts[sender] = 0
            sender_counts[sender] += 1
            
            # Extract domain
            domain_match = re.search(r'@([\w.-]+)', sender)
            if domain_match:
                domain = domain_match.group(1).lower()
                if not domain in domain_counts:
                    domain_counts[domain] = 0
                domain_counts[domain] += 1
        
        # Get top senders
        insights['top_senders'] = sorted(sender_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        insights['top_domains'] = sorted(domain_counts.items(), key=lambda x: x[1], reverse=True)[:5]
    
    # Priority distribution
    if 'Agent Priority' in email_df.columns:
        insights['priority_distribution'] = email_df['Agent Priority'].value_counts().to_dict()
    
    # Purpose/intent distribution
    if 'Purpose' in email_df.columns:
        insights['purpose_distribution'] = email_df['Purpose'].value_counts().to_dict()
    
    return insights

# --- Simplified Suggestion Card Display ---
def render_suggestion_card(suggestion, key_prefix):
    """Render a single suggestion card with action buttons"""
    title = suggestion.get('title', 'Suggestion') # Use .get for safety
    description = suggestion.get('description', '') # Use .get for safety

    # Use a unique container key based on suggestion type and hash
    container_key = f"container_{key_prefix}_{suggestion.get('type', 'unknown')}_{hash(title)}"

    # Use st.expander for better layout and isolation
    with st.expander(title, expanded=True): # Use title in expander
        # Use st.text for the description - safest option
        st.markdown(description, unsafe_allow_html=False)

        # Button Logic
        col1, col2 = st.columns([1, 1])
        with col1:
            # Ensure button keys are unique and valid
            yes_key = f"yes_{key_prefix}_{hash(str(suggestion.get('action', '')))}"
            if st.button("Yes, proceed", key=yes_key):
                logging.info(f"Yes clicked for suggestion: {suggestion.get('type')}")
                # Store action (still using DEBUG params for now)
                st.session_state.suggested_action = {
                    "action": suggestion.get('action'),
                    "params": suggestion.get('action_params', {}) # Use .get
                }
                st.success(f"Processing request...") # Show feedback
                time.sleep(0.5)
                st.rerun()

        with col2:
            dismiss_key = f"dismiss_{key_prefix}_{hash(str(suggestion.get('type', '')))}"
            if st.button("Dismiss", key=dismiss_key):
                logging.info(f"Dismiss clicked for suggestion: {suggestion.get('type')}")
                suggestion_type = suggestion.get('type')
                if suggestion_type:
                    # Ensure dismissed_suggestions exists and is a set
                    if "dismissed_suggestions" not in st.session_state or not isinstance(st.session_state.dismissed_suggestions, set):
                        st.session_state.dismissed_suggestions = set()
                    st.session_state.dismissed_suggestions.add(suggestion_type)
                    st.success(f"Suggestion dismissed.")
                    time.sleep(0.5)
                    st.rerun()
                else:
                    st.warning("Could not dismiss suggestion: type unknown.")

def handle_suggestion_action(action, params):
    """Handle the action when a suggestion is accepted"""
    # Store in session state for later processing
    st.session_state.suggested_action = {
        "action": action,
        "params": params
    }

def dismiss_suggestion(suggestion_type):
    """Mark a suggestion as dismissed"""
    st.session_state.dismissed_suggestions.add(suggestion_type)

def generate_proactive_suggestions(self, email_df, user_preferences=None): # Removed last_suggestion_types for now
    """Generate proactive suggestions - More Stable Version"""
    logging.debug("--- Entered generate_proactive_suggestions ---")
    # Ensure insights calculation is safe or handled
    try:
        insights = self.analyze_email_patterns(email_df)
        if not insights:
            logging.warning("No insights generated, cannot create suggestions.")
            return []
    except Exception as e:
        logging.error(f"Error during insight analysis: {e}", exc_info=True)
        return []

    # Define a potential order of importance for suggestion types
    # Adjust this order based on desired priority
    suggestion_priority_order = [
        "high_priority",
        "pending_actions",
        "unanswered_questions",
        "sender_rule",
        "domain_filter",
        "recurring_meeting",
        "follow_up",
        "time_management",
        "email_cleanup",
        "scheduled_send",
        "priority_summary"
        # Add any other types here in desired order
    ]

    # Ensure all defined types are in the priority list
    for key in self.suggestion_types.keys():
        if key not in suggestion_priority_order:
            suggestion_priority_order.append(key) # Add any missing ones at the end

    # Generate ALL potentially valid suggestions first
    all_qualifying_suggestions = []
    logging.debug(f"Checking suggestion types in order: {suggestion_priority_order}")
    for suggestion_type in suggestion_priority_order:
        generator_func = self.suggestion_types.get(suggestion_type)
        if not generator_func: continue

        try:
            # Pass user_preferences here if needed by generator
            suggestion = generator_func(email_df, insights, user_preferences)
            if suggestion:
                # Ensure type is correctly set
                if suggestion.get("type") != suggestion_type:
                     logging.warning(f"Mismatch: Generator for {suggestion_type} produced type {suggestion.get('type')}. Forcing.")
                     suggestion["type"] = suggestion_type
                all_qualifying_suggestions.append(suggestion)
                logging.debug(f"Qualified suggestion generated: Type='{suggestion_type}'")
            # else: # Optional log
            #    logging.debug(f"Generator for '{suggestion_type}' returned None (did not qualify).")
        except Exception as e:
            logging.error(f"Error generating {suggestion_type} suggestion: {e}", exc_info=True)

    # Select the top N suggestions based on the priority order
    max_suggestions = 3 # Let's reduce this for stability during testing
    final_suggestions = all_qualifying_suggestions[:max_suggestions]

    logging.info(f"Generated {len(final_suggestions)} suggestions (out of {len(all_qualifying_suggestions)} qualifying). Types: {[s.get('type') for s in final_suggestions]}")
    return final_suggestions


def display_proactive_suggestions(self, email_df):
    """Display proactive suggestions - CORRECTED VERSION"""
    logging.debug("--- Entered display_proactive_suggestions ---")
    st.caption(f"✓ Enhanced suggestions active - Dismissed: {list(st.session_state.get('dismissed_suggestions', set()))}")
    # Ensure session state exists
    if "dismissed_suggestions" not in st.session_state:
        st.session_state.dismissed_suggestions = set()

    # --- Generate Suggestions ONCE ---
    # Use self.memory if available, otherwise None
    user_prefs = self.memory.get_user_preferences() if self.memory else None
    suggestions = self.generate_proactive_suggestions(
        email_df,
        user_preferences=user_prefs,  # Consistent variable name
        last_suggestion_types=st.session_state.get("last_suggestion_types", [])
    )

    # Check if suggestions is None or empty
    if suggestions is None or len(suggestions) == 0:
        logging.debug("display_proactive_suggestions: No suggestions generated or list is empty.")
        return

    st.subheader("📊 Proactive Suggestions")

    # --- Filtering based on CURRENT session state ---
    active_suggestions = []
    dismissed_ui_count = 0
    try:
        # Get the set dismissed *in this session*
        dismissed_state_value = getattr(st.session_state, "dismissed_suggestions", set())
        
        dismissed_set_for_filtering = set()
        if isinstance(dismissed_state_value, set):
            dismissed_set_for_filtering = {str(item).lower() for item in dismissed_state_value if isinstance(item, str)}

        logging.debug(f"Filtering {len(suggestions)} generated suggestions against dismissed set: {dismissed_set_for_filtering}")

        # Filter the generated list
        # Fixed: Use loop variable 's' consistently
        for s in suggestions:
            s_type = s.get("type") if isinstance(s, dict) else None
            s_type_lower = str(s_type).lower() if s_type else None
            is_dismissed = s_type_lower in dismissed_set_for_filtering if s_type_lower else True

            logging.debug(f"Filtering: Sug Type='{s_type_lower}', Dismissed={is_dismissed}")
            if not is_dismissed:
                active_suggestions.append(s)

        original_suggestion_count = len(suggestions)
        dismissed_ui_count = original_suggestion_count - len(active_suggestions)
        logging.debug(f"Filtering complete. Active count: {len(active_suggestions)}")

    except Exception as e_filt:
        st.error(f"Error during suggestion filtering: {e_filt}")
        logging.error(f"Error filtering suggestions: {e_filt}", exc_info=True)
        active_suggestions = []  # Show none if filtering fails

    # --- Display Dismissed Count ---
    if dismissed_ui_count > 0:
        st.caption(f"({dismissed_ui_count} suggestions dismissed this session. Reset in Settings.)")

    # --- Render Active Suggestion Cards ---
    if not active_suggestions:
        st.info("No active suggestions to display.")
    else:
        logging.debug(f"Rendering {len(active_suggestions)} active suggestion cards.")
        for i, suggestion in enumerate(active_suggestions):
            try:
                self.render_suggestion_card(suggestion, f"sugg_{i}")
            except Exception as e_render:
                st.error(f"Error rendering suggestion card {i}: {e_render}")
                logging.error(f"Error rendering card {i} (data: {suggestion}): {e_render}", exc_info=True)

    # Store current suggestions for reference
    st.session_state[SUGGESTIONS_STATE_KEY] = suggestions

def render_enhanced_dashboard():
    """Render simplified dashboard with charts removed to reduce redundancy with Insights tab."""
    df_emails = fetch_recent_emails(limit=100)
    col_toggle_spacer, col_toggle = st.columns([3, 1])
    with col_toggle:
        autonomous_mode = st.toggle("Autonomous Mode",
                                  value=st.session_state.get("autonomous_mode", False),
                                  help="When enabled, I'll be more proactive and take initiative")
        st.session_state["autonomous_mode"] = autonomous_mode
    
    suggestions_to_display = [] # Initialize

    if df_emails is not None and not df_emails.empty:
        st.markdown("### At a Glance")
        glance_col1, glance_col2, glance_col3 = st.columns(3)
        with glance_col1:
            # ... (Email Trends rendering code) ...
            pass
        with glance_col2:
            # ... (Priority Focus rendering code) ...
            pass
        with glance_col3:
            # ... (Time Management rendering code) ...
            pass

        # --- Suggestion Generation & Caching (SINGLE INSTANCE) ---
        try:
            current_df_hash = pd.util.hash_pandas_object(df_emails[['Email ID', 'Processed At']], index=True).sum()
        except Exception:
            logging.warning("Hash calculation failed")
            current_df_hash = None
            
        last_df_hash = st.session_state.get(LAST_DF_HASH_KEY, None)
        
        if current_df_hash is not None and (current_df_hash != last_df_hash or SUGGESTIONS_STATE_KEY not in st.session_state):
            logging.info("Regenerating suggestions...")
            user_prefs = memory.get_user_preferences() if memory else None # Ensure 'memory' is accessible here
            generated_suggestions = proactive_agent.generate_proactive_suggestions( # Ensure 'proactive_agent' is accessible
                df_emails, 
                user_preferences=user_prefs
            )
            st.session_state[SUGGESTIONS_STATE_KEY] = generated_suggestions
            st.session_state[LAST_DF_HASH_KEY] = current_df_hash
            suggestions_to_display = generated_suggestions
        else:
            logging.debug("Using cached suggestions.")
            suggestions_to_display = st.session_state.get(SUGGESTIONS_STATE_KEY, [])
        # --- End Suggestion Generation & Caching ---

    else:
        # No emails fetched
        st.info("No email data available to display on the dashboard.")
        # Clear suggestion cache if no emails
        if SUGGESTIONS_STATE_KEY in st.session_state:
            del st.session_state[SUGGESTIONS_STATE_KEY]
        if LAST_DF_HASH_KEY in st.session_state:
            del st.session_state[LAST_DF_HASH_KEY]
        # suggestions_to_display remains empty (already initialized as such)

    # --- Display Proactive Suggestions ---
    # This call is now correctly placed and will use the 'suggestions_to_display'
    # list that was populated (or left empty) by the logic above.
    proactive_agent.display_proactive_suggestions(suggestions_to_display) # Ensure 'proactive_agent' is accessible
    
def render_autonomous_tab():
    st.markdown("## Autonomous Email Management")

    if not memory:
        st.error("Memory system is not available. Cannot load or save autonomous settings.")
        return

    user_profile_data = memory.user_profile if memory.user_profile else {}
    agent_prefs = user_profile_data.get("agent_preferences", {})
    autonomous_settings = user_profile_data.get("autonomous_settings", {})

    # --- Autonomous Mode Toggle ---
    # 1. Determine the initial value for the session state based on persisted data
    persisted_autonomous_mode = agent_prefs.get("autonomous_mode_enabled", False)

    # 2. Initialize st.session_state["autonomous_mode"] ONCE per session if not set,
    #    using the persisted value.
    if "autonomous_mode_initialized_from_persisted" not in st.session_state:
        st.session_state["autonomous_mode"] = persisted_autonomous_mode
        st.session_state["autonomous_mode_initialized_from_persisted"] = True # Mark as initialized

    # 3. The st.toggle widget directly modifies st.session_state["autonomous_mode"]
    #    We use a callback to handle the logic *after* the toggle changes its state.

    def autonomous_mode_on_change():
        # This callback runs *after* st.session_state["autonomous_mode_main_toggle_key"] is updated by Streamlit
        current_ui_toggle_state = st.session_state.autonomous_mode_main_toggle_key # Get the new state from the widget
        
        # Update the general session state variable we use elsewhere
        st.session_state["autonomous_mode"] = current_ui_toggle_state

        # Save the new state to Firestore
        if memory.save_profile_updates({"agent_preferences.autonomous_mode_enabled": current_ui_toggle_state}):
            if current_ui_toggle_state:
                st.toast("Autonomous mode enabled and preference saved!", icon="🤖")
            else:
                st.toast("Autonomous mode disabled and preference saved.", icon="👤")
            logging.info(f"UI: Saved agent_preferences.autonomous_mode_enabled: {current_ui_toggle_state}")
            if "agent_preferences" not in memory.user_profile: memory.user_profile["agent_preferences"] = {}
            memory.user_profile["agent_preferences"]["autonomous_mode_enabled"] = current_ui_toggle_state
        else:
            st.error("Failed to save autonomous mode preference.")
            # Optionally revert UI if save fails - tricky with callbacks, toast might be enough
            # st.session_state["autonomous_mode"] = not current_ui_toggle_state # Revert general state
            # Need to also revert st.session_state.autonomous_mode_main_toggle_key, which is harder.

    st.toggle(
        "Enable Autonomous Mode",
        value=st.session_state["autonomous_mode"], # Read from our general session state variable
        key="autonomous_mode_main_toggle_key",    # Key for the widget itself
        on_change=autonomous_mode_on_change,      # Callback to handle saving
        help="When enabled, Maia will be more proactive and can take initiative based on your configured permissions and scheduled tasks."
    )

    # The rest of the tab content depends on st.session_state["autonomous_mode"]
    if not st.session_state.get("autonomous_mode", False):
        st.warning("""
        Autonomous mode is currently disabled. Enable it above to allow Maia to:
        - Proactively manage your inbox based on learned patterns.
        - Automatically categorize and prioritize emails (if permissions are granted).
        - Suggest responses and actions more readily.
        - Execute scheduled tasks like daily summaries or auto-archiving.
        """)
    else:
        st.success("Autonomous mode is enabled. Maia is actively assisting with your inbox based on your configurations below.")
        # ... (rest of your render_autonomous_tab function for when mode is enabled) ...
        # The logic for loading/saving other settings like Proactivity Level, Permissions,
        # and Scheduled Tasks should remain similar to the previous version,
        # ensuring they read their initial values from `agent_prefs` or `autonomous_settings`
        # and save changes back to `memory`.

        # Example: Proactivity Level (ensure it uses st.session_state["autonomous_mode"] for disabled state)
        st.markdown("### Autonomy Settings") # This section only shows if mode is ON
        settings_col1, settings_col2 = st.columns(2)

        with settings_col1:
            st.markdown("#### Proactivity Level")
            # current_suggestion_freq is already loaded from agent_prefs at the top
            current_suggestion_freq = agent_prefs.get("suggestion_frequency", "medium")
            proactivity_map_inv = {"low": "Minimal", "medium": "Balanced", "high": "Highly Proactive"}
            current_proactivity_slider_value = proactivity_map_inv.get(current_suggestion_freq, "Balanced")

            proactivity = st.select_slider(
                "How proactive should Maia be with suggestions?",
                options=["Minimal", "Balanced", "Highly Proactive"],
                value=current_proactivity_slider_value,
                key="proactivity_level_slider",
                disabled=not st.session_state["autonomous_mode"] # Correctly uses the session state
            )
            # ... (save logic for proactivity as before) ...
            suggestion_freq_map = {"Minimal": "low", "Balanced": "medium", "Highly Proactive": "high"}
            selected_freq = suggestion_freq_map[proactivity]

            if selected_freq != current_suggestion_freq: # Only save if changed
                if memory.save_profile_updates({"agent_preferences.suggestion_frequency": selected_freq}):
                    st.toast(f"Proactivity level set to: {proactivity}", icon="👍")
                    logging.info(f"UI: Saved agent_preferences.suggestion_frequency: {selected_freq}")
                    if "agent_preferences" not in memory.user_profile: memory.user_profile["agent_preferences"] = {}
                    memory.user_profile["agent_preferences"]["suggestion_frequency"] = selected_freq
                    st.rerun() # Rerun to reflect change if necessary
                else:
                    st.error("Failed to save proactivity level.")
        
        # ... (rest of the settings: Permissions, Scheduled Tasks, ensuring they also use
        #      `disabled=not st.session_state["autonomous_mode"]` and load/save their
        #      specific values from/to agent_prefs or autonomous_settings in memory.user_profile)

        with settings_col2:
            st.markdown("#### Autonomous Permissions")
            allow_auto_categorization_persisted = agent_prefs.get("allow_auto_categorization", True)
            # ... (similar loading and saving for other checkboxes) ...
            new_allow_auto_categorization = st.checkbox(
                "Allow automatic categorization (based on learning)",
                value=allow_auto_categorization_persisted, # Load persisted
                key="perm_auto_categorize",
                disabled=not st.session_state["autonomous_mode"]
            )
            if new_allow_auto_categorization != allow_auto_categorization_persisted:
                if memory.save_profile_updates({"agent_preferences.allow_auto_categorization": new_allow_auto_categorization}):
                    st.toast("Auto-categorization permission updated.", icon="👍")
                    if "agent_preferences" not in memory.user_profile: memory.user_profile["agent_preferences"] = {}
                    memory.user_profile["agent_preferences"]["allow_auto_categorization"] = new_allow_auto_categorization

            allow_auto_priority_persisted = agent_prefs.get("allow_auto_priority", True)
            new_allow_auto_priority = st.checkbox(
                "Allow automatic priority assignment (based on learning)",
                value=allow_auto_priority_persisted, # Load persisted
                key="perm_auto_priority",
                disabled=not st.session_state["autonomous_mode"]
            )
            if new_allow_auto_priority != allow_auto_priority_persisted:
                if memory.save_profile_updates({"agent_preferences.allow_auto_priority": new_allow_auto_priority}):
                    st.toast("Auto-priority permission updated.", icon="👍")
                    if "agent_preferences" not in memory.user_profile: memory.user_profile["agent_preferences"] = {}
                    memory.user_profile["agent_preferences"]["allow_auto_priority"] = new_allow_auto_priority

            allow_auto_archiving_persisted = agent_prefs.get("allow_auto_archiving", False)
            new_allow_auto_archiving = st.checkbox(
                "Allow automatic archiving of low priority emails",
                value=allow_auto_archiving_persisted, # Load persisted
                key="perm_auto_archive",
                disabled=not st.session_state["autonomous_mode"]
            )
            if new_allow_auto_archiving != allow_auto_archiving_persisted:
                if memory.save_profile_updates({"agent_preferences.allow_auto_archiving": new_allow_auto_archiving}):
                    st.toast("Auto-archiving permission updated.", icon="👍")
                    if "agent_preferences" not in memory.user_profile: memory.user_profile["agent_preferences"] = {}
                    memory.user_profile["agent_preferences"]["allow_auto_archiving"] = new_allow_auto_archiving
            
            archive_permission = new_allow_auto_archiving # For use by Auto-Archive save button

            allow_auto_draft_persisted = agent_prefs.get("allow_auto_draft", False)
            new_allow_auto_draft = st.checkbox(
                "Allow automatic draft creation for simple replies",
                value=allow_auto_draft_persisted, # Load persisted
                key="perm_auto_draft",
                disabled=not st.session_state["autonomous_mode"]
            )
            if new_allow_auto_draft != allow_auto_draft_persisted:
                if memory.save_profile_updates({"agent_preferences.allow_auto_draft": new_allow_auto_draft}):
                    st.toast("Auto-draft permission updated.", icon="👍")
                    if "agent_preferences" not in memory.user_profile: memory.user_profile["agent_preferences"] = {}
                    memory.user_profile["agent_preferences"]["allow_auto_draft"] = new_allow_auto_draft


        st.markdown("---")
        st.markdown("### Scheduled Email Tasks")
        # ... (Daily Summary, Auto-Archive, Follow-up sections as before,
        #      ensuring they use `disabled=not st.session_state["autonomous_mode"]`
        #      and also `disabled=not specific_task_enable_toggle` for their sub-controls)
        task_col1, task_col2, task_col3 = st.columns(3)
        with task_col1:
            st.markdown("#### Daily Summary")
            daily_summary_settings = autonomous_settings.get("daily_summary", {})
            current_summary_enabled = daily_summary_settings.get("enabled", False)
            current_summary_time_str = daily_summary_settings.get("time", "17:00")
            try:
                current_summary_time_obj = datetime.strptime(current_summary_time_str, "%H:%M").time()
            except ValueError:
                current_summary_time_obj = datetime.strptime("17:00", "%H:%M").time()
            current_summary_options = daily_summary_settings.get("content", ["High priority emails", "Action requests"])

            summary_enabled_toggle = st.toggle(
                "Enable Daily Summary",
                value=current_summary_enabled,
                key="daily_summary_enable_toggle_auto_on",
                disabled=not st.session_state["autonomous_mode"]
            )
            summary_time = st.time_input(
                "Summary delivery time",
                value=current_summary_time_obj,
                disabled=not st.session_state["autonomous_mode"] or not summary_enabled_toggle,
                key="daily_summary_time_input_auto_on"
            )
            summary_options = st.multiselect(
                "Include in summary",
                ["High priority emails", "Action requests", "Questions", "Statistics", "Recommendations"],
                default=current_summary_options,
                disabled=not st.session_state["autonomous_mode"] or not summary_enabled_toggle,
                key="daily_summary_options_multiselect_auto_on"
            )
            if st.button("Save Daily Summary Settings", key="save_daily_summary_button_auto_on", disabled=not st.session_state["autonomous_mode"]):
                update_data = {
                    "autonomous_settings.daily_summary.enabled": summary_enabled_toggle,
                    "autonomous_settings.daily_summary.time": summary_time.strftime("%H:%M"),
                    "autonomous_settings.daily_summary.content": summary_options
                }
                if memory.save_profile_updates(update_data):
                    st.success("Daily summary preferences saved!")
                    logging.info(f"UI: Saved daily summary settings: {update_data}")
                    if "autonomous_settings" not in memory.user_profile: memory.user_profile["autonomous_settings"] = {}
                    if "daily_summary" not in memory.user_profile["autonomous_settings"]:
                         memory.user_profile["autonomous_settings"]["daily_summary"] = {}
                    memory.user_profile["autonomous_settings"]["daily_summary"]["enabled"] = summary_enabled_toggle
                    memory.user_profile["autonomous_settings"]["daily_summary"]["time"] = summary_time.strftime("%H:%M")
                    memory.user_profile["autonomous_settings"]["daily_summary"]["content"] = summary_options
                    st.rerun()
                else:
                    st.error("Failed to save daily summary preferences.")

        with task_col2:
            st.markdown("#### Auto-Archive")
            auto_archive_settings = autonomous_settings.get("auto_archive", {})
            current_archive_enabled = auto_archive_settings.get("enabled", False)
            current_archive_criteria = auto_archive_settings.get("criteria", ["Promotions", "Notifications"])
            current_archive_excluded_senders = auto_archive_settings.get("excluded_senders", [])

            archive_enabled_toggle = st.toggle(
                "Enable Auto-Archive",
                value=current_archive_enabled,
                key="auto_archive_enable_toggle_auto_on",
                disabled=not st.session_state["autonomous_mode"]
            )
            archive_criteria = st.multiselect(
                "Archive emails matching these purposes:",
                ["Low priority", "Promotions", "Notifications", "Social", "Older than 7 days", "Already responded"],
                default=current_archive_criteria,
                disabled=not st.session_state["autonomous_mode"] or not archive_enabled_toggle,
                key="auto_archive_criteria_multiselect_auto_on"
            )
            archive_excluded_text = "\n".join(current_archive_excluded_senders)
            archive_excluded_input = st.text_area(
                "Never archive senders (one per line, e.g., boss@example.com):",
                value=archive_excluded_text,
                height=100,
                disabled=not st.session_state["autonomous_mode"] or not archive_enabled_toggle,
                key="auto_archive_excluded_textarea_auto_on"
            )
            if st.button("Save Auto-Archive Settings", key="save_auto_archive_button_auto_on", disabled=not st.session_state["autonomous_mode"]):
                current_main_archive_permission = agent_prefs.get("allow_auto_archiving", False)
                if not current_main_archive_permission: # Check the permission from agent_prefs
                     st.error("To enable auto-archiving, please first check 'Allow automatic archiving...' under Autonomous Permissions.")
                else:
                    excluded_list = [s.strip().lower() for s in archive_excluded_input.splitlines() if s.strip()]
                    update_data = {
                        "autonomous_settings.auto_archive.enabled": archive_enabled_toggle,
                        "autonomous_settings.auto_archive.criteria": archive_criteria,
                        "autonomous_settings.auto_archive.excluded_senders": excluded_list
                    }
                    if memory.save_profile_updates(update_data):
                        st.success("Auto-archive rules configured!")
                        logging.info(f"UI: Saved auto-archive settings: {update_data}")
                        if "autonomous_settings" not in memory.user_profile: memory.user_profile["autonomous_settings"] = {}
                        if "auto_archive" not in memory.user_profile["autonomous_settings"]:
                            memory.user_profile["autonomous_settings"]["auto_archive"] = {}
                        memory.user_profile["autonomous_settings"]["auto_archive"]["enabled"] = archive_enabled_toggle
                        memory.user_profile["autonomous_settings"]["auto_archive"]["criteria"] = archive_criteria
                        memory.user_profile["autonomous_settings"]["auto_archive"]["excluded_senders"] = excluded_list
                        st.rerun()
                    else:
                        st.error("Failed to save auto-archive rules.")

        with task_col3:
            st.markdown("#### Follow-up Reminders")
            follow_up_settings = autonomous_settings.get("follow_up", {})
            current_follow_up_enabled = follow_up_settings.get("enabled", False)
            current_remind_days = follow_up_settings.get("remind_days", 3)
            current_priority_only = follow_up_settings.get("priority_only", True)

            follow_up_enabled_toggle = st.toggle(
                "Enable Follow-up Reminders",
                value=current_follow_up_enabled,
                key="follow_up_enable_toggle_auto_on",
                disabled=not st.session_state["autonomous_mode"]
            )
            remind_days = st.number_input(
                "Remind if no response after (days):",
                min_value=1, max_value=14,
                value=current_remind_days,
                disabled=not st.session_state["autonomous_mode"] or not follow_up_enabled_toggle,
                key="follow_up_remind_days_numberinput_auto_on"
            )
            priority_only = st.checkbox(
                "Only for high priority emails",
                value=current_priority_only,
                disabled=not st.session_state["autonomous_mode"] or not follow_up_enabled_toggle,
                key="follow_up_priority_only_checkbox_auto_on"
            )
            if st.button("Save Follow-up Settings", key="save_follow_up_button_auto_on", disabled=not st.session_state["autonomous_mode"]):
                update_data = {
                    "autonomous_settings.follow_up.enabled": follow_up_enabled_toggle,
                    "autonomous_settings.follow_up.remind_days": remind_days,
                    "autonomous_settings.follow_up.priority_only": priority_only
                }
                if memory.save_profile_updates(update_data):
                    st.success("Follow-up reminder system configured!")
                    logging.info(f"UI: Saved follow-up settings: {update_data}")
                    if "autonomous_settings" not in memory.user_profile: memory.user_profile["autonomous_settings"] = {}
                    if "follow_up" not in memory.user_profile["autonomous_settings"]:
                        memory.user_profile["autonomous_settings"]["follow_up"] = {}
                    memory.user_profile["autonomous_settings"]["follow_up"]["enabled"] = follow_up_enabled_toggle
                    memory.user_profile["autonomous_settings"]["follow_up"]["remind_days"] = remind_days
                    memory.user_profile["autonomous_settings"]["follow_up"]["priority_only"] = priority_only
                    st.rerun()
                else:
                    st.error("Failed to save follow-up system settings.")

def process_pending_suggestion_actions():
    """Process any pending suggestion actions using the ProactiveAgent."""
    rerun_needed = False # Flag if UI update is needed
    action_processed_that_affects_suggestions = False # Flag

    if "suggested_action" in st.session_state and st.session_state.suggested_action:
        action_data = st.session_state.suggested_action
        action_type = action_data.get('action') # Get action type
        logging.info(f"Processing pending suggestion action: {action_type}")

        # --- CORRECTED Unpacking ---
        # Call the agent to process the action, expect 3 return values
        response_text, was_handled, _ = proactive_agent.process_suggestion_action(action_data)
        # Use underscore _ for the third value (download_data) as it's not used here yet
        # --- END CORRECTION ---

        # Clear the suggestion state variable AFTER processing
        del st.session_state.suggested_action

        # Add assistant response to chat history
        if response_text:
            st.session_state[CHAT_HISTORY_KEY].append({
                "role": "assistant",
                "content": response_text,
                "context": {"hint": "action_result", "data": {"action": action_type, "handled": was_handled}}
            })
            rerun_needed = True

        # Clear Suggestion Cache if Action Affects Generation
        if was_handled and action_type in ["create_sender_rule", "create_domain_filter"]:
            logging.info(f"Action '{action_type}' affects suggestions. Clearing suggestion cache.")
            if SUGGESTIONS_STATE_KEY in st.session_state:
                del st.session_state[SUGGESTIONS_STATE_KEY]
            if LAST_DF_HASH_KEY in st.session_state:
                del st.session_state[LAST_DF_HASH_KEY]

        if not was_handled:
             logging.warning(f"Suggestion action '{action_type}' was not fully handled by the agent.")

    return rerun_needed # Return flag to trigger st.rerun in the main UI loop if needed

# --- Function to process chat commands ---
def generate_agent_response(user_query, memory_system=None, llm_client=None, config=None):
    """
    Enhanced agent response generation with memory and context awareness

    Args:
        user_query: The user's message
        memory_system: Agent memory system instance
        llm_client: The initialized LLM client instance
        config: The loaded configuration dictionary

    Returns:
        tuple: (response_text, context_object)
    """
    # Check if dependencies were passed
    if not llm_client:
        logging.error("generate_agent_response called without llm_client.")
        return "Error: LLM client not available for generating response.", {"hint": "error", "data": None}
    if not config:
        logging.error("generate_agent_response called without config.")
        return "Error: Configuration not available for generating response.", {"hint": "error", "data": None}

    query_lower = user_query.lower()
    logging.debug(f"generate_agent_response: query_lower='{query_lower}'")
    current_time_str = datetime.now().strftime("%H:%M")
    response_text = ""
    context_object = {"hint": "default", "data": None}
    
    response_templates = {
        "db_error": "I'm having trouble connecting to the database right now. Can you try again in a moment?",
        "status_base": f"As of {current_time_str}, I'm operational and monitoring your emails. Here's my current status:",
        "no_priority": f"I haven't found any high priority emails today. Your inbox seems manageable at the moment! Is there anything specific you're looking for?",
        "summary_not_found_prompt": "I tried to find a summary for the email '{subject}' (ID: {email_id}), but it looks like I didn't generate one when processing it. This usually happens for lower priority emails. Would you like me to **summarize** it now?",
        "id_not_found": "I couldn't find an email with ID '{email_id}' in my records. It might have been processed before I started tracking, or there might be a typo in the ID.",
        "id_missing_for_summary": "To summarize an email, I need the email ID. You can either ask to see recent high priority emails first, or if you know the ID, you can ask like this: 'Summarize email ABC123'.",
        "id_missing_for_draft": "To help draft a reply, I need the email ID. You can ask like this: 'Draft a reply to ABC123'.", # New template
        "greeting_help": f"""Hi there! I'm your email assistant. I can help you manage your inbox by identifying important emails, summarizing content, and learning from your feedback.

Here are some things you can ask me:
- "What's your status?" - I'll tell you about my current state and learning
- "Show me high priority emails" - I'll list emails I've classified as important
- "Summarize email [ID]" - I'll provide a summary of a specific email
- "List emails requiring action" - I'll show emails that need your attention
- "Draft a reply to [ID]" - I'll help you write a response
- "Help" - I'll show you this help message again

You can also give me feedback by correcting my priority assessments in the Email Feedback tab.""",
        "fallback": "I'm not sure how to help with '{user_query}'. You can ask about my status, high priority emails, or request email summaries. Type 'help' for more options.",
        "general_error": "I encountered an error while processing your request: {error_message}. Please try again or check the logs for more details."
    }
    # --- Now check db ---
    if not db:
        logging.error("generate_agent_response: Firestore client (db) not available.")
        return response_templates.get("db_error", "Error: Database connection is unavailable."), {"hint": "error", "data": None}
        
    # --- Context Check Logic ---
    last_assistant_message = None
    current_last_hint = "N/A"
    current_last_data_summary = "N/A"
    if st.session_state.get(CHAT_HISTORY_KEY) and len(st.session_state[CHAT_HISTORY_KEY]) > 1:
        if st.session_state[CHAT_HISTORY_KEY][-2]["role"] == "assistant":
             last_assistant_message = st.session_state[CHAT_HISTORY_KEY][-2]
             current_last_hint = last_assistant_message.get("context", {}).get("hint", "Hint not found")
             current_last_data = last_assistant_message.get("context", {}).get("data")
             current_last_data_summary = str(current_last_data)[:100] + "..." if current_last_data else "None"

    logging.debug(f"generate_agent_response: query='{user_query}', last_hint='{current_last_hint}', last_data_summary='{current_last_data_summary}'")

    if last_assistant_message:
        last_hint = last_assistant_message.get("context", {}).get("hint")
        last_data = last_assistant_message.get("context", {}).get("data")

        # Check 1: Live Summarization prompt
        if last_hint == "summary_not_found_prompt" and is_affirmative(query_lower):
            email_id_to_summarize = last_data.get("id") if last_data else None
            if email_id_to_summarize:
                logging.info(f"User confirmed live summarization for email {email_id_to_summarize}.")

                # --- Perform Live Summarization ---
                try:
                    # 1. Fetch email data from Firestore
                    email_ref = db.collection(EMAILS_COLLECTION).document(email_id_to_summarize)
                    doc = email_ref.get()
                    if not doc.exists:
                        logging.error(f"Could not find email {email_id_to_summarize} in Firestore for live summarization.")
                        response_text = f"Sorry, I couldn't find the data for email `{email_id_to_summarize}` to summarize it."
                        context_object = {"hint": "error", "data": {"id": email_id_to_summarize}}
                        if memory_system: memory_system.add_interaction(user_query, response_text, {"type": "error_summary_fetch", "email_id": email_id_to_summarize})
                        return response_text, context_object

                    email_data_dict = doc.to_dict()
                    email_data_dict['id'] = email_id_to_summarize # Ensure ID is in dict

                    # 2. Show thinking message and call LLM for SUMMARY
                    with st.spinner(f"Generating summary for email `{email_id_to_summarize}`..."):
                        summary_result = summarize_email_with_memory(
                            llm_client=llm_client,
                            email_data=email_data_dict,
                            config=config,
                            memory=memory_system,
                            summary_type="standard"
                        )

                    # 3. Format response based on result
                    if summary_result and not summary_result.startswith("Error:"):
                        response_text = (
                            f"Okay, here's the summary I generated for email `{email_id_to_summarize}`:\n\n---\n{summary_result}\n---\n\n"
                            "Would you like me to take any further action?"
                        )
                        context_object = {"hint": "live_summary_complete", "data": {"id": email_id_to_summarize, "summary": summary_result}}
                    else:
                        logging.warning(f"Live summarization for email {email_id_to_summarize} failed or returned error: {summary_result}")
                        response_text = f"Sorry, I wasn't able to generate a summary for email `{email_id_to_summarize}` at this time. The error was: {summary_result}"
                        context_object = {"hint": "error", "data": {"id": email_id_to_summarize}}

                except Exception as e:
                    logging.error(f"Error during live summarization for {email_id_to_summarize}: {e}", exc_info=True)
                    response_text = f"An unexpected error occurred while summarizing email `{email_id_to_summarize}`."
                    context_object = {"hint": "error", "data": {"id": email_id_to_summarize}}

                if memory_system:
                    memory_system.add_interaction(user_query, response_text, {"type": "confirm_summary_done", "email_id": email_id_to_summarize, "result": summary_result if 'summary_result' in locals() else None})
                return response_text, context_object # Return early

            else:
                 logging.warning("Affirmative response received for prompt, but email ID was missing in context.")
    
    # Check 2: Follow-up to Action List with Prioritization Logic
        elif last_hint == "action_list" and ("prioritize" in query_lower or "which first" in query_lower or "handle first" in query_lower or "order" in query_lower):
            email_ids_to_prioritize = last_data.get("ids") if last_data and isinstance(last_data.get("ids"), list) else []
            if email_ids_to_prioritize:
                logging.info(f"User asked to prioritize {len(email_ids_to_prioritize)} action items.")
                try:
                    fetched_emails = []
                    for email_id in email_ids_to_prioritize:
                        if not email_id: continue
                        email_ref = db.collection(EMAILS_COLLECTION).document(email_id)
                        doc = email_ref.get()
                        if doc.exists:
                            email_data = doc.to_dict()
                            # Ensure timestamp is timezone-aware or handle None
                            ts = email_data.get('processed_timestamp')
                            if isinstance(ts, datetime) and ts.tzinfo is None:
                                ts = ts.replace(tzinfo=timezone.utc)
                            elif not isinstance(ts, datetime):
                                ts = datetime.min.replace(tzinfo=timezone.utc) # Default for sorting

                            fetched_emails.append({
                                'id': email_id,
                                'priority': email_data.get('priority', 'MEDIUM'),
                                'subject': email_data.get('subject', '[No Subject]'),
                                'sender': email_data.get('sender', '[No Sender]'),
                                'timestamp': ts # Use processed timestamp
                            })
                        else:
                            logging.warning(f"Could not find email {email_id} in Firestore during prioritization fetch.")

                    if not fetched_emails:
                         response_text = "I couldn't retrieve the details for the action items to prioritize them."
                         context_object = {"hint": "error_prioritization_fetch", "data": {"ids": email_ids_to_prioritize}}
                    else:
                        priority_order = {PRIORITY_CRITICAL: 0, PRIORITY_HIGH: 1, PRIORITY_MEDIUM: 2, PRIORITY_LOW: 3, 'N/A': 4}
                        def get_sort_key(email):
                            prio_val = priority_order.get(email['priority'], 4)
                            # Sort descending by timestamp (most recent first within priority)
                            return (prio_val, -email['timestamp'].timestamp())
                        sorted_emails = sorted(fetched_emails, key=get_sort_key)

                        response_text = f"Okay, based on priority and recency, here's the recommended order to handle those {len(sorted_emails)} action items:\n\n---\n"
                        for i, email in enumerate(sorted_emails, 1):
                            # Use html.escape for safety, but remove for readability on sender/subject
                            sender_display = (email['sender'][:30] + '...') if len(email['sender']) > 33 else email['sender']
                            subject_display = (email['subject'][:50] + '...') if len(email['subject']) > 53 else email['subject']
                            response_text += f"\n{i}. **{email['priority']}**: {subject_display} (From: {sender_display}, ID: `{email['id']}`)"
                        response_text += f"\n\n---"
                        context_object = {"hint": "prioritization_complete", "data": {"sorted_ids": [e['id'] for e in sorted_emails]}}

                    if memory_system:
                        memory_system.add_interaction(user_query, response_text, {"type": "request_prioritization_done", "email_ids": email_ids_to_prioritize})
                    return response_text, context_object # Return for success

                except Exception as e:
                    logging.error(f"Error during prioritization logic for action items: {e}", exc_info=True)
                    response_text = "Sorry, I encountered an error while trying to prioritize the action items."
                    context_object = {"hint": "error_prioritization", "data": {"ids": email_ids_to_prioritize}}
                    if memory_system:
                        memory_system.add_interaction(user_query, response_text, {"type": "request_prioritization_error_exception", "email_ids": email_ids_to_prioritize})
                    return response_text, context_object
            else:
                logging.warning("Prioritization requested, but email IDs were missing from action_list context.")
                # Fall through if IDs missing
        # --- *** END NEW Check 2 *** ---
    
    # --- MODIFIED Check for actions after Draft Display ---
        elif last_hint == "draft_displayed" and last_data:
            logging.debug(f"Entered draft_displayed block with query: '{query_lower}'") # Existing debug
            original_email_id = last_data.get("email_id")
            original_draft_text = last_data.get("draft_text")
            recipient_email = last_data.get("recipient_email")
            original_subject = last_data.get("original_subject")
        
            # --- Check 1: Copy Command ---
            copy_keywords = {"copy", "copy draft", "copy text"}
            if query_lower in copy_keywords:
                logging.info(f"User requested copy for draft of email {original_email_id}")
                if original_draft_text:
                    try:
                        pyperclip.copy(original_draft_text)
                        response_text = "Okay, I've copied the draft text to your clipboard."
                        # Keep the context as draft_displayed in case they want to revise/send next
                        context_object = {"hint": "draft_displayed", "data": last_data}
                        st.success("Draft copied to clipboard!") # Show immediate feedback
                        time.sleep(0.5)
                    except Exception as e:
                        logging.error(f"Failed to copy draft to clipboard: {e}")
                        response_text = "Sorry, I couldn't copy the text to your clipboard automatically. You can copy it manually from the message above."
                        context_object = {"hint": "error", "data": last_data}
                else:
                    response_text = "There doesn't seem to be any draft text to copy."
                    context_object = {"hint": "error", "data": last_data}
        
                if memory_system:
                    memory_system.add_interaction(user_query, response_text, {"type": "copy_draft_command", "email_id": original_email_id})
                return response_text, context_object
        
            # --- Check 2: Send Command ---
            send_keywords = {"send", "send draft", "send email", "send it", "send via gmail", 'send gmail'}
            if any(keyword in query_lower for keyword in send_keywords):
                logging.info(f"User requested send (via chat) for draft of email {original_email_id}")
                if recipient_email and original_draft_text:
                    # Generate the Gmail compose link
                    gmail_compose_link = _create_gmail_compose_link(
                        recipient=recipient_email,
                        subject=original_subject,
                        body=original_draft_text
                    )
                    if gmail_compose_link:
                        # Respond with the link for the user to click
                        response_text = f"Okay, I've prepared the draft for Gmail. You can review and send it there.\n\n[Open Draft in Gmail]({gmail_compose_link})\n\nReady for your next query."
                        context_object = {"hint": "gmail_link_action_taken", "data": None} # Neutral hint, clear draft data from immediate context
                        st.success("Gmail compose link generated!") # Optional immediate feedback
                        time.sleep(0.5)
                    else:
                        response_text = "Sorry, I couldn't generate the link to open this draft in Gmail."
                        context_object = {"hint": "error", "data": last_data} # Keep draft context on error
                else:
                    response_text = "I can't prepare the Gmail link because I'm missing the recipient or the draft text."
                    context_object = {"hint": "error", "data": last_data} # Keep draft context on error
        
                if memory_system:
                    memory_system.add_interaction(user_query, response_text, {"type": "send_draft_command_link", "email_id": original_email_id})
                return response_text, context_object
            
            # --- Check 3: Revision Command (Modified for Consistency) ---
            # Keywords that imply a specific instruction is forthcoming or is the query itself
            # NEW DEBUG LOGS FOR REVISION TRIGGER EVALUATION:
            logging.debug(f"DRAFT_DISPLAYED (Revision Check): query_lower.strip() is '{query_lower.strip()}'")
            logging.debug(f"DRAFT_DISPLAYED (Revision Check): (query_lower.strip() == 'revise') is {query_lower.strip() == 'revise'}")
            logging.debug(f"DRAFT_DISPLAYED (Revision Check): (query_lower.strip() == 'edit') is {query_lower.strip() == 'edit'}")
            specific_revision_keywords = {
                "make it", "add", "remove", "change to", "rephrase", 
                "shorter", "longer", "formal", "casual", "polite", "simpler", "detailed"
            }
            # Keywords that are generic triggers for starting a revision, similar to the button
            generic_revision_triggers = {
                "revise", "edit", "change this draft", "revise draft", "edit draft"
            }
            
            # Debug logging for revision triggers
            logging.debug(f"Checking revision triggers: generic={list(generic_revision_triggers)}, specific={list(specific_revision_keywords)}")
        
            is_specific_instruction = any(keyword in query_lower for keyword in specific_revision_keywords)
            is_generic_trigger = any(trigger == query_lower.strip() for trigger in generic_revision_triggers) or \
                                 (query_lower.strip() == "revise" or query_lower.strip() == "edit")
            # NEW DEBUG LOGS FOR CALCULATED FLAGS:
            logging.debug(f"DRAFT_DISPLAYED (Revision Check): is_generic_trigger calculated as: {is_generic_trigger}")
            logging.debug(f"DRAFT_DISPLAYED (Revision Check): is_specific_instruction calculated as: {is_specific_instruction}")
            logging.debug(f"Trigger checks: is_generic_trigger={is_generic_trigger}, is_specific_instruction={is_specific_instruction}")
        
            # If it's a generic trigger AND NOT a specific instruction (to avoid "revise make it shorter" being caught as generic)
            if is_generic_trigger and not is_specific_instruction:
                logging.info(f"User initiated generic revision for draft of email {original_email_id} via chat.") # Corrected log
                response_text = "Okay, how should I revise the draft?"
                # Set new hint, pass original draft data for context (same as button)
                context_object = {
                    "hint": "awaiting_revision_instruction", 
                    "data": last_data # last_data already contains original_email_id, draft_text, etc.
                }
                logging.debug(f"Generic trigger: Setting hint to 'awaiting_revision_instruction'. Data being passed: {str(last_data)[:100]}...")
                if memory_system:
                    memory_system.add_interaction(user_query, response_text, {"type": "initiate_revise_prompt", "email_id": original_email_id})
                # TODO: This editing feature is being expanded with more capabilities in the future
                return response_text, context_object # THIS RETURN IS CRITICAL
        
            # Else, if it contains any revision-like keyword (generic or specific), treat query as the instruction
            # This covers cases like "revise to be more formal" or just "make it shorter"
            elif any(keyword in query_lower for keyword in generic_revision_triggers.union(specific_revision_keywords)): # Handles specific instructions
                logging.debug(f"Treating '{user_query}' as a specific revision instruction.") # Corrected log
                revision_instruction = user_query 
                if original_email_id and original_draft_text:
                    logging.info(f"User requested specific revision for draft of email {original_email_id}. Instruction: '{revision_instruction}'")
                    # --- Perform Revision (existing logic) ---
                    try:
                        email_ref = db.collection(EMAILS_COLLECTION).document(original_email_id) # Example line from your file
                        doc = email_ref.get()
                        if not doc.exists:
                            raise ValueError(f"Original email {original_email_id} not found for revision context.")
                        original_email_data_dict = doc.to_dict()
                        original_email_data_dict['id'] = original_email_id
        
                        with st.spinner(f"Revising draft for email `{original_email_id}`..."):
                            revised_draft_text = revise_email_draft(
                                llm_client=llm_client,
                                original_draft=original_draft_text,
                                revision_instruction=revision_instruction,
                                original_email_data=original_email_data_dict,
                                config=config,
                                memory=memory_system
                            )
        
                        if revised_draft_text and not revised_draft_text.startswith("Error:"):
                            subject_display = html.escape(original_email_data_dict.get('subject', '[No Subject]'))
                            
                            is_apology = False
                            apology_keywords = ["i apologize, but i cannot", "unable to change the color", "as a text-based assistant, i do not have the capability"]
                            if any(keyword in revised_draft_text.lower() for keyword in apology_keywords):
                                is_apology = True
                                logging.info("Detected apology message in revised_draft_text.")
        
                            response_text = (
                                f"Okay, I've {'responded to' if is_apology else 'revised the draft for'} '{subject_display}' based on your instruction:\n\n"
                                f"---\n```text\n{revised_draft_text}\n```\n---\n\n"
                                f"{'What would you like to do next?' if is_apology else 'Is this better? Or would you like further changes? You can also use the buttons below.'}"
                            )
                            context_object = {
                                "hint": "revision_apology_given" if is_apology else "draft_displayed",
                                "data": {
                                    "email_id": original_email_id,
                                    "draft_text": revised_draft_text,
                                    "recipient_email": recipient_email,
                                    "original_subject": original_subject
                                }
                            }
                        else: # Error from revise_email_draft
                            logging.error(f"Draft revision failed for {original_email_id}: {revised_draft_text}")
                            response_text = f"Sorry, I wasn't able to revise the draft for email `{original_email_id}`. The error was: {revised_draft_text}"
                            context_object = {"hint": "error", "data": {"id": original_email_id}}
                    
                    except ValueError as ve: 
                        logging.error(f"ValueError during revision process for {original_email_id}: {ve}", exc_info=True)
                        response_text = f"Sorry, I couldn't find the original email data needed to revise the draft for {original_email_id}."
                        context_object = {"hint": "error", "data": {"id": original_email_id}}
                    
                    except Exception as e:
                        logging.error(f"Unexpected error during draft revision process for {original_email_id}: {type(e).__name__} - {e}", exc_info=True)
                        response_text = f"An unexpected error occurred while trying to revise the draft for email `{original_email_id}`."
                        context_object = {"hint": "error", "data": {"id": original_email_id}}
        
                    if memory_system:
                        memory_system.add_interaction(user_query, response_text, {"type": "revise_draft_specific_instruction", "email_id": original_email_id})
                    return response_text, context_object
                else: # Missing original_email_id or original_draft_text
                    logging.warning("Revision requested, but email_id or original_draft missing from context.")
                    response_text = "Sorry, I seem to have lost the context for the draft revision. Please ask me to draft it again."
                    context_object = {"hint": "error", "data": {"id": original_email_id}} # Pass ID if available
                    if memory_system:
                         memory_system.add_interaction(user_query, response_text, {"type": "error_revise_context_missing", "email_id": original_email_id})
                    return response_text, context_object
            
            # --- Check 4: Accept Draft Command ---
            accept_keywords = {"accept", "accept draft", "looks good", "good to go", "that's fine", "done with draft", "draft accepted"}
            if any(keyword in query_lower for keyword in accept_keywords): # Check if any keyword is a substring
                logging.info(f"User accepted draft via chat for email {original_email_id}")
                response_text = "Draft accepted. Ready for your next query."
                context_object = {"hint": "draft_accepted_ready_for_next", "data": None} # Neutral hint
                
                if memory_system: # Ensure memory_system is accessible here
                    memory_system.add_interaction(user_query, response_text, {"type": "accept_draft_command", "email_id": original_email_id})
                return response_text, context_object # Return early
            
            # If nothing above matched
            logging.debug(f"Query '{user_query}' after draft_displayed hint didn't match any draft-specific commands.")
            # No return - allow fall-through to other general handlers or the final fallback
                    
        # --- MODIFIED Check for Revision Request ---
        # Check if the *previous* assistant message was prompting for revision instructions
        elif last_hint == "awaiting_revision_instruction" and last_data:
            logging.debug(f"Entered 'awaiting_revision_instruction' block. User query (as instruction): '{user_query}'. Data from context: {str(last_data)[:100]}...")
            original_email_id = last_data.get("email_id")
            original_draft_text = last_data.get("draft_text")
            recipient_email = last_data.get("recipient_email")
            original_subject = last_data.get("original_subject")
            revision_instruction = user_query # The user's input *is* the instruction
            # TODO: Add capabilities to interpret different types of revision requests more intelligently
            if original_email_id and original_draft_text:
                logging.info(f"User provided revision instruction for draft of email {original_email_id}: '{revision_instruction}'")

                # 1. Fetch original email data again (needed for context in revision)
                try:
                    email_ref = db.collection(EMAILS_COLLECTION).document(original_email_id)
                    doc = email_ref.get()
                    if not doc.exists:
                        raise ValueError(f"Original email {original_email_id} not found for revision context.")
                    original_email_data_dict = doc.to_dict()
                    original_email_data_dict['id'] = original_email_id

                    # 2. Call the revision function
                    with st.spinner(f"Revising draft for email `{original_email_id}`..."):
                        revised_draft_text = revise_email_draft(
                            llm_client=llm_client,
                            original_draft=original_draft_text,
                            revision_instruction=revision_instruction,
                            original_email_data=original_email_data_dict,
                            config=config,
                            memory=memory_system
                        )

                    # 3. Format and display the response
                    if revised_draft_text and not revised_draft_text.startswith("Error:"):
                        subject_display = html.escape(original_email_data_dict.get('subject', '[No Subject]')) # Or original_subject
                        
                        # --- DETECT APOLOGY ---
                        is_apology = False
                        apology_keywords = ["i apologize, but i cannot", "unable to change the color", "as a text-based assistant, i do not have the capability"]
                        if any(keyword in revised_draft_text.lower() for keyword in apology_keywords):
                            is_apology = True
                            logging.info("Detected apology message in revised_draft_text.")
                    
                        response_text = (
                            f"Okay, I've {'responded to' if is_apology else 'revised the draft for'} '{subject_display}' based on your instruction:\n\n" # Slightly alter intro
                            f"---\n```text\n{revised_draft_text}\n```\n---\n\n"
                            # Modify the follow-up question if it's an apology
                            f"{'What would you like to do next?' if is_apology else 'Is this better? Or would you like further changes? You can also use the buttons below.'}"
                        )
                        context_object = {
                            "hint": "revision_apology_given" if is_apology else "draft_displayed", # Change hint if apology
                            "data": { # Still pass the data, though draft_text is now the apology
                                "email_id": original_email_id,
                                "draft_text": revised_draft_text, # This will be the apology text
                                "recipient_email": recipient_email,
                                "original_subject": original_subject
                            }
                        }
                    else:
                        logging.error(f"Draft revision failed for {original_email_id}: {revised_draft_text}")
                        response_text = f"Sorry, I wasn't able to revise the draft for email `{original_email_id}`. The error was: {revised_draft_text}"
                        context_object = {"hint": "error", "data": {"id": original_email_id}}

                except Exception as e:
                    logging.error(f"Error during draft revision process for {original_email_id}: {e}", exc_info=True)
                    response_text = f"An unexpected error occurred while trying to revise the draft for email `{original_email_id}`."
                    context_object = {"hint": "error", "data": {"id": original_email_id}}

                if memory_system:
                    memory_system.add_interaction(user_query, response_text, {"type": "revise_draft", "email_id": original_email_id})
                return response_text, context_object # Return early after handling revision

            else:
                logging.warning("Revision instruction received, but email_id or original_draft missing from context.")    
    
    # Check 4: Handling Choice between Summary and Analysis
        elif last_hint == "prompt_summary_or_analysis" and last_data:
            email_id_for_action = last_data.get("id")
            email_data_for_action = last_data.get("email_data")

            if email_id_for_action and email_data_for_action:
                user_wants_summary = "summary" in query_lower or "summarize" in query_lower
                user_wants_analysis = "analysis" in query_lower or "analyze" in query_lower
                is_affirmative_reply = is_affirmative(query_lower)
                action_taken = False

                # --- Handle Summary Request ---
                if user_wants_summary or (is_affirmative_reply and not user_wants_analysis): # Default affirmative to summary
                    if user_wants_summary:
                        logging.info(f"User chose live summarization for {email_id_for_action}.")
                    else:
                        logging.info(f"User gave affirmative reply, defaulting to live summarization for {email_id_for_action}.")

                    try:
                        with st.spinner(f"Generating summary for email `{email_id_for_action}`..."):
                            summary_result = summarize_email_with_memory(
                                llm_client=llm_client, email_data=email_data_for_action,
                                config=config, memory=memory_system, summary_type="standard"
                            )
                        if summary_result and not summary_result.startswith("Error:"):
                            response_text = f"Okay, here's the summary for email `{email_id_for_action}`:\n\n---\n{summary_result}\n---\n\nWhat else can I help with?"
                            context_object = {"hint": "live_summary_complete", "data": {"id": email_id_for_action, "summary": summary_result}}
                            # --- !! ADD FIRESTORE UPDATE !! ---
                            try:
                                email_ref = db.collection(EMAILS_COLLECTION).document(email_id_for_action)
                                email_ref.update({'summary': summary_result, 'summary_type': 'standard'}) # Assuming standard type for live summary
                                logging.info(f"Updated Firestore document {email_id_for_action} with live summary.")
                            except Exception as e_update:
                                logging.error(f"Failed to update Firestore with live summary for {email_id_for_action}: {e_update}")
                            # --- !! END FIRESTORE UPDATE !! ---
                        else:
                            response_text = f"Sorry, I couldn't generate a summary for `{email_id_for_action}`. Error: {summary_result}"
                            context_object = {"hint": "error", "data": {"id": email_id_for_action}}
                        action_taken = True
                    except Exception as e:
                        logging.error(f"Error during live summarization for {email_id_for_action}: {e}", exc_info=True)
                        response_text = f"An unexpected error occurred while summarizing email `{email_id_for_action}`."
                        context_object = {"hint": "error", "data": {"id": email_id_for_action}}
                        action_taken = True

                # --- Handle Analysis Request ---
                elif user_wants_analysis:
                    logging.info(f"User chose live analysis for {email_id_for_action}.")
                    try:
                        with st.spinner(f"Performing fresh analysis for email `{email_id_for_action}`..."):
                            analysis_result = analyze_email_with_context(
                                llm_client=llm_client, email_data=email_data_for_action,
                                config=config, memory=memory_system
                            )
                        if analysis_result:
                            response_text = (
                                f"Okay, here's a fresh analysis for email `{email_id_for_action}`:\n\n"
                                f"- **Urgency Score:** {analysis_result.get('urgency_score', 'N/A')}\n"
                                f"- **Purpose:** {analysis_result.get('purpose', 'N/A')}\n"
                                f"- **Response Needed:** {'Yes' if analysis_result.get('response_needed') else 'No'}\n"
                                f"- **Estimated Time:** {analysis_result.get('estimated_time', 'N/A')} minutes\n\n"
                                f"Would you like me to generate a summary based on this analysis?"
                            )
                            context_object = {"hint": "prompt_summary_after_analysis", "data": {"id": email_id_for_action, "email_data": email_data_for_action}}
                            # --- !! ADD FIRESTORE UPDATE !! ---
                            try:
                                email_ref = db.collection(EMAILS_COLLECTION).document(email_id_for_action)
                                update_data = {
                                    'llm_urgency': analysis_result.get('urgency_score'),
                                    'llm_purpose': analysis_result.get('purpose'),
                                    'response_needed': analysis_result.get('response_needed', False),
                                    'estimated_time': analysis_result.get('estimated_time', 5),
                                    'last_live_analysis_ts': firestore.SERVER_TIMESTAMP # Add timestamp
                                }
                                update_data = {k: v for k, v in update_data.items() if v is not None}
                                email_ref.update(update_data)
                                logging.info(f"Updated Firestore document {email_id_for_action} with live analysis results.")
                            except Exception as e_update:
                                logging.error(f"Failed to update Firestore with live analysis for {email_id_for_action}: {e_update}")
                            # --- !! END FIRESTORE UPDATE !! ---
                        else:
                            response_text = f"Sorry, I couldn't perform a fresh analysis for `{email_id_for_action}` at this time."
                            context_object = {"hint": "error", "data": {"id": email_id_for_action}}
                        action_taken = True
                    except Exception as e:
                        logging.error(f"Error during live analysis for {email_id_for_action}: {e}", exc_info=True)
                        response_text = f"An unexpected error occurred while analyzing email `{email_id_for_action}`."
                        context_object = {"hint": "error", "data": {"id": email_id_for_action}}
                        action_taken = True

                # Handle unclear response
                if not action_taken:
                    response_text = "Sorry, I wasn't sure if you wanted a summary or a fresh analysis. Please clarify by saying 'generate summary' or 'perform analysis'."
                    context_object = {"hint": "prompt_summary_or_analysis", "data": last_data}

                if memory_system:
                    memory_system.add_interaction(user_query, response_text, {"type": "response_to_summary_analysis_prompt", "email_id": email_id_for_action})
                return response_text, context_object

            else:
                logging.warning("Context hint 'prompt_summary_or_analysis' found, but email_id or email_data missing in context.")

        # Check 5: Handling Summary Request after Live Analysis
        elif last_hint == "prompt_summary_after_analysis" and last_data:
             email_id_for_summary = last_data.get("id")
             email_data_for_summary = last_data.get("email_data")

             if is_affirmative(query_lower) or "summary" in query_lower or "summarize" in query_lower:
                 if email_id_for_summary and email_data_for_summary:
                     logging.info(f"User confirmed summary after live analysis for {email_id_for_summary}.")
                     try:
                         with st.spinner(f"Generating summary based on fresh analysis for email `{email_id_for_summary}`..."):
                             summary_result = summarize_email_with_memory(
                                 llm_client=llm_client, email_data=email_data_for_summary,
                                 config=config, memory=memory_system, summary_type="standard"
                             )
                         if summary_result and not summary_result.startswith("Error:"):
                             response_text = f"Okay, here's the summary based on the fresh analysis for email `{email_id_for_summary}`:\n\n---\n{summary_result}\n---\n\nWhat else can I help with?"
                             context_object = {"hint": "live_summary_complete", "data": {"id": email_id_for_summary, "summary": summary_result}}
                             # --- !! ADD FIRESTORE UPDATE !! ---
                             try:
                                 email_ref = db.collection(EMAILS_COLLECTION).document(email_id_for_summary)
                                 email_ref.update({'summary': summary_result, 'summary_type': 'standard'}) # Assuming standard type
                                 logging.info(f"Updated Firestore document {email_id_for_summary} with live summary (post-analysis).")
                             except Exception as e_update:
                                 logging.error(f"Failed to update Firestore with live summary (post-analysis) for {email_id_for_summary}: {e_update}")
                             # --- !! END FIRESTORE UPDATE !! ---
                         else:
                             response_text = f"Sorry, I couldn't generate a summary for `{email_id_for_summary}` even after the analysis. Error: {summary_result}"
                             context_object = {"hint": "error", "data": {"id": email_id_for_summary}}
                     except Exception as e:
                         logging.error(f"Error during live summarization after analysis for {email_id_for_summary}: {e}", exc_info=True)
                         response_text = f"An unexpected error occurred while summarizing email `{email_id_for_summary}`."
                         context_object = {"hint": "error", "data": {"id": email_id_for_summary}}

                     if memory_system:
                         memory_system.add_interaction(user_query, response_text, {"type": "confirm_summary_post_analysis", "email_id": email_id_for_summary})
                     return response_text, context_object
                 else:
                     logging.warning("Context hint 'prompt_summary_after_analysis' found, but email_id or email_data missing.")
             else:
                 response_text = "Okay, understood. Let me know if there's anything else."
                 context_object = {"hint": "default", "data": None}
                 if memory_system:
                     memory_system.add_interaction(user_query, response_text, {"type": "decline_summary_post_analysis", "email_id": email_id_for_summary})
                 return response_text, context_object

        # --- END NEW CHECKS ---
    
    # --- Greeting Logic Check (MODIFIED) ---
    GREETING_KEYWORDS = {"hello", "hi", "hey", "good morning", "good afternoon", "good evening"}
    # Create a regex pattern for whole word matching
    # Escape any special regex characters in keywords if they could exist (unlikely for these simple greetings)
    greeting_pattern_parts = [re.escape(kw) for kw in GREETING_KEYWORDS]
    GREETING_KEYWORDS_PATTERN = r"\b(" + "|".join(greeting_pattern_parts) + r")\b"
    
    # Check if the query primarily consists of a greeting or starts with one,
    # and is relatively short, to avoid misinterpreting longer commands.
    is_primarily_greeting = False
    if len(query_lower.split()) <= 3: # Only consider short phrases as primarily greetings
        is_primarily_greeting = bool(re.search(GREETING_KEYWORDS_PATTERN, query_lower))
    
    logging.debug(f"generate_agent_response: is_primarily_greeting={is_primarily_greeting}, memory_system_exists={bool(memory_system)}")
    if is_primarily_greeting and memory_system: # Use the new flag
        logging.debug("generate_agent_response: Entering GREETING_KEYWORDS block (is_primarily_greeting).")
        greeting = random.choice(GREETING_MESSAGES)
        response_text = f"{greeting}\n\n{response_templates['greeting_help']}"
        context_object = {"hint": "greeting_help_displayed", "data": None}
        if memory_system: memory_system.add_interaction(user_query, response_text, {"type": "greeting_help"})
        return response_text, context_object

    # Get conversation context from memory (keep this)
    conversation_context = {}
    if memory_system:
        conversation_context = memory_system.get_conversation_context(user_query)
    if USER_PROFILE_KEY in st.session_state:
        st.session_state[USER_PROFILE_KEY]["last_active"] = datetime.now()
        st.session_state[USER_PROFILE_KEY]["total_interactions"] += 1

    try:
        # Check for status/how are you queries
        if "status" in query_lower or "how are you" in query_lower:
            # --- FIX: Use actual database call for feedback count ---
            state = get_agent_state()
            try:
                count = database_utils.get_feedback_count() # Use the function
            except Exception as e_count:
                logging.error(f"Error getting feedback count from database_utils: {e_count}")
                count = "Error fetching" # Show error in UI if count fails
            # --- END FIX ---

            if "how are you" in query_lower:
                status_intro = f"I'm doing well, thanks for asking! "
            else:
                status_intro = ""

            status_details = f"\n\n*   **Current Feedback Count:** {count}\n*   **Last Retrain Used Count:** {state.get('last_feedback_count', 0)}\n*   **Last Retrained/State Update:** {state.get('last_updated', 'N/A')}"
            response_text = status_intro + response_templates["status_base"] + status_details
            context_object = {"hint": "status_displayed", "data": None}
            if memory_system: memory_system.add_interaction(user_query, response_text, {"type": "status_check"})

        # Check for high priority email queries
        elif "critical emails" in query_lower or "high priority" in query_lower or "important emails" in query_lower:
            logging.debug("generate_agent_response: Matched 'high priority' keywords.")
            # Initialize response_text and context_object for this branch
            current_response_text = ""
            current_context_object = {"hint": "default", "data": None}

            try:
                high_prio_emails = database_utils.get_todays_high_priority_emails()
                
                if high_prio_emails: # Check if the list is not empty
                    current_response_text = f"I found **{len(high_prio_emails)}** CRITICAL/HIGH priority emails processed today:\n\n---\n"
                    email_ids_shown = []
                    for i, email in enumerate(high_prio_emails[:5], 1):
                        subject = email.get('subject', '[No Subject]')
                        sender = email.get('sender', '[No Sender]')
                        prio = email.get('priority', 'N/A')
                        email_id = email.get('email_id')
                        if email_id:
                            email_ids_shown.append(email_id)
                        sender_display = (sender[:30] + '...') if len(sender) > 33 else sender
                        subject_display = (subject[:50] + '...') if len(subject) > 53 else subject
                        current_response_text += f"\n{i}. **{prio}**: {subject_display} (From: {sender_display})"
                        if email_id:
                            current_response_text += f" (ID: `{email_id}`)"
                    current_response_text += f"\n\n---"
                    current_response_text += f"\n\nWould you like me to summarize any of these emails? Just ask me to 'summarize email [ID]'. Or I can help draft a reply to any of them."
                    current_context_object = {"hint": "email_list_displayed", "data": {"ids": email_ids_shown}}
                else: # high_prio_emails is empty
                    current_response_text = response_templates["no_priority"]
                    current_context_object = {"hint": "default", "data": None}

            except Exception as e_prio:
                logging.error(f"Error getting high priority emails from database_utils: {e_prio}", exc_info=True)
                high_prio_emails = [] # Ensure it's a list for memory logging
                current_response_text = "Sorry, I encountered an error while fetching high priority emails."
                current_context_object = {"hint": "error", "data": None}
            
            if memory_system: # Log interaction
                memory_system.add_interaction(user_query, current_response_text, {"type": "priority_emails", "count": len(high_prio_emails) if high_prio_emails else 0})
            
            return current_response_text, current_context_object # Always return

            email_ids_shown = []
            if high_prio_emails:
                response_text = f"I found **{len(high_prio_emails)}** CRITICAL/HIGH priority emails processed today:\n\n---\n"
                for i, email in enumerate(high_prio_emails[:5], 1): # Limit display
                    # Use .get with defaults for safety
                    subject = email.get('subject', '[No Subject]')
                    sender = email.get('sender', '[No Sender]')
                    prio = email.get('priority', 'N/A')
                    email_id = email.get('email_id') # ID should be added by the fetch function

                    if email_id:
                        email_ids_shown.append(email_id)

                    # Use html.escape for safety, but remove for readability on sender/subject
                    sender_display = (sender[:30] + '...') if len(sender) > 33 else sender
                    subject_display = (subject[:50] + '...') if len(subject) > 53 else subject

                    response_text += f"\n{i}. **{prio}**: {subject_display} (From: {sender_display})"
                    if email_id: # Add ID if available
                        response_text += f" (ID: `{email_id}`)"

                response_text += f"\n\n---"
                response_text += f"\n\nWould you like me to summarize any of these emails? Just ask me to 'summarize email [ID]'. Or I can help draft a reply to any of them."
                context_object = {"hint": "email_list_displayed", "data": {"ids": email_ids_shown}}
            else:
                # Check if the fetch function returned an empty list (no error) or if it failed earlier
                if 'response_text' not in locals(): # Only set this if no error occurred during fetch
                    response_text = response_templates["no_priority"]
                    context_object = {"hint": "default", "data": None}

            if memory_system and 'response_text' in locals(): # Log only if response was generated
                memory_system.add_interaction(user_query, response_text, {"type": "priority_emails", "count": len(high_prio_emails)})

        # Check for action request emails
        elif (("action" in query_lower and "request" in query_lower) or
              "need action" in query_lower or
              "require action" in query_lower or
              query_lower == "list emails requiring action"):
            action_emails = fetch_emails_by_purpose("Action Request", 5) # Fetch DF

            if not action_emails.empty:
                response_text = f"I found {len(action_emails)} emails marked as Action Requests. Here are the most recent ones:\n\n---\n"
                email_ids_for_context = []

                for i, email_row in enumerate(action_emails.iterrows(), 1):
                    email_data = email_row[1]
                    current_email_id = email_data['Email ID']

                    # --- FIX: Ensure only unique IDs are added ---
                    if current_email_id not in email_ids_for_context:
                        email_ids_for_context.append(current_email_id)
                    # --- END FIX ---

                    # Use html.escape for safety, but remove for readability on sender/subject
                    sender_display = email_data['Sender']
                    subject_display = email_data['Subject']
                    summary_display = html.escape(email_data['Summary']) if email_data['Summary'] != 'N/A' else 'N/A' # Escape only if not N/A
                    priority_display = email_data['Priority']

                    response_text += f"\n{i}. **{subject_display}** from {sender_display} - {priority_display} priority (ID: `{current_email_id}`)" # Add ID here
                    if summary_display != 'N/A' and summary_display:
                        response_text += f"\n   *Summary: {summary_display}*"
                    response_text += "\n"

                response_text += f"\n---\n\nWould you like me to help you draft responses to any of these emails? Or I can help prioritize which ones to handle first."
                context_object = {"hint": "action_list", "data": {"ids": email_ids_for_context}}
            else:
                response_text = "I couldn't find any emails marked as requiring action."
                context_object = {"hint": "default", "data": None}

            if memory_system:
                memory_system.add_interaction(user_query, response_text, {"type": "action_emails"})

        # Check for summarize queries
        elif "summarize email" in query_lower or "summary for" in query_lower:
            match = re.search(r'([a-zA-Z0-9]{10,})', query_lower) # More specific regex for typical IDs
            if match:
                email_id = match.group(1)
                email_ref = db.collection(EMAILS_COLLECTION).document(email_id)
                doc = email_ref.get()

                if doc.exists:
                    email_data = doc.to_dict()
                    summary = email_data.get('summary')
                    subject = email_data.get('subject', '[No Subject]')
                    sender = email_data.get('sender', '[No Sender]')

                    if summary and not str(summary).startswith("Error:"):
                        # Display the raw summary directly, escaping potentially harmful HTML
                        response_text = f"Here's my summary of the email from {html.escape(sender)} with subject '{html.escape(subject)}':\n\n---\n\n{html.escape(summary)}\n\n---\n\n"
                        response_text += "\nWould you like me to help you respond to this email or take any other action?"
                        context_object = {"hint": "summary_displayed", "data": {"id": email_id, "subject": subject, "sender": sender}}
                    else:
                        # --- MODIFIED: Summary missing or error ---
                        # Fetch existing analysis details for context
                        existing_purpose = email_data.get('llm_purpose', 'N/A')
                        existing_priority = email_data.get('priority', 'N/A')
                        existing_urgency = email_data.get('llm_urgency', 'N/A')

                        # Construct the prompt offering a choice
                        response_text = (
                            f"I don't have a pre-generated summary for the email '{html.escape(subject)}' (ID: {email_id}).\n\n"
                            f"My initial assessment was:\n"
                            f"- Purpose: {existing_purpose}\n"
                            f"- Priority: {existing_priority}\n"
                            f"- Urgency Score: {existing_urgency}\n\n"
                            f"Would you like me to **generate a summary** now, or perform a **fresh analysis** of this email?"
                        )
                        # Set a new context hint to handle the choice
                        context_object = {"hint": "prompt_summary_or_analysis", "data": {"id": email_id, "subject": subject, "email_data": email_data}} # Store full email_data
                        # --- END MODIFICATION ---
                else:
                    # Email ID not found in Firestore
                    response_text = response_templates["id_not_found"].format(email_id=email_id)
                    context_object = {"hint": "default", "data": None}
            else:
                # No email ID found in the user query
                response_text = response_templates["id_missing_for_summary"]
                context_object = {"hint": "default", "data": None}

            if memory_system:
                memory_system.add_interaction(user_query, response_text, {"type": "email_summary_request", "email_id": email_id if match else None})

        
        # --- *** NEW: Handle draft reply requests *** ---
        elif "draft" in query_lower and ("reply" in query_lower or "response" in query_lower):
            match = re.search(r'([a-zA-Z0-9]{10,})', query_lower) # Regex for ID
            if match:
                email_id = match.group(1)
                logging.info(f"Draft requested for email ID: {email_id}")
                # 1. Fetch original email data from Firestore
                try:
                    email_ref = db.collection(EMAILS_COLLECTION).document(email_id)
                    doc = email_ref.get()
                    if not doc.exists:
                        logging.warning(f"Email {email_id} not found in Firestore for drafting.")
                        response_text = response_templates["id_not_found"].format(email_id=email_id)
                        context_object = {"hint": "error", "data": {"id": email_id}}
                    else:
                        email_data_dict = doc.to_dict()
                        email_data_dict['id'] = email_id # Ensure ID is present
                        
                        # --- ADDED: Extract recipient and subject ---
                        original_sender = email_data_dict.get('sender')
                        recipient_email = _extract_email_address(original_sender)
                        original_subject = email_data_dict.get('subject', '[No Subject]')
                        # --- END ADDED ---
                        
                        # 2. Call the drafting function from agent_logic
                        with st.spinner(f"Drafting reply for email `{email_id}`..."):
                            # For now, use a generic response type. Can be refined later.
                            response_type = "standard_reply"
                            draft_text = generate_email_response(
                                llm_client=llm_client,
                                email_data=email_data_dict,
                                response_type=response_type,
                                config=config,
                                memory=memory_system
                            )

                        # 3. Format and display the response
                        if draft_text and not draft_text.startswith("Error:"):
                            subject_display = html.escape(email_data_dict.get('subject', '[No Subject]'))
                            response_text = (
                                f"Okay, here's a draft reply for the email '{subject_display}' (ID: `{email_id}`):\n\n"
                                f"---\n"
                                f"```text\n" # Use text code block for plain text email
                                f"{draft_text}\n"
                                f"```\n"
                                f"---\n\n"
                                f"How does this look? You can ask me to revise it (e.g., 'make it shorter', 'make it more formal')."
                            )
                            # --- MODIFIED: Add recipient/subject to context data ---
                            context_object = {
                                "hint": "draft_displayed",
                                "data": {
                                    "email_id": email_id,
                                    "draft_text": draft_text,
                                    "recipient_email": recipient_email, # Store recipient
                                    "original_subject": original_subject # Store subject
                                }
                            }
                            # Optionally store draft in session state if needed for complex editing later
                            # st.session_state["drafts"].append({"id": f"draft_{time.time()}", "email_id": email_id, "text": draft_text})
                        else:
                            logging.error(f"Draft generation failed for {email_id}: {draft_text}")
                            response_text = f"Sorry, I wasn't able to generate a draft for email `{email_id}` at this time. The error was: {draft_text}"
                            context_object = {"hint": "error", "data": {"id": email_id}}

                except Exception as e:
                    logging.error(f"Error during draft generation process for {email_id}: {e}", exc_info=True)
                    response_text = f"An unexpected error occurred while trying to draft a reply for email `{email_id}`."
                    context_object = {"hint": "error", "data": {"id": email_id}}

            else: # No ID found in the query
                response_text = response_templates["id_missing_for_draft"]
                context_object = {"hint": "default", "data": None}

            if memory_system:
                memory_system.add_interaction(user_query, response_text, {"type": "draft_reply_requested", "email_id": email_id if match else None})
        
        # Check for greeting/help queries
        elif "hello" in query_lower or "hi" in query_lower or "help" in query_lower:
            logging.debug("generate_agent_response: Matched general 'hello/hi/help' keywords.")
            if memory_system and ("hello" in query_lower or "hi" in query_lower):
                greeting = memory_system.get_greeting()
                response_text = (greeting + "\n\n" + response_templates["greeting_help"]) if greeting else response_templates["greeting_help"]
            else:
                response_text = response_templates["greeting_help"]
            context_object = {"hint": "greeting_help_displayed", "data": None}
            if memory_system: memory_system.add_interaction(user_query, response_text, {"type": "help_request"})

        # Handle feedback-related questions
        elif "feedback" in query_lower or "learning" in query_lower or "improve" in query_lower:
            trigger_count = config.get('retraining', {}).get('trigger_feedback_count', 10) # Get from config
            response_text = f"I learn from your feedback! When you correct my priority assessments in the Email Feedback tab, I store those corrections and use them to improve my classification. After collecting enough feedback ({trigger_count} corrections), I automatically retrain my model to make better predictions."
            context_object = {"hint": "learning_explained", "data": None}
            if memory_system: memory_system.add_interaction(user_query, response_text, {"type": "feedback_explanation"})

        # Handle questions about autonomous mode
        elif "autonomous" in query_lower or "automatic" in query_lower:
            current_mode = st.session_state.get("autonomous_mode", False) # Get current state
            if "enable" in query_lower or "turn on" in query_lower or "activate" in query_lower:
                st.session_state["autonomous_mode"] = True
                response_text = "I've enabled autonomous mode. I'll now be more proactive and take initiative when handling your emails. I'll suggest actions and offer assistance without you having to ask explicitly."
                context_object = {"hint": "autonomous_enabled", "data": None}
            elif "disable" in query_lower or "turn off" in query_lower or "deactivate" in query_lower:
                st.session_state["autonomous_mode"] = False
                response_text = "I've disabled autonomous mode. I'll now wait for your explicit instructions before taking actions on emails."
                context_object = {"hint": "autonomous_disabled", "data": None}
            else:
                response_text = f"Autonomous mode is currently {'enabled' if current_mode else 'disabled'}. When enabled, I'll be more proactive and take initiative in handling your emails. Would you like to enable or disable autonomous mode?"
                context_object = {"hint": "autonomous_status", "data": None}
            if memory_system: memory_system.add_interaction(user_query, response_text, {"type": "autonomous_mode", "status": st.session_state["autonomous_mode"]})

        # Handle questions about the agent itself
        elif "who are you" in query_lower or "what can you do" in query_lower or "your name" in query_lower:
            response_text = f"I'm Maia, your AI email assistant. I help you manage your inbox by analyzing emails, identifying important messages, providing summaries, and learning from your feedback. I can classify emails by priority and purpose, generate summaries of important emails, and help you take actions like archiving or responding to messages."
            if st.session_state.get("autonomous_mode", False):
                response_text += "\n\nI'm currently in autonomous mode, which means I'll be more proactive in offering assistance and suggesting actions. I'll learn from our interactions to better understand your preferences and email patterns."
            context_object = {"hint": "agent_description", "data": None}
            if memory_system: memory_system.add_interaction(user_query, response_text, {"type": "agent_description"})

        # Enhanced capabilities for email types (questions)
        elif "questions" in query_lower or "question emails" in query_lower:
            question_emails = fetch_emails_by_purpose("Question", 5)
            if not question_emails.empty:
                response_text = f"I found {len(question_emails)} emails with questions. Here are the most recent ones:\n\n---\n"
                email_ids = []
                for i, email_row in enumerate(question_emails.iterrows(), 1):
                    email_data = email_row[1]
                    current_email_id = email_data['Email ID']
                    if current_email_id not in email_ids: email_ids.append(current_email_id) # Add unique ID
                    sender_display = email_data['Sender']
                    subject_display = email_data['Subject']
                    summary_display = html.escape(email_data['Summary']) if email_data['Summary'] != 'N/A' else 'N/A'
                    priority_display = email_data['Priority']
                    response_text += f"\n{i}. **{subject_display}** from {sender_display} - {priority_display} priority (ID: `{current_email_id}`)"
                    if summary_display != 'N/A' and summary_display:
                        response_text += f"\n   *Summary: {summary_display}*\n"
                    else:
                        response_text += "\n" # Add newline even if no summary
                response_text += f"\n---\n\nWould you like me to help draft responses to any of these questions?"
                context_object = {"hint": "question_list", "data": {"ids": email_ids}}
            else:
                response_text = "I couldn't find any emails marked as containing questions."
                context_object = {"hint": "default", "data": None}
            if memory_system: memory_system.add_interaction(user_query, response_text, {"type": "question_emails"})

        
        # Fallback for unknown queries
        else:
            related_convs = []
            if memory_system:
                related_convs = memory_system.get_related_conversations(user_query)
            if related_convs:
                latest_related = related_convs[0]
                response_text = f"I think you're asking about something similar to our earlier conversation. Previously, you asked me about '{latest_related.get('user_message', '')}'. Is there something specific from that topic you'd like me to help with?"
                context_object = {"hint": "context_recall", "data": {"previous_query": latest_related.get('user_message', '')}}
            else:
                response_text = response_templates["fallback"].format(user_query=user_query)
                context_object = {"hint": "default", "data": None}
            if memory_system: memory_system.add_interaction(user_query, response_text, {"type": "unknown_query"})

    except Exception as e:
        logging.error(f"Error generating response: {e}", exc_info=True)
        response_text = response_templates["general_error"].format(error_message=str(e))
        context_object = {"hint": "error", "data": None}

    return (response_text, context_object)

def render_suggestion_history_section():
    """Render the suggestion history section in the Settings tab"""
    st.markdown("### Suggestion History")
    st.info("This shows your recent interactions with suggestions.")
    
    # Get history data
    history_records = proactive_agent.suggestion_history.get_recent_history(limit=50)
    
    if not history_records:
        st.info("No suggestion history available yet.")
        return
    
    # Prepare data for display
    history_data = []
    for record in history_records:
        # Format timestamps
        timestamp = record.get('timestamp')
        if timestamp:
            if hasattr(timestamp, 'strftime'):
                shown_time = timestamp.strftime('%Y-%m-%d %H:%M')
            else:
                shown_time = str(timestamp)
        else:
            shown_time = 'N/A'
            
        # Format response
        response = 'No Response'
        if record.get('was_accepted') is True:
            response = '✅ Accepted'
        elif record.get('was_accepted') is False:
            response = '❌ Dismissed'
            
        # Add to display data
        history_data.append({
            'Date': shown_time,
            'Suggestion': record.get('suggestion_title', 'Unknown'),
            'Type': record.get('suggestion_type', 'unknown'),
            'Priority': record.get('suggestion_priority', 'medium').title(),
            'Response': response
        })
    
    # Create DataFrame
    history_df = pd.DataFrame(history_data)
    
    # Add to display with column configuration
    st.dataframe(
        history_df,
        column_config={
            'Date': st.column_config.TextColumn('Date Shown'),
            'Suggestion': st.column_config.TextColumn('Suggestion Title'),
            'Type': st.column_config.TextColumn('Type'),
            'Priority': st.column_config.TextColumn('Priority'),
            'Response': st.column_config.TextColumn('Your Response'),
        },
        hide_index=True,
        use_container_width=True
    )
    
    # Add statistics
    st.markdown("### Suggestion Analytics")
    stats = proactive_agent.suggestion_history.get_stats(days_back=30)
    
    if stats:
        col1, col2, col3 = st.columns(3)
        
        with col1:
            total_shown = stats.get('total_shown', 0)
            st.metric("Suggestions Shown", f"{total_shown}")
            
        with col2:
            acceptance_rate = stats.get('acceptance_rate', 0) * 100
            st.metric("Acceptance Rate", f"{acceptance_rate:.1f}%")
            
        with col3:
            dismissal_rate = stats.get('dismissal_rate', 0) * 100
            st.metric("Dismissal Rate", f"{dismissal_rate:.1f}%")
            
        # Display type breakdown
        st.markdown("#### Suggestion Performance by Type")
        
        by_type = stats.get('by_type', {})
        type_data = []
        
        for suggestion_type, type_stats in by_type.items():
            shown = type_stats.get('shown', 0)
            if shown > 0:
                accepted = type_stats.get('accepted', 0)
                acceptance_rate = (accepted / shown) * 100
                
                # Format type name for display
                display_name = suggestion_type.replace('_', ' ').title()
                
                type_data.append({
                    'Type': display_name,
                    'Shown': shown,
                    'Accepted': accepted,
                    'Acceptance Rate': f"{acceptance_rate:.1f}%"
                })
        
        if type_data:
            type_df = pd.DataFrame(type_data)
            st.dataframe(type_df, hide_index=True, use_container_width=True)


# --- Main Streamlit App Layout ---
# Display agent header
display_agent_header()

# Tabs for organization with improved design
tabs = st.tabs(["💬 Chat & Dashboard", "✉️ Email Feedback", "📊 Insights", "⚙️ Settings", "🤖 Autonomous"])

# Check for current tab setting from previous run
if CURRENT_TAB_KEY in st.session_state:
    tab_idx = st.session_state[CURRENT_TAB_KEY]
    # No easy way to programmatically select a tab in Streamlit
    # The tabs will default to the first one

with tabs[0]:
    st.markdown("## Chat with Maia")
    
    # Chat Interface
    chat_container = st.container(height=500) # Set height for scrollability
    with chat_container:
        # Display chat history with custom styling
        for message in st.session_state[CHAT_HISTORY_KEY]:
            display_chat_message(message["role"], message["content"])
    
    # Check for and process any pending suggestion actions
    rerun_needed_suggestion = process_pending_suggestion_actions()
    if rerun_needed_suggestion:
        st.rerun()
    # --- Display Draft Action Buttons Conditionally ---
    show_draft_buttons = False
    draft_context_data = None
    if st.session_state.get(CHAT_HISTORY_KEY):
        last_message = st.session_state[CHAT_HISTORY_KEY][-1]
        if last_message["role"] == "assistant" and last_message.get("context", {}).get("hint") == "draft_displayed":
            show_draft_buttons = True
            draft_context_data = last_message.get("context", {}).get("data", {})

    if show_draft_buttons and draft_context_data:
        st.markdown("---")
        st.markdown("##### Draft Actions:")
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            # Copy Button
            draft_text_to_copy = draft_context_data.get("draft_text", "")
            if st.button("👍 Looks Good (Copy)", key="copy_draft_button"):
                try:
                    pyperclip.copy(draft_text_to_copy)
                    st.success("Draft copied to clipboard!")
                    # Optionally add a confirmation message to chat
                    copy_confirm_msg = {
                        "role": "assistant",
                        "content": "Great! I've copied the draft to your clipboard.",
                        "context": {"hint": "draft_displayed", "data": draft_context_data} # <--- CORRECTED LINE
                    }
                    st.session_state[CHAT_HISTORY_KEY].append(copy_confirm_msg)
                    # We might want to clear the 'draft_displayed' hint here or let the next user input handle it.
                    # For now, let's just rerun to show the confirmation.
                    time.sleep(0.5) # Short pause for user to see success message
                    st.rerun()
                except Exception as e:
                    logging.error(f"Failed to copy to clipboard: {e}")
                    st.error("Failed to copy to clipboard. You can manually copy the text from the message above.")

        with col2:
            # Revise Button
            if st.button("🔄 Revise...", key="revise_draft_button"):
                # Add assistant prompt asking for revision instructions
                revise_prompt_msg = {
                    "role": "assistant",
                    "content": "Okay, how should I revise the draft?",
                    # Set new hint, pass original draft data for context
                    "context": {"hint": "awaiting_revision_instruction", "data": draft_context_data}
                }
                st.session_state[CHAT_HISTORY_KEY].append(revise_prompt_msg)
                st.rerun() # Rerun to display the prompt
        
        # --- MODIFIED: Use Gmail Compose Link Button ---
        with col3:
            # Send via Gmail Button (modified)
            recipient = draft_context_data.get("recipient_email")
            subject = draft_context_data.get("original_subject")
            body = draft_context_data.get("draft_text")
            email_id_for_send = draft_context_data.get("email_id") # Get email_id for logging
        
            if recipient and body: # Ensure we have recipient and body to send
                gmail_compose_link = _create_gmail_compose_link(recipient, subject, body)
                if gmail_compose_link:
                    if st.button("🚀 Send via Gmail", key="send_via_gmail_button"):
                        # 1. Add assistant message to chat
                        send_confirm_msg = {
                            "role": "assistant",
                            "content": f"Okay, I've prepared the draft for Gmail. You can review and send it there.\n\n[Open Draft in Gmail]({gmail_compose_link})\n\nReady for your next query.",
                            "context": {"hint": "gmail_link_action_taken", "data": None} # Neutral hint
                        }
                        st.session_state[CHAT_HISTORY_KEY].append(send_confirm_msg)
        
                        # 2. Open the link (using st.markdown for a clickable link in the new message)
                        # The link is now part of the chat message.
                        # If you want to *also* auto-open, it's trickier with st.button's direct action.
                        # For simplicity, we'll rely on the user clicking the link in the chat.
                        # If direct auto-opening is critical, we might need JavaScript, which is more complex.
        
                        st.success("Gmail compose link ready in chat!") # Immediate feedback
                        if memory: # Access memory if available
                            memory.add_interaction(
                                "Clicked 'Send via Gmail' button", 
                                send_confirm_msg["content"], 
                                {"type": "send_draft_button_link", "email_id": email_id_for_send}
                            )
                        time.sleep(0.5)
                        st.rerun()
                else:
                    st.button("🚀 Send via Gmail", key="send_gmail_button_link_fail", disabled=True, help="Could not generate Gmail link.")
            else:
                st.button("🚀 Send via Gmail", key="send_gmail_button_no_data", disabled=True, help="Missing recipient or draft text.")
        
        with col4:
            # Accept Draft Button
            if st.button("✅ Accept Draft", key="accept_draft_button"):
                accept_message = {
                    "role": "assistant",
                    "content": "Draft accepted. Ready for your next query.",
                    "context": {"hint": "draft_accepted_ready_for_next", "data": None}
                }
                st.session_state[CHAT_HISTORY_KEY].append(accept_message)
                st.success("Draft accepted!") # Optional immediate feedback
                time.sleep(0.5) # Short pause
                st.rerun()
    # Quick action buttons
    latest_assistant_msg = None
    for msg in reversed(st.session_state[CHAT_HISTORY_KEY]):
        if msg["role"] == "assistant":
            latest_assistant_msg = msg
            break
    
    if latest_assistant_msg:
        latest_hint = latest_assistant_msg.get("context", {}).get("hint", "default")
        latest_data = latest_assistant_msg.get("context", {}).get("data")
        
        st.markdown("---")
        st.markdown("### Quick Actions")
        
        action_buttons = []
        
        if latest_hint == "status_displayed":
            action_buttons = [
                {"label": "📋 Show High Priority", "action": "Show high priority emails today"},
                {"label": "📝 List Action Requests", "action": "List emails requiring action"},
                {"label": "❓ Help", "action": "Help"}
            ]
        elif latest_hint == "email_list_displayed":
            action_buttons = [
                {"label": "ℹ️ Check Status", "action": "What is the agent status?"},
                {"label": "📝 List Action Requests", "action": "List emails requiring action"},
                {"label": "❓ Help", "action": "Help"}
            ]
            if latest_data and isinstance(latest_data.get("ids"), list) and latest_data["ids"]:
                action_buttons.append({
                    "label": f"📄 Summarize First ({latest_data['ids'][0][:6]}...)",
                    "action": f"Summarize email {latest_data['ids'][0]}"
                })
        elif latest_hint == "summary_displayed":
            action_buttons = [
                {"label": "ℹ️ Check Status", "action": "What is the agent status?"},
                {"label": "📋 Show High Priority", "action": "Show high priority emails today"}
            ]
            if latest_data and isinstance(latest_data.get("id"), str):
                action_buttons.append({
                    "label": f"🗑️ Archive ({latest_data['id'][:6]}...)",
                    "action": f"archive_{latest_data['id']}"
                })
        elif latest_hint in ["action_list", "question_list"]:
            action_buttons = [
                {"label": "ℹ️ Check Status", "action": "What is the agent status?"},
                {"label": "📋 Show High Priority", "action": "Show high priority emails today"},
                {"label": "❓ Help", "action": "Help"}
            ]
            if latest_data and isinstance(latest_data.get("ids"), list) and latest_data["ids"]:
                action_buttons.append({
                    "label": f"📄 Summarize First ({latest_data['ids'][0][:6]}...)",
                    "action": f"Summarize email {latest_data['ids'][0]}"
                })
        else:
            action_buttons = [
                {"label": "ℹ️ Check Status", "action": "What is the agent status?"},
                {"label": "📋 Show High Priority", "action": "Show high priority emails today"},
                {"label": "📝 List Action Requests", "action": "List emails requiring action"},
                {"label": "❓ Help", "action": "Help"}
            ]
        
        cols = st.columns(len(action_buttons))
        for i, button in enumerate(action_buttons):
            if cols[i].button(button["label"], key=f"action_{i}_{latest_hint}"):
                if button["action"].startswith("archive_"):
                    email_id = button["action"].split("_")[1]
                    with st.spinner("Submitting archive request..."):
                        if request_email_action(email_id, "archive"):
                            st.success(f"Archive request sent for email {email_id[:6]}... Successfully!")
                            # Add message to chat about archiving
                            archive_confirm = {
                                "role": "assistant",
                                "content": f"I've submitted a request to archive email {email_id[:6]}... The email will be moved out of your inbox shortly.",
                                "context": {"hint": "archive_confirmed", "data": None}
                            }
                            st.session_state[CHAT_HISTORY_KEY].append(archive_confirm)
                            st.rerun()
                        else:
                            st.error("Failed to submit archive request.")
                else:
                    # Normal chat actions
                    st.session_state[CHAT_HISTORY_KEY].append({"role": "user", "content": button["action"]})
                    response_text, response_context = generate_agent_response(
                        button["action"],
                        memory_system=memory,
                        llm_client=llm_client,
                        config=ui_config
                    )
                    # --- ADD DEBUG LOG HERE ---
                    logging.debug(f"Quick Action: role='assistant', content='{response_text}', context='{response_context}'")
                    # --- END DEBUG LOG ---
                    st.session_state[CHAT_HISTORY_KEY].append({
                        "role": "assistant",
                        "content": response_text,
                        "context": response_context
                    })
                    st.rerun()
    
    # Chat input
    st.markdown("---")
    chat_input = st.chat_input("Ask me anything about your emails...", key="chat_input")
    
    if chat_input:
        # Add user message to chat
        st.session_state[CHAT_HISTORY_KEY].append({"role": "user", "content": chat_input})
        
        # Generate response with animation
        with chat_container: # Display inside the container
            display_chat_message("user", chat_input) # Display user message immediately
            with st.spinner(get_random_thinking()):
                response_text, response_context = generate_agent_response(
                    chat_input,
                    memory_system=memory,
                    llm_client=llm_client,
                    config=ui_config
                )
            # Display assistant response after generation
            display_chat_message("assistant", response_text, animation=True)

        # Save assistant message to history AFTER displaying
        st.session_state[CHAT_HISTORY_KEY].append({
            "role": "assistant",
            "content": response_text,
            "context": response_context
        })
        # Rerun to update the displayed chat history smoothly
        st.rerun()
    

    # Render Dashboard below chat
    st.markdown("---") # Separator
    render_enhanced_dashboard()
        
with tabs[1]:
    st.markdown("## Email Feedback")
    st.info("Help me learn by correcting my priority assessments below. Your feedback improves my classification over time.")

    # Add guidance for double-clicking
    st.info("💡 **Tip:** Double-click on any 'Correct Priority?' or 'Purpose' cell to open the dropdown menu and provide feedback.")

    # Display Success Message from Previous Run
    if FEEDBACK_SUCCESS_INFO_KEY in st.session_state and st.session_state[FEEDBACK_SUCCESS_INFO_KEY]:
        success_count = st.session_state[FEEDBACK_SUCCESS_INFO_KEY]
        st.success(f"Thank you! I've recorded your feedback for {success_count} email(s) and will use it to improve my classifications.")
        st.session_state[FEEDBACK_SUCCESS_INFO_KEY] = None

    if st.button("🔄 Refresh Email Table", key="refresh_email_table"):
        # Store current tab
        st.session_state[CURRENT_TAB_KEY] = 1
        
        st.cache_data.clear()
        # Clear suggestion cache
        if SUGGESTIONS_STATE_KEY in st.session_state:
            del st.session_state[SUGGESTIONS_STATE_KEY]
        if LAST_DF_HASH_KEY in st.session_state:
            del st.session_state[LAST_DF_HASH_KEY]
        # Clear other relevant states
        if PROCESSED_FEEDBACK_INDICES_KEY in st.session_state: 
            st.session_state[PROCESSED_FEEDBACK_INDICES_KEY].clear()
        if ORIGINAL_DF_KEY in st.session_state: 
            del st.session_state[ORIGINAL_DF_KEY]
        if PENDING_FEEDBACK_KEY in st.session_state: 
            st.session_state[PENDING_FEEDBACK_KEY] = []
        if FEEDBACK_SUCCESS_INFO_KEY in st.session_state: 
            st.session_state[FEEDBACK_SUCCESS_INFO_KEY] = None
        st.rerun()

    # Data Fetching and Editor Display
    df_emails_raw = fetch_recent_emails(limit=100)
    if ORIGINAL_DF_KEY not in st.session_state or st.session_state[ORIGINAL_DF_KEY].empty:
         st.session_state[ORIGINAL_DF_KEY] = df_emails_raw.copy()
    elif len(st.session_state[ORIGINAL_DF_KEY]) != len(df_emails_raw):
         st.session_state[ORIGINAL_DF_KEY] = df_emails_raw.copy()

    if not db: st.warning("Cannot connect to Firestore...")
    elif df_emails_raw.empty: st.info("No recently processed emails found in Firestore...")
    else:
        column_config = {
            "Email ID": st.column_config.TextColumn(disabled=True, width="small"),
            "Processed At": st.column_config.TextColumn(width="small", disabled=True),
            "Agent Priority": st.column_config.TextColumn(width="small", disabled=True),
            "Sender": st.column_config.TextColumn(width="medium", disabled=True),
            "Subject": st.column_config.TextColumn(width="large", disabled=True),
            "Summary": None,
            "Your Correction": st.column_config.SelectboxColumn(
                "Correct Priority?", 
                options=DISPLAY_OPTIONS, 
                required=False, 
                default="N/A", 
                width="medium"
            ),
            "Purpose": st.column_config.SelectboxColumn(
                "Purpose", 
                options=PURPOSE_OPTIONS, 
                required=False, 
                width="medium"
            )
        }
        
        df_to_edit = st.session_state.get(ORIGINAL_DF_KEY, df_emails_raw)
        edited_df_output = st.data_editor(
            df_to_edit,
            column_config=column_config,
            use_container_width=True,
            hide_index=True,
            key=EDITOR_STATE_KEY,
            on_change=handle_editor_changes,
            num_rows="fixed",
            disabled=["Email ID", "Processed At", "Agent Priority", "Sender", "Subject"]
        )

    # Process Pending Feedback
    processed_count_this_run = 0
    rerun_needed_for_message = False
    if PENDING_FEEDBACK_KEY in st.session_state and st.session_state[PENDING_FEEDBACK_KEY]:
        logging.info(f"Processing {len(st.session_state[PENDING_FEEDBACK_KEY])} pending feedback items...")
        items_to_process = st.session_state[PENDING_FEEDBACK_KEY][:]
        st.session_state[PENDING_FEEDBACK_KEY] = []

        for item in items_to_process:
            feedback_type = item.get("feedback_type", "priority")
            
            if feedback_type == "priority":
                success = submit_feedback_to_firestore(
                    item["email_id"], 
                    item["original_priority"],
                    corrected_priority=item["corrected_priority"],
                    sender=item["sender"],
                    feedback_type="priority"
                )
            elif feedback_type == "purpose":
                success = submit_feedback_to_firestore(
                    item["email_id"],
                    item["original_priority"],
                    corrected_purpose=item["corrected_purpose"],
                    sender=item["sender"],
                    feedback_type="purpose"
                )
            else:
                logging.error(f"Unknown feedback type: {feedback_type}")
                success = False
            
            if success:
                if "row_index" in item:
                    st.session_state.setdefault(PROCESSED_FEEDBACK_INDICES_KEY, set()).add(item["row_index"])
                processed_count_this_run += 1
            else:
                logging.error(f"Failed to submit {feedback_type} feedback for email {item['email_id']}")

        if processed_count_this_run > 0:
             logging.info(f"Finished processing {processed_count_this_run} pending feedback items.")
             st.session_state[FEEDBACK_SUCCESS_INFO_KEY] = processed_count_this_run
             # Remember current tab before rerun
             st.session_state[CURRENT_TAB_KEY] = 1  # Tab index for Email Feedback
             rerun_needed_for_message = True

    # Trigger rerun only if feedback was processed
    if rerun_needed_for_message:
        st.rerun()

with tabs[2]:
    st.markdown("## Email Insights")
    
    # Get the email data
    df_emails = fetch_recent_emails(limit=100)
    
    if df_emails.empty:
        st.info("No email data available to generate insights.")
    else:
        # Generate insights
        email_insights = analyze_email_patterns(df_emails)
        
        if not email_insights:
            st.warning("Could not generate insights from the available data.")
        else:
            # Create dashboard with insights and colored charts
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("### Priority Distribution")
                if 'priority_distribution' in email_insights:
                    # Create DataFrame for plotting
                    priority_data = pd.DataFrame({
                        'Priority': list(email_insights['priority_distribution'].keys()),
                        'Count': list(email_insights['priority_distribution'].values())
                    })
                    
                    # Create color map
                    color_map = {priority: PRIORITY_COLORS_CHART.get(priority, "#cccccc") for priority in priority_data['Priority']}
                    
                    # Create Plotly chart
                    fig = px.bar(
                        priority_data, 
                        x='Priority', 
                        y='Count',
                        color='Priority',
                        color_discrete_map=color_map,
                        template="plotly_dark"
                    )
                    
                    fig.update_layout(
                        margin=dict(l=0, r=0, t=20, b=0),
                        plot_bgcolor='rgba(0,0,0,0)',
                        paper_bgcolor='rgba(0,0,0,0)',
                        font=dict(size=12, color='#e0e0e0'),
                        xaxis=dict(title=None),
                        yaxis=dict(title=None),
                        showlegend=False
                    )
                    
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("No priority data available.")
            
            with col2:
                st.markdown("### Purpose Distribution")
                if 'purpose_distribution' in email_insights:
                    # Create DataFrame for plotting
                    purpose_data = pd.DataFrame({
                        'Purpose': list(email_insights['purpose_distribution'].keys()),
                        'Count': list(email_insights['purpose_distribution'].values())
                    })
                    
                    # Create color map
                    color_map = {purpose: PURPOSE_COLORS_CHART.get(purpose, "#cccccc") for purpose in purpose_data['Purpose']}
                    
                    # Create Plotly chart
                    fig = px.bar(
                        purpose_data, 
                        x='Purpose', 
                        y='Count',
                        color='Purpose',
                        color_discrete_map=color_map,
                        template="plotly_dark"
                    )
                    
                    fig.update_layout(
                        margin=dict(l=0, r=0, t=20, b=0),
                        plot_bgcolor='rgba(0,0,0,0)',
                        paper_bgcolor='rgba(0,0,0,0)',
                        font=dict(size=12, color='#e0e0e0'),
                        xaxis=dict(title=None),
                        yaxis=dict(title=None),
                        showlegend=False
                    )
                    
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("No purpose data available.")
            
            # Top senders section with green numbers
            st.markdown("### Top Senders")
            if 'top_senders' in email_insights and email_insights['top_senders']:
                sender_cols = st.columns(min(5, len(email_insights['top_senders'])))
                for i, (sender, count) in enumerate(email_insights['top_senders'][:5]):
                    # Extract first part of email for cleaner display
                    display_name = sender.split('@')[0] if '@' in sender else sender
                    display_name = display_name[:15] + '...' if len(display_name) > 15 else display_name
                    
                    with sender_cols[i]:
                        st.markdown(f"**#{i+1}**")
                        st.markdown(f"**{display_name}**")
                        # Use green color for email counts
                        st.markdown(f'<span class="email-count">↑ {count} emails</span>', unsafe_allow_html=True)
            else:
                st.info("No sender data available.")
            
            # Add common email patterns or agent observations
            st.markdown("### Agent Observations")
            
            # Calculate some additional insights
            total_emails = len(df_emails)
            high_priority = df_emails[df_emails['Agent Priority'].isin(['CRITICAL', 'HIGH'])].shape[0]
            high_prio_percentage = (high_priority / total_emails * 100) if total_emails > 0 else 0
            
            # Generate observations based on the data
            observations = []
            
            if high_prio_percentage > 30:
                observations.append("📈 **High volume of important emails**: Over 30% of your emails are high priority. Consider scheduling dedicated time to address these.")
            elif high_prio_percentage < 10:
                observations.append("✅ **Low urgent email volume**: Less than 10% of your emails require immediate attention. Your inbox seems well-managed!")
            
            if 'top_domains' in email_insights and email_insights['top_domains']:
                top_domain, top_domain_count = email_insights['top_domains'][0]
                if top_domain_count > total_emails * 0.3:
                    observations.append(f"🔍 **Dominant sender domain**: Over 30% of your emails come from *{top_domain}*. Consider creating a filter or rule for this domain.")
            
            if 'purpose_distribution' in email_insights:
                purposes = email_insights['purpose_distribution']
                if 'Action Request' in purposes and purposes['Action Request'] > total_emails * 0.25:
                    observations.append("⚠️ **High action items**: More than 25% of your emails require some action. I can help prioritize these for you.")
                
                if 'Notification' in purposes and 'Promotion' in purposes:
                    promo_notif_count = purposes.get('Notification', 0) + purposes.get('Promotion', 0)
                    if promo_notif_count > total_emails * 0.4:
                        observations.append("📣 **High promotional content**: Over 40% of your emails are promotions or notifications. Consider unsubscribing from unused newsletters.")
            
            if not observations:
                observations.append("📊 **Balanced email patterns**: Your email patterns appear balanced with no obvious pain points.")
            
            for obs in observations:
                st.markdown(obs)

with tabs[3]:
    st.markdown("## Settings & Preferences")

    # User Profile Section (keeps the same)
    st.markdown("### Your Profile")
    user_profile = st.session_state.get(USER_PROFILE_KEY, {})
    
    col1, col2, col3 = st.columns(3)
    with col1:
        first_seen = user_profile.get("first_seen", datetime.now())
        days_active = (datetime.now() - first_seen).days
        st.metric("Days Using Maia", f"{days_active}")
    
    with col2:
        total_interactions = user_profile.get("total_interactions", 0)
        st.metric("Total Interactions", f"{total_interactions}")
    
    with col3:
        feedback_given = user_profile.get("feedback_given", 0)
        st.metric("Feedback Provided", f"{feedback_given}")
    
    # --- ADD/VERIFY IMPORTANT SENDERS SECTION ---
    st.markdown("### Important Senders")
    st.info("Add email addresses or domains that should always be marked as CRITICAL priority. Add domains with @ prefix (e.g., @company.com)")
    
    current_important_list = [] # Default
    if memory:
        try:
            user_profile_data = memory.user_profile
            current_important_list = user_profile_data.get("email_preferences", {}).get("important_senders", [])
            logging.debug(f"Settings Tab: Loaded {len(current_important_list)} important senders from memory.")
        except Exception as e:
            st.error(f"Error loading important senders from memory: {e}")
            logging.error(f"Settings Tab: Error reading important senders from memory object: {e}", exc_info=True)
    
    important_text = "\n".join(current_important_list)
    
    edited_important = st.text_area(
        "Important Senders (one per line):",
        value=important_text,
        height=150,
        key="important_senders_input", # Use a distinct key
        placeholder="boss@company.com\nclient@example.com\n@critical-vendor.com"
    )
    
    if st.button("💾 Save Important Senders", key="save_important_button", type="primary"): # Distinct key
        new_important_list = [line.strip().lower() for line in edited_important.splitlines() if line.strip()]
    
        saved_important = False
        if memory:
            with st.spinner("Saving important senders..."):
                saved_important = memory.update_email_preferences("important_senders", new_important_list)
    
        if saved_important:
            st.success("Important senders list saved successfully!")
            # Optional: Add chat message
            st.rerun()
        else:
            st.error("Failed to save important senders list.")
    # --- END IMPORTANT SENDERS SECTION ---
    
    # Important Senders Section
    st.markdown("### Filtered Domains / Senders")
    st.info("Add domains (e.g., @newsletter.com) or specific senders to automatically filter or assign lower priority (feature may depend on backend implementation).")
    
    # Read Filtered Domains from Memory
    current_filtered_list = [] # Default
    if memory:
        try:
            user_profile_data = memory.user_profile
            current_filtered_list = user_profile_data.get("email_preferences", {}).get("filtered_domains", [])
            logging.debug(f"Settings Tab: Loaded {len(current_filtered_list)} filtered domains/senders from memory.")
        except Exception as e:
            st.error(f"Error loading filtered domains from memory: {e}")
            logging.error(f"Settings Tab: Error reading filtered domains from memory object: {e}", exc_info=True)
    
    # Display in text area
    filtered_text = "\n".join(current_filtered_list)
    
    edited_filtered = st.text_area(
        "Filtered Domains/Senders (one per line):",
        value=filtered_text, # Use the loaded value
        height=150, # Adjust height as needed
        key="filtered_domains_input",
        placeholder="@spamdomain.com\n@unwanted-newsletter.org\nannoying@example.net"
    )
    
    if st.button("💾 Save Filtered Domains/Senders", key="save_filtered_button", type="primary"):
        new_filtered_list = [line.strip().lower() for line in edited_filtered.splitlines() if line.strip()]
    
        # Save Preferences using AgentMemory
        saved_filtered = False
        if memory:
            with st.spinner("Saving filtered list..."):
                saved_filtered = memory.update_email_preferences("filtered_domains", new_filtered_list)
    
        if saved_filtered:
            st.success("Filtered domains/senders list saved successfully!")
            settings_message = {
                "role": "assistant",
                "content": f"I've updated your filtered domains/senders list with {len(new_filtered_list)} entries.",
                "context": {"hint": "settings_updated", "data": {"type": "filtered_domains"}}
            }
            st.session_state[CHAT_HISTORY_KEY].append(settings_message)
            st.rerun()
        else:
            st.error("Failed to save filtered list. Memory system might be unavailable.")

    # Notification Settings (keeps the same)
    st.markdown("### Notification Preferences")
    st.info("Configure how and when you want to be notified about important emails.")
    
    notify_critical = st.toggle("Notify for CRITICAL emails", value=True)
    notify_high = st.toggle("Notify for HIGH priority emails", value=True)
    
    st.caption("Note: Notification delivery requires browser notifications to be enabled.")
    
    if st.button("💾 Save Notification Settings", key="save_notifications"):
        st.success("Notification preferences saved!")
    
    st.markdown("### Google Calendar Integration")
    st.info("Connect your Google Calendar to allow Maia to automatically schedule suggested email checking times.")
    
    # --- State variables for the auth flow ---
    if 'calendar_auth_url' not in st.session_state:
        st.session_state.calendar_auth_url = None
    if 'calendar_auth_state' not in st.session_state:
        st.session_state.calendar_auth_state = None
    if 'calendar_auth_code_pasted' not in st.session_state:
        st.session_state.calendar_auth_code_pasted = ""
    # --- End State variables ---

    calendar_service_available = False
    if gcs_client_ui and ui_config:
        gcs_bucket_for_token = os.environ.get('GCS_BUCKET_NAME', 'ai-email-agent-state')
        if gcs_bucket_for_token:
            temp_calendar_service = get_calendar_service(
                storage_client_instance=gcs_client_ui,
                token_gcs_bucket=gcs_bucket_for_token,
                credentials_path=ui_config['gmail']['credentials_path']
            )
            if temp_calendar_service:
                calendar_service_available = True
                st.success("✅ Google Calendar is connected.")
                # Clear auth flow state if connected
                st.session_state.calendar_auth_url = None
                st.session_state.calendar_auth_state = None
                st.session_state.calendar_auth_code_pasted = ""
            else:
                # Only show warning if not in the middle of the auth flow
                if not st.session_state.calendar_auth_url:
                    st.warning("Google Calendar is not connected.")
        else:
            st.error("GCS Bucket Name for tokens is not configured (GCS_BUCKET_NAME env var).")

    # --- Authorization Button and Flow ---
    if not calendar_service_available and gcs_client_ui and ui_config:

        # Button to START the flow
        if not st.session_state.calendar_auth_url:
            if st.button("🔗 Start Google Calendar Connection", key="start_calendar_connect"):
                gcs_bucket_for_token = os.environ.get('GCS_BUCKET_NAME', 'ai-email-agent-state')
                if not gcs_bucket_for_token:
                    st.error("GCS_BUCKET_NAME environment variable not set.")
                else:
                    try:
                        flow = InstalledAppFlow.from_client_secrets_file(
                            ui_config['gmail']['credentials_path'],
                            CALENDAR_SCOPES,
                            # Specify the redirect_uri used in Google Cloud Console
                            redirect_uri='http://localhost:8501' # Or just http://localhost if that's what's registered
                        )
                        # Generate the URL and store the state
                        auth_url, state = flow.authorization_url(
                            access_type='offline', # Request refresh token
                            prompt='consent'       # Force consent screen every time
                        )
                        st.session_state.calendar_auth_url = auth_url
                        st.session_state.calendar_auth_state = state
                        st.rerun() # Rerun to display the URL and instructions

                    except Exception as e:
                        st.error(f"Failed to start Calendar connection: {e}")
                        logging.error(f"Calendar OAuth URL generation error: {e}", exc_info=True)

        # If URL generated, show instructions and input for code
        elif st.session_state.calendar_auth_url:
            st.markdown("---")
            st.markdown("**Step 1:** Click the link below to authorize access to your Google Calendar.")
            # Use link_button for better appearance
            st.link_button("Authorize with Google", st.session_state.calendar_auth_url, type="primary")
            # st.markdown(f"Authorization URL: {st.session_state.calendar_auth_url}") # Alternative display

            st.markdown("**Step 2:** After authorizing, Google will redirect you to a page (it might say 'This site can’t be reached' or similar). Copy the **code** value from the URL in your browser's address bar.")
            st.markdown("*(The URL will look something like `http://localhost:8501/?state=...&code=4/0Ab...&scope=...` - copy the part after `code=` and before the next `&`)*")

            auth_code = st.text_input(
                "**Step 3:** Paste the authorization code here:",
                key="calendar_auth_code_input",
                help="Paste the 'code' value from the URL after authorizing."
            )

            if st.button("✅ Verify Code and Connect", key="verify_calendar_code"):
                if not auth_code:
                    st.warning("Please paste the authorization code first.")
                else:
                    gcs_bucket_for_token = os.environ.get('GCS_BUCKET_NAME', 'ai-email-agent-state')
                    calendar_token_gcs_path = os.environ.get(CALENDAR_TOKEN_GCS_PATH_ENV, DEFAULT_CALENDAR_TOKEN_FILENAME)
                    if not gcs_bucket_for_token:
                        st.error("GCS_BUCKET_NAME environment variable not set.")
                    else:
                        with st.spinner("Verifying code and saving credentials..."):
                            try:
                                flow = InstalledAppFlow.from_client_secrets_file(
                                    ui_config['gmail']['credentials_path'],
                                    CALENDAR_SCOPES,
                                    state=st.session_state.calendar_auth_state, # Use stored state
                                    redirect_uri='http://localhost:8501' # Must match URL generation
                                )
                                # Exchange the code for tokens
                                flow.fetch_token(code=auth_code)
                                creds = flow.credentials # Get credentials object

                                # Save the credentials to GCS
                                saved = save_calendar_token_to_gcs(
                                    creds,
                                    gcs_client_ui,
                                    gcs_bucket_for_token,
                                    calendar_token_gcs_path
                                )
                                if saved:
                                    st.success("Google Calendar connected successfully! Refreshing...")
                                    # Clear auth flow state
                                    st.session_state.calendar_auth_url = None
                                    st.session_state.calendar_auth_state = None
                                    time.sleep(2)
                                    st.rerun()
                                else:
                                    st.error("Failed to save calendar credentials after verification.")

                            except Exception as e:
                                st.error(f"Failed to verify code or save credentials: {e}")
                                logging.error(f"Calendar code verification/save error: {e}", exc_info=True)
                                # Optionally clear state on error?
                                # st.session_state.calendar_auth_url = None
                                # st.session_state.calendar_auth_state = None

            if st.button("Cancel Connection Attempt", key="cancel_calendar_connect"):
                 st.session_state.calendar_auth_url = None
                 st.session_state.calendar_auth_state = None
                 st.rerun()
            st.markdown("---")    
    
    # Reset Suggestions Option
    st.markdown("### Reset Suggestions")
    st.info("If you've dismissed suggestions that you'd like to see again, use this option.")
    
    if st.button("Reset Dismissed Suggestions", key="reset_suggestions"):
        if "dismissed_suggestions" in st.session_state:
            st.session_state.dismissed_suggestions = set()
            st.success("All dismissed suggestions have been reset. You'll see them again in the Chat & Dashboard tab.")
    
    # Add under the "Reset Suggestions" section
    if st.checkbox("Show Debugging Info", value=False, key="show_debug"):
        st.json({
            "dismissed_suggestions": list(st.session_state.get("dismissed_suggestions", set())),
            "suggestion_cache_exists": SUGGESTIONS_STATE_KEY in st.session_state,
            "last_df_hash": st.session_state.get(LAST_DF_HASH_KEY, None)
        })
    # --- YENİ EKLENEN DEBUG BÖLÜMÜ ---
    st.markdown("### Debug Information")
    if st.checkbox("Show Session State Debug"):
        st.write("Dismissed Suggestions:", list(st.session_state.get("dismissed_suggestions", set())))
        if st.button("Clear Dismissed State"):
            st.session_state.dismissed_suggestions = set()
            st.success("Dismissed state cleared!")
            st.rerun() # Sayfayı yenile
    # --- YENİ DEBUG BÖLÜMÜNÜN SONU ---
    render_suggestion_history_section()
with tabs[4]:
    render_autonomous_tab()


# Footer
st.markdown("---")
st.caption(f"Maia Email Agent • Enhanced Suggestions Version • Made with ❤️ by SaKinLord")