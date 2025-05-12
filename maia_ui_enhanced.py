import streamlit as st

# Page Configuration - MUST BE FIRST STREAMLIT COMMAND
st.set_page_config(
    page_title="Maia - Your AI Email Assistant",
    page_icon="✉️",
    layout="wide",
    initial_sidebar_state="expanded"
)

"""
Enhanced Maia Email Agent UI with Mock Data
A comprehensive Streamlit interface showcasing all features
"""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import random
from typing import Dict, List, Tuple
import time

# Custom CSS for enhanced UI
st.markdown("""
<style>
    /* Main theme colors */
    :root {
        --primary-color: #0078ff;
        --secondary-color: #0d47a1;
        --bg-color: #0f1116;
        --card-bg: #1a1c23;
        --text-color: #e0e0e0;
        --accent-color: #3da5f4;
        --success-color: #00c853;
        --warning-color: #ffc107;
        --error-color: #f44336;
        --muted-color: #8d8d8d;
    }
    
    /* Global styles */
    .stApp {
        background-color: var(--bg-color);
    }
    
    /* Card component */
    .metric-card {
        background-color: var(--card-bg);
        border-radius: 15px;
        padding: 1.5rem;
        border: 1px solid rgba(255, 255, 255, 0.1);
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
        transition: transform 0.2s;
    }
    
    .metric-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 6px 20px rgba(0, 0, 0, 0.4);
    }
    
    /* Email preview card */
    .email-card {
        background-color: var(--card-bg);
        border-radius: 10px;
        padding: 1rem;
        margin-bottom: 0.8rem;
        border-left: 4px solid var(--primary-color);
        transition: all 0.2s;
    }
    
    .email-card.critical {
        border-left-color: var(--error-color);
    }
    
    .email-card.high {
        border-left-color: var(--warning-color);
    }
    
    .email-card.medium {
        border-left-color: var(--success-color);
    }
    
    .email-card.low {
        border-left-color: var(--muted-color);
    }
    
    /* Status badge */
    .status-badge {
        display: inline-block;
        padding: 0.25rem 0.75rem;
        border-radius: 20px;
        font-size: 0.85rem;
        font-weight: 600;
    }
    
    .status-badge.critical {
        background-color: rgba(244, 67, 54, 0.2);
        color: #ff5252;
    }
    
    .status-badge.high {
        background-color: rgba(255, 193, 7, 0.2);
        color: #ffc107;
    }
    
    .status-badge.medium {
        background-color: rgba(0, 200, 83, 0.2);
        color: #00c853;
    }
    
    .status-badge.low {
        background-color: rgba(141, 141, 141, 0.2);
        color: #8d8d8d;
    }
    
    /* Chat message */
    .chat-message {
        padding: 1rem;
        border-radius: 15px;
        margin-bottom: 1rem;
        animation: fadeIn 0.5s;
    }
    
    .chat-message.user {
        background-color: var(--card-bg);
        margin-left: 2rem;
    }
    
    .chat-message.assistant {
        background-color: var(--secondary-color);
        margin-right: 2rem;
    }
    
    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(10px); }
        to { opacity: 1; transform: translateY(0); }
    }
    
    /* Quick action button */
    .quick-action {
        background: linear-gradient(135deg, var(--primary-color), var(--accent-color));
        color: white;
        border: none;
        border-radius: 25px;
        padding: 0.5rem 1.5rem;
        font-weight: 600;
        transition: all 0.3s;
        cursor: pointer;
    }
    
    .quick-action:hover {
        transform: scale(1.05);
        box-shadow: 0 5px 15px rgba(0, 120, 255, 0.4);
    }
    
    /* Progress indicator */
    .progress-ring {
        transform: rotate(-90deg);
    }
    
    /* Floating action button */
    .fab {
        position: fixed;
        bottom: 2rem;
        right: 2rem;
        width: 60px;
        height: 60px;
        background: linear-gradient(135deg, var(--primary-color), var(--accent-color));
        border-radius: 50%;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.4);
        display: flex;
        align-items: center;
        justify-content: center;
        cursor: pointer;
        transition: all 0.3s;
    }
    
    .fab:hover {
        transform: scale(1.1);
        box-shadow: 0 6px 20px rgba(0, 120, 255, 0.5);
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'email_data' not in st.session_state:
    # Generate comprehensive mock data
    st.session_state.email_data = None 
    
if 'chat_messages' not in st.session_state:
    st.session_state.chat_messages = []
    st.session_state.chat_messages.append({
        'role': 'assistant',
        'content': "Hello! I'm Maia, your AI email assistant. I'm here to help you manage your inbox efficiently. How can I assist you today?"
    })

if 'selected_email' not in st.session_state:
    st.session_state.selected_email = None

if 'autonomous_mode' not in st.session_state:
    st.session_state.autonomous_mode = False

if 'current_tab' not in st.session_state:
    st.session_state.current_tab = 'Dashboard'

# Mock Data Generation Functions
def generate_mock_emails(count: int) -> pd.DataFrame:
    """Generate realistic mock email data"""
    
    priorities = ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW']
    purposes = ['Action Request', 'Information', 'Question', 'Meeting Invite', 
                'Promotion', 'Social', 'Notification', 'Newsletter']
    
    senders = [
        "john.smith@company.com", "sarah.johnson@client.com", "mike.wilson@vendor.com",
        "emma.davis@partner.com", "alex.brown@startup.com", "lisa.anderson@important.com",
        "newsletter@techdigest.com", "notifications@socialapp.com", "support@saas.com",
        "team@internal.com", "boss@company.com", "hr@company.com"
    ]
    
    subjects = [
        "Urgent: Contract Review Needed", "Q3 Financial Report", "Meeting Tomorrow at 2 PM",
        "Action Required: Update Your Profile", "Weekly Team Update", "New Feature Launch",
        "Your Order Has Shipped", "Invitation: Company Party", "Project Deadline Reminder",
        "Customer Feedback Analysis", "Budget Approval Request", "System Maintenance Notice"
    ]
    
    # Generate emails
    emails = []
    for i in range(count):
        sent_time = datetime.now() - timedelta(
            days=random.randint(0, 30),
            hours=random.randint(0, 23),
            minutes=random.randint(0, 59)
        )
        
        priority = random.choice(priorities)
        purpose = random.choice(purposes)
        
        # Adjust purpose based on priority for realism
        if priority == 'CRITICAL':
            purpose = random.choice(['Action Request', 'Question', 'Meeting Invite'])
        elif priority == 'LOW':
            purpose = random.choice(['Newsletter', 'Promotion', 'Notification'])
        
        email = {
            'id': f'EMAIL{1000+i}',
            'sender': random.choice(senders),
            'subject': random.choice(subjects),
            'priority': priority,
            'purpose': purpose,
            'sent_time': sent_time,
            'response_needed': purpose in ['Action Request', 'Question'],
            'estimated_time': random.randint(5, 60) if purpose == 'Action Request' else random.randint(1, 15),
            'read': random.choice([True, False]),
            'archived': False,
            'summary': generate_email_summary(purpose, priority),
            'body': generate_email_body(purpose, priority)
        }
        emails.append(email)
    
    return pd.DataFrame(emails).sort_values('sent_time', ascending=False)

def generate_email_summary(purpose: str, priority: str) -> str:
    """Generate a realistic email summary based on purpose and priority"""
    summaries = {
        'Action Request': {
            'CRITICAL': "Immediate action required on contract terms. Client waiting for response.",
            'HIGH': "Please review and approve the budget proposal by EOD tomorrow.",
            'MEDIUM': "Update needed on project timeline for next week's presentation.",
            'LOW': "Optional: Feedback on new office layout designs."
        },
        'Question': {
            'CRITICAL': "Urgent clarification needed on compliance issue affecting launch.",
            'HIGH': "Quick question about budget allocation for Q4 initiatives.",
            'MEDIUM': "Thoughts on proposed meeting schedule for next month?",
            'LOW': "Any preference for team lunch location?"
        },
        'Meeting Invite': {
            'CRITICAL': "Emergency board meeting regarding acquisition - attendance mandatory.",
            'HIGH': "Client presentation tomorrow at 2 PM - final prep meeting.",
            'MEDIUM': "Weekly team sync on Tuesday - project updates needed.",
            'LOW': "Optional coffee chat about new initiatives."
        },
        'Information': {
            'HIGH': "Q3 results exceed expectations - detailed analysis attached.",
            'MEDIUM': "Monthly newsletter with industry updates and trends.",
            'LOW': "FYI: Office will close early on Friday for maintenance."
        }
    }
    
    default_summary = "Email requires your attention based on content analysis."
    return summaries.get(purpose, {}).get(priority, default_summary)

def generate_email_body(purpose: str, priority: str) -> str:
    """Generate realistic email body content"""
    templates = {
        'Action Request': """
        Hi [Name],
        
        I hope this email finds you well. I'm reaching out regarding [topic].
        
        We need your input on the following items:
        - Review the attached document
        - Provide feedback by [date]
        - Approve the proposed changes
        
        This is {priority} priority as it impacts [consequence].
        
        Please let me know if you need any additional information.
        
        Best regards,
        [Sender]
        """,
        'Question': """
        Hi [Name],
        
        Quick question about [topic]:
        
        [Specific question details]
        
        I'd appreciate your thoughts when you have a moment. This is {priority} priority.
        
        Thanks,
        [Sender]
        """,
        'Meeting Invite': """
        Hi [Name],
        
        I'd like to schedule a meeting to discuss [topic].
        
        Proposed time: [Date and time]
        Duration: [Duration]
        Location: [Location/Virtual]
        
        Agenda:
        1. [Item 1]
        2. [Item 2]
        3. [Item 3]
        
        Please confirm your availability.
        
        Regards,
        [Sender]
        """
    }
    
    template = templates.get(purpose, "Email content for {purpose}")
    return template.format(priority=priority.lower(), purpose=purpose)

# Main UI Components

def display_header():
    """Display the main header with Maia branding"""
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col1:
        st.image("https://api.dicebear.com/7.x/bottts/svg?seed=Maia&backgroundColor=0066cc", width=80)
    
    with col2:
        st.markdown("<h1 style='text-align: center; color: #0078ff; margin: 0;'>Maia</h1>", 
                   unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; color: #8d8d8d; margin: 0;'>Your Intelligent Email Assistant</p>", 
                   unsafe_allow_html=True)
    
    with col3:
        # Status indicators
        status_col1, status_col2 = st.columns(2)
        with status_col1:
            if st.session_state.autonomous_mode:
                st.markdown("🤖 **Auto Mode**")
            else:
                st.markdown("👤 **Manual Mode**")
        
        with status_col2:
            st.markdown(f"📊 **{len(st.session_state.email_data)}** emails")

def display_dashboard():
    """Display the main dashboard with email overview"""
    
    # Quick stats
    st.markdown("## 📊 Dashboard Overview")
    
    col1, col2, col3, col4 = st.columns(4)
    
    email_df = st.session_state.email_data
    unread_count = len(email_df[~email_df['read']])
    critical_count = len(email_df[email_df['priority'] == 'CRITICAL'])
    action_count = len(email_df[email_df['purpose'] == 'Action Request'])
    avg_response_time = email_df[email_df['response_needed']]['estimated_time'].mean()
    
    with col1:
        st.metric("Unread Emails", unread_count, 
                 delta=f"-{random.randint(1,5)} today",
                 delta_color="inverse")
    
    with col2:
        st.metric("Critical Priority", critical_count,
                 delta=f"+{random.randint(0,2)} new",
                 delta_color="normal" if critical_count > 0 else "off")
    
    with col3:
        st.metric("Action Required", action_count,
                 help="Emails needing your response")
    
    with col4:
        st.metric("Avg Response Time", f"{avg_response_time:.0f} min",
                 help="Average time needed per email")
    
    # Email Timeline
    st.markdown("### 📧 Email Activity Timeline")
    timeline_data = create_timeline_chart(email_df)
    st.plotly_chart(timeline_data, use_container_width=True)
    
    # Priority Distribution
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 🎯 Priority Distribution")
        priority_chart = create_priority_chart(email_df)
        st.plotly_chart(priority_chart, use_container_width=True)
    
    with col2:
        st.markdown("### 📋 Purpose Analysis")
        purpose_chart = create_purpose_chart(email_df)
        st.plotly_chart(purpose_chart, use_container_width=True)
    
    # Top Senders
    st.markdown("### 👥 Top Senders")
    top_senders = email_df['sender'].value_counts().head(5)
    sender_cols = st.columns(5)
    
    for i, (sender, count) in enumerate(top_senders.items()):
        with sender_cols[i]:
            name = sender.split('@')[0].title()
            st.markdown(f"""
            <div class="metric-card" style="text-align: center;">
                <h4>{name}</h4>
                <p style="font-size: 24px; font-weight: bold; color: #00c853;">{count}</p>
                <p style="color: #8d8d8d;">emails</p>
            </div>
            """, unsafe_allow_html=True)
    
    # Smart Suggestions
    st.markdown("### 💡 Smart Suggestions")
    display_suggestions(email_df)

def create_timeline_chart(email_df):
    """Create email timeline visualization"""
    # Group emails by day
    email_df['date'] = email_df['sent_time'].dt.date
    daily_counts = email_df.groupby(['date', 'priority']).size().reset_index(name='count')
    
    fig = px.area(daily_counts, x='date', y='count', color='priority',
                  color_discrete_map={
                      'CRITICAL': '#f44336',
                      'HIGH': '#ffc107',
                      'MEDIUM': '#00c853',
                      'LOW': '#8d8d8d'
                  })
    
    fig.update_layout(
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font_color='#e0e0e0',
        showlegend=True,
        height=300
    )
    
    return fig

def create_priority_chart(email_df):
    """Create priority distribution donut chart"""
    priority_counts = email_df['priority'].value_counts()
    
    fig = go.Figure(data=[go.Pie(
        labels=priority_counts.index,
        values=priority_counts.values,
        hole=0.6,
        marker=dict(colors=['#f44336', '#ffc107', '#00c853', '#8d8d8d'])
    )])
    
    fig.update_traces(textposition='inside', textinfo='percent+label')
    fig.update_layout(
        showlegend=False,
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font_color='#e0e0e0',
        height=300
    )
    
    # Add center text
    fig.add_annotation(
        text=f"{len(email_df)}<br>Total",
        x=0.5, y=0.5,
        font=dict(size=20, color='#e0e0e0'),
        showarrow=False
    )
    
    return fig

def create_purpose_chart(email_df):
    """Create purpose distribution bar chart"""
    purpose_counts = email_df['purpose'].value_counts().head(5)
    
    fig = px.bar(
        x=purpose_counts.values,
        y=purpose_counts.index,
        orientation='h',
        color=purpose_counts.index,
        color_discrete_sequence=px.colors.sequential.Blues_r
    )
    
    fig.update_layout(
        showlegend=False,
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font_color='#e0e0e0',
        xaxis_title="Count",
        yaxis_title="",
        height=300
    )
    
    return fig

def display_suggestions(email_df):
    """Display smart suggestions based on email patterns"""
    suggestions = []
    
    # High priority emails
    critical_emails = email_df[email_df['priority'] == 'CRITICAL']
    if len(critical_emails) > 0:
        suggestions.append({
            'icon': '🚨',
            'title': f"You have {len(critical_emails)} critical emails",
            'description': "These require immediate attention",
            'action': 'View Critical Emails'
        })
    
    # Unread action requests
    unread_actions = email_df[(~email_df['read']) & (email_df['purpose'] == 'Action Request')]
    if len(unread_actions) > 0:
        suggestions.append({
            'icon': '📝',
            'title': f"{len(unread_actions)} unread action requests",
            'description': "These emails need your response",
            'action': 'Review Actions'
        })
    
    # Meeting invites
    meetings = email_df[email_df['purpose'] == 'Meeting Invite']
    if len(meetings) > 0:
        suggestions.append({
            'icon': '📅',
            'title': f"{len(meetings)} meeting invitations",
            'description': "Review and respond to meeting requests",
            'action': 'Check Calendar'
        })
    
    # Display suggestion cards
    cols = st.columns(len(suggestions))
    for i, suggestion in enumerate(suggestions):
        with cols[i]:
            st.markdown(f"""
            <div class="metric-card">
                <h3>{suggestion['icon']} {suggestion['title']}</h3>
                <p style="color: #8d8d8d;">{suggestion['description']}</p>
                <button class="quick-action">{suggestion['action']}</button>
            </div>
            """, unsafe_allow_html=True)

def display_inbox():
    """Display the email inbox with filtering and sorting"""
    st.markdown("## 📥 Inbox")
    
    # Filtering options
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        priority_filter = st.selectbox("Priority", ["All"] + st.session_state.email_data['priority'].unique().tolist())
    
    with col2:
        purpose_filter = st.selectbox("Purpose", ["All"] + st.session_state.email_data['purpose'].unique().tolist())
    
    with col3:
        status_filter = st.selectbox("Status", ["All", "Unread", "Read"])
    
    with col4:
        sort_by = st.selectbox("Sort by", ["Newest First", "Oldest First", "Priority", "Sender"])
    
    # Apply filters
    filtered_df = st.session_state.email_data.copy()
    
    if priority_filter != "All":
        filtered_df = filtered_df[filtered_df['priority'] == priority_filter]
    
    if purpose_filter != "All":
        filtered_df = filtered_df[filtered_df['purpose'] == purpose_filter]
    
    if status_filter == "Unread":
        filtered_df = filtered_df[~filtered_df['read']]
    elif status_filter == "Read":
        filtered_df = filtered_df[filtered_df['read']]
    
    # Apply sorting
    if sort_by == "Newest First":
        filtered_df = filtered_df.sort_values('sent_time', ascending=False)
    elif sort_by == "Oldest First":
        filtered_df = filtered_df.sort_values('sent_time', ascending=True)
    elif sort_by == "Priority":
        priority_order = {'CRITICAL': 0, 'HIGH': 1, 'MEDIUM': 2, 'LOW': 3}
        filtered_df['priority_order'] = filtered_df['priority'].map(priority_order)
        filtered_df = filtered_df.sort_values('priority_order')
    elif sort_by == "Sender":
        filtered_df = filtered_df.sort_values('sender')
    
    # Display email list
    st.markdown(f"Showing {len(filtered_df)} emails")
    
    # Email list with enhanced UI
    for _, email in filtered_df.iterrows():
        display_email_card(email)

def display_email_card(email):
    """Display individual email card with actions"""
    priority_class = email['priority'].lower()
    read_indicator = "" if email['read'] else "🔵 "
    
    with st.container():
        col1, col2, col3 = st.columns([3, 1, 1])
        
        with col1:
            st.markdown(f"""
            <div class="email-card {priority_class}">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <div>
                        <h4 style="margin: 0;">{read_indicator}{email['subject']}</h4>
                        <p style="color: #8d8d8d; margin: 5px 0;">From: {email['sender']}</p>
                        <p style="color: #8d8d8d; margin: 0;">
                            {email['sent_time'].strftime('%Y-%m-%d %H:%M')} • 
                            <span class="status-badge {priority_class}">{email['priority']}</span> • 
                            {email['purpose']}
                        </p>
                    </div>
                </div>
                <p style="margin-top: 10px;">{email['summary']}</p>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            if st.button("View", key=f"view_{email['id']}"):
                st.session_state.selected_email = email
                st.session_state.current_tab = 'Email Details'
                st.rerun()
        
        with col3:
            if st.button("Archive", key=f"archive_{email['id']}"):
                # Archive email logic
                st.success(f"Email archived: {email['subject']}")

def display_chat():
    """Display the chat interface with Maia"""
    st.markdown("## 💬 Chat with Maia")
    
    # Chat container
    chat_container = st.container()
    
    with chat_container:
        for message in st.session_state.chat_messages:
            if message['role'] == 'user':
                st.markdown(f"""
                <div class="chat-message user">
                    <strong>You:</strong> {message['content']}
                </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown(f"""
                <div class="chat-message assistant">
                    <strong>Maia:</strong> {message['content']}
                </div>
                """, unsafe_allow_html=True)
    
    # Chat input
    user_input = st.chat_input("Ask Maia anything about your emails...")
    
    if user_input:
        # Add user message
        st.session_state.chat_messages.append({'role': 'user', 'content': user_input})
        
        # Generate response (mock)
        response = generate_maia_response(user_input)
        st.session_state.chat_messages.append({'role': 'assistant', 'content': response})
        
        st.rerun()
    
    # Quick actions
    st.markdown("### Quick Actions")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if st.button("📊 Show High Priority"):
            response = "You have 3 high-priority emails that need your attention:\n1. Contract Review from john.smith@company.com\n2. Budget Approval from boss@company.com\n3. Client Meeting from sarah.johnson@client.com"
            st.session_state.chat_messages.append({'role': 'assistant', 'content': response})
            st.rerun()
    
    with col2:
        if st.button("📝 Draft Reply"):
            response = "I can help you draft a reply. Which email would you like to respond to?"
            st.session_state.chat_messages.append({'role': 'assistant', 'content': response})
            st.rerun()
    
    with col3:
        if st.button("📅 Schedule Time"):
            response = "Based on your email patterns, I suggest checking emails at 9 AM and 2 PM. Would you like me to schedule these times in your calendar?"
            st.session_state.chat_messages.append({'role': 'assistant', 'content': response})
            st.rerun()
    
    with col4:
        if st.button("🧹 Clean Inbox"):
            response = "I can help archive 15 low-priority emails and 8 newsletters. Would you like me to proceed?"
            st.session_state.chat_messages.append({'role': 'assistant', 'content': response})
            st.rerun()

def generate_maia_response(user_input: str) -> str:
    """Generate mock responses from Maia"""
    user_input_lower = user_input.lower()
    
    if "high priority" in user_input_lower or "important" in user_input_lower:
        return f"You have {random.randint(2, 5)} high-priority emails. The most urgent one is from your boss about the Q3 budget approval. Would you like me to summarize it?"
    
    elif "summarize" in user_input_lower:
        return "Here's a summary of your most recent critical email:\n\n**Subject:** Urgent: Contract Review Needed\n**From:** john.smith@company.com\n**Summary:** The client needs final approval on contract terms by tomorrow 5 PM. Key changes include payment schedule adjustment and delivery timeline modification. Requires your signature.\n\n**Suggested Action:** Review and respond within 2 hours."
    
    elif "draft" in user_input_lower or "reply" in user_input_lower:
        return "I'll help you draft a reply. Here's a suggested response:\n\n---\nDear John,\n\nThank you for the contract update. I've reviewed the key changes:\n- Payment schedule adjustment\n- Delivery timeline modification\n\nI approve these changes. Please proceed with the client.\n\nBest regards,\n[Your name]\n---\n\nWould you like me to revise this draft?"
    
    elif "schedule" in user_input_lower or "calendar" in user_input_lower:
        return "Based on your email patterns, you receive most emails between 10 AM - 2 PM. I suggest scheduling dedicated email time at:\n- 9:00 AM - 9:30 AM (Morning review)\n- 2:00 PM - 2:30 PM (Afternoon review)\n\nShall I add these to your calendar as recurring events?"
    
    elif "clean" in user_input_lower or "archive" in user_input_lower:
        return "I've identified emails that can be archived:\n- 12 newsletters older than 7 days\n- 8 promotional emails\n- 5 notification emails that you've already read\n\nTotal: 25 emails. This will free up your inbox significantly. Proceed with archiving?"
    
    else:
        return "I understand you're asking about your emails. I can help you with:\n- Prioritizing important emails\n- Drafting responses\n- Scheduling email time\n- Cleaning up your inbox\n- Analyzing email patterns\n\nWhat would you like to do?"

def display_insights():
    """Display email insights and analytics"""
    st.markdown("## 📊 Email Insights")
    
    email_df = st.session_state.email_data
    
    # Time period selector
    time_period = st.selectbox("Time Period", ["Last 7 Days", "Last 30 Days", "All Time"])
    
    # Filter by time period
    if time_period == "Last 7 Days":
        cutoff_date = datetime.now() - timedelta(days=7)
        filtered_df = email_df[email_df['sent_time'] > cutoff_date]
    elif time_period == "Last 30 Days":
        cutoff_date = datetime.now() - timedelta(days=30)
        filtered_df = email_df[email_df['sent_time'] > cutoff_date]
    else:
        filtered_df = email_df
    
    # Key metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Emails", len(filtered_df))
    
    with col2:
        response_rate = (filtered_df['response_needed'].sum() / len(filtered_df) * 100)
        st.metric("Response Rate", f"{response_rate:.1f}%")
    
    with col3:
        avg_time = filtered_df['estimated_time'].mean()
        st.metric("Avg Time/Email", f"{avg_time:.0f} min")
    
    with col4:
        unread_rate = ((~filtered_df['read']).sum() / len(filtered_df) * 100)
        st.metric("Unread Rate", f"{unread_rate:.1f}%")
    
    # Email volume by hour
    st.markdown("### 📈 Email Volume by Hour")
    hourly_data = filtered_df.copy()
    hourly_data['hour'] = hourly_data['sent_time'].dt.hour
    hourly_counts = hourly_data.groupby('hour').size().reset_index(name='count')
    
    fig = px.bar(hourly_counts, x='hour', y='count',
                 labels={'hour': 'Hour of Day', 'count': 'Number of Emails'})
    fig.update_layout(
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font_color='#e0e0e0'
    )
    st.plotly_chart(fig, use_container_width=True)
    
    # Sender analysis
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 👥 Top Senders")
        top_senders = filtered_df['sender'].value_counts().head(10)
        
        fig = px.bar(y=top_senders.index, x=top_senders.values,
                     orientation='h',
                     labels={'x': 'Number of Emails', 'y': 'Sender'})
        fig.update_layout(
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            font_color='#e0e0e0',
            yaxis={'categoryorder':'total ascending'}
        )
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.markdown("### 🏷️ Email Categories")
        category_counts = filtered_df['purpose'].value_counts()
        
        fig = go.Figure(data=[go.Pie(
            labels=category_counts.index,
            values=category_counts.values,
            hole=0.4
        )])
        
        fig.update_layout(
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            font_color='#e0e0e0'
        )
        st.plotly_chart(fig, use_container_width=True)
    
    # Response time analysis
    st.markdown("### ⏱️ Response Time Analysis")
    response_emails = filtered_df[filtered_df['response_needed']]
    
    fig = px.box(response_emails, x='priority', y='estimated_time',
                 color='priority',
                 color_discrete_map={
                     'CRITICAL': '#f44336',
                     'HIGH': '#ffc107',
                     'MEDIUM': '#00c853',
                     'LOW': '#8d8d8d'
                 },
                 labels={'estimated_time': 'Estimated Response Time (minutes)'})
    
    fig.update_layout(
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font_color='#e0e0e0',
        showlegend=False
    )
    st.plotly_chart(fig, use_container_width=True)

def display_settings():
    """Display settings and preferences"""
    st.markdown("## ⚙️ Settings")
    
    # User preferences
    st.markdown("### User Preferences")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### Email Management")
        auto_archive = st.checkbox("Auto-archive low priority emails after 30 days", value=True)
        smart_notifications = st.checkbox("Smart notifications for critical emails only", value=True)
        daily_summary = st.checkbox("Send daily email summary", value=False)
        
        if daily_summary:
            summary_time = st.time_input("Summary delivery time", value=datetime.strptime("09:00", "%H:%M").time())
    
    with col2:
        st.markdown("#### AI Assistant Settings")
        autonomous_mode = st.checkbox("Enable autonomous mode", value=st.session_state.autonomous_mode)
        
        if autonomous_mode != st.session_state.autonomous_mode:
            st.session_state.autonomous_mode = autonomous_mode
            st.rerun()
        
        suggestion_frequency = st.select_slider(
            "Suggestion frequency",
            options=["Minimal", "Balanced", "Proactive"],
            value="Balanced"
        )
        
        response_style = st.selectbox(
            "Response style",
            ["Professional", "Friendly", "Concise", "Detailed"]
        )
    
    # Important senders
    st.markdown("### Important Senders")
    st.info("Emails from these senders will always be marked as high priority")
    
    important_senders = st.text_area(
        "Enter email addresses (one per line)",
        value="boss@company.com\nceo@company.com\nimportant.client@example.com",
        height=100
    )
    
    # Filtered domains
    st.markdown("### Filtered Domains")
    st.info("Emails from these domains will be automatically categorized as low priority")
    
    filtered_domains = st.text_area(
        "Enter domains (one per line)",
        value="@newsletter.com\n@promotions.com\n@notifications.com",
        height=100
    )
    
    # Integration settings
    st.markdown("### Integrations")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        google_cal = st.checkbox("Google Calendar", value=True)
        if google_cal:
            st.success("✓ Connected")
    
    with col2:
        slack = st.checkbox("Slack", value=False)
        if slack:
            st.info("Click to connect")
    
    with col3:
        teams = st.checkbox("Microsoft Teams", value=False)
        if teams:
            st.info("Click to connect")
    
    # Save button
    if st.button("Save Settings", type="primary", use_container_width=True):
        st.success("Settings saved successfully!")

def display_email_details():
    """Display detailed view of selected email"""
    if st.session_state.selected_email is None:
        st.info("No email selected")
        return
    
    email = st.session_state.selected_email
    
    # Email header
    st.markdown(f"## {email['subject']}")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown(f"**From:** {email['sender']}")
    
    with col2:
        st.markdown(f"**Sent:** {email['sent_time'].strftime('%Y-%m-%d %H:%M')}")
    
    with col3:
        st.markdown(f"**Priority:** <span class='status-badge {email['priority'].lower()}'>{email['priority']}</span>", 
                   unsafe_allow_html=True)
    
    with col4:
        st.markdown(f"**Category:** {email['purpose']}")
    
    # Email body
    st.markdown("### Email Content")
    st.markdown(f"""
    <div style='background-color: #1a1c23; padding: 1.5rem; border-radius: 10px; margin: 1rem 0;'>
        {email['body']}
    </div>
    """, unsafe_allow_html=True)
    
    # AI Analysis
    st.markdown("### 🤖 Maia's Analysis")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### Summary")
        st.info(email['summary'])
        
        st.markdown("#### Suggested Actions")
        if email['response_needed']:
            st.success("✓ Response required")
            st.info(f"Estimated time: {email['estimated_time']} minutes")
        else:
            st.info("No immediate action required")
    
    with col2:
        st.markdown("#### Key Points")
        st.markdown("""
        - Contract review deadline tomorrow
        - Budget approval needed
        - Client waiting for response
        """)
        
        st.markdown("#### Related Emails")
        st.info("3 previous emails in this thread")
    
    # Action buttons
    st.markdown("### Actions")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if st.button("✍️ Draft Reply", type="primary", use_container_width=True):
            st.session_state.current_tab = 'Chat'
            st.session_state.chat_messages.append({
                'role': 'assistant',
                'content': f"I'll help you draft a reply to '{email['subject']}'. Here's a suggested response:\n\n[Draft will appear here]"
            })
            st.rerun()
    
    with col2:
        if st.button("📅 Schedule Meeting", use_container_width=True):
            st.success("Opening calendar...")
    
    with col3:
        if st.button("🏷️ Change Priority", use_container_width=True):
            # Priority change logic
            pass
    
    with col4:
        if st.button("🗑️ Archive", use_container_width=True):
            st.success("Email archived")

# Main App Navigation
def main():
    if st.session_state.email_data is None:
        st.session_state.email_data = generate_mock_emails(100)
    display_header()
    
    # Create tabs
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "📊 Dashboard", 
        "📥 Inbox", 
        "💬 Chat", 
        "📈 Insights", 
        "⚙️ Settings",
        "📧 Email Details"
    ])
    
    with tab1:
        display_dashboard()
    
    with tab2:
        display_inbox()
    
    with tab3:
        display_chat()
    
    with tab4:
        display_insights()
    
    with tab5:
        display_settings()
    
    with tab6:
        display_email_details()
    
    # Footer
    st.markdown("---")
    st.markdown(
        "<p style='text-align: center; color: #8d8d8d;'>Maia Email Agent • AI-Powered Email Management • Made with ❤️</p>",
        unsafe_allow_html=True
    )

if __name__ == "__main__":
    main()