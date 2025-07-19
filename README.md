# Maia - Intelligent Email Processing System

[![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)](https://python.org)
[![React](https://img.shields.io/badge/React-19.1.0-blue.svg)](https://reactjs.org)
[![TypeScript](https://img.shields.io/badge/TypeScript-4.9+-blue.svg)](https://typescriptlang.org)
[![Google Cloud](https://img.shields.io/badge/Google%20Cloud-Platform-blue.svg)](https://cloud.google.com)

Maia is an intelligent email processing and management system that uses AI to automatically classify, analyze, and manage Gmail emails. The system combines machine learning models, large language models (GPT-4, Claude), and rule-based logic to provide automated email prioritization, actionable insights, and autonomous task management.

## 🚀 Features

### Core Functionality
- **AI-Powered Email Classification**: Hybrid LLM system using OpenAI GPT-4 and Anthropic Claude
- **Real-time Processing**: Automatic processing of incoming Gmail emails
- **Intelligent Prioritization**: ML-based priority scoring with configurable thresholds
- **Autonomous Actions**: Auto-archiving, meeting preparation, and task creation
- **Smart Insights**: Email analysis with reasoning explanations and confidence scores

### Dashboard & UI
- **Real-time Dashboard**: Live updates via WebSocket communication
- **Interactive Charts**: Email analytics with visual insights
- **Responsive Design**: Modern React 19 frontend with Tailwind CSS
- **Multi-theme Support**: Light/dark mode with user preferences
- **Performance Monitoring**: Built-in performance tracking and optimization

### Integrations
- **Gmail API**: Read-only email access with optional labeling
- **Google Cloud Firestore**: Document storage and real-time synchronization
- **WebSocket Communication**: Real-time updates via Socket.IO
- **OAuth 2.0 Authentication**: Secure Google account integration
- **Webhook Support**: External task management system integration

## 🏗️ Architecture

### Backend (Python)
```
├── main.py                    # Google Cloud Function entry point
├── api_server.py              # Flask API server with WebSocket support
├── agent_logic.py             # Core email analysis and Gmail API integration
├── reasoning_integration.py   # Enhanced reasoning system with explainable AI
├── hybrid_llm_system.py       # Multi-provider LLM routing and budget management
├── database_utils.py          # Firestore database operations
├── auth_utils.py              # Google OAuth 2.0 authentication
├── ml_utils.py                # Machine learning models and training
└── task_utils.py              # Task automation and webhook integration
```

### Frontend (React + TypeScript)
```
├── src/
│   ├── components/
│   │   ├── auth/               # Authentication components
│   │   ├── dashboard/          # Main dashboard interface
│   │   ├── settings/           # Configuration management
│   │   └── common/             # Shared UI components
│   ├── store/                  # Zustand state management
│   ├── services/               # API and WebSocket services
│   └── hooks/                  # Custom React hooks
```

## 📦 Installation

### Prerequisites
- **Python 3.9+** with pip
- **Node.js 16+** with npm
- **Google Cloud Account** with Gmail API and Firestore enabled
- **API Keys**: OpenAI and Anthropic for LLM services

### Backend Setup

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd process_emails_gcf_function-source
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables**
   ```bash
   # Set required environment variables
   export GOOGLE_APPLICATION_CREDENTIALS=path/to/service-account-key.json
   export OPENAI_API_KEY=your-openai-api-key
   export ANTHROPIC_API_KEY=your-anthropic-api-key
   export GCS_BUCKET_NAME=your-bucket-name
   ```

5. **Set up configuration**
   ```bash
   cp config.template.json config.json
   # Edit config.json with your specific settings
   ```

### Frontend Setup

1. **Navigate to frontend directory**
   ```bash
   cd frontend
   ```

2. **Install dependencies**
   ```bash
   npm install
   ```

3. **Start development server**
   ```bash
   npm start
   ```

### Google Cloud Setup

1. **Enable APIs**
   - Gmail API
   - Cloud Firestore API
   - Cloud Functions API (for deployment)

2. **Create service account**
   - Download credentials JSON file
   - Set `GOOGLE_APPLICATION_CREDENTIALS` environment variable

3. **Configure OAuth 2.0**
   - Create OAuth 2.0 credentials in Google Cloud Console
   - Download credentials.json file
   - Place in project root directory

## 🔧 Configuration

### Core Configuration (`config.json`)

```json
{
  "gmail": {
    "scopes": ["https://www.googleapis.com/auth/gmail.readonly"],
    "fetch_max_results": 150,
    "fetch_labels": ["INBOX", "UNREAD"]
  },
  "llm": {
    "provider": "anthropic",
    "model_name": "claude-3-haiku-20240307",
    "analysis_max_tokens": 100,
    "temperature": 0.6
  },
  "classification": {
    "important_senders": ["boss@company.com"],
    "subject_keywords_high": ["urgent", "action required"],
    "subject_keywords_low": ["newsletter", "promotion"]
  },
  "autonomous_tasks": {
    "auto_archive": { "enabled": true, "confidence_threshold": 0.95 },
    "auto_task_creation": { "enabled": true, "confidence_threshold": 0.90 }
  }
}
```

### LLM Budget Management
- **GPT-4**: $120/month budget limit
- **Claude**: $5/month budget limit
- **Hybrid routing**: Automatic provider selection based on cost and availability

### Machine Learning
- **Auto-retraining**: Triggers after 10 user feedback corrections
- **Feature pipeline**: scikit-learn based classification models
- **Performance tracking**: Model accuracy and confidence monitoring

## 🚀 Usage

### Running Locally

1. **Start backend server**
   ```bash
   python api_server.py
   ```

2. **Start frontend (in separate terminal)**
   ```bash
   cd frontend
   npm start
   ```

3. **Access application**
   - Frontend: http://localhost:3000
   - API: http://localhost:5000

### Processing Emails

1. **Manual Processing**
   ```bash
   python main.py
   ```

2. **Automated Processing**
   - Set up Google Cloud Function deployment
   - Configure Cloud Scheduler for periodic execution

### Testing

```bash
# Backend tests
pytest

# Frontend tests
cd frontend
npm test

# Specific test files
python test_backend_fixes.py
```

## 📊 Performance & Monitoring

### Performance Targets
- **Processing Speed**: < 5 seconds per email
- **System Uptime**: 99% availability
- **Response Time**: < 2 seconds for API calls

### Monitoring Features
- Real-time performance metrics via `usePerformance` hook
- WebSocket connection health monitoring
- LLM API usage and budget tracking
- Machine learning model performance metrics

## 🔐 Security

### Authentication & Authorization
- **Google OAuth 2.0**: Secure user authentication
- **JWT Tokens**: Session management
- **Scoped Access**: Read-only Gmail access by default

### Data Protection
- **Environment Variables**: Secure API key storage
- **Firestore Security Rules**: Database access control
- **HTTPS Only**: Encrypted communication
- **No Secret Logging**: Secure credential handling

## 🌐 Deployment

### Google Cloud Functions

1. **Deploy email processor**
   ```bash
   gcloud functions deploy process_emails \
     --runtime python39 \
     --trigger-http \
     --source . \
     --entry-point process_emails_handler
   ```

2. **Deploy API server**
   ```bash
   gcloud functions deploy api_server \
     --runtime python39 \
     --trigger-http \
     --source . \
     --entry-point api_handler
   ```

### Frontend Deployment

1. **Build production version**
   ```bash
   cd frontend
   npm run build
   ```

2. **Deploy to hosting service**
   - Google Cloud Storage + Cloud CDN
   - Netlify, Vercel, or similar platforms

## 📁 Project Structure

```
process_emails_gcf_function-source/
├── 📄 config.json                  # Main configuration file
├── 📄 config.template.json         # Configuration template
├── 📄 requirements.txt             # Python dependencies
├── 🐍 main.py                      # Cloud Function entry point
├── 🐍 api_server.py                # Flask API server
├── 🐍 agent_logic.py               # Core email processing
├── 🐍 reasoning_integration.py     # AI reasoning system
├── 🐍 hybrid_llm_system.py         # LLM provider management
├── 🐍 database_utils.py            # Database operations
├── 🐍 auth_utils.py                # Authentication utilities
├── 🐍 ml_utils.py                  # Machine learning models
├── 🐍 task_utils.py                # Task automation
├── 📁 frontend/                    # React application
│   ├── 📄 package.json            # Frontend dependencies
│   ├── 📁 src/
│   │   ├── 📁 components/         # React components
│   │   ├── 📁 store/              # State management
│   │   ├── 📁 services/           # API services
│   │   └── 📁 hooks/              # Custom hooks
│   └── 📄 tailwind.config.js      # Styling configuration
└── 📁 venv/                       # Python virtual environment
```

## 🤝 Contributing

### Development Workflow
1. Create feature branch from `main`
2. Make changes following existing code conventions
3. Run tests and ensure they pass
4. Submit pull request with detailed description

### Code Style
- **Python**: Follow PEP 8 guidelines
- **TypeScript**: Use ESLint configuration
- **Commits**: Use conventional commit messages

### Testing Requirements
- Unit tests for new functionality
- Integration tests for API endpoints
- Frontend component testing with React Testing Library

## 📈 Roadmap

### Planned Features
- **Multi-provider Email Support**: Outlook, Exchange integration
- **Advanced Analytics**: Detailed reporting and insights
- **Mobile Application**: React Native mobile app
- **API Rate Limiting**: Enhanced request throttling
- **Batch Processing**: Bulk email operations

### Performance Improvements
- **Caching Layer**: Redis for improved response times
- **Parallel Processing**: Concurrent email analysis
- **Model Optimization**: Faster ML inference
- **Database Indexing**: Optimized Firestore queries

## 🐛 Troubleshooting

### Common Issues

1. **Gmail API Rate Limits**
   ```bash
   # Check API quotas in Google Cloud Console
   # Implement exponential backoff in requests
   ```

2. **LLM API Failures**
   ```bash
   # Verify API keys are set correctly
   # Check budget limits in config.json
   # Monitor provider status pages
   ```

3. **WebSocket Connection Issues**
   ```bash
   # Check CORS configuration
   # Verify Socket.IO versions match
   # Monitor network connectivity
   ```

4. **Database Connection Problems**
   ```bash
   # Verify Firestore permissions
   # Check service account credentials
   # Monitor database rules
   ```

### Debug Mode
```bash
# Enable debug logging
export FLASK_ENV=development
python api_server.py --debug
```

## 📜 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- **OpenAI**: GPT-4 language model
- **Anthropic**: Claude language model
- **Google Cloud**: Infrastructure and APIs
- **React Team**: Frontend framework
- **scikit-learn**: Machine learning library

## 📞 Support

For support and questions:
- 📧 Create an issue in the GitHub repository
- 🔍 Review CLAUDE.md for AI assistant guidance

---

**Maia** - Making email management intelligent and effortless 🤖✉️
