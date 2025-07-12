# -*- coding: utf-8 -*-
"""
Real-time Email Processing Integration Module

Bridges the existing email processing pipeline with WebSocket real-time events.
Provides enhanced email processing with live progress updates to the frontend.
"""

import logging
import time
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
import threading

# Import existing email processing components
from agent_logic import (
    get_unread_email_ids, get_email_details, parse_email_content,
    process_email_with_memory, load_config
)
from reasoning_integration import (
    process_email_with_enhanced_reasoning,
    create_proactive_insights,
    get_autonomous_action_recommendations
)
from database_utils import (
    is_email_processed, add_processed_email,
    get_feedback_history, read_user_preferences
)
from agent_memory import AgentMemory
import websocket_events
from auth_utils import get_authenticated_services
import ml_utils

logger = logging.getLogger(__name__)

class RealtimeEmailProcessor:
    """
    Handles real-time email processing with WebSocket event broadcasting.
    Integrates with existing email processing pipeline while providing live updates.
    """
    
    def __init__(self, config: Dict[str, Any], memory: AgentMemory):
        self.config = config
        self.memory = memory
        self.ml_pipeline = None
        self.ml_label_encoder = None
        
    def load_ml_components(self):
        """Load ML pipeline and label encoder if available"""
        try:
            self.ml_pipeline = ml_utils.load_pipeline()
            self.ml_label_encoder = ml_utils.load_label_encoder()
            logger.info("ML components loaded successfully")
        except Exception as e:
            logger.warning(f"Failed to load ML components: {e}")
            
    def process_single_email_realtime(
        self, 
        user_id: str, 
        email_id: str, 
        gmail_service: Any,
        llm_client: Any,
        use_enhanced_reasoning: bool = True
    ) -> Optional[Dict[str, Any]]:
        """
        Process a single email with real-time WebSocket updates.
        
        Args:
            user_id: User identifier for WebSocket room targeting
            email_id: Gmail email ID to process
            gmail_service: Authenticated Gmail service
            llm_client: LLM client for analysis
            use_enhanced_reasoning: Whether to use enhanced reasoning system
            
        Returns:
            Processed email data dictionary or None if failed
        """
        try:
            logger.info(f"Starting real-time processing for email {email_id}, user {user_id}")
            
            # Step 1: Fetch email details
            logger.info("Fetching email details from Gmail...")
            email_details = get_email_details(gmail_service, email_id)
            if not email_details:
                logger.error(f"Failed to fetch email details for {email_id}")
                return None
                
            # Step 2: Parse email content
            logger.info("Parsing email content...")
            parsed_email = parse_email_content(email_details)
            if not parsed_email:
                logger.error(f"Failed to parse email content for {email_id}")
                return None
                
            # Broadcast: Email processing started
            websocket_events.broadcast_email_processing_started(user_id, parsed_email)
            
            # Step 3: Check if already processed
            if is_email_processed(email_id):
                logger.info(f"Email {email_id} already processed, skipping")
                return None
                
            # Step 4: Get user feedback history
            feedback_history = get_feedback_history()
            
            # Step 5: Process email with enhanced reasoning or legacy system
            if use_enhanced_reasoning:
                logger.info("Using enhanced reasoning system...")
                priority, analysis_result, reasoning_result = process_email_with_enhanced_reasoning(
                    parsed_email=parsed_email,
                    llm_client=llm_client,
                    feedback_history=feedback_history,
                    ml_pipeline=self.ml_pipeline,
                    ml_label_encoder=self.ml_label_encoder,
                    config=self.config,
                    memory=self.memory,
                    use_reasoning_engine=True
                )
                
                # Broadcast: LLM analysis complete with reasoning
                if analysis_result:
                    websocket_events.broadcast_llm_analysis_complete(
                        user_id, email_id, analysis_result
                    )
                    
                # Broadcast: Classification complete
                if reasoning_result:
                    classification_data = {
                        'priority': reasoning_result.priority,
                        'confidence': reasoning_result.confidence,
                        'reasoning_steps': len(reasoning_result.reasoning_chain)
                    }
                    websocket_events.broadcast_classification_complete(
                        user_id, email_id, classification_data
                    )
                
                # Create processed_data dict for enhanced reasoning path
                processed_data = {
                    'priority': priority,
                    'analysis': analysis_result,
                    'reasoning': reasoning_result,
                    **parsed_email
                }
                if analysis_result:
                    processed_data.update(analysis_result)
                    
            else:
                logger.info("Using legacy processing system...")
                # Use existing process_email_with_memory function
                processed_data = process_email_with_memory(
                    email_data=parsed_email,
                    llm_client=llm_client,
                    config=self.config,
                    memory=self.memory,
                    feedback_history=feedback_history,
                    ml_pipeline=self.ml_pipeline,
                    ml_label_encoder=self.ml_label_encoder
                )
                
                if processed_data:
                    # Extract analysis results for broadcasting
                    analysis_result = {
                        'purpose': processed_data.get('purpose', 'Unknown'),
                        'priority': processed_data.get('priority', 'MEDIUM'),
                        'urgency': processed_data.get('urgency', 'Medium'),
                        'confidence': processed_data.get('confidence', 0.5),
                        'summary': processed_data.get('summary', '')
                    }
                    
                    # Broadcast: LLM analysis complete
                    websocket_events.broadcast_llm_analysis_complete(
                        user_id, email_id, analysis_result
                    )
                    
                    # Broadcast: Classification complete
                    classification_data = {
                        'priority': processed_data.get('priority', 'MEDIUM'),
                        'confidence': processed_data.get('confidence', 0.5)
                    }
                    websocket_events.broadcast_classification_complete(
                        user_id, email_id, classification_data
                    )
                    
            # Step 6: Generate suggestions
            logger.info("Generating action suggestions...")
            if use_enhanced_reasoning and reasoning_result:
                # Get autonomous action recommendations
                autonomous_actions = get_autonomous_action_recommendations(
                    reasoning_result, processed_data, self.config
                )
                for suggestion in autonomous_actions:
                    websocket_events.broadcast_suggestion_generated(
                        user_id, email_id, suggestion, "autonomous"
                    )
            else:
                # Generate basic suggestions based on processed data
                suggestions = self._generate_basic_suggestions(processed_data)
                for suggestion in suggestions:
                    websocket_events.broadcast_suggestion_generated(
                        user_id, email_id, suggestion, "basic"
                    )
                    
            # Step 7: Save processed email to database
            try:
                # CRITICAL: Add user_id to email data before saving
                email_to_save = (processed_data or parsed_email).copy()
                email_to_save['user_id'] = user_id
                
                # Ensure received_date is available for API queries
                if 'date' in email_to_save and 'received_date' not in email_to_save:
                    email_to_save['received_date'] = email_to_save['date']
                
                add_processed_email(email_to_save)
                logger.info(f"Successfully saved processed email {email_id} for user {user_id}")
            except Exception as e:
                logger.error(f"Failed to save processed email {email_id}: {e}")
                
            # Step 8: Execute autonomous actions if enabled
            user_prefs = read_user_preferences()
            if user_prefs.get('autonomous_mode', {}).get('enabled', False):
                self._execute_autonomous_actions(user_id, email_id, processed_data or parsed_email)
                
            logger.info(f"Successfully completed real-time processing for email {email_id}")
            return processed_data or parsed_email
            
        except Exception as e:
            logger.error(f"Error in real-time email processing for {email_id}: {e}", exc_info=True)
            return None
            
    def process_multiple_emails_realtime(
        self,
        user_id: str,
        gmail_service: Any,
        llm_client: Any,
        max_emails: int = 5,
        use_enhanced_reasoning: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Process multiple unread emails with real-time updates.
        
        Args:
            user_id: User identifier for WebSocket room targeting
            gmail_service: Authenticated Gmail service
            llm_client: LLM client for analysis
            max_emails: Maximum number of emails to process
            use_enhanced_reasoning: Whether to use enhanced reasoning system
            
        Returns:
            List of processed email data dictionaries
        """
        try:
            logger.info(f"Starting batch email processing for user {user_id}, max {max_emails} emails")
            
            # Get unread email IDs
            unread_ids = get_unread_email_ids(gmail_service, max_results=max_emails)
            if not unread_ids:
                logger.info("No unread emails found")
                return []
                
            logger.info(f"Found {len(unread_ids)} unread emails to process")
            
            processed_emails = []
            for i, email_id in enumerate(unread_ids):
                logger.info(f"Processing email {i+1}/{len(unread_ids)}: {email_id}")
                
                processed_email = self.process_single_email_realtime(
                    user_id=user_id,
                    email_id=email_id,
                    gmail_service=gmail_service,
                    llm_client=llm_client,
                    use_enhanced_reasoning=use_enhanced_reasoning
                )
                
                if processed_email:
                    processed_emails.append(processed_email)
                    
                # Small delay between emails to prevent rate limiting
                time.sleep(1)
                
            logger.info(f"Completed batch processing: {len(processed_emails)} emails processed successfully")
            return processed_emails
            
        except Exception as e:
            logger.error(f"Error in batch email processing: {e}", exc_info=True)
            return []
            
    def _generate_basic_suggestions(self, processed_data: Dict[str, Any]) -> List[str]:
        """Generate basic action suggestions based on processed email data"""
        suggestions = []
        
        if not processed_data:
            return suggestions
            
        priority = processed_data.get('priority', 'MEDIUM')
        purpose = processed_data.get('purpose', 'Unknown')
        
        # Priority-based suggestions
        if priority == 'CRITICAL':
            suggestions.append('Respond immediately - marked as critical priority')
        elif priority == 'HIGH':
            suggestions.append('Schedule time to respond today')
        elif priority == 'LOW':
            suggestions.append('Consider archiving if no action needed')
            
        # Purpose-based suggestions
        if purpose == 'Action Request':
            suggestions.append('Add to task list for follow-up')
        elif purpose == 'Meeting Request':
            suggestions.append('Check calendar and respond')
        elif purpose == 'Information':
            suggestions.append('Review and file for reference')
        elif purpose == 'Promotion':
            suggestions.append('Archive or unsubscribe if not relevant')
            
        return suggestions
        
    def _execute_autonomous_actions(self, user_id: str, email_id: str, processed_data: Dict[str, Any]):
        """Execute autonomous actions based on processed email data"""
        try:
            priority = processed_data.get('priority', 'MEDIUM')
            purpose = processed_data.get('purpose', 'Unknown')
            
            # Example autonomous actions
            if purpose == 'Promotion' and priority == 'LOW':
                action = 'Auto-archived promotional email'
                websocket_events.broadcast_autonomous_action_executed(
                    user_id, email_id, 'archive', action
                )
                logger.info(f"Executed autonomous action for {email_id}: {action}")
                
        except Exception as e:
            logger.error(f"Error executing autonomous actions for {email_id}: {e}")


def create_realtime_processor(user_id: str = "default_user") -> RealtimeEmailProcessor:
    """
    Factory function to create a RealtimeEmailProcessor instance.
    
    Args:
        user_id: User identifier for memory system
        
    Returns:
        Configured RealtimeEmailProcessor instance
    """
    try:
        # Load configuration
        config = load_config("config.json")
        if not config:
            raise ValueError("Failed to load configuration")
            
        # Initialize memory system
        from database_utils import get_db
        db = get_db()
        if not db:
            raise ValueError("Failed to initialize database connection")
            
        memory = AgentMemory(db_client=db, user_id=user_id)
        
        # Create processor
        processor = RealtimeEmailProcessor(config, memory)
        processor.load_ml_components()
        
        logger.info(f"Created RealtimeEmailProcessor for user {user_id}")
        return processor
        
    except Exception as e:
        logger.error(f"Failed to create RealtimeEmailProcessor: {e}")
        raise