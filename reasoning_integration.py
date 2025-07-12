# -*- coding: utf-8 -*-
"""
Integration bridge between the new reasoning system and existing email processing pipeline.
Handles backward compatibility while enabling new explainable AI features.
"""

import logging
from typing import List, Dict, Any, Optional, Tuple
from reasoning_engine import ClassificationResult, ExplainableReasoningEngine
import agent_logic

def process_email_with_enhanced_reasoning(
    parsed_email: Dict[str, Any],
    llm_client: Any,
    feedback_history: Dict[str, str],
    ml_pipeline: Any,
    ml_label_encoder: Any,
    config: Dict[str, Any],
    memory: Any = None,
    user_important_senders: list = None,
    use_reasoning_engine: bool = True
) -> Tuple[str, Optional[Dict[str, Any]], Optional[ClassificationResult]]:
    """
    Enhanced email processing that can use either the new reasoning engine or fall back to legacy system.
    
    Args:
        parsed_email: Email data dictionary
        llm_client: LLM client instance
        feedback_history: User feedback mappings
        ml_pipeline: ML model pipeline
        ml_label_encoder: ML label encoder
        config: Configuration dictionary
        memory: Memory system instance
        user_important_senders: List of important senders
        use_reasoning_engine: Whether to use the new reasoning engine
        
    Returns:
        Tuple of (priority_string, analysis_result_dict, reasoning_result)
    """
    
    if use_reasoning_engine:
        try:
            # Use new reasoning engine
            reasoning_result = agent_logic.classify_email_with_reasoning(
                parsed_email=parsed_email,
                llm_client=llm_client,
                feedback_history=feedback_history,
                ml_pipeline=ml_pipeline,
                ml_label_encoder=ml_label_encoder,
                config=config,
                memory=memory,
                user_important_senders=user_important_senders
            )
            
            # Extract analysis from reasoning chain if available
            analysis_result = None
            for step in reasoning_result.reasoning_chain:
                if step.step_type == 'llm_analysis' and step.result:
                    analysis_result = step.result
                    break
            
            # Always ensure we have LLM analysis for purpose detection
            if analysis_result is None:
                logging.info(f"No LLM analysis found in reasoning chain for email {parsed_email.get('id')}, performing explicit analysis...")
                try:
                    analysis_result = agent_logic.analyze_email_with_context(
                        llm_client, parsed_email, config, memory
                    )
                    if analysis_result:
                        logging.info(f"Successfully obtained LLM analysis: purpose={analysis_result.get('purpose')}, urgency={analysis_result.get('urgency_score')}")
                    else:
                        logging.warning(f"LLM analysis returned None for email {parsed_email.get('id')}")
                except Exception as e:
                    logging.error(f"Failed to get LLM analysis for email {parsed_email.get('id')}: {e}", exc_info=True)
                    analysis_result = None
            
            logging.info(f"Enhanced reasoning classification: {reasoning_result.priority} "
                        f"(confidence: {reasoning_result.confidence:.1f}%)")
            
            return reasoning_result.priority, analysis_result, reasoning_result
            
        except Exception as e:
            logging.error(f"Reasoning engine failed, falling back to legacy system: {e}")
            # Fall through to legacy system
    
    # Use legacy classification system
    try:
        priority, analysis_result = agent_logic.classify_and_get_analysis_with_memory(
            parsed_email=parsed_email,
            llm_client=llm_client,
            feedback_history=feedback_history,
            ml_pipeline=ml_pipeline,
            ml_label_encoder=ml_label_encoder,
            config=config,
            memory=memory,
            user_important_senders=user_important_senders
        )
        
        logging.info(f"Legacy classification: {priority}")
        return priority, analysis_result, None
        
    except Exception as e:
        logging.error(f"Both reasoning engine and legacy system failed: {e}")
        # Ultimate fallback
        return "MEDIUM", None, None


def enhance_existing_email_processing():
    """
    Function to gradually migrate existing email processing to use reasoning engine.
    This can be called from main.py to upgrade the classification system.
    """
    
    def enhanced_process_email_with_memory(
        parsed_email, llm_client, feedback_history, ml_pipeline, ml_label_encoder, 
        config, memory=None, user_important_senders=None
    ):
        """
        Drop-in replacement for existing process_email_with_memory function
        that adds reasoning capabilities while maintaining backward compatibility.
        """
        
        # Check if reasoning engine should be used (can be controlled via config)
        use_reasoning = config.get('reasoning', {}).get('enabled', True)
        
        priority, analysis_result, reasoning_result = process_email_with_enhanced_reasoning(
            parsed_email=parsed_email,
            llm_client=llm_client,
            feedback_history=feedback_history,
            ml_pipeline=ml_pipeline,
            ml_label_encoder=ml_label_encoder,
            config=config,
            memory=memory,
            user_important_senders=user_important_senders,
            use_reasoning_engine=use_reasoning
        )
        
        # If we have reasoning result, add it to the email data for storage
        if reasoning_result:
            # Convert reasoning result to storable dict
            reasoning_dict = {
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
            
            # Add reasoning data to email
            if 'reasoning_result' not in parsed_email:
                parsed_email['reasoning_result'] = reasoning_dict
        
        # Return in the format expected by existing code
        return priority, analysis_result
    
    return enhanced_process_email_with_memory


def create_proactive_insights(
    email_data: Dict[str, Any],
    reasoning_result: Optional[ClassificationResult],
    memory: Any = None
) -> Dict[str, Any]:
    """
    Generate proactive insights based on email analysis and reasoning.
    
    Args:
        email_data: Email data dictionary
        reasoning_result: Classification result with reasoning
        memory: Memory system instance
        
    Returns:
        Dictionary with insight data
    """
    
    insights = {
        'type': 'email_insights',
        'timestamp': email_data.get('processed_at'),
        'email_id': email_data.get('id'),
        'suggestions': [],
        'patterns': [],
        'actions': []
    }
    
    if reasoning_result:
        # Add reasoning-based insights
        insights['confidence'] = reasoning_result.confidence
        insights['decision_method'] = reasoning_result.metadata.get('decision_method')
        
        # Low confidence insight
        if reasoning_result.confidence < 70:
            insights['suggestions'].append({
                'type': 'feedback_request',
                'priority': 'medium',
                'message': 'This email classification has low confidence. Your feedback would help improve accuracy.',
                'action': 'provide_feedback'
            })
        
        # High confidence urgent email
        if reasoning_result.priority in ['CRITICAL', 'HIGH'] and reasoning_result.confidence > 90:
            insights['suggestions'].append({
                'type': 'urgent_attention',
                'priority': 'high',
                'message': 'High confidence urgent email detected. Consider reviewing immediately.',
                'action': 'review_now'
            })
        
        # Pattern recognition insights
        if 'critical_sender' in reasoning_result.decision_factors:
            insights['patterns'].append({
                'type': 'important_sender',
                'message': f'This sender is marked as important in your settings.',
                'sender': email_data.get('sender', '')
            })
        
        # Suggest autonomous actions based on confidence
        reasoning_engine = ExplainableReasoningEngine({})  # Empty config for threshold checking
        
        if reasoning_engine.get_autonomous_action_confidence('archive', reasoning_result):
            if reasoning_result.priority == 'LOW' and 'promotion' in email_data.get('llm_purpose', '').lower():
                insights['actions'].append({
                    'type': 'auto_archive',
                    'confidence': reasoning_result.confidence,
                    'message': 'This promotional email could be automatically archived.',
                    'safe_to_execute': True
                })
        
        if reasoning_engine.get_autonomous_action_confidence('label', reasoning_result):
            insights['actions'].append({
                'type': 'auto_label',
                'confidence': reasoning_result.confidence,
                'message': f'Could automatically apply "{reasoning_result.priority}" priority label.',
                'safe_to_execute': reasoning_result.confidence > 85
            })
    
    # Add general email insights
    sender = email_data.get('sender', '')
    subject = email_data.get('subject', '')
    
    # Detect patterns
    if any(word in subject.lower() for word in ['meeting', 'calendar', 'schedule']):
        insights['patterns'].append({
            'type': 'meeting_request',
            'message': 'This appears to be a meeting-related email.',
            'suggestion': 'Consider checking your calendar for conflicts.'
        })
    
    if any(word in subject.lower() for word in ['invoice', 'payment', 'billing']):
        insights['patterns'].append({
            'type': 'financial',
            'message': 'This appears to be a financial/billing email.',
            'suggestion': 'Verify sender authenticity before taking action.'
        })
    
    # Check for reply patterns with memory
    if memory:
        try:
            # Get conversation history for this sender
            sender_history = memory.get_conversation_history(filters={'sender': sender})
            if len(sender_history) > 1:
                insights['patterns'].append({
                    'type': 'ongoing_conversation',
                    'message': f'Part of ongoing conversation with {sender}.',
                    'context': f'{len(sender_history)} previous messages'
                })
        except Exception as e:
            logging.warning(f"Failed to get conversation history for insights: {e}")
    
    return insights


def get_autonomous_action_recommendations(
    reasoning_result: ClassificationResult,
    email_data: Dict[str, Any],
    config: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """
    Get autonomous action recommendations based on reasoning result and confidence.
    
    Returns:
        List of recommended actions with confidence and safety flags
    """
    
    if not reasoning_result:
        return []
    
    recommendations = []
    reasoning_engine = ExplainableReasoningEngine(config)
    
    # Archive recommendations
    if reasoning_engine.get_autonomous_action_confidence('archive', reasoning_result):
        if reasoning_result.priority == 'LOW':
            purpose = email_data.get('llm_purpose', '').lower()
            if any(word in purpose for word in ['promotion', 'newsletter', 'marketing']):
                recommendations.append({
                    'action': 'archive',
                    'confidence': reasoning_result.confidence,
                    'reason': f'Low priority {purpose} email',
                    'safe_to_execute': reasoning_result.confidence > 95,
                    'requires_confirmation': reasoning_result.confidence < 95
                })
    
    # Labeling recommendations
    if reasoning_engine.get_autonomous_action_confidence('label', reasoning_result):
        recommendations.append({
            'action': 'apply_priority_label',
            'confidence': reasoning_result.confidence,
            'reason': f'High confidence {reasoning_result.priority} classification',
            'label': f'Maia/Priority/{reasoning_result.priority}',
            'safe_to_execute': reasoning_result.confidence > 85,
            'requires_confirmation': False
        })
    
    # Response suggestions
    if reasoning_engine.get_autonomous_action_confidence('suggestion', reasoning_result):
        analysis_result = None
        for step in reasoning_result.reasoning_chain:
            if step.step_type == 'llm_analysis' and step.result:
                analysis_result = step.result
                break
        
        if analysis_result and analysis_result.get('response_needed', False):
            recommendations.append({
                'action': 'suggest_response',
                'confidence': reasoning_result.confidence,
                'reason': 'Email likely requires a response',
                'estimated_time': analysis_result.get('estimated_time', 5),
                'safe_to_execute': False,  # Always require human review for responses
                'requires_confirmation': True
            })
    
    return recommendations