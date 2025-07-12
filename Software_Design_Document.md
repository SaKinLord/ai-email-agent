# SOFTWARE DESIGN DOCUMENT

**CENG 495 Senior Design Project I**  
**University of Turkish Aeronautical Association**

---

**Project Title:** Maia - Intelligent Email Processing and Management System  
**Project Member:** Mert Olgun  
**Project Advisor:** Abdülvahap Ömer Toprak  
**Date:** 25.06.2025

---

## 1. Introduction

### 1.1. Purpose of the System

The Maia Email Processing System is an AI-powered intelligent email assistant designed to automatically classify, analyze, and manage email communications. The system leverages advanced machine learning models, large language models (LLMs), and sophisticated reasoning engines to provide users with automated email prioritization, intelligent response suggestions, and autonomous task creation capabilities. The primary goal is to reduce email management overhead and enhance productivity by intelligently triaging incoming emails and providing actionable insights.

### 1.2. Scope of the System

The system encompasses the following core capabilities:
- **Automated Email Classification**: Real-time classification of emails by priority levels (CRITICAL, HIGH, MEDIUM, LOW)
- **Intelligent Purpose Detection**: Identification of email types (action requests, meeting invitations, newsletters, promotions)
- **AI-Powered Analysis**: Content analysis using multiple LLM providers (GPT-4, Claude-3-Haiku)
- **Autonomous Actions**: Automated task creation, email archiving, and priority adjustments based on confidence thresholds
- **Learning and Adaptation**: Continuous improvement through user feedback and machine learning model retraining
- **Real-time Processing**: WebSocket-based live updates with modern React frontend
- **Multi-Model Integration**: Hybrid approach combining rule-based logic, ML models, and LLMs

**System Boundaries:**
- Integrates exclusively with Gmail through Google APIs
- Supports only English language content analysis
- Focuses on business and professional email management
- Does not perform actual email sending or modification (read-only with labeling capabilities)

### 1.3. Objectives and Success Criteria of the Project

**Primary Objectives:**
1. **Accurate Email Classification**: Achieve 95%+ accuracy in email priority classification through hybrid AI approach
2. **Real-time Processing**: Process incoming emails within 5 seconds of receipt with live frontend updates
3. **Cost-Effective AI Usage**: Implement budget-aware LLM routing to optimize API costs ($125/month combined budget)
4. **User Adaptation**: Improve classification accuracy by 10% within 30 days through user feedback learning
5. **Autonomous Operation**: Execute autonomous actions (archiving, task creation) with 90%+ user satisfaction

**Success Criteria:**
- Email processing latency under 5 seconds for 99% of emails
- User feedback integration with 48-hour model retraining cycle
- Frontend responsiveness with sub-100ms WebSocket update propagation
- Budget tracking accuracy within 5% of actual API costs
- System uptime of 99.5% during operational hours

### 1.4. Definitions, Acronyms, and Abbreviations

| Term | Definition |
|------|------------|
| **API** | Application Programming Interface |
| **GCF** | Google Cloud Functions |
| **LLM** | Large Language Model |
| **ML** | Machine Learning |
| **NLP** | Natural Language Processing |
| **OAuth** | Open Authorization protocol |
| **CRUD** | Create, Read, Update, Delete operations |
| **WebSocket** | Real-time bidirectional communication protocol |
| **JWT** | JSON Web Token for authentication |
| **TF-IDF** | Term Frequency-Inverse Document Frequency |
| **Maia** | The system's name, referring to the AI email assistant |
| **Reasoning Engine** | Component that provides explainable AI decision-making |
| **Hybrid LLM System** | Multi-provider AI system for cost optimization |
| **Agent Memory** | System for maintaining conversation context and user preferences |
| **Autonomous Actions** | System-initiated actions based on confidence thresholds |

### 1.5. References

**External Libraries and Dependencies:**
- **AI/ML Services**: OpenAI GPT-4 API, Anthropic Claude API, scikit-learn 1.6.1
- **Google Cloud Services**: Firestore, Storage, Secret Manager, Gmail API
- **Backend Framework**: Flask 3.1.0, functions-framework 3.8.2
- **Frontend Framework**: React 19.1.0, TypeScript 4.9.5, Tailwind CSS 3.4.17
- **Real-time Communication**: Socket.IO 4.8.1, Flask-SocketIO
- **Authentication**: google-auth-oauthlib 1.2.1, PyJWT
- **Data Processing**: pandas 2.2.3, numpy 2.2.4, joblib 1.4.2
- **NLP Libraries**: spacy 3.8.7, nltk 3.9.1, transformers 4.52.3
- **Testing**: pytest 8.4.0, @testing-library/react 16.3.0

### 1.6. Overview

This document provides a comprehensive technical specification for the Maia Email Processing System. Section 2 analyzes the current email management challenges that the system addresses. Section 3 details the proposed system architecture, functional requirements, and technical specifications. Section 3.4 presents the system models including use cases, class diagrams, and sequence diagrams that illustrate the system's behavior and interactions.

## 2. Current System

This is a greenfield project, and there is no existing system to replace. The project addresses the universal challenge of email overload in professional environments, where users typically receive 50-200 emails daily without intelligent filtering or prioritization. Traditional email clients provide basic sorting and filtering capabilities but lack AI-powered analysis, contextual understanding, or learning capabilities. The Maia system introduces a new paradigm of intelligent email assistance that was previously unavailable.

## 3. Proposed System

### 3.1. Overview

The Maia Email Processing System employs a modern microservices architecture combining Python-based backend services with a React TypeScript frontend. The system is designed for deployment on Google Cloud Platform, leveraging managed services for scalability and reliability.

**Core Architectural Components:**
- **Backend Services**: Python Flask API server with Google Cloud Functions integration
- **Frontend Application**: React 19 with TypeScript, Tailwind CSS, and Zustand state management
- **Database Layer**: Google Cloud Firestore for document storage and real-time synchronization
- **AI/ML Layer**: Hybrid system combining OpenAI GPT-4, Anthropic Claude, and custom scikit-learn models
- **Authentication**: Google OAuth 2.0 with JWT token management
- **Real-time Communication**: WebSocket integration using Socket.IO

**Technology Stack:**
- **Backend**: Python 3.x, Flask, Google Cloud Functions
- **Frontend**: React 19, TypeScript 4.9, Tailwind CSS 3.4
- **Database**: Google Cloud Firestore (NoSQL document database)
- **AI Services**: OpenAI GPT-4, Anthropic Claude-3-Haiku
- **Deployment**: Google Cloud Platform (GCP)
- **Development**: Node.js 16+, Python virtual environments

### 3.2. Functional Requirements

1. **The system shall authenticate users through Google OAuth 2.0 and maintain secure session management with JWT tokens.**

2. **The system shall fetch unread emails from Gmail API with configurable batch sizes (default: 100 emails) and support multiple inbox labels.**

3. **The system shall classify emails into priority levels (CRITICAL, HIGH, MEDIUM, LOW) using a hybrid approach combining ML models, rule-based logic, and LLM analysis.**

4. **The system shall identify email purposes including action_request, meeting_invite, newsletter, promotion, social, and task_related categories.**

5. **The system shall assign urgency scores (1-5 scale) and confidence scores (0-100%) to all email classifications.**

6. **The system shall generate contextual reply suggestions for emails excluding promotional and newsletter content.**

7. **The system shall extract actionable tasks from emails and create task entries with due dates when confidence exceeds 95%.**

8. **The system shall provide real-time email processing updates through WebSocket connections to the frontend dashboard.**

9. **The system shall maintain user feedback history and retrain ML models when feedback count exceeds configurable thresholds (default: 10 corrections).**

10. **The system shall execute autonomous actions (archiving, priority adjustment) when confidence levels exceed user-defined thresholds (default: 95% for archiving).**

11. **The system shall provide detailed reasoning explanations for all AI-driven decisions through the explainable AI engine.**

12. **The system shall track and enforce budget limits for LLM API usage with automatic provider switching ($120/month GPT-4, $5/month Claude).**

13. **The system shall maintain conversation context and user preferences through the agent memory system.**

14. **The system shall support email batch processing with progress tracking and cancellation capabilities.**

15. **The system shall provide dashboard analytics including processing statistics, cost tracking, and performance metrics.**

### 3.3. Nonfunctional Requirements

#### 3.3.1. Usability

The system provides an intuitive web-based dashboard with modern Material Design principles. The React frontend offers responsive design for desktop and mobile access. API endpoints follow RESTful conventions with comprehensive error messages and status codes. WebSocket integration provides real-time feedback without page refreshes. The system includes contextual help, tooltips, and clear visual indicators for AI confidence levels and reasoning explanations.

#### 3.3.2. Reliability

The system implements comprehensive error handling through try-catch blocks throughout the Python backend with graceful degradation when AI services are unavailable. Retry mechanisms with exponential backoff handle transient failures. Detailed logging captures all operations for debugging and monitoring. The system maintains data consistency through Firestore transactions and includes automatic failover between LLM providers when primary services fail.

#### 3.3.3. Performance

The system utilizes asynchronous processing for email operations to handle concurrent requests efficiently. Caching mechanisms in the agent memory system reduce redundant API calls. Database queries are optimized with appropriate indexing in Firestore. The hybrid LLM system routes requests to the most efficient provider based on task complexity. Frontend performance is optimized through code splitting, lazy loading, and memoized components. Target processing time is under 5 seconds per email with 99% uptime.

#### 3.3.4. Supportability

The codebase follows modular architecture with clear separation of concerns across components. Comprehensive logging at INFO and DEBUG levels supports troubleshooting. Configuration management through JSON files and environment variables enables easy deployment customization. The system includes automated testing suites for both backend (pytest) and frontend (Jest/React Testing Library). Documentation includes API specifications, deployment guides, and troubleshooting procedures.

#### 3.3.5. Implementation

**Programming Languages:** Python 3.x (backend), TypeScript/JavaScript (frontend)
**Backend Framework:** Flask 3.1.0 with Google Cloud Functions framework
**Frontend Framework:** React 19.1.0 with TypeScript 4.9.5
**State Management:** Zustand 5.0.5 for React state management
**Styling:** Tailwind CSS 3.4.17 with custom components
**Database:** Google Cloud Firestore (NoSQL document database)
**Authentication:** Google OAuth 2.0 with JWT token management
**AI/ML Libraries:** scikit-learn 1.6.1, transformers 4.52.3, spacy 3.8.7

#### 3.3.6. Interface

**REST API Endpoints:**
- `GET /api/health` - System health check
- `POST /api/auth/login` - User authentication
- `GET /api/emails/unread` - Fetch unread emails
- `POST /api/emails/process` - Process email batch
- `POST /api/feedback` - Submit user feedback
- `GET /api/settings` - Retrieve user preferences
- `PUT /api/settings` - Update configuration

**WebSocket Events:**
- `email_processing_started` - Processing initiated
- `email_analysis_complete` - Analysis finished
- `batch_progress_update` - Batch processing progress
- `autonomous_action_executed` - Automated action completed

**External API Integrations:**
- Gmail API v1 for email access and labeling
- Google Calendar API for meeting context
- OpenAI GPT-4 API for complex analysis
- Anthropic Claude API for cost-effective processing

#### 3.3.7. Packaging

The application uses Docker containerization with multi-stage builds for optimal production deployment. Python dependencies are managed through requirements.txt with pinned versions. The frontend build process uses Create React App with optimized production bundles. Google Cloud Functions deployment is managed through the functions-framework. Environment variables and secrets are managed through Google Cloud Secret Manager. The system includes deployment scripts for development, staging, and production environments.

#### 3.3.8. Legal

This information could not be determined from the provided codebase. No LICENSE file was found in the repository. The system utilizes various open-source libraries with different licenses including MIT (React, Flask), Apache 2.0 (Google Cloud libraries), and BSD licenses (scikit-learn, pandas). Commercial API services from OpenAI and Anthropic require separate licensing agreements and usage fees.

### 3.4. System Models

#### 3.4.1. Scenarios

**Scenario 1: Morning Email Triage**
Sarah arrives at the office and opens the Maia dashboard. The system has already processed 47 new emails overnight. She sees 3 emails marked as CRITICAL (from her CEO and two important clients), 8 marked as HIGH priority (project deadlines and meeting requests), and the rest automatically categorized. Sarah reviews the AI-generated summaries and reply suggestions, approves 2 autonomous task creations, and focuses on the critical emails first. The system saves her 30 minutes of manual email sorting.

**Scenario 2: Real-time Email Processing**
During a busy afternoon, John receives urgent emails while working on a presentation. The Maia system processes each email in real-time, immediately notifying him through the WebSocket connection when a CRITICAL email arrives from his project manager about a client emergency. The system provides a 2-sentence summary and suggests three response options. John quickly selects and sends a response, never leaving his presentation work.

**Scenario 3: Feedback Learning**
After using Maia for two weeks, Lisa notices that newsletters from a specific technical blog are being marked as LOW priority, but she finds them valuable. She provides feedback marking them as MEDIUM priority. The system updates her preferences and begins processing similar emails differently. Within 48 hours, the ML model retrains with her feedback, improving future classifications for similar content patterns.

#### 3.4.2. Use Case Model

**Primary Actors:**
- **End User**: Professional email user seeking intelligent email management
- **System Administrator**: Personnel responsible for system configuration and monitoring
- **Gmail API**: External service providing email data access

**Key Use Cases:**

**UC1: Authenticate User**
- Actor: End User
- Description: User logs in through Google OAuth to access the email processing system
- Preconditions: User has valid Google account with Gmail access
- Main Flow: User clicks login, redirected to Google OAuth, grants permissions, receives JWT token
- Postconditions: User authenticated and authorized for email access

**UC2: Process Email Batch**
- Actor: End User, System
- Description: System analyzes multiple emails and provides prioritization and insights
- Preconditions: User authenticated, emails available in Gmail inbox
- Main Flow: System fetches emails, applies hybrid AI analysis, stores results, updates dashboard
- Postconditions: Emails classified with priority, purpose, and confidence scores

**UC3: Execute Autonomous Action**
- Actor: System
- Description: System automatically performs actions based on high-confidence analysis
- Preconditions: Email analysis complete, confidence above threshold
- Main Flow: System evaluates confidence, executes action (archive/label), logs activity
- Postconditions: Action completed and recorded in audit log

**UC4: Provide Feedback**
- Actor: End User
- Description: User corrects AI classifications to improve system accuracy
- Preconditions: Email processing complete, user disagrees with classification
- Main Flow: User selects correct classification, submits feedback, system updates models
- Postconditions: Feedback stored, model retraining triggered if threshold met

**UC5: Generate Reply Suggestions**
- Actor: System
- Description: System creates contextual response options for emails requiring replies
- Preconditions: Email classified as action-required, not promotional content
- Main Flow: System analyzes email context, generates suggestions, user selects or modifies
- Postconditions: Reply suggestions available for user selection

#### 3.4.3. Analysis Object Model (Class Diagram)

**Core Classes and Relationships:**

```
EmailProcessor (main.py)
├── Attributes: config, storage_client, secret_client, db
├── Methods: process_emails(), classify_email(), store_results()
├── Relationships: Uses AgentLogic, DatabaseUtils, ReasoningEngine

AgentLogic (agent_logic.py)
├── Attributes: gmail_service, memory_system
├── Methods: get_unread_emails(), parse_email_content(), analyze_email_with_context()
├── Relationships: Aggregates AgentMemory, Uses Gmail API

ReasoningEngine (reasoning_integration.py)
├── Attributes: confidence_thresholds, rules, llm_manager
├── Methods: process_with_enhanced_reasoning(), create_proactive_insights()
├── Relationships: Composes HybridLLMManager, Uses MLUtils

HybridLLMManager (hybrid_llm_system.py)
├── Attributes: budget_tracker, provider_configs, current_provider
├── Methods: route_request(), track_usage(), switch_provider()
├── Relationships: Interfaces with OpenAI API, Anthropic API

AgentMemory (agent_memory.py)
├── Attributes: conversation_history, user_preferences, feedback_patterns
├── Methods: store_interaction(), get_context(), update_preferences()
├── Relationships: Uses DatabaseUtils for persistence

DatabaseUtils (database_utils.py)
├── Attributes: firestore_client, collections
├── Methods: store_email(), get_feedback(), update_preferences()
├── Relationships: Interfaces with Google Cloud Firestore

Email (Data Model)
├── Attributes: id, subject, sender, content, priority, confidence, timestamp
├── Methods: to_dict(), from_dict(), validate()
├── Relationships: Stored by DatabaseUtils, Processed by EmailProcessor

APIServer (api_server.py)
├── Attributes: app, socketio, auth_manager
├── Methods: handle_auth(), process_batch(), emit_updates()
├── Relationships: Uses EmailProcessor, Manages WebSocket connections
```

**Key Relationships:**
- **Composition**: HybridLLMManager contains multiple LLM providers
- **Aggregation**: EmailProcessor aggregates multiple processing components
- **Inheritance**: All API endpoints inherit from Flask base classes
- **Interface**: DatabaseUtils implements Firestore interface contract
- **Dependency**: ReasoningEngine depends on MLUtils for predictions

#### 3.4.4. Dynamic Model (Sequence Diagram)

**Sequence Diagram: Email Processing Flow**

```
User -> Frontend: Request email processing
Frontend -> APIServer: POST /api/emails/process
APIServer -> EmailProcessor: process_emails()
EmailProcessor -> AgentLogic: get_unread_emails()
AgentLogic -> Gmail API: fetch emails
Gmail API -> AgentLogic: return email data
AgentLogic -> EmailProcessor: parsed emails
EmailProcessor -> ReasoningEngine: analyze_emails()
ReasoningEngine -> MLUtils: get_ml_prediction()
MLUtils -> ReasoningEngine: prediction result
ReasoningEngine -> HybridLLMManager: get_llm_analysis()
HybridLLMManager -> OpenAI API: analyze content
OpenAI API -> HybridLLMManager: analysis result
HybridLLMManager -> ReasoningEngine: formatted analysis
ReasoningEngine -> EmailProcessor: final classification
EmailProcessor -> DatabaseUtils: store_results()
DatabaseUtils -> Firestore: save email data
EmailProcessor -> APIServer: processing complete
APIServer -> Frontend: WebSocket update
Frontend -> User: Display results
```

**Key Interaction Patterns:**
1. **Authentication Flow**: User → Frontend → Google OAuth → Backend → JWT validation
2. **Real-time Updates**: Backend → WebSocket → Frontend → User notification
3. **Feedback Learning**: User correction → Database → ML model → Improved predictions
4. **Autonomous Actions**: High confidence → Reasoning engine → Automatic execution → Audit log
5. **Error Handling**: API failure → Retry logic → Fallback provider → Graceful degradation

---

**Document Generated:** 25.06.2025  
**Version:** 1.0  
**Status:** Final Draft