from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class BaseClass(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Reusable class identity row — a real FK target for
    `CharacterLevel.base_class_id`, mirroring `BaseRace`. Class rules content
    (hit die, BAB/save progression, skill points, class skills, spell type,
    archetypes, option groups) stays in `classes.json` until roadmap slice 8;
    `name` here is the join key back to that fixture data."""

    __tablename__ = "base_classes"

    name: Mapped[str] = mapped_column(String(255), unique=True)
