# Maia - Your Intelligent Email Agent 📧🤖

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)  
[![Python Version](https://img.shields.io/badge/python-3.11-blue.svg)](https://www.python.org/downloads/release/python-311/)  
<!-- Add other badges as appropriate, e.g., build status, code coverage -->

Maia is an AI-powered email assistant designed to help you manage your Gmail inbox more efficiently. It intelligently classifies emails, provides summaries, suggests actions, learns from your feedback, and can even perform autonomous tasks to keep your inbox organized.

---

**Table of Contents**

*   [Overview](#overview)  
*   [Features](#features)  
*   [Architecture](#architecture)  
*   [Tech Stack](#tech-stack)  
*   [Getting Started](#getting-started)  
    *   [Prerequisites](#prerequisites)  
    *   [Installation](#installation)  
    *   [Configuration](#configuration)  
        *   [Google Cloud Project Setup](#google-cloud-project-setup)  
        *   [Anthropic API Key](#anthropic-api-key)  
        *   [Local Configuration Files](#local-configuration-files)  
        *   [Environment Variables for GCF](#environment-variables-for-gcf)  
*   [Usage](#usage)  
    *   [Running the Streamlit UI Locally](#running-the-streamlit-ui-locally)  
    *   [Deploying the Backend GCF](#deploying-the-backend-gcf)  
    *   [Initial Gmail Authentication](#initial-gmail-authentication)  
    *   [Using the UI](#using-the-ui)  
*   [Key Components](#key-components)  
*   [Autonomous Mode](#autonomous-mode)  
*   [ML Model Retraining](#ml-model-retraining)  
*   [Troubleshooting](#troubleshooting)  
*   [Contributing](#contributing)  
*   [License](#license)  
*   [Acknowledgements](#acknowledgements)  

---

## Overview

In today's fast-paced digital world, managing a flood of emails can be overwhelming. Maia aims to alleviate this by leveraging Large Language Models (LLMs) and Machine Learning (ML) to understand, prioritize, and help you act on your emails. It provides a user-friendly Streamlit interface for interaction and a Google Cloud Function backend for continuous processing and autonomous actions.

## Features

*   **Gmail Integration:** Securely connects to your Gmail account to read and process emails.  
*   **Intelligent Email Analysis:**  
    *   Uses Anthropic's Claude LLM for deep content understanding.  
    *   Determines email purpose (e.g., Action Request, Information, Question, Promotion).  
    *   Assesses urgency and estimates time needed for handling.  
    *   Identifies if a response is likely needed.  
*   **Priority Classification:**  
    *   Combines LLM analysis, rule-based logic (important senders, keywords), and a custom-trained ML model to assign priorities (CRITICAL, HIGH, MEDIUM, LOW).  
*   **Summarization:** Generates concise summaries for high-priority or requested emails.  
*   **Action Suggestions:** Proactively suggests relevant actions (e.g., archive, reply, schedule) based on email content and analysis.  
*   **Draft Generation & Revision:** Assists in drafting email replies and allows for iterative revisions based on user instructions.  
*   **User Feedback Loop:** Learns from your priority and purpose corrections via the UI to improve its ML model over time.  
*   **Autonomous Mode:**  
    *   **Auto-Archiving:** Automatically archives emails based on defined criteria (e.g., old promotions).  
    *   **Daily Summaries:** Can send a daily summary of important emails.  
    *   **Follow-up Reminders:** Identifies sent emails that haven't received replies and creates tasks.  
    *   **Auto-Categorization:** Can automatically apply Gmail labels based on its classification (e.g., "Maia/Priority/High").  
    *   **Re-evaluation:** Periodically re-evaluates emails with initially "Unknown" purposes.  
*   **Google Calendar Integration:** Can suggest and (with permission) schedule email checking blocks in your Google Calendar.  
*   **Streamlit Web Interface:** Provides an interactive dashboard, chat interface, feedback mechanism, and settings management.  
*   **Persistent Memory:** Utilizes Firestore to store processed email data, user preferences, feedback, and agent state.  
*   **Secure API Key Management:** Uses Google Cloud Secret Manager for API keys.  
*   **GCS for State & Models:** Leverages Google Cloud Storage for OAuth tokens, ML models, and retraining state.  

## Architecture

Maia consists of two main parts:

1.  **Streamlit UI (`ui_app.py`):** The user-facing web application where users can interact with the agent, view processed emails, provide feedback, and manage settings. Runs locally or can be deployed.  
2.  **Google Cloud Function (`main.py` - `process_emails_gcf`):** The backend worker that:  
    *   Periodically fetches new emails from Gmail.  
    *   Processes them using `agent_logic.py` (LLM analysis, ML classification).  
    *   Stores results in Firestore via `database_utils.py`.  
    *   Handles ML model retraining based on feedback.  
    *   Executes autonomous tasks if enabled.  
    *   Processes action requests (e.g., archiving, applying labels, sending drafts) queued from the UI or autonomous tasks.  

Data flow involves Gmail API → GCF → LLM/ML → Firestore ← Streamlit UI.

## Tech Stack

*   **Backend:** Python, Google Cloud Functions (Gen 2)  
*   **Frontend:** Streamlit  
*   **LLM:** Anthropic Claude (via API)  
*   **Machine Learning:** Scikit-learn, Pandas, Joblib  
*   **Database:** Google Cloud Firestore  
*   **Storage:** Google Cloud Storage (for tokens, ML models, state files)  
*   **Secrets Management:** Google Cloud Secret Manager  
*   **Authentication:** Google OAuth 2.0  
*   **Scheduling (for GCF):** Google Cloud Scheduler (recommended)  

---

## Getting Started

> **NOTE:** Throughout this README, you will see placeholders like `[YOUR_PROJECT_ID]`, `[YOUR_GCS_BUCKET_NAME]`, etc. You **must** replace these with the specific names and IDs corresponding to your own Google Cloud Project and resources when you set up the agent.

### Prerequisites

1.  **Python 3.11** (as specified in your GCF runtime).  
2.  **Google Cloud SDK (gcloud CLI)** installed and authenticated.  
3.  A **Google Cloud Project** with the following APIs enabled:  
    *   Gmail API  
    *   Google Cloud Functions API  
    *   Cloud Build API (usually enabled with Functions)  
    *   Firestore API  
    *   Cloud Storage API  
    *   Secret Manager API  
    *   Google Calendar API (if using calendar features)  
    *   Artifact Registry API (for GCF Gen 2)  
4.  A **Gmail Account** you want the agent to manage.  
5.  An **Anthropic API Key**.  
6.  `pip` and `venv` for Python package management.

### Installation

1.  **Clone the repository:**  
    ```bash
    git clone https://github.com/SaKinLord/ai-email-agent
    cd maia-email-agent
    ```
2.  **Create and activate a virtual environment:**  
    ```bash
    python -m venv venv
    # Windows
    .\venv\Scripts\activate
    # macOS/Linux
    source venv/bin/activate
    ```
3.  **Install dependencies:**  
    ```bash
    pip install -r requirements.txt
    ```

### Configuration

#### 1. Google Cloud Project Setup

*   Create a new Google Cloud Project or use an existing one.  
*   Enable the APIs listed in **Prerequisites**.  
*   Set up Firestore in Native mode.  
*   Create a Google Cloud Storage bucket. This bucket will be used for:  
    *   Gmail OAuth token (`gmail_token.json`)  
    *   Calendar OAuth token (`calendar_token.json`)  
    *   ML model files (`feature_pipeline.joblib`, `label_encoder.joblib`)  
    *   Retraining state file (`retrain_state.json`)  
*   **Note your Project ID** (e.g., `my-email-agent-project`) **and the GCS Bucket Name** you create (e.g., `maia-agent-storage-unique123`).  
*   Whenever you see `[YOUR_PROJECT_ID]` or `[YOUR_GCS_BUCKET_NAME]` in this README, replace them with your actual project ID and bucket name.

#### 2. Anthropic API Key

*   Obtain an API key from [Anthropic](https://www.anthropic.com/).  
*   Store this API key securely in **Google Cloud Secret Manager**.  
    *   Create a new secret (e.g., `anthropic-api-key`).  
    *   Add a new version with your API key as the secret value.  
    *   **Note the full _Resource Name_ of the secret version.** It will look like:  
        ```
        projects/[YOUR_PROJECT_ID]/secrets/[YOUR_SECRET_NAME]/versions/[VERSION_ID_OR_LATEST]
        ```  
    *   Anytime you see `projects/[YOUR_PROJECT_ID]/secrets/[YOUR_SECRET_NAME]/versions/latest`, replace `[YOUR_PROJECT_ID]` and `[YOUR_SECRET_NAME]` accordingly.

#### 3. Local Configuration Files

*   **`credentials.json`**:  
    *   In Google Cloud Console → APIs & Services → Credentials, create an **OAuth 2.0 Client ID**.  
    *   Choose **“Desktop app”** as the application type.  
    *   Download the JSON file and save it as `credentials.json` in the root of your project directory.  
    *   _Important:_ In the OAuth client’s settings, add these Authorized redirect URIs if you plan to use Calendar integration from Streamlit:  
      ```
      http://localhost:8501
      http://localhost
      ```  
*   **`config.json`**:  
    *   A `config.template.json` is provided. Rename it to `config.json`.  
    *   Open `config.json` and update the following fields:  
        *   `"gmail": { "credentials_path": "credentials.json" }`  
        *   `"llm": { "api_key_env_var": "ANTHROPIC_API_KEY", "action_suggestion_max_tokens": 300 }`  
        *   Other settings (e.g., classification rules, default thresholds) as needed.  
*   **`.env` file (for local development only, _DO NOT COMMIT TO GIT_):**  
    *   In the project root, create a file named `.env`:  
        ```env
        # .env - For local development. DO NOT COMMIT THIS FILE TO GIT!

        ANTHROPIC_API_KEY="sk-ant-your-actual-api-key"          # Your actual Anthropic API key
        GCS_BUCKET_NAME="your-gcs-bucket-name"                  # e.g., maia-agent-storage-unique123
        TOKEN_GCS_PATH="gmail_token.json"                       # Path in the bucket for Gmail token
        STATE_GCS_PATH="retrain_state.json"                     # Path in the bucket for retraining state
        MODEL_GCS_BUCKET="your-model-gcs-bucket-name"           # e.g., maia-models-bucket (can be same as GCS_BUCKET_NAME)
        MODEL_GCS_PATH_PREFIX="ml_models/"                      # Folder within model bucket
        CALENDAR_TOKEN_GCS_PATH="calendar_token.json"           # Path in the bucket for Calendar token
        ANTHROPIC_SECRET_NAME="projects/[YOUR_PROJECT_ID]/secrets/[YOUR_SECRET_NAME]/versions/latest"
        ```
    *   _Important:_ Add `.env` to your `.gitignore` so you don’t accidentally push secrets to GitHub.

#### 4. Environment Variables for GCF

When deploying the `process_emails_gcf` function, you **must** set these environment variables. Replace every placeholder with your actual values:

*   `GCS_BUCKET_NAME="[YOUR_GCS_BUCKET_NAME]"`  
*   `TOKEN_GCS_PATH="gmail_token.json"` (or your preferred path)  
*   `STATE_GCS_PATH="retrain_state.json"` (or your preferred path)  
*   `ANTHROPIC_SECRET_NAME="projects/[YOUR_PROJECT_ID]/secrets/[YOUR_SECRET_NAME]/versions/latest"`  
*   `MODEL_GCS_BUCKET="[YOUR_MODEL_GCS_BUCKET_NAME]"`  
*   `MODEL_GCS_PATH_PREFIX="ml_models/"`  
*   `CALENDAR_TOKEN_GCS_PATH="calendar_token.json"` (or your preferred path)  

Whenever you see `[YOUR_GCS_BUCKET_NAME]`, `[YOUR_PROJECT_ID]`, or `[YOUR_SECRET_NAME]` below, replace them accordingly.

---

## Usage

### 1. Initial Gmail Authentication (Local)

Before the GCF can run autonomously or the UI can fully access Gmail, you need to perform an initial OAuth 2.0 flow to generate `gmail_token.json`.

1.  Ensure your `credentials.json` is in the project root and `config.json` points to it.  
2.  Ensure your GCS bucket (specified by `GCS_BUCKET_NAME` in your `.env` or GCF environment) exists.  
3.  Run `main.py` locally from its directory:  
    ```bash
    python main.py
    ```  
4.  This will trigger a browser window asking you to log in with your Gmail account and grant permissions.  
5.  After successful authorization, a `gmail_token.json` will be created and uploaded to the GCS bucket specified by `GCS_BUCKET_NAME` and `TOKEN_GCS_PATH`.

### 2. Running the Streamlit UI Locally

1.  Ensure your `.env` file is configured with your Anthropic API key and GCS bucket details.  
2.  Activate your virtual environment:  
    ```bash
    # Windows
    .\venv\Scripts\activate

    # macOS/Linux
    source venv/bin/activate
    ```  
3.  Run the Streamlit app:  
    ```bash
    streamlit run ui_app.py
    ```  
4.  Open the local URL (usually `http://localhost:8501`) in your browser.

### 3. Deploying the Backend GCF (`process_emails_gcf`)

1.  Authenticate `gcloud` CLI with your project:  
    ```bash
    gcloud auth login
    gcloud config set project [YOUR_PROJECT_ID]
    ```  
2.  Ensure `credentials.json` and `config.json` are in the root of the directory you are deploying from.  
3.  Deploy the function (replace placeholders with your own values):  
    ```bash
    gcloud functions deploy process_emails_gcf \
      --gen2 \
      --runtime=python311 \
      --region=[YOUR_REGION] \
      --source=. \
      --entry-point=process_emails_gcf \
      --trigger-http \
      --no-allow-unauthenticated \
      --service-account=[YOUR_GCF_SERVICE_ACCOUNT_EMAIL] \
      --set-env-vars=GCS_BUCKET_NAME="[YOUR_GCS_BUCKET_NAME]",\
TOKEN_GCS_PATH="gmail_token.json",\
STATE_GCS_PATH="retrain_state.json",\
ANTHROPIC_SECRET_NAME="projects/[YOUR_PROJECT_ID]/secrets/[YOUR_SECRET_NAME]/versions/latest",\
MODEL_GCS_BUCKET="[YOUR_MODEL_GCS_BUCKET_NAME]",\
MODEL_GCS_PATH_PREFIX="ml_models/",\
CALENDAR_TOKEN_GCS_PATH="calendar_token.json" \
      --memory=1GiB \
      --timeout=540s
    ```  
    *   Replace `[YOUR_REGION]` (e.g., `europe-west1`).  
    *   Replace `[YOUR_GCF_SERVICE_ACCOUNT_EMAIL]` (e.g., `email-agent-runner@[YOUR_PROJECT_ID].iam.gserviceaccount.com`). Ensure this service account has permissions for Firestore, GCS (read/write to the buckets), Secret Manager (secret accessor), Cloud Functions Invoker, and to run Gmail API calls (this is implicitly handled by the user's OAuth token, but the GCF service account also needs to have required permissions).  
4.  **Schedule the GCF:** Use Google Cloud Scheduler to trigger this HTTP function periodically (e.g., every 10–15 minutes).

### 4. Using the UI

*   **💬 Chat & Dashboard:** Interact with Maia, view proactive suggestions, and see an overview.  
*   **✉️ Email Feedback:** Review email classifications and provide corrections for priority and purpose. This feedback is used for retraining.  
*   **📊 Insights:** View distributions of email priorities and purposes.  
*   **⚙️ Settings:**  
    *   Manage important senders and filtered domains.  
    *   Configure notification preferences (UI only for now).  
    *   Connect Google Calendar for scheduling assistance.  
    *   View suggestion history and analytics.  
*   **🤖 Autonomous:** Enable/disable autonomous mode and configure specific autonomous tasks (auto-archiving, daily summaries, follow-ups).

---

## Key Components

*   **`ui_app.py`:** Main Streamlit application file. Handles user interface, interaction logic, and calls to agent functionalities.  
*   **`main.py`:** Google Cloud Function (`process_emails_gcf`). Backend for email processing, retraining, autonomous tasks, and action request execution.  
*   **`agent_logic.py`:** Core logic for email processing, including Gmail API interaction, LLM calls for analysis/summarization/drafting, classification rules, and integration with the ML model.  
*   **`agent_memory.py`:** Manages user profiles, preferences, conversation history, and suggestion history using Firestore.  
*   **`database_utils.py`:** Utility functions for interacting with Firestore (saving emails, feedback, state).  
*   **`ml_utils.py`:** Handles ML pipeline building, training, prediction, and feature extraction helpers.  
*   **`enhanced_proactive_agent.py`:** Contains the `ProactiveAgent` class responsible for generating and managing proactive suggestions in the UI.  
*   **`config.json`:** Configuration file for various settings (Gmail, LLM, classification rules, etc.).  
*   **`credentials.json`:** OAuth 2.0 client secrets (obtained from Google Cloud Console).  
*   **`requirements.txt`:** Python package dependencies.  

---

## Autonomous Mode

When enabled in the UI's “Autonomous” tab, the GCF backend can perform tasks like:

*   **Auto-Archiving:** Moves emails matching certain criteria (e.g., old promotions) out of the inbox.  
*   **Daily Summary:** Generates and (if configured) sends a daily email summary of important items.  
*   **Follow-up Reminders:** Creates tasks for sent emails that haven't received a reply after a configured period.  
*   **Auto-Categorization:** Applies Gmail labels (e.g., “Maia/Priority/High”) to newly processed emails.  
*   **Re-evaluate Unknowns:** Periodically re-analyzes emails whose purpose was initially unclear.  

Each task has its own settings and can be enabled/disabled individually within the Autonomous tab, provided the main “Enable Autonomous Mode” is active. The GCF checks these preferences from the user's profile in Firestore.

---

## ML Model Retraining

*   The system collects feedback on email priority and purpose provided through the “Email Feedback” tab in the UI.  
*   When the number of new feedback entries reaches the `trigger_feedback_count` (defined in `config.json`, default 10), the GCF automatically initiates a retraining process during its next run.  
*   **Process:**  
    1.  `fetch_and_prepare_training_data` (in `main.py`) queries Firestore for all feedback and corresponding email details.  
    2.  `build_and_train_pipeline` (in `ml_utils.py`) uses this data to train a new Scikit-learn classification model (TF-IDF + Logistic Regression).  
    3.  The new pipeline (`feature_pipeline.joblib`) and label encoder (`label_encoder.joblib`) are saved to the GCS bucket specified by `MODEL_GCS_BUCKET` and `MODEL_GCS_PATH_PREFIX`.  
    4.  The `retrain_state.json` file in GCS is updated with the current feedback count.  
*   Subsequent GCF runs will load and use this newly retrained model for classifying emails.

---

## Troubleshooting

*   **Authentication Errors (GCF):**  
    *   `RuntimeError: Gmail authentication failed.`  
        *   Ensure `credentials.json` is deployed with your GCF.  
        *   Ensure `gmail_token.json` in GCS is valid. If not, delete it from GCS and re-run `python main.py` locally to regenerate it.  
        *   Check GCF service account permissions for GCS (reading/writing token) and Secret Manager (accessing Anthropic key).  
*   **Firestore Index Errors (GCF Logs):**  
    *   If logs show `google.api_core.exceptions.FailedPrecondition: 400 The query requires an index...`, click the link provided in the error message to create the required composite index in Firestore. Wait for it to build.  
*   **“Invalid Label” Error (GCF Logs for `apply_label` action):**  
    *   The agent tries to apply labels like “Maia/Priority/Medium”. These labels must exist in your Gmail account. The agent will attempt to create them if they don't exist (as per recent code changes). If creation fails, check GCF logs for errors from `get_or_create_label_ids`.  
*   **Streamlit UI Issues:**  
    *   Ensure all dependencies in `requirements.txt` are installed in your virtual environment.  
    *   Check the Streamlit command prompt/terminal for Python errors.  
    *   Ensure your `.env` file is correctly configured for local runs.  
*   **Autonomous Tasks Not Running:**  
    *   Verify “Enable Autonomous Mode” is ON in the UI and saved to Firestore.  
    *   Verify individual task toggles (e.g., “Enable Daily Summary”) are ON and their settings saved.  
    *   Check the `last_run_utc` for the task in `user_memory/default_user/autonomous_tasks` in Firestore. The task will only run if its configured interval has passed since this timestamp.  
    *   Check GCF logs for specific errors related to that task.

---

## Contributing

Contributions are welcome! If you'd like to contribute, please follow these steps:

1.  Fork the repository.  
2.  Create a new branch:  
    ```bash
    git checkout -b feature/YourFeature
    # or
    git checkout -b bugfix/YourBugfix
    ```  
3.  Make your changes.  
4.  Commit your changes:  
    ```bash
    git commit -m "Add some feature"
    ```  
5.  Push to the branch:  
    ```bash
    git push origin feature/YourFeature
    ```  
6.  Open a Pull Request.

---

## License

This project is licensed under the MIT License – see the [LICENSE.md](LICENSE.md) file for details (you'll need to create this file if you choose MIT).

---

## Acknowledgements

*   Google Cloud Platform for its robust services.  
*   Anthropic for the Claude LLM.  
*   The Streamlit team for the easy-to-use web framework.  
*   DiceBear for the avatars.  
*   Contributors and users of this project.

---

*This README is a template. Please review and customize it thoroughly for your project.*  
