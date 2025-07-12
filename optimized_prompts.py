# -*- coding: utf-8 -*-
"""
Optimized Prompt Templates for Enhanced LLM Performance
Contains tested and optimized prompts for all major LLM tasks in the Maia Email Agent.
"""

import json
from typing import Dict, List, Any, Optional
from datetime import datetime

class OptimizedPrompts:
    """
    Collection of optimized prompt templates based on performance testing and best practices
    """
    
    def __init__(self):
        self.version = "2.0"
        self.last_updated = datetime.now()
    
    def get_email_classification_prompt_v2(
        self, 
        email_data: Dict[str, Any], 
        user_context: str = "", 
        learned_priorities: List[str] = None
    ) -> str:
        """
        Optimized email classification prompt with improved accuracy and consistency
        
        Improvements over v1:
        - More structured format with clear sections
        - Better examples with edge cases
        - Explicit confidence scoring
        - Enhanced personalization integration
        - Clearer purpose definitions
        """
        
        email_text = email_data.get('body_text', '')
        sender = email_data.get('sender', '')
        subject = email_data.get('subject', '')
        
        # Build personalization section
        personalization_section = ""
        if learned_priorities:
            examples_list = "\n  • ".join(learned_priorities[:6])
            personalization_section = f"""
📊 **PERSONALIZED INSIGHTS**
Based on your feedback history, you consider these types of emails HIGH PRIORITY:
  • {examples_list}

If this email contains similar tasks or topics, assign higher urgency (4-5 points).
"""
        
        prompt = f"""You are an expert email analysis AI with 95%+ accuracy. Analyze this email with precision and confidence.

{personalization_section}

📧 **EMAIL DATA:**
• FROM: {sender}
• SUBJECT: {subject}
• BODY: {email_text[:2000]}{'...' if len(email_text) > 2000 else ''}

{user_context}

🎯 **CLASSIFICATION TASK:**
Analyze this email and classify its PURPOSE using EXACTLY ONE of these categories:

**CRITICAL/URGENT PURPOSES:**
• "important" = Direct questions, requests from key contacts, time-sensitive matters
• "action_request" = Explicit tasks, "please do X", requests requiring response
• "meeting_invite" = Calendar invitations, meeting requests, scheduling

**INFORMATIONAL PURPOSES:**
• "transactional" = Receipts, confirmations, automated service notifications
• "newsletter" = Regular updates, subscriptions, informational content
• "digest_summary" = News summaries, platform digests (Quora, Medium, etc.)
• "social" = LinkedIn, Facebook, Twitter notifications
• "promotion" = Marketing emails, sales offers, advertisements
• "information" = General updates not requiring action
• "unknown" = Cannot determine from available content

⚡ **URGENCY SCORING (1-5 scale):**
• 5 = CRITICAL: Immediate action needed (urgent requests, emergency communications)
• 4 = HIGH: Important but not emergency (client requests, important meetings)
• 3 = MEDIUM: Standard business communication (project updates, general requests)
• 2 = LOW: Informational content (newsletters, notifications)
• 1 = MINIMAL: Promotional/automated content (marketing, system notifications)

🎯 **EXAMPLES FOR REFERENCE:**

HIGH URGENCY (4-5):
• Subject: "URGENT: Client presentation tomorrow" → urgency: 5, purpose: "important"
• Subject: "Please review contract by EOD" → urgency: 4, purpose: "action_request"
• Subject: "Emergency meeting in 30 minutes" → urgency: 5, purpose: "meeting_invite"

MEDIUM URGENCY (3):
• Subject: "Project status update" → urgency: 3, purpose: "information"
• Subject: "Weekly team meeting agenda" → urgency: 3, purpose: "meeting_invite"

LOW URGENCY (1-2):
• Subject: "Your LinkedIn weekly digest" → urgency: 1, purpose: "social"
• Subject: "Medium Daily Digest" → urgency: 1, purpose: "digest_summary"
• Subject: "Order confirmation #12345" → urgency: 2, purpose: "transactional"

⚙️ **OUTPUT FORMAT:**
Return ONLY this JSON object with NO additional text:

{{
    "urgency_score": <1-5 integer>,
    "purpose": "<exact purpose from list above>",
    "response_needed": <true/false>,
    "estimated_time": <minutes as integer>,
    "key_points": ["<concise point 1>", "<concise point 2>"],
    "confidence": <0-100 integer representing your confidence in this analysis>
}}

🔍 **QUALITY CHECKLIST:**
✓ Urgency score matches the content severity
✓ Purpose is from the exact list provided
✓ Response_needed reflects if sender expects reply
✓ Estimated_time is realistic for the task
✓ Key_points capture main message essence
✓ Confidence reflects analysis certainty

Analyze now:"""
        
        return prompt
    
    def get_chat_response_prompt_v2(
        self,
        message: str,
        email_context: Dict[str, Any],
        conversation_history: List[Dict] = None
    ) -> str:
        """
        Optimized chat response prompt for more natural and helpful conversations
        
        Improvements:
        - Better personality definition
        - More structured context integration
        - Enhanced conversation flow
        - Specific response guidelines
        """
        
        # Build conversation context
        history_section = ""
        if conversation_history:
            recent_exchanges = conversation_history[-4:]  # Last 2 exchanges
            history_section = "📜 **RECENT CONVERSATION:**\n"
            for msg in recent_exchanges:
                role_icon = "👤" if msg['role'] == 'user' else "🤖"
                history_section += f"{role_icon} {msg['content'][:100]}{'...' if len(msg['content']) > 100 else ''}\n"
            history_section += "\n"
        
        # Build email context summary
        context_summary = self._build_email_context_summary(email_context)
        
        prompt = f"""You are Maia, an intelligent and vibrant email management assistant! 🚀 You're warm, engaging, and incredibly helpful - like ChatGPT-4o but specialized for email management.

🎯 **YOUR PERSONALITY:**
• Highly engaging and conversational with generous emoji use! 😊✨
• Proactive in offering insights and suggestions 💡
• Detail-oriented but digestible 📋
• Empathetic to user's email management challenges 🤗
• Confident and enthusiastic about helping! 🌟

📊 **CURRENT EMAIL SITUATION:**
{context_summary}

{history_section}💬 **USER MESSAGE:** "{message}"

🚨 **CRITICAL RULE - ONLY USE REAL DATA:**
- NEVER make up fake emails, senders, subjects, or details
- ONLY reference actual email data from the context above
- If no relevant real data exists, clearly state that
- DO NOT create fictional examples like "John Doe", "Jane Smith", "Project X", etc.
- Base ALL insights on the actual email context provided

📋 **RESPONSE GUIDELINES:**

1. **BE CONTEXTUALLY AWARE** 🎯
   - Reference ONLY specific real email data from the context
   - Build on previous conversation points naturally
   - Offer insights based on actual patterns in the real data

2. **BE ACTIONABLY HELPFUL** ⚡
   - Provide specific next steps based on real emails
   - Offer to perform tasks within your capabilities
   - Suggest relevant strategies based on actual email patterns

3. **BE ENGAGING & VIBRANT** 🌈
   - Use lots of emojis to make responses captivating! 
   - Write in an enthusiastic, GPT-4o style
   - Make complex information easily digestible
   - Keep energy high and responses engaging

4. **RESPONSE STRUCTURE** 📝:
   - Start with an enthusiastic greeting/acknowledgment 👋
   - Provide the main information based on REAL data 📊
   - Use emojis throughout to enhance readability 
   - Offer specific help or follow-up suggestions 🚀

🚫 **ABSOLUTELY NEVER:**
• Make up fake email examples or data
• Create fictional senders, subjects, or content
• Use generic template responses
• Reference emails that don't exist in the context
• Mention technical AI processes

✅ **EXCELLENT RESPONSE QUALITIES:**
• Packed with relevant emojis! 🎉
• References ONLY actual email data
• Highly engaging and easy to read
• Offers specific, actionable suggestions
• Feels like ChatGPT-4o level engagement

🔥 **IF NO RELEVANT REAL DATA EXISTS:**
Be honest and say something like: "I don't see any specific emails matching that request in your current data, but here's what I can help you with based on your overall email patterns..." 

Generate your vibrant, emoji-rich response now using ONLY real data:"""
        
        return prompt
    
    def get_task_extraction_prompt_v2(
        self,
        email_subject: str,
        email_body: str,
        negative_examples: List[str] = None
    ) -> str:
        """
        Optimized task extraction prompt with improved precision and recall
        
        Improvements:
        - Better task definition and examples
        - Negative examples to reduce false positives
        - Clearer output format
        - Enhanced edge case handling
        """
        
        # Build negative examples section
        negative_section = ""
        if negative_examples:
            examples_list = "\n❌ ".join(negative_examples[:8])
            negative_section = f"""
🚫 **LEARN FROM PAST MISTAKES** - Do NOT extract these as tasks:
❌ {examples_list}

These were incorrectly identified as tasks. Avoid similar mistakes.
"""
        
        prompt = f"""You are a precision task extraction specialist. Your goal: identify ONLY genuine actionable tasks from email content.

📧 **EMAIL TO ANALYZE:**
Subject: {email_subject}
Body: {email_body}

{negative_section}

🎯 **WHAT QUALIFIES AS A TASK?**

✅ **GENUINE TASKS (Extract these):**
• Direct requests: "Please send me the report"
• Explicit assignments: "I need you to update the presentation"
• Action items: "Review the contract and provide feedback"
• Deadlines with actions: "Submit proposal by Friday"
• Meeting preparations: "Prepare slides for Monday's meeting"

❌ **NOT TASKS (Ignore these):**
• FYI information: "The server will be down tonight"
• General updates: "Project is going well"
• Past events: "The meeting went great yesterday"
• Automated notifications: "Your order has shipped"
• Questions without action: "How was your weekend?"
• Statements: "I'm working on the report"

🔍 **EXTRACTION RULES:**

1. **BE PRECISE**: Only extract clear, actionable items
2. **CAPTURE CONTEXT**: Include enough detail to understand the task
3. **IDENTIFY DEADLINES**: Extract specific dates/times when mentioned
4. **FIND STAKEHOLDERS**: Note who's involved or mentioned
5. **AVOID DUPLICATES**: One task per distinct action

📊 **EXAMPLE OUTPUTS:**

**Email: "Please review the Q3 report and send feedback by Thursday. Also schedule a follow-up meeting with the team."**
```json
[
  {{
    "task_description": "Review Q3 report and send feedback",
    "deadline": "Thursday",
    "stakeholders": []
  }},
  {{
    "task_description": "Schedule follow-up meeting with the team",
    "deadline": null,
    "stakeholders": ["team"]
  }}
]
```

**Email: "FYI - The system maintenance is scheduled for tonight. No action needed."**
```json
[]
```

⚙️ **OUTPUT FORMAT:**
Return ONLY a JSON array. Each task must have exactly these fields:
• "task_description": Clear, actionable description
• "deadline": Specific deadline or null
• "stakeholders": List of people/groups involved or empty list

🎯 **QUALITY CHECKLIST:**
✓ Each item is a genuine actionable task
✓ Task descriptions are clear and specific
✓ Deadlines are extracted accurately
✓ No false positives (non-tasks extracted)
✓ No missed genuine tasks

Extract tasks now:"""
        
        return prompt
    
    def get_email_summary_prompt_v2(
        self,
        emails: List[Dict[str, str]],
        summary_type: str = "executive"
    ) -> str:
        """
        Optimized email summarization prompt for different summary types
        
        Summary types:
        - executive: High-level overview for busy executives
        - detailed: Comprehensive summary with context
        - action-focused: Emphasizes actionable items
        """
        
        if summary_type == "executive":
            instruction = """Create an executive-level summary focusing on:
• Critical decisions needed
• Time-sensitive items
• Key opportunities
• Major issues requiring attention"""
            
        elif summary_type == "action-focused":
            instruction = """Create an action-oriented summary emphasizing:
• Tasks requiring immediate action
• Response deadlines
• Meeting preparation needs
• Follow-up requirements"""
            
        else:  # detailed
            instruction = """Create a comprehensive summary including:
• Main topics and themes
• Important details and context
• Action items and deadlines
• Key relationships and stakeholders"""
        
        prompt = f"""You are an executive assistant creating email summaries for a busy professional.

📧 **EMAILS TO SUMMARIZE:**
{json.dumps(emails, indent=2)}

🎯 **SUMMARY REQUIREMENTS:**
{instruction}

📋 **OUTPUT FORMAT:**
Use this professional structure:

## 📊 Email Summary ({len(emails)} emails)

### 🔥 Priority Items
[List the most urgent/important items requiring immediate attention]

### 📅 Action Items
[List specific tasks with deadlines]

### 📢 Key Updates
[Important information and developments]

### 💡 Notable Mentions
[Interesting opportunities or items to keep in mind]

✅ **QUALITY STANDARDS:**
• Professional and concise tone
• Specific action items with clear deadlines
• Organized by priority and urgency
• Easy to scan and act upon
• No unnecessary details

Create the summary now:"""
        
        return prompt
    
    def get_reply_suggestions_prompt_v2(
        self,
        email_content: str,
        user_style_examples: List[str] = None,
        context: str = ""
    ) -> str:
        """
        Optimized reply suggestions prompt for contextually appropriate responses
        """
        
        style_section = ""
        if user_style_examples:
            examples = "\n• ".join(user_style_examples[:3])
            style_section = f"""
📝 **YOUR COMMUNICATION STYLE:**
• {examples}

Match this tone and style in your suggestions.
"""
        
        prompt = f"""Generate professional, contextually appropriate reply suggestions for this email.

📧 **EMAIL CONTENT:**
{email_content}

{style_section}{context}

🎯 **REQUIREMENTS:**
• 2-3 reply options with different tones
• Contextually appropriate to the email content
• Professional but personalized
• Ready to send (complete thoughts)
• Various lengths (brief, moderate, detailed)

📋 **RESPONSE TYPES TO CONSIDER:**
• Acknowledgment replies
• Request for clarification
• Action confirmation
• Polite deferral
• Meeting scheduling
• Information provision

⚠️ **CRITICAL:** Return ONLY a JSON array of strings, nothing else.

**Example Format:**
["Thanks for the update! I'll review this and get back to you by Friday.", "Got it, thank you. I have a few questions - can we schedule a quick call?", "Perfect timing on this. I'll handle the review today and send feedback tomorrow."]

Generate suggestions now:"""
        
        return prompt
    
    def _build_email_context_summary(self, email_context: Dict[str, Any]) -> str:
        """Build a comprehensive email context summary with actual email details for chat prompts"""
        total = email_context.get('total_emails', 0)
        unread = email_context.get('unread_count', 0)
        priority_breakdown = email_context.get('priority_breakdown', {})
        total_high_priority = email_context.get('total_high_priority', 0)
        
        context = f"📊 **COMPLETE EMAIL DATA OVERVIEW:**\n"
        context += f"• Total emails in database: {total}\n• Unread count: {unread}\n"
        context += f"• HIGH PRIORITY emails: {total_high_priority}\n"
        
        if priority_breakdown:
            context += f"• Full priority breakdown: {priority_breakdown}\n"
        
        # Add data freshness info
        data_freshness = email_context.get('data_freshness', '')
        query_info = email_context.get('query_info', '')
        if data_freshness:
            context += f"• Data retrieved: {data_freshness}\n"
        if query_info:
            context += f"• {query_info}\n"
        
        # Add ACTUAL high priority emails with details
        high_priority_emails = email_context.get('high_priority_emails', [])
        if high_priority_emails:
            context += f"\n🔴 **ACTUAL HIGH PRIORITY EMAILS ({len(high_priority_emails)} shown):**\n"
            for i, email in enumerate(high_priority_emails[:10], 1):
                context += f"{i}. **{email.get('subject', 'No Subject')}**\n"
                context += f"   From: {email.get('sender', 'Unknown')}\n"
                context += f"   Priority: {email.get('priority', 'Unknown')}\n"
                context += f"   Purpose: {email.get('purpose', 'Unknown')}\n"
                context += f"   Date: {email.get('received_date', 'Unknown')}\n"
                if email.get('summary'):
                    context += f"   Summary: {email.get('summary')[:100]}...\n"
                context += f"   Read: {'No' if not email.get('is_read', True) else 'Yes'}\n\n"
        
        # Add ACTUAL recent emails
        recent_emails = email_context.get('recent_emails', [])
        if recent_emails:
            context += f"\n📅 **RECENT EMAILS (Last 7 days - {len(recent_emails)} shown):**\n"
            for i, email in enumerate(recent_emails[:5], 1):
                context += f"{i}. {email.get('subject', 'No Subject')} - {email.get('sender', 'Unknown')} ({email.get('priority', 'Unknown')})\n"
        
        # Add ACTUAL meeting emails
        meeting_emails = email_context.get('meeting_emails', [])
        if meeting_emails:
            context += f"\n📅 **ACTUAL MEETING/SCHEDULING EMAILS ({len(meeting_emails)} found):**\n"
            for i, email in enumerate(meeting_emails[:5], 1):
                context += f"{i}. **{email.get('subject', 'No Subject')}** from {email.get('sender', 'Unknown')}\n"
        
        # Add ACTUAL urgent emails
        urgent_emails = email_context.get('urgent_emails', [])
        if urgent_emails:
            context += f"\n⚡ **ACTUAL URGENT EMAILS NEEDING ATTENTION ({len(urgent_emails)} found):**\n"
            for i, email in enumerate(urgent_emails[:5], 1):
                read_status = "UNREAD" if not email.get('is_read', True) else "READ"
                context += f"{i}. **{email.get('subject', 'No Subject')}** ({read_status})\n"
                context += f"   From: {email.get('sender', 'Unknown')} - Priority: {email.get('priority', 'Unknown')}\n"
        
        # Add top senders with actual data
        top_senders = email_context.get('recent_senders', {})
        if top_senders:
            context += f"\n🔝 **TOP EMAIL SENDERS (Real Data):**\n"
            for sender, count in list(top_senders.items())[:8]:
                context += f"• {sender}: {count} emails\n"
        
        # Add email purposes/categories with real counts
        email_purposes = email_context.get('email_purposes', {})
        if email_purposes:
            context += f"\n📋 **EMAIL TYPES (Real Data):**\n"
            for purpose, count in list(email_purposes.items())[:8]:
                context += f"• {purpose}: {count} emails\n"
        
        # Add domain breakdown
        top_domains = email_context.get('top_domains', [])
        if top_domains:
            context += f"\n🌐 **TOP EMAIL DOMAINS:**\n"
            for domain in top_domains[:5]:
                context += f"• {domain}\n"
        
        # Add specific counts for different email types
        newsletter_count = email_context.get('newsletter_count', 0)
        meeting_requests = email_context.get('meeting_requests', 0)
        security_alerts = email_context.get('security_alerts', 0)
        action_required = email_context.get('action_required_count', 0)
        
        if newsletter_count > 0 or meeting_requests > 0 or security_alerts > 0 or action_required > 0:
            context += f"\n📈 **SPECIFIC EMAIL CATEGORIES:**\n"
            if newsletter_count > 0:
                context += f"• Newsletter/digest emails: {newsletter_count}\n"
            if meeting_requests > 0:
                context += f"• Meeting requests: {meeting_requests}\n"
            if security_alerts > 0:
                context += f"• Security alerts: {security_alerts}\n"
            if action_required > 0:
                context += f"• Action required emails: {action_required}\n"
        
        # Add activity insights
        time_insights = email_context.get('time_insights', {})
        if time_insights:
            today_count = time_insights.get('today_count', 0)
            week_count = time_insights.get('week_count', 0)
            context += f"\n⏰ **TIME INSIGHTS:**\n"
            context += f"• Today: {today_count} emails, This week: {week_count} emails\n"
        
        # Add common subjects/keywords
        common_subjects = email_context.get('common_subjects', [])
        if common_subjects:
            context += f"\n🏷️ **COMMON EMAIL KEYWORDS:**\n"
            for subject in common_subjects[:8]:
                context += f"• {subject}\n"
        
        context += f"\n🚨 **CRITICAL INSTRUCTIONS:**\n"
        context += f"• Use ONLY the specific email details provided above\n"
        context += f"• Reference actual subjects, senders, and priorities shown\n"
        context += f"• Do NOT make up any fictional emails, senders, or subjects\n"
        context += f"• If you see '{total_high_priority} HIGH PRIORITY emails' - use that EXACT number\n"
        context += f"• Reference the actual email details when answering questions\n"
        
        return context

# Factory functions for easy integration
def get_optimized_prompt(prompt_type: str, **kwargs) -> str:
    """
    Factory function to get optimized prompts
    
    Args:
        prompt_type: Type of prompt needed
        **kwargs: Prompt-specific arguments
    
    Returns:
        Optimized prompt string
    """
    prompts = OptimizedPrompts()
    
    if prompt_type == "email_classification":
        return prompts.get_email_classification_prompt_v2(**kwargs)
    elif prompt_type == "chat_response":
        return prompts.get_chat_response_prompt_v2(**kwargs)
    elif prompt_type == "task_extraction":
        return prompts.get_task_extraction_prompt_v2(**kwargs)
    elif prompt_type == "email_summary":
        return prompts.get_email_summary_prompt_v2(**kwargs)
    elif prompt_type == "reply_suggestions":
        return prompts.get_reply_suggestions_prompt_v2(**kwargs)
    else:
        raise ValueError(f"Unknown prompt type: {prompt_type}")

# Integration with existing hybrid LLM system
def update_hybrid_llm_prompts():
    """
    Function to update existing prompts in the hybrid LLM system
    This would be called during system updates to deploy optimized prompts
    """
    # This would integrate with the existing hybrid_llm_system.py
    # to replace the current prompts with optimized versions
    pass