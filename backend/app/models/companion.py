import uuid

from sqlalchemy import CheckConstraint, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class BaseCompanionLevelSource(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """One source of an effective master level for a companion track
    (roadmap slice 10, step 1) — e.g. "Druide level" or "Waldläufer level −3"
    for `animal_companion`, "Magier level" for `familiar`. Pure data; the
    sum per track is computed by `rules/companions.py`'s
    `master_effective_level`.

    `track` is the stacking group: `animal_companion` (mounts included) or
    `familiar`. Sources of one track add up (PF1e: companion levels from
    several sources stack), unless they share a `stack_group` — then only
    the highest counts (no source needs that yet).

    Trigger: exactly one of `class_ability_id` / `feat_id` (check
    constraint). A source only counts while its trigger is among the
    character's granted class abilities (`CharacterContext.
    granted_ability_ids`, Sekundärklasse grants included) or picked feats.

    `kind`: `class_level` (levels in `root_class_id`, then
    `(level + offset) // divisor`, floored at `minimum` and at 0 — same
    formula as `rules/secondary_class.py`'s `secondary_effective_level`),
    `character_level` (total level, same formula) or `flat_bonus` (`offset`
    as a plain bonus, e.g. Stallmeister +1). A source whose real rule
    doesn't fit (the Kleriker's Tier-Domäne taken by a Druide counts *Druide*
    level −3) gets a `rules/companions.py` `COMPANION_LEVEL_HANDLERS` entry
    keyed by this row's id instead of extra columns.

    `label` is the breakdown text on the sheet ("Druide", "Stallmeister")."""

    __tablename__ = "base_companion_level_sources"
    __table_args__ = (
        CheckConstraint(
            "(class_ability_id IS NULL) <> (feat_id IS NULL)", name="ck_companion_level_source_one_trigger"
        ),
        CheckConstraint(
            "kind IN ('class_level', 'character_level', 'flat_bonus')", name="ck_companion_level_source_kind"
        ),
        CheckConstraint("track IN ('animal_companion', 'familiar')", name="ck_companion_level_source_track"),
    )

    track: Mapped[str] = mapped_column(String(32))
    label: Mapped[str] = mapped_column(String(255))
    class_ability_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("base_class_abilities.id"), nullable=True
    )
    feat_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("base_feats.id"), nullable=True)
    kind: Mapped[str] = mapped_column(String(32))
    root_class_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("base_classes.id"), nullable=True
    )
    offset: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    divisor: Mapped[int] = mapped_column(Integer, default=1, server_default="1")
    minimum: Mapped[int | None] = mapped_column(Integer, nullable=True)
    stack_group: Mapped[str | None] = mapped_column(String(64), nullable=True)
