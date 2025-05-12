# -*- coding: utf-8 -*-
"""
Created on Sun May 11 03:56:09 2025

@author: merto
"""

import pandas as pd
import logging
from google.cloud import storage
import os

# Assuming ml_utils.py is in the same directory or accessible in PYTHONPATH
from ml_utils import build_and_train_pipeline, extract_domain 
# If main.py has fetch_and_prepare_training_data and you want to use it:
# from main import fetch_and_prepare_training_data # You'd also need to initialize db in main
# from database_utils import db as firestore_db # If using db from database_utils

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Configuration (Adjust these as needed) ---
# For real data, you might fetch from Firestore. For now, let's use mock.
USE_MOCK_DATA = True 
MOCK_DATA_SAMPLES = [
    {'subject': "Urgent meeting request", 'body_text': "Please join the call now.", 'llm_purpose': "Meeting Invite", 'sender': "boss@company.com", 'llm_urgency': 5, 'corrected_priority': "CRITICAL"},
    {'subject': "Project Update", 'body_text': "Here is the weekly status.", 'llm_purpose': "Information", 'sender': "team@internal.com", 'llm_urgency': 3, 'corrected_priority': "MEDIUM"},
    {'subject': "Big Sale!", 'body_text': "Don't miss out on savings!", 'llm_purpose': "Promotion", 'sender': "promo@spam.com", 'llm_urgency': 1, 'corrected_priority': "LOW"},
    {'subject': "Action needed: Review document", 'body_text': "Please review by EOD.", 'llm_purpose': "Action Request", 'sender': "manager@company.com", 'llm_urgency': 4, 'corrected_priority': "HIGH"},
    {'subject': "Another critical issue", 'body_text': "System down, fix now!", 'llm_purpose': "Action Request", 'sender': "alerts@company.com", 'llm_urgency': 5, 'corrected_priority': "CRITICAL"},
]

# --- GCS Configuration (Ensure these are set as env vars or defined here) ---
# It's better to use environment variables for these in a real scenario
MODEL_GCS_BUCKET_NAME = os.environ.get('MODEL_GCS_BUCKET', 'ai-email-agent-state') # REPLACE or set env var
MODEL_GCS_PREFIX = os.environ.get('MODEL_GCS_PATH_PREFIX', 'ml_models_test/')

LOCAL_PIPELINE_FILENAME = "test_pipeline.joblib"
LOCAL_ENCODER_FILENAME = "test_encoder.joblib"

def get_training_data():
    if USE_MOCK_DATA:
        logging.info("Using mock data for training.")
        df = pd.DataFrame(MOCK_DATA_SAMPLES)
        df['text_features'] = df['subject'] + " " + df['body_text']
        df['sender_domain'] = df['sender'].apply(extract_domain)
        # Ensure all required columns are present
        df = df[['text_features', 'llm_purpose', 'sender_domain', 'llm_urgency', 'corrected_priority']]
        return df
    else:
        # TODO: Implement fetching real data if needed for more thorough testing
        # This would involve initializing Firestore client and calling
        # fetch_and_prepare_training_data(firestore_db)
        # For now, this path is not implemented in this test script.
        logging.warning("Real data fetching not implemented in this test script. Set USE_MOCK_DATA=True.")
        return pd.DataFrame()


if __name__ == "__main__":
    logging.info("Starting ML Utils Training Test...")

    if not MODEL_GCS_BUCKET_NAME or MODEL_GCS_BUCKET_NAME == 'your-ml-model-bucket-name':
        logging.error("MODEL_GCS_BUCKET environment variable not set or is default. Exiting.")
        exit()

    training_data_df = get_training_data()

    if training_data_df.empty:
        logging.error("No training data available. Exiting.")
        exit()

    logging.info(f"Prepared training data with {len(training_data_df)} samples.")
    logging.info(f"Training data columns: {training_data_df.columns.tolist()}")
    logging.info(f"Training data head:\n{training_data_df.head()}")


    try:
        gcs_storage_client = storage.Client()
        logging.info("GCS Storage Client initialized.")
    except Exception as e:
        logging.error(f"Failed to initialize GCS client: {e}")
        exit()

    # Construct full blob names for GCS
    pipeline_gcs_blob_name = os.path.join(MODEL_GCS_PREFIX, LOCAL_PIPELINE_FILENAME)
    encoder_gcs_blob_name = os.path.join(MODEL_GCS_PREFIX, LOCAL_ENCODER_FILENAME)

    pipeline, label_encoder = build_and_train_pipeline(
        training_df=training_data_df,
        storage_client=gcs_storage_client,
        bucket_name=MODEL_GCS_BUCKET_NAME,
        pipeline_blob_name=pipeline_gcs_blob_name, # Pass full GCS path
        encoder_blob_name=encoder_gcs_blob_name,   # Pass full GCS path
        local_pipeline_filename=LOCAL_PIPELINE_FILENAME, # Pass base name for temp local save
        local_encoder_filename=LOCAL_ENCODER_FILENAME    # Pass base name for temp local save
    )

    if pipeline and label_encoder:
        logging.info("SUCCESS: build_and_train_pipeline completed successfully.")
        logging.info(f"Pipeline object: {pipeline}")
        logging.info(f"LabelEncoder classes: {label_encoder.classes_}")
        logging.info(f"Models should be uploaded to gs://{MODEL_GCS_BUCKET_NAME}/{MODEL_GCS_PREFIX}")
    else:
        logging.error("FAILURE: build_and_train_pipeline did not complete successfully.")