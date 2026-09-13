"""add masterwork fields to base items and character gear

Revision ID: c3f1c0239344
Revises: b222744b5d20
Create Date: 2026-09-12 14:38:15.483674

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c3f1c0239344'
down_revision: Union[str, Sequence[str], None] = 'b222744b5d20'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# The four tool rows that used to be separate "X, Meisterarbeit" `BaseItem`
# catalog rows, each paired with the plain row it duplicated — masterwork is
# now `CharacterGear.is_masterwork` (an instance flag) priced by the plain
# row's own `masterwork_price_delta`, not a second catalog row. See
# `models.item.BaseItem.masterwork_price_delta`'s docstring for why the
# surcharge itself isn't a flat per-category constant here.
_MEISTERARBEIT_ROW_MIGRATIONS = [
    # (old "X, Meisterarbeit" id, canonical plain-row id, gp surcharge)
    ("03eaf970-6f90-578e-aff7-0b6707f7617d", "a413de5c-392e-5030-b593-db63a6766fb1", 70.0),  # Diebeswerkzeug
    ("a4c3cf1d-6bca-58f4-9b4c-c5545394b472", "9a96760c-de07-550d-a614-f56417eb3bb9", 95.0),  # Musikinstrument
    ("4e8a194c-b13d-5288-b5c5-b0f6df263de5", "eceb292b-ae7d-5c13-98f4-a25af0711b08", 49.0),  # Wahrsagekarten
    ("1eaf0b7c-422d-5771-b073-a2fc34b8e798", "1bba9661-fb1f-58fa-a3cb-ed6c69aa9f65", 50.0),  # Werkzeug eines Handwerkers
]


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('base_items', sa.Column('masterwork_price_delta', sa.Float(), nullable=True))
    op.add_column(
        'character_gear',
        sa.Column('is_masterwork', sa.Boolean(), nullable=False, server_default=sa.false()),
    )

    # Every weapon has the same flat +300 gp RAW masterwork surcharge (no
    # per-weapon exception exists in this catalog, unlike the named tools
    # below) — seeding it here too so a fresh `alembic upgrade head` is
    # already correct without waiting for the next `item_seed` run.
    op.execute("UPDATE base_items SET masterwork_price_delta = 300.0 WHERE category = 'weapon'")

    for old_id, canonical_id, delta in _MEISTERARBEIT_ROW_MIGRATIONS:
        op.execute(f"UPDATE base_items SET masterwork_price_delta = {delta} WHERE id = '{canonical_id}'")
        # Re-point any character who already owned the separate "X,
        # Meisterarbeit" row onto the plain row with the flag set, rather
        # than orphaning their `character_gear` row once it's deleted below.
        # `ON CONFLICT DO NOTHING` guards the one theoretical edge case where
        # a character owned both rows already (would otherwise violate
        # `character_gear`'s (character_id, item_id) unique constraint) —
        # that row is simply dropped along with the catalog row itself.
        op.execute(
            f"""
            UPDATE character_gear SET item_id = '{canonical_id}', is_masterwork = true
            WHERE item_id = '{old_id}'
            AND NOT EXISTS (
                SELECT 1 FROM character_gear existing
                WHERE existing.character_id = character_gear.character_id
                AND existing.item_id = '{canonical_id}'
            )
            """
        )
        op.execute(f"DELETE FROM character_gear WHERE item_id = '{old_id}'")
        op.execute(f"DELETE FROM base_items WHERE id = '{old_id}'")


def downgrade() -> None:
    """Downgrade schema. Re-inserts the four deleted catalog rows (static
    data, safe to recreate); does *not* reverse the `character_gear`
    re-pointing above, since which rows were touched isn't recoverable at
    downgrade time — same asymmetry `f2d551a5b053`'s rename accepts."""
    op.execute(
        """
        INSERT INTO base_items (id, name, category, price, weight_lb)
        VALUES
            ('03eaf970-6f90-578e-aff7-0b6707f7617d', 'Diebeswerkzeug [Meisterarbeit]', 'tool', 100.0, '2 Pfd.'),
            ('a4c3cf1d-6bca-58f4-9b4c-c5545394b472', 'Musikinstrument, Meisterarbeit', 'tool', 100.0, '3 Pfd.*'),
            ('4e8a194c-b13d-5288-b5c5-b0f6df263de5', 'Wahrsagekarten, Meisterarbeit', 'tool', 50.0, '1 Pfd.'),
            ('1eaf0b7c-422d-5771-b073-a2fc34b8e798', 'Werkzeug eines Handwerkers, Meisterarbeit', 'tool', 55.0, '5 Pfd.')
        ON CONFLICT (id) DO NOTHING
        """
    )
    op.drop_column('character_gear', 'is_masterwork')
    op.drop_column('base_items', 'masterwork_price_delta')
