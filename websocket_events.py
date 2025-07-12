# -*- coding: utf-8 -*-
"""
WebSocket Event Broadcasting Module
Provides functions to broadcast real-time events to connected clients
"""

import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional
import uuid

logger = logging.getLogger(__name__)

# Global reference to SocketIO instance (will be set by api_server.py)
socketio = None
active_connections = {}
db_client = None

def set_socketio_instance(socketio_instance, connections_dict, firestore_client=None):
    """Initialize the global socketio instance and connections"""
    global socketio, active_connections, db_client
    socketio = socketio_instance
    active_connections = connections_dict
    db_client = firestore_client

def store_activity_in_firestore(user_id: str, activity_type: str, stage: str, details: Dict[str, Any], status: str = "completed"):
    """Store activity in Firestore activities collection"""
    try:
        if not db_client:
            logger.warning("Firestore client not initialized - activity not persisted")
            return
        
        activity_data = {
            'id': str(uuid.uuid4()),
            'user_id': user_id,
            'type': activity_type,
            'stage': stage,
            'status': status,
            'details': details,
            'created_at': datetime.now(timezone.utc),
            'updated_at': datetime.now(timezone.utc)
        }
        
        # Store in Firestore
        db_client.collection('activities').add(activity_data)
        logger.debug(f"Activity stored in Firestore for user {user_id}: {activity_type}.{stage}")
        
    except Exception as e:
        logger.error(f"Error storing activity in Firestore: {e}")

def broadcast_email_processing_started(user_id: str, email_data: Dict[str, Any]):
    """Broadcast that email processing has started"""
    try:
        if not socketio:
            logger.warning("SocketIO not initialized")
            return
            
        event_data = {
            'email_id': email_data.get('id', 'unknown'),
            'subject': email_data.get('subject', 'No Subject')[:100],  # Truncate long subjects
            'sender': email_data.get('sender', 'Unknown Sender'),
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
        
        # Store activity in Firestore
        store_activity_in_firestore(
            user_id=user_id,
            activity_type='email_processing',
            stage='started',
            details=event_data,
            status='in_progress'
        )
        
        logger.info(f"Broadcasting email_processing_started for user {user_id}")
        socketio.emit('email_processing_started', event_data, room=f"user_{user_id}")
        
    except Exception as e:
        logger.error(f"Error broadcasting email_processing_started: {e}")

def broadcast_llm_analysis_complete(user_id: str, email_id: str, analysis_result: Dict[str, Any]):
    """Broadcast that LLM analysis is complete"""
    try:
        if not socketio:
            logger.warning("SocketIO not initialized")
            return
            
        event_data = {
            'email_id': email_id,
            'purpose': analysis_result.get('purpose', 'Unknown'),
            'priority': analysis_result.get('priority', 'UNKNOWN'), 
            'urgency': analysis_result.get('urgency', 'Unknown'),
            'confidence': analysis_result.get('confidence', 0.0),
            'summary': analysis_result.get('summary', '')[:200],  # Truncate long summaries
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
        
        # Store activity in Firestore
        store_activity_in_firestore(
            user_id=user_id,
            activity_type='email_processing',
            stage='llm_analysis',
            details=event_data,
            status='completed'
        )
        
        logger.info(f"Broadcasting llm_analysis_complete for user {user_id}, email {email_id}")
        socketio.emit('llm_analysis_complete', event_data, room=f"user_{user_id}")
        
    except Exception as e:
        logger.error(f"Error broadcasting llm_analysis_complete: {e}")

def broadcast_classification_complete(user_id: str, email_id: str, classification_result: Dict[str, Any]):
    """Broadcast that ML classification is complete"""
    try:
        if not socketio:
            logger.warning("SocketIO not initialized")
            return
            
        event_data = {
            'email_id': email_id,
            'priority': classification_result.get('priority', 'UNKNOWN'),
            'confidence': classification_result.get('confidence', 0.0),
            'ml_features': classification_result.get('features', {}),
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
        
        logger.info(f"Broadcasting classification_complete for user {user_id}, email {email_id}")
        socketio.emit('classification_complete', event_data, room=f"user_{user_id}")
        
    except Exception as e:
        logger.error(f"Error broadcasting classification_complete: {e}")

def broadcast_suggestion_generated(user_id: str, email_id: str, suggestion: str, suggestion_type: str = "action"):
    """Broadcast that a suggestion has been generated"""
    try:
        if not socketio:
            logger.warning("SocketIO not initialized")
            return
            
        event_data = {
            'email_id': email_id,
            'suggestion': suggestion[:300],  # Truncate long suggestions
            'type': suggestion_type,
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
        
        logger.info(f"Broadcasting suggestion_generated for user {user_id}, email {email_id}")
        socketio.emit('suggestion_generated', event_data, room=f"user_{user_id}")
        
    except Exception as e:
        logger.error(f"Error broadcasting suggestion_generated: {e}")

def broadcast_autonomous_action_executed(user_id: str, email_id: str, action: str, details: str = ""):
    """Broadcast that an autonomous action was executed"""
    try:
        if not socketio:
            logger.warning("SocketIO not initialized")
            return
            
        event_data = {
            'email_id': email_id,
            'action': action,
            'details': details[:200],  # Truncate long details
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
        
        # Store activity in Firestore
        store_activity_in_firestore(
            user_id=user_id,
            activity_type='autonomous_action',
            stage='execution',
            details=event_data,
            status='completed'
        )
        
        logger.info(f"Broadcasting autonomous_action_executed for user {user_id}: {action}")
        socketio.emit('autonomous_action_executed', event_data, room=f"user_{user_id}")
        
    except Exception as e:
        logger.error(f"Error broadcasting autonomous_action_executed: {e}")

def broadcast_training_progress(user_id: str, progress: int, details: str = ""):
    """Broadcast ML training progress"""
    try:
        if not socketio:
            logger.warning("SocketIO not initialized")
            return
            
        event_data = {
            'progress': min(100, max(0, progress)),  # Ensure 0-100 range
            'details': details[:100],  # Truncate long details
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
        
        logger.info(f"Broadcasting training_progress for user {user_id}: {progress}%")
        socketio.emit('training_progress', event_data, room=f"user_{user_id}")
        
    except Exception as e:
        logger.error(f"Error broadcasting training_progress: {e}")

def broadcast_system_status_update(user_id: str, status_data: Dict[str, Any]):
    """Broadcast system status update"""
    try:
        if not socketio:
            logger.warning("SocketIO not initialized")
            return
            
        # Ensure all required fields are present
        complete_status = {
            'is_processing': status_data.get('is_processing', False),
            'last_email_check': status_data.get('last_email_check', datetime.now(timezone.utc).isoformat()),
            'active_tasks': status_data.get('active_tasks', []),
            'autonomous_mode': status_data.get('autonomous_mode', False),
            'last_updated': datetime.now(timezone.utc).isoformat()
        }
        
        # Add ML training status if available
        if 'ml_training_status' in status_data:
            complete_status['ml_training_status'] = status_data['ml_training_status']
        
        logger.info(f"Broadcasting system_status_update for user {user_id}")
        socketio.emit('system_status_update', complete_status, room=f"user_{user_id}")
        
    except Exception as e:
        logger.error(f"Error broadcasting system_status_update: {e}")

def broadcast_activity_update(user_id: str, activity_data: Dict[str, Any]):
    """Broadcast generic activity update"""
    try:
        if not socketio:
            logger.warning("SocketIO not initialized")
            return
            
        # Ensure activity has required fields
        complete_activity = {
            'id': activity_data.get('id', f'activity_{int(datetime.now(timezone.utc).timestamp())}'),
            'type': activity_data.get('type', 'unknown'),
            'stage': activity_data.get('stage', 'unknown'),
            'status': activity_data.get('status', 'unknown'),
            'title': activity_data.get('title', 'Unknown Activity'),
            'description': activity_data.get('description', ''),
            'created_at': activity_data.get('created_at', datetime.now(timezone.utc).isoformat()),
            'updated_at': datetime.now(timezone.utc).isoformat()
        }
        
        # Add optional fields if present
        for field in ['progress', 'confidence', 'email_id', 'completed_at']:
            if field in activity_data:
                complete_activity[field] = activity_data[field]
        
        logger.info(f"Broadcasting activity_update for user {user_id}: {complete_activity['title']}")
        socketio.emit('activity_update', complete_activity, room=f"user_{user_id}")
        
    except Exception as e:
        logger.error(f"Error broadcasting activity_update: {e}")

def get_connected_users():
    """Get list of currently connected user IDs"""
    try:
        return list(active_connections.keys())
    except Exception as e:
        logger.error(f"Error getting connected users: {e}")
        return []

def is_user_connected(user_id: str) -> bool:
    """Check if a specific user is connected"""
    try:
        return user_id in active_connections
    except Exception as e:
        logger.error(f"Error checking user connection: {e}")
        return False

def broadcast_ml_training_started(user_id: str):
    """Broadcast that ML model training has started"""
    try:
        if not socketio:
            logger.warning("SocketIO not initialized")
            return
            
        event_data = {
            'status': 'started',
            'message': 'ML model retraining started',
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
        
        # Store activity in Firestore
        store_activity_in_firestore(
            user_id=user_id,
            activity_type='ml_training',
            stage='started',
            details=event_data,
            status='in_progress'
        )
        
        logger.info(f"Broadcasting ml_training_started for user {user_id}")
        socketio.emit('ml_training_started', event_data, room=f"user_{user_id}")
        
    except Exception as e:
        logger.error(f"Error broadcasting ml_training_started: {e}")

def broadcast_ml_training_complete(user_id: str, training_result: Dict[str, Any]):
    """Broadcast that ML model training is complete"""
    try:
        if not socketio:
            logger.warning("SocketIO not initialized")
            return
            
        event_data = {
            'status': 'completed',
            'message': f'AI model retrained successfully with {training_result.get("training_samples", 0)} feedback entries',
            'training_samples': training_result.get('training_samples', 0),
            'model_classes': training_result.get('model_classes', []),
            'timestamp': training_result.get('timestamp', datetime.now(timezone.utc).isoformat())
        }
        
        # Store activity in Firestore
        store_activity_in_firestore(
            user_id=user_id,
            activity_type='ml_training',
            stage='completed',
            details=event_data,
            status='completed'
        )
        
        logger.info(f"Broadcasting ml_training_complete for user {user_id}")
        socketio.emit('ml_training_complete', event_data, room=f"user_{user_id}")
        
    except Exception as e:
        logger.error(f"Error broadcasting ml_training_complete: {e}")

def broadcast_ml_training_progress(user_id: str, step: str, message: str, progress_percent: int = None):
    """Broadcast ML training progress updates"""
    try:
        if not socketio:
            logger.warning("SocketIO not initialized")
            return
            
        event_data = {
            'status': 'in_progress',
            'step': step,
            'message': message,
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
        
        if progress_percent is not None:
            event_data['progress'] = progress_percent
        
        # Store activity in Firestore
        store_activity_in_firestore(
            user_id=user_id,
            activity_type='ml_training',
            stage=step,
            details=event_data,
            status='in_progress'
        )
        
        logger.info(f"Broadcasting ml_training_progress for user {user_id}: {step} - {message}")
        socketio.emit('ml_training_progress', event_data, room=f"user_{user_id}")
        
    except Exception as e:
        logger.error(f"Error broadcasting ml_training_progress: {e}")

def broadcast_ml_training_error(user_id: str, error_message: str):
    """Broadcast ML training error"""
    try:
        if not socketio:
            logger.warning("SocketIO not initialized")
            return
            
        event_data = {
            'status': 'error',
            'message': 'ML model retraining failed',
            'error': error_message,
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
        
        # Store activity in Firestore
        store_activity_in_firestore(
            user_id=user_id,
            activity_type='ml_training',
            stage='error',
            details=event_data,
            status='failed'
        )
        
        logger.info(f"Broadcasting ml_training_error for user {user_id}: {error_message}")
        socketio.emit('ml_training_error', event_data, room=f"user_{user_id}")
        
    except Exception as e:
        logger.error(f"Error broadcasting ml_training_error: {e}")

def broadcast_report_generation_started(user_id: str):
    """Broadcast that report generation has started"""
    try:
        if not socketio:
            logger.warning("SocketIO not initialized")
            return
            
        event_data = {
            'status': 'started',
            'message': 'Starting email insights report generation...',
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
        
        # Store activity in Firestore
        store_activity_in_firestore(
            user_id=user_id,
            activity_type='report_generation',
            stage='initialize',
            details=event_data,
            status='in_progress'
        )
        
        logger.info(f"Broadcasting report_generation_started for user {user_id}")
        socketio.emit('report_generation_started', event_data, room=f"user_{user_id}")
        
    except Exception as e:
        logger.error(f"Error broadcasting report_generation_started: {e}")

def broadcast_report_generation_progress(user_id: str, step: str, message: str, progress_percent: int = None):
    """Broadcast report generation progress updates"""
    try:
        if not socketio:
            logger.warning("SocketIO not initialized")
            return
            
        event_data = {
            'status': 'in_progress',
            'step': step,
            'message': message,
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
        
        if progress_percent is not None:
            event_data['progress'] = progress_percent
        
        # Store activity in Firestore
        store_activity_in_firestore(
            user_id=user_id,
            activity_type='report_generation',
            stage=step,
            details=event_data,
            status='in_progress'
        )
        
        logger.info(f"Broadcasting report_generation_progress for user {user_id}: {step} - {message}")
        socketio.emit('report_generation_progress', event_data, room=f"user_{user_id}")
        
    except Exception as e:
        logger.error(f"Error broadcasting report_generation_progress: {e}")

def broadcast_report_generation_complete(user_id: str, report_data: Dict[str, Any]):
    """Broadcast that report generation is complete with chart data"""
    try:
        if not socketio:
            logger.warning("SocketIO not initialized")
            return
            
        stats = report_data.get('stats', {})
        total_emails = stats.get('total_emails', 0)
        
        event_data = {
            'status': 'completed',
            'message': f'Report generated with insights from {total_emails} emails',
            'total_emails': total_emails,
            'priority_breakdown': stats.get('priority_breakdown', {}),
            'top_senders': stats.get('top_senders', []),
            'common_purposes': stats.get('common_purposes', []),
            'charts': {
                'pie_chart': {
                    'title': 'Email Priority Distribution',
                    'data': [
                        {'label': 'Critical', 'value': stats.get('priority_breakdown', {}).get('CRITICAL', 0), 'color': '#dc2626'},
                        {'label': 'High', 'value': stats.get('priority_breakdown', {}).get('HIGH', 0), 'color': '#ea580c'},
                        {'label': 'Medium', 'value': stats.get('priority_breakdown', {}).get('MEDIUM', 0), 'color': '#ca8a04'},
                        {'label': 'Low', 'value': stats.get('priority_breakdown', {}).get('LOW', 0), 'color': '#16a34a'}
                    ]
                },
                'bar_chart': {
                    'title': 'Top Email Purposes',
                    'data': [
                        {'label': purpose.get('purpose', 'Unknown')[:20], 'value': purpose.get('count', 0), 'color': '#8b5cf6'}
                        for purpose in stats.get('common_purposes', [])[:5]
                    ]
                }
            },
            'timestamp': report_data.get('generated_at', datetime.now(timezone.utc).isoformat())
        }
        
        # Store activity in Firestore
        store_activity_in_firestore(
            user_id=user_id,
            activity_type='report_generation',
            stage='complete',
            details=event_data,
            status='completed'
        )
        
        logger.info(f"Broadcasting report_generation_complete for user {user_id}")
        socketio.emit('report_generation_complete', event_data, room=f"user_{user_id}")
        
    except Exception as e:
        logger.error(f"Error broadcasting report_generation_complete: {e}")

def broadcast_security_scan_started(user_id: str, hours_back: int = 24):
    """Broadcast that security scan has started"""
    try:
        if not socketio:
            logger.warning("SocketIO not initialized")
            return
            
        event_data = {
            'status': 'started',
            'message': f'Starting security scan of emails from last {hours_back} hours...',
            'hours_back': hours_back,
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
        
        # Store activity in Firestore
        store_activity_in_firestore(
            user_id=user_id,
            activity_type='security_scan',
            stage='initialize',
            details=event_data,
            status='in_progress'
        )
        
        logger.info(f"Broadcasting security_scan_started for user {user_id}")
        socketio.emit('security_scan_started', event_data, room=f"user_{user_id}")
        
    except Exception as e:
        logger.error(f"Error broadcasting security_scan_started: {e}")

def broadcast_security_scan_progress(user_id: str, step: str, message: str, progress_percent: int = None, emails_processed: int = None):
    """Broadcast security scan progress updates"""
    try:
        if not socketio:
            logger.warning("SocketIO not initialized")
            return
            
        event_data = {
            'status': 'in_progress',
            'step': step,
            'message': message,
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
        
        if progress_percent is not None:
            event_data['progress'] = progress_percent
            
        if emails_processed is not None:
            event_data['emails_processed'] = emails_processed
        
        # Store activity in Firestore
        store_activity_in_firestore(
            user_id=user_id,
            activity_type='security_scan',
            stage=step,
            details=event_data,
            status='in_progress'
        )
        
        logger.info(f"Broadcasting security_scan_progress for user {user_id}: {step} - {message}")
        socketio.emit('security_scan_progress', event_data, room=f"user_{user_id}")
        
    except Exception as e:
        logger.error(f"Error broadcasting security_scan_progress: {e}")

def broadcast_security_scan_complete(user_id: str, scan_results: Dict[str, Any]):
    """Broadcast that security scan is complete"""
    try:
        if not socketio:
            logger.warning("SocketIO not initialized")
            return
            
        threats_found = scan_results.get('threats_found', 0)
        emails_scanned = scan_results.get('emails_scanned', 0)
        
        event_data = {
            'status': 'completed',
            'message': scan_results.get('summary', f'Scan complete: {threats_found} threats found in {emails_scanned} emails'),
            'threats_found': threats_found,
            'emails_scanned': emails_scanned,
            'scan_details': scan_results.get('scan_details', []),
            'timestamp': scan_results.get('scan_timestamp', datetime.now(timezone.utc).isoformat())
        }
        
        # Store activity in Firestore
        store_activity_in_firestore(
            user_id=user_id,
            activity_type='security_scan',
            stage='complete',
            details=event_data,
            status='completed'
        )
        
        logger.info(f"Broadcasting security_scan_complete for user {user_id}")
        socketio.emit('security_scan_complete', event_data, room=f"user_{user_id}")
        
    except Exception as e:
        logger.error(f"Error broadcasting security_scan_complete: {e}")

def broadcast_action_queued(user_id: str, action_data: Dict[str, Any]):
    """Broadcast that an action has been queued"""
    try:
        if not socketio:
            logger.warning("SocketIO not initialized")
            return
            
        event_data = {
            'action_id': action_data.get('action_id'),
            'email_id': action_data.get('email_id'),
            'action_type': action_data.get('action_type'),
            'status': action_data.get('status', 'queued'),
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
        
        logger.info(f"Broadcasting action_queued for user {user_id}: {action_data.get('action_type')}")
        socketio.emit('action_queued', event_data, room=f"user_{user_id}")
        
    except Exception as e:
        logger.error(f"Error broadcasting action_queued: {e}")