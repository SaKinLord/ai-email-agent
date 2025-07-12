#!/usr/bin/env python3
"""
Debug script to check Firestore connection and collections
"""

import sys
import logging
from google.cloud import firestore

# Set up logging
logging.basicConfig(level=logging.INFO)

def test_firestore_connection():
    """Test basic Firestore connection"""
    try:
        # Try to initialize the client using service account
        client = firestore.Client.from_service_account_json('credentials.json')
        print("SUCCESS: Firestore client initialized successfully!")
        print(f"Project ID: {client.project}")
        return client
    except Exception as e:
        print(f"ERROR: Failed to initialize Firestore client: {e}")
        return None

def check_collections(client):
    """Check what collections exist and their document counts"""
    try:
        collections = ['emails', 'feedback', 'agent_state', 'action_requests']
        
        for collection_name in collections:
            print(f"\nChecking collection: {collection_name}")
            
            # Get collection reference
            collection_ref = client.collection(collection_name)
            
            # Try to get a few documents
            docs = list(collection_ref.limit(5).stream())
            print(f"   Found {len(docs)} documents (showing first 5)")
            
            if docs:
                # Show first document structure
                first_doc = docs[0]
                doc_data = first_doc.to_dict()
                print(f"   Sample document fields: {list(doc_data.keys())}")
                
                # If it's emails collection, show more details
                if collection_name == 'emails':
                    print(f"   Sample email fields:")
                    for key, value in doc_data.items():
                        if isinstance(value, str) and len(value) > 50:
                            print(f"      {key}: {value[:50]}...")
                        else:
                            print(f"      {key}: {value}")
            else:
                print("   No documents found in this collection")
                
    except Exception as e:
        print(f"ERROR: Error checking collections: {e}")

def test_emails_query(client):
    """Test the specific query used in ui_app.py"""
    try:
        print(f"\nTesting emails query (order by processed_timestamp)...")
        
        emails_ref = client.collection('emails').order_by(
            'processed_timestamp', direction=firestore.Query.DESCENDING
        ).limit(5)
        
        emails = list(emails_ref.stream())
        print(f"   Query returned {len(emails)} emails")
        
        for i, doc in enumerate(emails):
            data = doc.to_dict()
            processed_time = data.get('processed_timestamp', 'Missing')
            sender = data.get('sender', 'Unknown sender')
            subject = data.get('subject', 'No subject')
            priority = data.get('priority', 'Unknown priority')
            
            print(f"   Email {i+1}: {sender} - {subject[:30]}... (Priority: {priority}, Processed: {processed_time})")
            
    except Exception as e:
        print(f"ERROR: Error testing emails query: {e}")
        import traceback
        traceback.print_exc()

def main():
    print("Debugging Firestore connection and data...")
    
    # Test connection
    client = test_firestore_connection()
    if not client:
        print("Cannot proceed without Firestore connection.")
        return
    
    # Check collections
    check_collections(client)
    
    # Test specific query
    test_emails_query(client)
    
    print("\nDebug complete!")

if __name__ == "__main__":
    main()