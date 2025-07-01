#!/usr/bin/env python3
"""
Migration script to add genre, status, and is_mature fields to the novel table.
Run this script to update your database schema.
"""

import os
import sys
from sqlalchemy import text

# Add the parent directory to the path so we can import app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db


def add_novel_fields():
    """Add genre, status, and is_mature fields to the novel table"""
    app = create_app()
    
    with app.app_context():
        try:
            # Check if the fields already exist
            inspector = db.inspect(db.engine)
            columns = [col['name'] for col in inspector.get_columns('novel')]
            
            print("Current novel table columns:", columns)
            
            # Add genre field if it doesn't exist
            if 'genre' not in columns:
                print("Adding genre field...")
                db.session.execute(text("ALTER TABLE novel ADD COLUMN genre VARCHAR(100)"))
                db.session.commit()
                print("✓ Added genre field")
                # Set default genre for existing novels
                db.session.execute(text("UPDATE novel SET genre = 'general' WHERE genre IS NULL"))
                db.session.commit()
                print('✓ Set default genre for existing novels')
            else:
                print("✓ Genre field already exists")
            
            # Add status field if it doesn't exist
            if 'status' not in columns:
                print("Adding status field...")
                db.session.execute(text("ALTER TABLE novel ADD COLUMN status VARCHAR(50) DEFAULT 'ongoing'"))
                db.session.commit()
                print("✓ Added status field")
            else:
                print("✓ Status field already exists")
            
            # Add is_mature field if it doesn't exist
            if 'is_mature' not in columns:
                print("Adding is_mature field...")
                db.session.execute(text("ALTER TABLE novel ADD COLUMN is_mature BOOLEAN DEFAULT FALSE"))
                db.session.commit()
                print("✓ Added is_mature field")
            else:
                print("✓ is_mature field already exists")
            
            print("\n✅ Migration completed successfully!")
            print("The novel table now has all required fields: genre, status, and is_mature")
            
        except Exception as e:
            print(f"❌ Error during migration: {e}")
            return False
    
    return True

if __name__ == "__main__":
    print("🔄 Starting novel fields migration...")
    success = add_novel_fields()
    
    if success:
        print("\n🎉 Migration completed successfully!")
        print("You can now use the novel creation and editing features.")
    else:
        print("\n💥 Migration failed. Please check the error messages above.")
        sys.exit(1) 