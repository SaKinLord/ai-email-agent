# -*- coding: utf-8 -*-
"""
Modern Flask API Server for Maia Email Agent
Provides REST endpoints and WebSocket communication for real-time updates
"""
from dotenv import load_dotenv
import os
import logging
# Load environment variables
load_dotenv()

# Ensure required environment variables are set for development
#if not os.getenv('GCS_BUCKET_NAME'):
    #os.environ['GCS_BUCKET_NAME'] = 'maia-email-agent-dev-bucket'
    #logging.warning("GCS_BUCKET_NAME not set, using default development bucket name")

if not os.getenv('GOOGLE_APPLICATION_CREDENTIALS'):
    # For development, we can use the same credentials.json for Google Cloud services
    credentials_path = os.path.join(os.getcwd(), 'credentials.json')
    if os.path.exists(credentials_path):
        os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = credentials_path
        logging.info("GOOGLE_APPLICATION_CREDENTIALS set to local credentials.json")
    else:
        logging.warning("GOOGLE_APPLICATION_CREDENTIALS not set and credentials.json not found")
import json

from datetime import datetime, timedelta, timezone
from functools import wraps
import jwt
import requests
from flask import Flask, request, jsonify, session
from flask_cors import CORS
from flask_socketio import SocketIO, emit, join_room, leave_room
import secrets

# Local imports
from database_utils import get_db
from agent_memory import AgentMemory
from auth_utils import get_authenticated_services
import agent_logic
import websocket_events

# Google OAuth imports
from google_auth_oauthlib.flow import Flow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('FLASK_SECRET_KEY', secrets.token_hex(32))

# Configure session for CORS environment
app.config['SESSION_COOKIE_SAMESITE'] = 'None'
app.config['SESSION_COOKIE_SECURE'] = False  # Set to True in production with HTTPS
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_DOMAIN'] = None  # Allow cross-domain cookies for localhost

# Configure CORS
CORS(app, origins=['http://localhost:3000'], supports_credentials=True)

# Initialize SocketIO
socketio = SocketIO(app, cors_allowed_origins=['http://localhost:3000'], async_mode='threading')

# Global variables
db_client = get_db()
active_connections = {}  # user_id -> socket_id mapping

# Initialize WebSocket events module
websocket_events.set_socketio_instance(socketio, active_connections, db_client)

# JWT Configuration
JWT_SECRET = os.getenv('JWT_SECRET', app.config['SECRET_KEY'])
JWT_EXPIRY_HOURS = 24

# OAuth Configuration
GOOGLE_CLIENT_SECRETS_FILE = "credentials.json"
SCOPES = [
    'https://www.googleapis.com/auth/gmail.modify', 
    'https://www.googleapis.com/auth/calendar.events.readonly',
    'https://www.googleapis.com/auth/userinfo.profile',
    'https://www.googleapis.com/auth/userinfo.email'
]
REDIRECT_URI = 'http://localhost:3000/auth/callback'

def generate_jwt_token(user_id, user_email):
    """Generate JWT token for authenticated user"""
    payload = {
        'user_id': user_id,
        'email': user_email,
        'exp': datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRY_HOURS),
        'iat': datetime.now(timezone.utc)
    }
    return jwt.encode(payload, JWT_SECRET, algorithm='HS256')

def verify_jwt_token(token):
    """Verify and decode JWT token"""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=['HS256'])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None

def require_auth(f):
    """Decorator to require JWT authentication"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'error': 'Missing or invalid authorization header'}), 401
        
        token = auth_header.split(' ')[1]
        payload = verify_jwt_token(token)
        if not payload:
            return jsonify({'error': 'Invalid or expired token'}), 401
        
        # Pass the complete user payload as the first argument to the decorated function
        return f(payload, *args, **kwargs)
    
    return decorated_function

# ============================================================================
# Authentication Endpoints
# ============================================================================

@app.route('/api/auth/google-signin', methods=['POST'])
def google_signin():
    """Initiate Google OAuth flow"""
    try:
        logger.info("Starting Google OAuth flow initialization")
        logger.info(f"Credentials file path: {GOOGLE_CLIENT_SECRETS_FILE}")
        logger.info(f"Redirect URI: {REDIRECT_URI}")
        logger.info(f"Scopes: {SCOPES}")
        
        # Check if credentials file exists
        if not os.path.exists(GOOGLE_CLIENT_SECRETS_FILE):
            logger.error(f"Credentials file not found: {GOOGLE_CLIENT_SECRETS_FILE}")
            return jsonify({'error': f'Credentials file not found: {GOOGLE_CLIENT_SECRETS_FILE}'}), 500
        
        # Create OAuth flow
        logger.info("Creating OAuth flow from client secrets file")
        flow = Flow.from_client_secrets_file(
            GOOGLE_CLIENT_SECRETS_FILE,
            scopes=SCOPES,
            redirect_uri=REDIRECT_URI
        )
        logger.info("OAuth flow created successfully")
        
        # Generate authorization URL
        logger.info("Generating authorization URL")
        authorization_url, state = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true',
            prompt='consent'  # Force consent to get refresh token
        )
        logger.info(f"Authorization URL generated: {authorization_url[:100]}...")
        logger.info(f"State generated: {state}")
        
        # Note: State will be verified by frontend using sessionStorage
        # We don't store in Flask session since the callback comes via frontend
        logger.info(f"State generated and will be verified by frontend: {state}")
        
        response_data = {
            'success': True,
            'data': {
                'authorization_url': authorization_url,
                'state': state
            }
        }
        logger.info(f"Returning response: {json.dumps({k: v if k != 'data' else {k2: v2[:100] + '...' if k2 == 'authorization_url' and len(v2) > 100 else v2 for k2, v2 in v.items()} for k, v in response_data.items()})}")
        
        return jsonify(response_data)
    except Exception as e:
        logger.error(f"Error in google_signin: {e}")
        logger.error(f"Error type: {type(e).__name__}")
        logger.error(f"Error details: {str(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return jsonify({'error': f'Failed to initiate OAuth flow: {str(e)}'}), 500

@app.route('/api/auth/callback', methods=['POST'])
def auth_callback():
    """Handle OAuth callback and return JWT"""
    try:
        data = request.get_json()
        auth_code = data.get('code')
        state = data.get('state')
        
        if not auth_code:
            return jsonify({'error': 'Missing authorization code'}), 400
        
        # Debug callback
        logger.info(f"Callback received - State from request: {state}")
        logger.info(f"Authorization code received: {auth_code[:20]}...")
        
        # Note: State verification is handled by frontend using sessionStorage
        # This provides CSRF protection since only the frontend that initiated 
        # the flow will have the matching state value
        logger.info("State verification handled by frontend - proceeding with token exchange")
        
        # Exchange authorization code for tokens
        # Use manual token exchange to avoid scope mismatch issues
        # Google automatically adds 'openid' scope which causes Flow.fetch_token() to fail
        logger.info("Performing manual token exchange to handle Google's automatic scope additions")
        
        from google.oauth2 import credentials
        
        token_url = 'https://oauth2.googleapis.com/token'
        
        # Read client secrets
        with open(GOOGLE_CLIENT_SECRETS_FILE, 'r') as f:
            client_secrets = json.load(f)
        
        client_id = client_secrets['web']['client_id']
        client_secret = client_secrets['web']['client_secret']
        
        token_data = {
            'client_id': client_id,
            'client_secret': client_secret,
            'code': auth_code,
            'grant_type': 'authorization_code',
            'redirect_uri': REDIRECT_URI
        }
        
        logger.info("Sending token exchange request to Google")
        token_response = requests.post(token_url, data=token_data)
        
        if token_response.status_code != 200:
            logger.error(f"Token exchange failed with status {token_response.status_code}: {token_response.text}")
            raise Exception(f"Token exchange failed: {token_response.text}")
        
        token_info = token_response.json()
        logger.info("Token exchange successful")
        
        # Create credentials object with our requested scopes
        credentials = credentials.Credentials(
            token=token_info['access_token'],
            refresh_token=token_info.get('refresh_token'),
            token_uri=token_url,
            client_id=client_id,
            client_secret=client_secret,
            scopes=SCOPES  # Use our original scopes
        )
        
        # Get user info from Google
        from googleapiclient.discovery import build
        people_service = build('people', 'v1', credentials=credentials)
        profile = people_service.people().get(
            resourceName='people/me',
            personFields='names,emailAddresses'
        ).execute()
        
        # Extract user information
        email_addresses = profile.get('emailAddresses', [])
        names = profile.get('names', [])
        
        user_email = email_addresses[0]['value'] if email_addresses else 'unknown@email.com'
        user_name = names[0]['displayName'] if names else 'Unknown User'
        user_id = user_email  # Use email as user ID
        
        # Store credentials using existing auth_utils
        from auth_utils import _save_token_to_gcs
        _save_token_to_gcs(credentials)
        
        # Generate JWT token for this user
        jwt_token = generate_jwt_token(user_id, user_email)
        
        # No session cleanup needed since we're not using Flask sessions for state
        
        return jsonify({
            'success': True,
            'data': {
                'token': jwt_token,
                'user': {
                    'id': user_id,
                    'email': user_email,
                    'name': user_name
                }
            }
        })
    except Exception as e:
        logger.error(f"Error in auth_callback: {e}")
        return jsonify({'error': 'Authentication failed', 'details': str(e)}), 500

@app.route('/api/auth/refresh', methods=['POST'])
@require_auth
def refresh_token(current_user):
    """Refresh JWT token"""
    try:
        new_token = generate_jwt_token(current_user['user_id'], current_user['email'])
        return jsonify({
            'success': True,
            'data': {
                'token': new_token
            }
        })
    except Exception as e:
        logger.error(f"Error refreshing token: {e}")
        return jsonify({'error': 'Token refresh failed'}), 500

@app.route('/api/auth/logout', methods=['POST'])
@require_auth
def logout(current_user):
    """Logout user and invalidate session"""
    try:
        # Remove user from active connections
        if current_user['user_id'] in active_connections:
            del active_connections[current_user['user_id']]
        
        return jsonify({
            'success': True,
            'data': {
                'message': 'Logged out successfully'
            }
        })
    except Exception as e:
        logger.error(f"Error in logout: {e}")
        return jsonify({'error': 'Logout failed'}), 500

# ============================================================================
# Dashboard Endpoints
# ============================================================================

@app.route('/api/dashboard/overview', methods=['GET'])
@require_auth
def dashboard_overview(current_user):
    """Get dashboard overview data with AI Performance metrics"""
    try:
        import re
        from urllib.parse import urlparse
        from auth_utils import get_authenticated_services
        
        user_id = current_user['user_id']
        
        # Get email counts and priorities
        emails_ref = db_client.collection('emails').where(field_path='user_id', op_string='==', value=user_id)
        emails = list(emails_ref.stream())
        
        # Calculate basic email statistics
        total_emails = len(emails)
        priority_counts = {'CRITICAL': 0, 'HIGH': 0, 'MEDIUM': 0, 'LOW': 0}
        unread_count = 0
        
        for email_doc in emails:
            email_data = email_doc.to_dict()
            priority = email_data.get('priority', 'LOW')
            if priority in priority_counts:
                priority_counts[priority] += 1
            
            if email_data.get('unread', False):
                unread_count += 1
        
        # ========================================================================
        # AI PERFORMANCE METRICS CALCULATION
        # ========================================================================
        
        # 1. CLASSIFICATION ACCURACY
        # Calculate based on positive feedback ratio
        try:
            feedback_ref = db_client.collection('feedback').where(field_path='user_id', op_string='==', value=user_id)
            feedback_docs = list(feedback_ref.stream())
            
            if feedback_docs:
                positive_feedback_count = 0
                total_feedback_count = len(feedback_docs)
                
                for feedback_doc in feedback_docs:
                    feedback_data = feedback_doc.to_dict()
                    feedback_type = feedback_data.get('feedback_type', 'correction')
                    
                    # Count as positive if feedback_type is 'positive' or if original matches corrected
                    if feedback_type == 'positive':
                        positive_feedback_count += 1
                    elif feedback_type == 'correction':
                        # Check if original classification was actually correct
                        original_priority = feedback_data.get('original_priority')
                        feedback_priority = feedback_data.get('feedback_priority')
                        original_purpose = feedback_data.get('original_purpose')
                        feedback_purpose = feedback_data.get('feedback_purpose')
                        
                        if (original_priority == feedback_priority and 
                            original_purpose == feedback_purpose):
                            positive_feedback_count += 1
                
                classification_accuracy = round((positive_feedback_count / total_feedback_count) * 100, 1)
            else:
                classification_accuracy = 85.0  # Default when no feedback available
        except Exception as e:
            logger.warning(f"Error calculating classification accuracy: {e}")
            classification_accuracy = 85.0
        
        # 2. AUTO-ACTIONS TODAY
        # Count autonomous actions in the last 24 hours
        try:
            today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
            
            # Check multiple possible collections for autonomous actions
            auto_actions_today = 0
            
            # Check autonomous_actions collection
            try:
                actions_ref = db_client.collection('autonomous_actions').where(field_path='user_id', op_string='==', value=user_id)
                actions_today = list(actions_ref.where(field_path='timestamp', op_string='>=', value=today_start).stream())
                auto_actions_today += len(actions_today)
            except Exception:
                pass  # Collection might not exist
            
            # Check activities collection for autonomous actions
            try:
                activities_ref = db_client.collection('activities').where(field_path='user_id', op_string='==', value=user_id)
                activities_today = list(activities_ref.where(field_path='type', op_string='==', value='autonomous_action')
                                      .where(field_path='created_at', op_string='>=', value=today_start).stream())
                auto_actions_today += len(activities_today)
            except Exception:
                pass  # Collection might not exist
            
            # Check action_log collection
            try:
                action_log_ref = db_client.collection('action_log').where(field_path='user_id', op_string='==', value=user_id)
                log_today = list(action_log_ref.where(field_path='timestamp', op_string='>=', value=today_start).stream())
                auto_actions_today += len(log_today)
            except Exception:
                pass  # Collection might not exist
                
        except Exception as e:
            logger.warning(f"Error counting auto-actions today: {e}")
            auto_actions_today = 0
        
        # 3. TIME SAVED CALCULATION
        # Heuristic-based estimation using autonomous actions
        try:
            # Get all autonomous actions for time calculation
            all_actions = []
            
            # Collect from all possible collections
            for collection_name in ['autonomous_actions', 'activities', 'action_log']:
                try:
                    collection_ref = db_client.collection(collection_name).where('user_id', '==', user_id)
                    if collection_name == 'activities':
                        docs = list(collection_ref.where('type', '==', 'autonomous_action').stream())
                    else:
                        docs = list(collection_ref.stream())
                    all_actions.extend([doc.to_dict() for doc in docs])
                except Exception:
                    continue
            
            # Calculate time saved based on action types
            time_saved_seconds = 0
            action_counts = {
                'auto_archive': 0,
                'auto_summary': 0,
                'auto_task': 0,
                'auto_reply': 0,
                'auto_label': 0
            }
            
            for action in all_actions:
                action_type = action.get('action_type', '').lower()
                action_details = action.get('details', {})
                
                # Categorize actions and calculate time saved
                if 'archive' in action_type or action.get('action') == 'archive':
                    action_counts['auto_archive'] += 1
                    time_saved_seconds += 5  # 5 seconds per archive
                elif 'summary' in action_type or 'summarize' in action_type:
                    action_counts['auto_summary'] += 1
                    time_saved_seconds += 45  # 45 seconds per summary
                elif 'task' in action_type or 'todo' in action_type:
                    action_counts['auto_task'] += 1
                    time_saved_seconds += 20  # 20 seconds per task creation
                elif 'reply' in action_type or 'respond' in action_type:
                    action_counts['auto_reply'] += 1
                    time_saved_seconds += 60  # 60 seconds per reply
                elif 'label' in action_type or 'tag' in action_type:
                    action_counts['auto_label'] += 1
                    time_saved_seconds += 3  # 3 seconds per label
            
            # Convert to minutes and format nicely
            time_saved_minutes = time_saved_seconds / 60
            if time_saved_minutes < 60:
                time_saved_display = f"{time_saved_minutes:.0f}m"
            else:
                hours = time_saved_minutes / 60
                time_saved_display = f"{hours:.1f}h"
                
        except Exception as e:
            logger.warning(f"Error calculating time saved: {e}")
            time_saved_display = "0m"
            action_counts = {}
        
        # 4. SECURITY SCORE CALCULATION
        # Dynamic scoring based on recent email analysis
        try:
            # Start with perfect score
            security_score = 100
            
            # Get recent emails (last 7 days) for security analysis
            week_ago = datetime.now(timezone.utc) - timedelta(days=7)
            recent_emails_ref = db_client.collection('emails').where('user_id', '==', user_id)
            recent_emails = list(recent_emails_ref.where('received_date', '>=', week_ago).stream())
            
            security_risks = {
                'suspicious_senders': 0,
                'suspicious_links': 0,
                'urgent_language': 0,
                'unverified_senders': 0
            }
            
            # Known trusted domains for sender verification
            trusted_domains = [
                'gmail.com', 'outlook.com', 'yahoo.com', 'company.com',
                'github.com', 'linkedin.com', 'google.com', 'microsoft.com',
                'amazon.com', 'apple.com', 'facebook.com', 'twitter.com'
            ]
            
            for email_doc in recent_emails:
                email_data = email_doc.to_dict()
                sender = email_data.get('sender', '').lower()
                subject = email_data.get('subject', '').lower()
                body = email_data.get('body_text', '').lower()
                
                # Check for unverified/suspicious senders
                sender_domain = None
                if '@' in sender:
                    try:
                        sender_domain = sender.split('@')[-1].strip('>')
                        if sender_domain not in trusted_domains:
                            # Check if it's a suspicious domain pattern
                            if (any(char in sender_domain for char in ['1', '2', '3', '4', '5', '6', '7', '8', '9']) or
                                len(sender_domain.split('.')) > 3 or
                                'temp' in sender_domain or 'fake' in sender_domain):
                                security_risks['suspicious_senders'] += 1
                                security_score -= 5
                            else:
                                security_risks['unverified_senders'] += 1
                                security_score -= 2
                    except Exception:
                        security_risks['unverified_senders'] += 1
                        security_score -= 2
                
                # Check for suspicious links in email body
                if body:
                    urls = re.findall(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', body)
                    suspicious_url_patterns = ['bit.ly', 'tinyurl', 'short.link', 'click.', 'track.', 'redirect.']
                    
                    for url in urls:
                        try:
                            domain = urlparse(url).netloc.lower()
                            if any(pattern in domain for pattern in suspicious_url_patterns):
                                security_risks['suspicious_links'] += 1
                                security_score -= 10
                        except Exception:
                            continue
                
                # Check for urgent/suspicious language patterns
                urgent_patterns = [
                    'urgent', 'immediate action', 'verify account', 'suspended',
                    'expires today', 'act now', 'limited time', 'click here now',
                    'confirm identity', 'update payment'
                ]
                
                combined_text = f"{subject} {body}"
                for pattern in urgent_patterns:
                    if pattern in combined_text:
                        security_risks['urgent_language'] += 1
                        security_score -= 3
                        break  # Only count once per email
            
            # Ensure score doesn't go below 0
            security_score = max(0, security_score)
            
        except Exception as e:
            logger.warning(f"Error calculating security score: {e}")
            security_score = 95  # Default to high security score
            security_risks = {}
        
        # ========================================================================
        # RETURN ENHANCED DASHBOARD DATA
        # ========================================================================
        
        return jsonify({
            'success': True,
            'data': {
                # Basic email statistics
                'total_emails': total_emails,
                'unread_count': unread_count,
                'priority_counts': priority_counts,
                
                # AI Performance Metrics
                'ai_performance': {
                    'classification_accuracy': classification_accuracy,
                    'auto_actions_today': auto_actions_today,
                    'time_saved': time_saved_display,
                    'security_score': security_score
                },
                
                # Additional metrics for detailed analysis
                'performance_details': {
                    'total_feedback_count': len(feedback_docs) if 'feedback_docs' in locals() else 0,
                    'action_breakdown': action_counts if 'action_counts' in locals() else {},
                    'security_risks': security_risks if 'security_risks' in locals() else {},
                    'calculation_timestamp': datetime.now(timezone.utc).isoformat()
                },
                
                'last_updated': datetime.now(timezone.utc).isoformat()
            }
        })
        
    except Exception as e:
        logger.error(f"Error getting dashboard overview: {e}", exc_info=True)
        return jsonify({'error': 'Failed to fetch dashboard data'}), 500

@app.route('/api/dashboard/insights', methods=['GET'])
@require_auth
def dashboard_insights(current_user):
    """Get analytics and insights"""
    try:
        # Get user-specific data
        user_id = current_user['user_id']
        
        # Calculate daily email trend (last 7 days)
        daily_email_trend = []
        today = datetime.now(timezone.utc).date()
        for i in range(6, -1, -1):  # Last 7 days
            date = today - timedelta(days=i)
            date_start = datetime.combine(date, datetime.min.time())
            date_end = datetime.combine(date, datetime.max.time())
            
            emails_query = db_client.collection('emails').where('user_id', '==', user_id)
            emails_that_day = emails_query.where('received_date', '>=', date_start).where('received_date', '<=', date_end)
            count = len(list(emails_that_day.stream()))
            
            daily_email_trend.append({
                'date': date.isoformat(),
                'count': count
            })
        
        # Calculate classification accuracy from feedback
        feedback_ref = db_client.collection('feedback').where('user_id', '==', user_id)
        feedback_docs = list(feedback_ref.stream())
        
        if feedback_docs:
            correct_feedback = 0
            total_feedback = len(feedback_docs)
            
            for feedback_doc in feedback_docs:
                feedback_data = feedback_doc.to_dict()
                # Consider feedback positive if original classification matches feedback
                original_priority = feedback_data.get('original_priority')
                feedback_priority = feedback_data.get('feedback_priority')
                original_purpose = feedback_data.get('original_purpose')
                feedback_purpose = feedback_data.get('feedback_purpose')
                
                if (original_priority == feedback_priority and 
                    original_purpose == feedback_purpose):
                    correct_feedback += 1
            
            classification_accuracy = correct_feedback / total_feedback if total_feedback > 0 else 0.85
        else:
            classification_accuracy = 0.85  # Default when no feedback available
        
        # Count autonomous actions (last 30 days)
        thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)
        activities_ref = db_client.collection('activities').where('user_id', '==', user_id)
        autonomous_activities = activities_ref.where('type', '==', 'autonomous_action').where('created_at', '>=', thirty_days_ago)
        autonomous_actions_count = len(list(autonomous_activities.stream()))
        
        # Get feedback count
        feedback_count = len(feedback_docs)
        
        return jsonify({
            'success': True,
            'data': {
                'daily_email_trend': daily_email_trend,
                'classification_accuracy': round(classification_accuracy, 3),
                'autonomous_actions_count': autonomous_actions_count,
                'feedback_count': feedback_count
            }
        })
    except Exception as e:
        logger.error(f"Error getting insights: {e}")
        return jsonify({'error': 'Failed to fetch insights'}), 500

# ============================================================================
# Email Management Endpoints
# ============================================================================

@app.route('/api/emails', methods=['GET'])
@require_auth
def get_emails(current_user):
    """Get paginated email list"""
    try:
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 20))
        priority_filter = request.args.get('priority')
        
        # Build query
        query = db_client.collection('emails').where('user_id', '==', current_user['user_id'])
        
        if priority_filter:
            query = query.where('priority', '==', priority_filter)
        
        # Get emails with pagination
        emails = list(query.order_by('received_date', direction='DESCENDING').limit(limit).stream())
        
        email_list = []
        for email_doc in emails:
            email_data = email_doc.to_dict()
            email_data['id'] = email_doc.id  # Include document ID
            email_list.append(email_data)
        
        return jsonify({
            'success': True,
            'data': {
                'emails': email_list,
                'page': page,
                'total': len(email_list)
            }
        })
    except Exception as e:
        logger.error(f"Error getting emails: {e}")
        return jsonify({'error': 'Failed to fetch emails'}), 500

@app.route('/api/emails/<email_id>', methods=['GET'])
@require_auth
def get_email_details(current_user, email_id):
    """Get single email details"""
    try:
        email_doc = db_client.collection('emails').document(email_id).get()
        
        if not email_doc.exists:
            return jsonify({'error': 'Email not found'}), 404
        
        email_data = email_doc.to_dict()
        
        # Verify user ownership
        if email_data.get('user_id') != current_user['user_id']:
            return jsonify({'error': 'Unauthorized'}), 403
        
        email_data['id'] = email_doc.id  # Include document ID
        
        return jsonify({
            'success': True,
            'data': email_data
        })
    except Exception as e:
        logger.error(f"Error getting email details: {e}")
        return jsonify({'error': 'Failed to fetch email details'}), 500

@app.route('/api/emails/<email_id>/feedback', methods=['POST'])
@require_auth
def submit_email_feedback(current_user, email_id):
    """Submit feedback for email classification"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        # Verify email exists and user owns it
        email_doc = db_client.collection('emails').document(email_id).get()
        if not email_doc.exists:
            return jsonify({'error': 'Email not found'}), 404
        
        email_data = email_doc.to_dict()
        if email_data.get('user_id') != current_user['user_id']:
            return jsonify({'error': 'Unauthorized'}), 403
        
        # Validate required fields for structured feedback
        corrected_priority = data.get('corrected_priority')
        corrected_intent = data.get('corrected_intent')
        
        if not corrected_priority or not corrected_intent:
            return jsonify({'error': 'Both corrected_priority and corrected_intent are required'}), 400
        
        # Prepare feedback data
        feedback_data = {
            'email_id': email_id,
            'user_id': current_user['user_id'],
            'original_priority': email_data.get('priority'),
            'original_purpose': email_data.get('llm_purpose') or email_data.get('purpose'),
            'feedback_priority': corrected_priority,
            'feedback_purpose': corrected_intent,
            'feedback_type': 'structured_correction',  # New structured feedback type
            'timestamp': datetime.now(timezone.utc),
            'email_subject': email_data.get('subject'),
            'email_sender': email_data.get('sender')
        }
        
        # Store comprehensive feedback in Firestore with all rich data
        from database_utils import add_feedback
        success = add_feedback(
            email_id=email_id,
            original_priority=email_data.get('priority'),
            corrected_priority=corrected_priority,
            user_id=current_user['user_id'],
            corrected_purpose=corrected_intent,
            original_purpose=email_data.get('llm_purpose') or email_data.get('purpose'),
            feedback_type='structured_correction',
            timestamp=feedback_data['timestamp'],
            email_subject=feedback_data['email_subject'],
            email_sender=feedback_data['email_sender']
        )
        
        if not success:
            logger.error(f"Failed to save feedback for email {email_id}")
            return jsonify({'error': 'Failed to save feedback'}), 500
        
        logger.info(f"Feedback submitted for email {email_id} by user {current_user['user_id']}")
        
        return jsonify({
            'success': True,
            'message': 'Feedback submitted successfully'
        })
    except Exception as e:
        logger.error(f"Error submitting email feedback: {e}")
        return jsonify({'error': 'Failed to submit feedback'}), 500

@app.route('/api/feedback/debug', methods=['GET'])
@require_auth  
def debug_feedback_data(current_user):
    """Debug endpoint to check feedback data accessibility"""
    try:
        user_id = current_user['user_id']
        
        # Check total feedback count
        feedback_collection = db_client.collection('feedback')
        all_feedback = list(feedback_collection.stream())
        
        # Check user-specific feedback
        from google.cloud.firestore_v1.base_query import FieldFilter
        user_feedback_query = feedback_collection.where(
            filter=FieldFilter('user_id', '==', user_id)
        )
        user_feedback = list(user_feedback_query.stream())
        
        # Get structured feedback data
        from database_utils import get_user_feedback_data
        structured_feedback = get_user_feedback_data(user_id)
        
        response_data = {
            'total_feedback_docs': len(all_feedback),
            'user_feedback_docs': len(user_feedback),
            'structured_feedback_count': len(structured_feedback),
            'sample_raw_feedback': user_feedback[0].to_dict() if user_feedback else None,
            'sample_structured_feedback': structured_feedback[0] if structured_feedback else None,
            'user_id': user_id
        }
        
        return jsonify(response_data)
        
    except Exception as e:
        logger.error(f"Error in feedback debug: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/emails/<email_id>/action', methods=['POST'])
@require_auth
def execute_email_action(current_user, email_id):
    """Execute action on email (archive, label, etc.)"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        action_type = data.get('type')
        if not action_type:
            return jsonify({'error': 'Action type required'}), 400
        
        # Verify email exists and user owns it
        email_doc = db_client.collection('emails').document(email_id).get()
        if not email_doc.exists:
            return jsonify({'error': 'Email not found'}), 404
        
        email_data = email_doc.to_dict()
        if email_data.get('user_id') != current_user['user_id']:
            return jsonify({'error': 'Unauthorized'}), 403
        
        # Queue the action for execution
        action_data = {
            'user_id': current_user['user_id'],
            'email_id': email_id,
            'action_type': action_type,
            'params': data.get('params', {}),
            'status': 'pending',
            'created_at': datetime.now(timezone.utc),
            'gmail_message_id': email_data.get('id'),  # Gmail message ID
            'thread_id': email_data.get('thread_id')
        }
        
        # Store action request in Firestore
        action_ref = db_client.collection('action_requests').add(action_data)
        
        logger.info(f"Email action {action_type} queued for email {email_id} by user {current_user['user_id']}")
        
        # Broadcast action queued event
        try:
            from websocket_events import broadcast_action_queued
            broadcast_action_queued(current_user['user_id'], {
                'action_id': action_ref[1].id,
                'email_id': email_id,
                'action_type': action_type,
                'status': 'queued'
            })
        except Exception as broadcast_error:
            logger.warning(f"Failed to broadcast action queued event: {broadcast_error}")
        
        return jsonify({
            'success': True,
            'message': f'Action {action_type} queued successfully',
            'action_id': action_ref[1].id
        })
    except Exception as e:
        logger.error(f"Error executing email action: {e}")
        return jsonify({'error': 'Failed to execute action'}), 500

# ============================================================================
# Activity & History Endpoints
# ============================================================================

@app.route('/api/activity/recent', methods=['GET'])
@require_auth
def get_recent_activity(current_user):
    """Get recent agent activities"""
    try:
        # Get recent activities from Firestore
        activities_ref = db_client.collection('activities').where('user_id', '==', current_user['user_id'])
        activities = list(activities_ref.order_by('created_at', direction='DESCENDING').limit(10).stream())
        
        activity_list = []
        for activity_doc in activities:
            activity_data = activity_doc.to_dict()
            activity_list.append({
                'id': activity_doc.id,
                'type': activity_data.get('type'),
                'stage': activity_data.get('stage'),
                'status': activity_data.get('status'),
                'details': activity_data.get('details', {}),
                'created_at': activity_data.get('created_at'),
                'updated_at': activity_data.get('updated_at')
            })
        
        return jsonify({
            'success': True,
            'data': activity_list
        })
    except Exception as e:
        logger.error(f"Error getting recent activity: {e}")
        return jsonify({'error': 'Failed to fetch activity data'}), 500

# ============================================================================
# WebSocket Events
# ============================================================================

@socketio.on('connect')
def handle_connect(auth):
    """Handle WebSocket connection"""
    try:
        # Verify JWT token from auth data
        token = auth.get('token') if auth else None
        if not token:
            return False
        
        payload = verify_jwt_token(token)
        if not payload:
            return False
        
        user_id = payload['user_id']
        active_connections[user_id] = request.sid
        join_room(f"user_{user_id}")
        
        logger.info(f"User {user_id} connected via WebSocket")
        emit('connection_status', {'status': 'connected', 'user_id': user_id})
        
    except Exception as e:
        logger.error(f"WebSocket connection error: {e}")
        return False

@socketio.on('disconnect')
def handle_disconnect():
    """Handle WebSocket disconnection"""
    try:
        # Remove user from active connections
        user_to_remove = None
        for user_id, socket_id in active_connections.items():
            if socket_id == request.sid:
                user_to_remove = user_id
                break
        
        if user_to_remove:
            del active_connections[user_to_remove]
            leave_room(f"user_{user_to_remove}")
            logger.info(f"User {user_to_remove} disconnected")
        
    except Exception as e:
        logger.error(f"WebSocket disconnect error: {e}")

@socketio.on('subscribe_activities')
def handle_subscribe_activities(data=None):
    """Subscribe to activity updates"""
    try:
        # User is already in their room, emit confirmation
        logger.info(f"User subscribed to activities with data: {data}")
        emit('subscription_status', {'status': 'subscribed', 'type': 'activities'})
    except Exception as e:
        logger.error(f"Error subscribing to activities: {e}")

# ============================================================================
# Utility Functions for Real-time Updates
# ============================================================================

def broadcast_activity_update(user_id, activity_data):
    """Broadcast activity update to user's WebSocket connection"""
    try:
        socketio.emit('activity_update', activity_data, room=f"user_{user_id}")
    except Exception as e:
        logger.error(f"Error broadcasting activity update: {e}")

def broadcast_system_status(user_id, status_data):
    """Broadcast system status update to user"""
    try:
        socketio.emit('system_status_update', status_data, room=f"user_{user_id}")
    except Exception as e:
        logger.error(f"Error broadcasting system status: {e}")

# ============================================================================
# Test and Utility Endpoints
# ============================================================================

@app.route('/api/test/activity', methods=['POST'])
@require_auth
def test_activity_broadcast(current_user):
    """Test endpoint to broadcast sample activity"""
    try:
        # Create a test activity
        test_activity = {
            'id': f'test_{int(datetime.now(timezone.utc).timestamp())}',
            'type': 'email_processing',
            'stage': 'analyze',
            'status': 'completed',
            'title': 'Test Email Analysis',
            'description': 'This is a test activity for WebSocket verification',
            'confidence': 0.95,
            'created_at': datetime.now(timezone.utc).isoformat(),
            'updated_at': datetime.now(timezone.utc).isoformat()
        }
        
        # Broadcast to user using WebSocket events module
        websocket_events.broadcast_activity_update(current_user['user_id'], test_activity)
        
        return jsonify({
            'success': True,
            'data': {
                'message': 'Test activity broadcasted',
                'activity': test_activity
            }
        })
    except Exception as e:
        logger.error(f"Error broadcasting test activity: {e}")
        return jsonify({'error': 'Failed to broadcast test activity'}), 500

@app.route('/api/test/system-status', methods=['POST'])
@require_auth 
def test_system_status_broadcast(current_user):
    """Test endpoint to broadcast system status"""
    try:
        # Create test system status
        test_status = {
            'is_processing': True,
            'last_email_check': datetime.now(timezone.utc).isoformat(),
            'active_tasks': ['email_analysis', 'ml_classification'],
            'autonomous_mode': True,
            'last_updated': datetime.now(timezone.utc).isoformat()
        }
        
        # Broadcast to user using WebSocket events module
        websocket_events.broadcast_system_status_update(current_user['user_id'], test_status)
        
        return jsonify({
            'success': True,
            'data': {
                'message': 'System status broadcasted',
                'status': test_status
            }
        })
    except Exception as e:
        logger.error(f"Error broadcasting system status: {e}")
        return jsonify({'error': 'Failed to broadcast system status'}), 500

@app.route('/api/test/email-processing', methods=['POST'])
@require_auth
def test_email_processing_simulation(current_user):
    """Test endpoint to simulate complete email processing flow"""
    try:
        import time
        import threading
        
        # Capture user_id from request context before starting thread
        user_id = current_user['user_id']
        
        # Get test data from request or use defaults
        data = request.get_json() or {}
        email_data = {
            'id': f'test_email_{int(datetime.now(timezone.utc).timestamp())}',
            'subject': data.get('subject', 'Test Email for Processing'),
            'sender': data.get('sender', 'test@example.com'),
            'body': data.get('body', 'This is a test email for demonstrating real-time processing.')
        }
        
        def simulate_processing(user_id, email_data):
            """Simulate email processing steps with delays"""
            try:
                logger.info(f"Starting email processing simulation for user {user_id}")
                
                # Step 1: Email processing started
                websocket_events.broadcast_email_processing_started(user_id, email_data)
                time.sleep(2)
                
                # Step 2: LLM analysis complete
                analysis_result = {
                    'purpose': 'Test',
                    'priority': 'HIGH',
                    'urgency': 'Medium',
                    'confidence': 0.87,
                    'summary': 'This is a test email analysis result with high confidence.'
                }
                websocket_events.broadcast_llm_analysis_complete(user_id, email_data['id'], analysis_result)
                time.sleep(1.5)
                
                # Step 3: Classification complete
                classification_result = {
                    'priority': 'HIGH',
                    'confidence': 0.92,
                    'features': {'sender_importance': 0.8, 'subject_keywords': 0.9}
                }
                websocket_events.broadcast_classification_complete(user_id, email_data['id'], classification_result)
                time.sleep(1)
                
                # Step 4: Suggestion generated
                websocket_events.broadcast_suggestion_generated(
                    user_id, 
                    email_data['id'], 
                    "Reply to this email within 24 hours due to high priority",
                    "action"
                )
                time.sleep(0.5)
                
                # Step 5: System status update
                status_update = {
                    'is_processing': False,
                    'last_email_check': datetime.now(timezone.utc).isoformat(),
                    'active_tasks': [],
                    'autonomous_mode': True
                }
                websocket_events.broadcast_system_status_update(user_id, status_update)
                
                logger.info(f"Email processing simulation completed for user {user_id}")
                
            except Exception as e:
                logger.error(f"Error in simulate_processing thread: {e}")
                # Try to broadcast an error status
                try:
                    error_status = {
                        'is_processing': False,
                        'last_email_check': datetime.now(timezone.utc).isoformat(),
                        'active_tasks': [],
                        'autonomous_mode': False,
                        'error': str(e)
                    }
                    websocket_events.broadcast_system_status_update(user_id, error_status)
                except Exception as broadcast_error:
                    logger.error(f"Failed to broadcast error status: {broadcast_error}")
        
        # Run simulation in background thread with parameters
        thread = threading.Thread(target=simulate_processing, args=(user_id, email_data))
        thread.daemon = True
        thread.start()
        
        return jsonify({
            'success': True,
            'data': {
                'message': 'Email processing simulation started',
                'email_data': email_data,
                'user_id': user_id  # Include for debugging
            }
        })
        
    except Exception as e:
        logger.error(f"Error simulating email processing: {e}")
        return jsonify({'error': 'Failed to start email processing simulation'}), 500

@app.route('/api/email/process-real', methods=['POST'])
@require_auth
def process_real_gmail_emails(current_user):
    """Process real Gmail emails with real-time WebSocket updates"""
    try:
        import threading
        from realtime_email_processor import create_realtime_processor
        from auth_utils import get_authenticated_services
        import anthropic
        
        # Capture user_id from request context before starting thread
        user_id = current_user['user_id']
        
        # Get request parameters
        data = request.get_json() or {}
        max_emails = data.get('max_emails', 5)
        use_enhanced_reasoning = data.get('use_enhanced_reasoning', True)
        
        def process_real_emails(user_id, max_emails, use_enhanced_reasoning):
            """Process real Gmail emails in background thread"""
            try:
                logger.info(f"Starting real Gmail processing for user {user_id}")
                
                # Create real-time processor
                processor = create_realtime_processor(user_id)
                
                # Get authenticated Gmail service
                gmail_service, calendar_service = get_authenticated_services()
                if not gmail_service:
                    raise Exception("Failed to authenticate Gmail service")
                
                # Initialize LLM client (using environment variable for now)
                api_key = os.getenv('ANTHROPIC_API_KEY')
                if not api_key:
                    raise Exception("Anthropic API key not configured")
                    
                llm_client = anthropic.Anthropic(api_key=api_key)
                
                # Process emails with real-time updates
                processed_emails = processor.process_multiple_emails_realtime(
                    user_id=user_id,
                    gmail_service=gmail_service,
                    llm_client=llm_client,
                    max_emails=max_emails,
                    use_enhanced_reasoning=use_enhanced_reasoning
                )
                
                # Broadcast completion status
                completion_status = {
                    'is_processing': False,
                    'last_email_check': datetime.now(timezone.utc).isoformat(),
                    'active_tasks': [],
                    'autonomous_mode': False,
                    'processed_count': len(processed_emails)
                }
                websocket_events.broadcast_system_status_update(user_id, completion_status)
                
                logger.info(f"Completed real Gmail processing for user {user_id}: {len(processed_emails)} emails processed")
                
            except Exception as e:
                logger.error(f"Error in real Gmail processing thread for user {user_id}: {e}", exc_info=True)
                # Try to broadcast an error status
                try:
                    error_status = {
                        'is_processing': False,
                        'last_email_check': datetime.now(timezone.utc).isoformat(),
                        'active_tasks': [],
                        'autonomous_mode': False,
                        'error': str(e)
                    }
                    websocket_events.broadcast_system_status_update(user_id, error_status)
                except Exception as broadcast_error:
                    logger.error(f"Failed to broadcast error status: {broadcast_error}")
        
        # Run real email processing in background thread
        thread = threading.Thread(
            target=process_real_emails, 
            args=(user_id, max_emails, use_enhanced_reasoning)
        )
        thread.daemon = True
        thread.start()
        
        return jsonify({
            'success': True,
            'data': {
                'message': 'Real Gmail email processing started',
                'max_emails': max_emails,
                'use_enhanced_reasoning': use_enhanced_reasoning,
                'user_id': user_id
            }
        })
        
    except Exception as e:
        logger.error(f"Error starting real Gmail processing: {e}", exc_info=True)
        return jsonify({'error': 'Failed to start real Gmail processing'}), 500

# ============================================================================
# Settings API Endpoints
# ============================================================================

@app.route('/api/settings', methods=['GET'])
@require_auth
def get_settings(current_user):
    """Get all application settings"""
    try:
        # Load configuration from config.json
        config_path = 'config.json'
        if not os.path.exists(config_path):
            logger.error("config.json not found")
            return jsonify({
                'success': False,
                'error': 'Configuration file not found'
            }), 404
        
        with open(config_path, 'r') as f:
            config = json.load(f)
        
        logger.info("Settings loaded successfully")
        return jsonify({
            'success': True,
            'data': config
        })
        
    except Exception as e:
        logger.error(f"Failed to load settings: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Failed to load settings: {str(e)}'
        }), 500

@app.route('/api/settings', methods=['PUT'])
@require_auth
def update_settings(current_user):
    """Update all application settings"""
    try:
        new_config = request.get_json()
        if not new_config:
            return jsonify({
                'success': False,
                'error': 'No configuration data provided'
            }), 400
        
        # Validate configuration structure
        required_sections = ['gmail', 'llm', 'classification', 'database', 'ml', 'retraining']
        for section in required_sections:
            if section not in new_config:
                return jsonify({
                    'success': False,
                    'error': f'Missing required section: {section}'
                }), 400
        
        # Backup current config
        config_path = 'config.json'
        backup_path = f'config.backup.{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
        
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                current_config = json.load(f)
            with open(backup_path, 'w') as f:
                json.dump(current_config, f, indent=4)
            logger.info(f"Configuration backed up to {backup_path}")
        
        # Save new configuration
        with open(config_path, 'w') as f:
            json.dump(new_config, f, indent=4)
        
        logger.info("Settings updated successfully")
        return jsonify({
            'success': True,
            'message': 'Settings updated successfully',
            'backup_file': backup_path
        })
        
    except Exception as e:
        logger.error(f"Failed to update settings: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Failed to update settings: {str(e)}'
        }), 500

@app.route('/api/settings/<category>', methods=['GET'])
@require_auth
def get_settings_category(current_user, category):
    """Get specific settings category"""
    try:
        config_path = 'config.json'
        if not os.path.exists(config_path):
            return jsonify({
                'success': False,
                'error': 'Configuration file not found'
            }), 404
        
        with open(config_path, 'r') as f:
            config = json.load(f)
        
        if category not in config:
            return jsonify({
                'success': False,
                'error': f'Category "{category}" not found'
            }), 404
        
        logger.info(f"Settings category '{category}' loaded successfully")
        return jsonify({
            'success': True,
            'data': config[category]
        })
        
    except Exception as e:
        logger.error(f"Failed to load settings category '{category}': {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Failed to load settings: {str(e)}'
        }), 500

@app.route('/api/settings/<category>', methods=['PUT'])
@require_auth
def update_settings_category(current_user, category):
    """Update specific settings category"""
    try:
        new_category_data = request.get_json()
        if not new_category_data:
            return jsonify({
                'success': False,
                'error': 'No category data provided'
            }), 400
        
        config_path = 'config.json'
        if not os.path.exists(config_path):
            return jsonify({
                'success': False,
                'error': 'Configuration file not found'
            }), 404
        
        # Load current configuration
        with open(config_path, 'r') as f:
            config = json.load(f)
        
        # Update the specific category
        config[category] = new_category_data
        
        # Save updated configuration
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=4)
        
        logger.info(f"Settings category '{category}' updated successfully")
        return jsonify({
            'success': True,
            'message': f'Category "{category}" updated successfully'
        })
        
    except Exception as e:
        logger.error(f"Failed to update settings category '{category}': {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Failed to update settings: {str(e)}'
        }), 500

@app.route('/api/settings/validate', methods=['POST'])
@require_auth
def validate_settings(current_user):
    """Validate settings configuration"""
    try:
        config_data = request.get_json()
        if not config_data:
            return jsonify({
                'success': False,
                'error': 'No configuration data provided'
            }), 400
        
        validation_errors = []
        
        # Basic validation rules
        if 'gmail' in config_data:
            gmail_config = config_data['gmail']
            if 'fetch_max_results' in gmail_config:
                if not isinstance(gmail_config['fetch_max_results'], int) or gmail_config['fetch_max_results'] <= 0:
                    validation_errors.append('gmail.fetch_max_results must be a positive integer')
        
        if 'llm' in config_data:
            llm_config = config_data['llm']
            if 'analysis_max_tokens' in llm_config:
                if not isinstance(llm_config['analysis_max_tokens'], int) or llm_config['analysis_max_tokens'] <= 0:
                    validation_errors.append('llm.analysis_max_tokens must be a positive integer')
            if 'analysis_temperature' in llm_config:
                temp = llm_config['analysis_temperature']
                if not isinstance(temp, (int, float)) or temp < 0 or temp > 2:
                    validation_errors.append('llm.analysis_temperature must be a number between 0 and 2')
        
        if 'llm_settings' in config_data:
            llm_settings = config_data['llm_settings']
            if 'gpt_budget_monthly' in llm_settings:
                budget = llm_settings['gpt_budget_monthly']
                if not isinstance(budget, (int, float)) or budget < 0:
                    validation_errors.append('llm_settings.gpt_budget_monthly must be a non-negative number')
            if 'claude_budget_monthly' in llm_settings:
                budget = llm_settings['claude_budget_monthly']
                if not isinstance(budget, (int, float)) or budget < 0:
                    validation_errors.append('llm_settings.claude_budget_monthly must be a non-negative number')
        
        if 'autonomous_tasks' in config_data:
            for task_name, task_config in config_data['autonomous_tasks'].items():
                if 'confidence_threshold' in task_config:
                    threshold = task_config['confidence_threshold']
                    if not isinstance(threshold, (int, float)) or threshold < 0 or threshold > 1:
                        validation_errors.append(f'autonomous_tasks.{task_name}.confidence_threshold must be between 0 and 1')
        
        if validation_errors:
            return jsonify({
                'success': False,
                'error': 'Validation failed',
                'validation_errors': validation_errors
            }), 400
        
        logger.info("Settings validation completed successfully")
        return jsonify({
            'success': True,
            'message': 'Configuration validation passed'
        })
        
    except Exception as e:
        logger.error(f"Settings validation failed: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Validation failed: {str(e)}'
        }), 500

@app.route('/api/settings/reset', methods=['POST'])
@require_auth
def reset_all_settings(current_user):
    """Reset all settings to default values"""
    try:
        # Load default configuration from template
        template_path = 'config.template.json'
        if not os.path.exists(template_path):
            return jsonify({
                'success': False,
                'error': 'Configuration template not found'
            }), 404
        
        with open(template_path, 'r') as f:
            default_config = json.load(f)
        
        # Backup current config
        config_path = 'config.json'
        backup_path = f'config.backup.{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
        
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                current_config = json.load(f)
            with open(backup_path, 'w') as f:
                json.dump(current_config, f, indent=4)
            logger.info(f"Configuration backed up to {backup_path}")
        
        # Reset to default configuration
        with open(config_path, 'w') as f:
            json.dump(default_config, f, indent=4)
        
        logger.info("All settings reset to defaults")
        return jsonify({
            'success': True,
            'message': 'All settings reset to defaults',
            'backup_file': backup_path
        })
        
    except Exception as e:
        logger.error(f"Failed to reset settings: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Failed to reset settings: {str(e)}'
        }), 500

@app.route('/api/settings/reset/<category>', methods=['POST'])
@require_auth
def reset_settings_category(current_user, category):
    """Reset specific settings category to default values"""
    try:
        # Load default configuration from template
        template_path = 'config.template.json'
        if not os.path.exists(template_path):
            return jsonify({
                'success': False,
                'error': 'Configuration template not found'
            }), 404
        
        with open(template_path, 'r') as f:
            default_config = json.load(f)
        
        if category not in default_config:
            return jsonify({
                'success': False,
                'error': f'Category "{category}" not found in template'
            }), 404
        
        # Load current configuration
        config_path = 'config.json'
        if not os.path.exists(config_path):
            return jsonify({
                'success': False,
                'error': 'Configuration file not found'
            }), 404
        
        with open(config_path, 'r') as f:
            config = json.load(f)
        
        # Reset the specific category
        config[category] = default_config[category]
        
        # Save updated configuration
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=4)
        
        logger.info(f"Settings category '{category}' reset to defaults")
        return jsonify({
            'success': True,
            'message': f'Category "{category}" reset to defaults'
        })
        
    except Exception as e:
        logger.error(f"Failed to reset settings category '{category}': {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Failed to reset settings: {str(e)}'
        }), 500

# ============================================================================
# Autonomous Settings and Logs
# ============================================================================

@app.route('/api/autonomous/settings', methods=['GET'])
@require_auth
def get_autonomous_settings(current_user):
    """Get current autonomous settings"""
    try:
        user_id = current_user['user_id']
        
        # Load config file
        config_path = 'config.json'
        if not os.path.exists(config_path):
            return jsonify({
                'success': False,
                'error': 'Configuration file not found'
            }), 404
            
        with open(config_path, 'r') as f:
            config = json.load(f)
        
        # Extract autonomous tasks settings
        autonomous_settings = config.get('autonomous_tasks', {
            'auto_archive': {'enabled': True, 'confidence_threshold': 0.95},
            'auto_task_creation': {'enabled': True, 'confidence_threshold': 0.90},
            'auto_meeting_prep': {'enabled': True, 'confidence_threshold': 0.90}
        })
        
        return jsonify({
            'success': True,
            'data': autonomous_settings
        })
        
    except Exception as e:
        logger.error(f"Failed to get autonomous settings: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Failed to get autonomous settings: {str(e)}'
        }), 500

@app.route('/api/autonomous/settings', methods=['POST'])
@require_auth
def update_autonomous_settings(current_user):
    """Update autonomous settings"""
    try:
        user_id = current_user['user_id']
        new_settings = request.get_json()
        
        if not new_settings:
            return jsonify({
                'success': False,
                'error': 'No settings provided'
            }), 400
        
        # Load current config
        config_path = 'config.json'
        if not os.path.exists(config_path):
            return jsonify({
                'success': False,
                'error': 'Configuration file not found'
            }), 404
            
        with open(config_path, 'r') as f:
            config = json.load(f)
        
        # Update autonomous_tasks section
        config['autonomous_tasks'] = new_settings
        
        # Save updated config
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=4)
        
        # Log the settings update
        logger.info(f"User {user_id} updated autonomous settings")
        
        return jsonify({
            'success': True,
            'data': {
                'message': 'Autonomous settings updated successfully',
                'settings': new_settings
            }
        })
        
    except Exception as e:
        logger.error(f"Failed to update autonomous settings: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Failed to update autonomous settings: {str(e)}'
        }), 500

@app.route('/api/autonomous/logs', methods=['GET'])
@require_auth
def get_autonomous_logs(current_user):
    """Get autonomous action logs"""
    try:
        user_id = current_user['user_id']
        
        # Query Firestore for autonomous action logs
        firestore_client = db_client
        
        # Get the last 20 autonomous actions
        logs_query = (firestore_client.collection('autonomous_actions')
                     .where('user_id', '==', user_id)
                     .order_by('timestamp', direction='DESCENDING')
                     .limit(20))
        
        logs = []
        for doc in logs_query.stream():
            log_data = doc.to_dict()
            log_data['id'] = doc.id
            logs.append(log_data)
        
        return jsonify({
            'success': True,
            'data': logs
        })
        
    except Exception as e:
        logger.error(f"Failed to get autonomous logs: {str(e)}")
        # Return empty array if there's an error or no Firestore connection
        return jsonify({
            'success': True,
            'data': []
        })

# ============================================================================
# Quick Actions Endpoints
# ============================================================================

@app.route('/api/ml/retrain', methods=['POST'])
@require_auth
def retrain_model(current_user):
    """Retrain the AI classification model using user feedback"""
    try:
        import threading
        import pandas as pd
        from ml_utils import build_and_train_pipeline
        from google.cloud import storage
        from database_utils import get_user_feedback_data
        
        user_id = current_user['user_id']
        
        def retrain_background_task(user_id):
            """Background task to retrain the model"""
            try:
                # Broadcast training started event
                websocket_events.broadcast_ml_training_started(user_id)
                
                logger.info(f"Starting ML model retraining for user {user_id}")
                
                # Step 1: Gathering feedback data
                websocket_events.broadcast_ml_training_progress(
                    user_id, 
                    "gathering_data", 
                    "Gathering your feedback data for training...", 
                    10
                )
                
                # Get all feedback data from Firestore
                feedback_data = get_user_feedback_data(user_id)
                logger.info(f"Retrieved {len(feedback_data)} feedback items for user {user_id}")
                
                if not feedback_data or len(feedback_data) < 5:
                    error_msg = f"Need at least 5 feedback entries for training. Found only {len(feedback_data) if feedback_data else 0}. Please provide more feedback on email classifications first."
                    logger.warning(error_msg)
                    websocket_events.broadcast_ml_training_error(user_id, error_msg)
                    return
                
                # Step 2: Preparing training data
                websocket_events.broadcast_ml_training_progress(
                    user_id, 
                    "preparing_data", 
                    f"Preparing training dataset from {len(feedback_data)} feedback entries...", 
                    30
                )
                
                # Convert feedback to training DataFrame
                training_data = []
                for feedback in feedback_data:
                    # Create training row from feedback
                    training_row = {
                        'text_features': f"{feedback.get('email_subject', '')} {feedback.get('email_body', '')}",
                        'llm_purpose': feedback.get('original_purpose', 'Unknown'),
                        'sender_domain': feedback.get('sender_domain', 'unknown'),
                        'llm_urgency': 0.5,  # Default urgency value
                        'corrected_priority': feedback.get('feedback_priority', feedback.get('corrected_priority', 'MEDIUM'))
                    }
                    training_data.append(training_row)
                
                training_df = pd.DataFrame(training_data)
                logger.info(f"Prepared training dataset with {len(training_df)} samples")
                
                # Step 3: Setting up cloud storage
                websocket_events.broadcast_ml_training_progress(
                    user_id, 
                    "setup_storage", 
                    "Setting up cloud storage for model deployment...", 
                    50
                )
                
                # Initialize Google Cloud Storage
                storage_client = storage.Client()
                bucket_name = os.getenv('MODEL_GCS_BUCKET')
                model_prefix = os.getenv('MODEL_GCS_PATH_PREFIX', 'ml_models/')
                
                if not bucket_name:
                    error_msg = "Cloud storage not configured. Please contact administrator."
                    logger.error(error_msg)
                    websocket_events.broadcast_ml_training_error(user_id, error_msg)
                    return
                
                # Step 4: Training the AI model
                websocket_events.broadcast_ml_training_progress(
                    user_id, 
                    "training_model", 
                    "Training your personalized AI model with machine learning...", 
                    70
                )
                
                # Build and train the pipeline
                pipeline, label_encoder = build_and_train_pipeline(
                    training_df=training_df,
                    storage_client=storage_client,
                    bucket_name=bucket_name,
                    pipeline_blob_name=f"{model_prefix}feature_pipeline.joblib",
                    encoder_blob_name=f"{model_prefix}label_encoder.joblib"
                )
                
                if pipeline is None or label_encoder is None:
                    error_msg = "Failed to train the AI model. Please try again or contact support."
                    logger.error(error_msg)
                    websocket_events.broadcast_ml_training_error(user_id, error_msg)
                    return
                
                # Step 5: Finalizing deployment
                websocket_events.broadcast_ml_training_progress(
                    user_id, 
                    "deploying_model", 
                    "Deploying your new AI model to the cloud...", 
                    90
                )
                
                # Broadcast training completion
                training_result = {
                    'training_samples': len(training_df),
                    'model_classes': list(label_encoder.classes_),
                    'timestamp': datetime.now(timezone.utc).isoformat()
                }
                
                websocket_events.broadcast_ml_training_complete(user_id, training_result)
                logger.info(f"ML model retraining completed successfully for user {user_id}")
                
            except Exception as e:
                error_msg = f"Error during ML retraining: {str(e)}"
                logger.error(error_msg, exc_info=True)
                websocket_events.broadcast_ml_training_error(user_id, error_msg)
        
        # Start background training task
        thread = threading.Thread(target=retrain_background_task, args=(user_id,))
        thread.daemon = True
        thread.start()
        
        return jsonify({
            'success': True,
            'data': {
                'message': 'Model retraining started',
                'user_id': user_id
            }
        })
        
    except Exception as e:
        logger.error(f"Error starting ML retraining: {e}", exc_info=True)
        return jsonify({'error': 'Failed to start model retraining'}), 500


@app.route('/api/reports/generate', methods=['GET'])
@require_auth
def generate_report(current_user):
    """Generate an AI-powered summary report of recent email activity"""
    try:
        import anthropic
        from google.cloud import secretmanager
        
        user_id = current_user['user_id']
        
        # Step 1: Start report generation
        websocket_events.broadcast_report_generation_started(user_id)
        
        # Step 2: Gathering email data
        websocket_events.broadcast_report_generation_progress(
            user_id, 
            "gathering_data", 
            "Gathering email data from the last 24 hours...", 
            20
        )
        
        # Get emails from last 24 hours
        yesterday = datetime.now(timezone.utc) - timedelta(days=1)
        emails_ref = db_client.collection('emails').where('user_id', '==', user_id)
        
        # Debug: Check what emails exist for this user
        all_user_emails = list(emails_ref.stream())
        logger.info(f"Debug: Found {len(all_user_emails)} total emails for user {user_id}")
        
        if all_user_emails:
            sample_email = all_user_emails[0].to_dict()
            logger.info(f"Debug: Sample email received_date field: {sample_email.get('received_date')} (type: {type(sample_email.get('received_date'))})")
            logger.info(f"Debug: Comparing to yesterday: {yesterday} (type: {type(yesterday)})")
        
        # Try different date filtering approaches
        recent_emails = []
        try:
            recent_emails = list(emails_ref.where('received_date', '>=', yesterday).stream())
            logger.info(f"Debug: Found {len(recent_emails)} emails with date >= yesterday")
        except Exception as e:
            logger.warning(f"Date filtering failed: {e}")
            # Fallback: get all emails for now
            recent_emails = all_user_emails
            logger.info(f"Debug: Using all {len(recent_emails)} emails as fallback")
        
        if not recent_emails:
            # No data case - but let's still provide sample charts for testing
            logger.warning("No recent emails found, but checking if any emails exist for demo charts")
            if all_user_emails:
                # Use all available emails for demo
                recent_emails = all_user_emails[:5]  # Limit to 5 for demo
                logger.info(f"Using {len(recent_emails)} total emails for demo report")
            else:
                # Truly no emails - return empty report
                no_data_report = {
                    'report': 'No email activity found in your account.',
                    'stats': {
                        'total_emails': 0,
                        'priority_breakdown': {},
                        'top_senders': [],
                        'common_purposes': []
                    },
                    'generated_at': datetime.now(timezone.utc).isoformat()
                }
                websocket_events.broadcast_report_generation_complete(user_id, no_data_report)
                return jsonify({
                    'success': True,
                    'data': no_data_report
                })
        
        # Step 3: Analyzing email patterns
        websocket_events.broadcast_report_generation_progress(
            user_id, 
            "analyzing_patterns", 
            f"Analyzing patterns and trends in {len(recent_emails)} emails...", 
            50
        )
        
        # Calculate statistics
        priority_counts = {'CRITICAL': 0, 'HIGH': 0, 'MEDIUM': 0, 'LOW': 0}
        sender_counts = {}
        purpose_counts = {}
        
        for email_doc in recent_emails:
            email_data = email_doc.to_dict()
            
            # Count priorities
            priority = email_data.get('priority', 'LOW')
            if priority in priority_counts:
                priority_counts[priority] += 1
            
            # Count senders
            sender = email_data.get('sender', 'Unknown')
            sender_counts[sender] = sender_counts.get(sender, 0) + 1
            
            # Count purposes
            purpose = email_data.get('llm_purpose') or email_data.get('purpose', 'Unknown')
            purpose_counts[purpose] = purpose_counts.get(purpose, 0) + 1
        
        # Get top senders and purposes
        top_senders = sorted(sender_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        common_purposes = sorted(purpose_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        
        stats = {
            'total_emails': len(recent_emails),
            'priority_breakdown': priority_counts,
            'top_senders': [{'sender': sender, 'count': count} for sender, count in top_senders],
            'common_purposes': [{'purpose': purpose, 'count': count} for purpose, count in common_purposes]
        }
        
        # Step 4: Generating AI insights
        websocket_events.broadcast_report_generation_progress(
            user_id, 
            "generating_insights", 
            "Generating AI-powered insights and executive summary...", 
            80
        )
        
        # Get Anthropic API key from Secret Manager
        try:
            secret_client = secretmanager.SecretManagerServiceClient()
            secret_name = os.getenv('ANTHROPIC_SECRET_NAME')
            if not secret_name:
                # Fallback to environment variable
                api_key = os.getenv('ANTHROPIC_API_KEY')
            else:
                project_id = os.getenv('GOOGLE_CLOUD_PROJECT')
                name = f"projects/{project_id}/secrets/{secret_name}/versions/latest"
                response = secret_client.access_secret_version(request={"name": name})
                api_key = response.payload.data.decode("UTF-8")
        except Exception as e:
            logger.warning(f"Failed to get API key from Secret Manager: {e}")
            api_key = os.getenv('ANTHROPIC_API_KEY')
        
        if not api_key:
            return jsonify({'error': 'Anthropic API key not configured'}), 500
        
        # Generate LLM report
        client = anthropic.Anthropic(api_key=api_key)
        
        prompt = f"""Generate a brief, insightful morning report for an executive about their email activity in the last 24 hours.

Email Statistics:
- Total emails: {stats['total_emails']}
- Priority breakdown: {stats['priority_breakdown']}
- Top senders: {[item['sender'] for item in stats['top_senders'][:3]]}
- Common purposes: {[item['purpose'] for item in stats['common_purposes'][:3]]}

Please provide:
1. A concise executive summary (2-3 sentences)
2. Key highlights and trends
3. Any recommendations for attention or action

Keep the tone professional and focus on actionable insights."""

        message = client.messages.create(
            model="claude-3-haiku-20240307",
            max_tokens=300,
            messages=[{"role": "user", "content": prompt}]
        )
        
        report_text = message.content[0].text
        
        # Final step: Complete
        report_data = {
            'report': report_text,
            'stats': stats,
            'generated_at': datetime.now(timezone.utc).isoformat()
        }
        
        websocket_events.broadcast_report_generation_complete(user_id, report_data)
        
        return jsonify({
            'success': True,
            'data': report_data
        })
        
    except Exception as e:
        logger.error(f"Error generating report: {e}", exc_info=True)
        return jsonify({'error': 'Failed to generate report'}), 500


@app.route('/api/security/scan', methods=['POST'])
@require_auth
def security_scan(current_user):
    """Perform security scan of recent emails for potential threats"""
    try:
        import anthropic
        from google.cloud import secretmanager
        from auth_utils import get_authenticated_services
        import re
        from urllib.parse import urlparse
        
        user_id = current_user['user_id']
        
        # Get request parameters
        data = request.get_json() or {}
        hours_back = data.get('hours_back', 24)  # Default to last 24 hours
        
        # Step 1: Start security scan
        websocket_events.broadcast_security_scan_started(user_id, hours_back)
        
        # Step 2: Authentication and setup
        websocket_events.broadcast_security_scan_progress(
            user_id, 
            "authenticating", 
            "Authenticating with Gmail service...", 
            10
        )
        
        # Get authenticated Gmail service
        gmail_service, _ = get_authenticated_services()
        if not gmail_service:
            return jsonify({'error': 'Failed to authenticate Gmail service'}), 500
        
        # Step 3: Fetching emails
        websocket_events.broadcast_security_scan_progress(
            user_id, 
            "fetching_emails", 
            f"Fetching emails from the last {hours_back} hours...", 
            25
        )
        
        # Get recent emails from Gmail
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours_back)
        query = f"after:{cutoff_time.strftime('%Y/%m/%d')}"
        
        try:
            results = gmail_service.users().messages().list(userId='me', q=query, maxResults=50).execute()
            messages = results.get('messages', [])
        except Exception as e:
            logger.error(f"Error fetching emails from Gmail: {e}")
            return jsonify({'error': 'Failed to fetch emails from Gmail'}), 500
        
        if not messages:
            # No emails case - still broadcast completion
            no_emails_result = {
                'threats_found': 0,
                'summary': 'No emails found in the specified time range.',
                'scan_details': [],
                'emails_scanned': 0,
                'scan_timestamp': datetime.now(timezone.utc).isoformat()
            }
            websocket_events.broadcast_security_scan_complete(user_id, no_emails_result)
            return jsonify({
                'success': True,
                'data': no_emails_result
            })
        
        # Step 4: Preparing security analysis
        websocket_events.broadcast_security_scan_progress(
            user_id, 
            "preparing_analysis", 
            f"Found {len(messages)} emails. Preparing security analysis...", 
            40
        )
        
        # Security indicators to check
        suspicious_indicators = []
        threat_details = []
        
        # Get Anthropic API key for LLM analysis
        try:
            secret_client = secretmanager.SecretManagerServiceClient()
            secret_name = os.getenv('ANTHROPIC_SECRET_NAME')
            if not secret_name:
                api_key = os.getenv('ANTHROPIC_API_KEY')
            else:
                project_id = os.getenv('GOOGLE_CLOUD_PROJECT')
                name = f"projects/{project_id}/secrets/{secret_name}/versions/latest"
                response = secret_client.access_secret_version(request={"name": name})
                api_key = response.payload.data.decode("UTF-8")
        except Exception as e:
            logger.warning(f"Failed to get API key from Secret Manager: {e}")
            api_key = os.getenv('ANTHROPIC_API_KEY')
        
        llm_client = None
        if api_key:
            llm_client = anthropic.Anthropic(api_key=api_key)
        
        # Step 5: Analyzing emails for threats
        websocket_events.broadcast_security_scan_progress(
            user_id, 
            "analyzing_threats", 
            f"Scanning {min(len(messages), 20)} emails for security threats...", 
            60
        )
        
        # Analyze each email
        emails_to_analyze = messages[:20]  # Limit to 20 emails for performance
        for i, msg in enumerate(emails_to_analyze):
            # Update progress periodically
            if i > 0 and i % 5 == 0:
                progress = 60 + int((i / len(emails_to_analyze)) * 25)  # 60-85% range
                websocket_events.broadcast_security_scan_progress(
                    user_id, 
                    "analyzing_threats", 
                    f"Analyzed {i}/{len(emails_to_analyze)} emails. Scanning for threats...", 
                    progress,
                    i
                )
            try:
                msg_detail = gmail_service.users().messages().get(userId='me', id=msg['id']).execute()
                
                # Extract email data
                headers = msg_detail['payload'].get('headers', [])
                subject = next((h['value'] for h in headers if h['name'] == 'Subject'), '')
                sender = next((h['value'] for h in headers if h['name'] == 'From'), '')
                
                # Get email body
                body = ''
                if 'parts' in msg_detail['payload']:
                    for part in msg_detail['payload']['parts']:
                        if part['mimeType'] == 'text/plain' and 'data' in part['body']:
                            body = part['body']['data']
                            break
                elif msg_detail['payload']['mimeType'] == 'text/plain' and 'data' in msg_detail['payload']['body']:
                    body = msg_detail['payload']['body']['data']
                
                if body:
                    import base64
                    body = base64.urlsafe_b64decode(body + '==').decode('utf-8', errors='ignore')
                
                # Rule-based security checks
                security_flags = []
                
                # Check for suspicious links
                urls = re.findall(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', body)
                suspicious_domains = ['bit.ly', 'tinyurl.com', 'short.link', 'click.', 'track.']
                for url in urls:
                    domain = urlparse(url).netloc.lower()
                    if any(suspicious in domain for suspicious in suspicious_domains):
                        security_flags.append(f"Suspicious shortened URL: {domain}")
                
                # Check for urgent language patterns
                urgent_patterns = [
                    r'urgent.*action.*required',
                    r'verify.*account.*immediately',
                    r'suspend.*account',
                    r'click.*here.*now',
                    r'limited.*time.*offer',
                    r'act.*now.*expire'
                ]
                
                for pattern in urgent_patterns:
                    if re.search(pattern, subject + ' ' + body, re.IGNORECASE):
                        security_flags.append(f"Urgent language pattern detected: {pattern}")
                
                # Check for credential requests
                credential_patterns = [
                    r'password',
                    r'username',
                    r'social.*security',
                    r'credit.*card',
                    r'banking.*details'
                ]
                
                for pattern in credential_patterns:
                    if re.search(pattern, subject + ' ' + body, re.IGNORECASE):
                        security_flags.append(f"Potential credential request: {pattern}")
                
                # If LLM is available, do deeper analysis for suspicious emails
                if security_flags and llm_client:
                    try:
                        llm_prompt = f"""Analyze this email for phishing or security threats:
                        
Subject: {subject}
From: {sender}
Body: {body[:1000]}...

Current flags: {security_flags}

Rate the security risk (LOW/MEDIUM/HIGH) and provide a brief explanation."""

                        message = llm_client.messages.create(
                            model="claude-3-haiku-20240307",
                            max_tokens=150,
                            messages=[{"role": "user", "content": llm_prompt}]
                        )
                        
                        llm_analysis = message.content[0].text
                        
                        if security_flags:
                            threat_details.append({
                                'email_id': msg['id'],
                                'subject': subject[:100],
                                'sender': sender,
                                'flags': security_flags,
                                'llm_analysis': llm_analysis,
                                'risk_level': 'HIGH' if len(security_flags) > 2 else 'MEDIUM'
                            })
                            
                    except Exception as e:
                        logger.warning(f"LLM analysis failed for email {msg['id']}: {e}")
                        if security_flags:
                            threat_details.append({
                                'email_id': msg['id'],
                                'subject': subject[:100],
                                'sender': sender,
                                'flags': security_flags,
                                'risk_level': 'MEDIUM'
                            })
                
                elif security_flags:
                    # Add threat without LLM analysis
                    threat_details.append({
                        'email_id': msg['id'],
                        'subject': subject[:100],
                        'sender': sender,
                        'flags': security_flags,
                        'risk_level': 'MEDIUM'
                    })
                    
            except Exception as e:
                logger.warning(f"Error analyzing email {msg.get('id', 'unknown')}: {e}")
                continue
        
        # Step 6: Finalizing results
        websocket_events.broadcast_security_scan_progress(
            user_id, 
            "finalizing_results", 
            "Generating security scan summary...", 
            90
        )
        
        # Generate summary
        threats_found = len(threat_details)
        if threats_found == 0:
            summary = f"No security threats detected in {len(messages)} emails scanned."
        else:
            high_risk = sum(1 for t in threat_details if t.get('risk_level') == 'HIGH')
            medium_risk = sum(1 for t in threat_details if t.get('risk_level') == 'MEDIUM')
            summary = f"Found {threats_found} potential threats: {high_risk} high-risk, {medium_risk} medium-risk."
        
        # Complete
        scan_results = {
            'threats_found': threats_found,
            'summary': summary,
            'scan_details': threat_details,
            'emails_scanned': len(messages),
            'scan_timestamp': datetime.now(timezone.utc).isoformat()
        }
        
        websocket_events.broadcast_security_scan_complete(user_id, scan_results)
        
        return jsonify({
            'success': True,
            'data': scan_results
        })
        
    except Exception as e:
        logger.error(f"Error performing security scan: {e}", exc_info=True)
        return jsonify({'error': 'Failed to perform security scan'}), 500


@app.route('/api/ai/performance', methods=['GET'])
@require_auth
def get_ai_performance_metrics(current_user):
    """Get detailed AI performance metrics for the dashboard"""
    try:
        user_id = current_user['user_id']
        
        # Get time range from query parameters
        days_back = int(request.args.get('days_back', 30))
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_back)
        
        # Get all emails processed in the time period
        emails_ref = db_client.collection('emails').where('user_id', '==', user_id)
        processed_emails = list(emails_ref.where('processed_date', '>=', cutoff_date).stream())
        
        # Get all feedback in the time period
        feedback_ref = db_client.collection('feedback').where('user_id', '==', user_id)
        feedback_data = list(feedback_ref.where('timestamp', '>=', cutoff_date).stream())
        
        # Calculate metrics
        total_processed = len(processed_emails)
        total_feedback = len(feedback_data)
        
        # Classification accuracy from feedback
        if feedback_data:
            correct_classifications = 0
            for feedback_doc in feedback_data:
                feedback = feedback_doc.to_dict()
                original_priority = feedback.get('original_priority')
                feedback_priority = feedback.get('feedback_priority')
                original_purpose = feedback.get('original_purpose')
                feedback_purpose = feedback.get('feedback_purpose')
                
                # Consider correct if both priority and purpose match user feedback
                if (original_priority == feedback_priority and 
                    original_purpose == feedback_purpose):
                    correct_classifications += 1
            
            accuracy = correct_classifications / total_feedback if total_feedback > 0 else 0.0
        else:
            accuracy = 0.85  # Default when no feedback
        
        # Priority distribution accuracy
        priority_stats = {'CRITICAL': 0, 'HIGH': 0, 'MEDIUM': 0, 'LOW': 0}
        purpose_stats = {}
        confidence_scores = []
        
        for email_doc in processed_emails:
            email_data = email_doc.to_dict()
            
            # Count priorities
            priority = email_data.get('priority', 'LOW')
            if priority in priority_stats:
                priority_stats[priority] += 1
            
            # Count purposes
            purpose = email_data.get('llm_purpose') or email_data.get('purpose', 'Unknown')
            purpose_stats[purpose] = purpose_stats.get(purpose, 0) + 1
            
            # Collect confidence scores
            if 'confidence' in email_data:
                confidence_scores.append(email_data['confidence'])
        
        # Calculate average confidence
        avg_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0.0
        
        # Calculate processing speed (emails per day)
        processing_speed = total_processed / max(days_back, 1)
        
        # Get autonomous actions count
        actions_ref = db_client.collection('autonomous_actions').where('user_id', '==', user_id)
        autonomous_actions = list(actions_ref.where('timestamp', '>=', cutoff_date).stream())
        
        # Calculate response time metrics (if available)
        response_times = []
        for email_doc in processed_emails:
            email_data = email_doc.to_dict()
            received_date = email_data.get('received_date')
            processed_date = email_data.get('processed_date')
            
            if received_date and processed_date:
                if isinstance(received_date, str):
                    received_date = datetime.fromisoformat(received_date.replace('Z', '+00:00'))
                if isinstance(processed_date, str):
                    processed_date = datetime.fromisoformat(processed_date.replace('Z', '+00:00'))
                
                response_time = (processed_date - received_date).total_seconds()
                if response_time > 0:
                    response_times.append(response_time)
        
        avg_response_time = sum(response_times) / len(response_times) if response_times else 0.0
        
        # Calculate trend data (last 7 days)
        daily_metrics = []
        for i in range(6, -1, -1):
            date = datetime.now(timezone.utc).date() - timedelta(days=i)
            date_start = datetime.combine(date, datetime.min.time()).replace(tzinfo=timezone.utc)
            date_end = datetime.combine(date, datetime.max.time()).replace(tzinfo=timezone.utc)
            
            # Count emails processed that day
            day_emails = [e for e in processed_emails 
                         if date_start <= e.to_dict().get('processed_date', datetime.min.replace(tzinfo=timezone.utc)) <= date_end]
            
            # Count feedback that day
            day_feedback = [f for f in feedback_data 
                           if date_start <= f.to_dict().get('timestamp', datetime.min.replace(tzinfo=timezone.utc)) <= date_end]
            
            daily_metrics.append({
                'date': date.isoformat(),
                'emails_processed': len(day_emails),
                'feedback_received': len(day_feedback)
            })
        
        metrics = {
            'classification_accuracy': round(accuracy, 3),
            'total_emails_processed': total_processed,
            'total_feedback_received': total_feedback,
            'average_confidence': round(avg_confidence, 3),
            'processing_speed_per_day': round(processing_speed, 2),
            'autonomous_actions_taken': len(autonomous_actions),
            'average_response_time_seconds': round(avg_response_time, 2),
            'priority_distribution': priority_stats,
            'purpose_distribution': dict(sorted(purpose_stats.items(), key=lambda x: x[1], reverse=True)[:10]),
            'daily_trends': daily_metrics,
            'time_period_days': days_back,
            'last_updated': datetime.now(timezone.utc).isoformat()
        }
        
        return jsonify({
            'success': True,
            'data': metrics
        })
        
    except Exception as e:
        logger.error(f"Error getting AI performance metrics: {e}", exc_info=True)
        return jsonify({'error': 'Failed to fetch AI performance metrics'}), 500

# ============================================================================
# Agent Suggestion Endpoints
# ============================================================================

@app.route('/api/agent/suggestions', methods=['GET'])
@require_auth
def get_agent_suggestions(current_user):
    """Get proactive suggestions from the agent"""
    try:
        user_id = current_user['user_id']
        logger.info(f"Getting agent suggestions for user: {user_id}")
        
        # Initialize agent components
        memory = AgentMemory(db_client, user_id)
        
        # Load config
        config_path = os.path.join(os.getcwd(), 'config.json')
        if not os.path.exists(config_path):
            logger.error("Config file not found")
            return jsonify({'error': 'Configuration not available'}), 500
            
        with open(config_path, 'r') as f:
            config = json.load(f)
        
        # Get authenticated services
        gmail_service, calendar_service = get_authenticated_services()
        
        # Initialize LLM system (optional - agent can work without it for basic suggestions)
        try:
            from hybrid_llm_system import HybridLLMManager
            llm_system = HybridLLMManager(
                config.get('llm', {}),
                openai_api_key=os.getenv('OPENAI_API_KEY'),
                anthropic_api_key=os.getenv('ANTHROPIC_API_KEY')
            )
        except Exception as e:
            logger.warning(f"LLM system not available: {e}")
            llm_system = None
        
        # Initialize ProactiveAgent
        from enhanced_proactive_agent import ProactiveAgent
        agent = ProactiveAgent(
            db_client=db_client,
            memory=memory,
            user_id=user_id,
            llm_client=llm_system,
            config=config,
            gmail_service=gmail_service
        )
        
        # Get recent emails for analysis
        emails_collection = db_client.collection('emails')
        query = emails_collection.where('user_id', '==', user_id).order_by('processed_timestamp', direction='DESCENDING').limit(50)
        email_docs = list(query.stream())
        
        # Convert to DataFrame format expected by agent
        import pandas as pd
        email_data = []
        for doc in email_docs:
            data = doc.to_dict()
            email_data.append({
                'Sender': data.get('sender', ''),
                'Subject': data.get('subject', ''),
                'Agent Priority': data.get('priority', 'MEDIUM'),
                'Purpose': data.get('llm_purpose', data.get('purpose', '')),
                'Processed At': data.get('processed_timestamp', '').isoformat() if hasattr(data.get('processed_timestamp', ''), 'isoformat') else str(data.get('processed_timestamp', ''))
            })
        
        email_df = pd.DataFrame(email_data)
        
        # Get user preferences
        user_preferences = memory.get_user_preferences()
        
        # Generate suggestions
        try:
            suggestions = agent.generate_proactive_suggestions(email_df, user_preferences)
        except Exception as e:
            logger.warning(f"Error generating suggestions with agent: {e}")
            # Fallback to basic suggestions when agent fails
            suggestions = generate_fallback_suggestions(email_df, user_preferences)
        
        # Convert suggestions to JSON-serializable format
        clean_suggestions = []
        for suggestion in suggestions:
            clean_suggestion = {
                'type': suggestion.get('type'),
                'title': suggestion.get('title'),
                'description': suggestion.get('description'),
                'action': suggestion.get('action'),
                'action_params': suggestion.get('action_params', {}),
                'priority': suggestion.get('priority', 'medium'),
                'rationale': suggestion.get('rationale', ''),
                'relevance_score': suggestion.get('relevance_score', 0.5)
            }
            clean_suggestions.append(clean_suggestion)
        
        logger.info(f"Generated {len(clean_suggestions)} suggestions for user {user_id}")
        
        return jsonify({
            'success': True,
            'data': clean_suggestions
        })
        
    except Exception as e:
        logger.error(f"Error getting agent suggestions: {e}", exc_info=True)
        return jsonify({'error': 'Failed to generate suggestions'}), 500

@app.route('/api/agent/actions', methods=['POST'])
@require_auth
def process_agent_action(current_user):
    """Process an accepted suggestion action"""
    try:
        user_id = current_user['user_id']
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No action data provided'}), 400
        
        action = data.get('action')
        params = data.get('params', {})
        suggestion_type = data.get('type')
        
        if not action:
            return jsonify({'error': 'Action not specified'}), 400
        
        logger.info(f"Processing agent action for user {user_id}: {action}")
        
        # Initialize agent components (similar to suggestions endpoint)
        memory = AgentMemory(db_client, user_id)
        
        # Load config
        config_path = os.path.join(os.getcwd(), 'config.json')
        if not os.path.exists(config_path):
            logger.error("Config file not found")
            return jsonify({'error': 'Configuration not available'}), 500
            
        with open(config_path, 'r') as f:
            config = json.load(f)
        
        # Get authenticated services
        gmail_service, calendar_service = get_authenticated_services()
        
        # Initialize LLM system (optional)
        try:
            from hybrid_llm_system import HybridLLMManager
            llm_system = HybridLLMManager(
                config.get('llm', {}),
                openai_api_key=os.getenv('OPENAI_API_KEY'),
                anthropic_api_key=os.getenv('ANTHROPIC_API_KEY')
            )
        except Exception as e:
            logger.warning(f"LLM system not available: {e}")
            llm_system = None
        
        # Initialize ProactiveAgent
        from enhanced_proactive_agent import ProactiveAgent
        agent = ProactiveAgent(
            db_client=db_client,
            memory=memory,
            user_id=user_id,
            llm_client=llm_system,
            config=config,
            gmail_service=gmail_service
        )
        
        # Process the action
        action_data = {'action': action, 'params': params}
        response_text, was_handled, download_data = agent.process_suggestion_action(action_data)
        
        if was_handled:
            # Emit WebSocket event for real-time updates
            if user_id in active_connections:
                socketio.emit('agent_action_completed', {
                    'action': action,
                    'type': suggestion_type,
                    'response': response_text,
                    'timestamp': datetime.now(timezone.utc).isoformat()
                }, room=active_connections[user_id])
            
            return jsonify({
                'success': True,
                'data': {
                    'response': response_text,
                    'action_handled': was_handled,
                    'download_data': download_data
                }
            })
        else:
            return jsonify({
                'success': False,
                'error': response_text or 'Action could not be processed'
            }), 400
            
    except Exception as e:
        logger.error(f"Error processing agent action: {e}", exc_info=True)
        return jsonify({'error': 'Failed to process action'}), 500

@app.route('/api/agent/suggestions/<suggestion_type>/dismiss', methods=['POST'])
@require_auth
def dismiss_suggestion(current_user, suggestion_type):
    """Dismiss a specific suggestion type"""
    try:
        user_id = current_user['user_id']
        logger.info(f"Dismissing suggestion type '{suggestion_type}' for user {user_id}")
        
        # Initialize memory system
        memory = AgentMemory(db_client, user_id)
        
        # Record the dismissal
        memory.record_suggestion_response(suggestion_type, False)
        
        # Also record in suggestion history if available
        from enhanced_proactive_agent import SuggestionHistory
        suggestion_history = SuggestionHistory(db_client=db_client, user_id=user_id)
        
        # Find the most recent suggestion ID for this type (if any)
        type_history = suggestion_history.get_type_history(suggestion_type, limit=1)
        if type_history:
            recent_suggestion = type_history[0]
            suggestion_id = recent_suggestion.get('id')
            if suggestion_id:
                suggestion_history.update_suggestion_response(suggestion_id, was_accepted=False)
        
        return jsonify({
            'success': True,
            'message': f'Suggestion type "{suggestion_type}" dismissed'
        })
        
    except Exception as e:
        logger.error(f"Error dismissing suggestion: {e}", exc_info=True)
        return jsonify({'error': 'Failed to dismiss suggestion'}), 500

@app.route('/api/chat', methods=['POST'])
@require_auth
def chat_with_agent(current_user):
    """Enhanced conversational chat with intelligent email assistant and robust error handling"""
    start_time = datetime.now()
    user_id = current_user['user_id']
    
    try:
        # Validate request data
        data = request.get_json()
        if not data:
            logger.warning(f"Chat request from user {user_id} missing JSON data")
            return jsonify({
                'error': 'No message provided',
                'error_type': 'validation_error'
            }), 400
        
        message = data.get('message', '').strip()
        context = data.get('context', {})
        
        # Enhanced message validation
        if not message:
            return jsonify({
                'error': 'Message cannot be empty',
                'error_type': 'validation_error'
            }), 400
        
        if len(message) > 4000:
            return jsonify({
                'error': 'Message too long. Please keep messages under 4000 characters.',
                'error_type': 'message_too_long'
            }), 400
        
        # Rate limiting check (simple implementation)
        current_time = datetime.now()
        session_key = f"chat_rate_limit_{user_id}"
        if session_key not in session:
            session[session_key] = []
        
        # Clean old requests (older than 1 minute)
        session[session_key] = [req_time for req_time in session[session_key] 
                               if (current_time - req_time).seconds < 60]
        
        if len(session[session_key]) >= 30:  # Max 30 requests per minute
            logger.warning(f"Rate limit exceeded for user {user_id}")
            return jsonify({
                'error': 'Too many requests. Please wait a moment before sending another message.',
                'error_type': 'rate_limit_exceeded'
            }), 429
        
        session[session_key].append(current_time)
        
        logger.info(f"Processing enhanced chat message for user {user_id}: {message[:100]}...")
        
        # Load config with error handling
        config = {}
        try:
            config_path = os.path.join(os.getcwd(), 'config.json')
            if os.path.exists(config_path):
                with open(config_path, 'r') as f:
                    config = json.load(f)
            else:
                logger.warning("Config file not found, using defaults")
                config = {'llm': {}}  # Minimal default config
        except Exception as e:
            logger.error(f"Error loading config: {e}")
            config = {'llm': {}}  # Fallback to minimal config
        
        # Initialize systems with comprehensive error handling
        llm_system = None
        enhanced_chat = None
        
        try:
            from hybrid_llm_system import HybridLLMManager
            llm_system = HybridLLMManager(
                config.get('llm', {}),
                openai_api_key=os.getenv('OPENAI_API_KEY'),
                anthropic_api_key=os.getenv('ANTHROPIC_API_KEY')
            )
            logger.debug("LLM system initialized successfully")
        except Exception as e:
            logger.error(f"LLM system initialization failed: {e}")
            return _create_system_unavailable_response("AI system temporarily unavailable")
        
        try:
            from enhanced_chat_system import EnhancedChatSystem
            enhanced_chat = EnhancedChatSystem(
                llm_manager=llm_system,
                db_client=db_client,
                config=config
            )
            logger.debug("Enhanced chat system initialized successfully")
        except Exception as e:
            logger.error(f"Enhanced chat system initialization failed: {e}")
            return _create_basic_chat_response(message, user_id)
        
        # Process message with comprehensive error handling
        try:
            # Use threading with timeout for cross-platform compatibility
            import threading
            import queue
            
            def chat_worker(result_queue):
                try:
                    result = enhanced_chat.process_message(
                        user_id=user_id,
                        message=message,
                        conversation_context=context
                    )
                    result_queue.put(('success', result))
                except Exception as e:
                    result_queue.put(('error', e))
            
            # Create queue and thread for timeout handling
            result_queue = queue.Queue()
            chat_thread = threading.Thread(target=chat_worker, args=(result_queue,))
            chat_thread.daemon = True
            chat_thread.start()
            
            try:
                # Wait for result with 45-second timeout
                status, result = result_queue.get(timeout=45)
                if status == 'error':
                    raise result
                
                # Validate result
                if not result or not isinstance(result, dict):
                    raise ValueError("Invalid response from chat system")
                
                if 'response' not in result:
                    raise ValueError("Missing response in chat result")
                
                # Calculate processing time
                processing_time = (datetime.now() - start_time).total_seconds()
                logger.info(f"Chat processed successfully for user {user_id} in {processing_time:.2f}s")
                
                # Emit real-time update with error handling
                try:
                    socketio.emit('chat_message_processed', {
                        'user_id': user_id,
                        'message': message[:100],  # Truncate for logging
                        'response': result.get('response', '')[:200],  # Truncate response
                        'intent': result.get('intent'),
                        'timestamp': datetime.now().isoformat(),
                        'processing_time': processing_time
                    }, room=user_id)
                except Exception as ws_error:
                    logger.warning(f"WebSocket emission failed: {ws_error}")
                    # Continue without WebSocket - don't fail the request
                
                # Return successful response
                return jsonify({
                    'success': True,
                    'data': {
                        'response': result.get('response'),
                        'intent': result.get('intent', 'conversational'),
                        'entities': result.get('entities', {}),
                        'actions': result.get('actions', []),
                        'follow_up': result.get('follow_up', False),
                        'conversation_id': result.get('conversation_id'),
                        'timestamp': datetime.now().isoformat(),
                        'processing_time': processing_time,
                        'status': result.get('status', 'success')
                    }
                })
                
            except queue.Empty:
                logger.error(f"Chat processing timeout for user {user_id}")
                return _create_timeout_response()
            
        except Exception as e:
            logger.error(f"Enhanced chat processing failed for user {user_id}: {e}", exc_info=True)
            
            # Try basic fallback response
            return _create_intelligent_fallback_response(message, user_id, str(e))
        
    except Exception as e:
        logger.error(f"Critical error in chat endpoint for user {user_id}: {e}", exc_info=True)
        return jsonify({
            'error': 'An unexpected error occurred. Please try again.',
            'error_type': 'internal_error'
        }), 500

def _create_system_unavailable_response(message: str):
    """Create response when AI system is unavailable"""
    return jsonify({
        'success': True,
        'data': {
            'response': f"{message}. I can still help you with basic email information. Try asking simple questions like 'How many emails do I have?' or 'What's in my recent emails?'",
            'intent': 'system_unavailable',
            'entities': {},
            'actions': [
                {
                    'type': 'retry_later',
                    'label': 'Try Again Later',
                    'icon': '🔄',
                    'description': 'Try your request again in a few minutes',
                    'data': {'action': 'retry'}
                }
            ],
            'follow_up': True,
            'timestamp': datetime.now().isoformat(),
            'status': 'system_unavailable'
        }
    })

def _create_basic_chat_response(message: str, user_id: str):
    """Create basic response when enhanced system fails"""
    message_lower = message.lower()
    
    # Simple pattern matching for basic responses
    if any(word in message_lower for word in ['hi', 'hello', 'hey']):
        response = "Hello! I'm having some technical difficulties with my advanced features, but I'm still here to help with your emails. What would you like to know?"
    elif any(word in message_lower for word in ['help', 'what can you do']):
        response = "I'm your email assistant, though I'm running in limited mode right now. I can normally help with email summaries, organization, and insights. Please try again shortly for full functionality."
    elif any(word in message_lower for word in ['summary', 'summarize']):
        response = "I'd like to provide you with an email summary, but my analysis features are temporarily unavailable. You can check your recent emails manually while I recover."
    else:
        response = "I'm experiencing some technical difficulties with my enhanced features. I'm normally able to help with email analysis, summaries, and organization. Please try again shortly."
    
    return jsonify({
        'success': True,
        'data': {
            'response': response,
            'intent': 'basic_fallback',
            'entities': {},
            'actions': [
                {
                    'type': 'retry',
                    'label': 'Try Again',
                    'icon': '🔄',
                    'description': 'Retry your message',
                    'data': {'action': 'retry'}
                }
            ],
            'follow_up': True,
            'timestamp': datetime.now().isoformat(),
            'status': 'basic_mode'
        }
    })

def _create_timeout_response():
    """Create response when processing times out"""
    return jsonify({
        'success': True,
        'data': {
            'response': "I'm taking longer than usual to process your request. This might be due to high demand or complex analysis. Please try rephrasing your question or ask something simpler.",
            'intent': 'timeout',
            'entities': {},
            'actions': [
                {
                    'type': 'retry_simple',
                    'label': 'Ask Something Simpler',
                    'icon': '💡',
                    'description': 'Try a basic question',
                    'data': {'action': 'simplify'}
                },
                {
                    'type': 'retry_later',
                    'label': 'Try Again Later',
                    'icon': '⏰',
                    'description': 'Retry in a few minutes',
                    'data': {'action': 'retry'}
                }
            ],
            'follow_up': True,
            'timestamp': datetime.now().isoformat(),
            'status': 'timeout'
        }
    })

def _create_intelligent_fallback_response(message: str, user_id: str, error_details: str):
    """Create intelligent fallback based on the error and user intent"""
    message_lower = message.lower()
    
    # Analyze the error type
    if 'api' in error_details.lower() or 'llm' in error_details.lower():
        response = "I'm having trouble connecting to my AI capabilities right now. I can still provide basic information about your emails. What specific information do you need?"
    elif 'database' in error_details.lower() or 'firestore' in error_details.lower():
        response = "I'm experiencing database connectivity issues. Your email data might be temporarily inaccessible. Please try again in a few minutes."
    elif 'timeout' in error_details.lower():
        response = "Your request is taking longer than expected to process. This might be due to the complexity of your question. Try asking something simpler."
    else:
        response = "I encountered an unexpected issue while processing your request. Let me try to help you with a simpler approach."
    
    # Add context-specific suggestions
    actions = [
        {
            'type': 'retry',
            'label': 'Try Again',
            'icon': '🔄',
            'description': 'Retry your original message',
            'data': {'action': 'retry'}
        }
    ]
    
    if 'summary' in message_lower:
        actions.append({
            'type': 'basic_count',
            'label': 'Get Email Count',
            'icon': '📊',
            'description': 'Get a simple count of your emails',
            'data': {'action': 'basic_summary'}
        })
    
    return jsonify({
        'success': True,
        'data': {
            'response': response,
            'intent': 'intelligent_fallback',
            'entities': {},
            'actions': actions,
            'follow_up': True,
            'timestamp': datetime.now().isoformat(),
            'status': 'fallback',
            'error_handled': True
        }
    })

# ============================================================================
# Legacy chat functions removed - now using EnhancedChatSystem
# ============================================================================

# ============================================================================
# Health Check
# ============================================================================

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'active_connections': len(active_connections)
    })

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    debug = os.getenv('FLASK_ENV') == 'development'
    
    logger.info(f"Starting Maia API Server on port {port}")
    socketio.run(app, host='0.0.0.0', port=port, debug=debug)