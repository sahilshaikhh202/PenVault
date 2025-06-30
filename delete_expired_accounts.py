#!/usr/bin/env python3
"""
Script to delete expired accounts that have passed the 20-day waiting period.
This script can be run manually or scheduled as a cron job.

Usage:
    python delete_expired_accounts.py
"""

import os
import sys
from datetime import datetime, timedelta

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.models import User

def delete_expired_accounts():
    """Delete accounts that have passed the 20-day waiting period"""
    app = create_app()
    
    with app.app_context():
        try:
            # Find accounts that have passed the 20-day waiting period
            cutoff_date = datetime.utcnow() - timedelta(days=20)
            expired_accounts = User.query.filter(
                User.deletion_requested_at.isnot(None),
                User.deletion_requested_at <= cutoff_date
            ).all()
            
            if not expired_accounts:
                print("No expired accounts found.")
                return
            
            print(f"Found {len(expired_accounts)} expired accounts to delete.")
            
            deleted_count = 0
            for user in expired_accounts:
                try:
                    print(f"Deleting account: {user.username} (ID: {user.id})")
                    user.delete_account_permanently()
                    deleted_count += 1
                    print(f"Successfully deleted account: {user.username}")
                except Exception as e:
                    print(f"Error deleting user {user.username} (ID: {user.id}): {e}")
            
            print(f"Successfully deleted {deleted_count} out of {len(expired_accounts)} expired accounts.")
            
        except Exception as e:
            print(f"Error in delete_expired_accounts: {e}")
            sys.exit(1)

if __name__ == "__main__":
    delete_expired_accounts() 