"""`CharacterContext` — the single raw-data object every `HANDLERS`/
`EFFECT_HANDLERS` entry gets called with, across every rule-element family
(race abilities, class abilities, effects, weapon abilities with real
computed state). Decided 2026-08-10, refined 2026-08-10 (`roadmap.md`'s
"Uniform CharacterContext handler signature"; full rationale in
`readme.md`'s "Request pipeline" section). Holds only a character's own raw
state — ability scores, composition ids, active-effect rows — never a
computed/stacked value, so no handler can ever depend on another handler's
*output*, only on raw data every handler sees the same way.

Every field defaults to empty so a `CharacterContext` can be built even
where no persisted `Character` exists yet (e.g. `routers/races.py`'s
ability-score checks during character creation) — a handler that never
reads a given field is unaffected by that field being empty. Fields get
populated as the call sites that can actually supply them are migrated
(`roadmap.md`/`todos.md` track this per handler family); an empty field
today is an honest "not wired yet", the same convention `EFFECT_HANDLERS`
itself started with."""

from collections import Counter
from dataclasses import dataclass, field
from typing import TYPE_CHECKING
from uuid import UUID

if TYPE_CHECKING:
    from ..models.effect import CharacterEffect


@dataclass
class CharacterContext:
    ability_scores: dict[str, int] = field(default_factory=dict)
    skill_ranks: dict[UUID, int] = field(default_factory=dict)
    feat_ids: frozenset[UUID] = frozenset()
    trait_ids: frozenset[UUID] = frozenset()
    # trait id -> chosen skill id, for traits whose `BaseTrait.skill_choice_ability`
    # is set (2026-08-21, "Gewitztes Wortspiel") — a handler keyed by one of
    # those trait ids reads its own pick from here, same "raw composition
    # input, not a computed value" reasoning as every other field on this
    # dataclass. Empty for a character with no such trait.
    trait_skill_choices: dict[UUID, UUID] = field(default_factory=dict)
    # A `Counter`, not a `frozenset`: some class abilities are granted more
    # than once at different levels and each repetition has independent
    # mechanical weight (`sheet.py`'s `granted_class_ability_ids` docstring
    # — e.g. Seeräuber's Wilder Seemann, `rules/classes/barbarian.py`), so a
    # handler reading its own id's count off this field (same pattern
    # `rules/speed.py`'s `class_speed_bonus` already used before this field
    # existed) sees how many of its own grants are currently met, not just
    # whether it has any. A plain membership/iteration check (`x in
    # context.granted_ability_ids`) still works unchanged — `Counter` is a
    # `dict` subclass.
    granted_ability_ids: Counter[UUID] = field(default_factory=Counter)
    # Full rows, not just ids: unlike the other composition fields above, a
    # handler resolving an active effect needs to decide *how multiple
    # independent instances of its own id combine* (ability damage from two
    # sources sums; the same fear condition from two sources doesn't double
    # up) — see `rules/effects.py`'s docstring, which this field replaces
    # the reasoning of.
    active_effects: list["CharacterEffect"] = field(default_factory=list)
    gear_item_ids: frozenset[UUID] = frozenset()
    # How many `CharacterLevel` rows this character has per root class taken
    # (`Character._class_level_counts()`, keyed by id instead of by
    # `BaseClass` row) — the one raw input a level-scaling class-ability
    # handler needs (e.g. Kampfrausch's rounds/day, `rules/classes/
    # barbarian.py`) that nothing else on this dataclass already carries.
    level_counts_by_root_id: dict[UUID, int] = field(default_factory=dict)
    # How many times this character has picked each race-scoped
    # favored-class-bonus `BaseClassOptionChoice` id over their whole career
    # (`CharacterClassOption` rows with `group_key == "favored_class_bonus"`,
    # same "count, not membership" shape `granted_ability_ids` uses since a
    # pick can recur every favored level) — the one raw input a handler whose
    # daily allowance an ARG racial favored-class bonus augments needs (e.g.
    # Entfesselter Barbar's Kampfrausch rounds/day, `rules/classes/
    # barbarian.py`) that nothing else here carries. `rules/
    # favored_class_bonuses.py`'s own `HANDLERS` still owns *converting* a
    # pick count into a bonus value; this field only supplies the raw count.
    favored_class_bonus_pick_counts: Counter[UUID] = field(default_factory=Counter)
    # `BaseClassAbility.requires_active_ability_id` for every one of this
    # character's granted abilities that has it set (`sheet.py`'s
    # `build_character_sheet`, one query alongside the one that already
    # resolves `granted_ability_ids`) — lets `requirement_met` below answer
    # "is ability X's prerequisite currently satisfied" generically, so
    # `rules/handlers.py`'s granted-ability dispatch loops (`granted_ability_modifiers`,
    # `situational_skill_notes`, `sheet.py`'s `NATURAL_ATTACK_HANDLERS`/
    # `WEAPON_BONUS_DAMAGE_HANDLERS` loops) can skip calling a gated ability's
    # handler at all, instead of every such handler re-checking `has_active`
    # on its own hardcoded "what gates me" id.
    requires_active_ability_id: dict[UUID, UUID] = field(default_factory=dict)
    # Every weapon-category proficiency feat granted automatically by a
    # class ability (`rules/proficiency.py`'s `class_granted_proficiency_feat_ids`)
    # — always blanket-category, never a single weapon (an automatic grant
    # never carries a chosen weapon). Combined with `feat_ids` above by
    # `rules/proficiency.py`'s `known_weapon_types` to resolve the
    # `BaseItem.weapon_type` categories a character is blanket-proficient
    # with. Kept as its own field rather than folded into `feat_ids`:
    # `feat_ids` means "feats this character actually picked" everywhere
    # else on this dataclass (e.g. Waffenfinesse's own check in `sheet.py`),
    # and conflating the two would silently change that meaning for every
    # existing reader.
    class_granted_proficiency_feat_ids: frozenset[UUID] = frozenset()
    # Exact `BaseItem` ids a character is proficient with via a *picked*
    # single-weapon-choice feat ("Umgang mit Kriegswaffen"/"Umgang mit
    # exotischen Waffen" with `chosen_weapon_id` set — see
    # `rules/proficiency.py`'s module docstring on why these two feats are
    # dual-natured), a Kensai's own free weapon choice, or a race ability's
    # fixed named-weapon list (`rules/handlers.py`'s `WEAPON_PROFICIENCY_HANDLERS`,
    # e.g. Elf's "Elfische Waffenvertrautheit") — the other half of the same
    # weapon-proficiency check, for a weapon that's proficient by name rather
    # than by category.
    chosen_weapon_ids: frozenset[UUID] = frozenset()
    # Exact `BaseItem` ids that get Weapon Focus's +1 attack bonus — a
    # player's own picked "Waffenfokus" (`CharacterFeat.chosen_weapon_id`)
    # folded together with a Kensai's free grant of the same effect for
    # their kensai weapon (`rules/classes/kampfmagus.py`'s
    # `KENSAI_WEAPON_FOCUS_ABILITY_ID`) — one set regardless of source, same
    # reasoning as `chosen_weapon_ids` above.
    weapon_focus_weapon_ids: frozenset[UUID] = frozenset()
    # The armor currently equipped in the "ruestung" slot's weight class
    # (`BaseItem.armor_weight_class`, "light"/"medium"/"heavy") — `None` if
    # no armor is equipped at all. The one raw input a handler gating on
    # "no/light armor" needs (e.g. Kensai's/Duellant's Gewitzte Verteidigung)
    # that nothing else on this dataclass carries.
    equipped_armor_weight_class: str | None = None
    # Whether a shield is currently equipped in the "schild" slot — the
    # other half of the same gate.
    has_shield_equipped: bool = False

    def has_active(self, ability_id: UUID) -> bool:
        """Whether `active_effects` contains at least one instance sourced
        from `ability_id`."""
        return any(e.source_id == ability_id for e in self.active_effects)

    def requirement_met(self, ability_id: UUID) -> bool:
        """Whether `ability_id`'s own `requires_active_ability_id` (if any)
        is currently satisfied — `True` when it has no requirement at all.
        Doesn't apply to an ability gating *itself* (e.g. Kampfrausch's own
        handler only runs while its own effect is active in the first
        place, see `rules/handlers.py`'s `granted_ability_modifiers`
        docstring) — only to one ability requiring some *other* ability's
        effect."""
        required_id = self.requires_active_ability_id.get(ability_id)
        return required_id is None or self.has_active(required_id)
