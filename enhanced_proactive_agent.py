# enhanced_proactive_agent.py

# -*- coding: utf-8 -*-
"""
Created on Sun Apr 28 14:21:44 2025

@author: merto
"""

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta, time, timezone
import re
import html
from collections import Counter
import logging
import json
import random
# from datetime import datetime, timezone, timedelta # Original line - now combined above
from agent_memory import AgentMemory,SuggestionHistory
# import time # Keep this separate import for time.sleep if used elsewhere
from agent_logic import summarize_email_with_memory,get_calendar_service, create_calendar_event, parse_email_content, get_email_details,list_sent_emails,check_thread_for_reply
from google.cloud import firestore,storage
from google.cloud.firestore_v1.base_query import FieldFilter
import database_utils
import os

# --- UI Color Constants (copied from ui_app.py for rendering within this agent) ---
PRIMARY_COLOR = "#0078ff"
ERROR_COLOR = "#ff4b4b"
WARNING_COLOR = "#ff9900"
MUTED_COLOR = "#6c757d"
SUCCESS_COLOR = "#00c853" 
ACCENT_COLOR = "#3da5f4"  

# --- Define constants if not already globally available ---
EMAILS_COLLECTION = "emails"
PRIORITY_CRITICAL = "CRITICAL"
PRIORITY_HIGH = "HIGH"
PRIORITY_MEDIUM = "MEDIUM" # Added just in case
PRIORITY_LOW = "LOW"
MAX_EMAILS_TO_SUMMARIZE = 3
MAX_EMAILS_TO_ARCHIVE = 15
MAX_MEETINGS_TO_LIST = 5 # Limit for meeting list

def _extract_email_address(sender_string):
    """Extracts the email address from a sender string."""
    if not isinstance(sender_string, str): return None
    # Regex to find something that looks like an email address
    match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', sender_string)
    if match:
        return match.group(0)
    # Fallback if no standard email found (e.g., just a name)
    # Clean potential problematic characters just in case
    return re.sub(r'[<>"]', '', sender_string).strip() if sender_string else None
# --- !! END HELPER FUNCTION DEFINITION !! ---

class ProactiveAgent:
    """
    Enhanced proactive agent that provides smart suggestions
    and can take autonomous actions based on user preferences.
    """

    # --- MODIFIED __init__ ---
    def __init__(self, db_client=None, memory=None, user_id="default_user", llm_client=None, config=None, gmail_service=None): # Added llm_client, config
        """Initialize the proactive agent with database client, memory system, LLM client, and config"""
        self.db = db_client
        self.memory = memory if memory else AgentMemory(db_client, user_id)
        self.user_id = user_id
        self.llm_client = llm_client # Store LLM client
        self.config = config # Store config
        self.gmail_service = gmail_service
        self.suggestion_history = SuggestionHistory(db_client=db_client, user_id=user_id)
        self.suggestion_types = {
            "sender_rule": self.generate_sender_rule_suggestion, 
            "domain_filter": self.generate_domain_filter_suggestion,
            "pending_actions": self._generate_action_request_suggestion,
            "unanswered_questions": self._generate_question_suggestion,
            "high_priority": self._generate_high_priority_suggestion,
            "time_management": self._generate_time_management_suggestion,
            "recurring_meeting": self._generate_recurring_meeting_suggestion,
            "scheduled_send": self._generate_scheduled_send_suggestion,
            "email_cleanup": self._generate_email_cleanup_suggestion,
            "priority_summary": self._generate_priority_summary_suggestion,
            "follow_up": self._generate_follow_up_suggestion
        }
        # Add checks for required dependencies
        if not self.llm_client:
            logging.warning("ProactiveAgent initialized without an LLM client. Some actions may fail.")
        if not self.config:
            logging.warning("ProactiveAgent initialized without config. Some actions may fail.")
        if not self.db:
            logging.warning("ProactiveAgent initialized without Firestore client. Database operations will fail.")
        if not self.gmail_service:
             logging.warning("ProactiveAgent initialized without Gmail service. Some actions may fail.")

        logging.info("ProactiveAgent initialized")

    
    def analyze_email_patterns(self, email_df):
        """
        Analyze email patterns to generate insights and suggestions

        Args:
            email_df: DataFrame with email data

        Returns:
            dict: Insights from email analysis
        """
        if email_df.empty:
            return None

        insights = {}

        # Frequency analysis by sender
        if 'Sender' in email_df.columns:
            sender_counts = Counter()
            domain_counts = Counter()

            for sender in email_df['Sender']:
                sender_counts[sender] += 1
                # Extract domain
                domain_match = re.search(r'@([\w.-]+)', sender)
                if domain_match:
                    domain = domain_match.group(1).lower()
                    domain_counts[domain] += 1

            # Get top senders
            insights['top_senders'] = sender_counts.most_common(5)
            insights['top_domains'] = domain_counts.most_common(5)

        # Priority distribution
        if 'Agent Priority' in email_df.columns:
            priority_counts = email_df['Agent Priority'].value_counts().to_dict()
            insights['priority_distribution'] = priority_counts

        # Purpose/intent distribution
        if 'Purpose' in email_df.columns:
            purpose_counts = email_df['Purpose'].value_counts().to_dict()
            insights['purpose_distribution'] = purpose_counts

            # Check for emails that need follow-up
            action_emails = email_df[email_df['Purpose'] == 'Action Request']
            question_emails = email_df[email_df['Purpose'] == 'Question']
            meeting_emails = email_df[email_df['Purpose'] == 'Meeting Invite']

            insights['action_emails_count'] = len(action_emails)
            insights['question_emails_count'] = len(question_emails)
            insights['meeting_emails_count'] = len(meeting_emails)

        # Time-based analysis - when emails arrive
        if 'Processed At' in email_df.columns:
            # Extract timestamps if they're strings
            if email_df['Processed At'].dtype == 'object':
                try:
                    timestamps = pd.to_datetime(email_df['Processed At'])
                    # Get hour distribution
                    hour_counts = timestamps.dt.hour.value_counts().sort_index().to_dict()
                    insights['hour_distribution'] = hour_counts

                    # Get day distribution
                    day_counts = timestamps.dt.day_name().value_counts().to_dict()
                    insights['day_distribution'] = day_counts
                except:
                    logging.warning("Could not parse timestamp data for time analysis")

        # Subject analysis - identify recurring themes
        if 'Subject' in email_df.columns:
            # Perform simple keyword extraction
            subjects = " ".join(email_df['Subject'].astype(str))
            common_words = Counter(re.findall(r'\b[A-Za-z]{3,}\b', subjects.lower()))
            # Remove very common words
            for word in ['the', 'and', 'for', 'you', 'your', 'our', 'this', 'that', 'with', 'from']:
                if word in common_words:
                    del common_words[word]

            insights['subject_themes'] = common_words.most_common(10)

        return insights



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
        ]

        # Ensure all defined types are in the priority list
        for key in self.suggestion_types.keys():
            if key not in suggestion_priority_order:
                suggestion_priority_order.append(key) # Add any missing ones at the end

        # Generate ALL potentially valid suggestions first
        all_qualifying_suggestions = []
        logging.debug(f"Checking suggestion types in order: {suggestion_priority_order}")

        for suggestion_type in suggestion_priority_order:
            # --- Check if suggestion type should be shown FIRST ---
            if not self.should_show_suggestion_type(suggestion_type):
                logging.debug(f"Skipping suggestion type '{suggestion_type}' due to recent dismissal or cooldown.")
                continue # Skip to the next type

            # --- Get the generator function ---
            generator_func = self.suggestion_types.get(suggestion_type)
            if not generator_func:
                logging.warning(f"No generator function found for suggestion type: {suggestion_type}")
                continue # Skip if no generator exists

            # --- Now, safely try to generate the suggestion ---
            try:
                # Pass user_preferences here if needed by generator
                suggestion = generator_func(email_df, insights, user_preferences)
                if suggestion:
                    # Calculate relevance score (ensure this method handles errors)
                    try:
                        relevance_score = self.get_suggestion_type_score(suggestion_type)
                    except Exception as score_e:
                        logging.error(f"Error calculating score for {suggestion_type}: {score_e}", exc_info=True)
                        relevance_score = 0.5 # Default score on error
                    suggestion['relevance_score'] = relevance_score

                    # Ensure type is correctly set
                    if suggestion.get("type") != suggestion_type:
                         logging.warning(f"Mismatch: Generator for {suggestion_type} produced type {suggestion.get('type')}. Forcing.")
                         suggestion["type"] = suggestion_type

                    all_qualifying_suggestions.append(suggestion)
                    logging.debug(f"Qualified suggestion generated: Type='{suggestion_type}'")
                # else: # Optional log for non-qualifying generators
                #    logging.debug(f"Generator for '{suggestion_type}' returned None (did not qualify).")

            except Exception as e:
                # Catch errors during the specific generator function call
                logging.error(f"Error generating suggestion with generator for type '{suggestion_type}': {e}", exc_info=True)
                # Continue to the next suggestion type even if one fails

        # Sort by priority first, then by relevance score
        priority_order = {'critical': 0, 'high': 1, 'medium': 2, 'low': 3}
        sorted_suggestions = sorted(
            all_qualifying_suggestions,
            key=lambda s: (
                priority_order.get(s.get('priority', 'medium'), 99),  # Sort by priority first
                -s.get('relevance_score', 0)  # Then by relevance score (descending)
            )
        )

        # Select the top N suggestions based on the priority order
        max_suggestions = 3 # Let's reduce this for stability during testing
        final_suggestions = sorted_suggestions[:max_suggestions]

        logging.info(f"Generated {len(final_suggestions)} suggestions (out of {len(all_qualifying_suggestions)} qualifying). Types: {[s.get('type') for s in final_suggestions]}")
        return final_suggestions



    def generate_sender_rule_suggestion(self, email_df, insights, user_preferences):
        """Generate suggestion for creating a rule for a frequent sender"""
        if not insights or 'top_senders' not in insights or not insights['top_senders']:
            return None
        
        if insights and 'top_senders' in insights and insights['top_senders']:
            # --- Get important senders from provided preferences or memory ---
            important_senders = []
            if user_preferences and "email_preferences" in user_preferences:
                 important_senders = user_preferences.get("email_preferences", {}).get("important_senders", [])
            elif self.memory: # Fallback to fetching directly if needed (should be passed ideally)
                 prefs = self.memory.get_user_preferences()
                 important_senders = prefs.get("email_preferences", {}).get("important_senders", [])
            # Ensure comparison is case-insensitive and handles different formats
            important_senders_lower = {s.lower() for s in important_senders}
            # --- End Get important senders ---
            for sender_raw, count in insights['top_senders']:
                # --- Add Cleaning/Escaping (keep this) ---
                sender_display_name = sender_raw # Default
                email_part = _extract_email_address(sender_raw)
                name_match = re.match(r'^\s*"?([^"<]+)"?\s*<.*?>\s*$', sender_raw)
                if name_match: sender_display_name = name_match.group(1).strip()
                elif email_part and email_part != sender_raw:
                     potential_name = sender_raw.split('<')[0].strip()
                     if potential_name: sender_display_name = potential_name
                     else: sender_display_name = email_part
                elif email_part: sender_display_name = email_part
                sender_display_safe = html.escape(sender_display_name)
                # --- End Cleaning/Escaping ---
                
                # --- !! ADD CHECK: Is this sender already important? !! ---
                sender_raw_lower = sender_raw.lower()
                is_already_important = any(imp in sender_raw_lower for imp in important_senders_lower) or sender_raw_lower in important_senders_lower
                # --- !! END CHECK !! ---
                
                if count > 5 and not is_already_important:
                    description_text = f"You've received {count} emails from `{sender_display_safe}`. Want to set a priority rule?"
                    rationale_text = (f"This sender ('{sender_display_safe}') has sent you {count} emails recently. "
                                      f"Creating a rule can help automatically prioritize future communications from them. "
                                      f"This sender is not currently in your important senders list.")
                    return {
                        "type": "sender_rule",
                        "title": f"Create rule for {sender_display_safe}", # Ensure this specific title is used
                        "description": description_text,
                        "action": "create_sender_rule",
                        "action_params": {"sender": sender_raw},
                        "priority": "medium",
                        "rationale": rationale_text
                    }
        return None

    def generate_domain_filter_suggestion(self, email_df, insights, user_preferences):
        """Generate suggestion for filtering emails from a domain"""
        if not insights or 'top_domains' not in insights:
            return None
        
        if insights and 'top_domains' in insights and insights['top_domains']:
            # --- Get filtered domains from provided preferences or memory ---
            filtered_domains = []
            if user_preferences and "email_preferences" in user_preferences:
                filtered_domains = user_preferences.get("email_preferences", {}).get("filtered_domains", [])
            elif self.memory:
                prefs = self.memory.get_user_preferences()
                filtered_domains = prefs.get("email_preferences", {}).get("filtered_domains", [])
            # Ensure comparison is case-insensitive
            filtered_domains_lower = {d.lower() for d in filtered_domains}
            # --- End Get filtered domains ---
            for domain_raw, count in insights['top_domains']:
                # Skip common providers
                if domain_raw in ['gmail.com', 'outlook.com', 'hotmail.com', 'yahoo.com']:
                    continue
                # --- !! ADD CHECK: Is this domain already filtered? !! ---
                domain_raw_lower = domain_raw.lower()
                domain_check_at = f"@{domain_raw_lower}" # Format with @
                is_already_filtered = (domain_raw_lower in filtered_domains_lower or
                                       domain_check_at in filtered_domains_lower)
                # --- !! END CHECK !! ---
                if count > 3 and not is_already_filtered:
                    domain_display_safe = html.escape(domain_raw)
                    description_text = f"You've received {count} emails from `{domain_display_safe}`. Would you like to add a filter?"
                    title_text = f"Filter emails from @{domain_display_safe}"
                    rationale_text = (f"The domain '@{domain_display_safe}' accounts for {count} of your recent emails. "
                                    f"Filtering can help manage emails from this source, for example, by automatically labeling or archiving them. "
                                    f"This domain is not currently in your filtered domains list.")
                    logging.info(f"Generating domain_filter suggestion for '{domain_raw}' (not already filtered).")
                    return {
                        "type": "domain_filter",
                        "title": title_text,
                        "description": description_text,
                        "action": "create_domain_filter",
                        "action_params": {"domain": domain_raw},
                        "priority": "medium",
                        "rationale": rationale_text
                    }
                elif is_already_filtered:
                     logging.debug(f"Skipping domain_filter suggestion for '{domain_raw}' (already filtered).")
        return None

    def _generate_action_request_suggestion(self, email_df, insights, user_preferences):
        if not insights or 'action_emails_count' not in insights:
            return None
        action_count = insights['action_emails_count']
        if action_count > 0:
            rationale_text = (f"My analysis indicates {action_count} email(s) likely contain action requests or tasks. "
                              f"Summarizing these can help you quickly identify what needs to be done.")
            return {
                "type": "pending_actions",
                "title": f"Review {action_count} pending action item(s)", # More specific title
                "description": f"You have {action_count} email(s) that seem to require action. Want a summary?",
                "action": "summarize_action_items",
                "action_params": {"count": action_count},
                "priority": "high",
                "rationale": rationale_text # ADDED RATIONALE
            }
        return None



    def handle_dismiss_suggestion(self, suggestion_type):
        """Handles specifically dismissing a suggestion type for the session."""
        if not suggestion_type:
            logging.warning("Attempted to dismiss suggestion with no type.")
            return

        logging.info(f"Dismissing suggestion type: {suggestion_type}")
        # --- Log state BEFORE update ---
        current_dismissed = st.session_state.get("dismissed_suggestions", set())
        logging.debug(f"Dismiss Handler: State BEFORE add: {current_dismissed}")
        # --- End log ---

        # Ensure dismissed_suggestions exists and is a set
        if "dismissed_suggestions" not in st.session_state or not isinstance(st.session_state.dismissed_suggestions, set):
            st.session_state.dismissed_suggestions = set()

        st.session_state.dismissed_suggestions.add(suggestion_type)
        shown_suggestion_ids = st.session_state.get("shown_suggestion_ids", {})
        suggestion_id = shown_suggestion_ids.get(suggestion_type)

        if suggestion_id:
            self.suggestion_history.update_suggestion_response(suggestion_id, was_accepted=False)
            logging.debug(f"Recorded dismissal in suggestion history for ID: {suggestion_id}")
        else:
            logging.warning(f"Could not find suggestion ID for dismissed type: {suggestion_type}")
        # --- Log state AFTER update ---
        new_dismissed = st.session_state.get("dismissed_suggestions", set())
        logging.debug(f"Dismiss Handler: State AFTER add: {new_dismissed}")
        # --- End log ---

        # Optionally record the dismissal in memory
        if self.memory:
             self.memory.record_suggestion_response(suggestion_type, False)

        st.success(f"Suggestion type '{suggestion_type.replace('_',' ').title()}' dismissed for this session.")
        # time.sleep(0.5) # Removed sleep
        st.rerun() 

    def _generate_question_suggestion(self, email_df, insights, user_preferences):
        if not insights or 'question_emails_count' not in insights:
            return None
        question_count = insights['question_emails_count']
        if question_count > 0:
            rationale_text = (f"My analysis found {question_count} email(s) that likely contain direct questions. "
                              f"Reviewing these can help ensure you address all inquiries.")
            return {
                "type": "unanswered_questions",
                "title": f"Review {question_count} email(s) with questions", # More specific
                "description": f"You have {question_count} email(s) with questions. Want to review them?",
                "action": "summarize_questions",
                "action_params": {"count": question_count},
                "priority": "high",
                "rationale": rationale_text # ADDED RATIONALE
            }
        return None

    def _generate_high_priority_suggestion(self, email_df, insights, user_preferences):
        if not email_df.empty:
            high_priority_df = email_df[email_df['Agent Priority'].isin(['CRITICAL', 'HIGH'])] # Renamed for clarity
            count_high_priority = len(high_priority_df)
            if count_high_priority > 0:
                rationale_text = (f"There are {count_high_priority} email(s) classified as CRITICAL or HIGH priority. "
                                  f"Reviewing summaries of these can help you address the most important items first.")
                return {
                    "type": "high_priority",
                    "title": f"Summarize {count_high_priority} high priority email(s)", # More specific title
                    "description": f"You have {count_high_priority} high priority emails. Want me to summarize them?",
                    "action": "summarize_high_priority",
                    "action_params": {"count": count_high_priority},
                    "priority": "critical",
                    "rationale": rationale_text # ADDED RATIONALE
                }
        return None

    def _generate_time_management_suggestion(self, email_df, insights, user_preferences):
        if not insights or 'hour_distribution' not in insights:
            return None
        hour_distribution = insights.get('hour_distribution', {})
        if not hour_distribution: return None
        peak_hours = sorted(hour_distribution.items(), key=lambda x: x[1], reverse=True)[:2]
        if not peak_hours: return None

        peak_hour_1, count_1 = peak_hours[0]
        time_range_display = f"{peak_hour_1:02d}:00 - {peak_hour_1+1:02d}:00" # Ensure leading zero for hour

        if len(peak_hours) > 1:
            peak_hour_2, count_2 = peak_hours[1]
            time_range_display = f"{peak_hour_1:02d}:00 - {peak_hour_1+1:02d}:00 and {peak_hour_2:02d}:00 - {peak_hour_2+1:02d}:00"

        rationale_text = (f"Analysis of your email arrival times shows peak activity around {time_range_display}. "
                          f"Scheduling dedicated blocks during or after these times can improve focus and efficiency.")
        return {
            "type": "time_management",
            "title": "Optimize Email Checking Schedule",
            "description": f"Most of your emails arrive around {time_range_display}. Want to schedule dedicated email checking times?",
            "action": "schedule_email_time",
            "action_params": {"peak_hours": [h for h, _ in peak_hours]},
            "priority": "medium",
            "rationale": rationale_text # ADDED RATIONALE
        }


    def _generate_recurring_meeting_suggestion(self, email_df, insights, user_preferences):
        if not insights or 'meeting_emails_count' not in insights:
            return None
        meeting_count = insights.get('meeting_emails_count', 0)
        if meeting_count > 2: # Only suggest if there are several meeting invites
            rationale_text = (f"You've received {meeting_count} meeting invitations recently. "
                              f"I can help you list them, and if your calendar is connected, assist with scheduling or drafting responses.")
            return {
                "type": "recurring_meeting", # Type name might be a bit misleading, more like "manage meeting invites"
                "title": f"Manage {meeting_count} Meeting Invites",
                "description": f"You have {meeting_count} meeting invites. Would you like me to help organize or respond to them?",
                "action": "manage_meetings",
                "action_params": {"count": meeting_count},
                "priority": "medium",
                "rationale": rationale_text # ADDED RATIONALE
            }
        return None

    def _generate_scheduled_send_suggestion(self, email_df, insights, user_preferences):
        hour = datetime.now().hour
        if 9 <= hour <= 17: # Only suggest during typical work hours
            rationale_text = ("Sending emails at optimal times can increase their visibility and likelihood of a prompt response. "
                              "This feature allows you to compose emails when convenient and have them sent later.")
            return {
                "type": "scheduled_send",
                "title": "Consider Scheduled Email Sending",
                "description": "Would you like to draft emails now but schedule them to send at optimal times (e.g., recipient's morning)?",
                "action": "scheduled_send_setup", # This action would explain how to use the feature
                "action_params": {},
                "priority": "low",
                "rationale": rationale_text # ADDED RATIONALE
            }
        return None

    def _generate_email_cleanup_suggestion(self, email_df, insights, user_preferences):
        total_emails = len(email_df) if not email_df.empty else 0
        rationale_text = "No specific rationale for general cleanup suggestion if no low-priority emails are found." # Default

        if total_emails > 10:
            low_priority_count = email_df[email_df['Agent Priority'] == 'LOW'].shape[0] if not email_df.empty else 0

            if low_priority_count > MAX_EMAILS_TO_ARCHIVE // 2 :
                rationale_text = (f"You have {low_priority_count} emails classified as LOW priority. "
                                  f"Archiving these can help declutter your inbox. I can queue up to {MAX_EMAILS_TO_ARCHIVE} for archiving.")
                return {
                    "type": "email_cleanup",
                    "title": f"Archive {low_priority_count} low priority email(s)",
                    "description": f"You have {low_priority_count} low priority emails. Want me to help you archive them?",
                    "action": "cleanup_inbox",
                    "action_params": {"count": low_priority_count, "max_to_archive": MAX_EMAILS_TO_ARCHIVE},
                    "priority": "low",
                    "rationale": rationale_text
                }
            # Fallback if no low priority emails found but total > 10 (for "organize_inbox")
            elif total_emails > 20: # Make this condition a bit stricter for general organization
                rationale_text = (f"Your inbox has over {total_emails} processed emails. "
                                  f"Exploring filters or labels could help manage this volume more effectively.")
                return {
                    "type": "email_cleanup", # Re-use type, but different action
                    "title": "Explore Email Organization",
                    "description": "Would you like me to suggest ways to better organize your inbox (e.g., filters for frequent senders, labels for projects)?",
                    "action": "organize_inbox",
                    "action_params": {},
                    "priority": "low",
                    "rationale": rationale_text # ADDED RATIONALE
                }
        return None

    def _generate_priority_summary_suggestion(self, email_df, insights, user_preferences):
        daily_summary_enabled = False
        if self.memory:
            prefs = self.memory.get_user_preferences()
            daily_summary_enabled = prefs.get("agent_preferences", {}).get("daily_summary_enabled", False)

        if not daily_summary_enabled:
            rationale_text = ("A daily summary can provide a quick overview of your most important emails at the start of your day, "
                              "helping you prioritize tasks without needing to manually scan your entire inbox.")
            return {
                "type": "priority_summary",
                "title": "Enable Daily Priority Summaries",
                "description": "Would you like to receive a daily summary of your high priority emails each morning?",
                "action": "setup_daily_summary",
                "action_params": {},
                "priority": "low",
                "rationale": rationale_text # ADDED RATIONALE
            }
        return None

    def _generate_follow_up_suggestion(self, email_df, insights, user_preferences):
        # This suggestion is more about enabling a feature.
        # The actual check for follow-ups happens when the action is processed or autonomously.
        if not self.gmail_service: # Check if Gmail service is available
            logging.debug("Follow-up suggestion skipped: Gmail service not available to ProactiveAgent.")
            return None

        # Check if follow-up feature is already configured/enabled by user
        follow_up_enabled = self.memory.user_profile.get("autonomous_settings", {}).get("follow_up", {}).get("enabled", False)
        if follow_up_enabled:
            logging.debug("Follow-up suggestion skipped: Feature already enabled by user.")
            return None

        rationale_text = ("It's easy to lose track of emails awaiting replies. "
                          "I can help by periodically checking your sent items and alerting you to messages that haven't received a response after a few days.")
        return {
            "type": "follow_up",
            "title": "Enable Follow-up Reminders",
            "description": "Would you like me to help you follow up on sent emails that haven't received responses?",
            "action": "setup_follow_up", # This action will guide user or present current findings
            "action_params": {},
            "priority": "medium", # Changed from high, as it's more of a feature setup
            "rationale": rationale_text
        }

    def render_suggestion_card(self, suggestion, key_prefix):
        title = suggestion.get('title', 'Suggestion')
        description = suggestion.get('description', '')
        suggestion_type = suggestion.get('type', 'unknown')
        action_verb = suggestion.get('action', 'proceed')
        rationale = suggestion.get('rationale', "No specific rationale provided for this suggestion.") # Get rationale

        action_button_labels = {
            "create_sender_rule": "Create Rule", "create_domain_filter": "Add Filter",
            "summarize_action_items": "Summarize Actions", "summarize_questions": "Review Questions",
            "summarize_high_priority": "Summarize Priority", "schedule_email_time": "Schedule Time",
            "manage_meetings": "Organize Meetings", "scheduled_send_setup": "Setup Send Times",
            "cleanup_inbox": "Archive Low Prio", "organize_inbox": "Suggest Organization",
            "setup_daily_summary": "Enable Daily Summary", "setup_follow_up": "Setup Follow-ups"
        }
        yes_button_text = f"✅ {action_button_labels.get(action_verb, 'Yes, proceed')}"
        priority = suggestion.get('priority', self._get_default_priority(suggestion_type))
        
        # Unique keys
        card_id = f"card_{key_prefix}_{suggestion_type}_{hash(title)}" # More specific key
        yes_key = f"yes_{key_prefix}_{action_verb}_{hash(str(suggestion.get('action_params', {})))}"
        dismiss_key = f"dismiss_{key_prefix}_{suggestion_type}_{hash(title)}"
        popover_key = f"popover_{key_prefix}_{suggestion_type}_{hash(title)}"


        priority_colors = {
            'critical': ERROR_COLOR, 'high': WARNING_COLOR, # Using constants from ui_app
            'medium': PRIMARY_COLOR, 'low': MUTED_COLOR
        }
        border_color = priority_colors.get(priority, PRIMARY_COLOR)

        # Card Header with Title and Info Popover
        cols_header = st.columns([0.9, 0.1]) # Adjust ratio as needed
        with cols_header[0]:
            st.markdown(f"""
            <h3 style="color: {border_color}; margin-top: 0; margin-bottom: 0.1rem; font-size: 1.20rem; font-weight: 600;">
                <span style="display: inline-block; width: 8px; height: 8px; border-radius: 50%; margin-right: 8px; background-color: {border_color}; vertical-align: middle;"></span>
                {html.escape(title)}
            </h3>
            """, unsafe_allow_html=True)
        with cols_header[1]:
            # Using st.popover for the rationale
            with st.popover("Why?", help="Click to see why this suggestion is made.", use_container_width=False): # Temporarily removed key
                st.markdown(f"**Rationale for '{html.escape(title)}':**")
                st.markdown(html.escape(rationale))


        # Card Body (Description)
        st.markdown(f"""
        <div id="{card_id}" class="suggestion-card priority-{priority}" style="
            background-color: {border_color}1A; 
            border-left: 5px solid {border_color}; 
            border-radius: 10px; 
            padding: 0.75rem 1.25rem 1.25rem 1.25rem; /* Adjusted padding */
            margin-bottom: 1.25rem; 
            box-shadow: 0 4px 8px rgba(0, 0, 0, 0.2);
            animation: fadeIn 0.5s;
            margin-top: -10px; /* Pulls it slightly under the header */
            position: relative; /* For z-index if needed, though popover handles it */
            z-index: 1; /* Ensure card content is below popover */
            ">
            <p style="color: #e0e0e0; margin-bottom: 15px; line-height: 1.5; font-size: 0.95rem;">{html.escape(description)}</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Action Buttons (outside the styled div, but associated with the card)
        col_actions_1, col_actions_2 = st.columns([1,1])
        with col_actions_1:
            if st.button(
                yes_button_text, key=yes_key,
                on_click=self.handle_suggestion_action,
                args=(suggestion_type, suggestion.get('action'), suggestion.get('action_params', {}), True),
                use_container_width=True
            ):
                pass
        with col_actions_2:
            if st.button(
                "❌ Dismiss", key=dismiss_key,
                on_click=self.handle_dismiss_suggestion,
                args=(suggestion_type,),
                use_container_width=True
            ):
                pass
        st.markdown("---") # Separator after each card

    def _get_default_priority(self, suggestion_type):
        """
        Determine default priority level based on suggestion type

        Args:
            suggestion_type: String type identifier for the suggestion

        Returns:
            String priority level: 'critical', 'high', 'medium', or 'low'
        """
        # Map suggestion types to priority levels
        priority_mapping = {
            # Critical priority suggestions
            'high_priority': 'critical',

            # High priority suggestions
            'pending_actions': 'high',
            'unanswered_questions': 'high',
            'follow_up': 'high',

            # Medium priority suggestions
            'sender_rule': 'medium',
            'domain_filter': 'medium',
            'recurring_meeting': 'medium',
            'time_management': 'medium',

            # Low priority suggestions
            'email_cleanup': 'low',
            'scheduled_send': 'low',
            'priority_summary': 'low',
            'organize_inbox': 'low' # Added organize_inbox
        }

        # Return mapped priority or default to medium
        return priority_mapping.get(suggestion_type, 'medium')


    def handle_suggestion_action(self, suggestion_type, action, params, was_accepted):
        """Handles the action when a suggestion is accepted or dismissed"""
        # Store the action in session state for processing ONLY if accepted
        if was_accepted:
            logging.info(f"Suggestion accepted: Type={suggestion_type}, Action={action}, Params={params}") # Log type too
            st.session_state.suggested_action = {
                "action": action,
                "params": params
                # Optionally store suggestion_type if needed later:
                # "type": suggestion_type
            }
            # Find the suggestion ID using the type
            shown_suggestion_ids = st.session_state.get("shown_suggestion_ids", {})
            suggestion_id = shown_suggestion_ids.get(suggestion_type) # Lookup by type

            if suggestion_id:
                self.suggestion_history.update_suggestion_response(suggestion_id, was_accepted=True)
                logging.debug(f"Recorded acceptance in suggestion history for ID: {suggestion_id}")
            else:
                # This might happen if state was cleared or suggestion wasn't rendered correctly
                logging.warning(f"Could not find suggestion ID for accepted type: {suggestion_type}")

            # Record acceptance in memory (using type is fine here)
            if self.memory:
               self.memory.record_suggestion_response(suggestion_type, True)

            st.success(f"Processing request...")
            # time.sleep(0.5) # Removed sleep
            st.rerun()

    def should_show_suggestion_type(self, suggestion_type, cooldown_days=7):
        """Determine if a suggestion type should be shown based on history"""
        # Get recent history for this type
        type_history = self.suggestion_history.get_type_history(suggestion_type, limit=5)

        for record in type_history:
            # If it was recently dismissed, check the cooldown period
            if record.get('was_accepted') is False:
                timestamp = record.get('timestamp')
                if timestamp:
                    # Convert to datetime if needed
                    if not isinstance(timestamp, datetime):
                        try:
                            # Attempt parsing assuming it might be Firestore Timestamp or ISO string
                            if hasattr(timestamp, 'ToDatetime'): # Check if it's a Firestore Timestamp
                                timestamp = timestamp.ToDatetime()
                            else:
                                timestamp = datetime.fromisoformat(str(timestamp).replace('Z', '+00:00'))
                        except (ValueError, TypeError, AttributeError):
                            logging.warning(f"Could not parse timestamp {timestamp} for suggestion history check.")
                            continue # Skip this record if timestamp is unparseable

                    # Ensure timestamp is timezone-aware (assume UTC if naive)
                    if timestamp.tzinfo is None:
                        timestamp = timestamp.replace(tzinfo=timezone.utc)

                    # Check if within cooldown period
                    days_ago = (datetime.now(timezone.utc) - timestamp).days
                    if days_ago < cooldown_days:
                        # Still in cooldown period, don't show
                        logging.debug(f"Suggestion type '{suggestion_type}' skipped due to recent dismissal ({days_ago} days ago).")
                        return False

        # No recent dismissals found, ok to show
        return True

    def get_suggestion_type_score(self, suggestion_type, recency_days_tier1=7, recency_days_tier2=30):
        """
        Calculate a relevance score for a suggestion type based on history,
        incorporating recency and overall acceptance rate.
        """
        if not self.suggestion_history:
            return 0.5 # Neutral score if no history module

        # Get overall stats for this suggestion type
        stats = self.suggestion_history.get_stats(days_back=90) # Analyze last 90 days for overall rate
        type_specific_stats = stats.get('by_type', {}).get(suggestion_type, {})
        
        overall_shown = type_specific_stats.get('shown', 0)
        overall_accepted = type_specific_stats.get('accepted', 0)

        if overall_shown > 0:
            base_acceptance_rate = overall_accepted / overall_shown
        else:
            base_acceptance_rate = 0.5  # Neutral score for types with no interaction history

        # Recency weighting: Check recent interactions
        recent_history = self.suggestion_history.get_type_history(suggestion_type, limit=10)
        recency_boost = 0.0
        
        if recent_history:
            # Simple recency: boost if last interaction was positive, penalize if negative
            last_interaction = recent_history[0] # Most recent
            if last_interaction.get('was_accepted') is True:
                recency_boost = 0.15
            elif last_interaction.get('was_accepted') is False:
                recency_boost = -0.15

            # More detailed recency: average acceptance in last N days
            # (This part can be expanded if needed)
            # For now, the simple boost/penalty on the last interaction is a good start.

        # Combine base rate with recency boost
        # Ensure score stays within 0-1 range
        final_score = min(max(base_acceptance_rate + recency_boost, 0.0), 1.0)
        
        logging.debug(f"Score for '{suggestion_type}': BaseRate={base_acceptance_rate:.2f}, RecencyBoost={recency_boost:.2f}, FinalScore={final_score:.2f}")
        return final_score



    def display_proactive_suggestions(self, suggestions): # Accepts the list
        """Display proactive suggestions - With history tracking"""
        logging.debug("--- Entered display_proactive_suggestions ---")
        st.caption("✓ Enhanced suggestions active")
        # 1. Check if the provided list is valid
        if suggestions is None or len(suggestions) == 0: # Corrected check
            logging.debug("display_proactive_suggestions: Received empty suggestions list.")
            # Displaying info here might be redundant if ui_app handles it
            # st.info("No suggestions available.")
            return # Exit if no suggestions were passed

        # 2. Display Header (only if there are suggestions to potentially show)
        st.subheader("📊 Proactive Suggestions")

        # 3. Filtering based on CURRENT session state
        active_suggestions = []
        dismissed_ui_count = 0
        try:
            # Get the set dismissed *in this session*
            dismissed_state_value = st.session_state.get("dismissed_suggestions", set())
            # Optional Debug Display:
            # st.warning(f"DEBUG UI: Dismissed Set = {dismissed_state_value}")

            dismissed_set_for_filtering = set()
            if isinstance(dismissed_state_value, set):
                dismissed_set_for_filtering = {str(item).lower() for item in dismissed_state_value if isinstance(item, str)}

            logging.debug(f"Filtering {len(suggestions)} provided suggestions against dismissed set: {dismissed_set_for_filtering}")

            # Filter the PROVIDED list
            for s in suggestions: # Iterate the passed list 'suggestions'
                s_type = s.get("type") if isinstance(s, dict) else None
                s_type_lower = str(s_type).lower() if s_type else None
                # Treat suggestions without a type as invalid/dismissed
                is_dismissed = s_type_lower in dismissed_set_for_filtering if s_type_lower else True

                # logging.debug(f"Filtering: Sug Type='{s_type_lower}', Dismissed={is_dismissed}") # Keep if needed
                if not is_dismissed:
                    active_suggestions.append(s) # Append 's'

            original_suggestion_count = len(suggestions)
            dismissed_ui_count = original_suggestion_count - len(active_suggestions)
            logging.debug(f"Filtering complete. Active count: {len(active_suggestions)}")

        except Exception as e_filt:
             st.error(f"Error during suggestion filtering: {e_filt}")
             logging.error(f"Error filtering suggestions: {e_filt}", exc_info=True)
             active_suggestions = [] # Ensure list is empty on error
        # --- End Filtering ---

        # 4. Display Dismissed Count
        if dismissed_ui_count > 0:
            st.caption(f"({dismissed_ui_count} suggestions dismissed this session. Reset in Settings.)")
        # --- End Display Count ---

        # 5. Render Active Suggestion Cards
        suggestion_ids = {} # Initialize dict to store IDs for this display cycle
        if not active_suggestions:
             st.info("No active suggestions to display.") # Show message if filtering removed all
        else:
             logging.debug(f"Rendering {len(active_suggestions)} active suggestion cards.")
             for i, suggestion in enumerate(active_suggestions):
                 try:
                     # Call the agent's card rendering method
                     self.render_suggestion_card(suggestion, f"sugg_{i}")
                     # Record each displayed suggestion and store its ID
                     suggestion_id = self.suggestion_history.record_suggestion(suggestion, was_shown=True)
                     suggestion_type = suggestion.get('type')
                     if suggestion_type and suggestion_id:
                         suggestion_ids[suggestion_type] = suggestion_id
                     elif suggestion_type:
                         logging.warning(f"Failed to record suggestion ID for type: {suggestion_type}")

                 except Exception as e_render:
                     st.error(f"Error rendering suggestion card {i}: {e_render}")
                     logging.error(f"Error rendering card {i} (data: {suggestion}): {e_render}", exc_info=True)
        # --- End Rendering ---

        # Store IDs in session state for response tracking
        st.session_state["shown_suggestion_ids"] = suggestion_ids

    def process_suggestion_action(self, action_data):
        """
        Process an accepted suggestion action, generate response text, and update memory.
        Handles Google Calendar integration for schedule_email_time.

        Args:
            action_data: Dictionary with action details {'action': ..., 'params': ...}

        Returns:
            tuple: (response_text, was_handled, download_data)
        """
        if not action_data:
            return None, False, None

        action = action_data.get("action")
        params = action_data.get("params", {})
        response_text = ""
        was_handled = False
        download_data = None # Keep this for potential future use

        # --- Ensure dependencies are available ---
        if not self.db:
            logging.error(f"Cannot process action '{action}': Firestore client (self.db) is not available.")
            return "Sorry, I can't access the database right now to process that action.", False, None
        if not self.llm_client:
             logging.error(f"Cannot process action '{action}': LLM client (self.llm_client) is not available.")
             return "Sorry, I can't access the language model right now to process that action.", False, None
        if not self.config:
             logging.error(f"Cannot process action '{action}': Config (self.config) is not available.")
             return "Sorry, I'm missing some configuration needed to process that action.", False, None
        # --- End Dependency Check ---

        try: # Wrap processing in a try block
            # Handle different action types
            if action == "create_sender_rule":
                # ... (existing logic as before) ...
                sender_raw = params.get('sender', '')
                if sender_raw:
                    sender_display_name = sender_raw # Default
                    email_part = _extract_email_address(sender_raw)
                    name_match = re.match(r'^\s*"?([^"<]+)"?\s*<.*?>\s*$', sender_raw)
                    if name_match: sender_display_name = name_match.group(1).strip()
                    elif email_part and email_part != sender_raw:
                         potential_name = sender_raw.split('<')[0].strip()
                         if potential_name: sender_display_name = potential_name
                         else: sender_display_name = email_part
                    elif email_part: sender_display_name = email_part
                    sender_display_safe = html.escape(sender_display_name)

                    response_text = f"I've added `{sender_display_safe}` to your important senders list. Future emails from this sender will be marked as CRITICAL priority."
                    if self.memory:
                        prefs = self.memory.get_user_preferences()
                        important_senders = prefs.get("email_preferences", {}).get("important_senders", [])
                        if sender_raw not in important_senders:
                            important_senders.append(sender_raw)
                            self.memory.update_email_preferences("important_senders", important_senders)
                            logging.info(f"Memory updated: Added important sender '{sender_raw}'")
                        else:
                             logging.info(f"Sender '{sender_raw}' already in important senders list.")
                    was_handled = True
                else:
                    response_text = "Could not process sender rule: Sender information missing."



            elif action == "create_domain_filter":
                domain_raw = params.get('domain', '')
                if domain_raw:
                    domain_display_safe = html.escape(domain_raw)
                    response_text = f"I've created a filter for the domain `{domain_display_safe}`. You can customize it further in the Settings tab."
                    if self.memory:
                        prefs = self.memory.get_user_preferences()
                        filtered_domains = prefs.get("email_preferences", {}).get("filtered_domains", [])
                        domain_entry = f"@{domain_raw}" if not domain_raw.startswith("@") else domain_raw
                        if domain_entry not in filtered_domains:
                            filtered_domains.append(domain_entry)
                            self.memory.update_email_preferences("filtered_domains", filtered_domains)
                            logging.info(f"Memory updated: Added filtered domain '{domain_entry}'")
                        else:
                            logging.info(f"Domain '{domain_entry}' already in filtered domains list.")
                    was_handled = True
                else:
                    response_text = "Could not process domain filter: Domain information missing."

            # --- NEW: Summarization Action Handlers ---
            elif action in ["summarize_action_items", "summarize_questions", "summarize_high_priority"]:
                logging.info(f"Processing summarization action: {action}")
                emails_to_summarize = []
                query_description = ""

                # 1. Determine query based on action type
                query = self.db.collection(EMAILS_COLLECTION)
                if action == "summarize_action_items":
                    query = query.where(filter=FieldFilter('llm_purpose', '==', 'Action Request'))
                    query_description = "emails requiring action"
                elif action == "summarize_questions":
                    query = query.where(filter=FieldFilter('llm_purpose', '==', 'Question'))
                    query_description = "emails containing questions"
                elif action == "summarize_high_priority":
                    query = query.where(filter=FieldFilter('priority', 'in', [PRIORITY_CRITICAL, PRIORITY_HIGH]))
                    query_description = "high priority emails"

                # Order by most recent and limit
                query = query.order_by('processed_timestamp', direction=firestore.Query.DESCENDING).limit(MAX_EMAILS_TO_SUMMARIZE)

                # 2. Fetch emails from Firestore
                try:
                    results = query.stream()
                    for doc in results:
                        email_data = doc.to_dict()
                        email_data['id'] = doc.id # Add ID back
                        # Basic validation: ensure body_text exists
                        if email_data.get('body_text'):
                             emails_to_summarize.append(email_data)
                        else:
                             logging.warning(f"Skipping email {doc.id} for summarization due to missing body_text.")
                    logging.info(f"Fetched {len(emails_to_summarize)} emails for '{action}'.")
                except Exception as e_fetch:
                    logging.error(f"Firestore error fetching emails for '{action}': {e_fetch}", exc_info=True)
                    response_text = f"Sorry, I had trouble fetching the {query_description} from the database."
                    # Keep was_handled=False as the core action failed
                    return response_text, False, None # Return early on fetch error

                # 3. Summarize fetched emails
                if emails_to_summarize:
                    summaries = []
                    response_text = f"Okay, here are summaries for the latest {len(emails_to_summarize)} {query_description}:\n\n---\n"
                    for email_data in emails_to_summarize:
                        email_id = email_data.get('id', 'Unknown ID')
                        subject = email_data.get('subject', '[No Subject]')
                        sender = email_data.get('sender', '[No Sender]')
                        logging.debug(f"Summarizing email {email_id} for action '{action}'...")

                        # Call the summarization function from agent_logic
                        summary = summarize_email_with_memory(
                            llm_client=self.llm_client,
                            email_data=email_data,
                            config=self.config,
                            memory=self.memory,
                            summary_type="action_focused" if action == "summarize_action_items" else "standard" # Choose summary type
                        )

                        # Format the output
                        sender_display = sender # USE RAW
                        subject_display = subject # USE RAW
                        summary_display = summary # USE RAW
                        
                        summaries.append(
                            f"**Email from:** `{sender_display}`\n"  # Markdown will handle special chars within backticks
                            f"**Subject:** `{subject_display}` (ID: {email_id})\n"
                            f"**Summary:**\n{summary_display}\n" # Let st.markdown handle the summary content
                        )

                    response_text += "\n---\n\n".join(summaries) # Join summaries with separators
                    response_text += "\n---"
                    was_handled = True
                else:
                    response_text = f"I didn't find any recent {query_description} to summarize right now."
                    was_handled = True # Handled the request, even if no results

            # --- *** REPLACE THE cleanup_inbox PLACEHOLDER WITH THIS: *** ---
            elif action == "cleanup_inbox":
                logging.info(f"Processing suggestion action: {action}")
                emails_to_archive_ids = []
                try:
                    # Query Firestore for low priority emails, limit the result
                    query = self.db.collection(EMAILS_COLLECTION)\
                              .where(filter=FieldFilter('priority', '==', PRIORITY_LOW))\
                              .limit(MAX_EMAILS_TO_ARCHIVE) # Limit the query

                    results = query.stream()
                    for doc in results:
                        emails_to_archive_ids.append(doc.id)
                    logging.info(f"Found {len(emails_to_archive_ids)} low-priority emails to request archiving for.")

                except Exception as e_fetch:
                    logging.error(f"Firestore error fetching low-priority emails for cleanup: {e_fetch}", exc_info=True)
                    response_text = "Sorry, I had trouble fetching the emails for cleanup."
                    # Return early on fetch error, action not fully handled
                    return response_text, False, None

                # Request archiving for each found email
                submitted_count = 0
                failed_count = 0
                if emails_to_archive_ids:
                    for email_id in emails_to_archive_ids:
                        # Use the imported function from database_utils
                        if database_utils.request_email_action(email_id, "archive"):
                            submitted_count += 1
                        else:
                            failed_count += 1
                            logging.warning(f"Failed to submit archive request for email {email_id}")

                    # Format response based on submission results
                    if submitted_count > 0 and failed_count == 0:
                        response_text = f"Okay, I've submitted requests to archive {submitted_count} low-priority emails. The backend will process these shortly."
                    elif submitted_count > 0 and failed_count > 0:
                        response_text = f"Okay, I've submitted requests to archive {submitted_count} low-priority emails, but failed to submit requests for {failed_count} others. The backend will process the submitted ones."
                    elif submitted_count == 0 and failed_count > 0:
                        response_text = f"Sorry, I failed to submit archive requests for {failed_count} low-priority emails due to an error."
                    else: # Should not happen if list wasn't empty, but handle defensively
                         response_text = "I found low-priority emails but encountered an issue submitting archive requests."
                else:
                    # No low-priority emails found
                    response_text = "I didn't find any low-priority emails matching the criteria for cleanup right now."

                # Mark as handled because we processed the suggestion, even if 0 emails were archived
                was_handled = True
            # --- *** END OF REPLACEMENT for cleanup_inbox *** ---

            # --- Keep other placeholders ---
            elif action == "schedule_email_time":
                logging.info(f"Processing suggestion action: {action}")
                peak_hours = params.get("peak_hours", [])

                # --- DEFINE Variables needed for this action HERE ---
                gcs_client_instance = None
                gcs_bucket_for_token = None
                credentials_path_local = None
                try:
                    # Initialize GCS client specifically for this action if needed
                    gcs_client_instance = storage.Client()
                    # Get bucket name from environment variable
                    gcs_bucket_for_token = os.environ.get('GCS_BUCKET_NAME')
                    # Get credentials path from the agent's config
                    # Use the corrected self.config (no trailing comma from init)
                    if self.config and 'gmail' in self.config and 'credentials_path' in self.config['gmail']:
                         credentials_path_local = self.config['gmail']['credentials_path']
                    else:
                         logging.error("Could not retrieve credentials path from agent config.")
                         # Set to None if path is missing in config

                    if not gcs_bucket_for_token:
                         logging.error("GCS_BUCKET_NAME environment variable not set.")
                         # Set to None if env var is missing

                except Exception as e_setup:
                    logging.error(f"Error setting up GCS/Config for calendar action: {e_setup}", exc_info=True)
                    # Ensure variables are None if setup fails
                    gcs_client_instance = None
                    gcs_bucket_for_token = None
                    credentials_path_local = None
                # --- END Variable Definitions ---

                if not peak_hours or not isinstance(peak_hours, list):
                    response_text = "Okay, I understand you're interested in scheduling email time, but I couldn't retrieve the specific peak hours."
                    was_handled = True
                # Check if required variables were successfully obtained
                elif not gcs_client_instance or not gcs_bucket_for_token or not credentials_path_local:
                     response_text = "Okay, I noted your peak times, but I'm missing some configuration needed to access Google Calendar (GCS Bucket Name or Credentials Path not found)."
                     # Log specific missing items if possible
                     logging.error(f"Missing components for calendar action: GCS Client={bool(gcs_client_instance)}, Bucket={gcs_bucket_for_token}, Creds Path={credentials_path_local}")
                     was_handled = True
                else:
                    # 1. Try to get authenticated calendar service (pass the obtained variables)
                    calendar_service = get_calendar_service(
                        storage_client_instance=gcs_client_instance,
                        token_gcs_bucket=gcs_bucket_for_token,
                        credentials_path=credentials_path_local
                    )

                    if not calendar_service:
                        # User needs to authorize first
                        response_text = (
                            "Okay, I've noted your peak email times. To schedule reminders automatically, "
                            "I need access to your Google Calendar. Please go to the 'Settings' tab and click "
                            "'Connect Google Calendar' to grant permission."
                        )
                        was_handled = True
                    else:
                        # 2. User is authorized, proceed to create events
                        logging.info("Google Calendar authorized. Attempting to create events.")
                        created_count = 0
                        failed_count = 0
                        event_links = []
                        today = datetime.now(timezone.utc).date() # Use timezone-aware

                        for hour in sorted(peak_hours):
                            try:
                                h_int = int(hour)
                                if 0 <= h_int <= 23:
                                    # Use the imported 'time' object here
                                    start_dt = datetime.combine(today, time(hour=h_int, minute=0), tzinfo=timezone.utc)
                                    end_dt = start_dt + timedelta(hours=1)
                                    summary = f"Email Checking Block ({h_int:02d}:00)"
                                    description = "Dedicated time to check and process emails, suggested by Maia."
                                    recurrence = 'RRULE:FREQ=DAILY;INTERVAL=1' # Daily recurrence

                                    created_event = create_calendar_event(
                                        calendar_service,
                                        start_time=start_dt,
                                        end_time=end_dt,
                                        summary=summary,
                                        description=description,
                                        recurrence_rule=recurrence
                                    )
                                    if created_event:
                                        created_count += 1
                                        if created_event.get('htmlLink'):
                                            event_links.append(created_event.get('htmlLink'))
                                    else:
                                        failed_count += 1
                                else:
                                    logging.warning(f"Invalid hour value '{h_int}' skipped.")
                                    failed_count += 1 # Count as failure if value is out of range
                            except (ValueError, TypeError) as e_conv:
                                logging.warning(f"Invalid hour format '{hour}' skipped during conversion or time creation: {e_conv}")
                                failed_count += 1 # Count as failure if format is wrong

                        # 3. Format response based on success/failure
                        if created_count > 0 and failed_count == 0:
                            response_text = f"Success! I've scheduled {created_count} recurring daily reminder(s) in your primary Google Calendar for your peak email times."
                            if event_links:
                                response_text += f"\nYou can view the first event here: {event_links[0]}"
                        elif created_count > 0 and failed_count > 0:
                            response_text = f"Okay, I scheduled {created_count} reminder(s) in your Google Calendar, but failed to create {failed_count} others (check logs for details)."
                        elif failed_count > 0 and created_count == 0:
                            response_text = "Sorry, I tried to schedule the reminders in your Google Calendar, but encountered an error for all suggested times. Please check the application logs."
                        else: # Should not happen if valid_hours existed
                            response_text = "I attempted to schedule reminders, but something unexpected happened."

                        was_handled = True
                        # Optional: Update memory profile
                        if self.memory:
                            logging.info(f"Noted user preference and attempted calendar scheduling for hours: {peak_hours}")

            # --- NEW: Follow-up Action Handler ---
            elif action == "setup_follow_up":
                logging.info(f"Processing suggestion action: {action}")
                follow_up_candidates = []
                days_to_check = 7 # How far back to look for sent emails
                reply_wait_days = 3 # Minimum days to wait before suggesting follow-up

                if not self.gmail_service:
                    response_text = "Sorry, I need access to Gmail to check for follow-ups, but the connection isn't available."
                    return response_text, False, None

                try:
                    # 1. Get recent sent emails
                    sent_messages = list_sent_emails(self.gmail_service, days_ago=days_to_check, max_results=50)

                    if not sent_messages:
                        response_text = f"I checked your sent emails from the last {days_to_check} days but didn't find any candidates needing follow-up right now."
                        was_handled = True
                    else:
                        logging.info(f"Checking {len(sent_messages)} sent emails for replies...")
                        processed_threads = set() # Avoid checking the same thread multiple times
                        follow_up_needed_count = 0
                        max_to_list = 5 # Limit how many we show

                        for message_info in sent_messages:
                            thread_id = message_info.get('threadId')
                            message_id = message_info.get('id')

                            if not thread_id or not message_id or thread_id in processed_threads:
                                continue # Skip if missing info or thread already checked

                            processed_threads.add(thread_id)

                            # 2. Check if thread has replies after this message
                            has_reply = check_thread_for_reply(self.gmail_service, thread_id, message_id)

                            if not has_reply:
                                # 3. Fetch original message details to check date and get subject/recipient
                                try:
                                    msg_details = get_email_details(self.gmail_service, message_id)
                                    if msg_details:
                                        parsed = parse_email_content(msg_details)
                                        sent_date_str = parsed.get('date')
                                        # Attempt to parse date and check threshold
                                        try:
                                            # Gmail date format often like: 'Wed, 1 May 2024 10:15:30 +0000 (UTC)'
                                            # Need robust parsing
                                            sent_dt = None
                                            # Try common formats
                                            fmts = ["%a, %d %b %Y %H:%M:%S %z", "%a, %d %b %Y %H:%M:%S %Z"]
                                            for fmt in fmts:
                                                try:
                                                    # Strip potential timezone name in brackets like (UTC)
                                                    date_part = re.sub(r'\s*\([^)]*\)\s*$', '', sent_date_str)
                                                    sent_dt = datetime.strptime(date_part, fmt)
                                                    break # Stop if parsed
                                                except ValueError:
                                                    continue
                                            # Fallback if specific formats fail
                                            if sent_dt is None:
                                                from dateutil import parser # Use dateutil for more flexibility
                                                sent_dt = parser.parse(sent_date_str)

                                            # Ensure timezone aware for comparison
                                            if sent_dt.tzinfo is None:
                                                sent_dt = sent_dt.replace(tzinfo=timezone.utc) # Assume UTC if naive

                                            if (datetime.now(timezone.utc) - sent_dt).days >= reply_wait_days:
                                                # Add to candidates if no reply and old enough
                                                if follow_up_needed_count < max_to_list:
                                                    recipient = next((h['value'] for h in msg_details['payload']['headers'] if h['name'].lower() == 'to'), '[No Recipient]')
                                                    follow_up_candidates.append({
                                                        'id': message_id,
                                                        'subject': parsed.get('subject', '[No Subject]'),
                                                        'recipient': recipient
                                                    })
                                                follow_up_needed_count += 1

                                        except Exception as date_e:
                                             logging.warning(f"Could not parse date '{sent_date_str}' for message {message_id}: {date_e}")

                                except Exception as detail_e:
                                     logging.warning(f"Could not get details for sent message {message_id}: {detail_e}")

                        # 4. Format response
                        if follow_up_candidates:
                            response_text = f"Okay, I found {follow_up_needed_count} sent email(s) from the last {days_to_check} days that haven't received a reply after {reply_wait_days} days. Here are the most recent {len(follow_up_candidates)}:\n\n---\n"
                            for i, email in enumerate(follow_up_candidates, 1):
                                subject_display = html.escape((email['subject'][:60] + '...') if len(email['subject']) > 63 else email['subject'])
                                recipient_display = html.escape((email['recipient'][:40] + '...') if len(email['recipient']) > 43 else email['recipient'])
                                response_text += f"\n{i}. To: {recipient_display} - Subject: '{subject_display}' (ID: `{email['id']}`)"
                            response_text += f"\n\n---\n\nWould you like me to help draft a follow-up for any of these?"
                            # context_object = {"hint": "follow_up_list", "data": {"ids": [e['id'] for e in follow_up_candidates]}} # Store IDs for context - Handled in UI
                        else:
                            response_text = f"I checked your recent sent emails, but didn't find any older than {reply_wait_days} days needing a follow-up right now."

                        was_handled = True

                except Exception as e:
                    logging.error(f"Error during follow-up check logic: {e}", exc_info=True)
                    response_text = "Sorry, I encountered an error while checking for emails needing follow-up."
                    was_handled = False # Indicate failure

                return response_text, was_handled, None

            # --- *** NEW: Implement manage_meetings *** ---
            elif action == "manage_meetings":
                logging.info(f"Processing suggestion action: {action}")
                meeting_invites = []
                try:
                    # Query Firestore for meeting invites
                    query = self.db.collection(EMAILS_COLLECTION)\
                              .where(filter=FieldFilter('llm_purpose', '==', 'Meeting Invite'))\
                              .order_by('processed_timestamp', direction=firestore.Query.DESCENDING)\
                              .limit(MAX_MEETINGS_TO_LIST)

                    results = query.stream()
                    for doc in results:
                        email_data = doc.to_dict()
                        meeting_invites.append({
                            'id': doc.id,
                            'subject': email_data.get('subject', '[No Subject]'),
                            'sender': email_data.get('sender', '[No Sender]'),
                            'priority': email_data.get('priority', 'MEDIUM')
                        })
                    logging.info(f"Found {len(meeting_invites)} recent meeting invites.")

                except Exception as e_fetch:
                    logging.error(f"Firestore error fetching meeting invites: {e_fetch}", exc_info=True)
                    response_text = "Sorry, I had trouble fetching recent meeting invites."
                    return response_text, False, None

                if meeting_invites:
                    response_text = f"Okay, here are the latest {len(meeting_invites)} meeting invites I found:\n\n---\n"
                    for i, invite in enumerate(meeting_invites, 1):
                        sender_display = html.escape((invite['sender'][:30] + '...') if len(invite['sender']) > 33 else invite['sender'])
                        subject_display = html.escape((invite['subject'][:50] + '...') if len(invite['subject']) > 53 else invite['subject'])
                        response_text += f"\n{i}. **{subject_display}** (From: {sender_display}, Priority: {invite['priority']}, ID: `{invite['id']}`)"
                    response_text += "\n\n---\n\nI can help you draft accept/decline responses or add these to your calendar if you've connected it in Settings."
                    # Future: Add buttons or context for specific actions on these invites
                else:
                    response_text = "I didn't find any recent meeting invites in your processed emails."

                was_handled = True

            # --- *** NEW: Implement scheduled_send_setup *** ---
            elif action == "scheduled_send_setup":
                logging.info(f"Processing suggestion action: {action}")
                response_text = (
                    "Okay, I can help with scheduling emails! When you're drafting a reply using my help, "
                    "just tell me when you want it sent (e.g., 'schedule this for tomorrow at 9 AM', 'send this evening'). "
                    "I'll confirm the time before scheduling."
                )
                # Note: Actual scheduling logic would be part of the drafting process, not here.
                was_handled = True

            # --- *** NEW: Implement organize_inbox *** ---
            elif action == "organize_inbox":
                logging.info(f"Processing suggestion action: {action}")
                # Provide general advice or link to existing suggestions
                response_text = (
                    "Organizing your inbox can save time! Here are a few ideas:\n"
                    "*   **Filters:** Automatically label or archive emails from frequent senders (like newsletters or notifications). I can help set these up if you accept the 'Create rule' or 'Filter domain' suggestions.\n"
                    "*   **Labels:** Use labels to categorize emails by project, topic, or urgency.\n"
                    "*   **Archiving:** Regularly archive emails you've dealt with to keep your main inbox clean. I can help with the 'Inbox cleanup' suggestion.\n\n"
                    "Would you like me to look for specific opportunities, like frequent senders without filters?"
                )
                # Future: Could add a query here to find candidates for filtering/labeling
                was_handled = True

            # --- *** NEW: Implement setup_daily_summary *** ---
            elif action == "setup_daily_summary":
                logging.info(f"Processing suggestion action: {action}")
                preference_saved = False
                if self.memory:
                    try:
                        # Update a preference in the user's profile via AgentMemory
                        # Using a nested structure under agent_preferences
                        update_result = self.memory.save_profile_updates({"agent_preferences.daily_summary_enabled": True})
                        if update_result:
                            preference_saved = True
                            logging.info("User preference for daily summary saved via AgentMemory.")
                        else:
                            logging.error("Failed to save daily summary preference via AgentMemory.")
                    except Exception as e_pref:
                        logging.error(f"Error saving daily summary preference: {e_pref}", exc_info=True)

                if preference_saved:
                    response_text = (
                        "Great! I've noted that you'd like a daily summary of high-priority emails. "
                        "I'll aim to provide this each morning. You can manage this preference in the Settings tab."
                    )
                else:
                    response_text = (
                        "Okay, I understand you want daily summaries. However, I had trouble saving this preference right now. "
                        "Please try again later or check the application logs."
                    )
                # Note: Actual generation/delivery requires a separate scheduled backend process.
                was_handled = True

            # --- Final Else for Unknown/Default ---
            else:
                action_display = action.replace("_", " ").title() if action else "the requested action"
                response_text = f"Okay, proceeding with '{action_display}'. (Note: Full implementation for this action might be pending)."
                logging.warning(f"Action '{action}' default handler used (confirmation text only).")
                was_handled = bool(action) # Mark as handled if action name exists

        except Exception as e:
             # Main exception handling for the whole processing block
             logging.error(f"Error processing suggestion action '{action}': {e}", exc_info=True)
             response_text = f"Sorry, I encountered an error while trying to process the action: {action}. Error: {e}"
             # *** FIX HERE: Ensure was_handled is False and return 3 values ***
             was_handled = False # Indicate failure
             return response_text, was_handled, None # Return None for download_data
             # *** END FIX ***

        # Return the final response and handled status (this is the normal exit path)
        return response_text, was_handled, download_data

    def generate_autonomous_suggestion(self, email_df, context=None):
        """
        Generate a single autonomous suggestion based on context

        This is intended for proactive suggestions when not directly requested
        by the user, e.g., at the start of a session or after period of inactivity

        Args:
            email_df: DataFrame with email data
            context: Optional context dict

        Returns:
            dict: A suggestion dict or None
        """
        # Check if we should make an autonomous suggestion
        if self.memory and not self.memory.should_suggest_proactively():
            return None

        insights = self.analyze_email_patterns(email_df)
        if not insights:
            return None

        # Check for high priority issues first
        if insights.get('priority_distribution', {}).get('CRITICAL', 0) > 0:
            return self._generate_high_priority_suggestion(email_df, insights, None)

        if insights.get('action_emails_count', 0) > 2:
            return self._generate_action_request_suggestion(email_df, insights, None)

        # If no urgent issues, pick a random suggestion type
        suggestion_types = list(self.suggestion_types.keys())
        random.shuffle(suggestion_types)

        for suggestion_type in suggestion_types:
            # --- Check if suggestion type should be shown ---
            if not self.should_show_suggestion_type(suggestion_type):
                continue # Skip if recently dismissed

            generator_func = self.suggestion_types.get(suggestion_type)
            if generator_func: # Check if function exists
                suggestion = generator_func(email_df, insights, None)
                if suggestion:
                    return suggestion

        return None