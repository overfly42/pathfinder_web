"""Kampfmagus (Magus) and its four archetypes (Kensai, Seelenschmied,
Skirnir, Zauberstreiter) — each archetype's "Vermindertes Zauberwirken"
(Diminished Spellcasting, `SPELL_SLOT_DELTA` below), Kensai's own free
weapon choice (`KENSAI_WEAPON_CHOICE_ABILITY_ID`/`KENSAI_WEAPON_FOCUS_ABILITY_ID`),
Kensai's "Gewitzte Verteidigung" (Canny Defense, `HANDLERS` below), and the
Kampfmagus root class's own "Arkaner Vorrat" (Arcane Reservoir,
`ARKANER_VORRAT_ABILITY_ID` below — pool size plus its headline "verbessere
eine Waffe" action; the Skirnir archetype's own variant, several other
abilities that spend from the same pool, and the pool's level-5 special-
ability unlock are not yet implemented, see that id's own docstring), and
the Kampfmagus root class's own "Kampfzauberei" (Spell Combat,
`KAMPFZAUBEREI_ABILITY_ID` below — its flat -2 melee-attack-roll toggle
only; see that id's own docstring for what's not modeled yet).
"Vermindertes Zauberwirken" now has a real schema hook (`spells_per_day`)
to adjust (`import_kampfmagus_archetypes.py`'s docstring flagged this
ability as "no schema hook to replace" at the time it was seeded, back when
this app had no spell-slot-per-day tracking at all for any prepared caster
— `rules/spells.py`'s `spells_per_day`/`total_spell_slots` is that hook
now).

Identical rule text, independently granted at 1st level, for all four
archetypes: "Ein {Archetyp} besitzt pro Zaubergrad einen Zauberplatz
weniger. Sollte dies die tägliche Anzahl der verfügbaren Zauber eines
Grades auf 0 reduzieren, kann er nur dann Zauber dieses Grades wirken, wenn
er Bonuszauber aufgrund seiner Intelligenz für diesen Grad erhält." — one
fewer spell slot per grade (floored at 0, never negative), applied to the
base class-table value *before* the ability-modifier bonus is added; the
bonus itself is untouched, which is exactly what "kann ... wirken, wenn er
Bonuszauber ... erhält" describes (a reduced-to-0 base grade can still be
cast if the bonus alone grants a slot there)."""

from collections.abc import Callable
from uuid import UUID

from ..context import CharacterContext
from ..modifiers import Modifier, ModifierTarget
from ..progression import ability_mod

# Kampfmagus's own root `BaseClass` id (`base_classes.json`) — Kensai is one
# of its archetypes, not a separately leveled class, so a Kensai's levels
# are counted here the same way any other Kampfmagus's are
# (`context.level_counts_by_root_id`).
KAMPFMAGUS_ROOT_CLASS_ID = UUID("cebfc2a3-02fc-561a-8467-7f88ba567b01")

# Ability ids from `base_class_ability_grants.json` (one per archetype,
# level 1) — same ids `import_kampfmagus_archetypes.py` seeded.
SPELL_SLOT_DELTA: dict[UUID, int] = {
    UUID("c7790b93-5d98-50f8-b796-b3b282a44cdd"): -1,  # Kensai
    UUID("e2b15d6b-5804-5814-a4e9-38618a953645"): -1,  # Seelenschmied
    UUID("f98136ce-2c0e-5a96-8515-9af3689442df"): -1,  # Skirnir
    UUID("5e2c5e9e-1915-556d-a902-3aee007af2d7"): -1,  # Zauberstreiter
}

# Kensai's own "Umgang mit Waffen und Rüstungen (Kensai)" (2026-08-25) —
# `BaseClassAbility.requires_weapon_choice` is set on this row; the
# character's actual pick is persisted against this ability's id in
# `CharacterClassAbilityWeaponChoice`, read by `sheet.py`/`rules/proficiency.py`
# to grant proficiency for exactly that weapon.
KENSAI_WEAPON_CHOICE_ABILITY_ID = UUID("1022bc94-7324-5fb0-883a-ed80726277e0")

# Kensai's separate "Waffenfokus (Kensai)" class ability (level 1, PRD:
# "Mit Beginn der 1. Stufe erhält ein Kensai Waffenfokus mit seiner
# ausgewählten Waffe.") — grants Weapon Focus's +1 attack bonus
# (`rules/feats.py`'s `WAFFENFOKUS_ATTACK_BONUS`) for the *same* weapon
# chosen under `KENSAI_WEAPON_CHOICE_ABILITY_ID` above, entirely for free
# (no feat spent). A hand-frozen pairing between the two ability ids, same
# one-off convention as `rules/traits.py`'s `GEWITZTES_WORTSPIEL` — not
# worth a generic "which ability's choice do I reuse" schema field for the
# one class that currently needs it. `sheet.py`'s `_build_weapon_attacks`
# applies this alongside a player's own ordinary Waffenfokus pick, not as a
# parallel one-off.
KENSAI_WEAPON_FOCUS_ABILITY_ID = UUID("5ddd070b-8770-54bd-ba62-6788374554ce")

# Kampfmagus root class's own "Kampfzauberei" (Spell Combat), level 1
# (`base_class_abilities.json` id 8431426f-...). PRD: "Mit einer Vollen
# Aktion kann er alle Angriffe mit der Nahkampfwaffe mit einem Malus von -2
# ausführen und zugleich jeden Zauber von der Zauberliste des Kampfmagus
# wirken..." — flagged `is_persistent_effect`/`activation_scope: "self"`/
# `default_duration_rounds: 1` (same per-round-toggle shape as Heftiger
# Angriff, `rules/feats.py`'s `HEFTIGER_ANGRIFF`) so a player activates it
# via `POST .../effects` for the current round. `sheet.py`'s
# `_build_weapon_attacks` reads the toggle directly off `context.active_effects`
# (`_kampfzauberei_attack_penalty` there), the same "own-state toggle"
# pattern `_power_attack_effect` already uses — not a `HANDLERS` entry, since
# it's melee-weapon-attack-only, not a flat `Modifier`.
#
# Not modeled yet: the "one hand free, light/one-handed weapon in the
# other" precondition (no action-legality filtering exists anywhere else
# either, see `sheet.py`'s `_build_actions` docstring); the actual spell
# cast alongside it (no in-app spellcasting/dice-rolling exists at all,
# `rules/weapon_abilities.py`'s module docstring); the defensive-casting
# extra self-imposed malus/concentration bonus trade-off; and the level-8/14
# "Verbesserte/Mächtige Kampfzauberei" concentration bonuses (their own
# unimplemented `base_class_abilities.json` rows, ids f0bbb318-.../98bc15b7-...).
KAMPFZAUBEREI_ABILITY_ID = UUID("8431426f-761f-5fc8-bd01-63b369edce97")

# All three ids above have a real, computed effect — `sheet.py`'s
# `_build_weapon_attacks` reads them directly (`chosen_weapon_ids`/
# `weapon_focus_weapon_ids`/`_kampfzauberei_attack_penalty`'s own
# `context.active_effects` check) — but none is a `HANDLERS`/
# `NATURAL_ATTACK_HANDLERS`/`WEAPON_BONUS_DAMAGE_HANDLERS` entry: a weapon
# *choice* isn't a `Modifier` at all, the free Weapon Focus grant is the
# same per-weapon-slot decision `rules/feats.py`'s `WAFFENFOKUS`/
# `COMPUTED_OUTSIDE_HANDLERS_FEAT_IDS` documents for the player-picked
# version of the same feat, and Kampfzauberei's toggle needs to gate only
# melee (not ranged) weapons the same way `_power_attack_effect` already
# does for Heftiger Angriff (also not a `HANDLERS` entry, for the same
# reason). Merged into `rules/handlers.py`'s `has_mechanical_effect` (via
# `rules/classes/__init__.py`'s `APPLIED_OUTSIDE_HANDLERS_IDS`) so the
# sheet's "Nur Text" badge doesn't mislabel any of the three as flavor-only
# merely for not being a typed registry entry.
APPLIED_OUTSIDE_HANDLERS_IDS = frozenset(
    {KENSAI_WEAPON_CHOICE_ABILITY_ID, KENSAI_WEAPON_FOCUS_ABILITY_ID, KAMPFZAUBEREI_ABILITY_ID}
)

# "Gewitzte Verteidigung" (Canny Defense), level 1, PRD: "Wenn ein Kensai
# keine, oder eine leichte Rüstung trägt und keinen Schild verwendet, darf
# er pro Klassenstufe einen Punkt seines Intelligenz-Modifikators (falls
# vorhanden) auf seinen Geschicklichkeitsbonus für seine RK als
# Ausweichbonus addieren, wenn er seine ausgewählte Waffe führt." Identical
# text/mechanic to the (not-yet-a-real-`BaseClass`) Duellant prestige
# class's own version, `base_class_abilities.json` row b35b567e-...
GEWITZTE_VERTEIDIGUNG_KENSAI_ABILITY_ID = UUID("ebb8db2d-2caa-54c4-8a78-9131f0b44e1d")


def _gewitzte_verteidigung_kensai(context: CharacterContext) -> list[Modifier]:
    """"Pro Klassenstufe einen Punkt seines Intelligenz-Modifikators" is a
    cap that unlocks gradually, not a per-level multiplier: the bonus is
    `min(class level, Int mod)` — a 1st-level Kensai only ever gets +1
    towards AC regardless of how high the Int mod is, reaching the full Int
    mod only once class level >= Int mod. (Confirmed against the real rule
    text 2026-08-26 after a first pass mis-multiplied the two instead of
    capping — a level-1 Kensai with a +3 Int mod got +3, not the correct
    +1.)

    The "no/light armor, no shield" gate is real
    (`CharacterContext.equipped_armor_weight_class`/`has_shield_equipped`,
    added for exactly this ability). "Wenn er seine ausgewählte Waffe
    führt" (only while wielding the kensai's chosen weapon) is also real,
    via `kensai_chosen_weapon_id`/`equipped_weapon_ids` (2026-08-26,
    likewise added for this ability) — no chosen weapon yet, or the chosen
    weapon isn't in either weapon slot right now, and the bonus doesn't
    apply, matching a fresh Kensai who hasn't made the weapon choice yet.
    "Falls vorhanden" (only if the Int mod is actually positive) — a zero
    or negative Int mod grants no bonus, never a penalty."""
    if context.has_shield_equipped or context.equipped_armor_weight_class not in (None, "light"):
        return []
    if context.kensai_chosen_weapon_id is None or context.kensai_chosen_weapon_id not in context.equipped_weapon_ids:
        return []
    int_mod = ability_mod(context.ability_scores.get("IN", 10))
    if int_mod <= 0:
        return []
    kampfmagus_level = context.level_counts_by_root_id.get(KAMPFMAGUS_ROOT_CLASS_ID, 0)
    bonus = min(int_mod, kampfmagus_level)
    if bonus <= 0:
        return []
    return [Modifier(source="Gewitzte Verteidigung", type="dodge", value=bonus, target=ModifierTarget.AC)]


# Kampfmagus's own "Arkaner Vorrat" (Arcane Reservoir), level 1
# (`base_class_abilities.json` id 571a2783-…). A shared point pool
# (`_arkaner_vorrat_pool_points`, `DAILY_LIMITS` below) that several other
# class abilities (Zauberrückruf, Wissensvorrat, Kensai's Perfekter Schlag,
# ...) spend against by discrete amounts — none of those consumers are
# implemented yet, only the pool itself and its own headline action ("Waffe
# verbessern", below).
#
# That headline action is a *duration* effect (RAW: "für eine Minute"), not
# an instant one, but its own pool cost is a flat, always-1-point debit paid
# once at activation — structurally different from Kampfrausch (this
# module's only other DAILY_LIMITS precedent), whose "rounds/day" pool *is*
# its own active duration, drained automatically one unit per round ticked
# (`routers/characters.py`'s `advance_time`). Arkaner Vorrat's pool has no
# such 1:1 relationship to the resulting effect's `duration_remaining` (a
# 10-round buff still only ever costs 1 point, not 10) — `POOL_COST_AT_ACTIVATION`
# below is what tells `activate_effect`/`advance_time` apart: the pool is
# charged once, up front, and the effect's own countdown afterwards no
# longer touches it.
ARKANER_VORRAT_ABILITY_ID = UUID("571a2783-adb7-5222-8040-a1c4d40b4b0c")


def _arkaner_vorrat_pool_points(context: CharacterContext) -> int:
    """"Eine Anzahl an Punkten in Höhe seiner halben Stufe als Kampfmagus
    (Minimum 1) + seines IN-Modifikators" — the "Minimum 1" floors the
    halved-level term specifically (a 1st-level Kampfmagus already has a
    1-point pool before any Int bonus), not the sum as a whole."""
    kampfmagus_level = context.level_counts_by_root_id.get(KAMPFMAGUS_ROOT_CLASS_ID, 0)
    int_mod = ability_mod(context.ability_scores.get("IN", 10))
    return max(1, kampfmagus_level // 2) + int_mod


def _arkaner_vorrat_weapon_enhancement(context: CharacterContext) -> tuple[UUID, int] | None:
    """The enhancement bonus granted to whichever `BaseItem` is named by
    the active effect's own `target_item_id` (set at activation,
    `routers/characters.py`'s `activate_effect` — see that field's own
    docstring on `models.effect.CharacterEffect` for why it's an item id,
    not the owning `CharacterGear` row's own id) — `None` while the effect
    isn't active at all, or (defensively) if it's active with no target
    chosen. Unlike the pool's flat 1-point cost, the bonus *size* is purely
    computed from Kampfmagus level, never player-chosen or stored on the
    effect row: "+1 auf der 1. Stufe... für jeweils 4 weitere Stufen (ab der
    5., 9. ...) ein weiterer +1, bis zu einem Maximum von +5 auf der 17.
    Stufe" is exactly `1 + (level - 1) // 4`, capped at 5.

    Combining this with a weapon's own permanent `CharacterGear.enhancement`
    (capped at the same +5 total, per RAW) is `sheet.py`'s job — this
    handler only knows the character's own level, not any specific weapon's
    existing bonus, so it returns the nominal, uncapped-against-gear value."""
    effect = next(
        (e for e in context.active_effects if e.source_id == ARKANER_VORRAT_ABILITY_ID and e.target_item_id is not None),
        None,
    )
    if effect is None:
        return None
    kampfmagus_level = context.level_counts_by_root_id.get(KAMPFMAGUS_ROOT_CLASS_ID, 0)
    bonus = min(5, 1 + max(0, kampfmagus_level - 1) // 4)
    return (effect.target_item_id, bonus)


# Ability ids whose active `CharacterEffect` pays its own `DAILY_LIMITS`
# pool cost once, at activation (`routers/characters.py`'s `activate_effect`),
# rather than accruing it per round of active duration the way Kampfrausch's
# rounds/day does (`advance_time`) — see `ARKANER_VORRAT_ABILITY_ID`'s
# docstring above for why the two shapes need telling apart. The int is the
# flat number of pool points one activation costs.
POOL_COST_AT_ACTIVATION: dict[UUID, int] = {
    ARKANER_VORRAT_ABILITY_ID: 1,
}

# Display unit for a `DAILY_LIMITS` ability's "X von Y ... heute übrig"
# sheet text (`sheet.py`'s `_build_activatable_class_abilities`) — every
# `DAILY_LIMITS` id before this one happened to be a rounds/day pool
# (Kampfrausch), which is why that string used to hardcode "Runden";
# Arkaner Vorrat's pool is points, not rounds.
DAILY_LIMIT_UNIT_LABEL: dict[UUID, str] = {
    ARKANER_VORRAT_ABILITY_ID: "Punkten",
}


HANDLERS: dict[UUID, Callable[[CharacterContext], list[Modifier]]] = {
    GEWITZTE_VERTEIDIGUNG_KENSAI_ABILITY_ID: _gewitzte_verteidigung_kensai,
}

# This class's slice of `rules/handlers.py`'s merged `DAILY_LIMITS`.
DAILY_LIMITS: dict[UUID, Callable[[CharacterContext], int]] = {
    ARKANER_VORRAT_ABILITY_ID: _arkaner_vorrat_pool_points,
}

# This class's slice of `rules/handlers.py`'s merged `WEAPON_ENHANCEMENT_HANDLERS`
# — an ability id's currently active temporary enhancement bonus on one
# specific `CharacterGear` row, or `None` if not currently active.
WEAPON_ENHANCEMENT_HANDLERS: dict[UUID, Callable[[CharacterContext], tuple[UUID, int] | None]] = {
    ARKANER_VORRAT_ABILITY_ID: _arkaner_vorrat_weapon_enhancement,
}
