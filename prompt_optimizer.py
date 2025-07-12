# -*- coding: utf-8 -*-
"""
LLM Prompt Optimization and Performance Testing System
Tests and optimizes prompts for email classification, chat responses, and task extraction.
"""

import json
import logging
import time
import statistics
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
import asyncio
import concurrent.futures
from collections import defaultdict

logger = logging.getLogger(__name__)

@dataclass
class PromptTest:
    """Represents a single prompt performance test"""
    test_id: str
    prompt_version: str
    test_type: str  # 'email_classification', 'chat_response', 'task_extraction'
    input_data: Dict[str, Any]
    expected_output: Optional[Dict[str, Any]]
    actual_output: Optional[Dict[str, Any]]
    response_time: float
    token_usage: int
    cost: float
    accuracy_score: float  # 0.0 to 1.0
    confidence_score: float  # 0.0 to 1.0
    error_message: Optional[str]
    timestamp: datetime

@dataclass
class PromptVersion:
    """Represents a prompt template version"""
    version_id: str
    prompt_type: str
    template: str
    variables: List[str]
    description: str
    created_at: datetime
    performance_metrics: Dict[str, float]

@dataclass
class TestSuite:
    """Collection of test cases for a specific prompt type"""
    suite_name: str
    prompt_type: str
    test_cases: List[Dict[str, Any]]
    evaluation_criteria: Dict[str, Any]

class PromptOptimizer:
    """
    Comprehensive prompt optimization and testing system for LLM performance
    """
    
    def __init__(self, llm_manager, db_client, config):
        self.llm_manager = llm_manager
        self.db_client = db_client
        self.config = config
        self.test_results = []
        self.prompt_versions = {}
        
        # Performance thresholds
        self.performance_thresholds = {
            'email_classification': {
                'accuracy': 0.85,
                'response_time': 5.0,  # seconds
                'confidence': 0.80,
                'cost_per_classification': 0.02  # dollars
            },
            'chat_response': {
                'relevance': 0.80,
                'response_time': 8.0,
                'naturalness': 0.75,
                'cost_per_response': 0.05
            },
            'task_extraction': {
                'precision': 0.85,
                'recall': 0.80,
                'response_time': 6.0,
                'cost_per_extraction': 0.03
            }
        }
        
        # Initialize test suites
        self._initialize_test_suites()
    
    def _initialize_test_suites(self):
        """Initialize comprehensive test suites for different prompt types"""
        
        # Email Classification Test Suite
        self.email_classification_suite = TestSuite(
            suite_name="email_classification_v1",
            prompt_type="email_classification",
            test_cases=[
                {
                    "test_id": "urgent_meeting",
                    "email_data": {
                        "sender": "boss@company.com",
                        "subject": "URGENT: Emergency meeting in 30 minutes",
                        "body_text": "We need to discuss the critical project issue immediately. Please join the conference room."
                    },
                    "expected": {
                        "urgency_score": 5,
                        "purpose": "important",
                        "response_needed": True,
                        "priority": "CRITICAL"
                    }
                },
                {
                    "test_id": "newsletter",
                    "email_data": {
                        "sender": "newsletter@techcrunch.com",
                        "subject": "Today's Top Tech Stories",
                        "body_text": "Here are the top technology stories for today..."
                    },
                    "expected": {
                        "urgency_score": 1,
                        "purpose": "newsletter",
                        "response_needed": False,
                        "priority": "LOW"
                    }
                },
                {
                    "test_id": "linkedin_notification",
                    "email_data": {
                        "sender": "notifications-noreply@linkedin.com",
                        "subject": "You have new messages",
                        "body_text": "You have 3 new messages from your connections."
                    },
                    "expected": {
                        "urgency_score": 2,
                        "purpose": "social",
                        "response_needed": False,
                        "priority": "LOW"
                    }
                },
                {
                    "test_id": "project_update",
                    "email_data": {
                        "sender": "team-lead@company.com",
                        "subject": "Project Alpha Status Update",
                        "body_text": "The project is on track. Here's the latest progress report..."
                    },
                    "expected": {
                        "urgency_score": 3,
                        "purpose": "information",
                        "response_needed": False,
                        "priority": "MEDIUM"
                    }
                },
                {
                    "test_id": "action_request",
                    "email_data": {
                        "sender": "client@bigcorp.com",
                        "subject": "Please review the contract by Friday",
                        "body_text": "Could you please review the attached contract and send feedback by end of week?"
                    },
                    "expected": {
                        "urgency_score": 4,
                        "purpose": "action_request",
                        "response_needed": True,
                        "priority": "HIGH"
                    }
                }
            ],
            evaluation_criteria={
                "urgency_tolerance": 1,  # Allow ±1 point difference
                "purpose_exact_match": True,
                "response_needed_exact": True,
                "priority_mapping": {"CRITICAL": 5, "HIGH": 4, "MEDIUM": 3, "LOW": 2}
            }
        )
        
        # Chat Response Test Suite
        self.chat_response_suite = TestSuite(
            suite_name="chat_response_v1",
            prompt_type="chat_response",
            test_cases=[
                {
                    "test_id": "greeting",
                    "message": "Hi Maia, how are you?",
                    "context": {"email_count": 15, "unread_count": 3},
                    "expected_elements": ["greeting", "helpful_offer", "email_summary"]
                },
                {
                    "test_id": "priority_request",
                    "message": "Show me my most important emails",
                    "context": {"email_count": 50, "priority_breakdown": {"HIGH": 5, "MEDIUM": 20, "LOW": 25}},
                    "expected_elements": ["priority_acknowledgment", "actionable_response", "specific_counts"]
                },
                {
                    "test_id": "summary_request",
                    "message": "Can you summarize my emails from today?",
                    "context": {"today_count": 12, "urgent_count": 2},
                    "expected_elements": ["summary_offer", "count_mention", "urgency_highlight"]
                }
            ],
            evaluation_criteria={
                "min_response_length": 50,
                "max_response_length": 300,
                "required_elements_coverage": 0.8,
                "politeness_score": 0.7
            }
        )
        
        # Task Extraction Test Suite
        self.task_extraction_suite = TestSuite(
            suite_name="task_extraction_v1",
            prompt_type="task_extraction",
            test_cases=[
                {
                    "test_id": "single_task",
                    "email_subject": "Please review the quarterly report",
                    "email_body": "Hi, could you please review the Q3 quarterly report and send me your feedback by Thursday?",
                    "expected_tasks": [
                        {
                            "task_description": "Review the quarterly report and send feedback",
                            "deadline": "Thursday",
                            "stakeholders": ["sender"]
                        }
                    ]
                },
                {
                    "test_id": "multiple_tasks",
                    "email_subject": "Project coordination",
                    "email_body": "Please update the project timeline, schedule a meeting with the team, and prepare the presentation for Friday.",
                    "expected_tasks": [
                        {"task_description": "Update the project timeline", "deadline": None},
                        {"task_description": "Schedule a meeting with the team", "deadline": None},
                        {"task_description": "Prepare the presentation", "deadline": "Friday"}
                    ]
                },
                {
                    "test_id": "no_tasks",
                    "email_subject": "FYI: System maintenance tonight",
                    "email_body": "Just wanted to let you know that we'll be performing system maintenance tonight from 10 PM to 2 AM.",
                    "expected_tasks": []
                }
            ],
            evaluation_criteria={
                "task_count_tolerance": 1,
                "description_similarity_threshold": 0.7,
                "deadline_extraction_accuracy": 0.8
            }
        )
    
    async def run_comprehensive_test_suite(self, prompt_version: str = "current") -> Dict[str, Any]:
        """
        Run comprehensive performance tests across all prompt types
        """
        logger.info(f"Starting comprehensive prompt testing for version: {prompt_version}")
        
        results = {
            "test_session_id": f"test_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "prompt_version": prompt_version,
            "start_time": datetime.now(),
            "test_results": {},
            "performance_summary": {},
            "recommendations": []
        }
        
        # Test email classification
        logger.info("Testing email classification prompts...")
        email_results = await self._test_email_classification_suite()
        results["test_results"]["email_classification"] = email_results
        
        # Test chat responses
        logger.info("Testing chat response prompts...")
        chat_results = await self._test_chat_response_suite()
        results["test_results"]["chat_response"] = chat_results
        
        # Test task extraction
        logger.info("Testing task extraction prompts...")
        task_results = await self._test_task_extraction_suite()
        results["test_results"]["task_extraction"] = task_results
        
        # Calculate overall performance
        results["performance_summary"] = self._calculate_performance_summary(results["test_results"])
        results["recommendations"] = self._generate_optimization_recommendations(results)
        results["end_time"] = datetime.now()
        
        # Save results
        await self._save_test_results(results)
        
        return results
    
    async def _test_email_classification_suite(self) -> Dict[str, Any]:
        """Test email classification prompt performance"""
        suite_results = {
            "suite_name": self.email_classification_suite.suite_name,
            "test_cases": [],
            "metrics": {
                "accuracy": 0.0,
                "avg_response_time": 0.0,
                "avg_confidence": 0.0,
                "total_cost": 0.0,
                "success_rate": 0.0
            }
        }
        
        total_accuracy = 0.0
        total_response_time = 0.0
        total_confidence = 0.0
        total_cost = 0.0
        successful_tests = 0
        
        for test_case in self.email_classification_suite.test_cases:
            start_time = time.time()
            
            try:
                # Run classification
                result = await self._run_email_classification_test(test_case)
                response_time = time.time() - start_time
                
                # Calculate accuracy
                accuracy = self._calculate_classification_accuracy(test_case["expected"], result)
                
                # Extract metrics
                confidence = result.get("confidence", 0) / 100.0 if result.get("confidence", 0) > 1 else result.get("confidence", 0)
                cost = self._estimate_classification_cost(test_case["email_data"])
                
                test_result = {
                    "test_id": test_case["test_id"],
                    "success": True,
                    "accuracy": accuracy,
                    "response_time": response_time,
                    "confidence": confidence,
                    "cost": cost,
                    "expected": test_case["expected"],
                    "actual": result,
                    "error": None
                }
                
                total_accuracy += accuracy
                total_response_time += response_time
                total_confidence += confidence
                total_cost += cost
                successful_tests += 1
                
            except Exception as e:
                test_result = {
                    "test_id": test_case["test_id"],
                    "success": False,
                    "accuracy": 0.0,
                    "response_time": time.time() - start_time,
                    "confidence": 0.0,
                    "cost": 0.0,
                    "expected": test_case["expected"],
                    "actual": None,
                    "error": str(e)
                }
                logger.error(f"Email classification test failed: {test_case['test_id']} - {e}")
            
            suite_results["test_cases"].append(test_result)
        
        # Calculate suite metrics
        total_tests = len(self.email_classification_suite.test_cases)
        if successful_tests > 0:
            suite_results["metrics"] = {
                "accuracy": total_accuracy / successful_tests,
                "avg_response_time": total_response_time / successful_tests,
                "avg_confidence": total_confidence / successful_tests,
                "total_cost": total_cost,
                "success_rate": successful_tests / total_tests
            }
        
        return suite_results
    
    async def _run_email_classification_test(self, test_case: Dict[str, Any]) -> Dict[str, Any]:
        """Run a single email classification test"""
        email_data = test_case["email_data"]
        
        # Use the hybrid LLM system for classification
        result = self.llm_manager.analyze_email_optimized(
            email_data=email_data,
            config=self.config,
            memory=None
        )
        
        if not result:
            raise Exception("LLM analysis returned None")
        
        return result
    
    def _calculate_classification_accuracy(self, expected: Dict[str, Any], actual: Dict[str, Any]) -> float:
        """Calculate accuracy score for email classification"""
        if not actual:
            return 0.0
        
        score = 0.0
        total_factors = 0
        
        # Urgency score accuracy (±1 tolerance)
        expected_urgency = expected.get("urgency_score", 0)
        actual_urgency = actual.get("urgency_score", 0)
        urgency_diff = abs(expected_urgency - actual_urgency)
        urgency_score = max(0, 1 - (urgency_diff / 5.0))  # Normalize to 0-1
        score += urgency_score
        total_factors += 1
        
        # Purpose accuracy (exact match)
        expected_purpose = expected.get("purpose", "").lower()
        actual_purpose = actual.get("purpose", "").lower()
        purpose_score = 1.0 if expected_purpose == actual_purpose else 0.0
        score += purpose_score
        total_factors += 1
        
        # Response needed accuracy
        expected_response = expected.get("response_needed", False)
        actual_response = actual.get("response_needed", False)
        response_score = 1.0 if expected_response == actual_response else 0.0
        score += response_score
        total_factors += 1
        
        return score / total_factors if total_factors > 0 else 0.0
    
    async def _test_chat_response_suite(self) -> Dict[str, Any]:
        """Test chat response prompt performance"""
        suite_results = {
            "suite_name": self.chat_response_suite.suite_name,
            "test_cases": [],
            "metrics": {
                "relevance": 0.0,
                "avg_response_time": 0.0,
                "naturalness": 0.0,
                "total_cost": 0.0,
                "success_rate": 0.0
            }
        }
        
        total_relevance = 0.0
        total_response_time = 0.0
        total_naturalness = 0.0
        total_cost = 0.0
        successful_tests = 0
        
        for test_case in self.chat_response_suite.test_cases:
            start_time = time.time()
            
            try:
                # Mock enhanced chat system
                from enhanced_chat_system import EnhancedChatSystem
                chat_system = EnhancedChatSystem(self.llm_manager, self.db_client, self.config)
                
                # Run chat test
                result = chat_system.process_message(
                    user_id="test_user",
                    message=test_case["message"],
                    conversation_context=test_case.get("context", {})
                )
                
                response_time = time.time() - start_time
                
                # Calculate metrics
                relevance = self._calculate_chat_relevance(test_case, result)
                naturalness = self._calculate_response_naturalness(result.get("response", ""))
                cost = self._estimate_chat_cost(test_case["message"], result.get("response", ""))
                
                test_result = {
                    "test_id": test_case["test_id"],
                    "success": True,
                    "relevance": relevance,
                    "naturalness": naturalness,
                    "response_time": response_time,
                    "cost": cost,
                    "response": result.get("response", ""),
                    "error": None
                }
                
                total_relevance += relevance
                total_naturalness += naturalness
                total_response_time += response_time
                total_cost += cost
                successful_tests += 1
                
            except Exception as e:
                test_result = {
                    "test_id": test_case["test_id"],
                    "success": False,
                    "relevance": 0.0,
                    "naturalness": 0.0,
                    "response_time": time.time() - start_time,
                    "cost": 0.0,
                    "response": "",
                    "error": str(e)
                }
                logger.error(f"Chat response test failed: {test_case['test_id']} - {e}")
            
            suite_results["test_cases"].append(test_result)
        
        # Calculate suite metrics
        total_tests = len(self.chat_response_suite.test_cases)
        if successful_tests > 0:
            suite_results["metrics"] = {
                "relevance": total_relevance / successful_tests,
                "naturalness": total_naturalness / successful_tests,
                "avg_response_time": total_response_time / successful_tests,
                "total_cost": total_cost,
                "success_rate": successful_tests / total_tests
            }
        
        return suite_results
    
    def _calculate_chat_relevance(self, test_case: Dict[str, Any], result: Dict[str, Any]) -> float:
        """Calculate relevance score for chat responses"""
        response = result.get("response", "").lower()
        expected_elements = test_case.get("expected_elements", [])
        
        if not expected_elements:
            return 0.5  # Default score if no expected elements
        
        matched_elements = 0
        for element in expected_elements:
            # Simple keyword matching for demonstration
            if element == "greeting" and any(word in response for word in ["hello", "hi", "good"]):
                matched_elements += 1
            elif element == "helpful_offer" and any(word in response for word in ["help", "assist", "can i"]):
                matched_elements += 1
            elif element == "email_summary" and any(word in response for word in ["emails", "messages", "inbox"]):
                matched_elements += 1
            elif element == "priority_acknowledgment" and any(word in response for word in ["important", "priority", "urgent"]):
                matched_elements += 1
            elif element == "actionable_response" and any(word in response for word in ["show", "view", "here", "find"]):
                matched_elements += 1
        
        return matched_elements / len(expected_elements)
    
    def _calculate_response_naturalness(self, response: str) -> float:
        """Calculate naturalness score for responses"""
        if not response:
            return 0.0
        
        # Simple heuristics for naturalness
        score = 0.0
        
        # Length check (not too short or too long)
        length = len(response)
        if 50 <= length <= 300:
            score += 0.3
        
        # Sentence structure (has proper punctuation)
        if any(punct in response for punct in ['.', '!', '?']):
            score += 0.2
        
        # Personal pronouns (conversational)
        if any(pronoun in response.lower() for pronoun in ['i', 'you', 'your', 'my']):
            score += 0.2
        
        # Politeness indicators
        if any(polite in response.lower() for polite in ['please', 'thank', 'sorry', 'help']):
            score += 0.2
        
        # No technical jargon
        jargon_words = ['api', 'llm', 'model', 'algorithm', 'processing']
        if not any(jargon in response.lower() for jargon in jargon_words):
            score += 0.1
        
        return min(score, 1.0)
    
    async def _test_task_extraction_suite(self) -> Dict[str, Any]:
        """Test task extraction prompt performance"""
        suite_results = {
            "suite_name": self.task_extraction_suite.suite_name,
            "test_cases": [],
            "metrics": {
                "precision": 0.0,
                "recall": 0.0,
                "f1_score": 0.0,
                "avg_response_time": 0.0,
                "total_cost": 0.0,
                "success_rate": 0.0
            }
        }
        
        total_precision = 0.0
        total_recall = 0.0
        total_response_time = 0.0
        total_cost = 0.0
        successful_tests = 0
        
        for test_case in self.task_extraction_suite.test_cases:
            start_time = time.time()
            
            try:
                # Run task extraction
                result = self.llm_manager.extract_tasks_from_email(
                    email_body=test_case["email_body"],
                    email_subject=test_case["email_subject"]
                )
                
                response_time = time.time() - start_time
                
                # Calculate precision and recall
                precision, recall = self._calculate_task_extraction_metrics(
                    test_case["expected_tasks"], result or []
                )
                cost = self._estimate_task_extraction_cost(test_case["email_body"])
                
                test_result = {
                    "test_id": test_case["test_id"],
                    "success": True,
                    "precision": precision,
                    "recall": recall,
                    "f1_score": (2 * precision * recall) / (precision + recall) if (precision + recall) > 0 else 0,
                    "response_time": response_time,
                    "cost": cost,
                    "expected_tasks": test_case["expected_tasks"],
                    "extracted_tasks": result,
                    "error": None
                }
                
                total_precision += precision
                total_recall += recall
                total_response_time += response_time
                total_cost += cost
                successful_tests += 1
                
            except Exception as e:
                test_result = {
                    "test_id": test_case["test_id"],
                    "success": False,
                    "precision": 0.0,
                    "recall": 0.0,
                    "f1_score": 0.0,
                    "response_time": time.time() - start_time,
                    "cost": 0.0,
                    "expected_tasks": test_case["expected_tasks"],
                    "extracted_tasks": [],
                    "error": str(e)
                }
                logger.error(f"Task extraction test failed: {test_case['test_id']} - {e}")
            
            suite_results["test_cases"].append(test_result)
        
        # Calculate suite metrics
        total_tests = len(self.task_extraction_suite.test_cases)
        if successful_tests > 0:
            avg_precision = total_precision / successful_tests
            avg_recall = total_recall / successful_tests
            suite_results["metrics"] = {
                "precision": avg_precision,
                "recall": avg_recall,
                "f1_score": (2 * avg_precision * avg_recall) / (avg_precision + avg_recall) if (avg_precision + avg_recall) > 0 else 0,
                "avg_response_time": total_response_time / successful_tests,
                "total_cost": total_cost,
                "success_rate": successful_tests / total_tests
            }
        
        return suite_results
    
    def _calculate_task_extraction_metrics(self, expected_tasks: List[Dict], extracted_tasks: List[Dict]) -> Tuple[float, float]:
        """Calculate precision and recall for task extraction"""
        if not expected_tasks and not extracted_tasks:
            return 1.0, 1.0  # Perfect match for empty sets
        
        if not expected_tasks:
            return 0.0, 1.0 if not extracted_tasks else 0.0  # No tasks expected
        
        if not extracted_tasks:
            return 1.0 if not expected_tasks else 0.0, 0.0  # No tasks extracted
        
        # Simple matching based on task description similarity
        matched_tasks = 0
        for expected_task in expected_tasks:
            expected_desc = expected_task.get("task_description", "").lower()
            for extracted_task in extracted_tasks:
                extracted_desc = extracted_task.get("task_description", "").lower()
                # Simple similarity check (could be improved with fuzzy matching)
                if self._calculate_text_similarity(expected_desc, extracted_desc) > 0.7:
                    matched_tasks += 1
                    break
        
        precision = matched_tasks / len(extracted_tasks) if extracted_tasks else 0.0
        recall = matched_tasks / len(expected_tasks) if expected_tasks else 0.0
        
        return precision, recall
    
    def _calculate_text_similarity(self, text1: str, text2: str) -> float:
        """Simple text similarity calculation"""
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        
        if not words1 and not words2:
            return 1.0
        
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        
        return len(intersection) / len(union) if union else 0.0
    
    def _calculate_performance_summary(self, test_results: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate overall performance summary across all test suites"""
        summary = {
            "overall_score": 0.0,
            "performance_by_type": {},
            "bottlenecks": [],
            "strengths": [],
            "total_cost": 0.0,
            "avg_response_time": 0.0
        }
        
        total_scores = []
        total_cost = 0.0
        total_response_times = []
        
        for test_type, results in test_results.items():
            metrics = results.get("metrics", {})
            type_summary = {
                "success_rate": metrics.get("success_rate", 0.0),
                "avg_response_time": metrics.get("avg_response_time", 0.0),
                "cost": metrics.get("total_cost", 0.0),
                "threshold_status": {}
            }
            
            # Calculate type-specific score
            if test_type == "email_classification":
                type_score = (metrics.get("accuracy", 0.0) + metrics.get("avg_confidence", 0.0)) / 2
                type_summary["primary_metric"] = "accuracy"
                type_summary["primary_score"] = metrics.get("accuracy", 0.0)
                
                # Check thresholds
                thresholds = self.performance_thresholds["email_classification"]
                type_summary["threshold_status"] = {
                    "accuracy": metrics.get("accuracy", 0.0) >= thresholds["accuracy"],
                    "response_time": metrics.get("avg_response_time", 0.0) <= thresholds["response_time"],
                    "confidence": metrics.get("avg_confidence", 0.0) >= thresholds["confidence"]
                }
                
            elif test_type == "chat_response":
                type_score = (metrics.get("relevance", 0.0) + metrics.get("naturalness", 0.0)) / 2
                type_summary["primary_metric"] = "relevance"
                type_summary["primary_score"] = metrics.get("relevance", 0.0)
                
                thresholds = self.performance_thresholds["chat_response"]
                type_summary["threshold_status"] = {
                    "relevance": metrics.get("relevance", 0.0) >= thresholds["relevance"],
                    "response_time": metrics.get("avg_response_time", 0.0) <= thresholds["response_time"],
                    "naturalness": metrics.get("naturalness", 0.0) >= thresholds["naturalness"]
                }
                
            elif test_type == "task_extraction":
                type_score = metrics.get("f1_score", 0.0)
                type_summary["primary_metric"] = "f1_score"
                type_summary["primary_score"] = metrics.get("f1_score", 0.0)
                
                thresholds = self.performance_thresholds["task_extraction"]
                type_summary["threshold_status"] = {
                    "precision": metrics.get("precision", 0.0) >= thresholds["precision"],
                    "recall": metrics.get("recall", 0.0) >= thresholds["recall"],
                    "response_time": metrics.get("avg_response_time", 0.0) <= thresholds["response_time"]
                }
            
            summary["performance_by_type"][test_type] = type_summary
            total_scores.append(type_score)
            total_cost += metrics.get("total_cost", 0.0)
            if metrics.get("avg_response_time", 0.0) > 0:
                total_response_times.append(metrics.get("avg_response_time", 0.0))
        
        # Calculate overall metrics
        summary["overall_score"] = statistics.mean(total_scores) if total_scores else 0.0
        summary["total_cost"] = total_cost
        summary["avg_response_time"] = statistics.mean(total_response_times) if total_response_times else 0.0
        
        # Identify bottlenecks and strengths
        for test_type, type_summary in summary["performance_by_type"].items():
            if type_summary["primary_score"] < 0.7:
                summary["bottlenecks"].append(f"{test_type}: Low {type_summary['primary_metric']} ({type_summary['primary_score']:.2f})")
            elif type_summary["primary_score"] > 0.9:
                summary["strengths"].append(f"{test_type}: Excellent {type_summary['primary_metric']} ({type_summary['primary_score']:.2f})")
            
            if type_summary["avg_response_time"] > 8.0:
                summary["bottlenecks"].append(f"{test_type}: Slow response time ({type_summary['avg_response_time']:.2f}s)")
        
        return summary
    
    def _generate_optimization_recommendations(self, results: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate specific optimization recommendations based on test results"""
        recommendations = []
        performance_summary = results.get("performance_summary", {})
        
        # Analyze email classification performance
        email_perf = performance_summary.get("performance_by_type", {}).get("email_classification", {})
        if email_perf.get("primary_score", 0.0) < 0.85:
            recommendations.append({
                "type": "prompt_optimization",
                "priority": "high",
                "category": "email_classification",
                "issue": "Low classification accuracy",
                "recommendation": "Add more specific examples and clearer classification criteria to the email analysis prompt",
                "expected_improvement": "10-15% accuracy increase"
            })
        
        if email_perf.get("avg_response_time", 0.0) > 5.0:
            recommendations.append({
                "type": "performance_optimization",
                "priority": "medium",
                "category": "email_classification",
                "issue": "Slow response time",
                "recommendation": "Reduce prompt length and use Claude Haiku for simpler classifications",
                "expected_improvement": "30-40% response time reduction"
            })
        
        # Analyze chat response performance
        chat_perf = performance_summary.get("performance_by_type", {}).get("chat_response", {})
        if chat_perf.get("threshold_status", {}).get("naturalness", True) == False:
            recommendations.append({
                "type": "prompt_optimization",
                "priority": "medium",
                "category": "chat_response",
                "issue": "Unnatural response style",
                "recommendation": "Add more conversational examples and adjust system prompt for warmer tone",
                "expected_improvement": "20-25% naturalness improvement"
            })
        
        # Analyze task extraction performance
        task_perf = performance_summary.get("performance_by_type", {}).get("task_extraction", {})
        if task_perf.get("primary_score", 0.0) < 0.8:
            recommendations.append({
                "type": "prompt_optimization",
                "priority": "high",
                "category": "task_extraction",
                "issue": "Low task extraction accuracy",
                "recommendation": "Improve task definition examples and add negative examples to reduce false positives",
                "expected_improvement": "15-20% F1 score improvement"
            })
        
        # Cost optimization recommendations
        if performance_summary.get("total_cost", 0.0) > 1.0:  # Arbitrary threshold
            recommendations.append({
                "type": "cost_optimization",
                "priority": "medium",
                "category": "general",
                "issue": "High LLM costs",
                "recommendation": "Implement more aggressive model switching and prompt caching",
                "expected_improvement": "20-30% cost reduction"
            })
        
        # General performance recommendations
        avg_response_time = performance_summary.get("avg_response_time", 0.0)
        if avg_response_time > 7.0:
            recommendations.append({
                "type": "performance_optimization",
                "priority": "high",
                "category": "general",
                "issue": "Overall slow response times",
                "recommendation": "Implement parallel processing and prompt optimization across all components",
                "expected_improvement": "40-50% response time improvement"
            })
        
        return recommendations
    
    def _estimate_classification_cost(self, email_data: Dict[str, Any]) -> float:
        """Estimate cost for email classification"""
        text_length = len(email_data.get("body_text", "")) + len(email_data.get("subject", ""))
        estimated_tokens = text_length // 4  # Rough estimation
        return estimated_tokens * 0.00003  # Approximate GPT-4 cost per token
    
    def _estimate_chat_cost(self, message: str, response: str) -> float:
        """Estimate cost for chat response"""
        total_length = len(message) + len(response)
        estimated_tokens = total_length // 4
        return estimated_tokens * 0.00003
    
    def _estimate_task_extraction_cost(self, email_body: str) -> float:
        """Estimate cost for task extraction"""
        estimated_tokens = len(email_body) // 4
        return estimated_tokens * 0.00003
    
    async def _save_test_results(self, results: Dict[str, Any]):
        """Save test results to database for historical analysis"""
        try:
            # Save to Firestore
            test_results_ref = self.db_client.collection('prompt_test_results')
            doc_ref = test_results_ref.document(results["test_session_id"])
            
            # Convert datetime objects to strings for JSON serialization
            serializable_results = self._make_json_serializable(results)
            
            doc_ref.set(serializable_results)
            logger.info(f"Saved test results: {results['test_session_id']}")
            
        except Exception as e:
            logger.error(f"Error saving test results: {e}")
    
    def _make_json_serializable(self, obj):
        """Convert datetime objects to strings for JSON serialization"""
        if isinstance(obj, datetime):
            return obj.isoformat()
        elif isinstance(obj, dict):
            return {key: self._make_json_serializable(value) for key, value in obj.items()}
        elif isinstance(obj, list):
            return [self._make_json_serializable(item) for item in obj]
        else:
            return obj
    
    async def run_a_b_test(self, prompt_a: str, prompt_b: str, test_type: str, sample_size: int = 10) -> Dict[str, Any]:
        """
        Run A/B test between two prompt versions
        """
        logger.info(f"Starting A/B test for {test_type} with sample size {sample_size}")
        
        results = {
            "test_type": test_type,
            "prompt_a_results": [],
            "prompt_b_results": [],
            "comparison": {},
            "winner": None,
            "confidence": 0.0
        }
        
        # Get appropriate test cases
        if test_type == "email_classification":
            test_cases = self.email_classification_suite.test_cases[:sample_size]
        elif test_type == "chat_response":
            test_cases = self.chat_response_suite.test_cases[:sample_size]
        elif test_type == "task_extraction":
            test_cases = self.task_extraction_suite.test_cases[:sample_size]
        else:
            raise ValueError(f"Unknown test type: {test_type}")
        
        # Run tests for both prompts (simplified for demonstration)
        # In a real implementation, you would modify the prompts and run the actual tests
        
        return results

# Usage example
async def main():
    """Example usage of the prompt optimizer"""
    # This would be initialized with actual LLM manager, DB client, and config
    # optimizer = PromptOptimizer(llm_manager, db_client, config)
    # results = await optimizer.run_comprehensive_test_suite("v1.0")
    # print(json.dumps(results["performance_summary"], indent=2))
    pass

if __name__ == "__main__":
    asyncio.run(main())