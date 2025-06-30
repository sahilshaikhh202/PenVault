#!/usr/bin/env python3
"""
Test script to verify the chapter reading history functionality.
This script can be used to test the chapter history tracking and display.
"""

import os
import sys
from datetime import datetime, timedelta

# Add the project directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.models import Story, User, Novel, Chapter, ChapterReadingHistory

def test_chapter_history():
    """Test the chapter reading history functionality"""
    app = create_app()
    
    with app.app_context():
        print("=== Testing Chapter Reading History System ===")
        
        # Get a test user
        test_user = User.query.first()
        if not test_user:
            print("No users found in database. Please create a user first.")
            return
        
        print(f"Testing with user: {test_user.username}")
        
        # Get a test novel
        test_novel = Novel.query.first()
        if not test_novel:
            print("No novels found in database. Please create a novel first.")
            return
        
        print(f"Testing with novel: {test_novel.title}")
        
        # Get chapters for this novel
        chapters = Chapter.query.filter_by(novel_id=test_novel.id).order_by(Chapter.order.asc()).all()
        if not chapters:
            print("No chapters found for this novel. Please create chapters first.")
            return
        
        print(f"Found {len(chapters)} chapters")
        
        # Test chapter history tracking
        print("\n=== Testing Chapter History Tracking ===")
        
        # Simulate reading different chapters
        for i, chapter in enumerate(chapters[:3]):  # Test with first 3 chapters
            print(f"Simulating reading chapter: {chapter.title}")
            
            # Check if there's already an entry for this user and novel
            existing_history = ChapterReadingHistory.query.filter_by(
                user_id=test_user.id, 
                novel_id=test_novel.id
            ).first()
            
            if existing_history:
                # Update existing entry with new chapter and timestamp
                existing_history.chapter_id = chapter.id
                existing_history.timestamp = datetime.utcnow() - timedelta(hours=i)
                print(f"Updated existing history entry to chapter {chapter.title}")
            else:
                # Create new entry
                new_history = ChapterReadingHistory(
                    user_id=test_user.id,
                    novel_id=test_novel.id,
                    chapter_id=chapter.id,
                    timestamp=datetime.utcnow() - timedelta(hours=i)
                )
                db.session.add(new_history)
                print(f"Created new history entry for chapter {chapter.title}")
        
        try:
            db.session.commit()
            print("Successfully saved chapter history")
        except Exception as e:
            db.session.rollback()
            print(f"Error saving chapter history: {e}")
            return
        
        # Test reading history retrieval
        print("\n=== Testing Reading History Retrieval ===")
        
        # Get chapter reading history
        chapter_history = test_user.chapter_reading_history.order_by(ChapterReadingHistory.timestamp.desc()).all()
        print(f"Total chapter history entries: {len(chapter_history)}")
        
        for entry in chapter_history:
            print(f"- {entry.chapter.title} ({entry.novel.title}) - {entry.timestamp}")
        
        # Test combined history (as used in profile page)
        print("\n=== Testing Combined History (Profile Page Style) ===")
        
        combined_history = []
        
        # Get story reading history
        story_history = test_user.reading_history.order_by(ChapterReadingHistory.timestamp.desc()).limit(20).all()
        for entry in story_history:
            combined_history.append({
                'type': 'story',
                'title': entry.story.title,
                'timestamp': entry.timestamp,
                'story': entry.story,
                'novel': None,
                'chapter': None,
                'history_id': entry.id
            })
        
        # Get chapter reading history
        chapter_history = test_user.chapter_reading_history.order_by(ChapterReadingHistory.timestamp.desc()).limit(20).all()
        for entry in chapter_history:
            combined_history.append({
                'type': 'chapter',
                'title': f"{entry.chapter.title} ({entry.novel.title})",
                'timestamp': entry.timestamp,
                'story': entry.novel.story,
                'novel': entry.novel,
                'chapter': entry.chapter,
                'history_id': entry.id
            })
        
        # Sort combined history by timestamp (most recent first) and take top 20
        combined_history.sort(key=lambda x: x['timestamp'], reverse=True)
        combined_history = combined_history[:20]
        
        print(f"Combined history entries: {len(combined_history)}")
        for entry in combined_history:
            print(f"- [{entry['type'].upper()}] {entry['title']} - {entry['timestamp']}")
        
        print("\n=== Chapter History Test Complete ===")

if __name__ == '__main__':
    test_chapter_history() 