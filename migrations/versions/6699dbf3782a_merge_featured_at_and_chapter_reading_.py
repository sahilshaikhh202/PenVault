"""Merge featured_at and chapter_reading_history migrations

Revision ID: 6699dbf3782a
Revises: 589232b9597d, add_chapter_reading_history
Create Date: 2025-06-28 23:33:08.124174

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '6699dbf3782a'
down_revision = ('589232b9597d', 'add_chapter_reading_history')
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
