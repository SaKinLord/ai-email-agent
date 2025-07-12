# -*- coding: utf-8 -*-
"""
Created on Thu Apr 10 06:47:01 2025

@author: merto
"""


"""
ML Utilities for the AI Email Agent.
Focuses on pipeline building, training, prediction, and feature helpers,
assuming training data (DataFrame) is provided externally. Includes GCS saving.
"""

# --- Standard Library Imports ---
import pandas as pd
import joblib
import os
import re
import logging
import tempfile # Added for GCF temporary storage

# --- Third-party Imports ---
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import OneHotEncoder, LabelEncoder
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.linear_model import LogisticRegression
# from sklearn.metrics import classification_report # Keep if you add evaluation later
# NOTE: google-cloud-storage is NOT directly imported here.
# The storage_client object is expected to be passed in from main.py

# --- Constants ---
DEFAULT_PIPELINE_FILENAME = "feature_pipeline.joblib"
DEFAULT_LABEL_ENCODER_FILENAME = "label_encoder.joblib"

# --- Helper Functions ---

def extract_domain(sender):
    """Extracts domain or full email if domain cannot be reliably extracted."""
    if not isinstance(sender, str):
        return "unknown_domain"
    # Prioritize extracting from angle brackets if present
    match_bracket = re.search(r'<.+@([\w.-]+)>', sender)
    if match_bracket:
        return match_bracket.group(1).lower()
    # Fallback: look for @ symbol directly
    match_at = re.search(r'@([\w.-]+)', sender)
    if match_at:
        return match_at.group(1).lower()
    # Fallback: clean and use the whole string if no @ found (less ideal)
    sender_clean = re.sub(r'<.*?>', '', sender).strip().lower()
    logging.debug(f"Could not extract domain via regex for sender: '{sender}', using cleaned string: '{sender_clean}'")
    return sender_clean if sender_clean else "unknown_sender"

# --- Core ML Functions ---

def build_and_train_pipeline(training_df,
                             storage_client=None, # Added
                             bucket_name=None, # Added
                             pipeline_blob_name=DEFAULT_PIPELINE_FILENAME, # Use full blob path now
                             encoder_blob_name=DEFAULT_LABEL_ENCODER_FILENAME, # Use full blob path now
                             local_pipeline_filename=DEFAULT_PIPELINE_FILENAME, # Original base filename for local temp save
                             local_encoder_filename=DEFAULT_LABEL_ENCODER_FILENAME): # Original base filename for local temp save
    """
    Builds, trains, saves the scikit-learn pipeline and label encoder locally,
    and uploads them to Google Cloud Storage.
    Assumes training_df is a Pandas DataFrame with required columns:
    'text_features', 'llm_purpose', 'sender_domain', 'llm_urgency', 'corrected_priority'.
    Requires storage_client and bucket_name for GCS upload.
    """
    logging.info("--- Starting ML Pipeline Building and Training ---")
    if not isinstance(training_df, pd.DataFrame) or training_df.empty:
        logging.error("Training data is empty or not a DataFrame. Cannot train model.")
        return None, None

    required_cols = ['text_features', 'llm_purpose', 'sender_domain', 'llm_urgency', 'corrected_priority']
    missing_cols = [col for col in required_cols if col not in training_df.columns]
    if missing_cols:
        logging.error(f"Training DataFrame is missing required columns: {missing_cols}")
        return None, None

    # Define features (X) and target (y)
    X = training_df[['text_features', 'llm_purpose', 'sender_domain', 'llm_urgency']]
    y = training_df['corrected_priority']

    logging.info(f"Features prepared. Shape: {X.shape}")

    # Encode the target labels
    label_encoder = LabelEncoder()
    try:
        y_encoded = label_encoder.fit_transform(y)
        logging.info(f"Labels encoded. Classes found: {label_encoder.classes_}")
    except Exception as e:
        logging.error(f"Error encoding labels: {e}", exc_info=True)
        return None, None

    # Define preprocessing steps
    preprocessor = ColumnTransformer(
        transformers=[
            ('tfidf', TfidfVectorizer(stop_words='english', max_features=1000, ngram_range=(1, 2)), 'text_features'), # Added ngram_range
            ('onehot_purpose', OneHotEncoder(handle_unknown='ignore', min_frequency=0.01), ['llm_purpose']), # Added min_frequency
            ('onehot_domain', OneHotEncoder(handle_unknown='ignore', min_frequency=0.01), ['sender_domain']), # Added min_frequency
            ('numeric', 'passthrough', ['llm_urgency'])
        ],
        remainder='drop'
    )

    # Create the full pipeline
    pipeline = Pipeline([
        ('preprocess', preprocessor),
        ('classifier', LogisticRegression(solver='liblinear', random_state=42, class_weight='balanced', C=1.0)) # Added C parameter
    ])

    # Train the model
    logging.info("Training the model...")
    try:
        pipeline.fit(X, y_encoded)
        logging.info("Model training complete.")
    except Exception as e:
        logging.error(f"An error occurred during model training: {e}", exc_info=True)
        return None, None # Return None, None if training fails


    # --- Save Model Components Locally (to /tmp) and Upload to GCS ---
    # Use temp dir for reliable local saving in GCF's writable area
    with tempfile.TemporaryDirectory() as tmpdir:
        # Construct local paths using only the base filenames
        local_pipeline_path = os.path.join(tmpdir, os.path.basename(local_pipeline_filename))
        local_encoder_path = os.path.join(tmpdir, os.path.basename(local_encoder_filename))

        logging.info(f"Attempting to save models temporarily to: {tmpdir}")
        try:
            joblib.dump(pipeline, local_pipeline_path)
            logging.info(f"Pipeline temporarily saved to {local_pipeline_path}")
            joblib.dump(label_encoder, local_encoder_path)
            logging.info(f"Encoder temporarily saved to {local_encoder_path}")

            # Upload to GCS (ensure storage_client, bucket_name etc. are provided)
            if storage_client and bucket_name and pipeline_blob_name and encoder_blob_name:
                 logging.info(f"Attempting to upload models to GCS bucket: {bucket_name}")
                 bucket = storage_client.bucket(bucket_name)
                 pipeline_blob = bucket.blob(pipeline_blob_name) # Use full blob path
                 encoder_blob = bucket.blob(encoder_blob_name) # Use full blob path

                 pipeline_blob.upload_from_filename(local_pipeline_path, client=storage_client)
                 logging.info(f"Uploaded pipeline to gs://{bucket_name}/{pipeline_blob_name}")
                 encoder_blob.upload_from_filename(local_encoder_path, client=storage_client)
                 logging.info(f"Uploaded encoder to gs://{bucket_name}/{encoder_blob_name}")
                 logging.info("--- ML Pipeline Training and GCS Upload Successful ---")
                 return pipeline, label_encoder # Return fitted objects on success
            else:
                logging.error("GCS storage client, bucket name, or blob name missing. Cannot upload models.")
                return None, None # Fail if upload cannot happen

        except Exception as e:
            logging.error(f"Error saving pipeline/encoder locally to '{tmpdir}' or uploading to GCS: {e}", exc_info=True)
            return None, None # Fail if local save or upload fails

    # This part should not be reached if upload is successful due to return inside 'if'
    logging.error("Failed to save/upload models. Exited temporary directory block unexpectedly.")
    return None, None


def predict_priority(email_data_dict, pipeline, label_encoder):
    """
    Predicts the priority for a single email using the loaded pipeline and encoder.
    email_data_dict should contain: subject, body_text, llm_purpose, sender, llm_urgency
    """
    if not pipeline or not label_encoder:
        logging.error("ML pipeline or label encoder not loaded. Cannot predict.")
        return None

    if not isinstance(email_data_dict, dict):
         logging.error("Input email_data_dict is not a dictionary.")
         return None

    required_keys = ['subject', 'body_text', 'llm_purpose', 'sender', 'llm_urgency']
    missing_keys = [key for key in required_keys if key not in email_data_dict]
    if missing_keys:
        logging.error(f"Missing expected keys in input data for prediction: {missing_keys}")
        return None

    try:
        # Prepare input data in a DataFrame (pipeline expects it)
        input_df = pd.DataFrame([email_data_dict])

        # --- Data Cleaning / Preprocessing (Mirror training steps) ---
        input_df['subject'] = input_df['subject'].fillna('')
        input_df['body_text'] = input_df['body_text'].fillna('')
        input_df['text_features'] = input_df['subject'] + " " + input_df['body_text']
        # Ensure llm_urgency is numeric, default 0
        input_df['llm_urgency'] = pd.to_numeric(input_df['llm_urgency'], errors='coerce').fillna(0)
        input_df['llm_purpose'] = input_df['llm_purpose'].fillna("Unknown")
        input_df['sender_domain'] = input_df['sender'].apply(extract_domain)

        # Select feature columns in the correct order expected by the pipeline
        feature_columns = ['text_features', 'llm_purpose', 'sender_domain', 'llm_urgency']
        # Check if all needed columns exist after processing
        missing_feature_cols = [col for col in feature_columns if col not in input_df.columns]
        if missing_feature_cols:
             logging.error(f"DataFrame missing feature columns after preprocessing: {missing_feature_cols}")
             return None

        X_predict = input_df[feature_columns]

        # Make prediction
        logging.info("Attempting ML prediction...")
        predicted_label_numeric = pipeline.predict(X_predict)

        # Decode numeric label back to string
        predicted_priority_str = label_encoder.inverse_transform(predicted_label_numeric)

        logging.info(f"ML Prediction Successful: {predicted_priority_str[0]} (Numeric: {predicted_label_numeric[0]})")
        return predicted_priority_str[0] # Return the string label

    except KeyError as e:
        logging.error(f"Error during prediction preparation: Missing expected key: {e}", exc_info=True)
        return None
    except Exception as e:
        logging.error(f"An unexpected error occurred during ML prediction: {type(e).__name__}: {e}", exc_info=True)
        return None


# --- Model Loading Functions ---

def load_pipeline(storage_client=None, bucket_name=None, pipeline_blob_name=DEFAULT_PIPELINE_FILENAME):
    """
    Loads the ML pipeline from Google Cloud Storage.
    
    Args:
        storage_client: Google Cloud Storage client (optional, will try to create if None)
        bucket_name: GCS bucket name (optional, will try to get from environment if None)
        pipeline_blob_name: Blob name for the pipeline file
        
    Returns:
        Loaded pipeline object or None if failed
    """
    try:
        # Import GCS here to avoid import issues
        from google.cloud import storage
        
        # Get storage client
        if not storage_client:
            storage_client = storage.Client()
        
        # Get bucket name from environment if not provided
        if not bucket_name:
            bucket_name = os.getenv('MODEL_GCS_BUCKET') or os.getenv('GCS_BUCKET_NAME')
            if not bucket_name:
                logging.error("No bucket name provided and MODEL_GCS_BUCKET/GCS_BUCKET_NAME not set")
                return None
        
        # Add prefix if configured
        model_prefix = os.getenv('MODEL_GCS_PATH_PREFIX', '')
        if model_prefix and not pipeline_blob_name.startswith(model_prefix):
            pipeline_blob_name = model_prefix + pipeline_blob_name
        
        # Download pipeline from GCS
        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob(pipeline_blob_name)
        
        if not blob.exists():
            logging.warning(f"Pipeline file {pipeline_blob_name} not found in bucket {bucket_name}")
            return None
        
        # Download to temporary file and load
        with tempfile.NamedTemporaryFile(delete=False, suffix='.joblib') as temp_file:
            blob.download_to_filename(temp_file.name)
            pipeline = joblib.load(temp_file.name)
            
        # Clean up temp file
        os.unlink(temp_file.name)
        
        logging.info(f"Successfully loaded ML pipeline from {bucket_name}/{pipeline_blob_name}")
        return pipeline
        
    except Exception as e:
        logging.error(f"Failed to load ML pipeline: {e}", exc_info=True)
        return None


def load_label_encoder(storage_client=None, bucket_name=None, encoder_blob_name=DEFAULT_LABEL_ENCODER_FILENAME):
    """
    Loads the label encoder from Google Cloud Storage.
    
    Args:
        storage_client: Google Cloud Storage client (optional, will try to create if None)
        bucket_name: GCS bucket name (optional, will try to get from environment if None)
        encoder_blob_name: Blob name for the label encoder file
        
    Returns:
        Loaded label encoder object or None if failed
    """
    try:
        # Import GCS here to avoid import issues
        from google.cloud import storage
        
        # Get storage client
        if not storage_client:
            storage_client = storage.Client()
        
        # Get bucket name from environment if not provided
        if not bucket_name:
            bucket_name = os.getenv('MODEL_GCS_BUCKET') or os.getenv('GCS_BUCKET_NAME')
            if not bucket_name:
                logging.error("No bucket name provided and MODEL_GCS_BUCKET/GCS_BUCKET_NAME not set")
                return None
        
        # Add prefix if configured
        model_prefix = os.getenv('MODEL_GCS_PATH_PREFIX', '')
        if model_prefix and not encoder_blob_name.startswith(model_prefix):
            encoder_blob_name = model_prefix + encoder_blob_name
        
        # Download encoder from GCS
        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob(encoder_blob_name)
        
        if not blob.exists():
            logging.warning(f"Label encoder file {encoder_blob_name} not found in bucket {bucket_name}")
            return None
        
        # Download to temporary file and load
        with tempfile.NamedTemporaryFile(delete=False, suffix='.joblib') as temp_file:
            blob.download_to_filename(temp_file.name)
            label_encoder = joblib.load(temp_file.name)
            
        # Clean up temp file
        os.unlink(temp_file.name)
        
        logging.info(f"Successfully loaded label encoder from {bucket_name}/{encoder_blob_name}")
        return label_encoder
        
    except Exception as e:
        logging.error(f"Failed to load label encoder: {e}", exc_info=True)
        return None

