# Maia - AI Email Agent

An intelligent email management assistant powered by Claude AI and Gmail API that helps you manage your inbox efficiently.

## Features

- **Intelligent Email Classification**: Automatically categorizes emails by priority (CRITICAL, HIGH, MEDIUM, LOW)
- **Smart Summarization**: Generates concise summaries of important emails
- **Proactive Suggestions**: Offers intelligent suggestions based on email patterns
- **Learning System**: Improves classification accuracy based on user feedback
- **Memory System**: Remembers user preferences and patterns
- **Autonomous Mode**: Can operate proactively to manage your inbox
- **Draft Generation**: Creates email responses using AI
- **Google Calendar Integration**: Schedule email checking times
- **Action Tracking**: Queue and track email actions (archive, reply, etc.)

## Tech Stack

- **AI/ML**: Anthropic Claude API, Scikit-learn for ML classification
- **Backend**: Python, Google Cloud Functions
- **Frontend**: Streamlit for web UI
- **Database**: Google Firestore
- **APIs**: Gmail API, Google Calendar API
- **Storage**: Google Cloud Storage

## Prerequisites

- Python 3.8+
- Google Cloud Project with enabled APIs:
  - Gmail API
  - Google Calendar API
  - Firestore
  - Cloud Storage
  - Secret Manager
- Anthropic API key
- Gmail OAuth 2.0 credentials

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/SaKinLord/ai-email-agent/edit/main/README.md
   cd ai-email-agent
