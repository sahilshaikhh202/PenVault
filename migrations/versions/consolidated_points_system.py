"""consolidated points system

Revision ID: consolidated_points_system
Revises: f1d40b73c1dc
Create Date: 2024-03-19

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'consolidated_points_system'
down_revision = 'f1d40b73c1dc'
branch_labels = None
depends_on = None

def upgrade():
    # Create points_transactions table
    op.create_table('points_transaction',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('action', sa.String(length=50), nullable=False),
        sa.Column('points', sa.Integer(), nullable=False),
        sa.Column('timestamp', sa.DateTime(), nullable=True),
        sa.Column('details', sa.String(length=200), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['user.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    # Add points-related columns to user table
    op.add_column('user', sa.Column('points', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('user', sa.Column('last_daily_login', sa.Date(), nullable=True))
    op.add_column('user', sa.Column('last_post_points', sa.Date(), nullable=True))
    op.add_column('user', sa.Column('last_comment_points', sa.Date(), nullable=True))
    op.add_column('user', sa.Column('comment_points_count', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('user', sa.Column('share_points_count', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('user', sa.Column('referral_count', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('user', sa.Column('highest_pulse_tier', sa.String(length=20), nullable=True))

    # Add is_featured column to story table
    op.add_column('story', sa.Column('is_featured', sa.Boolean(), nullable=False, server_default='false'))

def downgrade():
    # Drop points_transactions table
    op.drop_table('points_transaction')

    # Drop points-related columns from user table
    op.drop_column('user', 'points')
    op.drop_column('user', 'last_daily_login')
    op.drop_column('user', 'last_post_points')
    op.drop_column('user', 'last_comment_points')
    op.drop_column('user', 'comment_points_count')
    op.drop_column('user', 'share_points_count')
    op.drop_column('user', 'referral_count')
    op.drop_column('user', 'highest_pulse_tier')

    # Drop is_featured column from story table
    op.drop_column('story', 'is_featured') 