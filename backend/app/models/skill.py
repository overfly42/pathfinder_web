import uuid

from sqlalchemy import Boolean, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class BaseSkill(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Identity-only catalog of skills (name + governing ability), replacing
    the old `skills.json` fixture — a real table so `BaseClassSkill` has a
    proper FK target and skill names have a stable id a future translation
    layer can key off of (name stays a single, unlocalized string for now,
    matching `BaseRace`/`BaseClass` — real DE/EN is still an open item, see
    todos.md)."""

    __tablename__ = "base_skills"

    name: Mapped[str] = mapped_column(String(255))
    # "ST"/"GE"/"KO"/"IN"/"WE"/"CH" — the same fixed 2-letter code convention
    # used everywhere else in this codebase (Character.ability_score_*,
    # rules/race_abilities.py), not a BaseAttribute FK.
    ability: Mapped[str] = mapped_column(String(2))
    # PF1e core's "Trained Only" column (Handle Animal, Knowledge (all),
    # Linguistics, Profession, Sleight of Hand, Spellcraft, Use Magic
    # Device, Disable Device): usable only with ranks > 0. Everything else
    # is usable untrained and belongs on the sheet even at 0 ranks — see
    # `sheet.py`'s `_build_skills`.
    trained_only: Mapped[bool] = mapped_column(Boolean, default=False)
    # The "Hintergrundfertigkeiten" alternate rule's fixed skill list
    # (http://prd.5footstep.de/Alternativregeln/Fertigkeiten/
    # Hintergrundfertigkeiten): Auftreten, Beruf, Fingerfertigkeit, Handwerk,
    # Kunstfertigkeit, Mit Tieren umgehen, Schätzen, Spezialwissen,
    # Sprachenkunde, Wissen (Adel/Baukunst/Geographie/Geschichte).
    # Kunstfertigkeit/Spezialwissen (2026-08-28) are themselves new skills
    # that alternate rule introduces, not just a re-flag on an existing one
    # — same `has_specialization` shape as Auftreten/Beruf/Handwerk below.
    # Meaningless unless `Character.use_background_skills` is set — see
    # that column's docstring and `rules/skill_points.py`'s
    # `background_skill_points_total`.
    is_background: Mapped[bool] = mapped_column(Boolean, default=False)
    # True only for Handwerk/Beruf/Auftreten: PF1e RAW requires picking a
    # concrete specialization ("Beruf (Seemann)") before ranks mean
    # anything — a character can hold the same skill multiple times, once
    # per specialization, each with its own rank total. See
    # `CharacterSkillRank.specialization_id`/`custom_specialization` and
    # `BaseSkillSpecialization` below.
    has_specialization: Mapped[bool] = mapped_column(Boolean, default=False)


class BaseSkillSpecialization(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Suggested specializations for a `has_specialization` skill (Handwerk/
    Beruf/Auftreten) — identity-only catalog rows, referenced by UUID from
    `CharacterSkillRank.specialization_id` rather than by name, so a future
    rule handler (`HANDLERS`-style, e.g. a class ability keyed to "Beruf
    (Seemann)" specifically) or translation layer never has to string-match
    a player-facing label. Same shape/reasoning as `BaseClassOptionChoice`.

    This is a list of suggestions, not an exhaustive enum: a player can also
    type a specialization that isn't here (`CharacterSkillRank.custom_specialization`,
    free text) — nothing in PF1e bounds what a Craft/Profession/Perform
    specialization can be."""

    __tablename__ = "base_skill_specializations"
    __table_args__ = (UniqueConstraint("skill_id", "name"),)

    skill_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("base_skills.id"))
    name: Mapped[str] = mapped_column(String(255))


class BaseClassSkill(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Which skills are class skills for a class — replaces `classes.json`'s
    `classSkills: string[]` arrays. `base_class_id` is always a root class's
    id, matching what `classes.json` covers today (no archetype adds/swaps a
    class skill yet).

    `option_choice_id` (nullable, FK `base_class_option_choices`) is null for
    a class skill every member gets, and set for one conditional on a
    specific `BaseClassOptionChoice` — same meaning as
    `BaseClassAbilityGrant.option_choice_id`. First needed by Mystiker
    (Oracle): each Mysterium adds its own extra class skills on top of the
    class's base list (e.g. the Firmament mystery adds Fliegen), a pattern no
    earlier class needed (domains/bloodlines/favored terrain don't touch
    class skills) — see the conversation this was scoped from."""

    __tablename__ = "base_class_skills"
    __table_args__ = (UniqueConstraint("base_class_id", "skill_id", "option_choice_id"),)

    base_class_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("base_classes.id"))
    skill_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("base_skills.id"))
    option_choice_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("base_class_option_choices.id"), nullable=True
    )
