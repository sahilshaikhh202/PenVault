"""Add slug fields to Novel, Volume, Chapter and update models as needed

Revision ID: b531977eddd7
Revises: 04d16bcc558c
Create Date: 2025-06-05 14:34:30.704016

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import table, column
from sqlalchemy import String
from slugify import slugify


# revision identifiers, used by Alembic.
revision = 'b531977eddd7'
down_revision = '04d16bcc558c'
branch_labels = None
depends_on = None


def upgrade():
    # 1. Add slug columns as nullable
    with op.batch_alter_table('novel') as batch_op:
        batch_op.add_column(sa.Column('slug', sa.String(length=200), nullable=True))
    with op.batch_alter_table('volume') as batch_op:
        batch_op.add_column(sa.Column('slug', sa.String(length=200), nullable=True))
    with op.batch_alter_table('chapter') as batch_op:
        batch_op.add_column(sa.Column('slug', sa.String(length=200), nullable=True))

    # 2. Populate slugs for existing data
    bind = op.get_bind()
    # Populate novel slugs
    novels = bind.execute(sa.text("SELECT id, title FROM novel")).fetchall()
    for n in novels:
        slug = slugify(n.title)
        bind.execute(sa.text("UPDATE novel SET slug = :slug WHERE id = :id"), {"slug": slug, "id": n.id})
    # Populate volume slugs
    volumes = bind.execute(sa.text("SELECT id, title FROM volume")).fetchall()
    for v in volumes:
        slug = slugify(v.title)
        bind.execute(sa.text("UPDATE volume SET slug = :slug WHERE id = :id"), {"slug": slug, "id": v.id})
    # Populate chapter slugs
    chapters = bind.execute(sa.text("SELECT id, title FROM chapter")).fetchall()
    for c in chapters:
        slug = slugify(c.title)
        bind.execute(sa.text("UPDATE chapter SET slug = :slug WHERE id = :id"), {"slug": slug, "id": c.id})

    # 3. Alter columns to NOT NULL and add unique constraints
    with op.batch_alter_table('novel') as batch_op:
        batch_op.alter_column('slug', nullable=False)
        batch_op.create_unique_constraint('uq_novel_slug', ['slug'])
    with op.batch_alter_table('volume') as batch_op:
        batch_op.alter_column('slug', nullable=False)
        batch_op.create_unique_constraint('uq_volume_novel_slug', ['novel_id', 'slug'])
    with op.batch_alter_table('chapter') as batch_op:
        batch_op.alter_column('slug', nullable=False)
        batch_op.create_unique_constraint('uq_chapter_volume_slug', ['volume_id', 'slug'])


def downgrade():
    with op.batch_alter_table('chapter') as batch_op:
        batch_op.drop_constraint('uq_chapter_volume_slug', type_='unique')
        batch_op.drop_column('slug')
    with op.batch_alter_table('volume') as batch_op:
        batch_op.drop_constraint('uq_volume_novel_slug', type_='unique')
        batch_op.drop_column('slug')
    with op.batch_alter_table('novel') as batch_op:
        batch_op.drop_constraint('uq_novel_slug', type_='unique')
        batch_op.drop_column('slug')
