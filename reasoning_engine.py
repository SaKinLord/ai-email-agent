# -*- coding: utf-8 -*-
"""
Explainable Reasoning Engine for Maia Email Agent
Provides transparent, step-by-step reasoning for all email classification decisions.
"""

import logging
import json
from datetime import datetime
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass


@dataclass
class ReasoningStep:
    """Represents a single step in the reasoning process"""
    step_type: str  # 'feedback_check', 'ml_prediction', 'rule_match', 'llm_analysis'
    description: str
    weight: float  # 0.0 to 1.0
    confidence: float  # 0.0 to 1.0
    result: Any
    details: Dict[str, Any]


@dataclass
class ClassificationResult:
    """Complete classification result with explainable reasoning"""
    priority: str
    confidence: float  # Overall confidence 0-100%
    reasoning_chain: List[ReasoningStep]
    decision_factors: Dict[str, float]  # Factor weights that led to decision
    explanation: List[str]  # Human-readable explanations
    metadata: Dict[str, Any]  # Additional context


class ExplainableReasoningEngine:
    """
    Core reasoning engine that provides transparent decision-making for email classification.
    Replaces the black-box multi-layered approach with explainable AI reasoning.
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.reasoning_steps: List[ReasoningStep] = []
        self.decision_factors: Dict[str, float] = {}
        
        # Confidence thresholds for different actions (as decimals 0.0-1.0)
        self.confidence_thresholds = {
            'archive': 0.95,
            'label': 0.85,
            'priority_adjust': 0.80,
            'suggestion': 0.70
        }
    
    def classify_email_with_reasoning(
        self,
        email_data: Dict[str, Any],
        llm_client: Any,
        feedback_history: Dict[str, str],
        ml_pipeline: Any,
        ml_label_encoder: Any,
        memory: Any = None,
        user_important_senders: List[str] = None
    ) -> ClassificationResult:
        """
        Main classification method with full explainable reasoning.
        
        Returns:
            ClassificationResult: Complete result with reasoning chain
        """
        self.reasoning_steps = []
        self.decision_factors = {}
        
        # Initialize result structure
        final_priority = "MEDIUM"
        overall_confidence = 0.0
        explanation_parts = []
        
        sender = email_data.get('sender', '').lower()
        subject = email_data.get('subject', '').lower()
        body = email_data.get('body_text', '')
        
        # Step 1: Check feedback history (highest priority)
        feedback_result = self._check_feedback_history(sender, feedback_history)
        if feedback_result:
            final_priority = feedback_result.result
            overall_confidence = feedback_result.confidence
            explanation_parts.append(f"Used previous feedback for this sender ({feedback_result.details['sender_key']})")
            
            return ClassificationResult(
                priority=final_priority,
                confidence=overall_confidence,
                reasoning_chain=self.reasoning_steps,
                decision_factors=self.decision_factors,
                explanation=explanation_parts,
                metadata={
                    'decision_method': 'feedback_history',
                    'sender_key': feedback_result.details['sender_key']
                }
            )
        
        # Step 2: Enhanced LLM Analysis (for context and features)
        llm_analysis = self._perform_llm_analysis(email_data, llm_client, memory)
        
        # Step 3: ML Model Prediction (if available)
        ml_result = self._perform_ml_prediction(email_data, llm_analysis, ml_pipeline, ml_label_encoder)
        
        # Step 4: Critical Sender Rules Check
        critical_sender_result = self._check_critical_senders(sender, user_important_senders)
        
        # Step 5: Rule-based Analysis
        rule_result = self._perform_rule_analysis(sender, subject, body)
        
        # Step 6: Unified Decision Making
        final_result = self._make_unified_decision(
            llm_analysis, ml_result, critical_sender_result, rule_result
        )
        
        return final_result
    
    def _check_feedback_history(self, sender: str, feedback_history: Dict[str, str]) -> Optional[ReasoningStep]:
        """Check if we have previous feedback for this sender"""
        import re
        
        # Extract sender key (same logic as original)
        sender_key = sender
        match = re.search(r'<(.+?)>', sender)
        if match:
            sender_key = match.group(1).lower()
        else:
            sender_key = sender.split('@')[0] if '@' in sender else sender
            sender_key = re.sub(r'[^\w\s.-]', '', sender_key).strip().lower()
        
        if sender_key in feedback_history:
            corrected_priority = feedback_history[sender_key]
            step = ReasoningStep(
                step_type='feedback_check',
                description=f"Found previous feedback for sender '{sender_key}'",
                weight=1.0,  # Highest weight
                confidence=0.95,  # Very high confidence in user feedback
                result=corrected_priority,
                details={
                    'sender_key': sender_key,
                    'original_sender': sender,
                    'feedback_priority': corrected_priority
                }
            )
            self.reasoning_steps.append(step)
            self.decision_factors['user_feedback'] = 1.0
            return step
        
        # Log that no feedback was found
        step = ReasoningStep(
            step_type='feedback_check',
            description=f"No previous feedback found for sender '{sender_key}'",
            weight=0.0,
            confidence=1.0,
            result=None,
            details={'sender_key': sender_key}
        )
        self.reasoning_steps.append(step)
        return None
    
    def _perform_llm_analysis(self, email_data: Dict[str, Any], llm_client: Any, memory: Any) -> Optional[Dict[str, Any]]:
        """Perform LLM analysis and record reasoning"""
        from agent_logic import analyze_email_with_context
        
        try:
            analysis_result = analyze_email_with_context(llm_client, email_data, self.config, memory)
            
            if analysis_result:
                # Calculate confidence based on analysis quality
                urgency = analysis_result.get('urgency_score', 0)
                purpose = analysis_result.get('purpose', 'unknown')
                response_needed = analysis_result.get('response_needed', False)
                
                # Higher confidence for more decisive analysis
                confidence = min(0.9, (urgency / 5.0) * 0.8 + 0.2)
                
                step = ReasoningStep(
                    step_type='llm_analysis',
                    description=f"LLM analyzed urgency: {urgency}/5, purpose: {purpose}",
                    weight=0.6,
                    confidence=confidence,
                    result=analysis_result,
                    details={
                        'urgency_score': urgency,
                        'purpose': purpose,
                        'response_needed': response_needed,
                        'estimated_time': analysis_result.get('estimated_time', 5)
                    }
                )
                self.reasoning_steps.append(step)
                self.decision_factors['llm_analysis'] = 0.6
                
                return analysis_result
            else:
                step = ReasoningStep(
                    step_type='llm_analysis',
                    description="LLM analysis failed",
                    weight=0.0,
                    confidence=0.0,
                    result=None,
                    details={'error': 'Analysis returned None'}
                )
                self.reasoning_steps.append(step)
                return None
                
        except Exception as e:
            step = ReasoningStep(
                step_type='llm_analysis',
                description=f"LLM analysis error: {str(e)}",
                weight=0.0,
                confidence=0.0,
                result=None,
                details={'error': str(e)}
            )
            self.reasoning_steps.append(step)
            return None
    
    def _perform_ml_prediction(self, email_data: Dict[str, Any], llm_analysis: Optional[Dict[str, Any]], 
                              ml_pipeline: Any, ml_label_encoder: Any) -> Optional[ReasoningStep]:
        """Perform ML prediction and record reasoning"""
        if not ml_pipeline or not ml_label_encoder:
            step = ReasoningStep(
                step_type='ml_prediction',
                description="ML model not available",
                weight=0.0,
                confidence=0.0,
                result=None,
                details={'reason': 'Model not loaded'}
            )
            self.reasoning_steps.append(step)
            return None
        
        try:
            from ml_utils import predict_priority
            
            # Prepare prediction data
            prediction_data = email_data.copy()
            if llm_analysis:
                prediction_data['llm_urgency'] = llm_analysis.get('urgency_score', 0)
                prediction_data['llm_purpose'] = llm_analysis.get('purpose', 'Unknown')
                prediction_data['llm_response_needed'] = llm_analysis.get('response_needed', False)
                prediction_data['llm_estimated_time'] = llm_analysis.get('estimated_time', 5)
            else:
                prediction_data.update({
                    'llm_urgency': 0,
                    'llm_purpose': 'Unknown',
                    'llm_response_needed': False,
                    'llm_estimated_time': 5
                })
            
            ml_prediction = predict_priority(prediction_data, ml_pipeline, ml_label_encoder)
            
            if ml_prediction:
                # TODO: Extract prediction confidence from ML model if available
                confidence = 0.75  # Default confidence for ML predictions
                
                step = ReasoningStep(
                    step_type='ml_prediction',
                    description=f"ML model predicted: {ml_prediction}",
                    weight=0.7,
                    confidence=confidence,
                    result=ml_prediction,
                    details={
                        'prediction': ml_prediction,
                        'features_used': ['text', 'sender', 'llm_analysis']
                    }
                )
                self.reasoning_steps.append(step)
                self.decision_factors['ml_model'] = 0.7
                return step
            else:
                step = ReasoningStep(
                    step_type='ml_prediction',
                    description="ML prediction failed",
                    weight=0.0,
                    confidence=0.0,
                    result=None,
                    details={'error': 'Prediction returned None'}
                )
                self.reasoning_steps.append(step)
                return None
                
        except Exception as e:
            step = ReasoningStep(
                step_type='ml_prediction',
                description=f"ML prediction error: {str(e)}",
                weight=0.0,
                confidence=0.0,
                result=None,
                details={'error': str(e)}
            )
            self.reasoning_steps.append(step)
            return None
    
    def _check_critical_senders(self, sender: str, user_important_senders: List[str] = None) -> Optional[ReasoningStep]:
        """Check if sender is in critical/important sender list"""
        import re
        
        if user_important_senders is None:
            user_important_senders = []
        
        # Combine config and user important senders
        config_senders = [s.lower() for s in self.config['classification']['important_senders']]
        all_important_senders = set(config_senders + [s.lower() for s in user_important_senders])
        
        for imp_sender in all_important_senders:
            is_domain_rule = imp_sender.startswith("@")
            match_found = False
            
            if is_domain_rule:
                sender_domain_match = re.search(r'@([\w.-]+)', sender)
                if sender_domain_match:
                    sender_domain = "@" + sender_domain_match.group(1)
                    if sender_domain == imp_sender:
                        match_found = True
            elif imp_sender in sender:
                match_found = True
            
            if match_found:
                source = "User Preference" if imp_sender in [s.lower() for s in user_important_senders] else "Configuration"
                step = ReasoningStep(
                    step_type='rule_match',
                    description=f"Sender matches critical sender rule ({source})",
                    weight=0.9,  # Very high weight, but user feedback still overrides
                    confidence=0.95,
                    result="CRITICAL",
                    details={
                        'matched_rule': imp_sender,
                        'rule_source': source,
                        'rule_type': 'domain' if is_domain_rule else 'specific'
                    }
                )
                self.reasoning_steps.append(step)
                self.decision_factors['critical_sender'] = 0.9
                return step
        
        step = ReasoningStep(
            step_type='rule_match',
            description="No critical sender rules matched",
            weight=0.0,
            confidence=1.0,
            result=None,
            details={'checked_rules': len(all_important_senders)}
        )
        self.reasoning_steps.append(step)
        return None
    
    def _perform_rule_analysis(self, sender: str, subject: str, body: str) -> List[ReasoningStep]:
        """Perform rule-based analysis and record all matches"""
        rule_steps = []
        
        # Low priority keyword checks
        sender_keywords_low = self.config['classification']['sender_keywords_low']
        subject_keywords_low = self.config['classification']['subject_keywords_low']
        
        low_keywords = sender_keywords_low + subject_keywords_low
        for keyword in low_keywords:
            if keyword in sender or keyword in subject:
                step = ReasoningStep(
                    step_type='rule_match',
                    description=f"Low priority keyword '{keyword}' found",
                    weight=0.4,
                    confidence=0.8,
                    result="LOW",
                    details={
                        'keyword': keyword,
                        'location': 'sender' if keyword in sender else 'subject'
                    }
                )
                rule_steps.append(step)
                self.reasoning_steps.append(step)
        
        # High priority keyword checks
        subject_keywords_high = self.config['classification']['subject_keywords_high']
        for keyword in subject_keywords_high:
            if keyword in subject:
                step = ReasoningStep(
                    step_type='rule_match',
                    description=f"High priority keyword '{keyword}' found in subject",
                    weight=0.5,
                    confidence=0.8,
                    result="HIGH",
                    details={
                        'keyword': keyword,
                        'location': 'subject'
                    }
                )
                rule_steps.append(step)
                self.reasoning_steps.append(step)
        
        if not rule_steps:
            step = ReasoningStep(
                step_type='rule_match',
                description="No keyword rules matched",
                weight=0.0,
                confidence=1.0,
                result=None,
                details={'keywords_checked': len(low_keywords) + len(subject_keywords_high)}
            )
            self.reasoning_steps.append(step)
        
        return rule_steps
    
    def _make_unified_decision(self, llm_analysis: Optional[Dict[str, Any]], ml_result: Optional[ReasoningStep], 
                             critical_sender: Optional[ReasoningStep], rule_results: List[ReasoningStep]) -> ClassificationResult:
        """Make final decision based on all reasoning steps with enhanced explanations"""
        
        # Get user priority patterns for personalized explanations
        try:
            from task_utils import get_user_priority_patterns
            user_patterns = get_user_priority_patterns("default_user")
            has_personalization = user_patterns.get('has_patterns', False)
        except Exception:
            user_patterns = {}
            has_personalization = False
        
        # If critical sender matched, that's the decision
        if critical_sender and critical_sender.result:
            explanation = [f"Critical sender rule matched: {critical_sender.description}"]
            if has_personalization:
                explanation.append("This sender is marked as important in your personalized settings")
            
            return ClassificationResult(
                priority=critical_sender.result,
                confidence=critical_sender.confidence,  # Already 0.95, don't multiply by 100
                reasoning_chain=self.reasoning_steps,
                decision_factors=self.decision_factors,
                explanation=explanation,
                metadata={'decision_method': 'critical_sender_rule'}
            )
        
        # If ML prediction is available and confident, use it
        if ml_result and ml_result.result and ml_result.confidence > 0.7:
            explanation = [f"ML model prediction: {ml_result.result} (confidence: {ml_result.confidence:.0%})"]
            if llm_analysis:
                urgency = llm_analysis.get('urgency_score', 0)
                purpose = llm_analysis.get('purpose', 'unknown')
                explanation.append(f"Based on urgency score {urgency}/5 and purpose '{purpose}'")
            
            # Add personalization context
            if has_personalization:
                priority_themes = user_patterns.get('priority_themes', [])
                if priority_themes:
                    explanation.append(f"Leverages your feedback patterns on tasks like: {', '.join(priority_themes[:3])}")
                else:
                    explanation.append("Enhanced with your personal feedback history")
            
            return ClassificationResult(
                priority=ml_result.result,
                confidence=ml_result.confidence,  # Already between 0.0-1.0, don't multiply by 100
                reasoning_chain=self.reasoning_steps,
                decision_factors=self.decision_factors,
                explanation=explanation,
                metadata={'decision_method': 'ml_prediction'}
            )
        
        # Fall back to LLM analysis with enhanced decision logic
        if llm_analysis:
            urgency = llm_analysis.get('urgency_score', 0)
            purpose = llm_analysis.get('purpose', 'unknown').lower()
            response_needed = llm_analysis.get('response_needed', False)
            estimated_time = llm_analysis.get('estimated_time', 5)
            
            # Enhanced decision logic with detailed explanations
            if urgency >= 5 and response_needed and estimated_time > 10:
                priority = "CRITICAL"
                confidence = 0.90  # Convert to decimal (0.0-1.0)
                explanation = [
                    f"🚨 Very high urgency ({urgency}/5 points)",
                    f"📧 Response required within {estimated_time} minutes",
                    f"🎯 Purpose: {purpose}"
                ]
            elif urgency >= 4 or (response_needed and purpose in ["action request", "question"]):
                priority = "HIGH"
                confidence = 0.85  # Convert to decimal (0.0-1.0)
                explanation = [
                    f"⚡ High urgency ({urgency}/5 points)",
                    f"🎯 Purpose: {purpose}"
                ]
                if response_needed:
                    explanation.append("📧 Response needed")
                if purpose in ["action request", "question"]:
                    explanation.append("🔥 Requires immediate action")
            elif urgency >= 3 or purpose in ["action request", "question", "meeting invite"] or response_needed:
                priority = "MEDIUM"
                confidence = 0.80  # Convert to decimal (0.0-1.0)
                explanation = [
                    f"📊 Moderate urgency ({urgency}/5 points)",
                    f"🎯 Purpose: {purpose}"
                ]
                if response_needed:
                    explanation.append("📧 May need response")
                if purpose in ["meeting invite"]:
                    explanation.append("📅 Meeting coordination")
            else:
                priority = "LOW"
                confidence = 0.75  # Convert to decimal (0.0-1.0)
                explanation = [
                    f"📝 Low urgency ({urgency}/5 points)",
                    f"💡 Informational purpose: {purpose}",
                    "⏳ No immediate action required"
                ]
            
            # Add personalization insights before rule adjustments
            if has_personalization:
                task_types = user_patterns.get('task_types', [])
                personalization_strength = user_patterns.get('personalization_strength', 'none')
                
                if task_types and purpose in task_types:
                    explanation.append(f"🎯 Matches your priority patterns: {', '.join(task_types[:2])}")
                elif personalization_strength in ['moderate', 'strong']:
                    explanation.append(f"🤖 AI learning from {user_patterns.get('total_positive_examples', 0)} feedback examples")
            
            # Adjust for rule matches
            high_rules = [r for r in rule_results if r.result == "HIGH"]
            low_rules = [r for r in rule_results if r.result == "LOW"]
            
            if high_rules and priority not in ["CRITICAL"]:
                priority = "HIGH"
                explanation.append("⬆️ Elevated due to high-priority keyword rules")
                confidence = min(confidence + 0.05, 0.95)  # Slight confidence boost (decimal)
            elif low_rules and priority not in ["CRITICAL", "HIGH"]:
                priority = "LOW"
                explanation.append("⬇️ Reduced due to low-priority keyword rules")
                confidence = max(confidence - 0.05, 0.60)  # Slight confidence reduction (decimal)
            
            return ClassificationResult(
                priority=priority,
                confidence=confidence,
                reasoning_chain=self.reasoning_steps,
                decision_factors=self.decision_factors,
                explanation=explanation,
                metadata={'decision_method': 'llm_with_rules', 'has_personalization': has_personalization}
            )
        
        # Final fallback to rules only
        high_rules = [r for r in rule_results if r.result == "HIGH"]
        low_rules = [r for r in rule_results if r.result == "LOW"]
        
        if high_rules:
            return ClassificationResult(
                priority="HIGH",
                confidence=0.60,  # Convert to decimal (0.0-1.0)
                reasoning_chain=self.reasoning_steps,
                decision_factors=self.decision_factors,
                explanation=["Based on high-priority keyword rules only (LLM analysis failed)"],
                metadata={'decision_method': 'rules_only'}
            )
        elif low_rules:
            return ClassificationResult(
                priority="LOW",
                confidence=0.60,  # Convert to decimal (0.0-1.0)
                reasoning_chain=self.reasoning_steps,
                decision_factors=self.decision_factors,
                explanation=["Based on low-priority keyword rules only (LLM analysis failed)"],
                metadata={'decision_method': 'rules_only'}
            )
        else:
            return ClassificationResult(
                priority="MEDIUM",
                confidence=0.50,  # Convert to decimal (0.0-1.0)
                reasoning_chain=self.reasoning_steps,
                decision_factors=self.decision_factors,
                explanation=["No clear signals detected, defaulting to medium priority"],
                metadata={'decision_method': 'default_fallback'}
            )
    
    def get_autonomous_action_confidence(self, action_type: str, classification_result: ClassificationResult) -> bool:
        """
        Determine if the system is confident enough to perform an autonomous action.
        
        Args:
            action_type: Type of action ('archive', 'label', 'priority_adjust', 'suggestion')
            classification_result: The classification result with confidence
            
        Returns:
            bool: True if confident enough to perform the action
        """
        required_confidence = self.confidence_thresholds.get(action_type, 0.70)
        return classification_result.confidence >= required_confidence
    
    def generate_insight(self, classification_result: ClassificationResult, email_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate proactive insights about the email and user patterns.
        
        Returns:
            Dict with insight data for the UI
        """
        sender = email_data.get('sender', '')
        subject = email_data.get('subject', '')
        
        insight = {
            'type': 'classification_insight',
            'confidence': classification_result.confidence,
            'decision_method': classification_result.metadata.get('decision_method'),
            'explanation': classification_result.explanation,
            'suggestions': []
        }
        
        # Add specific suggestions based on reasoning
        if classification_result.confidence < 70:
            insight['suggestions'].append({
                'type': 'feedback_request',
                'message': 'This classification has low confidence. Your feedback would help improve accuracy.'
            })
        
        if 'critical_sender' in classification_result.decision_factors:
            insight['suggestions'].append({
                'type': 'sender_pattern',
                'message': f'This sender ({sender}) is marked as important in your settings.'
            })
        
        # Check for patterns that might need user attention
        if classification_result.priority == "HIGH" and classification_result.confidence > 90:
            insight['suggestions'].append({
                'type': 'urgent_action',
                'message': 'High confidence urgent email - consider reviewing immediately.'
            })
        
        return insight