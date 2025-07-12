# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is **Maia** - an intelligent email processing and management system that uses AI to automatically classify, analyze, and manage Gmail emails. The system combines machine learning models, large language models (GPT-4, Claude), and rule-based logic to provide automated email prioritization and actionable insights.

## Architecture

The system uses a hybrid Python backend + React frontend architecture:

- **Backend**: Python Flask API server with Google Cloud Functions integration
- **Frontend**: React 19 with TypeScript, Tailwind CSS, and Zustand state management  
- **Database**: Google Cloud Firestore for document storage and real-time sync
- **AI/ML**: Hybrid LLM system (OpenAI GPT-4, Anthropic Claude) + scikit-learn models
- **Authentication**: Google OAuth 2.0 with JWT tokens
- **Real-time**: WebSocket communication via Socket.IO

## Key Entry Points

- **`main.py`**: Main email processing logic and Google Cloud Function handler
- **`api_server.py`**: Flask API server providing REST endpoints and WebSocket communication
- **`agent_logic.py`**: Core email analysis and Gmail API integration
- **`reasoning_integration.py`**: Enhanced reasoning system with explainable AI
- **`hybrid_llm_system.py`**: Multi-provider LLM routing and budget management
- **`database_utils.py`**: Firestore database operations and utilities
- **`frontend/src/App.tsx`**: React frontend application entry point

## Common Development Tasks

### Backend Development
```bash
# Install Python dependencies
pip install -r requirements.txt

# Run the Flask API server locally
python api_server.py

# Test email processing function
python main.py

# Run Python tests
pytest

# Format code with ruff (if available)
ruff format .
```

### Frontend Development
```bash
# Navigate to frontend directory
cd frontend

# Install dependencies
npm install

# Start development server
npm start

# Build for production
npm run build

# Run tests
npm test
```

### Google Cloud Functions Deployment
```bash
# Deploy main email processing function
gcloud functions deploy process_emails --runtime python39 --trigger-http

# Deploy with specific configuration
gcloud functions deploy process_emails --source . --entry-point process_emails_handler
```

## Configuration

The system uses `config.json` for configuration with these key sections:
- **`gmail`**: Gmail API credentials and fetch settings
- **`llm`**: LLM provider settings and API configurations
- **`classification`**: Email classification rules and sender/keyword lists
- **`autonomous_tasks`**: Automated action thresholds and enablement
- **`reasoning`**: AI reasoning engine rules and confidence thresholds

## Key Components

### Email Processing Flow
1. **Gmail API** fetches unread emails via `agent_logic.py`
2. **ML Models** provide initial classification via `ml_utils.py`
3. **LLM Analysis** enhances classification via `hybrid_llm_system.py`
4. **Reasoning Engine** makes final decisions via `reasoning_integration.py`
5. **Database** stores results via `database_utils.py`
6. **WebSocket** broadcasts updates to frontend via `api_server.py`

### Frontend State Management
- **Zustand stores** in `frontend/src/store/` manage application state
- **API service** in `frontend/src/services/api.ts` handles backend communication
- **WebSocket service** in `frontend/src/services/websocket.ts` manages real-time updates

### Authentication Flow
- Google OAuth 2.0 handled by `auth_utils.py`
- JWT tokens for session management
- Frontend auth state managed by `authStore.ts`

## Development Environment

- **Python 3.x** with virtual environment recommended
- **Node.js 16+** for frontend development
- **Google Cloud credentials** required for Gmail API and Firestore
- **OpenAI and Anthropic API keys** for LLM services

## Important Notes

- The system is designed for Gmail integration only
- All email processing is read-only with optional labeling
- AI models require API keys set in environment variables
- Budget tracking is enforced for LLM usage ($120/month GPT-4, $5/month Claude)
- WebSocket connections enable real-time dashboard updates
- User feedback triggers ML model retraining when thresholds are met
- System designed for deployment on Google Cloud Platform
- Supports autonomous actions (archiving, task creation) based on confidence thresholds
- Target performance: <5 seconds per email processing, 99% uptime
- Machine learning models retrain automatically when feedback exceeds thresholds (default: 10 corrections)

## Environment Variables Required

```bash
# Google Cloud Configuration
GOOGLE_APPLICATION_CREDENTIALS=path/to/service-account-key.json
GCS_BUCKET_NAME=your-bucket-name

# AI API Keys
OPENAI_API_KEY=your-openai-api-key
ANTHROPIC_API_KEY=your-anthropic-api-key

# Optional: Flask configuration
FLASK_ENV=development
```