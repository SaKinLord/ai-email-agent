# -*- coding: utf-8 -*-
"""
Created on Sun Apr 28 14:05:23 2025

@author: merto
"""

import logging
from datetime import datetime, timedelta, timezone
import json
from google.cloud import firestore
from google.api_core import exceptions
from google.cloud.firestore_v1.base_query import FieldFilter # Add this import for new query syntax
import re

# --- Constants ---
USER_MEMORY_COLLECTION = "user_memory"
CONVERSATION_COLLECTION = "conversations"
MEMORY_RETENTION_DAYS = 30  # How long to keep detailed conversation history

class AgentMemory:
    """
    Handles the agent's memory capabilities, including:
    - Conversation history tracking
    - User preferences and profile
    - Context awareness across sessions
    - Learning from interactions
    """
    
    def __init__(self, db_client=None, user_id="default_user"):
        """Initialize the memory system with a Firestore client and user ID"""
        self.db = db_client
        self.user_id = user_id
        self.session_id = datetime.now().strftime("%Y%m%d%H%M%S")
        self.session_start = datetime.now()
        self.session_conversations = []
        self.user_profile = self._load_user_profile()
        
        # Phase 2.1: Conversational Memory for Context Awareness
        self.last_context_emails = None  # Stores the last DataFrame of emails for follow-up commands
        
        logging.info(f"AgentMemory initialized for user {user_id}, session {self.session_id}")
    
    def _load_user_profile(self):
        """Load the user profile from Firestore or create a new one"""
        default_profile = {
            "first_seen": datetime.now(),
            "last_active": datetime.now(),
            "total_sessions": 1,
            "total_interactions": 0,
            "feedback_given": 0,
            "email_preferences": {
                "important_senders": [],
                "filtered_domains": [],
                "notification_preferences": {
                    "notify_critical": True,
                    "notify_high": True,
                    "email_notifications": False
                }
            },
            "agent_preferences": {
            "greeting_style": "friendly",
            "suggestion_frequency": "medium",
            "dismiss_count": 0,
            "autonomous_mode_enabled": False 
        },
            "topic_interests": {},
            "common_queries": {},
            "interaction_patterns": {
                "avg_session_length_minutes": 0,
                "peak_usage_hour": None,
                "most_frequent_day": None,
                "response_to_suggestions": 0.0  # Percentage of accepted suggestions
            }
        }
        
        if not self.db:
            logging.warning("No Firestore client available. Using default user profile.")
            return default_profile
        
        try:
            user_doc_ref = self.db.collection(USER_MEMORY_COLLECTION).document(self.user_id)
            user_doc = user_doc_ref.get()
            
            if user_doc.exists:
                profile = user_doc.to_dict()
                # Update the profile with session information
                profile["last_active"] = datetime.now()
                profile["total_sessions"] = profile.get("total_sessions", 0) + 1
                user_doc_ref.update({
                    "last_active": profile["last_active"],
                    "total_sessions": profile["total_sessions"]
                })
                logging.info(f"Loaded existing user profile for {self.user_id}")
                return profile
            else:
                # Create a new profile
                user_doc_ref.set(default_profile) # <--- Sets the default
                logging.info(f"Created new user profile for {self.user_id}")
                return default_profile
                
        except Exception as e:
            logging.error(f"Error loading user profile: {e}", exc_info=True)
            return default_profile
    
    def save_profile_updates(self, updates=None):
        """Save updates to the user profile"""
        if not self.db:
            logging.warning("No Firestore client available. Can't save profile updates.")
            return False
        
        if not updates:
            # Just update the last_active timestamp
            updates = {"last_active": datetime.now()}
        
        try:
            user_doc_ref = self.db.collection(USER_MEMORY_COLLECTION).document(self.user_id)
            user_doc_ref.update(updates)
            
            # Update local copy of profile
            for key, value in updates.items():
                if "." in key:  # Handle nested fields
                    parts = key.split(".")
                    if len(parts) == 2:
                        if parts[0] in self.user_profile:
                            self.user_profile[parts[0]][parts[1]] = value
                else:
                    self.user_profile[key] = value
                    
            logging.info(f"Updated user profile for {self.user_id}")
            return True
        except Exception as e:
            logging.error(f"Error updating user profile: {e}", exc_info=True)
            return False
    
    def add_interaction(self, user_message, agent_response, context=None):
        """
        Add an interaction to the memory system
        
        Args:
            user_message: The message from the user
            agent_response: The response from the agent
            context: Optional context dictionary with metadata about the interaction
        """
        timestamp = datetime.now()
        
        # Create interaction object
        interaction = {
            "timestamp": timestamp,
            "user_message": user_message,
            "agent_response": agent_response,
            "context": context or {}
        }
        
        # Add to session conversations
        self.session_conversations.append(interaction)
        
        # Update interaction count in profile
        self.user_profile["total_interactions"] = self.user_profile.get("total_interactions", 0) + 1
        self.save_profile_updates({"total_interactions": self.user_profile["total_interactions"]})
        
        # Update common queries tracking
        query_type = self._categorize_query(user_message)
        if query_type:
            common_queries = self.user_profile.get("common_queries", {})
            common_queries[query_type] = common_queries.get(query_type, 0) + 1
            self.save_profile_updates({"common_queries": common_queries})
        
        # Store in Firestore if available
        if self.db:
            try:
                # Store in conversation collection
                conv_ref = self.db.collection(CONVERSATION_COLLECTION).document()
                conv_data = {
                    "user_id": self.user_id,
                    "session_id": self.session_id,
                    "timestamp": timestamp,
                    "user_message": user_message,
                    "agent_response": agent_response,
                    "context": context or {}
                }
                conv_ref.set(conv_data)
                logging.debug(f"Stored conversation in Firestore for {self.user_id}")
            except Exception as e:
                logging.error(f"Error storing conversation: {e}", exc_info=True)
    
    def get_recent_conversations(self, limit=5):
        """Get the most recent conversations"""
        return self.session_conversations[-limit:] if self.session_conversations else []
    
    def get_related_conversations(self, query, limit=3):
        """Find conversations related to the given query"""
        if not self.session_conversations:
            return []
        
        # Simple keyword matching for now
        query_words = set(re.findall(r'\w+', query.lower()))
        results = []
        
        for conversation in reversed(self.session_conversations):
            user_msg = conversation.get("user_message", "").lower()
            agent_resp = conversation.get("agent_response", "").lower()
            
            user_words = set(re.findall(r'\w+', user_msg))
            agent_words = set(re.findall(r'\w+', agent_resp))
            
            # Calculate overlap
            user_overlap = len(query_words.intersection(user_words)) / max(1, len(query_words))
            agent_overlap = len(query_words.intersection(agent_words)) / max(1, len(query_words))
            
            # If significant overlap, add to results
            if user_overlap > 0.3 or agent_overlap > 0.3:
                results.append(conversation)
                if len(results) >= limit:
                    break
        
        return results
    
    def get_conversation_context(self, query):
        """
        Get context information based on conversation history
        
        Returns a dictionary with useful context derived from recent and related conversations
        """
        context = {
            "recent_topics": [],
            "recent_actions": [],
            "related_conversations": self.get_related_conversations(query),
            "session_length": (datetime.now() - self.session_start).total_seconds() // 60,  # minutes
            "interactions_this_session": len(self.session_conversations)
        }
        
        # Extract topics and actions from recent conversations
        for conv in self.get_recent_conversations(3):
            # Extract topic from context if available
            if conv.get("context") and conv["context"].get("topic"):
                context["recent_topics"].append(conv["context"]["topic"])
            
            # Extract actions from context if available
            if conv.get("context") and conv["context"].get("action"):
                context["recent_actions"].append(conv["context"]["action"])
        
        return context
    
    def clear_session(self):
        """Clear the current session data"""
        self.session_conversations = []
        logging.info(f"Cleared session data for user {self.user_id}")
    
    def _categorize_query(self, query):
        """Categorize the type of query to track common queries"""
        query_lower = query.lower()
        
        if "status" in query_lower or "how are you" in query_lower:
            return "status_check"
        elif "high priority" in query_lower or "important" in query_lower:
            return "priority_emails"
        elif "summarize" in query_lower:
            return "summarize_email"
        elif "action" in query_lower and "request" in query_lower:
            return "action_requests"
        elif "help" in query_lower:
            return "help_request"
        elif "setting" in query_lower or "preference" in query_lower:
            return "settings"
        else:
            return "other"
    
    def update_email_preferences(self, preference_type, values):
        """
        Update email preferences in the user profile
        
        Args:
            preference_type: Type of preference (important_senders, filtered_domains, notification_preferences)
            values: The values to set for this preference
        """
        if preference_type not in ["important_senders", "filtered_domains", "notification_preferences"]:
            logging.warning(f"Invalid preference type: {preference_type}")
            return False
        
        try:
            update_path = f"email_preferences.{preference_type}"
            self.save_profile_updates({update_path: values})
            logging.info(f"Updated {preference_type} preferences for user {self.user_id}")
            return True
        except Exception as e:
            logging.error(f"Error updating preferences: {e}", exc_info=True)
            return False
    
    def get_greeting(self):
        """
        Generate a personalized greeting based on user profile and history
        """
        # Get hour for time-based greeting
        hour = datetime.now().hour
        time_greeting = "Good morning" if hour < 12 else "Good afternoon" if hour < 17 else "Good evening"
        
        # Different greeting styles
        style = self.user_profile.get("agent_preferences", {}).get("greeting_style", "friendly")
        
        # For returning users
        sessions = self.user_profile.get("total_sessions", 1)
        last_active = self.user_profile.get("last_active", datetime.now())
        
        if isinstance(last_active, str):
            try:
                last_active = datetime.fromisoformat(last_active)
            except ValueError:
                last_active = datetime.now()
        
        days_since_last = (datetime.now() - last_active).days if isinstance(last_active, datetime) else 0
        
        # Generate greeting
        if style == "brief":
            if sessions > 5:
                return f"Hello again."
            return f"{time_greeting}."
        elif style == "professional":
            if sessions > 5 and days_since_last < 1:
                return f"Welcome back. How may I assist with your emails today?"
            return f"{time_greeting}. I'm ready to help manage your emails."
        else:  # friendly
            if sessions > 5:
                if days_since_last > 7:
                    return f"{time_greeting}! It's been {days_since_last} days - great to see you again! How can I help with your emails today?"
                elif days_since_last > 1:
                    return f"{time_greeting}! Welcome back after {days_since_last} days! How can I help with your emails today?"
                else:
                    return f"{time_greeting}! Good to see you again today! How can I help with your emails?"
            else:
                return f"{time_greeting}! I'm Maia, your email assistant. How can I help you today?"
    
    def should_suggest_proactively(self):
        """Determine if the agent should make proactive suggestions based on user preferences"""
        # Ensure agent_preferences and suggestion_frequency exist with defaults
        agent_prefs = self.user_profile.get("agent_preferences", {})
        suggestion_frequency = agent_prefs.get("suggestion_frequency", "medium") # Default to medium
    
        interactions = len(self.session_conversations)
    
        if suggestion_frequency == "high":
            return interactions % 2 == 0
        elif suggestion_frequency == "medium":
            return interactions % 3 == 0
        else:  # low
            return interactions % 5 == 0
    
    def record_suggestion_response(self, suggestion_id, was_accepted):
        """
        Record how the user responded to a suggestion
        
        Args:
            suggestion_id: Identifier for the suggestion
            was_accepted: Boolean indicating if the suggestion was accepted
        """
        # Update acceptance rate
        interaction_patterns = self.user_profile.get("interaction_patterns", {})
        response_rate = interaction_patterns.get("response_to_suggestions", 0.0)
        suggestion_count = interaction_patterns.get("suggestion_count", 0)
        
        # Calculate new rate
        new_count = suggestion_count + 1
        new_rate = ((response_rate * suggestion_count) + (1.0 if was_accepted else 0.0)) / new_count
        
        # Update profile
        updates = {
            "interaction_patterns.response_to_suggestions": new_rate,
            "interaction_patterns.suggestion_count": new_count
        }
        
        if was_accepted:
            updates["interaction_patterns.accepted_suggestions"] = interaction_patterns.get("accepted_suggestions", 0) + 1
        else:
            updates["interaction_patterns.dismissed_suggestions"] = interaction_patterns.get("dismissed_suggestions", 0) + 1
            updates["agent_preferences.dismiss_count"] = self.user_profile.get("agent_preferences", {}).get("dismiss_count", 0) + 1
        
        self.save_profile_updates(updates)
    
    def get_user_preferences(self):
        """Get all user preferences"""
        return {
            "email_preferences": self.user_profile.get("email_preferences", {}),
            "agent_preferences": self.user_profile.get("agent_preferences", {})
        }
    
    def get_conversation_history(self, limit: int = 10, filters: dict = None) -> list:
        """
        Retrieves the most recent conversation history for the user.

        Args:
            limit (int): The maximum number of conversation entries to retrieve.
            filters (dict): Optional filters to apply to the query (e.g., {'sender': 'email@example.com'}).

        Returns:
            list: A list of conversation history dictionaries, ordered by timestamp.
                  Returns an empty list if no history is found or an error occurs.
        """
        if not self.db:
            logging.error("Database client not available in get_conversation_history.")
            return []
        
        try:
            # Get the user document reference and access the conversation_history subcollection
            user_doc_ref = self.db.collection(USER_MEMORY_COLLECTION).document(self.user_id)
            history_ref = user_doc_ref.collection('conversation_history')
            
            # Start with base query
            query = history_ref
            
            # Apply filters if provided
            if filters:
                for field, value in filters.items():
                    query = query.where(filter=FieldFilter(field, '==', value))
            
            # Order by timestamp and limit results
            query = query.order_by(
                'timestamp', direction=firestore.Query.DESCENDING
            ).limit(limit)
            
            history_entries = [doc.to_dict() for doc in query.stream()]
            
            # Reverse the list to have the oldest message first
            history_entries.reverse()
            
            logging.info(f"Retrieved {len(history_entries)} conversation history entries for user {self.user_id} (filters: {filters}).")
            return history_entries
            
        except Exception as e:
            logging.error(f"Failed to retrieve conversation history for user {self.user_id}: {e}", exc_info=True)
            return []
    
    def clean_old_conversations(self):
        """Remove conversations older than the retention period"""
        if not self.db:
            return
        
        try:
            retention_date = datetime.now() - timedelta(days=MEMORY_RETENTION_DAYS)
            old_convs = self.db.collection(CONVERSATION_COLLECTION)\
                            .where(filter=FieldFilter("user_id", "==", self.user_id))\
                            .where(filter=FieldFilter("timestamp", "<", retention_date))\
                            .stream()
            
            batch = self.db.batch()
            count = 0
            
            for doc in old_convs:
                batch.delete(doc.reference)
                count += 1
                
                # Firestore batches limited to 500 operations
                if count >= 450:
                    batch.commit()
                    batch = self.db.batch()
                    count = 0
            
            if count > 0:
                batch.commit()
            
            logging.info(f"Cleaned old conversations for user {self.user_id}")
        except Exception as e:
            logging.error(f"Error cleaning old conversations: {e}", exc_info=True)
    
    # Phase 2.1: Conversational Memory Methods
    
    def update_last_context(self, emails_df):
        """
        Store the provided DataFrame as the last context for follow-up commands.
        
        Args:
            emails_df: pandas.DataFrame containing email data from the last query
        """
        import pandas as pd
        
        if emails_df is not None and isinstance(emails_df, pd.DataFrame) and not emails_df.empty:
            self.last_context_emails = emails_df.copy()  # Make a copy to avoid reference issues
            logging.info(f"Updated last context with {len(emails_df)} emails")
        else:
            self.last_context_emails = None
            logging.info("Cleared last context (empty or invalid DataFrame provided)")
    
    def get_last_context(self):
        """
        Return the stored DataFrame from the last context.
        
        Returns:
            pandas.DataFrame or None: The last context emails or None if no context available
        """
        return self.last_context_emails
    
    def clear_context(self):
        """Reset the last context emails to None."""
        self.last_context_emails = None
        logging.info("Cleared conversational context")

# Add this to agent_memory.py or create a new suggestion_history.py

class SuggestionHistory:
    """Handles tracking and retrieval of suggestion history"""
    
    def __init__(self, db_client=None, user_id="default_user"):
        self.db = db_client
        self.user_id = user_id
        self.SUGGESTIONS_COLLECTION = "suggestion_history"
    
    def record_suggestion(self, suggestion_data, was_shown=True, was_accepted=None):
        """
        Record a suggestion event in the database
        
        Args:
            suggestion_data: Dictionary with suggestion details
            was_shown: Boolean indicating if suggestion was displayed
            was_accepted: Boolean or None - True if accepted, False if dismissed, None if no response yet
        
        Returns:
            str: The ID of the created record or None on failure
        """
        if not self.db:
            logging.warning("Database client not available for recording suggestion.")
            return None
            
        try:
            suggestion_ref = self.db.collection(self.SUGGESTIONS_COLLECTION).document()
            
            # Extract key data from suggestion
            suggestion_type = suggestion_data.get('type', 'unknown')
            suggestion_title = suggestion_data.get('title', 'Untitled Suggestion')
            suggestion_action = suggestion_data.get('action', 'unknown_action')
            suggestion_priority = suggestion_data.get('priority', 'medium')
            
            # Create record document
            record_data = {
                'user_id': self.user_id,
                'suggestion_type': suggestion_type,
                'suggestion_title': suggestion_title,
                'suggestion_action': suggestion_action,
                'suggestion_priority': suggestion_priority,
                'timestamp': firestore.SERVER_TIMESTAMP,
                'was_shown': was_shown,
                'was_accepted': was_accepted,
                'response_timestamp': None,
                'context_data': suggestion_data.get('action_params', {})
            }
            
            # Save to Firestore
            suggestion_ref.set(record_data)
            
            # Return the document ID for reference
            return suggestion_ref.id
            
        except Exception as e:
            logging.error(f"Error recording suggestion history: {e}", exc_info=True)
            return None
    
    def update_suggestion_response(self, suggestion_id, was_accepted):
        """
        Update a suggestion record with user's response
        
        Args:
            suggestion_id: ID of the suggestion record
            was_accepted: Boolean - True if accepted, False if dismissed
            
        Returns:
            Boolean indicating success
        """
        if not self.db:
            return False
            
        try:
            suggestion_ref = self.db.collection(self.SUGGESTIONS_COLLECTION).document(suggestion_id)
            
            suggestion_ref.update({
                'was_accepted': was_accepted,
                'response_timestamp': firestore.SERVER_TIMESTAMP
            })
            
            return True
        except Exception as e:
            logging.error(f"Error updating suggestion response: {e}", exc_info=True)
            return False
    
    def get_recent_history(self, limit=20):
        """
        Get recent suggestion history for the user (with error handling)

        Args:
            limit: Maximum number of records to return

        Returns:
            List of suggestion history records or empty list on error
        """
        if not self.db:
            logging.warning("SuggestionHistory: Database client not available for get_recent_history.")
            return []

        history_records = []
        try:
            query = self.db.collection(self.SUGGESTIONS_COLLECTION)\
                          .where(filter=FieldFilter('user_id', '==', self.user_id))\
                          .order_by('timestamp', direction=firestore.Query.DESCENDING)\
                          .limit(limit)

            results = query.stream()

            for doc in results:
                record = doc.to_dict()
                record['id'] = doc.id
                history_records.append(record)

            return history_records

        except exceptions.FailedPrecondition as e:
            # Specific handling for missing index error
            logging.error(f"Error fetching suggestion history: Missing Firestore index. Please create it. Details: {e}", exc_info=False) # Log less verbosely for this common error
            # Optionally, extract the index creation URL if needed, though it's in the main logs
            # index_match = re.search(r'(https://console.firebase.google.com/.*?)\s*$', str(e))
            # if index_match: logging.error(f"Index creation URL: {index_match.group(1)}")
            return [] # Return empty list gracefully
        except Exception as e:
            logging.error(f"Unexpected error fetching suggestion history: {e}", exc_info=True)
            return [] # Return empty list for other errors

    def get_type_history(self, suggestion_type, limit=10):
        """
        Get history for a specific suggestion type (with error handling)

        Args:
            suggestion_type: Type of suggestions to retrieve
            limit: Maximum number of records to return

        Returns:
            List of suggestion history records for the specified type or empty list on error
        """
        if not self.db:
            logging.warning("SuggestionHistory: Database client not available for get_type_history.")
            return []

        history_records = []
        try:
            query = self.db.collection(self.SUGGESTIONS_COLLECTION)\
                          .where(filter=FieldFilter('user_id', '==', self.user_id))\
                          .where(filter=FieldFilter('suggestion_type', '==', suggestion_type))\
                          .order_by('timestamp', direction=firestore.Query.DESCENDING)\
                          .limit(limit)

            results = query.stream()

            for doc in results:
                record = doc.to_dict()
                record['id'] = doc.id
                history_records.append(record)

            return history_records

        except exceptions.FailedPrecondition as e:
            # Specific handling for missing index error
            logging.error(f"Error fetching suggestion type history for '{suggestion_type}': Missing Firestore index. Please create it. Details: {e}", exc_info=False)
            return [] # Return empty list gracefully
        except Exception as e:
            logging.error(f"Unexpected error fetching suggestion type history for '{suggestion_type}': {e}", exc_info=True)
            return [] # Return empty list for other errors

    def get_stats(self, days_back=30):
        """
        Get suggestion statistics for analytics (with error handling)

        Args:
            days_back: Number of days to analyze

        Returns:
            Dictionary with statistics or empty dict on error
        """
        if not self.db:
            logging.warning("SuggestionHistory: Database client not available for get_stats.")
            return {}

        try:
            # Calculate the cutoff date
            # Ensure cutoff_date is timezone-aware if comparing with Firestore timestamps
            # Assuming Firestore timestamps are UTC
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_back)

            # Query all suggestions within the time period
            query = self.db.collection(self.SUGGESTIONS_COLLECTION)\
                          .where(filter=FieldFilter('user_id', '==', self.user_id))\
                          .where(filter=FieldFilter('timestamp', '>=', cutoff_date))
                          # Note: Cannot order by timestamp here if filtering by it with >=
                          # We will process all results and sort/analyze in memory if needed
                          # Or, if ordering is critical, the index needs timestamp ASC/DESC

            results = query.stream() # Use stream() for potentially large results

            # Process the results
            total_shown = 0
            total_accepted = 0
            total_dismissed = 0
            total_no_response = 0
            by_type = {}

            for doc in results:
                data = doc.to_dict()

                # Count totals
                if data.get('was_shown', False):
                    total_shown += 1

                    # Count by response
                    if data.get('was_accepted') is True:
                        total_accepted += 1
                    elif data.get('was_accepted') is False:
                        total_dismissed += 1
                    else:
                        total_no_response += 1

                # Count by type
                suggestion_type = data.get('suggestion_type', 'unknown')
                if suggestion_type not in by_type:
                    by_type[suggestion_type] = {
                        'shown': 0, 'accepted': 0, 'dismissed': 0, 'no_response': 0
                    }

                type_stats = by_type[suggestion_type]
                # Ensure we only count shown suggestions towards type stats if was_shown is True
                if data.get('was_shown', False):
                    type_stats['shown'] += 1
                    if data.get('was_accepted') is True:
                        type_stats['accepted'] += 1
                    elif data.get('was_accepted') is False:
                        type_stats['dismissed'] += 1
                    else:
                        type_stats['no_response'] += 1

            # Calculate rates
            acceptance_rate = total_accepted / total_shown if total_shown > 0 else 0
            dismissal_rate = total_dismissed / total_shown if total_shown > 0 else 0

            # Prepare the result
            return {
                'total_shown': total_shown,
                'total_accepted': total_accepted,
                'total_dismissed': total_dismissed,
                'total_no_response': total_no_response,
                'acceptance_rate': acceptance_rate,
                'dismissal_rate': dismissal_rate,
                'by_type': by_type,
                'days_analyzed': days_back
            }

        except exceptions.FailedPrecondition as e:
             # Specific handling for missing index error
            logging.error(f"Error calculating suggestion stats: Missing Firestore index. Please create it. Details: {e}", exc_info=False)
            return {} # Return empty dict gracefully
        except Exception as e:
            logging.error(f"Unexpected error calculating suggestion stats: {e}", exc_info=True)
            return {} # Return empty dict for other errors