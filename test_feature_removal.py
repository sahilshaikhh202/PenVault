#!/usr/bin/env python3
"""
Test script to verify the 24-hour feature removal functionality.
This script can be used to test the feature removal logic.
"""

import os
import sys
from datetime import datetime, timedelta

# Add the project directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.models import Story, User

def test_feature_removal():
    """Test the feature removal functionality"""
    app = create_app()
    
    with app.app_context():
        print("=== Testing 24-Hour Feature Removal System ===")
        
        # Get current featured stories
        current_featured = Story.query.filter_by(is_featured=True).all()
        print(f"Currently featured stories: {len(current_featured)}")
        
        for story in current_featured:
            if story.featured_at:
                time_until_expiry = (story.featured_at + timedelta(hours=24)) - datetime.utcnow()
                print(f"- {story.title}: Featured at {story.featured_at}, expires in {time_until_expiry}")
            else:
                print(f"- {story.title}: No featured_at timestamp (legacy data)")
        
        # Test the removal function
        print("\n=== Testing Removal Function ===")
        from app.routes import remove_expired_features
        removed_count = remove_expired_features()
        print(f"Removed {removed_count} expired features")
        
        # Check remaining featured stories
        remaining_featured = Story.query.filter_by(is_featured=True).all()
        print(f"Remaining featured stories: {len(remaining_featured)}")
        
        # Show stories that would be featured on homepage
        twenty_four_hours_ago = datetime.utcnow() - timedelta(hours=24)
        homepage_featured = Story.query.filter(
            Story.is_featured == True, 
            Story.is_published == True,
            Story.featured_at >= twenty_four_hours_ago
        ).order_by(Story.featured_at.desc()).all()
        
        print(f"\nStories that would appear on homepage: {len(homepage_featured)}")
        for story in homepage_featured:
            time_until_expiry = (story.featured_at + timedelta(hours=24)) - datetime.utcnow()
            print(f"- {story.title}: Expires in {time_until_expiry}")

if __name__ == '__main__':
    test_feature_removal() 