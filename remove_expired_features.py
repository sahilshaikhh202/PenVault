#!/usr/bin/env python3
"""
Script to automatically remove expired featured stories after 24 hours.
This script can be run as a scheduled task (cron job) to automatically clean up expired features.
"""

import os
import sys
from datetime import datetime, timedelta

# Add the project directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.models import Story

def remove_expired_features():
    """Remove stories that have been featured for more than 24 hours"""
    app = create_app()
    
    with app.app_context():
        try:
            twenty_four_hours_ago = datetime.utcnow() - timedelta(hours=24)
            expired_stories = Story.query.filter(
                Story.is_featured == True,
                Story.featured_at < twenty_four_hours_ago
            ).all()
            
            removed_count = 0
            for story in expired_stories:
                story.is_featured = False
                story.featured_at = None
                removed_count += 1
                print(f"Removed feature from: {story.title} (ID: {story.id})")
            
            if expired_stories:
                db.session.commit()
                print(f"Successfully removed {removed_count} expired featured stories")
            else:
                print("No expired featured stories found")
            
            return removed_count
            
        except Exception as e:
            db.session.rollback()
            print(f"Error removing expired features: {e}")
            return 0

if __name__ == '__main__':
    print(f"Starting expired feature removal at {datetime.utcnow()}")
    removed_count = remove_expired_features()
    print(f"Completed expired feature removal. Removed {removed_count} stories.")
    sys.exit(0 if removed_count >= 0 else 1) 