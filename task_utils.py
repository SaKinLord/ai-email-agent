# -*- coding: utf-8 -*-
"""
Task Management Utilities for Maia Email Agent
Handles task persistence, retrieval, and management in Firestore
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional
from database_utils import get_db
from google.cloud import firestore
from google.cloud.firestore_v1.base_query import FieldFilter

def save_task_to_firestore(task_data: Dict[str, Any], user_id: str, source_email_id: str) -> str:
    """
    Save an extracted task to Firestore.
    
    Args:
        task_data: Dictionary containing task_description, deadline, stakeholders
        user_id: ID of the user who owns this task
        source_email_id: ID of the email this task was extracted from
        
    Returns:
        str: The ID of the newly created task document
        
    Raises:
        Exception: If the save operation fails
    """
    try:
        # Prepare the task document
        task_document = {
            'user_id': user_id,
            'source_email_id': source_email_id,
            'task_description': task_data.get('task_description', ''),
            'deadline': task_data.get('deadline', None),
            'stakeholders': task_data.get('stakeholders', []),
            'status': 'pending',  # Default status
            'created_at': datetime.now(timezone.utc),
            'updated_at': datetime.now(timezone.utc),
            'completed_at': None,
            'creation_method': task_data.get('creation_method', 'manual')  # Track how task was created
        }
        
        # Save to the 'tasks' collection
        doc_ref = get_db().collection('tasks').add(task_document)
        task_id = doc_ref[1].id
        
        logging.info(f"Task saved successfully with ID: {task_id}")
        return task_id
        
    except Exception as e:
        logging.error(f"Failed to save task to Firestore: {e}")
        raise Exception(f"Task save failed: {str(e)}")

def get_tasks_for_user(user_id: str, status_filter: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Retrieve all tasks for a specific user from Firestore.
    
    Args:
        user_id: ID of the user
        status_filter: Optional status filter ('pending', 'completed', None for all)
        
    Returns:
        List of task dictionaries with document IDs included
    """
    try:
        # Query the tasks collection
        query = get_db().collection('tasks').where(filter=FieldFilter('user_id', '==', user_id))
        
        # Apply status filter if specified
        if status_filter:
            query = query.where(filter=FieldFilter('status', '==', status_filter))
        
        # Order by creation date (newest first)
        query = query.order_by('created_at', direction='DESCENDING')
        
        # Execute query
        docs = query.get()
        
        tasks = []
        for doc in docs:
            task_data = doc.to_dict()
            task_data['id'] = doc.id  # Include document ID
            tasks.append(task_data)
        
        logging.info(f"Retrieved {len(tasks)} tasks for user {user_id}")
        return tasks
        
    except Exception as e:
        logging.error(f"Failed to retrieve tasks for user {user_id}: {e}")
        return []

def update_task_status(task_id: str, new_status: str) -> bool:
    """
    Update the status of a task in Firestore.
    
    Args:
        task_id: ID of the task document to update
        new_status: New status ('pending', 'completed', 'cancelled')
        
    Returns:
        bool: True if update was successful, False otherwise
    """
    try:
        # Prepare update data
        update_data = {
            'status': new_status,
            'updated_at': datetime.now(timezone.utc)
        }
        
        # Add completion timestamp if marking as completed
        if new_status == 'completed':
            update_data['completed_at'] = datetime.now(timezone.utc)
        
        # Update the document
        get_db().collection('tasks').document(task_id).update(update_data)
        
        logging.info(f"Task {task_id} status updated to {new_status}")
        return True
        
    except Exception as e:
        logging.error(f"Failed to update task {task_id} status: {e}")
        return False

def delete_task(task_id: str) -> bool:
    """
    Delete a task from Firestore.
    
    Args:
        task_id: ID of the task document to delete
        
    Returns:
        bool: True if deletion was successful, False otherwise
    """
    try:
        get_db().collection('tasks').document(task_id).delete()
        logging.info(f"Task {task_id} deleted successfully")
        return True
        
    except Exception as e:
        logging.error(f"Failed to delete task {task_id}: {e}")
        return False

def get_task_by_id(task_id: str) -> Optional[Dict[str, Any]]:
    """
    Retrieve a specific task by its ID.
    
    Args:
        task_id: ID of the task document
        
    Returns:
        Task dictionary with ID included, or None if not found
    """
    try:
        doc = get_db().collection('tasks').document(task_id).get()
        
        if doc.exists:
            task_data = doc.to_dict()
            task_data['id'] = doc.id
            return task_data
        else:
            logging.warning(f"Task {task_id} not found")
            return None
            
    except Exception as e:
        logging.error(f"Failed to retrieve task {task_id}: {e}")
        return None

def get_tasks_by_source_email(source_email_id: str, user_id: str) -> List[Dict[str, Any]]:
    """
    Get all tasks extracted from a specific email.
    
    Args:
        source_email_id: ID of the source email
        user_id: ID of the user (for security)
        
    Returns:
        List of task dictionaries
    """
    try:
        query = get_db().collection('tasks').where(filter=FieldFilter('source_email_id', '==', source_email_id)).where(filter=FieldFilter('user_id', '==', user_id))
        docs = query.get()
        
        tasks = []
        for doc in docs:
            task_data = doc.to_dict()
            task_data['id'] = doc.id
            tasks.append(task_data)
        
        return tasks
        
    except Exception as e:
        logging.error(f"Failed to retrieve tasks for email {source_email_id}: {e}")
        return []

def get_task_stats(user_id: str) -> Dict[str, int]:
    """
    Get task statistics for a user.
    
    Args:
        user_id: ID of the user
        
    Returns:
        Dictionary with task counts by status
    """
    try:
        all_tasks = get_tasks_for_user(user_id)
        
        stats = {
            'total': len(all_tasks),
            'pending': 0,
            'completed': 0,
            'with_deadline': 0,
            'overdue': 0
        }
        
        now = datetime.now(timezone.utc)
        
        for task in all_tasks:
            status = task.get('status', 'pending')
            if status == 'pending':
                stats['pending'] += 1
            elif status == 'completed':
                stats['completed'] += 1
            
            # Check for deadlines
            deadline = task.get('deadline')
            if deadline:
                stats['with_deadline'] += 1
                
                # Parse deadline and check if overdue
                try:
                    if isinstance(deadline, str):
                        from dateutil import parser
                        deadline_dt = parser.parse(deadline)
                        if deadline_dt.tzinfo is None:
                            deadline_dt = deadline_dt.replace(tzinfo=timezone.utc)
                        
                        if deadline_dt < now and status == 'pending':
                            stats['overdue'] += 1
                except Exception:
                    pass  # Skip invalid date formats
        
        return stats
        
    except Exception as e:
        logging.error(f"Failed to get task stats for user {user_id}: {e}")
        return {'total': 0, 'pending': 0, 'completed': 0, 'with_deadline': 0, 'overdue': 0}

def is_task_already_saved(task_description: str, source_email_id: str, user_id: str) -> bool:
    """
    Check if a task with the same description from the same email is already saved.
    
    Args:
        task_description: Description of the task to check
        source_email_id: ID of the source email
        user_id: ID of the user
        
    Returns:
        bool: True if task already exists, False otherwise
    """
    try:
        query = get_db().collection('tasks').where(filter=FieldFilter('user_id', '==', user_id)).where(filter=FieldFilter('source_email_id', '==', source_email_id)).where(filter=FieldFilter('task_description', '==', task_description))
        docs = query.get()
        
        return len(docs) > 0
        
    except Exception as e:
        logging.error(f"Failed to check if task already exists: {e}")
        return False  # Return False on error to allow saving

def get_recent_autonomous_tasks(user_id: str, hours: int = 24) -> List[Dict[str, Any]]:
    """
    Get recent autonomous tasks created within the specified time period.
    
    Args:
        user_id: ID of the user
        hours: Number of hours to look back (default 24)
        
    Returns:
        List of recent autonomous task dictionaries with id included
    """
    try:
        # Calculate the cutoff time
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
        
        # Query for recent autonomous tasks
        query = (get_db().collection('tasks')
                .where(filter=FieldFilter('user_id', '==', user_id))
                .where(filter=FieldFilter('creation_method', '==', 'autonomous'))
                .where(filter=FieldFilter('created_at', '>=', cutoff_time))
                .order_by('created_at', direction=firestore.Query.DESCENDING))
        
        docs = query.get()
        
        tasks = []
        for doc in docs:
            task_data = doc.to_dict()
            task_data['id'] = doc.id
            tasks.append(task_data)
        
        return tasks
        
    except Exception as e:
        logging.error(f"Failed to retrieve recent autonomous tasks for user {user_id}: {e}")
        return []

# === PHASE 6: TASK FEEDBACK SYSTEM ===

def submit_task_feedback(task_id: str, user_id: str, feedback_type: str, comments: Optional[str] = None) -> str:
    """
    Submit feedback for an autonomous task to enable AI learning and improvement.
    
    Args:
        task_id: ID of the task being reviewed
        user_id: ID of the user providing feedback
        feedback_type: Type of feedback ('positive', 'negative', 'negative_implicit_delete')
        comments: Optional additional comments from the user
        
    Returns:
        str: The ID of the newly created feedback document
        
    Raises:
        Exception: If the feedback submission fails
    """
    try:
        # Get the original task to store context
        task_doc = get_db().collection('tasks').document(task_id).get()
        
        if not task_doc.exists:
            raise Exception(f"Task {task_id} not found")
        
        task_data = task_doc.to_dict()
        
        # Prepare the feedback document
        feedback_document = {
            'task_id': task_id,
            'user_id': user_id,
            'feedback_type': feedback_type,
            'comments': comments,
            'timestamp': datetime.now(timezone.utc),
            'task_description': task_data.get('task_description', ''),
            'task_creation_method': task_data.get('creation_method', 'unknown'),
            'source_email_id': task_data.get('source_email_id', ''),
            'task_deadline': task_data.get('deadline'),
            'task_stakeholders': task_data.get('stakeholders', []),
            'processed': False  # For future ML processing
        }
        
        # Save to the 'task_feedback' collection
        doc_ref = get_db().collection('task_feedback').add(feedback_document)
        feedback_id = doc_ref[1].id
        
        logging.info(f"Task feedback submitted successfully with ID: {feedback_id}")
        logging.info(f"Feedback details - Task: {task_id}, Type: {feedback_type}, User: {user_id}")
        
        return feedback_id
        
    except Exception as e:
        logging.error(f"Failed to submit task feedback: {e}")
        raise Exception(f"Task feedback submission failed: {str(e)}")

def get_feedback_for_task(task_id: str) -> Optional[Dict[str, Any]]:
    """
    Get existing feedback for a specific task.
    
    Args:
        task_id: ID of the task to check
        
    Returns:
        Dict containing feedback data if found, None otherwise
    """
    try:
        query = get_db().collection('task_feedback').where(filter=FieldFilter('task_id', '==', task_id)).limit(1)
        docs = query.get()
        
        for doc in docs:
            feedback_data = doc.to_dict()
            feedback_data['id'] = doc.id
            return feedback_data
        
        return None
        
    except Exception as e:
        logging.error(f"Failed to retrieve feedback for task {task_id}: {e}")
        return None

def has_feedback_been_submitted(task_id: str) -> bool:
    """
    Check if feedback has already been submitted for a task.
    
    Args:
        task_id: ID of the task to check
        
    Returns:
        bool: True if feedback exists, False otherwise
    """
    try:
        query = get_db().collection('task_feedback').where(filter=FieldFilter('task_id', '==', task_id)).limit(1)
        docs = query.get()
        
        return len(docs) > 0
        
    except Exception as e:
        logging.error(f"Failed to check feedback status for task {task_id}: {e}")
        return False  # Return False on error to allow feedback submission

def get_feedback_statistics(user_id: str, days: int = 30) -> Dict[str, Any]:
    """
    Get feedback statistics for learning insights.
    
    Args:
        user_id: ID of the user
        days: Number of days to look back
        
    Returns:
        Dict containing feedback statistics
    """
    try:
        # Calculate the cutoff time
        cutoff_time = datetime.now(timezone.utc) - timedelta(days=days)
        
        # Query for recent feedback
        query = (get_db().collection('task_feedback')
                .where(filter=FieldFilter('user_id', '==', user_id))
                .where(filter=FieldFilter('timestamp', '>=', cutoff_time)))
        
        docs = query.get()
        
        stats = {
            'total_feedback': 0,
            'positive_feedback': 0,
            'negative_feedback': 0,
            'implicit_deletes': 0,
            'accuracy_rate': 0.0,
            'feedback_by_type': {},
            'recent_feedback': []
        }
        
        for doc in docs:
            feedback_data = doc.to_dict()
            feedback_type = feedback_data.get('feedback_type', 'unknown')
            
            stats['total_feedback'] += 1
            
            if feedback_type == 'positive':
                stats['positive_feedback'] += 1
            elif feedback_type == 'negative':
                stats['negative_feedback'] += 1
            elif feedback_type == 'negative_implicit_delete':
                stats['implicit_deletes'] += 1
            
            # Count by type
            if feedback_type in stats['feedback_by_type']:
                stats['feedback_by_type'][feedback_type] += 1
            else:
                stats['feedback_by_type'][feedback_type] = 1
            
            # Add to recent feedback list
            stats['recent_feedback'].append({
                'task_description': feedback_data.get('task_description', ''),
                'feedback_type': feedback_type,
                'timestamp': feedback_data.get('timestamp'),
                'comments': feedback_data.get('comments')
            })
        
        # Calculate accuracy rate
        if stats['total_feedback'] > 0:
            stats['accuracy_rate'] = stats['positive_feedback'] / stats['total_feedback']
        
        return stats
        
    except Exception as e:
        logging.error(f"Failed to get feedback statistics for user {user_id}: {e}")
        return {'total_feedback': 0, 'positive_feedback': 0, 'negative_feedback': 0, 
                'implicit_deletes': 0, 'accuracy_rate': 0.0, 'feedback_by_type': {}, 'recent_feedback': []}

def mark_task_as_incorrect_and_archive(task_id: str, user_id: str) -> bool:
    """
    Mark a task as incorrect and archive it instead of deleting.
    Used when user provides negative feedback.
    
    Args:
        task_id: ID of the task to archive
        user_id: ID of the user (for verification)
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Update the task status to archived_incorrect
        task_ref = get_db().collection('tasks').document(task_id)
        task_ref.update({
            'status': 'archived_incorrect',
            'updated_at': datetime.now(timezone.utc),
            'archived_by': user_id,
            'archived_reason': 'negative_feedback'
        })
        
        logging.info(f"Task {task_id} marked as incorrect and archived")
        return True
        
    except Exception as e:
        logging.error(f"Failed to archive incorrect task {task_id}: {e}")
        return False

def delete_task_with_implicit_feedback(task_id: str, user_id: str) -> bool:
    """
    Delete a task and capture implicit feedback if it was autonomously created.
    
    Args:
        task_id: ID of the task to delete
        user_id: ID of the user performing the deletion
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Get the task to check creation method
        task_doc = get_db().collection('tasks').document(task_id).get()
        
        if not task_doc.exists:
            logging.warning(f"Task {task_id} not found for deletion")
            return False
        
        task_data = task_doc.to_dict()
        creation_method = task_data.get('creation_method', 'manual')
        
        # If task was autonomously created, capture implicit feedback
        if creation_method == 'autonomous':
            try:
                # Check if explicit feedback was already given
                if not has_feedback_been_submitted(task_id):
                    feedback_id = submit_task_feedback(
                        task_id=task_id,
                        user_id=user_id,
                        feedback_type='negative_implicit_delete',
                        comments='User manually deleted autonomous task'
                    )
                    logging.info(f"Captured implicit negative feedback for deleted autonomous task {task_id}")
                else:
                    logging.info(f"Explicit feedback already exists for task {task_id}, skipping implicit feedback")
            except Exception as e:
                logging.error(f"Failed to capture implicit feedback for task {task_id}: {e}")
                # Continue with deletion even if feedback submission fails
        
        # Delete the task
        get_db().collection('tasks').document(task_id).delete()
        
        logging.info(f"Task {task_id} deleted successfully (creation_method: {creation_method})")
        return True
        
    except Exception as e:
        logging.error(f"Failed to delete task {task_id}: {e}")
        return False

# === PHASE 6.1: DYNAMIC PROMPT LEARNING ===

def get_negative_feedback_examples(user_id: str, limit: int = 20) -> List[str]:
    """
    Get negative feedback examples to improve task extraction prompts.
    
    Retrieves task descriptions from feedback marked as negative or implicit delete
    to help the AI learn what NOT to identify as tasks.
    
    Args:
        user_id: ID of the user to get feedback examples for
        limit: Maximum number of examples to return (default 20)
        
    Returns:
        List of task description strings that were incorrectly identified as tasks
    """
    try:
        # Query for negative feedback (both explicit negative and implicit delete)
        negative_feedback_query = (get_db().collection('task_feedback')
                                 .where(filter=FieldFilter('user_id', '==', user_id))
                                 .where(filter=FieldFilter('feedback_type', 'in', ['negative', 'negative_implicit_delete']))
                                 .order_by('timestamp', direction=firestore.Query.DESCENDING)
                                 .limit(limit))
        
        docs = negative_feedback_query.get()
        
        negative_examples = []
        for doc in docs:
            feedback_data = doc.to_dict()
            task_description = feedback_data.get('task_description', '').strip()
            
            # Only add non-empty, unique descriptions
            if task_description and task_description not in negative_examples:
                negative_examples.append(task_description)
        
        logging.info(f"Retrieved {len(negative_examples)} negative feedback examples for user {user_id}")
        
        # Log examples for debugging (truncated)
        if negative_examples:
            sample_examples = negative_examples[:3]  # Show first 3 examples
            logging.info(f"Sample negative examples: {sample_examples}")
        
        return negative_examples
        
    except Exception as e:
        logging.error(f"Failed to retrieve negative feedback examples for user {user_id}: {e}")
        return []  # Return empty list on error to allow normal prompt operation

def get_learning_insights_summary(user_id: str) -> Dict[str, Any]:
    """
    Get a summary of learning insights for monitoring AI improvement.
    
    Args:
        user_id: ID of the user
        
    Returns:
        Dict containing learning metrics and insights
    """
    try:
        # Get recent feedback statistics
        stats = get_feedback_statistics(user_id, days=30)
        
        # Get negative examples count
        negative_examples = get_negative_feedback_examples(user_id, limit=50)
        
        insights = {
            'total_feedback_30_days': stats.get('total_feedback', 0),
            'accuracy_rate': stats.get('accuracy_rate', 0.0),
            'negative_examples_available': len(negative_examples),
            'learning_active': len(negative_examples) > 0,
            'recent_improvements': [],
            'learning_data_quality': 'good' if len(negative_examples) >= 5 else 'limited'
        }
        
        # Calculate improvement trends (simplified)
        if stats.get('total_feedback', 0) >= 10:
            if stats.get('accuracy_rate', 0) >= 0.8:
                insights['recent_improvements'].append('High accuracy rate maintained')
            if stats.get('implicit_deletes', 0) <= stats.get('total_feedback', 1) * 0.1:
                insights['recent_improvements'].append('Low implicit deletion rate')
        
        return insights
        
    except Exception as e:
        logging.error(f"Failed to get learning insights for user {user_id}: {e}")
        return {
            'total_feedback_30_days': 0,
            'accuracy_rate': 0.0,
            'negative_examples_available': 0,
            'learning_active': False,
            'recent_improvements': [],
            'learning_data_quality': 'unavailable'
        }

def get_positive_feedback_examples(user_id: str, limit: int = 10) -> List[str]:
    """
    Get positive feedback examples to improve email prioritization.
    
    Retrieves task descriptions from feedback marked as positive
    to help the AI learn what types of tasks/emails are important to the user.
    
    Args:
        user_id: ID of the user to get feedback examples for
        limit: Maximum number of examples to return (default 10)
        
    Returns:
        List of task description strings that were correctly identified and valued by user
    """
    try:
        # Query for positive feedback
        positive_feedback_query = (get_db().collection('task_feedback')
                                 .where(filter=FieldFilter('user_id', '==', user_id))
                                 .where(filter=FieldFilter('feedback_type', '==', 'positive'))
                                 .order_by('timestamp', direction=firestore.Query.DESCENDING)
                                 .limit(limit))
        
        docs = positive_feedback_query.get()
        
        positive_examples = []
        for doc in docs:
            feedback_data = doc.to_dict()
            task_description = feedback_data.get('task_description', '').strip()
            
            # Only add non-empty, unique descriptions
            if task_description and task_description not in positive_examples:
                positive_examples.append(task_description)
        
        logging.info(f"Retrieved {len(positive_examples)} positive feedback examples for user {user_id}")
        
        # Log examples for debugging (truncated)
        if positive_examples:
            sample_examples = positive_examples[:3]  # Show first 3 examples
            logging.info(f"Sample positive examples: {sample_examples}")
        
        return positive_examples
        
    except Exception as e:
        logging.error(f"Failed to retrieve positive feedback examples for user {user_id}: {e}")
        return []  # Return empty list on error to allow normal prompt operation

def get_user_priority_patterns(user_id: str) -> Dict[str, Any]:
    """
    Analyze user's positive feedback to identify priority patterns.
    
    Args:
        user_id: ID of the user
        
    Returns:
        Dict containing priority insights and patterns
    """
    try:
        positive_examples = get_positive_feedback_examples(user_id, limit=50)
        
        if not positive_examples:
            return {
                'has_patterns': False,
                'priority_themes': [],
                'task_types': [],
                'personalization_strength': 'none'
            }
        
        # Simple pattern analysis (could be enhanced with NLP)
        common_keywords = {}
        task_types = []
        
        for task in positive_examples:
            # Extract common keywords (simplified)
            words = task.lower().split()
            for word in words:
                if len(word) > 3:  # Skip short words
                    common_keywords[word] = common_keywords.get(word, 0) + 1
            
            # Identify task types based on common patterns
            if any(keyword in task.lower() for keyword in ['send', 'email', 'contact']):
                task_types.append('communication')
            elif any(keyword in task.lower() for keyword in ['report', 'analysis', 'review']):
                task_types.append('reporting')
            elif any(keyword in task.lower() for keyword in ['meeting', 'schedule', 'call']):
                task_types.append('scheduling')
            elif any(keyword in task.lower() for keyword in ['update', 'status', 'progress']):
                task_types.append('updates')
        
        # Get top keywords
        sorted_keywords = sorted(common_keywords.items(), key=lambda x: x[1], reverse=True)
        priority_themes = [word for word, count in sorted_keywords[:10] if count >= 2]
        
        # Determine personalization strength
        personalization_strength = 'none'
        if len(positive_examples) >= 15:
            personalization_strength = 'strong'
        elif len(positive_examples) >= 5:
            personalization_strength = 'moderate'
        elif len(positive_examples) >= 2:
            personalization_strength = 'weak'
        
        return {
            'has_patterns': len(positive_examples) > 0,
            'priority_themes': priority_themes,
            'task_types': list(set(task_types)),
            'personalization_strength': personalization_strength,
            'total_positive_examples': len(positive_examples)
        }
        
    except Exception as e:
        logging.error(f"Failed to analyze priority patterns for user {user_id}: {e}")
        return {
            'has_patterns': False,
            'priority_themes': [],
            'task_types': [],
            'personalization_strength': 'none'
        }

# === PHASE 7: EXPLAINABLE AI (XAI) ANALYTICS ===

def get_learning_analytics(user_id: str) -> Dict[str, Any]:
    """
    Get comprehensive learning analytics for the AI Insights dashboard.
    
    Aggregates task feedback data to provide transparency into AI learning progress
    and decision-making performance.
    
    Args:
        user_id: ID of the user to get analytics for
        
    Returns:
        Dict containing learning metrics including total feedback, accuracy rate,
        positive/negative feedback counts, and learning trends
    """
    try:
        # Query all task feedback for the user
        query = get_db().collection('task_feedback').where(filter=FieldFilter('user_id', '==', user_id))
        docs = query.get()
        
        if not docs:
            return {
                "total_feedback": 0,
                "positive_feedback": 0,
                "negative_feedback": 0,
                "accuracy_rate": 0.0,
                "learning_status": "No feedback data available",
                "recent_trend": "neutral"
            }
        
        # Initialize counters
        total_feedback = 0
        positive_feedback = 0
        negative_feedback = 0
        implicit_deletes = 0
        feedback_by_date = {}
        
        # Process all feedback entries
        for doc in docs:
            feedback_data = doc.to_dict()
            feedback_type = feedback_data.get('feedback_type', 'unknown')
            timestamp = feedback_data.get('timestamp')
            
            total_feedback += 1
            
            # Count by feedback type
            if feedback_type == 'positive':
                positive_feedback += 1
            elif feedback_type == 'negative':
                negative_feedback += 1
            elif feedback_type == 'negative_implicit_delete':
                negative_feedback += 1
                implicit_deletes += 1
            
            # Group by date for trend analysis
            if timestamp:
                try:
                    date_key = timestamp.date().isoformat() if hasattr(timestamp, 'date') else str(timestamp)[:10]
                    if date_key not in feedback_by_date:
                        feedback_by_date[date_key] = {'positive': 0, 'negative': 0}
                    
                    if feedback_type == 'positive':
                        feedback_by_date[date_key]['positive'] += 1
                    elif feedback_type in ['negative', 'negative_implicit_delete']:
                        feedback_by_date[date_key]['negative'] += 1
                except Exception:
                    pass  # Skip invalid dates
        
        # Calculate accuracy rate
        accuracy_rate = positive_feedback / total_feedback if total_feedback > 0 else 0.0
        
        # Determine learning status
        learning_status = "Learning actively"
        if total_feedback == 0:
            learning_status = "No feedback data available"
        elif accuracy_rate >= 0.9:
            learning_status = "Performing excellently"
        elif accuracy_rate >= 0.7:
            learning_status = "Learning and improving"
        elif accuracy_rate >= 0.5:
            learning_status = "Needs more feedback"
        else:
            learning_status = "Requires attention"
        
        # Calculate recent trend (simplified)
        recent_trend = "neutral"
        if len(feedback_by_date) >= 2:
            recent_dates = sorted(feedback_by_date.keys())[-7:]  # Last 7 days
            recent_accuracy = []
            
            for date in recent_dates:
                day_data = feedback_by_date[date]
                day_total = day_data['positive'] + day_data['negative']
                if day_total > 0:
                    day_accuracy = day_data['positive'] / day_total
                    recent_accuracy.append(day_accuracy)
            
            if len(recent_accuracy) >= 2:
                if recent_accuracy[-1] > recent_accuracy[0]:
                    recent_trend = "improving"
                elif recent_accuracy[-1] < recent_accuracy[0]:
                    recent_trend = "declining"
        
        analytics_result = {
            "total_feedback": total_feedback,
            "positive_feedback": positive_feedback,
            "negative_feedback": negative_feedback,
            "accuracy_rate": accuracy_rate,
            "learning_status": learning_status,
            "recent_trend": recent_trend,
            "implicit_deletes": implicit_deletes,
            "feedback_by_date": feedback_by_date
        }
        
        logging.info(f"Generated learning analytics for user {user_id}: {total_feedback} total feedback, {accuracy_rate:.2%} accuracy")
        
        return analytics_result
        
    except Exception as e:
        logging.error(f"Failed to get learning analytics for user {user_id}: {e}")
        return {
            "total_feedback": 0,
            "positive_feedback": 0,
            "negative_feedback": 0,
            "accuracy_rate": 0.0,
            "learning_status": "Error retrieving data",
            "recent_trend": "neutral",
            "implicit_deletes": 0,
            "feedback_by_date": {}
        }

# === PHASE 8: TASK INTEGRATION & EXPORT ===

def export_task_to_webhook(task_data: Dict[str, Any], webhook_url: str) -> bool:
    """
    Export a task to an external system via webhook.
    
    Sends task data to a webhook endpoint for integration with third-party
    task management systems (e.g., Trello, Asana, Notion, etc.).
    
    Args:
        task_data: Dictionary containing task information
        webhook_url: URL endpoint to send the task data to
        
    Returns:
        bool: True if export was successful, False otherwise
    """
    try:
        import requests
        from datetime import datetime, timezone
        
        # Prepare the payload for the webhook
        export_payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "source": "Maia Email Assistant",
            "export_type": "task",
            "task": {
                "id": task_data.get('id', 'unknown'),
                "description": task_data.get('task_description', ''),
                "status": task_data.get('status', 'pending'),
                "deadline": task_data.get('deadline'),
                "stakeholders": task_data.get('stakeholders', []),
                "created_at": task_data.get('created_at').isoformat() if task_data.get('created_at') and hasattr(task_data.get('created_at'), 'isoformat') else None,
                "creation_method": task_data.get('creation_method', 'manual'),
                "source_email_id": task_data.get('source_email_id'),
                "priority": task_data.get('priority', 'medium'),
                "user_id": task_data.get('user_id', 'default_user')
            },
            "integration_metadata": {
                "exported_by": "Maia Phase 8 Integration",
                "version": "1.0",
                "capabilities": ["task_management", "email_integration", "ai_assistance"]
            }
        }
        
        # Set request headers
        headers = {
            'Content-Type': 'application/json',
            'User-Agent': 'Maia-Email-Assistant/1.0',
            'X-Maia-Integration': 'task-export'
        }
        
        # Make the POST request to the webhook
        response = requests.post(
            webhook_url,
            json=export_payload,
            headers=headers,
            timeout=30,  # 30 second timeout
            verify=True  # Verify SSL certificates
        )
        
        # Check if the request was successful
        if response.status_code in [200, 201, 202]:
            logging.info(f"Task {task_data.get('id', 'unknown')} successfully exported to webhook")
            logging.info(f"Webhook response: {response.status_code} - {response.text[:200]}")
            return True
        else:
            logging.error(f"Webhook export failed with status {response.status_code}: {response.text}")
            return False
            
    except requests.exceptions.Timeout:
        logging.error("Webhook export failed: Request timed out")
        return False
    except requests.exceptions.ConnectionError:
        logging.error("Webhook export failed: Connection error")
        return False
    except requests.exceptions.RequestException as e:
        logging.error(f"Webhook export failed: Request error - {e}")
        return False
    except ImportError:
        logging.error("Webhook export failed: requests library not available")
        return False
    except Exception as e:
        logging.error(f"Webhook export failed: Unexpected error - {e}")
        return False

def test_webhook_connection(webhook_url: str) -> Dict[str, Any]:
    """
    Test the webhook connection with a simple ping.
    
    Args:
        webhook_url: URL endpoint to test
        
    Returns:
        Dict containing test results and status information
    """
    try:
        import requests
        from datetime import datetime, timezone
        
        # Prepare test payload
        test_payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "source": "Maia Email Assistant",
            "test": True,
            "message": "Webhook connection test from Maia",
            "integration_metadata": {
                "test_type": "connection_check",
                "version": "1.0"
            }
        }
        
        headers = {
            'Content-Type': 'application/json',
            'User-Agent': 'Maia-Email-Assistant/1.0',
            'X-Maia-Integration': 'connection-test'
        }
        
        # Make the test request
        response = requests.post(
            webhook_url,
            json=test_payload,
            headers=headers,
            timeout=10,  # Shorter timeout for tests
            verify=True
        )
        
        return {
            "success": response.status_code in [200, 201, 202],
            "status_code": response.status_code,
            "response_time_ms": response.elapsed.total_seconds() * 1000,
            "response_text": response.text[:200],  # First 200 chars
            "error": None
        }
        
    except requests.exceptions.Timeout:
        return {
            "success": False,
            "status_code": None,
            "response_time_ms": None,
            "response_text": None,
            "error": "Request timed out"
        }
    except requests.exceptions.ConnectionError:
        return {
            "success": False,
            "status_code": None,
            "response_time_ms": None,
            "response_text": None,
            "error": "Connection error"
        }
    except Exception as e:
        return {
            "success": False,
            "status_code": None,
            "response_time_ms": None,
            "response_text": None,
            "error": str(e)
        }

def get_integration_stats(user_id: str) -> Dict[str, Any]:
    """
    Get statistics about task integrations and exports.
    
    Args:
        user_id: ID of the user
        
    Returns:
        Dict containing integration statistics
    """
    try:
        # This could be enhanced to track actual export logs in the future
        # For now, we'll return basic stats based on tasks
        all_tasks = get_tasks_for_user(user_id)
        
        stats = {
            "total_tasks": len(all_tasks),
            "exportable_tasks": len([t for t in all_tasks if t.get('status') == 'pending']),
            "tasks_by_creation_method": {},
            "integration_ready": True,
            "supported_exports": ["webhook", "json"],
            "last_updated": datetime.now(timezone.utc).isoformat()
        }
        
        # Count by creation method
        for task in all_tasks:
            method = task.get('creation_method', 'manual')
            stats["tasks_by_creation_method"][method] = stats["tasks_by_creation_method"].get(method, 0) + 1
        
        return stats
        
    except Exception as e:
        logging.error(f"Failed to get integration stats for user {user_id}: {e}")
        return {
            "total_tasks": 0,
            "exportable_tasks": 0,
            "tasks_by_creation_method": {},
            "integration_ready": False,
            "supported_exports": [],
            "last_updated": datetime.now(timezone.utc).isoformat(),
            "error": str(e)
        }