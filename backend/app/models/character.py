import uuid

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Character(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Minimal "thin" character row (roadmap slice 2): identity, race, class,
    level fixed at 1, hit points. Ability scores/skills/feats/traits are a
    later "thick" pass. `class_name` is a plain fixture reference (the class
    name as it appears in `classes.json`), not a FK — classes stay in JSON
    fixtures until roadmap slice 8, unlike races."""

    __tablename__ = "characters"

    name: Mapped[str] = mapped_column(String(255))
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    race_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("base_races.id"))
    class_name: Mapped[str] = mapped_column(String(255))
    level: Mapped[int] = mapped_column(Integer, default=1)
    # Current (not max) HP — see readme.md's ER diagram, where max HP is derived
    # from per-level CharacterLevel.hit_points rows (roadmap slice 7), not stored
    # here. Nullable: HP calculation needs a class hit-die value that doesn't
    # exist anywhere yet (classes.json has no hit-die field) — a slice 3 concern,
    # not something to fake here with a placeholder number.
    current_hit_points: Mapped[int | None] = mapped_column(Integer, nullable=True)
