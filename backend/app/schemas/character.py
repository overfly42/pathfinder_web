from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, field_validator, model_validator

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


class FeatSelection(BaseModel):
    """One feat pick, plus its sub-choice if `BaseFeat.sub_choice_type` calls
    for one (roadmap.md's "Talent-Sub-Wahl-Schema") — a list rather than a
    dict keyed by `feat_id` (contrast `spell_ids`, still a flat dict) so an
    open-choice feat like Waffenfokus can legitimately appear more than once
    in the same submission, once per distinct weapon/skill/school. Exactly
    one of `chosen_weapon_id`/`chosen_skill_id`/`chosen_spell_school` may be
    set; whether one is *required*, and which, depends on the referenced
    feat's own `sub_choice_type` — that's catalog data, so it's checked
    server-side (`routers/characters.py`), not here."""

    model_config = ConfigDict(from_attributes=True)

    feat_id: UUID
    chosen_weapon_id: UUID | None = None
    chosen_skill_id: UUID | None = None
    chosen_spell_school: str | None = None

    @field_validator("chosen_spell_school")
    @classmethod
    def chosen_spell_school_must_not_be_blank(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("chosen_spell_school must not be blank")
        return value

    @model_validator(mode="after")
    def at_most_one_sub_choice(self) -> "FeatSelection":
        chosen = [self.chosen_weapon_id, self.chosen_skill_id, self.chosen_spell_school]
        if sum(1 for value in chosen if value is not None) > 1:
            raise ValueError(
                "a feat selection may set at most one of chosen_weapon_id/chosen_skill_id/chosen_spell_school"
            )
        return self


class SkillRankSelection(BaseModel):
    """One skill-rank entry — a list rather than a dict keyed by `skill_id`
    (contrast the flat shape `spell_ids`/`trait_skill_choices` still use)
    because a `has_specialization` skill (Handwerk/Beruf/Auftreten) can
    legitimately appear more than once in the same submission, once per
    distinct specialization — same "open choice, so a list" reasoning as
    `FeatSelection`. Exactly one of `specialization_id`/`custom_specialization`
    may be set; whether one is *required* (only when the referenced skill's
    `has_specialization` is true) is catalog data, so it's checked
    server-side (`routers/characters.py`'s `_validate_skill_specialization`),
    not here — same split `FeatSelection`/`_validate_feat_sub_choice` use."""

    model_config = ConfigDict(from_attributes=True)

    skill_id: UUID
    specialization_id: UUID | None = None
    custom_specialization: str | None = None
    ranks: int

    @field_validator("custom_specialization")
    @classmethod
    def custom_specialization_must_not_be_blank(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("custom_specialization must not be blank")
        return value

    @model_validator(mode="after")
    def at_most_one_specialization_choice(self) -> "SkillRankSelection":
        if self.specialization_id is not None and self.custom_specialization is not None:
            raise ValueError(
                "a skill rank selection may set at most one of specialization_id/custom_specialization"
            )
        return self


class GearSelection(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    item_id: UUID
    quantity: int

    @field_validator("quantity")
    @classmethod
    def quantity_must_be_positive(cls, value: int) -> int:
        if value < 1:
            raise ValueError("quantity must be at least 1")
        return value


class CharacterCreate(BaseModel):
    name: str
    user_id: UUID
    race_id: UUID
    classes: list[ClassSelection]
    # Player-entered HP roll for every level *except* the character's very
    # first (that one is always maxed automatically — see
    # `rules/progression.py`), keyed by character level number as a string
    # (e.g. `{"2": 7, "3": 5}` for a level-3 character) since JSON object
    # keys can't be ints. Validated server-side against that level's class's
    # `hit_dice` (`routers/characters.py`): must cover exactly levels
    # 2..total_level, one entry each, each between 1 and that die's max,
    # inclusive.
    hit_points: dict[str, int] = {}
    # Player-chosen favored-class bonus ("hp" | "skill" | a race+class-
    # specific BaseClassOptionChoice name, see LevelUp.favored_class_bonus)
    # for every level the character starts in their favored class (the root
    # of the first entry in `classes` — see `create_character`'s
    # `favored_root_id`), keyed by level number as a string, same reasoning
    # as `hit_points`. Unlike `hit_points`, level 1 is included: PF1e grants
    # this bonus starting at 1st level too, it's just never a *rolled* HP
    # value there. Validated server-side against exactly the favored-class
    # levels among 1..total_level.
    favored_class_bonus: dict[str, str] = {}
    ability_scores: dict[str, int]
    point_budget: Literal[10, 15, 20, 25]
    flex_ability: str | None = None
    # Optional alternate-trait names (matching `GET /api/races`' `alt[].name`
    # for this character's race), resolved server-side via
    # `routers/races.py`'s `resolve_alt_trait` and persisted as
    # `CharacterRacialChoice` rows — same table as `flex_ability`.
    alt_traits: list[str] = []
    # Opt-in to the "Hintergrundfertigkeiten" alternate rule (+2 skill ranks
    # per level, spendable only on `BaseSkill.is_background` skills) — a
    # one-time creation-time choice, persisted on `Character` and never
    # resubmitted at level-up (see that column's docstring in
    # models/character.py, and todos.md's "2026-08-19" entry for why it's
    # per-character rather than always-on or global).
    use_background_skills: bool = False
    # One entry per skill (or, for a has_specialization skill, per chosen
    # specialization — see SkillRankSelection) with its total ranks.
    # Collapsed onto the highest CharacterLevel row being created — see
    # CharacterSkillRank's docstring for why creation doesn't split this per
    # level the way a later level-up will.
    skill_ranks: list[SkillRankSelection] = []
    # Chosen feats (+ sub-choice, see FeatSelection), capped server-side by
    # the base progression plus any race/class bonus feat slots (see
    # rules/feat_slots.py; mirrors the wizard's featMax in
    # creationCalculations.ts). Collapsed onto the highest CharacterLevel row
    # being created, same reasoning as skill_ranks.
    feats: list[FeatSelection] = []
    # Chosen trait ids (max 2, a flat PF1e-standard cap unrelated to
    # race/class, unlike feats) — collapsed onto the highest CharacterLevel
    # row being created, same reasoning as feats.
    trait_ids: list[UUID] = []
    # trait_id (string, since UUID keys aren't valid JSON object keys) ->
    # chosen skill id, for traits whose `BaseTrait.skill_choice_ability` is
    # set (2026-08-21, "Gewitztes Wortspiel") — additive/optional rather than
    # folded into `trait_ids` itself (contrast `feats`' richer `FeatSelection`
    # list): a trait can only ever be taken once, so a plain dict keyed by
    # trait id is enough, same "dict keyed by stringified UUID" convention as
    # `skill_ranks`/`spell_ids`. Empty (the default) for every trait that
    # doesn't need a sub-choice. Validated server-side against `trait_ids`
    # and each trait's own `skill_choice_ability` in `routers/characters.py`
    # (same "can't check catalog data in a field validator" reasoning as
    # `_validate_feat_sub_choice`).
    trait_skill_choices: dict[str, UUID] = {}
    # base_class_id (string, since UUID keys aren't valid JSON object keys) ->
    # chosen spell ids, for spontaneous/arcane-prepared classes only (see
    # rules/spells.py) — grade-0 spells are mandatory-but-implicit for
    # arcane-prepared classes (validated as present, not counted against the
    # budget). Collapsed onto the highest CharacterLevel row being created,
    # same reasoning as skill_ranks/feats.
    spell_ids: dict[str, list[UUID]] = {}
    # Starting gear picked from the real `base_items` catalog (roadmap slice
    # 3's "minimal starting gear" — descriptive only, no equip slots or AC
    # computation yet, see CharacterGear). Unlike feats/trait_ids/
    # spell_ids, not collapsed onto a CharacterLevel row: gear isn't gained
    # at a level, it's the character's current inventory (CharacterGear is
    # keyed by character_id directly), matching how slice 4's in-play
    # gear endpoints will manage it too.
    gear: list[GearSelection] = []

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
    def skill_ranks_must_not_be_negative(cls, value: list[SkillRankSelection]) -> list[SkillRankSelection]:
        if any(selection.ranks < 0 for selection in value):
            raise ValueError("skill_ranks must not be negative")
        return value

    @field_validator("skill_ranks")
    @classmethod
    def skill_ranks_must_not_have_duplicate_selections(
        cls, value: list[SkillRankSelection]
    ) -> list[SkillRankSelection]:
        seen = set()
        for selection in value:
            key = (selection.skill_id, selection.specialization_id, selection.custom_specialization)
            if key in seen:
                raise ValueError("skill_ranks must not contain the same skill+specialization more than once")
            seen.add(key)
        return value

    @field_validator("feats")
    @classmethod
    def feats_must_not_have_duplicate_selections(cls, value: list[FeatSelection]) -> list[FeatSelection]:
        """Rejects the exact same feat+sub-choice twice — not just the same
        `feat_id` twice, since an open-choice feat (e.g. Waffenfokus) may
        legitimately be picked more than once for different weapons."""
        seen = set()
        for selection in value:
            key = (
                selection.feat_id,
                selection.chosen_weapon_id,
                selection.chosen_skill_id,
                selection.chosen_spell_school,
            )
            if key in seen:
                raise ValueError("feats must not contain the same feat with the same sub-choice more than once")
            seen.add(key)
        return value

    @field_validator("trait_ids")
    @classmethod
    def trait_ids_must_not_have_duplicates_and_max_two(cls, value: list[UUID]) -> list[UUID]:
        if len(set(value)) != len(value):
            raise ValueError("trait_ids must not contain duplicates")
        if len(value) > 2:
            raise ValueError("trait_ids must not exceed 2")
        return value

    @field_validator("spell_ids")
    @classmethod
    def spell_ids_must_not_have_duplicates(cls, value: dict[str, list[UUID]]) -> dict[str, list[UUID]]:
        for spell_ids in value.values():
            if len(set(spell_ids)) != len(spell_ids):
                raise ValueError("spell_ids must not contain duplicates within a class")
        return value

    @field_validator("gear")
    @classmethod
    def gear_must_not_have_duplicate_items(cls, value: list["GearSelection"]) -> list["GearSelection"]:
        item_ids = [selection.item_id for selection in value]
        if len(set(item_ids)) != len(item_ids):
            raise ValueError("gear must not contain the same item_id more than once")
        return value


class LevelUpTarget(BaseModel):
    """Which class this level-up's new `CharacterLevel` belongs to — either
    another level in a class the character already has ("existing", by that
    class's root `base_class_id`, matching `Character.classes[].id`), or the
    character's first level in a brand-new class ("new", a multiclass pick,
    same archetypes/options shape as `ClassSelection` since it's a level-1
    class-taken exactly like one row of `CharacterCreate.classes`)."""

    model_config = ConfigDict(from_attributes=True)

    mode: Literal["existing", "new"]
    base_class_id: UUID | None = None
    class_name: str | None = None
    archetypes: list[str] = []
    options: dict[str, list[str]] = {}

    @model_validator(mode="after")
    def mode_matches_fields(self) -> "LevelUpTarget":
        if self.mode == "existing":
            if self.base_class_id is None:
                raise ValueError("target.base_class_id is required when mode is 'existing'")
            if self.archetypes or self.options:
                raise ValueError("target.archetypes/options only apply to mode 'new'")
        else:
            if not (self.class_name and self.class_name.strip()):
                raise ValueError("target.class_name is required when mode is 'new'")
            if self.base_class_id is not None:
                raise ValueError("target.base_class_id does not apply to mode 'new'")
        return self


class LevelUp(BaseModel):
    """Body for `POST /api/characters/{id}/level-up` — adds exactly one new
    `CharacterLevel` to an existing character. Deliberately mirrors
    `CharacterCreate`'s field shapes (`FeatSelection`, per-group `options`)
    rather than inventing new ones, since the same validation/persistence
    code is reused for both. Unlike creation, every quantity here is this
    *level's own delta* (new skill ranks, new feats, one new spell), not a
    cumulative total — `routers/characters.py`'s level-up endpoint derives
    each delta's cap by calling the same budget functions creation uses
    twice (character's classes before/after this level) and subtracting."""

    target: LevelUpTarget
    # Player-entered HP roll for this one new level — never auto-maxed like a
    # character's very first level, since level-up is by definition not that.
    hit_points: int
    # Required exactly when this level is in the character's favored class
    # (http://prd.5footstep.de/Grundregelwerk/Fertigkeiten-erwerben: "Charaktere,
    # die eine Stufe in ihrer bevorzugten Klasse aufsteigen, erhalten die
    # Möglichkeit, 1 zusätzlichen Fertigkeitsrang oder 1 zusätzlichen
    # Trefferpunkt zu bekommen") — must be None otherwise. "hp"/"skill" are
    # the two stable literal values every class always offers, checked and
    # applied directly by `routers/characters.py` (+1 to hit_points above /
    # +1 to this level's skill-point budget). Any other value is a real
    # `BaseClassOptionChoice` name from that class's own `favored_class_bonus`
    # option group (e.g. an Advanced Race Guide alternate bonus scoped to the
    # character's race, `scripts/import_favored_class_bonus_halbork.py`,
    # 2026-08-16) — no longer a fixed `Literal`, DB-validated instead like
    # every other option-group pick.
    favored_class_bonus: str | None = None
    # Recurring per-class picks gated by the receiving class's own new level
    # (e.g. a ranger's 2nd favored enemy at level 5) — only meaningful for
    # mode "existing"; a "new" class's level-1 picks go in target.options
    # instead, same as CharacterCreate.classes[].options.
    existing_level_options: dict[str, list[str]] = {}
    ability_increase: str | None = None
    # One entry per skill/specialization (see SkillRankSelection) with its
    # *new* ranks gained this level — same shape/semantics as
    # CharacterCreate.skill_ranks, just a delta instead of a total. Per PF1e
    # (http://prd.5footstep.de/Grundregelwerk/Fertigkeiten-erwerben: "Du
    # kannst nie mehr Ränge in einer Fertigkeit besitzen, als es deinen
    # gesamten Trefferwürfeln entspricht"), the only cap on a single
    # skill+specialization is total ranks <= character level — a
    # skill/specialization with 0 prior ranks can legally receive more than 1
    # new rank in one level-up (e.g. catching up a long-neglected skill), not
    # just +1.
    skill_ranks: list[SkillRankSelection] = []
    # 0–2 entries: a regular new feat slot (odd levels) and/or a class bonus
    # feat slot (e.g. Kämpfer), both validated/stored identically — the
    # backend never distinguishes "regular" vs "bonus", only the frontend UI
    # explains the two as separate fields.
    feats: list[FeatSelection] = []
    spell_id: UUID | None = None

    @field_validator("ability_increase")
    @classmethod
    def ability_increase_must_be_a_known_key(cls, value: str | None) -> str | None:
        if value is not None and value not in ABILITY_KEYS:
            raise ValueError(f"ability_increase must be one of {ABILITY_KEYS}")
        return value

    @field_validator("skill_ranks")
    @classmethod
    def skill_ranks_must_be_positive(cls, value: list[SkillRankSelection]) -> list[SkillRankSelection]:
        if any(selection.ranks <= 0 for selection in value):
            raise ValueError("skill_ranks must be positive (omit a skill rather than sending 0)")
        return value

    @field_validator("skill_ranks")
    @classmethod
    def skill_ranks_must_not_have_duplicate_selections(
        cls, value: list[SkillRankSelection]
    ) -> list[SkillRankSelection]:
        seen = set()
        for selection in value:
            key = (selection.skill_id, selection.specialization_id, selection.custom_specialization)
            if key in seen:
                raise ValueError("skill_ranks must not contain the same skill+specialization more than once")
            seen.add(key)
        return value

    @field_validator("feats")
    @classmethod
    def feats_must_not_have_duplicate_selections(cls, value: list[FeatSelection]) -> list[FeatSelection]:
        seen = set()
        for selection in value:
            key = (
                selection.feat_id,
                selection.chosen_weapon_id,
                selection.chosen_skill_id,
                selection.chosen_spell_school,
            )
            if key in seen:
                raise ValueError("feats must not contain the same feat with the same sub-choice more than once")
            seen.add(key)
        return value


class HpAdjust(BaseModel):
    """Body for `PATCH /api/characters/{id}/hp`. `delta` is the signed
    change to *current* HP: positive heals, negative damages (matches the
    character sheet's `VitalsBar`/`onApplyHp` convention on the frontend).
    Persisted as the inverse onto `Character.damage_taken` — remaining HP is
    always derived at read time, never stored directly (see that column's
    docstring). Negative `delta` drains `Character.temporary_hit_points`
    first, only spilling into `damage_taken` once the temporary pool is
    exhausted (`routers/characters.py`'s `adjust_hp`); positive `delta`
    (real healing) never refills it.

    `temporary_hit_points`, when present, *sets* the temporary-HP pool to
    that value rather than adding to it — a spell/rage grant replaces the
    old pool rather than stacking with it (same simplification PF1e itself
    generally uses: temporary HP from the same or a new source doesn't
    stack, the player keeps the higher single pool). Independent of `delta`:
    both may be sent in one request (e.g. a GM manually setting HP down and
    granting temp HP at once), or just one."""

    delta: int | None = None
    temporary_hit_points: int | None = None


class GearUpdate(BaseModel):
    """Body for `PATCH /api/characters/{id}/gear/{item_id}` — any subset of
    quantity/enhancement/properties/special_ability_ids/stored_spell_id may
    be omitted (unchanged). `special_ability_ids`, when present, replaces the
    item's entire `BaseWeaponSpecialAbility` set (not a delta/append) — same
    replace-whole-list semantics as `properties`, just structured instead of
    freetext (see `models.character.CharacterGear`'s docstring).
    `stored_spell_id` sets which spell a wand instance stores (only valid for
    category "wand" — checked server-side in `routers/characters.py`, see
    roadmap.md's "Wondrous-Item-Katalog mit echter Attributsboni-Wirkung")."""

    quantity: int | None = None
    enhancement: int | None = None
    properties: list[str] | None = None
    special_ability_ids: list[UUID] | None = None
    stored_spell_id: UUID | None = None

    @field_validator("quantity")
    @classmethod
    def quantity_must_be_positive(cls, value: int | None) -> int | None:
        if value is not None and value < 1:
            raise ValueError("quantity must be at least 1")
        return value

    @field_validator("special_ability_ids")
    @classmethod
    def special_ability_ids_must_not_have_duplicates(cls, value: list[UUID] | None) -> list[UUID] | None:
        if value is not None and len(set(value)) != len(value):
            raise ValueError("special_ability_ids must not contain duplicates")
        return value


class SlotUpdate(BaseModel):
    """Body for `PUT /api/characters/{id}/slots/{slot_key}` — `item_id: null`
    unequips whatever is currently in that slot."""

    item_id: UUID | None = None


class SpellbookAdd(BaseModel):
    """Body for `POST /api/characters/{id}/spellbook` — the in-play
    "add a spell to the spellbook" action (`requirements_v2.md` §2.2),
    arcane-prepared classes only (see `rules/spells.py`'s module docstring:
    spontaneous casters only learn new spells at level-up, and
    divine-prepared casters have no known-spell list to add to)."""

    base_class_id: UUID
    spell_id: UUID


class SpellPrepare(BaseModel):
    """Body for `POST`/`DELETE .../spells/{spell_id}/prepare` and
    `POST .../spells/{spell_id}/cast` — same shape as `SpellbookAdd`, but for
    the in-play prepare/cast actions (`requirements_v2.md` §2.2's "vorbereitet"/
    "gewirkt" states), not the permanent known-list/spellbook."""

    base_class_id: UUID


class EffectActivate(BaseModel):
    """Body for `POST /api/characters/{id}/effects` — activates a persistent
    effect on a character (roadmap slice 5). `source_type` selects which
    catalog `source_id` resolves against; for "spell"/"class_ability"/"feat"
    the referenced row must have `is_persistent_effect=True`; "condition"
    only needs to exist in `BaseCondition`. Whether this specific character
    actually knows/has that spell/ability/feat isn't checked here — that's
    roadmap slice 6's "legality checks" (explicitly deferred, see
    roadmap.md), not this slice. `level` and the countdown fields are supplied
    by the player since nothing in the data model can derive them (see
    `models.effect.CharacterEffect`'s docstring) — all optional, so a simple
    "until removed" effect can omit every one. "feat" (2026-08-16, e.g.
    Heftiger Angriff) reuses this same generic activation flow rather than a
    parallel one — `BaseFeat.default_duration_rounds` only pre-fills the
    frontend's duration field, `duration_remaining` here is still whatever
    the player actually submits."""

    source_type: Literal["spell", "class_ability", "condition", "feat"]
    source_id: UUID
    level: int | None = None
    incubation_remaining: int | None = None
    duration_remaining: int | None = None
    frequency_rounds: int | None = None
    successes_required: int | None = None


class EffectSaveResult(BaseModel):
    """Body for `POST /api/characters/{id}/effects/{effect_id}/save-result`
    — records the outcome of one of an effect's periodic saves (poison/
    disease). Success increments `successes_current` (curing/deleting the
    effect once it reaches `successes_required`); failure resets
    `successes_current` to 0 without changing `level` (a failed save doesn't
    escalate severity). Either way `next_check_in` resets to
    `frequency_rounds`. Only updates the row's own state — the resulting
    stat impact stays computed at sheet-read time via `EFFECT_HANDLERS` off
    whatever the row currently holds, same composition-vs-computation split
    as everywhere else, not a mutation triggered from here."""

    success: bool


class AdvanceTime(BaseModel):
    """Body for `POST /api/characters/{id}/advance-time` — ticks every
    active effect's countdowns forward. Uses the same round conversion as
    the existing mock's time buttons (round=1, minute=10, hour=600); "day"
    is a full rest — plain-duration effects clear (matches the old mock's
    "+1 Tag includes a rest") but frequency-tracked ones (poison/disease)
    don't, since surviving a rest is correct PF1e behavior for those, unlike
    the old mock's blanket clear."""

    unit: Literal["round", "minute", "hour", "day"]


class EffectRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    character_id: UUID
    source_type: str
    source_id: UUID
    level: int | None
    incubation_remaining: int | None
    duration_remaining: int | None
    frequency_rounds: int | None
    next_check_in: int | None
    successes_current: int
    successes_required: int | None


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
    # Persisted state, not remaining HP — see `Character.damage_taken`'s
    # docstring; remaining HP is only derived in `sheet.py`'s fuller display
    # shape, not exposed here.
    damage_taken: int | None
    temporary_hit_points: int
    # Computed (not stored) from each class's own `bab_progression`/
    # `fort_save`/`ref_save`/`wil_save` and level count, summed across
    # classes — see `Character.bab`/`Character.saves` (models/character.py)
    # and `rules/progression.py`.
    bab: int
    saves: dict[str, int]
    ability_scores: dict[str, int]
    point_budget: int
    flex_ability: str | None
    alt_traits: list[str]
    use_background_skills: bool
    skill_ranks: dict[str, int]
    feats: list[FeatSelection]
    trait_ids: list[UUID]
    spell_ids: dict[str, list[UUID]]
    gear: list[GearSelection]
