from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, field_validator

from ..rules.point_buy import ABILITY_KEYS


class ClassSelection(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    class_name: str
    level: int
    # Zero or more archetypes for this class-taken (each a `BaseClass` row
    # whose `arch_class_of` is this class's root) — combining archetypes that
    # actually conflict isn't validated yet (see todos.md).
    archetypes: list[str] = []
    # Set server-side (the first class in a submitted `classes` list), not
    # read from client input on create — kept on this shared model since
    # CharacterRead needs to expose it per class-taken.
    is_favored: bool = False
    # group_key (e.g. "domain", "bloodline", "school") -> chosen value(s),
    # validated against that class's `optionGroups` in classes.json.
    options: dict[str, list[str]] = {}

    @field_validator("class_name")
    @classmethod
    def class_name_must_not_be_blank(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("class_name must not be blank")
        return stripped

    @field_validator("level")
    @classmethod
    def level_must_be_positive(cls, value: int) -> int:
        if value < 1:
            raise ValueError("level must be at least 1")
        return value


class CharacterCreate(BaseModel):
    name: str
    user_id: UUID
    race_id: UUID
    classes: list[ClassSelection]
    current_hit_points: int | None = None
    ability_scores: dict[str, int]
    point_budget: Literal[10, 15, 20, 25]
    flex_ability: str | None = None
    # Optional alternate-trait names (matching `GET /api/races`' `alt[].name`
    # for this character's race), resolved server-side via
    # `routers/races.py`'s `resolve_alt_trait` and persisted as
    # `CharacterRacialChoice` rows — same table as `flex_ability`.
    alt_traits: list[str] = []
    # skill_id (string, since UUID keys aren't valid JSON object keys) ->
    # ranks. Collapsed onto the highest CharacterLevel row being created —
    # see CharacterSkillRank's docstring for why creation doesn't split this
    # per level the way a later level-up will.
    skill_ranks: dict[str, int] = {}
    # Chosen feat ids, capped server-side by the base progression plus any
    # race/class bonus feat slots (see rules/feat_slots.py; mirrors the
    # wizard's featMax in creationCalculations.ts). Collapsed onto the
    # highest CharacterLevel row being created, same reasoning as skill_ranks.
    feat_ids: list[UUID] = []

    @field_validator("name")
    @classmethod
    def must_not_be_blank(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("must not be blank")
        return stripped

    @field_validator("classes")
    @classmethod
    def classes_must_not_be_empty(cls, value: list[ClassSelection]) -> list[ClassSelection]:
        if not value:
            raise ValueError("classes must not be empty")
        return value

    @field_validator("ability_scores")
    @classmethod
    def ability_scores_must_have_exactly_the_six_keys_in_range(cls, value: dict[str, int]) -> dict[str, int]:
        if set(value) != set(ABILITY_KEYS):
            raise ValueError(f"ability_scores must have exactly the keys {ABILITY_KEYS}")
        if any(score < 7 or score > 18 for score in value.values()):
            raise ValueError("ability_scores must each be between 7 and 18")
        return value

    @field_validator("flex_ability")
    @classmethod
    def flex_ability_must_be_a_known_key(cls, value: str | None) -> str | None:
        if value is not None and value not in ABILITY_KEYS:
            raise ValueError(f"flex_ability must be one of {ABILITY_KEYS}")
        return value

    @field_validator("alt_traits")
    @classmethod
    def alt_traits_must_not_have_duplicates(cls, value: list[str]) -> list[str]:
        if len(set(value)) != len(value):
            raise ValueError("alt_traits must not contain duplicates")
        return value

    @field_validator("skill_ranks")
    @classmethod
    def skill_ranks_must_not_be_negative(cls, value: dict[str, int]) -> dict[str, int]:
        if any(ranks < 0 for ranks in value.values()):
            raise ValueError("skill_ranks must not be negative")
        return value

    @field_validator("feat_ids")
    @classmethod
    def feat_ids_must_not_have_duplicates(cls, value: list[UUID]) -> list[UUID]:
        if len(set(value)) != len(value):
            raise ValueError("feat_ids must not contain duplicates")
        return value


class CharacterUpdate(BaseModel):
    name: str

    @field_validator("name")
    @classmethod
    def name_must_not_be_blank(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("name must not be blank")
        return stripped


class CharacterRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    user_id: UUID
    race_id: UUID
    classes: list[ClassSelection]
    level: int
    current_hit_points: int | None
    ability_scores: dict[str, int]
    point_budget: int
    flex_ability: str | None
    alt_traits: list[str]
    skill_ranks: dict[str, int]
    feat_ids: list[UUID]
