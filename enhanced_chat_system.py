# -*- coding: utf-8 -*-
"""
Enhanced Chat System for Maia Email Agent
Provides rich, dynamic conversational capabilities beyond basic intent classification
"""

import json
import logging
import re
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
import pandas as pd

logger = logging.getLogger(__name__)

class EnhancedChatSystem:
    """
    Enhanced conversational AI system that provides:
    1. Dynamic context awareness
    2. Multi-turn conversations
    3. Rich response generation
    4. Email-specific intelligence
    5. Natural language understanding
    """
    
    def __init__(self, llm_manager, db_client, config):
        self.llm_manager = llm_manager
        self.db_client = db_client
        self.config = config
        self.conversation_history = {}  # In-memory cache
        self.conversations_collection = 'conversations'  # Firestore collection for persistence
        
        # Optimized system prompt for enhanced conversational AI
        self.system_prompt = """You are Maia, a warm and intelligent email management assistant who genuinely cares about helping users stay organized and productive.

🎯 **YOUR PERSONALITY:**
• Conversational and friendly (never robotic or cold)
• Proactive in offering helpful insights and suggestions
• Empathetic to the challenges of email management
• Detail-oriented but concise in responses
• Confident in your capabilities while being humble

📧 **CORE CAPABILITIES:**
1. **Email Intelligence**
   - Provide insightful summaries and analysis
   - Identify patterns, trends, and urgent items
   - Explain email classifications with clear reasoning
   - Find specific emails using natural language queries

2. **Proactive Assistance**
   - Suggest actionable next steps
   - Recommend organization strategies
   - Identify follow-up opportunities
   - Offer workflow improvements

3. **Conversational Excellence**
   - Remember and build on conversation history
   - Ask thoughtful clarifying questions
   - Provide context-aware responses
   - Adapt to user communication preferences

💬 **RESPONSE GUIDELINES:**
• Use natural, conversational language (avoid corporate speak)
• Reference specific email data when relevant
• Build on previous conversation points naturally
• Offer concrete, actionable suggestions
• Ask follow-up questions to be more helpful
• Keep responses focused and valuable (under 250 words typically)

🚫 **NEVER:**
• Sound robotic or use template-like responses
• Mention AI/ML technical details unless specifically asked
• Give vague or generic advice
• Overwhelm with too much information at once
• Ignore the conversation context

✅ **ALWAYS:**
• Sound genuinely helpful and engaged
• Provide specific insights based on actual email data
• Offer clear next steps when appropriate
• Maintain conversation flow naturally
• Show understanding of the user's email management challenges"""

    def process_message(self, user_id: str, message: str, conversation_context: Dict = None) -> Dict[str, Any]:
        """
        Process a chat message with enhanced conversational capabilities and robust error handling
        """
        # Validate inputs
        if not user_id or not message or not message.strip():
            return self._create_error_response("Invalid input provided", "validation_error")
        
        # Check message length to prevent abuse
        if len(message) > 4000:
            return self._create_error_response("Message too long. Please keep messages under 4000 characters.", "message_too_long")
        
        try:
            # Load conversation history with retry mechanism
            conversation_history = self._load_conversation_history(user_id)
            
            # Add user message to history
            user_message = {
                'role': 'user',
                'content': message.strip(),
                'timestamp': datetime.now().isoformat()
            }
            conversation_history.append(user_message)
            
            # Update in-memory cache
            self.conversation_history[user_id] = conversation_history
            
            # Persist user message with error handling
            self._save_message_to_db(user_id, user_message)
            
            # Get user's email context with fallback
            email_context = self._get_email_context(user_id)
            
            # Build conversation prompt with context
            conversation_prompt = self._build_conversation_prompt(
                user_id, message, email_context, conversation_context
            )
            
            # Generate response using LLM with retry and fallback
            response = self._generate_response_with_retry(conversation_prompt, message)
            
            # Add assistant response to history
            assistant_message = {
                'role': 'assistant',
                'content': response,
                'timestamp': datetime.now().isoformat()
            }
            self.conversation_history[user_id].append(assistant_message)
            
            # Persist assistant message with error handling
            self._save_message_to_db(user_id, assistant_message)
            
            # Extract any actions or follow-ups from the response
            actions = self._extract_actions_from_response(response, message)
            
            # Determine if this conversation should continue
            follow_up = self._should_follow_up(response, message)
            
            return {
                'response': response,
                'intent': 'conversational',
                'entities': self._extract_entities_from_conversation(message, response),
                'actions': actions,
                'follow_up': follow_up,
                'conversation_id': f"conv_{user_id}_{len(self.conversation_history[user_id])}",
                'status': 'success'
            }
            
        except Exception as e:
            logger.error(f"Error in enhanced chat processing: {e}", exc_info=True)
            return self._create_comprehensive_fallback_response(message, str(e))

    def _get_email_context(self, user_id: str) -> Dict[str, Any]:
        """
        Get comprehensive and COMPLETE email context for the user - ensuring chat has full data access
        """
        try:
            logger.info(f"Getting comprehensive email context for user: {user_id}")
            
            # Get ALL emails for this user (no limit to ensure completeness)
            emails_ref = self.db_client.collection('emails')
            all_emails_query = emails_ref.where('user_id', '==', user_id)
            
            # Get all emails without limit to ensure we have complete data
            all_emails = list(all_emails_query.stream())
            logger.info(f"Retrieved {len(all_emails)} total emails from Firestore")
            
            if not all_emails:
                logger.warning(f"No emails found for user {user_id}")
                return {'total_emails': 0, 'summary': 'No emails found in database'}
            
            # Convert to detailed email data for analysis
            email_data = []
            high_priority_emails = []
            recent_emails = []
            
            for doc in all_emails:
                data = doc.to_dict()
                data['doc_id'] = doc.id
                email_data.append(data)
                
                # Collect high priority emails with full details
                priority = data.get('priority', '').upper()
                if priority in ['HIGH', 'CRITICAL']:
                    high_priority_emails.append({
                        'id': doc.id,
                        'subject': data.get('subject', 'No Subject'),
                        'sender': data.get('sender', 'Unknown'),
                        'priority': priority,
                        'purpose': data.get('purpose') or data.get('llm_purpose', 'Unknown'),
                        'received_date': data.get('received_date', ''),
                        'summary': data.get('summary', ''),
                        'is_read': data.get('is_read', True)
                    })
                
                # Collect recent emails (last 7 days)
                received_date = data.get('received_date')
                if received_date:
                    try:
                        from datetime import datetime, timedelta
                        if isinstance(received_date, str):
                            email_date = datetime.fromisoformat(received_date.replace('Z', '+00:00'))
                        else:
                            email_date = received_date
                        
                        if email_date >= datetime.now().replace(tzinfo=email_date.tzinfo) - timedelta(days=7):
                            recent_emails.append({
                                'subject': data.get('subject', 'No Subject'),
                                'sender': data.get('sender', 'Unknown'),
                                'priority': priority,
                                'purpose': data.get('purpose') or data.get('llm_purpose', 'Unknown'),
                                'received_date': received_date
                            })
                    except Exception as date_error:
                        logger.warning(f"Date parsing error for email {doc.id}: {date_error}")
            
            df = pd.DataFrame(email_data)
            logger.info(f"Created DataFrame with {len(df)} emails for analysis")
            
            # Ensure we have accurate priority counts
            priority_breakdown = {}
            if 'priority' in df.columns:
                priority_breakdown = df['priority'].value_counts().to_dict()
            
            # Try both 'purpose' and 'llm_purpose' fields
            email_purposes = {}
            if 'purpose' in df.columns:
                email_purposes = df['purpose'].fillna('Unknown').value_counts().to_dict()
            elif 'llm_purpose' in df.columns:
                email_purposes = df['llm_purpose'].fillna('Unknown').value_counts().to_dict()
            
            # Generate comprehensive context with REAL email details
            context = {
                'total_emails': len(df),
                'unread_count': len(df[df.get('is_read', True) == False]) if 'is_read' in df.columns else 0,
                'priority_breakdown': priority_breakdown,
                'recent_senders': df['sender'].value_counts().head(15).to_dict() if 'sender' in df.columns else {},
                'date_range': {
                    'oldest': df['processed_timestamp'].min() if 'processed_timestamp' in df.columns else None,
                    'newest': df['processed_timestamp'].max() if 'processed_timestamp' in df.columns else None
                },
                'common_subjects': self._extract_common_subjects(df),
                'email_purposes': email_purposes,
                
                # CRITICAL: Include actual email details for chat to reference
                'high_priority_emails': high_priority_emails[:20],  # Top 20 high priority with details
                'recent_emails': recent_emails[:15],  # Recent emails with details
                'total_high_priority': len(high_priority_emails),
                'total_critical': len([e for e in high_priority_emails if e['priority'] == 'CRITICAL']),
                
                # Enhanced context for rich interactions
                'security_alerts': self._count_security_emails(df),
                'meeting_requests': self._count_meeting_emails(df),
                'newsletter_count': self._count_newsletter_emails(df),
                'action_required_count': self._count_action_required_emails(df),
                'top_domains': self._get_top_email_domains(df),
                'time_insights': self._get_time_based_insights(df),
                
                # Add meeting-specific email details
                'meeting_emails': self._extract_meeting_emails(df),
                'urgent_emails': self._extract_urgent_emails(df),
                
                'data_freshness': datetime.now().isoformat(),
                'query_info': f"Retrieved {len(all_emails)} emails from Firestore without limit"
            }
            
            logger.info(f"Email context generated: {context['total_emails']} total, {context['total_high_priority']} high priority")
            return context
            
        except Exception as e:
            logger.error(f"Error getting email context: {e}", exc_info=True)
            return {'total_emails': 0, 'summary': f'Error retrieving email data: {str(e)}', 'error': str(e)}

    def _build_conversation_prompt(self, user_id: str, message: str, email_context: Dict, conversation_context: Dict = None) -> str:
        """
        Build an optimized conversation prompt with structured context and natural flow
        """
        from optimized_prompts import OptimizedPrompts
        
        # Get recent conversation history
        recent_history = self.conversation_history.get(user_id, [])[-6:]  # Last 3 exchanges
        
        # Use the optimized prompt builder
        prompts = OptimizedPrompts()
        return prompts.get_chat_response_prompt_v2(
            message=message,
            email_context=email_context,
            conversation_history=recent_history
        )

    def _generate_response_with_retry(self, prompt: str, original_message: str, max_retries: int = 3) -> str:
        """
        Generate a conversational response with retry mechanism and intelligent fallbacks
        """
        last_error = None
        
        for attempt in range(max_retries):
            try:
                # Choose optimal LLM for conversation
                provider, client = self.llm_manager.choose_optimal_llm('conversation', len(prompt))
                
                if provider.startswith('gpt') and client:
                    response_obj = client.chat.completions.create(
                        model="gpt-4",
                        messages=[
                            {"role": "system", "content": self.system_prompt},
                            {"role": "user", "content": prompt}
                        ],
                        max_tokens=800,
                        temperature=0.7,
                        timeout=30  # 30 second timeout
                    )
                    response = response_obj.choices[0].message.content
                    if response and len(response.strip()) > 10:  # Ensure meaningful response
                        return response
                    else:
                        raise ValueError("Response too short or empty")
                        
                elif provider.startswith('claude') and client:
                    response_obj = client.messages.create(
                        model="claude-3-haiku-20240307",
                        max_tokens=800,
                        temperature=0.7,
                        system=self.system_prompt,
                        messages=[{"role": "user", "content": prompt}]
                    )
                    response = response_obj.content[0].text
                    if response and len(response.strip()) > 10:
                        return response
                    else:
                        raise ValueError("Response too short or empty")
                else:
                    raise ValueError("No available LLM provider")
                    
            except Exception as e:
                last_error = e
                logger.warning(f"LLM attempt {attempt + 1} failed: {e}")
                
                # Try different approach on retry
                if attempt < max_retries - 1:
                    # Simplify prompt for retry
                    prompt = self._create_simplified_prompt(original_message)
                    continue
        
        # All retries failed, use rule-based fallback
        logger.error(f"All LLM attempts failed. Last error: {last_error}")
        return self._generate_rule_based_response(original_message)
    
    def _generate_rule_based_response(self, message: str) -> str:
        """
        Generate a response using simple rules when LLM is unavailable
        """
        message_lower = message.lower()
        
        # Basic pattern matching for common requests
        if any(word in message_lower for word in ['summary', 'summarize']):
            return "I'd like to provide you with an email summary, but I'm experiencing technical difficulties with my AI analysis. You can check your recent emails manually, and I'll try to provide a detailed summary once my systems are back online."
        
        elif any(word in message_lower for word in ['urgent', 'priority', 'important']):
            return "I can't access my priority analysis right now, but I recommend checking your most recent emails for anything time-sensitive. Look for emails from known contacts or with urgent keywords in the subject line."
        
        elif any(word in message_lower for word in ['organize', 'filter', 'archive']):
            return "I'm having trouble with my organization features at the moment. You can manually sort your emails by date, sender, or subject while I recover. I'll be able to provide automated organization suggestions once I'm back online."
        
        elif any(word in message_lower for word in ['hi', 'hello', 'hey']):
            return "Hello! I'm Maia, your email assistant. I'm experiencing some technical difficulties right now, but I'm still here to help. You can try asking me simple questions about your emails, and I'll do my best to assist you."
        
        elif any(word in message_lower for word in ['help', 'what can you do']):
            return "I'm your email management assistant, though I'm running in limited mode right now. Normally I can summarize emails, find important messages, suggest organization strategies, and provide email insights. Please try again shortly for full functionality."
        
        else:
            return "I'm having some technical difficulties and can't fully process your request right now. I'm an email management assistant that normally helps with summaries, organization, and email insights. Please try rephrasing your question or ask again shortly."
    
    def _create_simplified_prompt(self, message: str) -> str:
        """
        Create a simpler prompt for retry attempts
        """
        return f"""You are Maia, an email assistant. The user said: "{message}"
        
Respond helpfully and conversationally. Keep it simple and direct. If you can't fully answer, explain what you'd normally do and suggest they try again.
        
User message: {message}"""

    def _extract_actions_from_response(self, response: str, user_message: str) -> List[Dict]:
        """
        Extract actionable items and generate rich quick actions from the conversation
        """
        actions = []
        response_lower = response.lower()
        user_lower = user_message.lower()
        
        # Email management actions
        if any(word in response_lower for word in ['high priority', 'urgent', 'important']):
            actions.append({
                'type': 'view_high_priority',
                'label': 'View High Priority Emails',
                'icon': '🔴',
                'description': 'Show all high priority emails',
                'data': {'filter': 'priority:high'}
            })
        
        if any(word in response_lower for word in ['summary', 'summarize']):
            actions.append({
                'type': 'detailed_summary',
                'label': 'Get Detailed Summary',
                'icon': '📊',
                'description': 'Get comprehensive email analysis',
                'data': {'action': 'detailed_analysis'}
            })
        
        if any(word in response_lower for word in ['organize', 'filter', 'archive']):
            actions.append({
                'type': 'organize_inbox',
                'label': 'Organize Inbox',
                'icon': '📁',
                'description': 'Set up email organization',
                'data': {'action': 'organize'}
            })
        
        # Follow-up actions based on content
        if any(word in response_lower for word in ['meeting', 'calendar', 'schedule']):
            actions.append({
                'type': 'calendar_integration',
                'label': 'Check Calendar',
                'icon': '📅',
                'description': 'View related calendar events',
                'data': {'action': 'calendar'}
            })
        
        # Smart contextual actions
        if 'linkedin' in response_lower:
            actions.append({
                'type': 'filter_linkedin',
                'label': 'Filter LinkedIn Emails',
                'icon': '💼',
                'description': 'Manage LinkedIn notifications',
                'data': {'filter': 'sender:linkedin.com'}
            })
        
        if any(word in response_lower for word in ['security', 'alert', 'warning']):
            actions.append({
                'type': 'security_review',
                'label': 'Review Security',
                'icon': '🔒',
                'description': 'Check security-related emails',
                'data': {'filter': 'security:true'}
            })
        
        # Always include helpful follow-up actions
        actions.extend([
            {
                'type': 'ask_followup',
                'label': 'Tell me more',
                'icon': '💡',
                'description': 'Get additional insights',
                'data': {'action': 'expand'}
            },
            {
                'type': 'new_topic',
                'label': 'Ask something else',
                'icon': '❓',
                'description': 'Start a new topic',
                'data': {'action': 'new_topic'}
            }
        ])
        
        return actions[:4]  # Return max 4 actions to avoid UI clutter

    def _should_follow_up(self, response: str, user_message: str) -> bool:
        """
        Determine if the conversation should continue with follow-up questions
        """
        # Check if response contains questions or suggestions for continuation
        follow_up_indicators = [
            '?', 'would you like', 'should i', 'do you want', 
            'let me know', 'what about', 'anything else'
        ]
        
        return any(indicator in response.lower() for indicator in follow_up_indicators)

    def _extract_entities_from_conversation(self, message: str, response: str) -> Dict:
        """
        Extract entities from the conversational context
        """
        entities = {}
        
        # Extract time references
        time_patterns = {
            'today': r'\btoday\b',
            'yesterday': r'\byesterday\b',
            'this_week': r'\bthis week\b',
            'last_week': r'\blast week\b'
        }
        
        for time_ref, pattern in time_patterns.items():
            if re.search(pattern, message.lower()):
                entities['time_reference'] = time_ref
        
        # Extract priority mentions
        priority_patterns = {
            'high': r'\b(high|urgent|important|critical)\b',
            'low': r'\b(low|unimportant|spam)\b'
        }
        
        for priority, pattern in priority_patterns.items():
            if re.search(pattern, message.lower()):
                entities['priority_filter'] = priority
        
        # Extract sender mentions
        sender_match = re.search(r'from\s+([a-zA-Z0-9@.\-]+)', message.lower())
        if sender_match:
            entities['sender_filter'] = sender_match.group(1)
        
        return entities

    def _extract_common_subjects(self, df: pd.DataFrame) -> List[str]:
        """
        Extract common subject patterns from emails
        """
        if 'subject' not in df.columns:
            return []
        
        # Simple keyword extraction from subjects
        subjects = df['subject'].dropna().str.lower()
        common_words = []
        
        for subject in subjects:
            words = re.findall(r'\b\w+\b', subject)
            common_words.extend([w for w in words if len(w) > 3])
        
        # Count word frequency
        word_counts = pd.Series(common_words).value_counts()
        return word_counts.head(10).index.tolist()

    def _get_recent_activity(self, user_id: str) -> Dict:
        """
        Get recent user activity for context
        """
        try:
            # Get recent activities from the activity log
            activities_ref = self.db_client.collection('activities')
            recent_activities = list(activities_ref.where('user_id', '==', user_id)
                                   .order_by('timestamp', direction='DESCENDING')
                                   .limit(10).stream())
            
            activity_types = [doc.to_dict().get('type', 'unknown') for doc in recent_activities]
            return {
                'recent_activities': activity_types,
                'last_activity': recent_activities[0].to_dict().get('timestamp') if recent_activities else None
            }
        except Exception as e:
            logger.error(f"Error getting recent activity: {e}")
            return {}

    def _create_error_response(self, error_message: str, error_type: str) -> Dict[str, Any]:
        """
        Create a standardized error response
        """
        return {
            'response': error_message,
            'intent': 'error',
            'entities': {},
            'actions': [{
                'type': 'retry',
                'label': 'Try again',
                'icon': '🔄',
                'description': 'Try sending your message again',
                'data': {'action': 'retry'}
            }],
            'follow_up': True,
            'status': 'error',
            'error_type': error_type
        }
    
    def _create_comprehensive_fallback_response(self, original_message: str, error_details: str) -> Dict[str, Any]:
        """
        Provide intelligent fallback responses based on the type of failure
        """
        # Try to understand what the user wanted despite the error
        intent_hints = self._guess_user_intent(original_message)
        
        # Provide contextual fallback based on guessed intent
        if 'summary' in intent_hints or 'summarize' in intent_hints:
            fallback_message = "I'm having trouble generating a detailed summary right now, but I can tell you that you have emails in your inbox. Would you like me to try a simpler approach or can you try asking again?"
        elif 'urgent' in intent_hints or 'priority' in intent_hints:
            fallback_message = "I can't access the full priority analysis right now, but I'd recommend checking your most recent emails for anything urgent. Please try your request again."
        elif 'organize' in intent_hints or 'filter' in intent_hints:
            fallback_message = "I'm having trouble with organization features right now. You can manually sort emails by date or sender while I recover. Please try again shortly."
        else:
            fallback_message = "I'm experiencing some technical difficulties and can't provide my full assistance right now. Could you try rephrasing your question? I'm here to help with email management, summaries, and organization."
        
        # Add helpful fallback actions
        actions = [
            {
                'type': 'retry_message',
                'label': 'Try Again',
                'icon': '🔄',
                'description': 'Retry your original message',
                'data': {'action': 'retry', 'original_message': original_message}
            },
            {
                'type': 'simple_request',
                'label': 'Ask Something Simpler',
                'icon': '💡',
                'description': 'Try a basic question like "What emails do I have?"',
                'data': {'action': 'suggest_simple'}
            }
        ]
        
        # Add specific recovery suggestions based on error type
        if 'api' in error_details.lower() or 'llm' in error_details.lower():
            actions.append({
                'type': 'basic_summary',
                'label': 'Basic Email Count',
                'icon': '📊',
                'description': 'Get a simple email count without AI analysis',
                'data': {'action': 'basic_summary'}
            })
        
        return {
            'response': fallback_message,
            'intent': 'fallback',
            'entities': {'original_intent': intent_hints},
            'actions': actions,
            'follow_up': True,
            'status': 'fallback',
            'recovery_suggestions': True
        }

    def clear_conversation_history(self, user_id: str):
        """
        Clear conversation history for a user (both in-memory and database)
        """
        if user_id in self.conversation_history:
            del self.conversation_history[user_id]
        
        # Clear from database
        try:
            conversation_ref = self.db_client.collection(self.conversations_collection).document(user_id)
            conversation_ref.delete()
            logger.info(f"Cleared conversation history for user {user_id}")
        except Exception as e:
            logger.error(f"Error clearing conversation history for user {user_id}: {e}")

    def get_conversation_summary(self, user_id: str) -> str:
        """
        Get a summary of the current conversation
        """
        history = self.conversation_history.get(user_id, [])
        if not history:
            return "No conversation history"
        
        return f"Conversation with {len(history)} messages, started at {history[0]['timestamp']}"

    def _load_conversation_history(self, user_id: str) -> List[Dict]:
        """
        Load conversation history from Firestore
        """
        try:
            conversation_ref = self.db_client.collection(self.conversations_collection).document(user_id)
            conversation_doc = conversation_ref.get()
            
            if conversation_doc.exists:
                data = conversation_doc.to_dict()
                messages = data.get('messages', [])
                
                # Only load recent messages (last 20) to avoid memory issues
                recent_messages = messages[-20:] if len(messages) > 20 else messages
                logger.info(f"Loaded {len(recent_messages)} conversation messages for user {user_id}")
                return recent_messages
            else:
                logger.info(f"No existing conversation history for user {user_id}")
                return []
                
        except Exception as e:
            logger.error(f"Error loading conversation history for user {user_id}: {e}")
            return []

    def _save_message_to_db(self, user_id: str, message: Dict):
        """
        Persist a single message to Firestore
        """
        try:
            conversation_ref = self.db_client.collection(self.conversations_collection).document(user_id)
            
            # Get existing conversation or create new one
            conversation_doc = conversation_ref.get()
            if conversation_doc.exists:
                data = conversation_doc.to_dict()
                messages = data.get('messages', [])
            else:
                messages = []
                data = {
                    'user_id': user_id,
                    'created_at': datetime.now(),
                    'last_updated': datetime.now()
                }
            
            # Add new message
            messages.append(message)
            
            # Keep only last 50 messages in database to prevent bloat
            if len(messages) > 50:
                messages = messages[-50:]
            
            # Update document
            data.update({
                'messages': messages,
                'last_updated': datetime.now(),
                'message_count': len(messages)
            })
            
            conversation_ref.set(data)
            
        except Exception as e:
            logger.error(f"Error saving message to database for user {user_id}: {e}")

    def _get_conversation_context_summary(self, user_id: str) -> str:
        """
        Generate a brief summary of the conversation context for the LLM
        """
        history = self.conversation_history.get(user_id, [])
        if len(history) < 2:
            return "This is the start of our conversation."
        
        recent_messages = history[-4:]  # Last 2 exchanges
        topics = []
        
        for msg in recent_messages:
            if msg['role'] == 'user':
                # Extract key topics from user messages
                content = msg['content'].lower()
                if 'email' in content:
                    topics.append('email management')
                if any(word in content for word in ['summary', 'summarize']):
                    topics.append('email summaries')
                if any(word in content for word in ['priority', 'urgent', 'important']):
                    topics.append('email priorities')
        
        if topics:
            return f"We've been discussing: {', '.join(set(topics))}"
        else:
            return "We're having an ongoing conversation about your emails."

    def _count_security_emails(self, df: pd.DataFrame) -> int:
        """Count emails related to security"""
        if df.empty or 'subject' not in df.columns:
            return 0
        
        security_keywords = ['security', 'alert', 'warning', 'suspicious', 'unauthorized', 'breach', 'verification']
        security_count = 0
        
        for subject in df['subject'].fillna('').str.lower():
            if any(keyword in subject for keyword in security_keywords):
                security_count += 1
                
        return security_count

    def _count_meeting_emails(self, df: pd.DataFrame) -> int:
        """Count emails related to meetings"""
        if df.empty or 'subject' not in df.columns:
            return 0
        
        meeting_keywords = ['meeting', 'call', 'zoom', 'teams', 'conference', 'appointment', 'schedule']
        meeting_count = 0
        
        for subject in df['subject'].fillna('').str.lower():
            if any(keyword in subject for keyword in meeting_keywords):
                meeting_count += 1
                
        return meeting_count

    def _count_newsletter_emails(self, df: pd.DataFrame) -> int:
        """Count newsletter/promotional emails"""
        if df.empty or 'sender' not in df.columns:
            return 0
        
        newsletter_keywords = ['newsletter', 'noreply', 'no-reply', 'marketing', 'promo', 'unsubscribe']
        newsletter_count = 0
        
        for sender in df['sender'].fillna('').str.lower():
            if any(keyword in sender for keyword in newsletter_keywords):
                newsletter_count += 1
                
        return newsletter_count

    def _count_action_required_emails(self, df: pd.DataFrame) -> int:
        """Count emails that require action"""
        if df.empty:
            return 0
        
        # Use existing purpose classification if available
        if 'llm_purpose' in df.columns:
            action_purposes = ['action_required', 'meeting', 'task', 'urgent']
            return len(df[df['llm_purpose'].fillna('').str.lower().isin(action_purposes)])
        
        # Fallback to subject analysis
        action_keywords = ['action required', 'please', 'request', 'urgent', 'asap', 'deadline']
        action_count = 0
        
        if 'subject' in df.columns:
            for subject in df['subject'].fillna('').str.lower():
                if any(keyword in subject for keyword in action_keywords):
                    action_count += 1
                    
        return action_count

    def _get_top_email_domains(self, df: pd.DataFrame) -> List[str]:
        """Extract top email domains from senders"""
        if df.empty or 'sender' not in df.columns:
            return []
        
        domains = []
        for sender in df['sender'].fillna(''):
            if '@' in sender:
                domain = sender.split('@')[-1].lower()
                domains.append(domain)
        
        # Count domain frequency
        domain_counts = pd.Series(domains).value_counts()
        return domain_counts.head(5).index.tolist()

    def _get_time_based_insights(self, df: pd.DataFrame) -> Dict:
        """Generate time-based email insights with error handling"""
        if df.empty or 'processed_timestamp' not in df.columns:
            return {}
        
        try:
            # Convert timestamps if they're not already datetime
            timestamps = pd.to_datetime(df['processed_timestamp'], errors='coerce')
            
            # Filter out invalid timestamps
            valid_timestamps = timestamps.dropna()
            if valid_timestamps.empty:
                return {'status': 'no_valid_timestamps'}
            
            # Get today's emails
            today = datetime.now().date()
            today_emails = len(valid_timestamps[valid_timestamps.dt.date == today])
            
            # Get this week's emails
            week_start = today - timedelta(days=today.weekday())
            week_emails = len(valid_timestamps[valid_timestamps.dt.date >= week_start])
            
            # Calculate average safely
            avg_per_day = round(len(df) / 7, 1) if len(df) > 0 else 0
            
            # Get busiest day safely
            busiest_day = 'Unknown'
            try:
                if not valid_timestamps.empty:
                    day_counts = valid_timestamps.dt.day_name().mode()
                    if not day_counts.empty:
                        busiest_day = day_counts.iloc[0]
            except Exception:
                pass
            
            return {
                'today_count': today_emails,
                'week_count': week_emails,
                'avg_per_day': avg_per_day,
                'busiest_day': busiest_day,
                'total_analyzed': len(valid_timestamps)
            }
        except Exception as e:
            logger.error(f"Error calculating time insights: {e}")
            return {'status': 'error', 'error_message': str(e)[:100]}  # Limit error message length
    
    def _guess_user_intent(self, message: str) -> List[str]:
        """
        Try to guess user intent from their message for better fallback responses
        """
        message_lower = message.lower()
        intents = []
        
        # Email management intents
        if any(word in message_lower for word in ['summary', 'summarize', 'overview']):
            intents.append('summary')
        
        if any(word in message_lower for word in ['urgent', 'priority', 'important', 'critical']):
            intents.append('priority')
        
        if any(word in message_lower for word in ['organize', 'filter', 'sort', 'archive']):
            intents.append('organize')
        
        if any(word in message_lower for word in ['find', 'search', 'look for', 'where']):
            intents.append('search')
        
        if any(word in message_lower for word in ['meeting', 'calendar', 'schedule', 'appointment']):
            intents.append('calendar')
        
        if any(word in message_lower for word in ['help', 'what can you do', 'how']):
            intents.append('help')
        
        # Greeting/social intents
        if any(word in message_lower for word in ['hi', 'hello', 'hey', 'good morning', 'good afternoon']):
            intents.append('greeting')
        
        return intents

    def _extract_meeting_emails(self, df: pd.DataFrame) -> List[Dict]:
        """Extract detailed meeting-related emails"""
        meeting_emails = []
        if df.empty or 'subject' not in df.columns:
            return meeting_emails
        
        meeting_keywords = ['meeting', 'call', 'zoom', 'teams', 'conference', 'appointment', 'schedule', 'calendar']
        
        for _, row in df.iterrows():
            subject = str(row.get('subject', '')).lower()
            if any(keyword in subject for keyword in meeting_keywords):
                meeting_emails.append({
                    'subject': row.get('subject', 'No Subject'),
                    'sender': row.get('sender', 'Unknown'),
                    'priority': row.get('priority', 'Unknown'),
                    'received_date': str(row.get('received_date', '')),
                    'summary': row.get('summary', '')
                })
        
        return meeting_emails[:10]  # Limit to top 10
    
    def _extract_urgent_emails(self, df: pd.DataFrame) -> List[Dict]:
        """Extract detailed urgent emails needing attention"""
        urgent_emails = []
        if df.empty:
            return urgent_emails
        
        # Filter for urgent emails
        urgent_keywords = ['urgent', 'asap', 'emergency', 'critical', 'immediate', 'deadline']
        
        for _, row in df.iterrows():
            subject = str(row.get('subject', '')).lower()
            priority = str(row.get('priority', '')).upper()
            
            is_urgent = (priority in ['HIGH', 'CRITICAL'] or 
                        any(keyword in subject for keyword in urgent_keywords))
            
            if is_urgent:
                urgent_emails.append({
                    'subject': row.get('subject', 'No Subject'),
                    'sender': row.get('sender', 'Unknown'),
                    'priority': priority,
                    'received_date': str(row.get('received_date', '')),
                    'summary': row.get('summary', ''),
                    'is_read': row.get('is_read', True)
                })
        
        return urgent_emails[:15]  # Limit to top 15