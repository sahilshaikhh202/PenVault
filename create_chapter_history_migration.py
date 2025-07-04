#!/usr/bin/env python3
"""
Script to create a database migration for the ChapterReadingHistory model.
Run this script to generate the migration file.
"""

import os
import sys

# Add the project directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def create_migration():
    """Create the migration file for ChapterReadingHistory"""
    migration_content = '''"""Add ChapterReadingHistory model

Revision ID: add_chapter_reading_history
Revises: 44bd232cdddf
Create Date: 2025-01-27 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_chapter_reading_history'
down_revision = '44bd232cdddf'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('chapter_reading_history',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('novel_id', sa.Integer(), nullable=False),
    sa.Column('chapter_id', sa.Integer(), nullable=False),
    sa.Column('timestamp', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['chapter_id'], ['chapter.id'], ),
    sa.ForeignKeyConstraint(['novel_id'], ['novel.id'], ),
    sa.ForeignKeyConstraint(['user_id'], ['user.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('user_id', 'novel_id', name='uq_user_novel_reading')
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('chapter_reading_history')
    # ### end Alembic commands ###
'''
    
    # Create migrations directory if it doesn't exist
    migrations_dir = os.path.join('migrations', 'versions')
    os.makedirs(migrations_dir, exist_ok=True)
    
    # Write the migration file
    migration_file = os.path.join(migrations_dir, 'add_chapter_reading_history.py')
    with open(migration_file, 'w') as f:
        f.write(migration_content)
    
    print(f"Migration file created: {migration_file}")
    print("To apply the migration, run: flask db upgrade")

if __name__ == '__main__':
    create_migration() 