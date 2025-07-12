# -*- coding: utf-8 -*-
"""
Enhanced Maia UI App with Modern Design and Explainable Reasoning
Features:
- Clean, assistant-first interface
- Explainable AI reasoning displays
- Improved performance with lazy loading
- Modern design system
- Better user experience flows
"""

from dotenv import load_dotenv
load_dotenv()

import streamlit as st
import pandas as pd
import logging
import html as html_module
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Any, Optional
import json
from google.cloud import firestore
from google.cloud.firestore_v1.base_query import FieldFilter

# Import existing modules
from modern_ui import ModernDesign, ModernComponents, create_modern_plotly_chart
from reasoning_engine import ClassificationResult
import agent_logic
import agent_memory
import database_utils
from hybrid_llm_system import create_hybrid_llm_manager
import task_utils
# Set page config with modern design
st.set_page_config(
    layout="wide",
    page_title="Maia - Your Intelligent Email Assistant",
    page_icon="🤖",
    initial_sidebar_state="collapsed"
)
# Configuration and LLM Manager are now centralized in initialize_session_state()
# This avoids duplication and ensures proper initialization order



# Apply modern styling
st.markdown(ModernDesign.get_css(), unsafe_allow_html=True)

def run_pre_flight_checks():
    """
    Pre-Flight Check System - Validates critical prerequisites before app startup.
    Prevents cascading errors by checking environment and configuration.
    """
    import os
    
    # List to collect all missing requirements
    missing_requirements = []
    
    # Check 1: Environment Variables
    if not os.environ.get('ANTHROPIC_API_KEY'):
        missing_requirements.append("❌ **ERROR: ANTHROPIC_API_KEY environment variable not set**")
    
    if not os.environ.get('OPENAI_API_KEY'):
        missing_requirements.append("❌ **ERROR: OPENAI_API_KEY environment variable not set**")
    
    # Check 2: Critical Configuration Files
    if not os.path.exists('config.json'):
        missing_requirements.append("❌ **config.json** file not found in project root")
    
    if not os.path.exists('credentials.json'):
        missing_requirements.append("❌ **credentials.json** file not found in project root")
    
    # If any requirements are missing, display comprehensive error and halt
    if missing_requirements:
        st.error("🚨 **Pre-Flight Check Failed: Critical Prerequisites Missing**")
        
        st.markdown("### Missing Requirements:")
        for requirement in missing_requirements:
            st.markdown(f"- {requirement}")
        
        st.markdown("### 🔧 **Setup Instructions:**")
        
        if "ANTHROPIC_API_KEY" in str(missing_requirements):
            st.markdown("""
            **Anthropic API Key:**
            1. Get your API key from [Anthropic Console](https://console.anthropic.com/)
            2. Set environment variable: `export ANTHROPIC_API_KEY="sk-ant-..."`
            3. Or add to `.env` file: `ANTHROPIC_API_KEY="sk-ant-..."`
            """)
        
        if "OPENAI_API_KEY" in str(missing_requirements):
            st.markdown("""
            **OpenAI API Key:**
            1. Get your API key from [OpenAI Platform](https://platform.openai.com/api-keys)
            2. Set environment variable: `export OPENAI_API_KEY="sk-..."`
            3. Or add to `.env` file: `OPENAI_API_KEY="sk-..."`
            """)
        
        if "config.json" in str(missing_requirements):
            st.markdown("""
            **Configuration File:**
            1. Copy `config.template.json` to `config.json`
            2. Edit `config.json` with your settings
            """)
        
        if "credentials.json" in str(missing_requirements):
            st.markdown("""
            **Google Credentials:**
            1. Go to [Google Cloud Console](https://console.cloud.google.com/)
            2. Create OAuth 2.0 Client ID (Desktop app)
            3. Download as `credentials.json` in project root
            """)
        
        st.markdown("### 📚 **Documentation:**")
        st.markdown("See `README.md` and `TROUBLESHOOTING.md` for detailed setup instructions.")
        
        # Halt execution gracefully
        st.stop()
    
    # If all checks pass, log success
    logging.info("✅ Pre-flight checks passed - all prerequisites available")

# Constants
EMAILS_COLLECTION = "emails"
FEEDBACK_COLLECTION = "feedback"
STATE_COLLECTION = "agent_state"

# Cache configuration
@st.cache_data(ttl=600)
def get_cached_email_data(limit: int = 50) -> pd.DataFrame:
    """
    Fetches email data from Firestore with a 10-minute cache.

    This function queries the database and caches the result for 10 minutes (600 seconds)
    to improve performance and reduce Firestore read costs. The cache is automatically
    invalidated after the TTL expires.

    Args:
        limit (int): The maximum number of emails to fetch.

    Returns:
        pd.DataFrame: A DataFrame containing the email data.
    """
    try:
        database_utils.initialize_firestore()
        db = database_utils.get_db()
        if not db:
            st.error("Database connection could not be established. Check credentials.")
            return pd.DataFrame()
        
        logging.info("CACHE MISS: Fetching fresh email data from Firestore.")
        
        # Optimized query with pagination
        emails_ref = db.collection(EMAILS_COLLECTION).order_by(
            'processed_timestamp', direction='DESCENDING'
        ).limit(limit)
        
        emails = []
        for doc in emails_ref.stream():
            email_data = doc.to_dict()
            email_data['id'] = doc.id
            emails.append(email_data)
        
        return pd.DataFrame(emails) if emails else pd.DataFrame()
    
    except Exception as e:
        logging.error(f"Error fetching cached email data: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=60)  # 1-minute cache for insights
def get_cached_insights() -> Dict[str, Any]:
    """Cached insights calculation"""
    try:
        df = get_cached_email_data(100)  # Look at more emails for insights
        if df.empty:
            return {
                'total_emails': 0,
                'high_priority': 0,
                'processed_today': 0,
                'avg_confidence': 0
            }
        
        today = datetime.now(timezone.utc).date()
        processed_today = 0
        
        for _, row in df.iterrows():
            processed_timestamp = row.get('processed_timestamp')
            if processed_timestamp and hasattr(processed_timestamp, 'date'):
                if processed_timestamp.date() == today:
                    processed_today += 1
        
        high_priority_count = len(df[df['priority'].fillna('').isin(['CRITICAL', 'HIGH'])])
        
        # Calculate average confidence if available
        confidences = []
        for _, row in df.iterrows():
            reasoning = row.get('reasoning_result')
            if reasoning and isinstance(reasoning, dict):
                conf = reasoning.get('confidence', 0)
                if conf > 0:
                    confidences.append(conf)
        
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0
        
        return {
            'total_emails': len(df),
            'high_priority': high_priority_count,
            'processed_today': processed_today,
            'avg_confidence': round(avg_confidence, 1)
        }
    
    except Exception as e:
        logging.error(f"Error calculating insights: {e}")
        return {
            'total_emails': 0,
            'high_priority': 0,
            'processed_today': 0,
            'avg_confidence': 0
        }

def initialize_session_state():
    """Initialize session state variables and centralized configuration"""
    
    # === CENTRALIZED CONFIGURATION MANAGEMENT ===
    if 'config' not in st.session_state:
        try:
            with open('config.json', 'r', encoding='utf-8') as f:
                st.session_state.config = json.load(f)
            logging.info("Configuration loaded successfully into session state")
        except FileNotFoundError:
            st.error("`config.json` not found. System features will be limited.")
            logging.warning("config.json not found, using empty config")
            st.session_state.config = {}
        except Exception as e:
            st.error(f"Error loading config: {e}. System features may not work properly.")
            logging.error(f"Error loading config: {e}")
            st.session_state.config = {}
    
    # === CENTRALIZED LLM MANAGER ===
    if 'llm_manager' not in st.session_state:
        try:
            import os
            from hybrid_llm_system import create_hybrid_llm_manager

            # --- START: NEW GUARD CLAUSE ---
            openai_api_key = os.getenv('OPENAI_API_KEY')
            anthropic_api_key = os.getenv('ANTHROPIC_API_KEY')

            if not openai_api_key or not anthropic_api_key:
                st.error("🔴 FATAL ERROR: LLM API keys are missing!")
                st.markdown("""
                **Your `OPENAI_API_KEY` or `ANTHROPIC_API_KEY` is not configured.**
                
                Please ensure your `.env` file in the project root contains both keys:
                ```
                OPENAI_API_KEY="sk-..."
                ANTHROPIC_API_KEY="sk-ant-..."
                ```
                After adding the keys, please restart the application.
                """)
                # Stop the application completely
                st.stop()
            # --- END: NEW GUARD CLAUSE ---

            # Now, create the manager using the validated keys
            st.session_state.llm_manager = create_hybrid_llm_manager(
                st.session_state.config, 
                openai_api_key=openai_api_key, 
                anthropic_api_key=anthropic_api_key
            )
            logging.info("LLM Manager initialized successfully into session state")

        except Exception as e:
            st.error(f"Failed to initialize LLM manager: {e}")
            logging.error(f"Failed to initialize LLM manager: {e}")
            st.session_state.llm_manager = None
    
    # === UI STATE VARIABLES ===
    if 'chat_history' not in st.session_state:
        st.session_state.chat_history = []
    
    if 'current_view' not in st.session_state:
        st.session_state.current_view = 'dashboard'
    
    if 'selected_email' not in st.session_state:
        st.session_state.selected_email = None
    
    if 'show_reasoning' not in st.session_state:
        st.session_state.show_reasoning = {}

def format_emails_as_markdown(emails_df: pd.DataFrame, email_type: str = "emails") -> str:
    """Format emails DataFrame as a conversational markdown string"""
    if emails_df.empty:
        return f"I couldn't find any {email_type} at the moment. Your inbox might be empty or there might be a processing delay."
    
    # Create header message
    count = len(emails_df)
    if email_type == "high priority emails":
        header = f"Of course! Here are your {count} high-priority emails:"
    elif email_type == "recent emails":
        header = f"Here are your {count} most recent emails:"
    else:
        header = f"I found {count} {email_type}:"
    
    # Format each email
    email_entries = []
    for _, email in emails_df.iterrows():
        priority = email.get('priority', 'MEDIUM')
        subject = email.get('subject', 'No Subject')
        sender = email.get('sender', 'Unknown Sender')
        
        # Format timestamp
        timestamp = email.get('processed_timestamp')
        if timestamp and hasattr(timestamp, 'strftime'):
            time_str = timestamp.strftime('%Y-%m-%d %I:%M %p')
        else:
            time_str = 'Unknown time'
        
        # Choose emoji based on priority
        if priority == 'CRITICAL':
            emoji = '🚨'
        elif priority == 'HIGH':
            emoji = '📧'
        elif priority == 'MEDIUM':
            emoji = '📬'
        else:
            emoji = '📭'
        
        # Format the email entry
        entry = f"""{emoji} **{priority}** - {subject}
    👤 From: {sender}
    🗓️ Received: {time_str}"""
        
        email_entries.append(entry)
    
    # Combine header and entries
    result = header + "\n\n" + "\n\n".join(email_entries)
    
    # Add helpful footer
    result += "\n\nYou can ask me to summarize any of these emails by mentioning the subject, or ask for more details about your inbox!"
    
    return result

def format_insights_as_markdown(insights: Dict[str, Any]) -> str:
    """Format insights dictionary as a conversational markdown string"""
    
    # Create header message
    header = "Of course! Here is a summary of your email activity:"
    
    # Format the metrics with emojis and friendly language
    total_emails = insights.get('total_emails', 0)
    high_priority = insights.get('high_priority', 0)
    processed_today = insights.get('processed_today', 0)
    avg_confidence = insights.get('avg_confidence', 0)
    
    metrics = f"""
📊 **Total Emails:** {total_emails}
🔥 **High Priority:** {high_priority}
✅ **Processed Today:** {processed_today}
🧠 **Avg. Confidence:** {avg_confidence}%"""
    
    # Add contextual commentary based on the data
    footer_parts = []
    
    if high_priority > 0:
        footer_parts.append(f"You have {high_priority} high-priority emails that might need attention.")
    
    if processed_today == 0:
        footer_parts.append("No new emails processed today.")
    elif processed_today == 1:
        footer_parts.append("1 email was processed today.")
    else:
        footer_parts.append(f"{processed_today} emails were processed today.")
    
    if avg_confidence > 80:
        footer_parts.append("My classification confidence is quite high!")
    elif avg_confidence > 60:
        footer_parts.append("My classification confidence is moderate.")
    elif avg_confidence > 0:
        footer_parts.append("My classification confidence could be improved with more feedback.")
    
    # Combine all parts
    result = header + "\n" + metrics
    
    if footer_parts:
        result += "\n\n" + " ".join(footer_parts)
    
    result += "\n\nIs there anything specific you'd like to know more about?"
    
    return result

def search_emails_by_subject(query_terms: str, limit: int = 10) -> pd.DataFrame:
    """Search emails by subject content using intelligent scoring-based matching"""
    try:
        database_utils.initialize_firestore()
        db = database_utils.get_db()
        if not db:
            st.error("Database connection could not be established. Check credentials.")
            return pd.DataFrame()
        
        def calculate_relevance_score(subject: str, query_words: list) -> float:
            """Calculate relevance score for an email subject based on query words"""
            if not subject or not query_words:
                return 0.0
            
            subject_lower = subject.lower()
            query_words_lower = [word.lower() for word in query_words]
            
            # Filter out very common/stop words that shouldn't contribute to scoring
            stop_words = {'an', 'a', 'the', 'that', 'this', 'does', 'not', 'is', 'are', 'was', 'were', 
                         'be', 'been', 'being', 'have', 'has', 'had', 'do', 'did', 'will', 'would', 
                         'should', 'could', 'can', 'may', 'might', 'must', 'shall', 'of', 'in', 'on', 
                         'at', 'to', 'for', 'with', 'by', 'from', 'about', 'into', 'through', 'during',
                         'before', 'after', 'above', 'below', 'up', 'down', 'out', 'off', 'over', 
                         'under', 'again', 'further', 'then', 'once', 'email', 'emails', 'exist'}
            
            # Filter query words to remove stop words
            meaningful_words = [word for word in query_words_lower if word not in stop_words and len(word) > 2]
            
            if not meaningful_words:
                return 0.0
            
            score = 0.0
            
            # Basic score: count how many meaningful query words appear in the subject
            word_matches = 0
            for word in meaningful_words:
                if word in subject_lower:
                    word_matches += 1
                    score += 1.0
            
            # If no meaningful words match, return 0
            if word_matches == 0:
                return 0.0
            
            # Bonus points for consecutive sequence matches
            # Check if query words appear in the same order consecutively
            query_text = ' '.join(meaningful_words)
            
            # Check for exact phrase match (highest bonus)
            if query_text in subject_lower:
                score += 5.0
            else:
                # Check for partial consecutive sequences
                for i in range(len(meaningful_words)):
                    for j in range(i + 2, len(meaningful_words) + 1):  # At least 2 words
                        phrase = ' '.join(meaningful_words[i:j])
                        if phrase in subject_lower:
                            # Bonus based on sequence length
                            sequence_length = j - i
                            score += sequence_length * 1.5
            
            # Bonus for word density (what percentage of meaningful words matched)
            word_density = word_matches / len(meaningful_words)
            score += word_density * 2.0
            
            # Slight bonus for exact word matches (not just substring matches)
            subject_words = subject_lower.split()
            exact_matches = sum(1 for word in meaningful_words if word in subject_words)
            score += exact_matches * 0.5
            
            return score
        
        # Parse query terms
        query_words = query_terms.strip().split()
        if not query_words:
            return pd.DataFrame()
        
        # Calculate dynamic threshold based on query complexity
        def calculate_dynamic_threshold(query_words: list) -> float:
            """Calculate a dynamic threshold based on query complexity"""
            # Filter meaningful words (same logic as in scoring)
            stop_words = {'an', 'a', 'the', 'that', 'this', 'does', 'not', 'is', 'are', 'was', 'were', 
                         'be', 'been', 'being', 'have', 'has', 'had', 'do', 'did', 'will', 'would', 
                         'should', 'could', 'can', 'may', 'might', 'must', 'shall', 'of', 'in', 'on', 
                         'at', 'to', 'for', 'with', 'by', 'from', 'about', 'into', 'through', 'during',
                         'before', 'after', 'above', 'below', 'up', 'down', 'out', 'off', 'over', 
                         'under', 'again', 'further', 'then', 'once', 'email', 'emails', 'exist'}
            
            meaningful_words = [word.lower() for word in query_words if word.lower() not in stop_words and len(word) > 2]
            meaningful_count = len(meaningful_words)
            
            if meaningful_count == 0:
                return 10.0  # Very high threshold for meaningless queries
            elif meaningful_count == 1:
                return 4.0   # Very high threshold for single-word queries (must be very strong match)
            elif meaningful_count == 2:
                return 3.5   # High threshold for two-word queries
            elif meaningful_count == 3:
                return 3.0   # Medium-high threshold for three-word queries  
            elif meaningful_count == 4:
                return 2.5   # Medium threshold for four-word queries
            else:
                return 2.0   # Lower threshold for very complex queries (more flexible)
        
        # Get emails to search through (increased to get better results)
        emails_ref = db.collection(EMAILS_COLLECTION).order_by(
            'processed_timestamp', direction='DESCENDING'
        ).limit(200)  # Search through more emails for better precision
        
        # Calculate the dynamic threshold for this query
        threshold = calculate_dynamic_threshold(query_words)
        
        # Score all emails
        scored_emails = []
        for doc in emails_ref.stream():
            email_data = doc.to_dict()
            email_data['id'] = doc.id
            
            subject = email_data.get('subject', '')
            score = calculate_relevance_score(subject, query_words)
            
            # Apply dynamic threshold - only include emails with meaningful scores
            if score >= threshold:
                email_data['_relevance_score'] = score
                scored_emails.append(email_data)
        
        # Sort by relevance score (highest first) and limit results
        scored_emails.sort(key=lambda x: x['_relevance_score'], reverse=True)
        top_emails = scored_emails[:limit]
        
        # Remove the internal scoring field before returning
        for email in top_emails:
            email.pop('_relevance_score', None)
        
        return pd.DataFrame(top_emails) if top_emails else pd.DataFrame()
    
    except Exception as e:
        logging.error(f"Error searching emails by subject: {e}")
        return pd.DataFrame()

def search_emails_by_purpose(purpose: str, limit: int = 20) -> pd.DataFrame:
    """Search emails by llm_purpose field"""
    try:
        database_utils.initialize_firestore()
        db = database_utils.get_db()
        if not db:
            st.error("Database connection could not be established. Check credentials.")
            return pd.DataFrame()
        
        # Query emails with specific purpose
        emails_ref = db.collection(EMAILS_COLLECTION).where(
            filter=FieldFilter('llm_purpose', '==', purpose)
        ).order_by('processed_timestamp', direction='DESCENDING').limit(limit)
        
        emails = []
        for doc in emails_ref.stream():
            email_data = doc.to_dict()
            email_data['id'] = doc.id
            emails.append(email_data)
        
        return pd.DataFrame(emails) if emails else pd.DataFrame()
    
    except Exception as e:
        logging.error(f"Error searching emails by purpose: {e}")
        return pd.DataFrame()

def extract_email_reference(query: str) -> str:
    """Extract email subject reference from user query"""
    # Look for patterns like "about 'Project Deadline'" or "about Project Deadline"
    import re
    
    # Pattern 1: "about 'something'" or "about "something""
    match = re.search(r'about\s+[\'"]([^\'"]+)[\'"]', query, re.IGNORECASE)
    if match:
        return match.group(1)
    
    # Pattern 2: "about something" (without quotes)
    match = re.search(r'about\s+(.+?)(?:\s+email|\s*$)', query, re.IGNORECASE)
    if match:
        return match.group(1).strip()
    
    # Pattern 3: "the email with" or "email with"
    match = re.search(r'(?:the\s+)?email\s+with\s+(.+?)(?:\s+in|\s*$)', query, re.IGNORECASE)
    if match:
        return match.group(1).strip()
    
    return ""

def categorize_query_intent(query: str, memory_system=None) -> Dict[str, Any]:
    """Analyze query and determine intent with parameters - improved priority order and logic with context awareness"""
    query_lower = query.lower()
    
    # PRIORITY 0: Contextual Follow-up (Phase 2.1 Enhancement)
    if memory_system:
        last_context = memory_system.get_last_context()
        follow_up_keywords = ['them', 'these', 'those', 'the content', 'those emails', 'these emails']
        is_follow_up_query = any(keyword in query_lower for keyword in follow_up_keywords)
        
        if last_context is not None and not last_context.empty and is_follow_up_query:
            if any(word in query_lower for word in ['summarize', 'read', 'content', 'what do they say', 'tell me about']):
                return {'intent': 'summarize_context_content', 'data': last_context}
            # Future: Add other contextual follow-up actions here (e.g., 'delete them', 'archive them')
    
    def clean_email_reference(text: str) -> str:
        """Clean up extracted email reference by removing keywords and normalizing"""
        # Remove common keywords that might be included
        cleanup_patterns = [
            'the email about ',
            'email about ',
            'the email with the subject ',
            'email with the subject ',
            'the email titled ',
            'email titled ',
            'the email regarding ',
            'email regarding ',
            'the email ',
            'email ',
            'about ',
            'regarding ',
            'titled ',
            'subject ',
            'with the subject ',
            'the subject ',
        ]
        
        # Apply cleanup patterns
        cleaned = text.lower().strip()
        for pattern in cleanup_patterns:
            if cleaned.startswith(pattern):
                cleaned = cleaned[len(pattern):].strip()
        
        # Remove quotes
        cleaned = cleaned.strip('"\'')
        
        return cleaned
    
    # PRIORITY 1: Explicit Specific Summary - Most specific patterns first
    if any(summary_word in query_lower for summary_word in ['summarize', 'summary']):
        # Check for explicit quoted or specific email references first
        email_ref = extract_email_reference(query)
        if email_ref:
            return {
                'intent': 'specific_email_summary',
                'email_reference': clean_email_reference(email_ref)
            }
        
        # Check for explicit patterns with "about", "titled", "subject", "regarding"
        explicit_patterns = [
            ('summarize the email about ', 'about '),
            ('summarize email about ', 'about '),
            ('summary of the email about ', 'about '),
            ('summary of email about ', 'about '),
            ('summarize the email titled ', 'titled '),
            ('summarize email titled ', 'titled '),
            ('summarize the email regarding ', 'regarding '),
            ('summarize email regarding ', 'regarding '),
            ('give me a summary of the email with the subject ', 'subject '),
            ('summary of the email with the subject ', 'subject '),
            ('summarize the email with the subject ', 'subject '),
        ]
        
        for full_pattern, fallback_pattern in explicit_patterns:
            if full_pattern in query_lower:
                subject_part = query_lower.split(full_pattern, 1)[1].strip()
                if subject_part and len(subject_part) > 2:
                    return {
                        'intent': 'specific_email_summary',
                        'email_reference': clean_email_reference(subject_part)
                    }
            elif fallback_pattern in query_lower and any(word in query_lower for word in ['summarize', 'summary']):
                subject_part = query_lower.split(fallback_pattern, 1)[1].strip()
                if subject_part and len(subject_part) > 2:
                    return {
                        'intent': 'specific_email_summary',
                        'email_reference': clean_email_reference(subject_part)
                    }
    
    # PRIORITY 2: Priority Search - Check for priority keywords
    if any(word in query_lower for word in ['high priority', 'urgent', 'critical']):
        # Check if user wants to summarize priority emails
        if any(summary_word in query_lower for summary_word in ['summarize', 'summary']):
            return {'intent': 'summarize_priority', 'priority': ['CRITICAL', 'HIGH']}
        else:
            return {'intent': 'priority_search', 'priority': ['CRITICAL', 'HIGH']}
    
    if any(word in query_lower for word in ['low priority', 'low']):
        # Check if user wants to summarize priority emails
        if any(summary_word in query_lower for summary_word in ['summarize', 'summary']):
            return {'intent': 'summarize_priority', 'priority': ['LOW']}
        else:
            return {'intent': 'priority_search', 'priority': ['LOW']}
    
    # PRIORITY 3: Category Search - Check for category keywords
    category_mapping = {
        'action': ['action', 'actions', 'action required', 'tasks', 'todo'],
        'information': ['information', 'info', 'informational'],
        'question': ['question', 'questions', 'asking'],
        'promotion': ['promotion', 'promotions', 'ads', 'marketing', 'newsletter', 'newsletters'],
        'meeting': ['meeting', 'meetings', 'calendar', 'appointment'],
        'urgent': ['urgent', 'emergency', 'asap']
    }
    
    for purpose, keywords in category_mapping.items():
        if any(keyword in query_lower for keyword in keywords):
            # Check if user wants to summarize category emails
            if any(summary_word in query_lower for summary_word in ['summarize', 'summary']):
                return {
                    'intent': 'summarize_category',
                    'category': purpose
                }
            else:
                return {
                    'intent': 'category_search',
                    'category': purpose
                }
    
    # PRIORITY 4: Flexible Specific Summary - General "summarize X" pattern
    if any(summary_word in query_lower for summary_word in ['summarize', 'summary']):
        # Check for flexible "summarize X" pattern
        if query_lower.startswith('summarize '):
            subject_part = query_lower[10:].strip()  # Remove "summarize " prefix
            if subject_part and len(subject_part) > 2:
                # Check if the subject_part contains priority or category keywords
                all_priority_keywords = ['high priority', 'urgent', 'critical', 'low priority', 'low']
                all_category_keywords = []
                for keywords in category_mapping.values():
                    all_category_keywords.extend(keywords)
                
                # If subject_part contains any priority/category keywords, don't treat as specific email
                if not any(keyword in subject_part for keyword in all_priority_keywords + all_category_keywords):
                    return {
                        'intent': 'specific_email_summary',
                        'email_reference': clean_email_reference(subject_part)
                    }
        
        # Only fall back to general summary if no specific email indicators found
        if query_lower.strip() in ['summary', 'summarize', 'give me a summary', 'provide summary']:
            return {'intent': 'general_summary'}
    
    # PRIORITY 4.5: Email Content Summarization - Read and summarize email bodies
    content_summarization_keywords = [
        'summarize content', 'read them for me', 'what do they say', 'read the emails',
        'what are the emails about', 'email content', 'email contents', 'read content',
        'what\'s in the emails', 'tell me what they say', 'what do these emails say'
    ]
    
    if any(keyword in query_lower for keyword in content_summarization_keywords):
        return {'intent': 'summarize_email_content'}
    
    # PRIORITY 5: General Commands - Be more specific about recent emails
    # Make recent_emails check stricter - only trigger for specific patterns
    specific_recent_patterns = ['inbox', 'recent emails', 'latest emails', 'show emails', 'show my emails']
    if any(pattern in query_lower for pattern in specific_recent_patterns) or query_lower.strip() == 'emails':
        return {'intent': 'recent_emails'}
    
    # Check for overview
    if any(word in query_lower for word in ['overview']):
        return {'intent': 'general_summary'}
    
    # PRIORITY 6: Mark as Read Intent
    mark_as_read_keywords = [
        'mark as read', 'mark them as read', 'mark these as read', 'mark read',
        'mark emails as read', 'mark all as read', 'read these emails',
        'set as read', 'mark as seen'
    ]
    
    if any(keyword in query_lower for keyword in mark_as_read_keywords):
        return {'intent': 'mark_as_read'}
    
    # PRIORITY 7: Autonomous Action Reporting Intent
    autonomous_report_keywords = [
        'what did you do today', 'what have you done', 'show my activity report', 
        'activity report', 'autonomous actions', 'what actions', 'show actions',
        'what did maia do', 'report', 'autonomous report', 'activity summary',
        'what did you archive', 'show archived emails', 'autonomous activity'
    ]
    
    if any(keyword in query_lower for keyword in autonomous_report_keywords):
        return {'intent': 'report_autonomous_actions'}
    
    # Default fallback
    return {'intent': 'unknown', 'query': query}

def get_next_step_suggestions(intent: str, data: Any, result_message: str = "") -> List[Dict[str, str]]:
    """
    Phase 2.2: Generate proactive next-step suggestions based on the last action.
    
    Args:
        intent: The intent that was just processed
        data: The data returned from the action (e.g., DataFrame, insights)
        result_message: The message that was returned to help contextualize suggestions
        
    Returns:
        List of suggestion dictionaries with 'label' and 'query' keys
    """
    suggestions = []
    
    # Email list search actions - suggest content summarization and new searches
    if intent in ['priority_search', 'category_search', 'specific_email_summary', 'recent_emails']:
        # Check if we have email data (non-empty results)
        has_emails = False
        if data is not None:
            # Handle DataFrame
            if hasattr(data, 'empty') and not data.empty:
                has_emails = True
            # Handle list or other collections
            elif hasattr(data, '__len__') and len(data) > 0:
                has_emails = True
        
        if has_emails:
            # Primary suggestion: Summarize content of found emails
            suggestions.append({
                'label': '💡 Summarize Content of These Emails',
                'query': 'summarize them'
            })
            
            # Secondary suggestion: Start a new search based on intent
            if intent == 'priority_search':
                suggestions.append({
                    'label': '🔍 Show Low Priority Emails',
                    'query': 'show low priority emails'
                })
            elif intent == 'category_search':
                suggestions.append({
                    'label': '📧 Show High Priority Emails',
                    'query': 'show high priority emails'
                })
            else:
                suggestions.append({
                    'label': '🔍 Start a New Search',
                    'query': 'show high priority emails'
                })
        else:
            # No emails found - suggest alternative searches
            suggestions.append({
                'label': '📧 Show High Priority Emails',
                'query': 'show high priority emails'
            })
            suggestions.append({
                'label': '📰 Show Newsletters',
                'query': 'show newsletters'
            })
    
    # Content summarization actions - suggest follow-up actions
    elif intent == 'summarize_context_content':
        suggestions.append({
            'label': '✅ Mark These as Read',
            'query': 'mark as read'
        })
        suggestions.append({
            'label': '🗂️ Show All Newsletters',
            'query': 'show newsletters'
        })
        suggestions.append({
            'label': '📧 Show High Priority Emails',
            'query': 'show high priority emails'
        })
    
    # Regular email content summarization
    elif intent == 'summarize_email_content':
        suggestions.append({
            'label': '📊 Get Inbox Overview',
            'query': 'give me an overview'
        })
        suggestions.append({
            'label': '🔍 Search Specific Emails',
            'query': 'show high priority emails'
        })
    
    # Summarization of priority/category emails
    elif intent in ['summarize_priority', 'summarize_category']:
        suggestions.append({
            'label': '📋 Show Recent Emails',
            'query': 'show recent emails'
        })
        suggestions.append({
            'label': '📊 Get Inbox Overview',
            'query': 'give me an overview'
        })
    
    # General overview/summary - suggest specific searches
    elif intent == 'general_summary':
        suggestions.append({
            'label': '👀 Show High Priority Emails',
            'query': 'show high priority emails'
        })
        suggestions.append({
            'label': '📰 Show Newsletters',
            'query': 'show newsletters'
        })
        suggestions.append({
            'label': '📋 Show Recent Emails',
            'query': 'show recent emails'
        })
    
    # Unknown or error states - provide helpful starting points
    elif intent == 'unknown':
        suggestions.append({
            'label': '📧 Show High Priority Emails',
            'query': 'show high priority emails'
        })
        suggestions.append({
            'label': '📊 Get Inbox Overview',
            'query': 'give me an overview'
        })
    
    # Default fallback suggestions (always available)
    # Add a help suggestion if we don't have many suggestions yet
    if len(suggestions) < 2:
        suggestions.append({
            'label': '❓ Show Help',
            'query': 'help'
        })
    
    # Limit to maximum of 3 suggestions to avoid UI clutter
    return suggestions[:3]

def create_response_with_suggestions(response_type: str, message: str, data: Any, intent: str) -> Dict[str, Any]:
    """
    Helper function to create response with proactive suggestions.
    """
    # Generate suggestions based on the intent and data
    suggestions = get_next_step_suggestions(intent, data, message)
    
    return {
        'type': response_type,
        'message': message,
        'data': data,
        'suggestions': suggestions  # Phase 2.2: Add proactive suggestions
    }

def process_user_query(query: str, memory_system: Any, llm_manager: Any) -> Dict[str, Any]:
    """Intelligent query processing with advanced intent recognition using dependency injection"""
    try:
        database_utils.initialize_firestore()
        
        # Analyze query intent (Phase 2.1: Now context-aware)
        intent_data = categorize_query_intent(query, memory_system)
        intent = intent_data['intent']
        
        # Handle specific email summary requests
        if intent == 'specific_email_summary':
            email_ref = intent_data['email_reference']
            emails_df = search_emails_by_subject(email_ref, limit=5)
            
            if emails_df.empty:
                # Clear context since no emails found
                memory_system.clear_context()
                email_ref_escaped = html_module.escape(email_ref)
                return {
                    'type': 'text',
                    'message': f"I couldn't find any emails about '{email_ref_escaped}'. Could you try rephrasing or check if the subject contains different keywords?",
                    'data': None
                }
            
            # Update context with found emails for potential follow-up
            memory_system.update_last_context(emails_df)
            
            # If multiple emails found, show them for user to clarify
            if len(emails_df) > 1:
                email_ref_escaped = html_module.escape(email_ref)
                formatted_message = f"I found {len(emails_df)} emails that might match '{email_ref_escaped}':\n\n"
                formatted_message += format_emails_as_markdown(emails_df, f"emails about '{email_ref_escaped}'")
                formatted_message += "\n\nPlease be more specific about which email you'd like me to summarize."
            else:
                # Single email found - provide its summary
                email = emails_df.iloc[0]
                summary = email.get('summary', 'No summary available for this email.')
                subject = email.get('subject', 'No Subject')
                sender = email.get('sender', 'Unknown Sender')
                
                # Escape HTML characters to prevent InvalidCharacterError
                subject_escaped = html_module.escape(subject)
                sender_escaped = html_module.escape(sender)
                summary_escaped = html_module.escape(summary)
                
                formatted_message = f"Here's a summary of the email '{subject_escaped}' from {sender_escaped}:\n\n"
                formatted_message += f"📝 **Summary:** {summary_escaped}\n\n"
                formatted_message += "Would you like me to provide more details about this email or help with anything else?"
            
            return create_response_with_suggestions('text', formatted_message, emails_df, intent)
        
        # Handle category-based email searches
        elif intent == 'category_search':
            category = intent_data['category']
            emails_df = search_emails_by_purpose(category, limit=15)
            
            if emails_df.empty:
                # Clear context since no emails found
                memory_system.clear_context()
                return {
                    'type': 'text',
                    'message': f"I couldn't find any emails categorized as '{category}'. This might mean there are no such emails, or they haven't been processed with purpose classification yet.",
                    'data': None
                }
            
            # Update context with found emails for potential follow-up
            memory_system.update_last_context(emails_df)
            
            formatted_message = format_emails_as_markdown(emails_df, f"{category} emails")
            return create_response_with_suggestions('text', formatted_message, emails_df, intent)
        
        # Handle priority-based searches
        elif intent == 'priority_search':
            priorities = intent_data['priority']
            df = get_cached_email_data()
            filtered_emails = df[df['priority'].fillna('').isin(priorities)]
            
            if filtered_emails.empty:
                # Clear context since no emails found
                memory_system.clear_context()
                priority_text = ' and '.join(priorities).lower()
                return {
                    'type': 'text',
                    'message': f"I couldn't find any {priority_text} priority emails.",
                    'data': None
                }
            
            # Update context with found emails for potential follow-up
            memory_system.update_last_context(filtered_emails)
            
            priority_text = ' and '.join(priorities).lower()
            formatted_message = format_emails_as_markdown(filtered_emails, f"{priority_text} priority emails")
            
            return create_response_with_suggestions('text', formatted_message, filtered_emails, intent)
        
        # Handle priority-based summarization
        elif intent == 'summarize_priority':
            priorities = intent_data['priority']
            df = get_cached_email_data()
            filtered_emails = df[df['priority'].fillna('').isin(priorities)]
            
            if filtered_emails.empty:
                priority_text = ' and '.join(priorities).lower()
                return {
                    'type': 'text',
                    'message': f"I couldn't find any {priority_text} priority emails to summarize.",
                    'data': None
                }
            
            # Limit to top 5 most recent emails to avoid overwhelming output
            top_emails = filtered_emails.head(5)
            priority_text = ' and '.join(priorities).lower()
            
            formatted_message = f"Of course! Here are the summaries for your {len(top_emails)} most recent {priority_text} priority emails:\n\n"
            
            for _, email in top_emails.iterrows():
                priority = email.get('priority', 'UNKNOWN')
                subject = html_module.escape(email.get('subject', 'No Subject'))
                sender = html_module.escape(email.get('sender', 'Unknown Sender'))
                summary = html_module.escape(email.get('summary', 'No summary available for this email.'))
                
                # Priority emoji mapping
                priority_emoji = {
                    'CRITICAL': '🚨',
                    'HIGH': '📧',
                    'MEDIUM': '📄',
                    'LOW': '📝'
                }.get(priority, '📬')
                
                formatted_message += f"{priority_emoji} **{priority}** - {subject}\n"
                formatted_message += f"From: {sender}\n"
                formatted_message += f"📝 Summary: {summary}\n\n"
            
            formatted_message += "Is there anything specific you'd like to know more about these emails?"
            
            return {
                'type': 'text',
                'message': formatted_message,
                'data': None
            }
        
        # Handle category-based summarization
        elif intent == 'summarize_category':
            category = intent_data['category']
            emails_df = search_emails_by_purpose(category, limit=15)
            
            if emails_df.empty:
                return {
                    'type': 'text',
                    'message': f"I couldn't find any {category} emails to summarize. This might mean there are no such emails, or they haven't been processed with purpose classification yet.",
                    'data': None
                }
            
            # Limit to top 5 most recent emails to avoid overwhelming output
            top_emails = emails_df.head(5)
            
            formatted_message = f"Of course! Here are the summaries for your {len(top_emails)} most recent {category} emails:\n\n"
            
            for _, email in top_emails.iterrows():
                priority = email.get('priority', 'UNKNOWN')
                subject = html_module.escape(email.get('subject', 'No Subject'))
                sender = html_module.escape(email.get('sender', 'Unknown Sender'))
                
                # Fix "Summary: nan" display bug
                import pandas as pd
                raw_summary = email.get('summary', 'No summary available for this email.')
                if not raw_summary or pd.isna(raw_summary):
                    display_summary = "No summary available for this email."
                else:
                    display_summary = raw_summary
                summary = html_module.escape(display_summary)
                
                # Priority emoji mapping
                priority_emoji = {
                    'CRITICAL': '🚨',
                    'HIGH': '📧',
                    'MEDIUM': '📄',
                    'LOW': '📝'
                }.get(priority, '📬')
                
                formatted_message += f"{priority_emoji} **{priority}** - {subject}\n"
                formatted_message += f"From: {sender}\n"
                formatted_message += f"📝 Summary: {summary}\n\n"
            
            formatted_message += "Is there anything specific you'd like to know more about these emails?"
            
            return {
                'type': 'text',
                'message': formatted_message,
                'data': None
            }
        
        # Handle recent emails
        elif intent == 'recent_emails':
            df = get_cached_email_data(10)
            
            # Update context with recent emails for potential follow-up
            memory_system.update_last_context(df)
            
            formatted_message = format_emails_as_markdown(df, "recent emails")
            
            return create_response_with_suggestions('text', formatted_message, df, intent)
        
        # Phase 2.1: Handle contextual content summarization
        elif intent == 'summarize_context_content':
            # Use the emails stored in the intent data (from memory context)
            emails_to_summarize_df = intent_data['data']
            
            # Prepare emails with subject and body for summarization
            emails_for_summary = []
            for _, email in emails_to_summarize_df.iterrows():
                email_dict = {
                    'subject': email.get('subject', 'No Subject'),
                    'body': email.get('body_text', email.get('body_snippet', 'No content available'))
                }
                emails_for_summary.append(email_dict)
            
            # Check if LLM manager is available
            if not llm_manager:
                return {
                    'type': 'text',
                    'message': "Email content summarization is currently unavailable. The LLM manager could not be initialized. Please check your configuration.",
                    'data': None
                }
            
            try:
                # Use the injected LLM manager to summarize the contextual emails
                summary_result = llm_manager.summarize_email_bodies(emails_for_summary)
                
                # Clear context after summarizing to prevent accidental reuse
                memory_system.clear_context()
                
                response_message = f"📧 **Email Content Summary** (from previous results)\n\n{summary_result}"
                return create_response_with_suggestions('text', response_message, emails_for_summary, intent)
                
            except Exception as e:
                logging.error(f"Error during contextual email summarization: {e}")
                memory_system.clear_context()  # Clear context even on error
                return {
                    'type': 'text',
                    'message': f"I encountered an error while summarizing those email contents: {str(e)}. Please try again or check the system logs.",
                    'data': None
                }
        
        # Handle email content summarization
        elif intent == 'summarize_email_content':
            # First, check if there are recent emails to summarize
            df = get_cached_email_data(10)  # Get recent emails
            
            if df.empty:
                return {
                    'type': 'text',
                    'message': "I don't see any recent emails to summarize the content of. Please make sure there are emails in your inbox that have been processed.",
                    'data': None
                }
            
            # Prepare emails with subject and body for summarization
            emails_for_summary = []
            for _, email in df.iterrows():
                email_dict = {
                    'subject': email.get('subject', 'No Subject'),
                    'body': email.get('body_text', email.get('body_snippet', 'No content available'))
                }
                emails_for_summary.append(email_dict)
            
            # Check if LLM manager is available
            if not llm_manager:
                return {
                    'type': 'text',
                    'message': "Email content summarization is currently unavailable. The LLM manager could not be initialized. Please check your configuration.",
                    'data': None
                }
            
            try:
                # Use the injected LLM manager (dependency injection pattern)
                summary_result = llm_manager.summarize_email_bodies(emails_for_summary)
                
                return {
                    'type': 'text',
                    'message': f"📧 **Email Content Summary**\n\n{summary_result}",
                    'data': emails_for_summary
                }
                
            except Exception as e:
                logging.error(f"Error during email content summarization: {e}")
                return {
                    'type': 'text',
                    'message': f"I encountered an error while summarizing the email content: {str(e)}. Please try again or check the system logs.",
                    'data': None
                }
        
        # Handle general summary
        elif intent == 'general_summary':
            # Clear context since this doesn't produce an email list
            memory_system.clear_context()
            
            insights = get_cached_insights()
            formatted_message = format_insights_as_markdown(insights)
            
            # Part 3: Add proactive autonomous action reporting to general summary
            try:
                # Quick count of autonomous actions in the last 24 hours
                from datetime import datetime, timedelta
                
                twenty_four_hours_ago = datetime.now(timezone.utc) - timedelta(hours=24)
                
                db = database_utils.get_db()
                if db:
                    action_log_collection = db.collection('action_log')
                    query = action_log_collection.where(filter=FieldFilter('timestamp', '>=', twenty_four_hours_ago))
                    actions = list(query.stream())
                    
                    if actions:
                        # Count actions by type
                        auto_archive_count = sum(1 for action in actions if action.to_dict().get('action_type') == 'auto_archive')
                        auto_calendar_count = sum(1 for action in actions if action.to_dict().get('action_type') == 'auto_calendar_draft')
                        
                        # Add proactive reporting to the summary
                        proactive_actions = []
                        if auto_archive_count > 0:
                            proactive_actions.append(f"auto-archived {auto_archive_count} low-priority email{'s' if auto_archive_count != 1 else ''}")
                        if auto_calendar_count > 0:
                            proactive_actions.append(f"created {auto_calendar_count} draft calendar event{'s' if auto_calendar_count != 1 else ''}")
                        
                        if proactive_actions:
                            action_text = " and ".join(proactive_actions)
                            formatted_message += f"\n\n✨ **Proactive Actions:** I also {action_text} for you today. Ask 'show my activity report' for details."
            except Exception as e:
                logging.error(f"Error adding proactive reporting to general summary: {e}")
                # Don't fail the entire summary if proactive reporting fails
            
            return create_response_with_suggestions('text', formatted_message, insights, intent)
        
        # Handle mark as read
        elif intent == 'mark_as_read':
            # Get last context emails if available
            last_context = memory_system.get_last_context()
            
            if last_context is None or last_context.empty:
                return {
                    'type': 'text',
                    'message': "I don't have any recent emails in context to mark as read. Please first show me some emails (e.g., 'show high priority emails') and then I can mark them as read.",
                    'data': None
                }
            
            # Extract email IDs from context
            email_ids = []
            if hasattr(last_context, 'to_dict'):
                # DataFrame case
                for _, email in last_context.iterrows():
                    email_id = email.get('id')
                    if email_id:
                        email_ids.append(email_id)
            elif isinstance(last_context, list):
                # List case
                for email in last_context:
                    email_id = email.get('id') if isinstance(email, dict) else None
                    if email_id:
                        email_ids.append(email_id)
            
            if not email_ids:
                return {
                    'type': 'text',
                    'message': "I couldn't find any email IDs from the recent context. Please try showing me some emails first.",
                    'data': None
                }
            
            try:
                # Import the mark_emails_as_read function
                from agent_logic import mark_emails_as_read, authenticate_gmail
                
                # Get configuration from session state
                config = st.session_state.get('config', {})
                gmail_config = config.get('gmail', {})
                
                # Authenticate Gmail (simplified for demo - in production this would use proper auth flow)
                # Note: This is a placeholder since full Gmail auth requires proper setup
                gmail_service = None
                
                if gmail_service:
                    # Mark emails as read
                    result = mark_emails_as_read(gmail_service, email_ids)
                    
                    success_count = result.get('success_count', 0)
                    errors = result.get('errors', [])
                    
                    if success_count > 0:
                        # Clear context after successful operation
                        memory_system.clear_context()
                        
                        message = f"✅ Successfully marked {success_count} email(s) as read!"
                        if errors:
                            message += f"\n\n⚠️ {len(errors)} email(s) had errors:\n" + "\n".join(f"• {error}" for error in errors[:3])
                            if len(errors) > 3:
                                message += f"\n• ... and {len(errors) - 3} more"
                    else:
                        message = f"❌ Failed to mark emails as read. Errors:\n" + "\n".join(f"• {error}" for error in errors[:3])
                else:
                    # Gmail service not available - return helpful message
                    message = f"📧 Mark as Read feature is being prepared!\n\nI found {len(email_ids)} email(s) that would be marked as read:\n"
                    
                    # Show which emails would be affected
                    count = 0
                    for _, email in last_context.head(5).iterrows():
                        subject = email.get('subject', 'No Subject')
                        sender = email.get('sender', 'Unknown Sender')
                        message += f"• {html_module.escape(subject)} from {html_module.escape(sender)}\n"
                        count += 1
                    
                    if len(email_ids) > 5:
                        message += f"• ... and {len(email_ids) - 5} more\n"
                    
                    message += "\n🔧 This feature requires Gmail API authentication to be fully functional."
                
                return create_response_with_suggestions('text', message, None, intent)
                
            except Exception as e:
                logging.error(f"Error in mark_as_read handler: {e}")
                return {
                    'type': 'text',
                    'message': f"❌ Error marking emails as read: {str(e)}",
                    'data': None
                }
        
        # Handle autonomous action reporting
        elif intent == 'report_autonomous_actions':
            # Clear context since this doesn't produce an email list
            memory_system.clear_context()
            
            try:
                # Query action_log collection for actions in the last 24 hours
                from datetime import datetime, timedelta
                
                # Calculate 24 hours ago
                twenty_four_hours_ago = datetime.now(timezone.utc) - timedelta(hours=24)
                
                # Query Firestore for recent autonomous actions
                db = database_utils.get_db()
                if not db:
                    return {
                        'type': 'text',
                        'message': "🔧 Unable to generate activity report. Database connection is not available.",
                        'data': None
                    }
                
                action_log_collection = db.collection('action_log')
                query = action_log_collection.where(filter=FieldFilter('timestamp', '>=', twenty_four_hours_ago)).order_by('timestamp', direction=firestore.Query.DESCENDING)
                
                actions = list(query.stream())
                
                if not actions:
                    formatted_message = "### 🤖 Autonomous Activity Report\n\n"
                    formatted_message += "I haven't performed any autonomous actions in the last 24 hours.\n\n"
                    formatted_message += "💡 When I do take autonomous actions (like auto-archiving promotional emails), they'll appear here for your transparency and peace of mind."
                else:
                    # Group actions by type for better reporting
                    action_counts = {}
                    action_details = []
                    
                    for action_doc in actions:
                        action_data = action_doc.to_dict()
                        action_type = action_data.get('action_type', 'unknown')
                        
                        # Count actions by type
                        if action_type not in action_counts:
                            action_counts[action_type] = 0
                        action_counts[action_type] += 1
                        
                        # Store details for listing
                        email_subject = action_data.get('email_subject', '[No Subject]')
                        reason = action_data.get('reason', 'No reason provided')
                        timestamp = action_data.get('timestamp')
                        
                        action_details.append({
                            'type': action_type,
                            'subject': email_subject,
                            'reason': reason,
                            'timestamp': timestamp
                        })
                    
                    # Format the response message
                    formatted_message = "### 🤖 Here's what I've done for you autonomously in the last 24 hours:\n\n"
                    
                    # Summary by action type
                    if 'auto_archive' in action_counts:
                        archive_count = action_counts['auto_archive']
                        formatted_message += f"**📁 Auto-Archived {archive_count} emails:**\n"
                        
                        # Show first few archived emails
                        archived_actions = [a for a in action_details if a['type'] == 'auto_archive']
                        for i, action in enumerate(archived_actions[:5]):
                            subject_escaped = html_module.escape(action['subject'])
                            reason_escaped = html_module.escape(action['reason'])
                            formatted_message += f"   • Archived '{subject_escaped}' ({reason_escaped})\n"
                        
                        if len(archived_actions) > 5:
                            formatted_message += f"   • ...and {len(archived_actions) - 5} more.\n"
                        
                        formatted_message += "\n"
                    
                    # Handle calendar draft actions
                    if 'auto_calendar_draft' in action_counts:
                        calendar_count = action_counts['auto_calendar_draft']
                        formatted_message += f"**📅 Created {calendar_count} draft calendar event{'s' if calendar_count != 1 else ''}:**\n"
                        
                        # Show first few calendar events
                        calendar_actions = [a for a in action_details if a['type'] == 'auto_calendar_draft']
                        for i, action in enumerate(calendar_actions[:5]):
                            subject_escaped = html_module.escape(action['subject'])
                            reason_escaped = html_module.escape(action['reason'])
                            # Extract event summary if available (it's stored in the action details)
                            action_doc_data = next((ad for ad in actions if ad.to_dict().get('email_subject') == action['subject']), None)
                            event_summary = ''
                            if action_doc_data:
                                action_data_dict = action_doc_data.to_dict()
                                event_summary = action_data_dict.get('event_summary', 'Meeting')
                                event_summary_escaped = html_module.escape(event_summary)
                                formatted_message += f"   • Created draft '{event_summary_escaped}' from email '{subject_escaped}' ({reason_escaped})\n"
                            else:
                                formatted_message += f"   • Created draft event from email '{subject_escaped}' ({reason_escaped})\n"
                        
                        if len(calendar_actions) > 5:
                            formatted_message += f"   • ...and {len(calendar_actions) - 5} more.\n"
                        
                        formatted_message += "\n"
                    
                    # Add any other action types here in the future
                    
                    formatted_message += "✨ These actions help keep your inbox organized and your calendar up-to-date automatically. All actions are performed with high confidence thresholds to ensure accuracy.\n\n"
                    formatted_message += "💡 You can ask 'what did you do today?' anytime to see this report!"
                
                return create_response_with_suggestions('text', formatted_message, None, intent)
                
            except Exception as e:
                logging.error(f"Error generating autonomous action report: {e}")
                return {
                    'type': 'text',
                    'message': f"❌ Error generating activity report: {str(e)}. Please try again or check the system logs.",
                    'data': None
                }
        
        # Handle unknown queries (improved fallback)
        else:
            # Clear context for unknown queries
            memory_system.clear_context()
            suggestions = [
                "📧 'Show me high priority emails'",
                "🔍 'Summarize the email about Project Deadline'", 
                "📊 'Give me a summary of my inbox'",
                "🏷️ 'Show me any newsletters'",
                "⚡ 'Any action required emails?'"
            ]
            
            formatted_message = f"I'm not sure how to help with '{query}' yet, but I'm learning! 🤖\n\n"
            formatted_message += "Here are some things I can help you with:\n\n" + "\n".join(suggestions)
            formatted_message += "\n\nFeel free to try rephrasing your question or ask me something else!"
            
            return {
                'type': 'text',
                'message': formatted_message,
                'data': None
            }
    
    except Exception as e:
        logging.error(f"Error processing query: {e}")
        return {
            'type': 'error',
            'message': "I encountered an error processing your request. Please try again.",
            'data': None
        }

def render_email_with_reasoning(email_data: Dict[str, Any], show_reasoning: bool = False, prefix: str = ""):
    """Render email card with optional reasoning display"""
    email_id = email_data.get('id', 'unknown')
    
    # Basic email card with unique prefix
    ModernComponents.render_email_card(email_data, prefix=prefix)
    
    # Always show priority reasoning if available, regardless of show_reasoning flag
    if 'reasoning_result' in email_data:
        reasoning_data = email_data['reasoning_result']
        
        # Convert to ClassificationResult if it's a dict
        if isinstance(reasoning_data, dict):
            priority = reasoning_data.get('priority', 'Unknown')
            confidence = reasoning_data.get('confidence', 0)
            
            # Show "Why this priority?" expander for explainable AI
            with st.expander(f"❓ Why {priority} priority?", expanded=False):
                # Quick summary at top
                decision_method = reasoning_data.get('metadata', {}).get('decision_method', 'Unknown')
                st.markdown(f"**🎯 AI Decision:** {priority} priority (confidence: {confidence:.1f}%)")
                
                # Main explanations - the "why"
                if 'explanation' in reasoning_data and reasoning_data['explanation']:
                    st.markdown("**🔍 Reasoning:**")
                    for i, explanation in enumerate(reasoning_data['explanation'], 1):
                        # Clean up explanation formatting
                        clean_explanation = explanation.strip()
                        if not clean_explanation.startswith(('•', '-', '▪')):
                            clean_explanation = f"• {clean_explanation}"
                        st.markdown(clean_explanation)
                else:
                    st.markdown("• No detailed explanation available")
                
                # Show additional technical details if show_reasoning is True
                if show_reasoning:
                    st.markdown("---")
                    st.markdown("**🔧 Technical Details:**")
                    st.markdown(f"**Decision Method:** {decision_method}")
                    
                    # Show reasoning chain for detailed analysis
                    if 'reasoning_chain' in reasoning_data and reasoning_data['reasoning_chain']:
                        st.markdown("**🧠 Detailed Decision Process:**")
                        for i, step in enumerate(reasoning_data['reasoning_chain']):
                            icon = {
                                'feedback_check': '👤',
                                'llm_analysis': '🧠',
                                'ml_prediction': '🤖',
                                'rule_match': '📋',
                                'sender_check': '📧',
                                'keyword_analysis': '🔤'
                            }.get(step.get('step_type', ''), '•')
                            
                            confidence_str = ""
                            if 'confidence' in step and step['confidence'] is not None:
                                confidence_str = f" ({step['confidence']:.1f}% confidence)"
                            
                            result_str = ""
                            if 'result' in step and step['result']:
                                result_str = f" → {step['result']}"
                            
                            st.markdown(f"{i+1}. {icon} {step.get('description', 'Unknown step')}{result_str}{confidence_str}")
                
                # Add learning context
                has_personalization = reasoning_data.get('metadata', {}).get('has_personalization', False)
                if has_personalization:
                    st.markdown("---")
                    st.markdown("🤖 **AI Learning**: This decision incorporates your personal feedback patterns")
                elif decision_method == 'ml_prediction':
                    st.markdown("---")
                    st.markdown("🤖 **AI Learning**: Based on machine learning model trained on user feedback")
    
    # Add reply suggestions for emails (Phase 8 feature)
    if email_data.get('body_text') or email_data.get('body_snippet'):
        # Check if this email might need a reply (not promotional/social emails)
        email_purpose = str(email_data.get('llm_purpose', '')).lower()
        should_suggest_replies = email_purpose not in ['promotion', 'social', 'newsletter'] and email_data.get('priority', 'LOW') != 'LOW'
        
        if should_suggest_replies:
            with st.expander("💬 Quick Reply Suggestions", expanded=False):
                try:
                    # Get the hybrid LLM manager from session state
                    llm_manager = st.session_state.get('llm_manager')
                    
                    if llm_manager:
                        # Get email content for analysis
                        email_content = email_data.get('body_text') or email_data.get('body_snippet', '')
                        
                        if email_content and len(email_content.strip()) > 10:
                            # Generate reply suggestions
                            with st.spinner("🧠 Generating reply suggestions..."):
                                reply_suggestions = llm_manager.generate_reply_suggestions(email_content[:1000])  # Limit content length
                            
                            if reply_suggestions and len(reply_suggestions) > 0:
                                st.markdown("**✨ Suggested Replies:**")
                                
                                # Display reply suggestions as buttons
                                for i, suggestion in enumerate(reply_suggestions):
                                    # Create unique button key
                                    button_key = f"reply_{email_id}_{i}_{prefix}"
                                    col1, col2 = st.columns([4, 1])
                                    
                                    with col1:
                                        # Display the suggestion text
                                        st.markdown(f"**{i+1}.** {suggestion}")
                                    
                                    with col2:
                                        # Copy button (for now, we'll show in a text area for copying)
                                        if st.button("📋 Copy", key=button_key, help="Click to copy this reply"):
                                            # Store the copied text in session state for display
                                            st.session_state[f'copied_reply_{email_id}'] = suggestion
                                            st.toast(f"✅ Reply copied!", icon="📋")
                                
                                # Show copied reply in a text area for easy copying
                                if f'copied_reply_{email_id}' in st.session_state:
                                    st.markdown("**📋 Selected Reply (copy from text box below):**")
                                    st.text_area(
                                        "Copy this text:", 
                                        value=st.session_state[f'copied_reply_{email_id}'],
                                        height=80,
                                        key=f"reply_text_{email_id}_{prefix}",
                                        help="Select all text and copy (Ctrl+C / Cmd+C)"
                                    )
                                
                                st.markdown("💡 **Tip:** These replies are AI-generated. Feel free to customize them before sending!")
                            else:
                                st.info("Could not generate reply suggestions for this email.")
                        else:
                            st.info("Email content too short for reply suggestions.")
                    else:
                        st.warning("⚠️ Reply suggestions unavailable (LLM manager not initialized)")
                        
                except Exception as e:
                    st.error(f"❌ Error generating reply suggestions: {str(e)}")
                    logging.error(f"Reply suggestion error for email {email_id}: {e}")
                    
                # Manual reply option
                st.markdown("---")
                st.markdown("**✍️ Or compose your own reply:**")
                manual_reply = st.text_area(
                    "Your reply:", 
                    placeholder="Type your custom reply here...",
                    key=f"manual_reply_{email_id}_{prefix}",
                    height=100
                )
    
    # Email Action Buttons (New Feature)
    render_email_actions(email_data, prefix)

def render_email_actions(email_data: Dict[str, Any], prefix: str = ""):
    """Render email action buttons (Archive, Label, Mark Important, Forward, Reply)"""
    email_id = email_data.get('id', 'unknown')
    
    with st.expander("⚡ Email Actions", expanded=False):
        st.markdown("**Quick Actions:**")
        
        # Create action button columns
        col1, col2, col3, col4, col5 = st.columns(5)
        
        with col1:
            if st.button("🗄️ Archive", key=f"archive_{email_id}_{prefix}", help="Archive this email"):
                handle_archive_email(email_id)
        
        with col2:
            if st.button("⭐ Important", key=f"important_{email_id}_{prefix}", help="Mark as important"):
                handle_mark_important(email_id)
        
        with col3:
            if st.button("🏷️ Label", key=f"label_{email_id}_{prefix}", help="Add a label"):
                st.session_state[f'show_label_dialog_{email_id}'] = True
                st.rerun()
        
        with col4:
            if st.button("↪️ Reply", key=f"reply_btn_{email_id}_{prefix}", help="Create reply draft"):
                st.session_state[f'show_reply_dialog_{email_id}'] = True
                st.rerun()
        
        with col5:
            if st.button("➡️ Forward", key=f"forward_{email_id}_{prefix}", help="Forward this email"):
                st.session_state[f'show_forward_dialog_{email_id}'] = True
                st.rerun()
        
        # Label Dialog
        if st.session_state.get(f'show_label_dialog_{email_id}', False):
            st.markdown("---")
            st.markdown("**🏷️ Add Label:**")
            
            # Predefined label options
            common_labels = ["Important", "Work", "Personal", "Follow-up", "Urgent", "To-do", "Archive"]
            
            col_label1, col_label2 = st.columns([3, 1])
            with col_label1:
                label_option = st.selectbox(
                    "Choose a label:",
                    ["Custom..."] + common_labels,
                    key=f"label_select_{email_id}_{prefix}"
                )
                
                if label_option == "Custom...":
                    custom_label = st.text_input(
                        "Custom label name:",
                        key=f"custom_label_{email_id}_{prefix}",
                        placeholder="Enter label name..."
                    )
                    final_label = custom_label
                else:
                    final_label = label_option
            
            with col_label2:
                if st.button("✅ Apply", key=f"apply_label_{email_id}_{prefix}"):
                    if final_label and final_label.strip():
                        handle_apply_label(email_id, final_label.strip())
                        st.session_state[f'show_label_dialog_{email_id}'] = False
                        st.rerun()
                    else:
                        st.error("Please enter a label name")
                
                if st.button("❌ Cancel", key=f"cancel_label_{email_id}_{prefix}"):
                    st.session_state[f'show_label_dialog_{email_id}'] = False
                    st.rerun()
        
        # Reply Dialog
        if st.session_state.get(f'show_reply_dialog_{email_id}', False):
            st.markdown("---")
            st.markdown("**↪️ Create Reply:**")
            
            col_reply1, col_reply2 = st.columns([4, 1])
            with col_reply1:
                reply_content = st.text_area(
                    "Reply content:",
                    key=f"reply_content_{email_id}_{prefix}",
                    placeholder="Type your reply here...",
                    height=100
                )
                
                reply_type = st.radio(
                    "Reply type:",
                    ["reply", "reply_all"],
                    key=f"reply_type_{email_id}_{prefix}",
                    horizontal=True
                )
            
            with col_reply2:
                if st.button("📝 Create Draft", key=f"create_reply_{email_id}_{prefix}"):
                    if reply_content and reply_content.strip():
                        handle_create_reply(email_id, reply_content.strip(), reply_type)
                        st.session_state[f'show_reply_dialog_{email_id}'] = False
                        st.rerun()
                    else:
                        st.error("Please enter reply content")
                
                if st.button("❌ Cancel", key=f"cancel_reply_{email_id}_{prefix}"):
                    st.session_state[f'show_reply_dialog_{email_id}'] = False
                    st.rerun()
        
        # Forward Dialog
        if st.session_state.get(f'show_forward_dialog_{email_id}', False):
            st.markdown("---")
            st.markdown("**➡️ Forward Email:**")
            
            col_fwd1, col_fwd2 = st.columns([4, 1])
            with col_fwd1:
                forward_to = st.text_input(
                    "Forward to (email):",
                    key=f"forward_to_{email_id}_{prefix}",
                    placeholder="recipient@example.com"
                )
                
                additional_message = st.text_area(
                    "Additional message (optional):",
                    key=f"forward_message_{email_id}_{prefix}",
                    placeholder="Add a message before the forwarded content...",
                    height=80
                )
            
            with col_fwd2:
                if st.button("📤 Create Draft", key=f"create_forward_{email_id}_{prefix}"):
                    if forward_to and forward_to.strip():
                        # Basic email validation
                        if "@" in forward_to and "." in forward_to:
                            email_content = email_data.get('body_text') or email_data.get('body_snippet', 'No content available')
                            handle_create_forward(email_id, forward_to.strip(), email_content, additional_message)
                            st.session_state[f'show_forward_dialog_{email_id}'] = False
                            st.rerun()
                        else:
                            st.error("Please enter a valid email address")
                    else:
                        st.error("Please enter recipient email")
                
                if st.button("❌ Cancel", key=f"cancel_forward_{email_id}_{prefix}"):
                    st.session_state[f'show_forward_dialog_{email_id}'] = False
                    st.rerun()

def handle_archive_email(email_id: str):
    """Handle archiving an email"""
    try:
        # Get Gmail service
        gmail_service = get_gmail_service()
        if not gmail_service:
            st.error("❌ Gmail service not available")
            return
        
        # Archive the email
        result = agent_logic.archive_email(gmail_service, email_id)
        
        if result["success"]:
            st.success("✅ Email archived successfully!")
            # Optionally refresh the email list
            st.session_state.cache_timestamp = 0  # Force cache refresh
        else:
            st.error(f"❌ Failed to archive email: {result['error']}")
    except Exception as e:
        st.error(f"❌ Error archiving email: {str(e)}")
        logging.error(f"Archive email error: {e}")

def handle_mark_important(email_id: str):
    """Handle marking an email as important"""
    try:
        # Get Gmail service
        gmail_service = get_gmail_service()
        if not gmail_service:
            st.error("❌ Gmail service not available")
            return
        
        # Mark as important
        result = agent_logic.mark_email_as_important(gmail_service, email_id)
        
        if result["success"]:
            st.success("⭐ Email marked as important!")
        else:
            st.error(f"❌ Failed to mark as important: {result['error']}")
    except Exception as e:
        st.error(f"❌ Error marking email as important: {str(e)}")
        logging.error(f"Mark important error: {e}")

def handle_apply_label(email_id: str, label_name: str):
    """Handle applying a label to an email"""
    try:
        # Get Gmail service
        gmail_service = get_gmail_service()
        if not gmail_service:
            st.error("❌ Gmail service not available")
            return
        
        # Apply label
        result = agent_logic.apply_label_to_email(gmail_service, email_id, label_name)
        
        if result["success"]:
            st.success(f"🏷️ Label '{label_name}' applied successfully!")
        else:
            st.error(f"❌ Failed to apply label: {result['error']}")
    except Exception as e:
        st.error(f"❌ Error applying label: {str(e)}")
        logging.error(f"Apply label error: {e}")

def handle_create_reply(email_id: str, reply_content: str, reply_type: str):
    """Handle creating a reply draft"""
    try:
        # Get Gmail service
        gmail_service = get_gmail_service()
        if not gmail_service:
            st.error("❌ Gmail service not available")
            return
        
        # Create reply draft
        result = agent_logic.create_reply_draft(gmail_service, email_id, reply_content, reply_type)
        
        if result["success"]:
            st.success(f"📝 Reply draft created! Draft ID: {result['draft_id']}")
            st.info("💡 Check your Gmail drafts to review and send the reply.")
        else:
            st.error(f"❌ Failed to create reply: {result['error']}")
    except Exception as e:
        st.error(f"❌ Error creating reply: {str(e)}")
        logging.error(f"Create reply error: {e}")

def handle_create_forward(email_id: str, forward_to: str, email_content: str, additional_message: str):
    """Handle creating a forward draft"""
    try:
        # Get Gmail service
        gmail_service = get_gmail_service()
        if not gmail_service:
            st.error("❌ Gmail service not available")
            return
        
        # Create forward draft
        result = agent_logic.create_forward_draft(gmail_service, email_id, forward_to, email_content, additional_message)
        
        if result["success"]:
            st.success(f"📤 Forward draft created! Draft ID: {result['draft_id']}")
            st.info("💡 Check your Gmail drafts to review and send the forward.")
        else:
            st.error(f"❌ Failed to create forward: {result['error']}")
    except Exception as e:
        st.error(f"❌ Error creating forward: {str(e)}")
        logging.error(f"Create forward error: {e}")

def get_gmail_service():
    """Get Gmail service from session state or authenticate"""
    try:
        # Try to get from session state first
        if 'gmail_service' in st.session_state:
            return st.session_state.gmail_service
        
        # If not available, try to authenticate
        from auth_utils import get_authenticated_services
        gmail_service, _ = get_authenticated_services()
        
        if gmail_service:
            # Cache in session state
            st.session_state.gmail_service = gmail_service
            return gmail_service
        
        return None
    except Exception as e:
        logging.error(f"Failed to get Gmail service: {e}")
        return None

def handle_suggestion_click(suggestion_query: str):
    """
    Phase 2.2: Handle suggestion button clicks by processing the suggested query.
    """
    # Retrieve the LLM manager from session state
    llm_manager = st.session_state.llm_manager
    
    # Add user message for the suggestion click
    st.session_state.chat_history.append({
        'role': 'user',
        'content': suggestion_query,
        'timestamp': datetime.now()
    })
    
    # Process the suggested query
    memory_system = agent_memory.AgentMemory(db_client=database_utils.db)
    response_data = process_user_query(suggestion_query, memory_system, llm_manager)
    
    # Add assistant response
    st.session_state.chat_history.append({
        'role': 'assistant',
        'content': response_data['message'],
        'response_data': response_data,
        'timestamp': datetime.now()
    })
    
    # Trigger rerun to update the UI
    st.rerun()

def handle_send_chat():
    """Handle sending a chat message"""
    # Retrieve the LLM manager from session state
    llm_manager = st.session_state.llm_manager
    
    user_input = st.session_state.get("chat_input", "").strip()
    
    if user_input:
        # Add user message
        st.session_state.chat_history.append({
            'role': 'user',
            'content': user_input,
            'timestamp': datetime.now()
        })
        
        # Process query
        memory_system = agent_memory.AgentMemory(db_client=database_utils.db)
        response_data = process_user_query(user_input, memory_system, llm_manager)
        
        # Add assistant response
        st.session_state.chat_history.append({
            'role': 'assistant',
            'content': response_data['message'],
            'response_data': response_data,
            'timestamp': datetime.now()
        })
        
        # Clear input
        st.session_state.chat_input = ""

# === PHASE 9: TODAY'S AGENDA COMPONENT ===

def render_daily_agenda():
    """
    Render the Today's Agenda component - the pinnacle feature that transforms
    Maia from reactive to proactive by synthesizing emails, tasks, and calendar
    into a personalized daily agenda.
    """
    try:
        # Create agenda section header
        st.markdown("""
        <div class="section-title" style="background: linear-gradient(90deg, #667eea 0%, #764ba2 100%); 
                                          color: white; padding: 1rem; border-radius: 8px; margin-bottom: 1rem; 
                                          text-align: center; font-size: 1.1rem;">
            🌟 Today's Agenda - Your Personalized Daily Brief
        </div>
        """, unsafe_allow_html=True)
        
        # Add refresh button and loading state
        col1, col2 = st.columns([3, 1])
        
        with col2:
            if st.button("🔄 Refresh Agenda", key="refresh_agenda"):
                # Clear any cached agenda data
                if 'agenda_data' in st.session_state:
                    del st.session_state['agenda_data']
        
        # Check if agenda is cached in session state
        if 'agenda_data' not in st.session_state:
            # Show loading state
            with st.spinner("🔮 Curating your daily agenda..."):
                # Import and call the agenda synthesis function with dependency injection
                from agent_logic import build_daily_agenda
                
                # Get the one true manager from session state
                llm_manager = st.session_state.llm_manager
                if not llm_manager:
                    st.error("❌ LLM Manager not available. Please check your API key configuration.")
                    return
                
                # Pass it to the function (dependency injection)
                agenda_result = build_daily_agenda("default_user", llm_manager=llm_manager)
                st.session_state['agenda_data'] = agenda_result
        
        agenda_result = st.session_state['agenda_data']
        
        # Handle different agenda states
        if agenda_result['status'] == 'success':
            agenda_data = agenda_result['agenda']
            
            # Display greeting
            if agenda_data.get('greeting'):
                st.markdown(f"""
                <div style="background: var(--card-bg); border-radius: 8px; padding: 1rem; margin-bottom: 1rem; 
                           border-left: 4px solid #667eea; font-size: 1rem; color: var(--text-primary);">
                    {agenda_data['greeting']}
                </div>
                """, unsafe_allow_html=True)
            
            # Display key highlight
            if agenda_data.get('key_highlight'):
                st.markdown(f"""
                <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                           color: white; padding: 1rem; border-radius: 8px; margin-bottom: 1rem; 
                           font-weight: 500; text-align: center;">
                    💡 {agenda_data['key_highlight']}
                </div>
                """, unsafe_allow_html=True)
            
            # Display agenda items
            if agenda_data.get('agenda_items'):
                st.markdown("### 📋 Your Priority Items")
                
                for i, item in enumerate(agenda_data['agenda_items'], 1):
                    # Determine icon and color based on item type
                    type_config = {
                        'meeting': {'icon': '📅', 'color': '#4CAF50', 'bg_color': '#E8F5E8'},
                        'email': {'icon': '📧', 'color': '#FF9800', 'bg_color': '#FFF3E0'},
                        'task': {'icon': '✅', 'color': '#2196F3', 'bg_color': '#E3F2FD'},
                        'general': {'icon': '💼', 'color': '#9C27B0', 'bg_color': '#F3E5F5'}
                    }
                    
                    item_type = item.get('type', 'general')
                    config = type_config.get(item_type, type_config['general'])
                    
                    # Format the item display
                    title = item.get('title', item.get('subject', item.get('description', 'No Title')))
                    context = item.get('context', '')
                    time_info = item.get('time', '')
                    priority_info = item.get('priority', '')
                    
                    # Build the item card with interactive elements
                    item_id = f"agenda_item_{i}"
                    
                    # Add time prefix if available
                    time_prefix = f"**{time_info}** • " if time_info else ""
                    priority_prefix = f"**{priority_info}** • " if priority_info else ""
                    
                    st.markdown(f"""
                    <div style="background: {config['bg_color']}; border-left: 4px solid {config['color']}; 
                               border-radius: 8px; padding: 1rem; margin-bottom: 0.75rem;">
                        <div style="color: {config['color']}; font-weight: bold; margin-bottom: 0.5rem;">
                            {config['icon']} {time_prefix}{priority_prefix}{title}
                        </div>
                        <div style="color: var(--text-secondary); font-size: 0.9rem; line-height: 1.4;">
                            {context}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # Add action buttons for relevant items
                    if item_type == 'email':
                        col1, col2, col3, col4 = st.columns([1, 1, 1, 4])
                        with col1:
                            if st.button("📖 View", key=f"view_email_{i}"):
                                st.info("Navigate to Emails tab to view this email")
                        with col2:
                            if st.button("↩️ Reply", key=f"reply_email_{i}"):
                                st.info("Navigate to Emails tab to reply to this email")
                        with col3:
                            if st.button("✅ Mark Done", key=f"done_email_{i}"):
                                st.success("Email marked as handled!")
                    
                    elif item_type == 'task':
                        col1, col2, col3, col4 = st.columns([1, 1, 1, 4])
                        with col1:
                            if st.button("📋 View", key=f"view_task_{i}"):
                                st.info("Navigate to My Tasks tab to view task details")
                        with col2:
                            if st.button("✅ Complete", key=f"complete_task_{i}"):
                                st.success("Task marked as completed!")
                        with col3:
                            if st.button("📤 Export", key=f"export_task_{i}"):
                                st.info("Task export functionality - see My Tasks tab")
            
            # Display closing remark
            if agenda_data.get('closing_remark'):
                st.markdown(f"""
                <div style="background: var(--card-bg); border-radius: 8px; padding: 1rem; margin-top: 1rem; 
                           text-align: center; color: var(--text-secondary); font-style: italic;">
                    {agenda_data['closing_remark']}
                </div>
                """, unsafe_allow_html=True)
            
            # Show data source summary
            raw_data = agenda_result.get('raw_data', {})
            st.markdown(f"""
            <div style="color: var(--text-secondary); font-size: 0.8rem; text-align: center; margin-top: 1rem;">
                📊 Synthesized from {raw_data.get('emails_count', 0)} priority emails, 
                {raw_data.get('tasks_count', 0)} urgent tasks, and {raw_data.get('events_count', 0)} calendar events
            </div>
            """, unsafe_allow_html=True)
        
        elif agenda_result['status'] == 'error':
            # Handle error state gracefully
            error_message = agenda_result.get('message', 'Unknown error')
            
            # Check if this is an authentication-related error
            if any(auth_keyword in error_message.lower() for auth_keyword in ['authentication', 'token', 'refresh', 'oauth', 'credentials']):
                st.warning("⚠️ **Authentication Required**")
                st.markdown("""
                **Your Google authentication has expired.** Please run the following command in your terminal to log in again:
                
                ```bash
                python main.py
                ```
                
                This will open a browser window to re-authenticate with Google.
                """)
            else:
                st.warning(f"⚠️ **Agenda Synthesis Temporarily Unavailable**")
                st.markdown(f"**Issue:** {error_message}")
            
            # Show fallback information
            raw_data = agenda_result.get('raw_data', {})
            if any(raw_data.values()):
                st.markdown("**Available Data:**")
                if raw_data.get('emails_count', 0) > 0:
                    st.markdown(f"• {raw_data['emails_count']} priority emails (see Recent Activity below)")
                if raw_data.get('tasks_count', 0) > 0:
                    st.markdown(f"• {raw_data['tasks_count']} urgent tasks (see My Tasks tab)")
                if raw_data.get('events_count', 0) > 0:
                    st.markdown(f"• {raw_data['events_count']} calendar events")
            
            st.markdown("💡 **Tip:** Try refreshing the agenda or check your configuration settings.")
        
        # Add separator before other dashboard content
        st.markdown("---")
    
    except Exception as e:
        st.error(f"❌ **Error Loading Today's Agenda:** {str(e)}")
        st.markdown("""
        📖 **Troubleshooting:**
        - Ensure you have proper API keys configured
        - Check that agent_logic.py and hybrid_llm_system.py are available
        - Try refreshing the page or restart the application
        """)
        logging.error(f"Error rendering daily agenda: {e}", exc_info=True)


def render_chat_interface():
    """Render the main chat interface"""
    st.markdown('<div class="section-title">💬 Chat with Maia</div>', unsafe_allow_html=True)
    
    # Chat history container
    chat_container = st.container()
    
    with chat_container:
        # Create a scrollable chat area
        st.markdown('<div class="chat-container">', unsafe_allow_html=True)
        
        # Show greeting if no chat history
        if not st.session_state.chat_history:
            st.markdown("""
            <div class="chat-message assistant-message">
                👋 Hello! I'm Maia, your intelligent email assistant. I can help you:
                <ul>
                    <li>🔍 Find and prioritize important emails</li>
                    <li>📊 Analyze your email patterns</li>
                    <li>✍️ Draft responses and manage conversations</li>
                    <li>🤖 Explain my reasoning for email classifications</li>
                </ul>
                What would you like to know about your emails?
            </div>
            """, unsafe_allow_html=True)
        
        # Display chat history
        for i, message in enumerate(st.session_state.chat_history):
            message_class = "user-message" if message['role'] == 'user' else "assistant-message"
            
            st.markdown(f"""
            <div class="chat-message {message_class}">
                {message['content']}
            </div>
            """, unsafe_allow_html=True)
            
            # Phase 2.2: Show suggestion buttons after assistant messages
            if (message['role'] == 'assistant' and 
                'response_data' in message and 
                'suggestions' in message['response_data'] and 
                message['response_data']['suggestions'] and
                i == len(st.session_state.chat_history) - 1):  # Only show for latest message
                
                suggestions = message['response_data']['suggestions']
                
                st.markdown("**What's next?**")
                
                # Create columns for suggestion buttons
                num_suggestions = len(suggestions)
                if num_suggestions > 0:
                    cols = st.columns(num_suggestions)
                    
                    for j, suggestion in enumerate(suggestions):
                        with cols[j]:
                            # Create unique button key
                            button_key = f"suggestion_{i}_{j}_{suggestion['label'][:10]}"
                            
                            if st.button(
                                suggestion['label'], 
                                key=button_key,
                                use_container_width=True,
                                help=f"Execute: {suggestion['query']}"
                            ):
                                # Handle suggestion button click
                                handle_suggestion_click(suggestion['query'])
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Chat input
    col1, col2 = st.columns([5, 1])
    
    with col1:
        user_input = st.text_input(
            "Message",
            placeholder="Ask me about your emails...",
            key="chat_input",
            label_visibility="collapsed"
        )
    
    with col2:
        st.button("Send", key="send_chat", use_container_width=True, on_click=handle_send_chat)

def render_email_management():
    """Render email management interface"""
    st.markdown('<div class="section-title">📧 Email Management</div>', unsafe_allow_html=True)
    
    # Add email actions info banner
    st.info("✨ **New!** Each email now has action buttons: Archive, Label, Mark Important, Reply, and Forward. Look for the '⚡ Email Actions' expander in each email card.")
    
    # Quick actions
    action = ModernComponents.render_quick_actions()
    if action:
        st.session_state.current_view = action
        st.rerun()
    
    # Bulk Actions Section
    st.markdown('<div class="subsection-title">🔧 Bulk Actions</div>', unsafe_allow_html=True)
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if st.button("🗄️ Archive All Low Priority", help="Archive all LOW priority emails"):
            handle_bulk_archive_low_priority()
    
    with col2:
        if st.button("🏷️ Label by Priority", help="Add priority labels to emails"):
            handle_bulk_label_by_priority()
    
    with col3:
        st.selectbox("Filter by Purpose:", 
                    ["All", "promotion", "social", "newsletter", "action_required", "personal"],
                    key="purpose_filter")
    
    with col4:
        st.selectbox("Filter by Priority:",
                    ["All", "CRITICAL", "HIGH", "MEDIUM", "LOW"],
                    key="priority_filter")
    
    # Apply filters
    df = get_cached_email_data(50)  # Get more emails for filtering
    
    if not df.empty:
        # Apply filters
        purpose_filter = st.session_state.get("purpose_filter", "All")
        priority_filter = st.session_state.get("priority_filter", "All")
        
        if purpose_filter != "All":
            df = df[df['llm_purpose'] == purpose_filter]
        
        if priority_filter != "All":
            df = df[df['priority'] == priority_filter]
        
        # Limit to 20 for display
        df = df.head(20)
        
        st.markdown(f'<div class="subsection-title">📧 Emails ({len(df)} shown)</div>', unsafe_allow_html=True)
        
        if not df.empty:
            for _, email in df.iterrows():
                email_dict = email.to_dict()
                render_email_with_reasoning(email_dict, show_reasoning=True, prefix="mgmt_")
        else:
            st.info("No emails match the selected filters.")
    else:
        st.info("No emails found. Check your email processing configuration.")

def handle_bulk_archive_low_priority():
    """Handle bulk archiving of low priority emails"""
    try:
        gmail_service = get_gmail_service()
        if not gmail_service:
            st.error("❌ Gmail service not available")
            return
        
        # Get low priority emails
        df = get_cached_email_data(100)
        low_priority_emails = df[df['priority'] == 'LOW']
        
        if low_priority_emails.empty:
            st.info("No low priority emails found to archive.")
            return
        
        # Archive each email
        success_count = 0
        for _, email in low_priority_emails.iterrows():
            result = agent_logic.archive_email(gmail_service, email['id'])
            if result["success"]:
                success_count += 1
        
        st.success(f"✅ Successfully archived {success_count} low priority emails!")
        
        # Force cache refresh
        st.session_state.cache_timestamp = 0
        
    except Exception as e:
        st.error(f"❌ Error in bulk archive: {str(e)}")
        logging.error(f"Bulk archive error: {e}")

def handle_bulk_label_by_priority():
    """Handle bulk labeling emails by their priority"""
    try:
        gmail_service = get_gmail_service()
        if not gmail_service:
            st.error("❌ Gmail service not available")
            return
        
        # Get recent emails
        df = get_cached_email_data(50)
        
        if df.empty:
            st.info("No emails found to label.")
            return
        
        success_count = 0
        for _, email in df.iterrows():
            priority = email.get('priority', 'UNKNOWN')
            if priority and priority != 'UNKNOWN':
                label_name = f"Priority/{priority}"
                result = agent_logic.apply_label_to_email(gmail_service, email['id'], label_name)
                if result["success"]:
                    success_count += 1
        
        st.success(f"✅ Successfully labeled {success_count} emails with priority labels!")
        
    except Exception as e:
        st.error(f"❌ Error in bulk labeling: {str(e)}")
        logging.error(f"Bulk label error: {e}")

def render_insights_dashboard():
    """Render insights and analytics dashboard"""
    # Get insights data
    insights = get_cached_insights()
    
    # Render metrics dashboard
    ModernComponents.render_insight_dashboard(insights)
    
    # Additional charts
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown('<div class="subsection-title">Priority Distribution</div>', unsafe_allow_html=True)
        df = get_cached_email_data(100)
        if not df.empty:
            priority_counts = df['priority'].value_counts().to_dict()
            fig = create_modern_plotly_chart(priority_counts, 'pie')
            st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.markdown('<div class="subsection-title">Daily Email Volume</div>', unsafe_allow_html=True)
        # Create sample daily volume data
        daily_data = {'Mon': 12, 'Tue': 8, 'Wed': 15, 'Thu': 10, 'Fri': 6, 'Sat': 3, 'Sun': 2}
        fig = create_modern_plotly_chart(daily_data, 'bar')
        st.plotly_chart(fig, use_container_width=True)

def render_ai_insights_tab():
    """Render the AI Insights tab showing explainable AI analytics and learning transparency"""
    st.markdown('<div class="section-title">🧠 AI Learning Analytics & Transparency</div>', unsafe_allow_html=True)
    st.markdown("Understand how Maia learns from your feedback and makes decisions")
    
    try:
        # Get learning analytics data
        analytics = task_utils.get_learning_analytics("default_user")
        
        # Display key metrics using st.metric
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            accuracy_percentage = f"{analytics['accuracy_rate']:.1%}"
            delta_color = "normal"
            if analytics['recent_trend'] == "improving":
                delta_color = "normal"
            elif analytics['recent_trend'] == "declining":
                delta_color = "inverse"
            
            st.metric(
                label="🎯 AI Accuracy Rate",
                value=accuracy_percentage,
                delta=analytics['recent_trend'].title() if analytics['recent_trend'] != "neutral" else None
            )
        
        with col2:
            st.metric(
                label="📊 Total Feedback Given",
                value=analytics['total_feedback']
            )
        
        with col3:
            st.metric(
                label="✅ Correct AI Actions",
                value=analytics['positive_feedback']
            )
        
        with col4:
            st.metric(
                label="❌ User Corrections",
                value=analytics['negative_feedback']
            )
        
        # Learning status indicator
        st.markdown('<div class="subsection-title">🤖 AI Learning Status</div>', unsafe_allow_html=True)
        
        # Color-coded status based on accuracy
        status_color = "#28a745"  # Green
        if analytics['accuracy_rate'] < 0.5:
            status_color = "#dc3545"  # Red
        elif analytics['accuracy_rate'] < 0.7:
            status_color = "#ffc107"  # Yellow
        
        st.markdown(f"""
        <div style="
            background: linear-gradient(135deg, {status_color}20, {status_color}10);
            border-left: 4px solid {status_color};
            padding: 1rem;
            border-radius: 8px;
            margin: 1rem 0;
        ">
            <strong>Status:</strong> {analytics['learning_status']}<br>
            <small>The AI is continuously learning from your feedback to improve task detection and prioritization.</small>
        </div>
        """, unsafe_allow_html=True)
        
        # Learning over time visualization (if data is available)
        if analytics.get('feedback_by_date') and len(analytics['feedback_by_date']) > 1:
            st.markdown('<div class="subsection-title">📈 Learning Progress Over Time</div>', unsafe_allow_html=True)
            
            # Prepare data for chart
            dates = sorted(analytics['feedback_by_date'].keys())
            accuracy_data = []
            
            for date in dates:
                day_data = analytics['feedback_by_date'][date]
                total = day_data['positive'] + day_data['negative']
                if total > 0:
                    accuracy = day_data['positive'] / total
                    accuracy_data.append(accuracy)
                else:
                    accuracy_data.append(None)
            
            # Create DataFrame for line chart
            if accuracy_data and any(acc is not None for acc in accuracy_data):
                chart_data = pd.DataFrame({
                    'Date': dates,
                    'Accuracy Rate': accuracy_data
                })
                chart_data = chart_data.dropna()  # Remove rows with None values
                
                if not chart_data.empty:
                    st.line_chart(chart_data.set_index('Date'), y='Accuracy Rate')
                else:
                    st.info("Not enough data points to show learning trend yet. Keep providing feedback!")
            else:
                st.info("Learning trend will appear here as you provide more feedback over time.")
        else:
            st.info("💡 **Tip:** As you provide more feedback on AI actions, you'll see learning trends and progress charts here.")
        
        # Recent feedback insights
        if analytics['total_feedback'] > 0:
            st.markdown('<div class="subsection-title">🔍 Recent Learning Insights</div>', unsafe_allow_html=True)
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("**Feedback Breakdown**")
                feedback_data = {
                    'Positive': analytics['positive_feedback'],
                    'Corrections': analytics['negative_feedback']
                }
                
                if analytics.get('implicit_deletes', 0) > 0:
                    st.markdown(f"• Implicit corrections (task deletions): {analytics['implicit_deletes']}")
                
                # Simple feedback visualization
                for feedback_type, count in feedback_data.items():
                    percentage = (count / analytics['total_feedback']) * 100 if analytics['total_feedback'] > 0 else 0
                    st.progress(percentage / 100)
                    st.caption(f"{feedback_type}: {count} ({percentage:.0f}%)")
            
            with col2:
                st.markdown("**Learning Recommendations**")
                
                if analytics['accuracy_rate'] >= 0.9:
                    st.success("🎉 Excellent! The AI is performing very well.")
                elif analytics['accuracy_rate'] >= 0.7:
                    st.info("📚 Good progress! Continue providing feedback to improve accuracy.")
                elif analytics['total_feedback'] < 10:
                    st.warning("🔄 More feedback needed for better AI learning.")
                else:
                    st.warning("⚠️ Consider reviewing AI actions and providing specific feedback.")
                
                # Show learning tips
                st.markdown("**💡 Learning Tips:**")
                st.markdown("• Use 👍 for correct AI actions")
                st.markdown("• Use 👎 for incorrect AI actions")
                st.markdown("• Delete incorrect tasks to provide implicit feedback")
        
        else:
            st.info("""
            📖 **Welcome to AI Insights!**
            
            This dashboard will show how Maia learns from your feedback once you start using the system.
            
            **To get started:**
            1. Let Maia process some emails and detect tasks
            2. Provide feedback using 👍 and 👎 buttons
            3. Return here to see learning analytics and transparency data
            """)
    
    except Exception as e:
        st.error(f"❌ Error loading AI insights: {str(e)}")
        st.info("Please ensure the task feedback system is properly configured.")

def render_my_tasks():
    """Render the My Tasks tab with pending and completed tasks"""
    
    try:
        from task_utils import get_tasks_for_user, update_task_status, get_task_stats
    except ImportError:
        st.error("❌ Task management system not available. Please check if task_utils.py is properly installed.")
        return
    
    user_id = "default_user"  # Default user ID - in production this would come from authentication
    
    # Header
    st.markdown('<div class="section-title">✅ My Tasks</div>', unsafe_allow_html=True)
    
    # Get task statistics
    task_stats = get_task_stats(user_id)
    
    # Task statistics dashboard
    stats_col1, stats_col2, stats_col3, stats_col4 = st.columns(4)
    
    with stats_col1:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">{task_stats.get('total', 0)}</div>
            <div class="metric-label">Total Tasks</div>
        </div>
        """, unsafe_allow_html=True)
    
    with stats_col2:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">{task_stats.get('pending', 0)}</div>
            <div class="metric-label">Pending</div>
        </div>
        """, unsafe_allow_html=True)
    
    with stats_col3:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">{task_stats.get('completed', 0)}</div>
            <div class="metric-label">Completed</div>
        </div>
        """, unsafe_allow_html=True)
    
    with stats_col4:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">{task_stats.get('overdue', 0)}</div>
            <div class="metric-label">Overdue</div>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Task sections
    pending_col, completed_col = st.columns([1, 1])
    
    with pending_col:
        st.markdown('<div class="subsection-title">🕒 Pending Tasks</div>', unsafe_allow_html=True)
        
        # Get pending tasks
        pending_tasks = get_tasks_for_user(user_id, status_filter='pending')
        
        if not pending_tasks:
            st.info("🎉 No pending tasks! You're all caught up.")
        else:
            for task in pending_tasks:
                render_task_card(task, is_pending=True)
    
    with completed_col:
        st.markdown('<div class="subsection-title">✅ Completed Tasks</div>', unsafe_allow_html=True)
        
        # Get completed tasks (limit to recent 10)
        completed_tasks = get_tasks_for_user(user_id, status_filter='completed')[:10]
        
        if not completed_tasks:
            st.info("No completed tasks yet.")
        else:
            for task in completed_tasks:
                render_task_card(task, is_pending=False)
            
            if len(get_tasks_for_user(user_id, status_filter='completed')) > 10:
                st.markdown("*Showing 10 most recent completed tasks*")

def render_task_card(task: Dict[str, Any], is_pending: bool = True):
    """Render an individual task card"""
    
    try:
        from task_utils import update_task_status
    except ImportError:
        st.error("Task utilities not available")
        return
    
    task_id = task.get('id', '')
    task_description = task.get('task_description', 'No description')
    deadline = task.get('deadline')
    stakeholders = task.get('stakeholders', [])
    source_email_id = task.get('source_email_id', '')
    created_at = task.get('created_at')
    creation_method = task.get('creation_method', 'manual')
    
    # Format creation date
    if created_at:
        if hasattr(created_at, 'strftime'):
            created_str = created_at.strftime('%Y-%m-%d')
        else:
            created_str = str(created_at)[:10]  # Take first 10 chars for date
    else:
        created_str = 'Unknown'
    
    # Check if deadline is overdue
    is_overdue = False
    if deadline and is_pending:
        try:
            from dateutil import parser
            from datetime import timezone
            deadline_dt = parser.parse(deadline) if isinstance(deadline, str) else deadline
            if deadline_dt.tzinfo is None:
                deadline_dt = deadline_dt.replace(tzinfo=timezone.utc)
            is_overdue = deadline_dt < datetime.now(timezone.utc)
        except Exception:
            pass
    
    # Task card styling
    border_color = "var(--error)" if is_overdue else ("var(--success)" if not is_pending else "var(--primary)")
    
    with st.container():
        st.markdown(f"""
        <div class="modern-card" style="margin: 0.5rem 0; padding: 1rem; border-left: 4px solid {border_color};">
            <div style="margin-bottom: 0.75rem;">
                <div style="color: var(--text-primary); font-weight: 500; margin-bottom: 0.5rem;">
                    {html_module.escape(task_description)}
                </div>
        """, unsafe_allow_html=True)
        
        # Show autonomous creation indicator
        if creation_method == 'autonomous':
            st.markdown(f"""
                <div style="color: var(--accent); font-size: 0.75rem; margin-bottom: 0.5rem; font-weight: 500;">
                    🤖 Auto-detected on {created_str}
                </div>
            """, unsafe_allow_html=True)
        
        # Show deadline if available
        if deadline:
            deadline_color = "var(--error)" if is_overdue else "var(--warning)"
            overdue_text = " (OVERDUE)" if is_overdue else ""
            st.markdown(f"""
                <div style="color: {deadline_color}; font-size: 0.875rem; margin-bottom: 0.25rem;">
                    ⏰ <strong>Deadline:</strong> {html_module.escape(str(deadline) if deadline else 'No deadline')}{overdue_text}
                </div>
            """, unsafe_allow_html=True)
        
        # Show stakeholders if available
        if stakeholders:
            stakeholder_text = ", ".join(stakeholders)
            st.markdown(f"""
                <div style="color: var(--text-secondary); font-size: 0.875rem; margin-bottom: 0.25rem;">
                    👥 <strong>Stakeholders:</strong> {html_module.escape(stakeholder_text)}
                </div>
            """, unsafe_allow_html=True)
        
        # Show creation date
        st.markdown(f"""
            <div style="color: var(--text-muted); font-size: 0.75rem; margin-bottom: 0.5rem;">
                Created: {created_str}
            </div>
        """, unsafe_allow_html=True)
        
        st.markdown("</div>", unsafe_allow_html=True)
        
        # Action buttons (Phase 8: Added Export functionality)
        action_col1, action_col2, action_col3, action_col4 = st.columns([1, 1, 1, 1])
        
        with action_col1:
            if is_pending:
                if st.button("✅ Complete", key=f"complete_{task_id}", help="Mark this task as completed"):
                    if update_task_status(task_id, 'completed'):
                        st.success("Task marked as completed!")
                        st.rerun()
                    else:
                        st.error("Failed to update task status")
            else:
                st.markdown("*Completed*")
        
        with action_col2:
            if source_email_id:
                if st.button("📧 View Email", key=f"view_email_{task_id}", help="Go to source email"):
                    # Switch to Emails tab and highlight the source email
                    # This would require additional session state management
                    st.session_state['highlight_email'] = source_email_id
                    st.info("Email highlighting feature coming soon!")
        
        with action_col3:
            # Export button (Phase 8 Integration Feature)
            if st.button("🚀 Export", key=f"export_{task_id}", help="Export this task to external system"):
                try:
                    # Load config to get webhook URL
                    # Get configuration from session state
                    config = st.session_state.get('config', {})
                    webhook_url = config.get('integrations', {}).get('task_webhook_url', '')
                    
                    if webhook_url and webhook_url != "https://webhook.site/unique-id-here":
                        # Import the export function
                        from task_utils import export_task_to_webhook
                        
                        with st.spinner("🚀 Exporting task..."):
                            success = export_task_to_webhook(task, webhook_url)
                        
                        if success:
                            st.toast("✅ Task exported successfully!", icon="🚀")
                            logging.info(f"Task {task_id} exported successfully to {webhook_url}")
                        else:
                            st.error("❌ Export failed. Check logs for details.")
                    else:
                        # Show configuration instructions
                        st.warning("⚙️ Webhook URL not configured")
                        st.info("""
                        **To enable task export:**
                        1. Get a webhook URL from webhook.site or your task management system
                        2. Update `config.json` → `integrations` → `task_webhook_url`
                        3. Try exporting again
                        """)
                        
                except ImportError:
                    st.error("❌ Export functionality not available")
                except Exception as e:
                    st.error(f"❌ Export error: {str(e)}")
                    logging.error(f"Task export error for {task_id}: {e}")
        
        with action_col4:
            # Delete button with implicit feedback capture
            if st.button("🗑️ Delete", key=f"delete_{task_id}", help="Delete this task"):
                try:
                    from task_utils import delete_task_with_implicit_feedback
                    if delete_task_with_implicit_feedback(task_id, "default_user"):
                        st.success("Task deleted successfully!")
                        st.rerun()
                    else:
                        st.error("Failed to delete task")
                except ImportError:
                    st.error("Task deletion not available")
                except Exception as e:
                    st.error(f"Error deleting task: {e}")
        
        # === PHASE 6: FEEDBACK SECTION FOR AUTONOMOUS TASKS ===
        if creation_method == 'autonomous':
            try:
                from task_utils import submit_task_feedback, has_feedback_been_submitted, mark_task_as_incorrect_and_archive
                
                # Check if feedback has already been submitted
                feedback_submitted = has_feedback_been_submitted(task_id)
                
                if not feedback_submitted:
                    st.markdown("""
                    <div style="margin-top: 1rem; padding: 0.75rem; background: var(--card-bg); border-radius: 6px; border: 1px solid var(--border);">
                        <div style="color: var(--text-secondary); font-size: 0.8rem; margin-bottom: 0.5rem; font-weight: 500;">
                            🎯 Was this task correctly identified?
                        </div>
                    """, unsafe_allow_html=True)
                    
                    feedback_col1, feedback_col2 = st.columns(2)
                    
                    with feedback_col1:
                        if st.button("👍 Correct", key=f"feedback_positive_{task_id}", 
                                   help="This task was correctly identified by AI"):
                            try:
                                feedback_id = submit_task_feedback(task_id, "default_user", "positive")
                                st.success("✅ Thanks for your feedback! This helps Maia learn.")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Failed to submit feedback: {e}")
                    
                    with feedback_col2:
                        if st.button("👎 Incorrect", key=f"feedback_negative_{task_id}", 
                                   help="This should not have been identified as a task"):
                            try:
                                feedback_id = submit_task_feedback(task_id, "default_user", "negative")
                                mark_task_as_incorrect_and_archive(task_id, "default_user")
                                st.success("✅ Thanks for your feedback! Task has been removed.")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Failed to submit feedback: {e}")
                    
                    st.markdown("</div>", unsafe_allow_html=True)
                else:
                    # Show thank you message for already submitted feedback
                    st.markdown("""
                    <div style="margin-top: 1rem; padding: 0.5rem; background: var(--success-bg); border-radius: 6px; border: 1px solid var(--success);">
                        <div style="color: var(--success); font-size: 0.8rem; text-align: center;">
                            ✅ Thanks for your feedback!
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                    
            except ImportError as e:
                st.error(f"Feedback system not available: {e}")
        
        # Close the card
        st.markdown("</div>", unsafe_allow_html=True)

def main():
    """Main application function"""
    # Run pre-flight checks first - halt execution if critical prerequisites missing
    run_pre_flight_checks()
    
    # Check authentication - show login UI if needed
    from auth_utils import require_authentication
    if not require_authentication():
        return  # Authentication UI is shown, stop here
    
    # Initialize session state
    initialize_session_state()
    
    # Render header
    ModernComponents.render_agent_header()
    
    # Cache refresh button - accessible from all tabs
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("🔄 Refresh Emails", help="Clear cache and fetch fresh email data from database"):
            get_cached_email_data.clear()
            get_cached_insights.clear()  # Also clear insights cache since it depends on email data
            st.toast("Email cache cleared! Fetching fresh data...", icon="🔄")
            st.rerun()
    
    # Navigation tabs
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "🏠 Dashboard", 
        "💬 Chat", 
        "📧 Emails", 
        "✅ My Tasks",
        "📊 Analytics",
        "🧠 AI Insights"
    ])
    
    with tab1:
        # Dashboard view - combination of insights and recent activity
        insights = get_cached_insights()
        ModernComponents.render_insight_dashboard(insights)
        
        # === PHASE 9: TODAY'S AGENDA - The Crown Jewel Feature ===
        render_daily_agenda()
        
        # Recent activity
        st.markdown('<div class="section-title">🕒 Recent Activity</div>', unsafe_allow_html=True)
        
        recent_emails = get_cached_email_data(5)
        if not recent_emails.empty:
            for _, email in recent_emails.iterrows():
                email_dict = email.to_dict()
                render_email_with_reasoning(email_dict, show_reasoning=False, prefix="dash_")
        else:
            st.info("No recent email activity to display.")
        
        # Recent autonomous activity
        st.markdown('<div class="section-title">🤖 Recent Autonomous Activity</div>', unsafe_allow_html=True)
        
        try:
            from task_utils import get_recent_autonomous_tasks
            recent_autonomous_tasks = get_recent_autonomous_tasks("default_user", hours=24)
            
            if recent_autonomous_tasks:
                st.markdown(f"""
                <div style="background: var(--card-bg); border-radius: 8px; padding: 1rem; margin-bottom: 1rem; border: 1px solid var(--border);">
                    <div style="color: var(--text-secondary); font-size: 0.875rem; margin-bottom: 0.75rem;">
                        🎯 Maia auto-detected {len(recent_autonomous_tasks)} task(s) in the last 24 hours:
                    </div>
                """, unsafe_allow_html=True)
                
                for task in recent_autonomous_tasks[:3]:  # Show max 3 recent tasks
                    task_desc = task.get('task_description', 'Unknown task')
                    created_at = task.get('created_at')
                    source_email_id = task.get('source_email_id', '')
                    
                    # Format creation time
                    if created_at:
                        if hasattr(created_at, 'strftime'):
                            time_str = created_at.strftime('%H:%M')
                        else:
                            time_str = str(created_at)[:5]  # Take first 5 chars for time
                    else:
                        time_str = 'Unknown'
                    
                    st.markdown(f"""
                        <div style="margin: 0.5rem 0; padding: 0.5rem; background: var(--background); border-radius: 4px;">
                            <div style="color: var(--text-primary); font-size: 0.875rem; font-weight: 500;">
                                📝 {html_module.escape(task_desc[:80] + '...' if len(task_desc) > 80 else task_desc)}
                            </div>
                            <div style="color: var(--text-muted); font-size: 0.75rem;">
                                Detected at {time_str} from email
                            </div>
                        </div>
                    """, unsafe_allow_html=True)
                
                st.markdown("</div>", unsafe_allow_html=True)
                
                # Show link to full task list if there are many
                if len(recent_autonomous_tasks) > 3:
                    st.markdown(f"""
                    <div style="text-align: center; margin-top: 0.5rem;">
                        <span style="color: var(--text-secondary); font-size: 0.875rem;">
                            ... and {len(recent_autonomous_tasks) - 3} more. View all in "My Tasks" tab.
                        </span>
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.markdown("""
                <div style="background: var(--card-bg); border-radius: 8px; padding: 1rem; margin-bottom: 1rem; border: 1px solid var(--border);">
                    <div style="color: var(--text-secondary); font-size: 0.875rem; text-align: center;">
                        No autonomous tasks detected in the last 24 hours.
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
        except Exception as e:
            st.error(f"Could not load recent autonomous activity: {e}")
        
        # Quick chat interface
        st.markdown('<div class="section-title">💬 Quick Questions</div>', unsafe_allow_html=True)
        
        quick_col1, quick_col2, quick_col3 = st.columns(3)
        
        with quick_col1:
            if st.button("Show high priority emails", key="quick_high_priority"):
                # Add to chat history
                st.session_state.chat_history.append({
                    'role': 'user',
                    'content': 'Show me high priority emails',
                    'timestamp': datetime.now()
                })
                
                # Process and respond
                memory_system = agent_memory.AgentMemory(db_client=database_utils.db)
                response_data = process_user_query('high priority emails', memory_system, hybrid_llm_manager)
                
                st.session_state.chat_history.append({
                    'role': 'assistant',
                    'content': response_data['message'],
                    'response_data': response_data,
                    'timestamp': datetime.now()
                })
                
                st.rerun()
        
        with quick_col2:
            if st.button("Summarize my inbox", key="quick_summary"):
                st.session_state.chat_history.append({
                    'role': 'user',
                    'content': 'Summarize my inbox',
                    'timestamp': datetime.now()
                })
                
                memory_system = agent_memory.AgentMemory(db_client=database_utils.db)
                response_data = process_user_query('summary', memory_system, hybrid_llm_manager)
                
                st.session_state.chat_history.append({
                    'role': 'assistant',
                    'content': response_data['message'],
                    'response_data': response_data,
                    'timestamp': datetime.now()
                })
                
                st.rerun()
        
        with quick_col3:
            if st.button("Show recent emails", key="quick_recent"):
                st.session_state.chat_history.append({
                    'role': 'user',
                    'content': 'Show me recent emails',
                    'timestamp': datetime.now()
                })
                
                memory_system = agent_memory.AgentMemory(db_client=database_utils.db)
                response_data = process_user_query('recent emails', memory_system, hybrid_llm_manager)
                
                st.session_state.chat_history.append({
                    'role': 'assistant',
                    'content': response_data['message'],
                    'response_data': response_data,
                    'timestamp': datetime.now()
                })
                
                st.rerun()
    
    with tab2:
        # Full chat interface
        render_chat_interface()
    
    with tab3:
        # Email management interface
        render_email_management()
    
    with tab4:
        # My Tasks interface
        render_my_tasks()
    
    with tab5:
        # Analytics and insights
        render_insights_dashboard()
    
    with tab6:
        # AI Insights - Explainable AI analytics and learning transparency
        render_ai_insights_tab()
    
    # Footer
    st.markdown("""
    <div style="text-align: center; margin-top: 3rem; padding: 1rem; color: var(--text-muted); font-size: 0.875rem;">
        🤖 Maia Email Assistant • Enhanced with Explainable AI • Made with ❤️ using Streamlit
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()