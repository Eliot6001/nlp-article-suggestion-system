#!/usr/bin/env python

import os
import sys
from datetime import datetime, timezone
import logging
import json

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import Config
from user_profile_builder import UserProfileBuilder as ProfileBuilder
from mock_supabase import MockSupabaseManager, write_test_data_to_file
from local_user_profile_builder import LocalUserProfileBuilder

def setup_test_environment():
    """Set up the test environment using real article data"""
    data_path = "mock_data.json"
    article_source = "../../result.txt"  # Path to your article data
    
    # Always regenerate data from source file
    if os.path.exists(article_source):
        print(f"Generating test data from {article_source}")
        write_test_data_to_file(data_path)  # This now uses result.txt
    else:
        raise FileNotFoundError(f"Article source file not found: {article_source}")
    
    return data_path

def inspect_test_data(data_path):
    """Print summary of test data"""
    with open(data_path, 'r') as f:
        data = json.load(f)
    
    print(f"\nTest data summary:")
    print(f"- {len(data['user_ids'])} users")
    print(f"- {len(data['post_ids'])} posts")
    print(f"- {len(data['activities'])} activities")
    
    # Verify article metadata
    if not data['metadata']:
        print("\nWARNING: No article metadata loaded!")
    else:
        print(f"\nFirst article metadata:")
        first_post = data['post_ids'][0]
        print(f"Post ID: {first_post}")
        print(f"Keywords: {', '.join(data['metadata'][first_post].get('keywords', []))}")
        print(f"Topics: {', '.join(data['metadata'][first_post].get('topics', []))}")

def run_test(data_path, user_limit=3):
    """Run the profile builder with test data"""
    config = Config()
    builder = LocalUserProfileBuilder(config, data_path)
    
    print(f"\nProcessing profiles for {user_limit} users...")
    try:
        builder.process_users(user_limit)
    except Exception as e:
        print(f"\nERROR in profile building: {str(e)}")
        raise

if __name__ == "__main__":
    print("Starting local test of User Profile Builder\n")
    try:
        data_path = setup_test_environment()
        inspect_test_data(data_path)
        run_test(data_path)
    except Exception as e:
        print(f"\nTest failed: {str(e)}")
        sys.exit(1)
    print("\nTest completed successfully!")