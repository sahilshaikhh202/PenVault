#!/usr/bin/env python3
"""
Migration script to add tour tracking fields to existing users
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.models import User

def migrate_tour_fields():
    """Add tour tracking fields to existing users"""
    app = create_app()
    
    with app.app_context():
        try:
            # Get all users
            users = User.query.all()
            
            for user in users:
                # Set default values for tour fields
                if not hasattr(user, 'tour_completed') or user.tour_completed is None:
                    user.tour_completed = False
                
                if not hasattr(user, 'tour_progress') or user.tour_progress is None:
                    user.tour_progress = {}
            
            # Commit changes
            db.session.commit()
            print(f"Successfully migrated {len(users)} users with tour fields")
            
        except Exception as e:
            db.session.rollback()
            print(f"Error during migration: {e}")
            return False
    
    return True

if __name__ == '__main__':
    print("Starting tour fields migration...")
    success = migrate_tour_fields()
    if success:
        print("Migration completed successfully!")
    else:
        print("Migration failed!")
        sys.exit(1) 