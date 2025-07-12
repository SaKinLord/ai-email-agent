# -*- coding: utf-8 -*-
"""
Hybrid LLM System for Cost Optimization
Optimizes API usage based on available credits:
- GPT-4: $120/month budget - primary for reasoning and complex analysis
- Claude: $5/month budget - specific tasks requiring Anthropic's strengths
"""

import logging
try:
    import openai
except ImportError:
    openai = None
    logging.warning("OpenAI package not available. GPT features will be disabled.")

import anthropic
from typing import Dict, Any, Optional, Tuple, List
from datetime import datetime, timedelta
import json
import os
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception

def is_retryable_llm_error(exception):
    """
    Return True if the exception is a transient error that should be retried, False otherwise.
    
    This function implements intelligent retry logic:
    - Retry on server errors (5xx) from API providers
    - Do NOT retry on client errors (4xx) like authentication failures
    - Retry on network timeouts and connection issues
    - Do NOT retry on quota/rate limit errors (429) that need different handling
    
    Args:
        exception: The exception that was raised
        
    Returns:
        bool: True if the error should be retried, False if it should fail immediately
    """
    # Check for Anthropic API errors
    if hasattr(exception, '__class__') and 'anthropic' in str(exception.__class__):
        # For anthropic.APIStatusError, check the status code
        if hasattr(exception, 'status_code'):
            status_code = exception.status_code
            # Retry on server errors (500-599), fail immediately on client errors (400-499)
            if 400 <= status_code < 500:
                return False  # Client error - don't retry (auth, rate limit, etc.)
            elif status_code >= 500:
                return True   # Server error - retry
        # For anthropic.APITimeoutError and other timeout errors, retry
        if 'timeout' in str(exception.__class__).lower() or 'APITimeoutError' in str(exception.__class__):
            return True
    
    # Check for OpenAI API errors
    if openai and hasattr(exception, '__class__') and 'openai' in str(exception.__class__):
        # For openai.APIStatusError, check the status code
        if hasattr(exception, 'status_code'):
            status_code = exception.status_code
            # Retry on server errors (500-599), fail immediately on client errors (400-499)
            if 400 <= status_code < 500:
                return False  # Client error - don't retry
            elif status_code >= 500:
                return True   # Server error - retry
        # For openai.APITimeoutError and other timeout errors, retry
        if 'timeout' in str(exception.__class__).lower() or 'APITimeoutError' in str(exception.__class__):
            return True
    
    # For generic network errors and timeouts, retry
    if isinstance(exception, (TimeoutError, ConnectionError, OSError)):
        return True
    
    # For other exceptions, don't retry by default (they might be programming errors)
    return False

def get_user_friendly_error_message(exception, provider="LLM"):
    """
    Generate user-friendly error messages for non-retryable errors.
    
    Args:
        exception: The exception that was raised
        provider: The service provider ("Claude", "OpenAI", or "LLM")
        
    Returns:
        str: User-friendly error message
    """
    # Check for Anthropic API errors
    if hasattr(exception, '__class__') and 'anthropic' in str(exception.__class__):
        if hasattr(exception, 'status_code'):
            status_code = exception.status_code
            if status_code == 401:
                return f"Authentication Error: Please check your Claude API key. It appears to be invalid or expired."
            elif status_code == 403:
                return f"Permission Error: Your Claude API key doesn't have permission to access this resource."
            elif status_code == 429:
                return f"Rate Limit Error: Claude API rate limit exceeded. Please wait a moment and try again."
            elif 400 <= status_code < 500:
                return f"Claude API Error ({status_code}): {str(exception)}"
    
    # Check for OpenAI API errors
    if openai and hasattr(exception, '__class__') and 'openai' in str(exception.__class__):
        if hasattr(exception, 'status_code'):
            status_code = exception.status_code
            if status_code == 401:
                return f"Authentication Error: Please check your OpenAI API key. It appears to be invalid or expired."
            elif status_code == 403:
                return f"Permission Error: Your OpenAI API key doesn't have permission to access this resource."
            elif status_code == 429:
                return f"Rate Limit Error: OpenAI API rate limit exceeded. Please wait a moment and try again."
            elif 400 <= status_code < 500:
                return f"OpenAI API Error ({status_code}): {str(exception)}"
    
    # Generic error message for other cases
    return f"{provider} Error: {str(exception)}"

class HybridLLMManager:
    """
    Manages hybrid LLM usage to optimize costs while maintaining quality.
    Routes requests to the most appropriate model based on task type and budget.
    """
    
    def __init__(self, config: Dict[str, Any], openai_api_key: Optional[str] = None, anthropic_api_key: Optional[str] = None):
        self.config = config
        self.openai_api_key = openai_api_key
        self.anthropic_api_key = anthropic_api_key
        
        # Initialize clients
        self.openai_client = None
        self.anthropic_client = None
        
        # Budget tracking (simple in-memory for now, could be enhanced with persistent storage)
        self.monthly_usage = {
            'gpt': {'tokens': 0, 'cost': 0.0, 'requests': 0},
            'claude': {'tokens': 0, 'cost': 0.0, 'requests': 0}
        }
        
        # Cost per token (approximate)
        self.token_costs = {
            'gpt-4': {'input': 0.03/1000, 'output': 0.06/1000},  # GPT-4 pricing per 1K tokens
            'claude-3': {'input': 0.015/1000, 'output': 0.075/1000}  # Claude-3 pricing per 1K tokens
        }
        
        # Budget limits
        self.budget_limits = {
            'gpt': 120.0,  # $120/month
            'claude': 5.0   # $5/month
        }
        
        self._initialize_clients()
        
        # Debug logging
        logging.info(f"LLM Manager initialization complete:")
        logging.info(f"  - OpenAI client available: {self.openai_client is not None}")
        logging.info(f"  - Anthropic client available: {self.anthropic_client is not None}")
    
    def _initialize_clients(self):
        """Initialize LLM clients based on provided API keys"""
        try:
            # Initialize OpenAI client
            if openai is not None:
                if self.openai_api_key:
                    self.openai_client = openai.OpenAI(api_key=self.openai_api_key)
                    logging.info("OpenAI client initialized successfully")
                else:
                    logging.info("OpenAI API key not provided, OpenAI features disabled")
            else:
                logging.warning("OpenAI package not available, skipping OpenAI initialization")
            
            # Initialize Anthropic client
            if self.anthropic_api_key:
                self.anthropic_client = anthropic.Anthropic(api_key=self.anthropic_api_key)
                logging.info("Anthropic client initialized successfully")
            else:
                logging.info("Anthropic API key not provided, Anthropic features disabled")
                
        except Exception as e:
            logging.error(f"Error initializing LLM clients: {e}")
    
    def _estimate_tokens(self, text: str) -> int:
        """Rough estimation of token count (4 chars ≈ 1 token)"""
        return len(text) // 4
    
    def _check_budget_availability(self, provider: str, estimated_cost: float) -> bool:
        """Check if we have budget available for the request"""
        current_usage = self.monthly_usage[provider]['cost']
        budget_limit = self.budget_limits[provider]
        
        return (current_usage + estimated_cost) <= budget_limit
    
    def _log_usage(self, provider: str, tokens_used: int, cost: float):
        """Log usage for budget tracking"""
        self.monthly_usage[provider]['tokens'] += tokens_used
        self.monthly_usage[provider]['cost'] += cost
        self.monthly_usage[provider]['requests'] += 1
        
        logging.info(f"{provider.upper()} usage: {tokens_used} tokens, ${cost:.4f} cost")
    
    def choose_optimal_llm(self, task_type: str, text_length: int) -> Tuple[str, Any]:
        """
        Choose the optimal LLM for a given task based on:
        1. Task type suitability
        2. Available budget
        3. Cost efficiency
        
        Returns:
            Tuple of (provider_name, client_instance)
        """
        
        estimated_tokens = self._estimate_tokens(str(text_length))
        
        # Task-specific routing logic
        if task_type == 'email_analysis':
            # GPT-4 is primary for analysis due to better reasoning
            if self.openai_client:
                estimated_cost = estimated_tokens * self.token_costs['gpt-4']['input'] * 1.5  # Include output estimate
                if self._check_budget_availability('gpt', estimated_cost):
                    return 'gpt-4', self.openai_client
            
            # Fallback to Claude if GPT budget exhausted
            if self.anthropic_client:
                estimated_cost = estimated_tokens * self.token_costs['claude-3']['input'] * 1.5
                if self._check_budget_availability('claude', estimated_cost):
                    return 'claude-3', self.anthropic_client
        
        elif task_type == 'summarization':
            # GPT-4 preferred for summarization
            if self.openai_client:
                estimated_cost = estimated_tokens * self.token_costs['gpt-4']['input'] * 0.3  # Shorter output
                if self._check_budget_availability('gpt', estimated_cost):
                    return 'gpt-4', self.openai_client
            
            # Claude fallback
            if self.anthropic_client:
                estimated_cost = estimated_tokens * self.token_costs['claude-3']['input'] * 0.3
                if self._check_budget_availability('claude', estimated_cost):
                    return 'claude-3', self.anthropic_client
        
        elif task_type == 'response_generation':
            # Claude excels at response generation
            if self.anthropic_client:
                estimated_cost = estimated_tokens * self.token_costs['claude-3']['input'] * 2.0  # Longer output
                if self._check_budget_availability('claude', estimated_cost):
                    return 'claude-3', self.anthropic_client
            
            # GPT fallback
            if self.openai_client:
                estimated_cost = estimated_tokens * self.token_costs['gpt-4']['input'] * 2.0
                if self._check_budget_availability('gpt', estimated_cost):
                    return 'gpt-4', self.openai_client
        
        elif task_type == 'action_suggestions':
            # Use GPT-4 for structured action suggestions
            if self.openai_client:
                estimated_cost = estimated_tokens * self.token_costs['gpt-4']['input'] * 0.5
                if self._check_budget_availability('gpt', estimated_cost):
                    return 'gpt-4', self.openai_client
        
        # Ultimate fallback - prefer GPT due to larger budget
        if self.openai_client:
            return 'gpt-4', self.openai_client
        elif self.anthropic_client:
            return 'claude-3', self.anthropic_client
        else:
            raise Exception("No LLM clients available")
    
    def analyze_email_optimized(self, email_data: Dict[str, Any], config: Dict[str, Any], 
                               memory: Any = None) -> Optional[Dict[str, Any]]:
        """
        Optimized email analysis using the best available LLM within budget.
        """
        
        email_text = email_data.get('body_text', '')
        text_length = len(email_text)
        
        # Choose optimal LLM
        provider, client = self.choose_optimal_llm('email_analysis', text_length)
        
        # Prepare common analysis prompt
        analysis_prompt = self._create_analysis_prompt(email_data, config, memory)
        
        try:
            if provider.startswith('gpt'):
                return self._analyze_with_gpt(client, analysis_prompt, email_data, config)
            elif provider.startswith('claude'):
                return self._analyze_with_claude(client, analysis_prompt, email_data, config)
        
        except Exception as e:
            logging.error(f"Analysis failed with {provider}: {e}")
            
            # Try fallback provider
            if provider.startswith('gpt') and self.anthropic_client:
                try:
                    return self._analyze_with_claude(self.anthropic_client, analysis_prompt, email_data, config)
                except Exception as e2:
                    logging.error(f"Fallback analysis also failed: {e2}")
            
            return None
    
    def _create_analysis_prompt(self, email_data: Dict[str, Any], config: Dict[str, Any], 
                               memory: Any = None) -> str:
        """Create optimized analysis prompt using the new prompt templates."""
        
        from optimized_prompts import get_optimized_prompt
        
        # Get user context
        user_context = ""
        if memory:
            try:
                # Get basic user preferences without complex context generation
                prefs = memory.get_user_preferences()
                important_senders = prefs.get('email_preferences', {}).get('important_senders', [])
                if important_senders:
                    user_context = f"Important senders: {', '.join(important_senders[:5])}"
            except Exception as e:
                logging.warning(f"Failed to get user context: {e}")
        
        # Get positive feedback examples for personalized prioritization
        learned_priorities = []
        try:
            from task_utils import get_positive_feedback_examples
            positive_examples = get_positive_feedback_examples("default_user", limit=8)
            if positive_examples:
                learned_priorities = positive_examples
                logging.info(f"Personalized prioritization: Using {len(positive_examples)} positive examples")
        except Exception as e:
            logging.warning(f"Could not retrieve positive feedback for prioritization: {e}")
        
        # Use the optimized prompt template
        return get_optimized_prompt(
            "email_classification",
            email_data=email_data,
            user_context=user_context,
            learned_priorities=learned_priorities
        )
    
    @retry(
        retry=retry_if_exception(is_retryable_llm_error),  # Only retry on transient errors
        stop=stop_after_attempt(3),  # Try a total of 3 times
        wait=wait_exponential(multiplier=1, min=2, max=10)  # Wait 2s, then 4s, etc.
    )
    def _analyze_with_gpt(self, client, prompt: str, email_data: Dict[str, Any], 
                         config: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Analyze email using GPT-4 with automatic retry mechanism.
        
        This function includes automatic retries with exponential backoff for increased
        reliability when dealing with transient network errors or temporary service
        unavailability.
        """
        
        try:
            # The main prompt now contains all instructions, so a simple system message is sufficient.
            response = client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are an expert email analysis agent. Follow the user's instructions precisely and return only the requested JSON object."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=500,
                temperature=0.1
            )
            
            # Extract and parse response
            content = response.choices[0].message.content.strip()
            
            # Clean JSON if needed
            if content.startswith('```json'):
                content = content.replace('```json', '').replace('```', '').strip()
            
            result = json.loads(content)
            
            # Log usage
            tokens_used = response.usage.total_tokens
            cost = tokens_used * (self.token_costs['gpt-4']['input'] + self.token_costs['gpt-4']['output']) / 2
            self._log_usage('gpt', tokens_used, cost)
            
            logging.info(f"GPT-4 analysis successful: urgency={result.get('urgency_score')}, purpose={result.get('purpose')}")
            return result
            
        except json.JSONDecodeError as e:
            logging.error(f"Failed to parse GPT-4 response as JSON: {e}")
            return None
        except Exception as e:
            # Check if this is a non-retryable error
            if not is_retryable_llm_error(e):
                user_message = get_user_friendly_error_message(e, "OpenAI")
                logging.error(f"GPT-4 analysis failed with non-retryable error: {user_message}")
                return None
            else:
                # For retryable errors, re-raise to trigger retry mechanism
                logging.error(f"GPT-4 analysis error (will retry): {e}")
                raise e
    
    @retry(
        retry=retry_if_exception(is_retryable_llm_error),  # Only retry on transient errors
        stop=stop_after_attempt(3),  # Try a total of 3 times
        wait=wait_exponential(multiplier=1, min=2, max=10)  # Wait 2s, then 4s, etc.
    )
    def _analyze_with_claude(self, client, prompt: str, email_data: Dict[str, Any], 
                            config: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Analyze email using Claude with automatic retry mechanism.
        
        This function includes automatic retries with exponential backoff for increased
        reliability when dealing with transient network errors or temporary service
        unavailability.
        """
        
        try:
            message = client.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=500,
                temperature=0.1,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            
            # Extract and parse response
            content = message.content[0].text.strip()
            
            # Clean JSON if needed
            if content.startswith('```json'):
                content = content.replace('```json', '').replace('```', '').strip()
            
            result = json.loads(content)
            
            # Log usage (approximate)
            estimated_tokens = self._estimate_tokens(prompt + content)
            cost = estimated_tokens * (self.token_costs['claude-3']['input'] + self.token_costs['claude-3']['output']) / 2
            self._log_usage('claude', estimated_tokens, cost)
            
            logging.info(f"Claude analysis successful: urgency={result.get('urgency_score')}, purpose={result.get('purpose')}")
            return result
            
        except json.JSONDecodeError as e:
            logging.error(f"Failed to parse Claude response as JSON: {e}")
            return None
        except Exception as e:
            # Check if this is a non-retryable error
            if not is_retryable_llm_error(e):
                user_message = get_user_friendly_error_message(e, "Claude")
                logging.error(f"Claude analysis failed with non-retryable error: {user_message}")
                return None
            else:
                # For retryable errors, re-raise to trigger retry mechanism
                logging.error(f"Claude analysis error (will retry): {e}")
                raise e
    
    def summarize_email_optimized(self, email_data: Dict[str, Any], config: Dict[str, Any],
                                 summary_type: str = "standard") -> Optional[str]:
        """
        Optimized email summarization using the best available LLM within budget.
        """
        
        email_text = email_data.get('body_text', '')
        if not email_text:
            return "No email content to summarize."
        
        text_length = len(email_text)
        provider, client = self.choose_optimal_llm('summarization', text_length)
        
        # Create summarization prompt
        summary_prompt = self._create_summary_prompt(email_data, summary_type)
        
        try:
            if provider.startswith('gpt'):
                return self._summarize_with_gpt(client, summary_prompt)
            elif provider.startswith('claude'):
                return self._summarize_with_claude(client, summary_prompt)
        
        except Exception as e:
            logging.error(f"Summarization failed with {provider}: {e}")
            return f"Summarization failed: {str(e)}"
    
    def _create_summary_prompt(self, email_data: Dict[str, Any], summary_type: str) -> str:
        """Create optimized summary prompt"""
        
        email_text = email_data.get('body_text', '')
        sender = email_data.get('sender', '')
        subject = email_data.get('subject', '')
        
        if summary_type == "brief":
            instruction = "Provide a 1-2 sentence summary focusing only on the most critical information."
        elif summary_type == "detailed":
            instruction = "Provide a comprehensive summary including all key points, context, and action items."
        else:  # standard
            instruction = "Provide a clear, concise summary of the main points and any action items."
        
        prompt = f"""Email from {sender}
Subject: {subject}

{email_text[:3000]}{'...' if len(email_text) > 3000 else ''}

{instruction} Do not include introductory phrases - provide only the summary content."""
        
        return prompt
    
    @retry(
        retry=retry_if_exception(is_retryable_llm_error),  # Only retry on transient errors
        stop=stop_after_attempt(3),  # Try a total of 3 times
        wait=wait_exponential(multiplier=1, min=2, max=10)  # Wait 2s, then 4s, etc.
    )
    def _summarize_with_gpt(self, client, prompt: str) -> Optional[str]:
        """
        Summarize using GPT-4 with automatic retry mechanism.
        
        This function includes automatic retries with exponential backoff for increased
        reliability when dealing with transient network errors or temporary service
        unavailability.
        """
        try:
            response = client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are an expert at creating clear, concise email summaries."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=300,
                temperature=0.1
            )
            
            summary = response.choices[0].message.content.strip()
            
            # Log usage
            tokens_used = response.usage.total_tokens
            cost = tokens_used * (self.token_costs['gpt-4']['input'] + self.token_costs['gpt-4']['output']) / 2
            self._log_usage('gpt', tokens_used, cost)
            
            return summary
            
        except Exception as e:
            # Check if this is a non-retryable error
            if not is_retryable_llm_error(e):
                user_message = get_user_friendly_error_message(e, "OpenAI")
                logging.error(f"GPT-4 summarization failed with non-retryable error: {user_message}")
                return None
            else:
                # For retryable errors, re-raise to trigger retry mechanism
                logging.error(f"GPT-4 summarization error (will retry): {e}")
                raise e
    
    @retry(
        retry=retry_if_exception(is_retryable_llm_error),  # Only retry on transient errors
        stop=stop_after_attempt(3),  # Try a total of 3 times
        wait=wait_exponential(multiplier=1, min=2, max=10)  # Wait 2s, then 4s, etc.
    )
    def _summarize_with_claude(self, client, prompt: str) -> Optional[str]:
        """
        Summarize using Claude with automatic retry mechanism.
        
        This function includes automatic retries with exponential backoff for increased
        reliability when dealing with transient network errors or temporary service
        unavailability.
        """
        try:
            message = client.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=300,
                temperature=0.1,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            
            summary = message.content[0].text.strip()
            
            # Log usage
            estimated_tokens = self._estimate_tokens(prompt + summary)
            cost = estimated_tokens * (self.token_costs['claude-3']['input'] + self.token_costs['claude-3']['output']) / 2
            self._log_usage('claude', estimated_tokens, cost)
            
            return summary
            
        except Exception as e:
            # Check if this is a non-retryable error
            if not is_retryable_llm_error(e):
                user_message = get_user_friendly_error_message(e, "Claude")
                logging.error(f"Claude summarization failed with non-retryable error: {user_message}")
                return None
            else:
                # For retryable errors, re-raise to trigger retry mechanism
                logging.error(f"Claude summarization error (will retry): {e}")
                raise e
    
    @retry(
        retry=retry_if_exception(is_retryable_llm_error),  # Only retry on transient errors
        stop=stop_after_attempt(3),  # Try a total of 3 times
        wait=wait_exponential(multiplier=1, min=2, max=10)  # Wait 2s, then 4s, etc.
    )
    def summarize_email_bodies(self, emails: List[Dict[str, str]]) -> str:
        """
        Generate concise, action-oriented summaries for email content with automatic retry mechanism.
        
        This function includes automatic retries with exponential backoff for increased
        reliability when dealing with transient network errors or temporary service
        unavailability.
        
        Args:
            emails: List of email dictionaries with 'subject' and 'body' keys
            
        Returns:
            Formatted Markdown string with summaries and action items
        """
        if not emails:
            return "No emails provided for summarization."
        
        try:
            # Construct the prompt for email content summarization
            system_prompt = "You are an elite executive assistant named Maia. Your goal is to read the user's emails and provide a concise, action-oriented summary to save them time."
            
            user_prompt = f"""Please review the following emails and provide a summary for each.

**Emails to Summarize:**
```json
{json.dumps(emails, indent=2)}
```

**Your Task:**
For each email, provide:
- A 1-2 sentence summary of its main point.
- A clear "Call to Action" (e.g., "Reply Needed", "FYI", "Decision Required").

**Output Format (Use Markdown):**

## Email Summaries

### Subject: [Email 1 Subject]
**Summary:** [Your 1-2 sentence summary of email 1]  
**Action:** [Identified call to action for email 1]

### Subject: [Email 2 Subject]
**Summary:** [Your 1-2 sentence summary of email 2]  
**Action:** [Identified call to action for email 2]

Continue this pattern for all provided emails."""
            
            # Use Claude for email summarization (more cost-effective for this task)
            if not self.anthropic_client:
                logging.error("Anthropic client not available for email summarization")
                return "Email summarization unavailable: Anthropic client not initialized."
            
            # Check budget availability
            estimated_cost = len(json.dumps(emails)) * 0.00001  # Rough estimate
            if not self._check_budget_availability('claude', estimated_cost):
                logging.warning("Claude budget exceeded, email summarization unavailable")
                return "Email summarization unavailable: Budget limit reached for this month."
            
            # Make the API call
            message = self.anthropic_client.messages.create(
                model="claude-3-haiku-20240307",  # Use Haiku for cost efficiency
                max_tokens=800,  # Allow for longer summaries of multiple emails
                temperature=0.1,  # Low temperature for consistent, factual summaries
                system=system_prompt,
                messages=[
                    {"role": "user", "content": user_prompt}
                ]
            )
            
            summary = message.content[0].text.strip()
            
            # Log usage for budget tracking
            estimated_tokens = self._estimate_tokens(user_prompt + summary)
            cost = estimated_tokens * (self.token_costs['claude-3']['input'] + self.token_costs['claude-3']['output']) / 2
            self._log_usage('claude', estimated_tokens, cost)
            
            logging.info(f"Successfully summarized {len(emails)} emails using Claude")
            return summary
            
        except Exception as e:
            # Check if this is a non-retryable error that should provide user-friendly message
            if not is_retryable_llm_error(e):
                user_message = get_user_friendly_error_message(e, "Claude")
                logging.error(f"Email summarization failed with non-retryable error: {user_message}")
                return f"Email summarization unavailable: {user_message}"
            else:
                # For retryable errors, log and re-raise to trigger retry mechanism
                logging.error(f"Email summarization error (will retry): {e}")
                raise e
    
    @retry(
        retry=retry_if_exception(is_retryable_llm_error),  # Only retry on transient errors
        stop=stop_after_attempt(3),  # Try a total of 3 times
        wait=wait_exponential(multiplier=1, min=2, max=10)  # Wait 2s, then 4s, etc.
    )
    def extract_tasks_from_email(self, email_body: str, email_subject: str) -> Optional[List[Dict[str, Any]]]:
        """
        Extract actionable tasks from an email using AI analysis with dynamic learning.
        
        This function analyzes email content to identify explicit and implicit tasks,
        deadlines, and stakeholders, returning them as structured, actionable items.
        Uses negative feedback examples to improve accuracy over time.
        
        Args:
            email_body: The body text of the email
            email_subject: The subject line of the email
            
        Returns:
            List of task dictionaries with task_description, deadline, and stakeholders,
            or None if extraction fails due to an error
        """
        
        if not email_body or not email_subject:
            return []
        
        try:
            # PHASE 6.1: Get negative feedback examples for dynamic learning
            negative_examples = []
            try:
                from task_utils import get_negative_feedback_examples
                negative_examples = get_negative_feedback_examples("default_user", limit=15)
                logging.info(f"Dynamic learning: Using {len(negative_examples)} negative examples")
            except Exception as e:
                logging.warning(f"Could not retrieve negative feedback examples: {e}")
                # Continue without learning examples
            
            # Use optimized task extraction prompt
            from optimized_prompts import get_optimized_prompt
            
            user_prompt = get_optimized_prompt(
                "task_extraction",
                email_subject=email_subject,
                email_body=email_body,
                negative_examples=negative_examples
            )
            
            system_prompt = "You are a hyper-efficient productivity analyst. Your sole purpose is to read an email and extract actionable tasks into a structured JSON format. If no tasks are found, you must return an empty JSON array `[]`."

            # Choose optimal LLM for task extraction (prefer GPT-4 for complex reasoning)
            text_length = len(email_body)
            provider, client = self.choose_optimal_llm('email_analysis', text_length)
            
            # Use GPT-4 for task extraction if available (better at structured reasoning)
            if provider.startswith('gpt') and self.openai_client:
                response = self.openai_client.chat.completions.create(
                    model="gpt-4",
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    max_tokens=1000,  # Allow more tokens for multiple tasks
                    temperature=0.1   # Low temperature for consistent, structured output
                )
                
                content = response.choices[0].message.content.strip()
                
                # Log usage
                tokens_used = response.usage.total_tokens
                cost = tokens_used * (self.token_costs['gpt-4']['input'] + self.token_costs['gpt-4']['output']) / 2
                self._log_usage('gpt', tokens_used, cost)
                
            elif provider.startswith('claude') and self.anthropic_client:
                message = self.anthropic_client.messages.create(
                    model="claude-3-haiku-20240307",  # Use Sonnet for better reasoning
                    max_tokens=1000,
                    temperature=0.1,
                    system=system_prompt,
                    messages=[
                        {"role": "user", "content": user_prompt}
                    ]
                )
                
                content = message.content[0].text.strip()
                
                # Log usage
                estimated_tokens = self._estimate_tokens(user_prompt + content)
                cost = estimated_tokens * (self.token_costs['claude-3']['input'] + self.token_costs['claude-3']['output']) / 2
                self._log_usage('claude', estimated_tokens, cost)
            
            else:
                logging.error("No LLM client available for task extraction")
                return None
            
            # Clean JSON if needed (remove markdown code blocks)
            if content.startswith('```json'):
                content = content.replace('```json', '').replace('```', '').strip()
            elif content.startswith('```'):
                content = content.replace('```', '').strip()
            
            # Parse the JSON response
            try:
                tasks = json.loads(content)
                
                # Validate that it's a list
                if not isinstance(tasks, list):
                    logging.warning(f"Task extraction returned non-list: {type(tasks)}")
                    return None
                
                # Validate each task object
                validated_tasks = []
                for task in tasks:
                    if isinstance(task, dict) and 'task_description' in task:
                        # Ensure required fields exist with proper defaults
                        validated_task = {
                            'task_description': str(task.get('task_description', '')),
                            'deadline': task.get('deadline', None),
                            'stakeholders': task.get('stakeholders', [])
                        }
                        
                        # Ensure stakeholders is a list
                        if not isinstance(validated_task['stakeholders'], list):
                            validated_task['stakeholders'] = []
                        
                        validated_tasks.append(validated_task)
                
                logging.info(f"Successfully extracted {len(validated_tasks)} tasks from email")
                return validated_tasks
                
            except json.JSONDecodeError as e:
                logging.error(f"Failed to parse task extraction JSON response: {e}")
                logging.error(f"Raw response: {content[:500]}...")
                return None
                
        except Exception as e:
            # Check if this is a non-retryable error
            if not is_retryable_llm_error(e):
                user_message = get_user_friendly_error_message(e, "Task Extraction")
                logging.error(f"Task extraction failed with non-retryable error: {user_message}")
                return None
            else:
                # For retryable errors, re-raise to trigger retry mechanism
                logging.error(f"Task extraction error (will retry): {e}")
                raise e
    
    @retry(
        retry=retry_if_exception(is_retryable_llm_error),  # Only retry on transient errors
        stop=stop_after_attempt(3),  # Try a total of 3 times
        wait=wait_exponential(multiplier=1, min=2, max=10)  # Wait 2s, then 4s, etc.
    )
    def generate_reply_suggestions(self, email_content: str, user_style_examples: List[str] = None) -> List[str]:
        """
        Generate contextual reply suggestions for an email using LLM analysis.
        
        This function analyzes the email content and generates 2-3 relevant, contextual
        reply options that the user can choose from for quick responses.
        
        Args:
            email_content: The email body text to analyze
            user_style_examples: Optional list of user writing style examples for personalization
            
        Returns:
            List of reply suggestion strings (usually 2-3 options)
        """
        try:
            # Choose optimal LLM for this task (Claude Haiku is good for quick tasks)
            llm_choice = self.choose_optimal_llm(task_type='response_generation', text_length=500)
            
            # Create the prompt for generating reply suggestions
            prompt = self._create_reply_suggestions_prompt(email_content, user_style_examples)
            
            if llm_choice == 'gpt':
                return self._generate_replies_with_gpt(prompt)
            else:
                return self._generate_replies_with_claude(prompt)
                
        except Exception as e:
            # Check if this is a non-retryable error
            if not is_retryable_llm_error(e):
                user_message = get_user_friendly_error_message(e, "LLM")
                logging.error(f"Reply generation failed with non-retryable error: {user_message}")
                return ["Thanks for your email!", "I'll get back to you soon.", "Noted, thank you."]  # Fallback responses
            else:
                # For retryable errors, re-raise to trigger retry mechanism
                logging.error(f"Reply generation error (will retry): {e}")
                raise e
    
    def _create_reply_suggestions_prompt(self, email_content: str, user_style_examples: List[str] = None) -> str:
        """Create the prompt for reply suggestion generation"""
        
        style_context = ""
        if user_style_examples:
            style_context = f"\n\nUser Writing Style Examples:\n" + "\n".join([f"- {example}" for example in user_style_examples[:3]])
        
        prompt = f"""Analyze the following email content. Your task is to generate 2-3 contextually appropriate reply suggestions.

Email Content:
{email_content}
{style_context}

**CRITICAL REQUIREMENT:**
Your output MUST be a single, valid JSON array of strings and NOTHING else. Do not include any explanation, introduction, or any text outside of the JSON array.

**Good Example (Correct Format):**
["Thanks for the update! I will review this.", "Got it, thank you.", "I'll get back to you on this shortly."]

**Bad Example (Incorrect Format):**
Based on the email, here are some suggestions: ["Suggestion 1"]

Now, generate the reply suggestions based on the email content.
**JSON Array Output Only:**"""

        return prompt
    
    def _generate_replies_with_gpt(self, prompt: str) -> List[str]:
        """Generate reply suggestions using GPT"""
        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a helpful assistant that generates professional email reply suggestions. Always respond with valid JSON arrays of strings."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=300,
                temperature=0.7
            )
            
            reply_text = response.choices[0].message.content.strip()
            
            # Guard clause: Check if reply_text is empty or invalid before parsing JSON
            if not reply_text or reply_text.strip() == "":
                logging.warning("GPT returned an empty string for reply suggestions. Skipping.")
                return []
            
            # Parse JSON response
            try:
                replies = json.loads(reply_text)
                if isinstance(replies, list) and all(isinstance(r, str) for r in replies):
                    # Log usage
                    estimated_tokens = self._estimate_tokens(prompt + reply_text)
                    cost = estimated_tokens * (self.token_costs['gpt-3.5-turbo']['input'] + self.token_costs['gpt-3.5-turbo']['output']) / 2
                    self._log_usage('gpt', estimated_tokens, cost)
                    
                    return replies[:3]  # Limit to 3 suggestions
                else:
                    raise ValueError("Invalid JSON format")
            except json.JSONDecodeError as e:
                logging.warning(f"GPT returned a non-JSON string for reply suggestions: {reply_text[:100]}")
                return []  # Return an empty list gracefully
            except ValueError as e:
                logging.warning(f"GPT returned invalid JSON format for reply suggestions: {e}")
                return []  # Return an empty list gracefully
                
        except Exception as e:
            # Check if this is a non-retryable error
            if not is_retryable_llm_error(e):
                user_message = get_user_friendly_error_message(e, "GPT")
                logging.error(f"GPT reply generation failed with non-retryable error: {user_message}")
                return None
            else:
                # For retryable errors, re-raise to trigger retry mechanism
                logging.error(f"GPT reply generation error (will retry): {e}")
                raise e
    
    def _generate_replies_with_claude(self, prompt: str) -> List[str]:
        """Generate reply suggestions using Claude"""
        try:
            message = self.anthropic_client.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=300,
                temperature=0.7,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            
            reply_text = message.content[0].text.strip()
            
            # Guard clause: Check if reply_text is empty or invalid before parsing JSON
            if not reply_text or reply_text.strip() == "":
                logging.warning("Claude returned an empty string for reply suggestions. Skipping.")
                return []
            
            # Parse JSON response
            try:
                replies = json.loads(reply_text)
                if isinstance(replies, list) and all(isinstance(r, str) for r in replies):
                    # Log usage
                    estimated_tokens = self._estimate_tokens(prompt + reply_text)
                    cost = estimated_tokens * (self.token_costs['claude-3']['input'] + self.token_costs['claude-3']['output']) / 2
                    self._log_usage('claude', estimated_tokens, cost)
                    
                    return replies[:3]  # Limit to 3 suggestions
                else:
                    raise ValueError("Invalid JSON format")
            except json.JSONDecodeError as e:
                logging.warning(f"Claude returned a non-JSON string for reply suggestions: {reply_text[:100]}")
                return []  # Return an empty list gracefully
            except ValueError as e:
                logging.warning(f"Claude returned invalid JSON format for reply suggestions: {e}")
                return []  # Return an empty list gracefully
                
        except Exception as e:
            # Check if this is a non-retryable error
            if not is_retryable_llm_error(e):
                user_message = get_user_friendly_error_message(e, "Claude")
                logging.error(f"Claude reply generation failed with non-retryable error: {user_message}")
                return None
            else:
                # For retryable errors, re-raise to trigger retry mechanism
                logging.error(f"Claude reply generation error (will retry): {e}")
                raise e
    
    def _extract_fallback_replies(self, text: str) -> List[str]:
        """Extract reply suggestions from malformed text as fallback"""
        # Look for quoted strings or bullet points
        import re
        
        # Try to find quoted strings
        quoted_pattern = r'"([^"]*)"'
        quoted_matches = re.findall(quoted_pattern, text)
        
        if quoted_matches and len(quoted_matches) >= 2:
            return [match.strip() for match in quoted_matches[:3] if len(match.strip()) > 5]
        
        # Try to find bullet points or numbered lists
        bullet_pattern = r'(?:[-*•]|\d+\.)\s*(.+?)(?=\n|$)'
        bullet_matches = re.findall(bullet_pattern, text, re.MULTILINE)
        
        if bullet_matches and len(bullet_matches) >= 2:
            return [match.strip() for match in bullet_matches[:3] if len(match.strip()) > 5]
        
        # Fallback to generic responses
        return [
            "Thanks for your email!",
            "I'll review this and get back to you.",
            "Noted, thank you for the update."
        ]

    def get_usage_stats(self) -> Dict[str, Any]:
        """Get current usage statistics"""
        stats = {
            'gpt': {
                'usage': self.monthly_usage['gpt'],
                'budget_remaining': self.budget_limits['gpt'] - self.monthly_usage['gpt']['cost'],
                'usage_percentage': (self.monthly_usage['gpt']['cost'] / self.budget_limits['gpt']) * 100
            },
            'claude': {
                'usage': self.monthly_usage['claude'],
                'budget_remaining': self.budget_limits['claude'] - self.monthly_usage['claude']['cost'],
                'usage_percentage': (self.monthly_usage['claude']['cost'] / self.budget_limits['claude']) * 100
            }
        }
        
        return stats

    # === PHASE 9: AGENDA SYNTHESIS ===
    
    def synthesize_agenda_summary(self, emails: List[Dict], tasks: List[Dict], events: List[Dict]) -> Optional[Dict]:
        """
        Synthesize daily agenda from emails, tasks, and calendar events using AI.
        Acts as a 'digital chief of staff' to create personalized agenda summaries.
        
        Args:
            emails: List of critical/high priority emails
            tasks: List of urgent tasks  
            events: List of calendar events for today
            
        Returns:
            Dict containing structured agenda summary or None if failed
        """
        try:
            # Determine which LLM to use for agenda synthesis
            # This is a complex reasoning task, so prefer GPT-4 if budget allows
            prompt_length = self._estimate_agenda_prompt_length(emails, tasks, events)
            provider, client = self.choose_optimal_llm('reasoning', prompt_length)
            
            logging.info(f"Synthesizing agenda with {provider} (estimated tokens: {prompt_length})")
            
            # Create comprehensive agenda synthesis prompt
            agenda_prompt = self._create_agenda_synthesis_prompt(emails, tasks, events)
            
            # Generate synthesis based on chosen provider
            if provider.startswith('gpt'):
                return self._synthesize_agenda_with_gpt(client, agenda_prompt)
            elif provider.startswith('claude'):
                return self._synthesize_agenda_with_claude(client, agenda_prompt)
            else:
                logging.error(f"Unknown provider for agenda synthesis: {provider}")
                return None
                
        except Exception as e:
            logging.error(f"Error during agenda synthesis: {e}", exc_info=True)
            return None
    
    def _estimate_agenda_prompt_length(self, emails: List[Dict], tasks: List[Dict], events: List[Dict]) -> int:
        """Estimate token count for agenda synthesis prompt"""
        # Base prompt (~500 tokens) + data content
        base_tokens = 500
        
        # Estimate tokens from data
        email_tokens = sum(len(str(email.get('subject', '') + email.get('body_snippet', ''))) // 4 for email in emails)
        task_tokens = sum(len(str(task.get('description', ''))) // 4 for task in tasks)
        event_tokens = sum(len(str(event.get('title', '') + event.get('description', ''))) // 4 for event in events)
        
        return base_tokens + email_tokens + task_tokens + event_tokens
    
    def _create_agenda_synthesis_prompt(self, emails: List[Dict], tasks: List[Dict], events: List[Dict]) -> str:
        """Create comprehensive prompt for agenda synthesis"""
        
        # Format current date
        from datetime import datetime
        today = datetime.now().strftime("%A, %B %d, %Y")
        
        # Build data sections
        email_section = self._format_emails_for_prompt(emails)
        task_section = self._format_tasks_for_prompt(tasks)
        event_section = self._format_events_for_prompt(events)
        
        prompt = f"""You are an expert AI assistant acting as a digital chief of staff. Your task is to synthesize today's agenda from multiple data sources into a personalized, actionable summary.

Today is {today}.

DATA TO SYNTHESIZE:

CRITICAL/HIGH PRIORITY EMAILS (last 24 hours):
{email_section}

URGENT TASKS (overdue or due today):
{task_section}

TODAY'S CALENDAR EVENTS:
{event_section}

INSTRUCTIONS:
1. Act as a professional chief of staff who understands priorities and context
2. Identify the main themes and focus areas for the day
3. Highlight the most critical items that need immediate attention
4. Provide actionable context for each agenda item
5. Use a warm but professional tone

OUTPUT FORMAT (JSON):
Return ONLY a valid JSON object with this exact structure:
{{
  "greeting": "A warm, personalized greeting for the day",
  "key_highlight": "1-2 sentences identifying the main focus/theme for today",
  "agenda_items": [
    {{"type": "meeting", "time": "10:00 AM", "title": "Meeting Title", "context": "Why this meeting matters today"}},
    {{"type": "email", "priority": "CRITICAL", "subject": "Email Subject", "context": "What action is needed"}},
    {{"type": "task", "priority": "OVERDUE", "description": "Task description", "context": "Why this is urgent"}}
  ],
  "closing_remark": "An encouraging or motivational closing statement"
}}

CRITICAL REQUIREMENTS:
- Maximum 6 agenda items total
- Prioritize by urgency and importance
- Include actionable context for each item
- Keep descriptions concise but informative
- Return ONLY valid JSON, no other text"""

        return prompt
    
    def _format_emails_for_prompt(self, emails: List[Dict]) -> str:
        """Format emails for prompt inclusion"""
        if not emails:
            return "No critical emails in the last 24 hours."
        
        formatted = []
        for email in emails:
            sender = email.get('sender', 'Unknown')
            subject = email.get('subject', 'No Subject')
            priority = email.get('priority', 'MEDIUM')
            snippet = email.get('body_snippet', '')[:150] + '...' if email.get('body_snippet') else ''
            
            formatted.append(f"- {priority}: '{subject}' from {sender}\n  Preview: {snippet}")
        
        return '\n'.join(formatted)
    
    def _format_tasks_for_prompt(self, tasks: List[Dict]) -> str:
        """Format tasks for prompt inclusion"""
        if not tasks:
            return "No urgent tasks."
        
        formatted = []
        for task in tasks:
            description = task.get('description', 'No Description')
            priority = task.get('priority', 'medium').upper()
            deadline = task.get('deadline', '')
            overdue_status = " (OVERDUE)" if task.get('is_overdue') else ""
            
            formatted.append(f"- {priority}{overdue_status}: {description}")
            if deadline:
                formatted.append(f"  Deadline: {deadline}")
        
        return '\n'.join(formatted)
    
    def _format_events_for_prompt(self, events: List[Dict]) -> str:
        """Format calendar events for prompt inclusion"""
        if not events:
            return "No calendar events scheduled for today."
        
        formatted = []
        for event in events:
            title = event.get('title', 'No Title')
            time = event.get('time', 'Unknown Time')
            location = event.get('location', '')
            
            event_line = f"- {time}: {title}"
            if location:
                event_line += f" (at {location})"
            
            formatted.append(event_line)
        
        return '\n'.join(formatted)
    
    @retry(
        retry=retry_if_exception(is_retryable_llm_error),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    def _synthesize_agenda_with_gpt(self, client, prompt: str) -> Optional[Dict]:
        """Synthesize agenda using GPT-4"""
        try:
            response = client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are an expert digital chief of staff who synthesizes daily agendas."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=800,
                temperature=0.3
            )
            
            synthesis_text = response.choices[0].message.content.strip()
            
            # Parse JSON response
            try:
                agenda_data = json.loads(synthesis_text)
                
                # Log usage
                tokens_used = response.usage.total_tokens
                cost = tokens_used * (self.token_costs['gpt-4']['input'] + self.token_costs['gpt-4']['output']) / 2
                self._log_usage('gpt', tokens_used, cost)
                
                logging.info("Successfully synthesized agenda with GPT-4")
                return agenda_data
                
            except json.JSONDecodeError as e:
                logging.error(f"Failed to parse GPT-4 agenda JSON: {e}")
                return self._create_fallback_agenda()
                
        except Exception as e:
            if not is_retryable_llm_error(e):
                user_message = get_user_friendly_error_message(e, "GPT")
                logging.error(f"GPT-4 agenda synthesis failed: {user_message}")
                return None
            else:
                logging.error(f"GPT-4 agenda synthesis error (will retry): {e}")
                raise e
    
    @retry(
        retry=retry_if_exception(is_retryable_llm_error),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    def _synthesize_agenda_with_claude(self, client, prompt: str) -> Optional[Dict]:
        """Synthesize agenda using Claude"""
        try:
            message = client.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=800,
                temperature=0.3,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            
            synthesis_text = message.content[0].text.strip()
            
            # Parse JSON response
            try:
                agenda_data = json.loads(synthesis_text)
                
                # Log usage
                estimated_tokens = self._estimate_tokens(prompt + synthesis_text)
                cost = estimated_tokens * (self.token_costs['claude-3']['input'] + self.token_costs['claude-3']['output']) / 2
                self._log_usage('claude', estimated_tokens, cost)
                
                logging.info("Successfully synthesized agenda with Claude")
                return agenda_data
                
            except json.JSONDecodeError as e:
                logging.error(f"Failed to parse Claude agenda JSON: {e}")
                return self._create_fallback_agenda()
                
        except Exception as e:
            if not is_retryable_llm_error(e):
                user_message = get_user_friendly_error_message(e, "Claude")
                logging.error(f"Claude agenda synthesis failed: {user_message}")
                return None
            else:
                logging.error(f"Claude agenda synthesis error (will retry): {e}")
                raise e
    
    def _create_fallback_agenda(self) -> Dict:
        """Create a fallback agenda when AI synthesis fails"""
        from datetime import datetime
        
        return {
            "greeting": "Good morning! Here's your agenda overview for today.",
            "key_highlight": "I've gathered your priority items, though I had some difficulty with the full analysis.",
            "agenda_items": [
                {
                    "type": "general", 
                    "priority": "HIGH", 
                    "title": "Review Priority Items", 
                    "context": "Please check your dashboard for critical emails and urgent tasks."
                }
            ],
            "closing_remark": "Have a productive day!"
        }


# Factory function for easy integration
def create_hybrid_llm_manager(config: Dict[str, Any], openai_api_key: Optional[str] = None, anthropic_api_key: Optional[str] = None) -> HybridLLMManager:
    """Create and configure hybrid LLM manager with provided API keys"""
    return HybridLLMManager(config, openai_api_key=openai_api_key, anthropic_api_key=anthropic_api_key)