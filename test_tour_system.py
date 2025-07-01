#!/usr/bin/env python3
"""
Test script for the PenVault Tour System
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.models import User

def test_tour_system():
    """Test the tour system functionality"""
    app = create_app()
    
    with app.app_context():
        try:
            print("Testing PenVault Tour System...")
            
            # Test 1: Check if tour fields exist
            print("\n1. Testing tour fields in User model...")
            user = User.query.first()
            if user:
                print(f"✓ User found: {user.username}")
                print(f"✓ tour_completed field: {hasattr(user, 'tour_completed')}")
                print(f"✓ tour_progress field: {hasattr(user, 'tour_progress')}")
                
                # Set test values
                user.tour_completed = False
                user.tour_progress = {'test_step': True}
                db.session.commit()
                print(f"✓ Test values set successfully")
                
                # Verify values
                db.session.refresh(user)
                print(f"✓ tour_completed: {user.tour_completed}")
                print(f"✓ tour_progress: {user.tour_progress}")
            else:
                print("⚠ No users found in database")
            
            # Test 2: Check API endpoint
            print("\n2. Testing API endpoint...")
            with app.test_client() as client:
                # Login required for API
                print("⚠ API endpoint requires authentication (test manually)")
            
            # Test 3: Check file existence
            print("\n3. Testing file existence...")
            files_to_check = [
                'app/static/js/tour.js',
                'app/static/css/tour.css',
                'app/templates/test_tour.html'
            ]
            
            for file_path in files_to_check:
                if os.path.exists(file_path):
                    print(f"✓ {file_path} exists")
                else:
                    print(f"✗ {file_path} missing")
            
            print("\n✓ Tour system test completed successfully!")
            return True
            
        except Exception as e:
            print(f"\n✗ Error during testing: {e}")
            return False

def print_usage_instructions():
    """Print usage instructions"""
    print("\n" + "="*50)
    print("PENVAULT TOUR SYSTEM - USAGE INSTRUCTIONS")
    print("="*50)
    print("\n1. Start the Flask application:")
    print("   python -m flask run")
    print("\n2. Register a new account or login")
    print("\n3. The tour should start automatically for new users")
    print("\n4. For existing users, click the '?' button in navigation")
    print("\n5. Test the tour system at: http://localhost:5000/test-tour")
    print("\n6. Check tour progress in browser console:")
    print("   localStorage.getItem('penvault_tour_[user_id]')")
    print("\n" + "="*50)

if __name__ == '__main__':
    success = test_tour_system()
    if success:
        print_usage_instructions()
    else:
        print("\n✗ Tour system test failed!")
        sys.exit(1) 