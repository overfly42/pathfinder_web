"""companion HD choices, repeatable feats (roadmap slice 10 step 3)

Revision ID: e5b8d3f1a6c2
Revises: db3ee20a6bdb
Create Date: 2026-10-17 16:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e5b8d3f1a6c2'
down_revision: Union[str, Sequence[str], None] = 'db3ee20a6bdb'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('base_classes', sa.Column('allowed_skill_ids', sa.JSON(), nullable=True))
    op.add_column('base_classes', sa.Column('recommended_feat_ids', sa.JSON(), nullable=True))
    op.add_column('base_feats', sa.Column('is_repeatable', sa.Boolean(), server_default='false', nullable=False))
    op.add_column(
        'character_levels', sa.Column('choices_pending', sa.Boolean(), server_default='false', nullable=False)
    )
    # Companions created before this step got their HD without any feat/
    # skill/ability-increase choices — those choices are still open.
    op.execute(
        """
        UPDATE character_levels SET choices_pending = true
        WHERE base_class_id IN (SELECT id FROM base_classes WHERE is_companion_class)
        """
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('character_levels', 'choices_pending')
    op.drop_column('base_feats', 'is_repeatable')
    op.drop_column('base_classes', 'recommended_feat_ids')
    op.drop_column('base_classes', 'allowed_skill_ids')
