# -*- coding: utf-8 -*-
"""
Modern UI Components for Maia Email Agent
Clean, assistant-first interface with improved performance and UX
"""

import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
from typing import Dict, List, Any, Optional
from datetime import datetime
import logging
import html

# Modern Design System
class ModernDesign:
    """Modern design system with improved color palette and components"""
    
    # Enhanced Color Palette
    COLORS = {
        'primary': '#0066ff',
        'primary_light': '#4d94ff',
        'primary_dark': '#0047b3',
        'secondary': '#1a1d29',
        'background': '#0a0b0f',
        'surface': '#151821',
        'surface_light': '#1f222e',
        'text_primary': '#ffffff',
        'text_secondary': '#b8bcc8',
        'text_muted': '#6b7280',
        'success': '#10b981',
        'warning': '#f59e0b',
        'error': '#ef4444',
        'info': '#3b82f6',
        'accent': '#8b5cf6',
    }
    
    # Typography Scale
    TYPOGRAPHY = {
        'h1': '2.5rem',
        'h2': '2rem',
        'h3': '1.5rem',
        'h4': '1.25rem',
        'body': '1rem',
        'small': '0.875rem',
        'tiny': '0.75rem'
    }
    
    # Spacing Scale
    SPACING = {
        'xs': '0.25rem',
        'sm': '0.5rem',
        'md': '1rem',
        'lg': '1.5rem',
        'xl': '2rem',
        'xxl': '3rem'
    }
    
    @classmethod
    def get_css(cls) -> str:
        """Return complete modern CSS styling"""
        return f"""
        <style>
        /* CSS Custom Properties */
        :root {{
            --primary: {cls.COLORS['primary']};
            --primary-light: {cls.COLORS['primary_light']};
            --primary-dark: {cls.COLORS['primary_dark']};
            --secondary: {cls.COLORS['secondary']};
            --background: {cls.COLORS['background']};
            --surface: {cls.COLORS['surface']};
            --surface-light: {cls.COLORS['surface_light']};
            --text-primary: {cls.COLORS['text_primary']};
            --text-secondary: {cls.COLORS['text_secondary']};
            --text-muted: {cls.COLORS['text_muted']};
            --success: {cls.COLORS['success']};
            --warning: {cls.COLORS['warning']};
            --error: {cls.COLORS['error']};
            --info: {cls.COLORS['info']};
            --accent: {cls.COLORS['accent']};
        }}
        
        /* Base App Styling */
        .stApp {{
            background: linear-gradient(135deg, var(--background) 0%, var(--secondary) 100%);
            color: var(--text-primary);
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
        }}
        
        /* Enhanced Typography */
        .main-title {{
            font-size: {cls.TYPOGRAPHY['h1']};
            font-weight: 700;
            color: var(--text-primary);
            margin-bottom: {cls.SPACING['lg']};
            text-align: center;
        }}
        
        .section-title {{
            font-size: {cls.TYPOGRAPHY['h2']};
            font-weight: 600;
            color: var(--text-primary);
            margin-bottom: {cls.SPACING['md']};
            border-bottom: 2px solid var(--primary);
            padding-bottom: {cls.SPACING['sm']};
        }}
        
        .subsection-title {{
            font-size: {cls.TYPOGRAPHY['h3']};
            font-weight: 500;
            color: var(--text-secondary);
            margin-bottom: {cls.SPACING['sm']};
        }}
        
        /* Modern Card System */
        .modern-card {{
            background: var(--surface);
            border-radius: 16px;
            padding: {cls.SPACING['lg']};
            margin-bottom: {cls.SPACING['md']};
            border: 1px solid rgba(255, 255, 255, 0.08);
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
            backdrop-filter: blur(10px);
            transition: all 0.3s ease;
        }}
        
        .modern-card:hover {{
            transform: translateY(-2px);
            box-shadow: 0 8px 30px rgba(0, 102, 255, 0.2);
            border-color: rgba(0, 102, 255, 0.3);
        }}
        
        .priority-card {{
            border-left: 4px solid var(--primary);
            background: linear-gradient(135deg, var(--surface) 0%, var(--surface-light) 100%);
        }}
        
        .insight-card {{
            border: 1px solid var(--accent);
            background: linear-gradient(135deg, var(--surface) 0%, rgba(139, 92, 246, 0.1) 100%);
        }}
        
        /* Enhanced Chat Interface */
        .chat-container {{
            max-height: 600px;
            overflow-y: auto;
            padding: {cls.SPACING['md']};
            background: var(--surface);
            border-radius: 16px;
            border: 1px solid rgba(255, 255, 255, 0.08);
            margin-bottom: {cls.SPACING['md']};
        }}
        
        .chat-message {{
            padding: {cls.SPACING['md']};
            margin-bottom: {cls.SPACING['sm']};
            border-radius: 12px;
            animation: slideInMessage 0.3s ease-out;
            max-width: 85%;
        }}
        
        .user-message {{
            background: var(--primary);
            color: white;
            margin-left: auto;
            border-bottom-right-radius: 4px;
        }}
        
        .assistant-message {{
            background: var(--surface-light);
            color: var(--text-primary);
            border-bottom-left-radius: 4px;
        }}
        
        .reasoning-display {{
            background: var(--surface-light);
            border-left: 3px solid var(--info);
            padding: {cls.SPACING['md']};
            margin: {cls.SPACING['sm']} 0;
            border-radius: 0 8px 8px 0;
            font-size: {cls.TYPOGRAPHY['small']};
        }}
        
        .confidence-meter {{
            background: var(--surface-light);
            border-radius: 8px;
            padding: {cls.SPACING['sm']};
            margin: {cls.SPACING['xs']} 0;
        }}
        
        .confidence-bar {{
            height: 6px;
            border-radius: 3px;
            background: linear-gradient(90deg, var(--error) 0%, var(--warning) 50%, var(--success) 100%);
            position: relative;
            overflow: hidden;
        }}
        
        .confidence-indicator {{
            position: absolute;
            top: 0;
            left: 0;
            height: 100%;
            background: rgba(255, 255, 255, 0.3);
            border-radius: 3px;
            transition: width 0.5s ease;
        }}
        
        /* Modern Button System */
        .stButton > button {{
            background: linear-gradient(135deg, var(--primary) 0%, var(--primary-light) 100%);
            color: white;
            border: none;
            border-radius: 12px;
            padding: {cls.SPACING['sm']} {cls.SPACING['lg']};
            font-weight: 500;
            font-size: {cls.TYPOGRAPHY['body']};
            cursor: pointer;
            transition: all 0.2s ease;
            box-shadow: 0 2px 8px rgba(0, 102, 255, 0.3);
        }}
        
        .stButton > button:hover {{
            transform: translateY(-1px);
            box-shadow: 0 4px 12px rgba(0, 102, 255, 0.4);
            background: linear-gradient(135deg, var(--primary-light) 0%, var(--primary) 100%);
        }}
        
        .stButton > button:active {{
            transform: translateY(0);
        }}
        
        /* Secondary Button */
        .secondary-btn {{
            background: transparent !important;
            color: var(--text-secondary) !important;
            border: 1px solid rgba(255, 255, 255, 0.2) !important;
        }}
        
        .secondary-btn:hover {{
            background: var(--surface-light) !important;
            color: var(--text-primary) !important;
        }}
        
        /* Success/Warning/Error Buttons */
        .success-btn {{
            background: linear-gradient(135deg, var(--success) 0%, #059669 100%) !important;
        }}
        
        .warning-btn {{
            background: linear-gradient(135deg, var(--warning) 0%, #d97706 100%) !important;
        }}
        
        .error-btn {{
            background: linear-gradient(135deg, var(--error) 0%, #dc2626 100%) !important;
        }}
        
        /* Enhanced Form Styling */
        .stTextInput > div > div > input {{
            background: var(--surface);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 12px;
            color: var(--text-primary);
            padding: {cls.SPACING['md']};
            font-size: {cls.TYPOGRAPHY['body']};
        }}
        
        .stTextInput > div > div > input:focus {{
            border-color: var(--primary);
            box-shadow: 0 0 0 2px rgba(0, 102, 255, 0.2);
        }}
        
        .stSelectbox > div > div > select {{
            background: var(--surface);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 12px;
            color: var(--text-primary);
        }}
        
        /* Modern Data Display */
        .stDataFrame {{
            background: var(--surface);
            border-radius: 12px;
            border: 1px solid rgba(255, 255, 255, 0.08);
            overflow: hidden;
        }}
        
        .stDataFrame thead {{
            background: var(--surface-light);
        }}
        
        .stDataFrame th {{
            color: var(--text-primary) !important;
            font-weight: 600;
            padding: {cls.SPACING['md']} !important;
            border-bottom: 1px solid rgba(255, 255, 255, 0.1) !important;
        }}
        
        .stDataFrame td {{
            color: var(--text-secondary) !important;
            padding: {cls.SPACING['sm']} {cls.SPACING['md']} !important;
            border-bottom: 1px solid rgba(255, 255, 255, 0.05) !important;
        }}
        
        /* Navigation & Tabs */
        .stTabs {{
            background: var(--surface);
            border-radius: 16px;
            padding: {cls.SPACING['sm']};
            margin-bottom: {cls.SPACING['lg']};
        }}
        
        .stTabs [data-baseweb="tab-list"] {{
            gap: {cls.SPACING['sm']};
            background: var(--surface-light);
            border-radius: 12px;
            padding: {cls.SPACING['xs']};
        }}
        
        .stTabs [data-baseweb="tab"] {{
            background: transparent;
            color: var(--text-secondary);
            border-radius: 8px;
            padding: {cls.SPACING['sm']} {cls.SPACING['md']};
            font-weight: 500;
            transition: all 0.2s ease;
        }}
        
        .stTabs [aria-selected="true"] {{
            background: var(--primary);
            color: white;
            box-shadow: 0 2px 8px rgba(0, 102, 255, 0.3);
        }}
        
        /* Metrics & Stats */
        .metric-card {{
            background: var(--surface);
            border-radius: 12px;
            padding: {cls.SPACING['lg']};
            text-align: center;
            border: 1px solid rgba(255, 255, 255, 0.08);
            transition: all 0.2s ease;
        }}
        
        .metric-card:hover {{
            transform: translateY(-2px);
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.2);
        }}
        
        .metric-value {{
            font-size: {cls.TYPOGRAPHY['h2']};
            font-weight: 700;
            color: var(--primary);
            margin-bottom: {cls.SPACING['xs']};
        }}
        
        .metric-label {{
            font-size: {cls.TYPOGRAPHY['small']};
            color: var(--text-secondary);
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}
        
        /* Priority Indicators */
        .priority-critical {{
            color: var(--error);
            background: rgba(239, 68, 68, 0.1);
            padding: {cls.SPACING['xs']} {cls.SPACING['sm']};
            border-radius: 6px;
            font-weight: 600;
            font-size: {cls.TYPOGRAPHY['small']};
        }}
        
        .priority-high {{
            color: var(--warning);
            background: rgba(245, 158, 11, 0.1);
            padding: {cls.SPACING['xs']} {cls.SPACING['sm']};
            border-radius: 6px;
            font-weight: 600;
            font-size: {cls.TYPOGRAPHY['small']};
        }}
        
        .priority-medium {{
            color: var(--info);
            background: rgba(59, 130, 246, 0.1);
            padding: {cls.SPACING['xs']} {cls.SPACING['sm']};
            border-radius: 6px;
            font-weight: 600;
            font-size: {cls.TYPOGRAPHY['small']};
        }}
        
        .priority-low {{
            color: var(--success);
            background: rgba(16, 185, 129, 0.1);
            padding: {cls.SPACING['xs']} {cls.SPACING['sm']};
            border-radius: 6px;
            font-weight: 600;
            font-size: {cls.TYPOGRAPHY['small']};
        }}
        
        /* Animations */
        @keyframes slideInMessage {{
            from {{
                opacity: 0;
                transform: translateY(10px);
            }}
            to {{
                opacity: 1;
                transform: translateY(0);
            }}
        }}
        
        @keyframes fadeIn {{
            from {{ opacity: 0; }}
            to {{ opacity: 1; }}
        }}
        
        @keyframes pulse {{
            0%, 100% {{ opacity: 1; }}
            50% {{ opacity: 0.5; }}
        }}
        
        /* Loading States */
        .loading-indicator {{
            display: inline-flex;
            align-items: center;
            gap: {cls.SPACING['sm']};
            color: var(--text-secondary);
            font-size: {cls.TYPOGRAPHY['small']};
        }}
        
        .loading-dots {{
            display: inline-flex;
            gap: 2px;
        }}
        
        .loading-dots span {{
            width: 4px;
            height: 4px;
            background: var(--primary);
            border-radius: 50%;
            animation: pulse 1.4s ease-in-out infinite;
        }}
        
        .loading-dots span:nth-child(2) {{
            animation-delay: 0.2s;
        }}
        
        .loading-dots span:nth-child(3) {{
            animation-delay: 0.4s;
        }}
        
        /* Responsive Design */
        @media (max-width: 768px) {{
            .modern-card {{
                padding: {cls.SPACING['md']};
                margin-bottom: {cls.SPACING['sm']};
            }}
            
            .chat-message {{
                max-width: 95%;
            }}
            
            .main-title {{
                font-size: {cls.TYPOGRAPHY['h2']};
            }}
        }}
        
        /* Scrollbar Styling */
        ::-webkit-scrollbar {{
            width: 8px;
        }}
        
        ::-webkit-scrollbar-track {{
            background: var(--surface);
            border-radius: 4px;
        }}
        
        ::-webkit-scrollbar-thumb {{
            background: var(--primary);
            border-radius: 4px;
        }}
        
        ::-webkit-scrollbar-thumb:hover {{
            background: var(--primary-light);
        }}
        </style>
        """


class ModernComponents:
    """Modern UI components with improved performance and UX"""
    
    @staticmethod
    def render_agent_header():
        """Render modern agent header with branding"""
        st.markdown("""
        <div class="modern-card" style="text-align: center; margin-bottom: 2rem;">
            <div style="display: flex; align-items: center; justify-content: center; gap: 1rem;">
                <img src="https://api.dicebear.com/6.x/bottts/svg?seed=Maia&backgroundColor=0066ff" 
                     width="60" height="60" style="border-radius: 50%; border: 3px solid var(--primary);">
                <div>
                    <h1 class="main-title" style="margin: 0; font-size: 2rem;">🤖 Maia</h1>
                    <p style="margin: 0; color: var(--text-secondary); font-size: 1.1rem;">Your Intelligent Email Assistant</p>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    @staticmethod
    def render_insight_dashboard(insights: Dict[str, Any]):
        """Render modern insights dashboard"""
        st.markdown('<div class="section-title">📊 Email Insights</div>', unsafe_allow_html=True)
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-value">{insights.get('total_emails', 0)}</div>
                <div class="metric-label">Total Emails</div>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-value">{insights.get('high_priority', 0)}</div>
                <div class="metric-label">High Priority</div>
            </div>
            """, unsafe_allow_html=True)
        
        with col3:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-value">{insights.get('processed_today', 0)}</div>
                <div class="metric-label">Processed Today</div>
            </div>
            """, unsafe_allow_html=True)
        
        with col4:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-value">{insights.get('avg_confidence', '0')}%</div>
                <div class="metric-label">Avg Confidence</div>
            </div>
            """, unsafe_allow_html=True)
    
    @staticmethod
    def render_reasoning_display(reasoning_chain: List[Any], confidence: float):
        """Render explainable reasoning display"""
        st.markdown(f"""
        <div class="reasoning-display">
            <h4 style="margin-top: 0; color: var(--info);">🧠 Decision Reasoning</h4>
            <div class="confidence-meter">
                <div style="display: flex; justify-content: space-between; margin-bottom: 0.5rem;">
                    <span style="font-size: 0.875rem; color: var(--text-secondary);">Confidence</span>
                    <span style="font-size: 0.875rem; font-weight: 600; color: var(--text-primary);">{confidence:.1f}%</span>
                </div>
                <div class="confidence-bar">
                    <div class="confidence-indicator" style="width: {confidence}%;"></div>
                </div>
            </div>
        """, unsafe_allow_html=True)
        
        for i, step in enumerate(reasoning_chain):
            icon = {
                'feedback_check': '👤',
                'llm_analysis': '🧠',
                'ml_prediction': '🤖',
                'rule_match': '📋'
            }.get(step.step_type, '•')
            
            st.markdown(f"""
            <div style="margin: 0.5rem 0; padding-left: 1rem;">
                <span style="color: var(--primary);">{icon}</span>
                <span style="color: var(--text-secondary); font-size: 0.875rem;">{html.escape(step.description)}</span>
            </div>
            """, unsafe_allow_html=True)
        
        st.markdown("</div>", unsafe_allow_html=True)
    
    @staticmethod
    def render_chat_interface():
        """Render modern chat interface"""
        st.markdown('<div class="section-title">💬 Chat with Maia</div>', unsafe_allow_html=True)
        
        # Chat container
        chat_container = st.container()
        
        with chat_container:
            st.markdown('<div class="chat-container" id="chat-messages">', unsafe_allow_html=True)
            
            # Display chat history
            if 'chat_history' not in st.session_state:
                st.session_state.chat_history = []
            
            for message in st.session_state.chat_history:
                message_class = "user-message" if message['role'] == 'user' else "assistant-message"
                st.markdown(f"""
                <div class="chat-message {message_class}">
                    {html.escape(message['content'])}
                </div>
                """, unsafe_allow_html=True)
            
            st.markdown('</div>', unsafe_allow_html=True)
        
        # Chat input
        user_input = st.text_input(
            "Ask me anything about your emails...",
            placeholder="e.g., 'Show me high priority emails' or 'Summarize my inbox'",
            key="chat_input"
        )
        
        col1, col2 = st.columns([6, 1])
        with col2:
            if st.button("Send", key="send_chat"):
                if user_input:
                    # Add user message to history
                    st.session_state.chat_history.append({
                        'role': 'user',
                        'content': user_input,
                        'timestamp': datetime.now()
                    })
                    
                    # Process and add assistant response
                    # This would connect to your existing chat logic
                    response = "I'm processing your request..."  # Placeholder
                    st.session_state.chat_history.append({
                        'role': 'assistant', 
                        'content': response,
                        'timestamp': datetime.now()
                    })
                    
                    st.rerun()
    
    @staticmethod
    def render_email_card(email_data: Dict[str, Any], reasoning_result: Optional[Any] = None, prefix: str = ""):
        """Render modern email card with reasoning"""
        priority = email_data.get('priority', 'MEDIUM')
        priority_class = f"priority-{priority.lower()}"
        
        # Format timestamp
        timestamp = email_data.get('processed_at', 'Unknown')
        if isinstance(timestamp, datetime):
            timestamp_str = timestamp.strftime('%H:%M')
        else:
            timestamp_str = str(timestamp)
        
        st.markdown(f"""
        <div class="modern-card priority-card">
            <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 1rem;">
                <div style="flex: 1;">
                    <div style="display: flex; align-items: center; gap: 0.5rem; margin-bottom: 0.5rem;">
                        <span class="{priority_class}">{priority}</span>
                        <span style="color: var(--text-muted); font-size: 0.875rem;">{timestamp_str}</span>
                    </div>
                    <h4 style="margin: 0 0 0.5rem 0; color: var(--text-primary);">{html.escape(email_data.get('subject', 'No Subject'))}</h4>
                    <p style="margin: 0; color: var(--text-secondary); font-size: 0.875rem;">From: {html.escape(email_data.get('sender', 'Unknown'))}</p>
                </div>
            </div>
        """, unsafe_allow_html=True)
        
        # Show reasoning if available
        if reasoning_result:
            ModernComponents.render_reasoning_display(
                reasoning_result.reasoning_chain, 
                reasoning_result.confidence
            )
        
        # Action buttons
        col1, col2, col3, col4 = st.columns(4)
        email_id = email_data.get('id', 'unknown')
        
        with col1:
            if st.button("View", key=f"{prefix}view_{email_id}"):
                # Toggle view state
                view_key = f"show_details_{email_id}"
                st.session_state[view_key] = not st.session_state.get(view_key, False)
        
        with col2:
            if st.button("Summarize", key=f"{prefix}summarize_{email_id}"):
                # Toggle summary state
                summary_key = f"show_summary_{email_id}"
                st.session_state[summary_key] = not st.session_state.get(summary_key, False)
        
        with col3:
            if st.button("📝 Extract Tasks", key=f"{prefix}extract_tasks_{email_id}"):
                # Toggle task extraction state
                tasks_key = f"show_tasks_{email_id}"
                st.session_state[tasks_key] = not st.session_state.get(tasks_key, False)
        
        with col4:
            if st.button("Actions", key=f"{prefix}actions_{email_id}"):
                # Toggle actions state
                actions_key = f"show_actions_{email_id}"
                st.session_state[actions_key] = not st.session_state.get(actions_key, False)
        
        # Show expanded content based on button states
        ModernComponents._render_expanded_content(email_data, email_id, prefix)
        
        st.markdown("</div>", unsafe_allow_html=True)
    
    @staticmethod
    def _render_expanded_content(email_data: Dict[str, Any], email_id: str, prefix: str = ""):
        """Render expanded content based on button states"""
        
        # Show email details if View was clicked
        if st.session_state.get(f"show_details_{email_id}", False):
            with st.expander("📧 Email Details", expanded=True):
                st.markdown("**Full Email Content:**")
                body_text = email_data.get('body_text', 'No email content available.')
                # Limit the body text to prevent overwhelming display
                if len(body_text) > 2000:
                    body_text = body_text[:2000] + "..."
                st.text_area("Email Body", value=body_text, height=200, disabled=True, key=f"{prefix}body_{email_id}", label_visibility="collapsed")
                
                # Additional details
                st.markdown("**Email Metadata:**")
                metadata_col1, metadata_col2 = st.columns(2)
                
                with metadata_col1:
                    st.markdown(f"**Thread ID:** {email_data.get('thread_id', 'Unknown')}")
                    st.markdown(f"**LLM Urgency:** {email_data.get('llm_urgency', 'Unknown')}")
                
                with metadata_col2:
                    st.markdown(f"**LLM Purpose:** {email_data.get('llm_purpose', 'Unknown')}")
                    st.markdown(f"**Response Needed:** {email_data.get('response_needed', 'Unknown')}")
        
        # Show email summary if Summarize was clicked
        if st.session_state.get(f"show_summary_{email_id}", False):
            with st.expander("📝 Email Summary", expanded=True):
                summary = email_data.get('summary', 'No summary available for this email.')
                
                # Fix "Summary: nan" display bug
                import pandas as pd
                if not summary or pd.isna(summary):
                    display_summary = "No summary available for this email."
                else:
                    display_summary = summary
                
                st.markdown(f"**Summary:** {display_summary}")
                
                # Additional insights if available
                insights = email_data.get('insights')
                if insights:
                    st.markdown("**Additional Insights:**")
                    
                    # Handle both string and dictionary insights properly
                    if isinstance(insights, dict):
                        # Check if we have any meaningful content
                        has_content = False
                        
                        # Handle suggestions
                        suggestions = insights.get('suggestions', [])
                        if suggestions and isinstance(suggestions, list) and any(suggestions):
                            has_content = True
                            st.markdown("💡 **Proactive Suggestions:**")
                            for suggestion in suggestions:
                                if suggestion:  # Only show non-empty suggestions
                                    st.markdown(f"- {suggestion}")
                        
                        # Handle actions
                        actions = insights.get('actions', [])
                        if actions and isinstance(actions, list) and any(actions):
                            has_content = True
                            st.markdown("⚡️ **Suggested Actions:**")
                            for action in actions:
                                if isinstance(action, dict):
                                    # Format structured action data
                                    action_type = action.get('type', 'Action')
                                    description = action.get('description', str(action))
                                    st.markdown(f"- **{action_type}:** {description}")
                                elif action:  # Simple string action
                                    st.markdown(f"- {action}")
                        
                        # Handle any other insights keys (but exclude technical metadata)
                        processed_keys = {'suggestions', 'actions', 'type'}
                        excluded_keys = {'email_id', 'id', 'timestamp', 'confidence', 'estimated_time', 'urgency_score', 'response_needed'}
                        
                        for key, value in insights.items():
                            if key not in processed_keys and key not in excluded_keys and value:
                                # Only show user-relevant insights, not technical metadata
                                if isinstance(value, (str, int, float)) and len(str(value)) > 50:
                                    # Skip very long technical strings
                                    continue
                                    
                                has_content = True
                                formatted_key = key.replace('_', ' ').title()
                                if isinstance(value, list) and value:
                                    st.markdown(f"📋 **{formatted_key}:**")
                                    for item in value:
                                        if item:
                                            st.markdown(f"- {item}")
                                else:
                                    st.markdown(f"• **{formatted_key}:** {value}")
                        
                        # Show empty state if no meaningful content
                        if not has_content:
                            st.markdown("No additional AI insights were generated for this email.")
                    
                    else:
                        # Handle string insights directly
                        st.markdown(insights)
                
                # Estimated time and urgency (user-friendly formatting)
                est_time = email_data.get('estimated_time')
                if est_time:
                    try:
                        # Convert to float and format nicely
                        time_value = float(est_time)
                        if time_value <= 1:
                            time_display = "⚡ Quick (< 1 minute)"
                        elif time_value <= 5:
                            time_display = f"🕐 Short (~{int(time_value)} minutes)"
                        elif time_value <= 15:
                            time_display = f"⏰ Medium (~{int(time_value)} minutes)"
                        else:
                            time_display = f"📅 Extended (~{int(time_value)} minutes)"
                        
                        st.markdown(f"**Estimated Time:** {time_display}")
                    except (ValueError, TypeError):
                        # Fallback for non-numeric values
                        st.markdown(f"**Estimated Time:** {est_time}")
        
        # Show task extraction if Extract Tasks was clicked
        if st.session_state.get(f"show_tasks_{email_id}", False):
            ModernComponents._render_task_extraction(email_data, email_id, prefix)
        
        # Show actions menu if Actions was clicked
        if st.session_state.get(f"show_actions_{email_id}", False):
            with st.expander("⚡ Email Actions", expanded=True):
                st.markdown("**Available Actions:**")
                
                action_col1, action_col2, action_col3 = st.columns(3)
                
                with action_col1:
                    if st.button("✉️ Reply", key=f"{prefix}reply_{email_id}"):
                        st.success("Reply functionality coming soon!")
                        # TODO: Implement reply functionality
                
                with action_col2:
                    if st.button("➡️ Forward", key=f"{prefix}forward_{email_id}"):
                        st.success("Forward functionality coming soon!")
                        # TODO: Implement forward functionality
                
                with action_col3:
                    if st.button("🗄️ Archive", key=f"{prefix}archive_{email_id}"):
                        st.success("Archive functionality coming soon!")
                        # TODO: Implement archive functionality
                
                # Additional actions
                st.markdown("**More Actions:**")
                more_col1, more_col2 = st.columns(2)
                
                with more_col1:
                    if st.button("🏷️ Add Label", key=f"{prefix}label_{email_id}"):
                        st.info("Label functionality coming soon!")
                
                with more_col2:
                    if st.button("⭐ Mark Important", key=f"{prefix}important_{email_id}"):
                        st.info("Mark important functionality coming soon!")

    @staticmethod
    def _render_task_extraction(email_data: Dict[str, Any], email_id: str, prefix: str = ""):
        """Render task extraction functionality"""
        
        with st.expander("📝 Extracted Tasks", expanded=True):
            email_body = email_data.get('body_text', '')
            email_subject = email_data.get('subject', '')
            
            if not email_body or not email_subject:
                st.warning("Cannot extract tasks: Email content or subject is missing.")
                return
            
            # Check if we have a cached result
            cache_key = f"tasks_{email_id}"
            
            if cache_key not in st.session_state:
                # Show loading while extracting tasks
                with st.spinner("🤖 Analyzing email for actionable tasks..."):
                    try:
                        # Get the LLM manager from session state
                        llm_manager = st.session_state.get('llm_manager')
                        
                        if llm_manager is None:
                            st.error("❌ Task extraction unavailable: AI system not initialized.")
                            return
                        
                        # Extract tasks using the hybrid LLM system
                        tasks = llm_manager.extract_tasks_from_email(email_body, email_subject)
                        
                        # Cache the result
                        st.session_state[cache_key] = tasks
                        
                    except Exception as e:
                        logging.error(f"Task extraction failed: {e}")
                        st.error(f"❌ Task extraction failed: {str(e)}")
                        return
            
            # Get cached or newly extracted tasks
            tasks = st.session_state.get(cache_key)
            
            if tasks is None:
                st.error("❌ Task extraction failed due to an error. Please try again.")
                
                # Add a retry button
                if st.button("🔄 Retry Task Extraction", key=f"{prefix}retry_tasks_{email_id}"):
                    # Clear cache and trigger re-extraction
                    if cache_key in st.session_state:
                        del st.session_state[cache_key]
                    st.rerun()
                return
            
            elif len(tasks) == 0:
                st.info("📋 No actionable tasks found in this email.")
                st.markdown("*This email appears to be informational or doesn't contain specific action items.*")
            
            else:
                st.success(f"✅ Found {len(tasks)} actionable task{'s' if len(tasks) != 1 else ''}")
                
                # Display each task in a clean format
                for i, task in enumerate(tasks, 1):
                    with st.container():
                        st.markdown(f"""
                        <div class="modern-card" style="margin: 0.5rem 0; padding: 1rem; border-left: 4px solid var(--primary);">
                            <div style="display: flex; align-items: flex-start; gap: 0.75rem;">
                                <div style="background: var(--primary); color: white; border-radius: 50%; width: 24px; height: 24px; display: flex; align-items: center; justify-content: center; font-size: 0.875rem; font-weight: 600; flex-shrink: 0; margin-top: 0.125rem;">
                                    {i}
                                </div>
                                <div style="flex: 1;">
                                    <div style="color: var(--text-primary); font-weight: 500; margin-bottom: 0.5rem;">
                                        {html.escape(task.get('task_description', 'No description'))}
                                    </div>
                        """, unsafe_allow_html=True)
                        
                        # Show deadline if available
                        deadline = task.get('deadline')
                        if deadline:
                            st.markdown(f"""
                                    <div style="color: var(--warning); font-size: 0.875rem; margin-bottom: 0.25rem;">
                                        ⏰ <strong>Deadline:</strong> {html.escape(str(deadline))}
                                    </div>
                            """, unsafe_allow_html=True)
                        
                        # Show stakeholders if available
                        stakeholders = task.get('stakeholders', [])
                        if stakeholders:
                            stakeholder_text = ", ".join(stakeholders)
                            st.markdown(f"""
                                    <div style="color: var(--text-secondary); font-size: 0.875rem; margin-bottom: 0.5rem;">
                                        👥 <strong>Stakeholders:</strong> {html.escape(stakeholder_text)}
                                    </div>
                            """, unsafe_allow_html=True)
                        
                        st.markdown("""
                                </div>
                            </div>
                        """, unsafe_allow_html=True)
                        
                        # Add Save Task button for each task
                        ModernComponents._render_save_task_button(task, email_id, i, prefix)
                
                # Add action buttons for the tasks
                st.markdown("---")
                task_action_col1, task_action_col2 = st.columns(2)
                
                with task_action_col1:
                    if st.button("📋 Copy Tasks to Clipboard", key=f"{prefix}copy_tasks_{email_id}"):
                        # Format tasks for copying
                        task_text = f"Tasks from: {email_subject}\n\n"
                        for i, task in enumerate(tasks, 1):
                            task_text += f"{i}. {task.get('task_description', 'No description')}\n"
                            if task.get('deadline'):
                                task_text += f"   Deadline: {task.get('deadline')}\n"
                            if task.get('stakeholders'):
                                task_text += f"   Stakeholders: {', '.join(task.get('stakeholders'))}\n"
                            task_text += "\n"
                        
                        # In a real implementation, you'd copy to clipboard
                        # For now, show the formatted text
                        st.text_area("Copy this text:", value=task_text, height=100, key=f"{prefix}task_copy_{email_id}")
                
                with task_action_col2:
                    if st.button("🔄 Re-analyze Tasks", key=f"{prefix}reanalyze_tasks_{email_id}"):
                        # Clear cache and trigger re-extraction
                        if cache_key in st.session_state:
                            del st.session_state[cache_key]
                        st.rerun()

    @staticmethod
    def _render_save_task_button(task: Dict[str, Any], email_id: str, task_index: int, prefix: str = ""):
        """Render save task button for individual tasks"""
        
        # Import task utilities
        try:
            from task_utils import save_task_to_firestore, is_task_already_saved
        except ImportError:
            st.error("❌ Task management system not available")
            return
        
        task_description = task.get('task_description', '')
        user_id = "default_user"  # Default user ID - in production this would come from authentication
        
        # Check if task is already saved
        is_saved = is_task_already_saved(task_description, email_id, user_id)
        
        # Create unique button key
        save_button_key = f"{prefix}save_task_{email_id}_{task_index}"
        saved_state_key = f"task_saved_{email_id}_{task_index}"
        
        # Check if this specific task was just saved in this session
        just_saved = st.session_state.get(saved_state_key, False)
        
        # Button column
        button_col1, button_col2 = st.columns([1, 3])
        
        with button_col1:
            if is_saved or just_saved:
                # Show saved state
                st.markdown("""
                <div style="display: flex; align-items: center; gap: 0.5rem; color: var(--success); font-size: 0.875rem; font-weight: 500;">
                    ✅ Saved
                </div>
                """, unsafe_allow_html=True)
            else:
                # Show save button
                if st.button("➕ Save Task", key=save_button_key, help="Save this task to My Tasks"):
                    try:
                        # Save the task to Firestore
                        task_id = save_task_to_firestore(task, user_id, email_id)
                        
                        # Mark as saved in session state
                        st.session_state[saved_state_key] = True
                        
                        # Show success message
                        st.success(f"✅ Task saved successfully!")
                        st.rerun()
                        
                    except Exception as e:
                        st.error(f"❌ Failed to save task: {str(e)}")
        
        # Close the task card div
        st.markdown("</div>", unsafe_allow_html=True)

    @staticmethod
    def render_loading_state(message: str = "Processing..."):
        """Render modern loading state"""
        st.markdown(f"""
        <div class="loading-indicator">
            <span>{message}</span>
            <div class="loading-dots">
                <span></span>
                <span></span>
                <span></span>
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    @staticmethod
    def render_quick_actions():
        """Render quick action buttons"""
        st.markdown('<div class="subsection-title">⚡ Quick Actions</div>', unsafe_allow_html=True)
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            if st.button("📥 Check Inbox", key="quick_inbox"):
                return "check_inbox"
        
        with col2:
            if st.button("🔍 High Priority", key="quick_priority"):
                return "show_priority"
        
        with col3:
            if st.button("📊 Analytics", key="quick_analytics"):
                return "show_analytics"
        
        with col4:
            if st.button("⚙️ Settings", key="quick_settings"):
                return "show_settings"
        
        return None


def create_modern_plotly_chart(data: Dict[str, Any], chart_type: str = 'bar') -> go.Figure:
    """Create modern Plotly charts with dark theme"""
    
    if chart_type == 'bar':
        fig = go.Figure(data=[
            go.Bar(
                x=list(data.keys()),
                y=list(data.values()),
                marker=dict(
                    color=ModernDesign.COLORS['primary'],
                    line=dict(color=ModernDesign.COLORS['primary_dark'], width=1)
                )
            )
        ])
    
    elif chart_type == 'pie':
        fig = go.Figure(data=[
            go.Pie(
                labels=list(data.keys()),
                values=list(data.values()),
                marker=dict(
                    colors=[ModernDesign.COLORS['primary'], ModernDesign.COLORS['accent'], 
                           ModernDesign.COLORS['success'], ModernDesign.COLORS['warning']]
                )
            )
        ])
    
    # Apply modern dark theme
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor=ModernDesign.COLORS['surface'],
        plot_bgcolor=ModernDesign.COLORS['surface'],
        font=dict(
            family="Inter, sans-serif",
            size=12,
            color=ModernDesign.COLORS['text_secondary']
        ),
        margin=dict(l=20, r=20, t=40, b=20),
        height=400
    )
    
    return fig