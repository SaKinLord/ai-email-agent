# -*- coding: utf-8 -*-
"""
Created on Sun May 11 03:59:26 2025

@author: merto
"""
import tempfile
import pandas as pd
import joblib
import logging
import os
from google.cloud import storage # For downloading models from GCS

# Assuming ml_utils.py is in the same directory or accessible in PYTHONPATH
from ml_utils import predict_priority, extract_domain 

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Configuration ---
# Option: Load models from GCS or local path
LOAD_FROM_GCS = True # Set to False to load from local_model_path
GCS_MODEL_BUCKET = os.environ.get('MODEL_GCS_BUCKET', 'ai-email-agent-state') # From training
GCS_MODEL_PREFIX = os.environ.get('MODEL_GCS_PATH_PREFIX', 'ml_models_test/')    # From training
PIPELINE_FILENAME = "test_pipeline.joblib" # Must match filename used in training
ENCODER_FILENAME = "test_encoder.joblib"   # Must match filename used in training

LOCAL_MODEL_PATH = "./" # Path if loading locally (e.g., if you downloaded them)

# Sample email for prediction
sample_email_1 = {
    'subject': "URGENT inquiry about your services",
    'body_text': "Please call me back immediately, this is very important regarding our contract.",
    'llm_purpose': "Action Request",
    'sender': "vip_client@importantcustomer.com",
    'llm_urgency': 5
}
sample_email_2 = {
    'subject': "Weekly newsletter",
    'body_text': "Check out our latest updates and promotions for this week.",
    'llm_purpose': "Promotion",
    'sender': "newsletter@example.com",
    'llm_urgency': 1
}

def load_models_from_gcs(bucket_name, pipeline_blob_path, encoder_blob_path):
    try:
        storage_client = storage.Client()
        bucket = storage_client.bucket(bucket_name)
        
        pipeline_blob = bucket.blob(pipeline_blob_path)
        encoder_blob = bucket.blob(encoder_blob_path)

        with tempfile.TemporaryDirectory() as tmpdir:
            local_pipeline_file = os.path.join(tmpdir, PIPELINE_FILENAME)
            local_encoder_file = os.path.join(tmpdir, ENCODER_FILENAME)

            logging.info(f"Downloading pipeline from gs://{bucket_name}/{pipeline_blob_path} to {local_pipeline_file}")
            pipeline_blob.download_to_filename(local_pipeline_file)
            pipeline_model = joblib.load(local_pipeline_file)
            
            logging.info(f"Downloading encoder from gs://{bucket_name}/{encoder_blob_path} to {local_encoder_file}")
            encoder_blob.download_to_filename(local_encoder_file)
            label_encoder_model = joblib.load(local_encoder_file)
            
            return pipeline_model, label_encoder_model
    except Exception as e:
        logging.error(f"Error loading models from GCS: {e}")
        return None, None

if __name__ == "__main__":
    logging.info("Starting ML Utils Prediction Test...")
    pipeline = None
    label_encoder = None

    if LOAD_FROM_GCS:
        if not GCS_MODEL_BUCKET or GCS_MODEL_BUCKET == 'your-ml-model-bucket-name':
            logging.error("MODEL_GCS_BUCKET env var not set or is default. Cannot load from GCS.")
            exit()
        full_pipeline_gcs_path = os.path.join(GCS_MODEL_PREFIX, PIPELINE_FILENAME)
        full_encoder_gcs_path = os.path.join(GCS_MODEL_PREFIX, ENCODER_FILENAME)
        pipeline, label_encoder = load_models_from_gcs(GCS_MODEL_BUCKET, full_pipeline_gcs_path, full_encoder_gcs_path)
    else:
        try:
            pipeline = joblib.load(os.path.join(LOCAL_MODEL_PATH, PIPELINE_FILENAME))
            label_encoder = joblib.load(os.path.join(LOCAL_MODEL_PATH, ENCODER_FILENAME))
            logging.info("Loaded models from local path.")
        except Exception as e:
            logging.error(f"Error loading models from local path '{LOCAL_MODEL_PATH}': {e}")

    if not pipeline or not label_encoder:
        logging.error("Failed to load ML models. Exiting prediction test.")
        exit()

    logging.info("Models loaded successfully.")
    logging.info(f"Pipeline: {pipeline}")
    logging.info(f"Encoder classes: {label_encoder.classes_}")

    # Test prediction
    emails_to_test = [sample_email_1, sample_email_2]
    for i, email_data in enumerate(emails_to_test):
        logging.info(f"\n--- Predicting for Sample Email {i+1} ---")
        logging.info(f"Input data: {email_data}")
        predicted_prio = predict_priority(email_data, pipeline, label_encoder)
        if predicted_prio:
            logging.info(f"PREDICTED PRIORITY for Sample Email {i+1}: {predicted_prio}")
        else:
            logging.error(f"FAILED to predict priority for Sample Email {i+1}.")