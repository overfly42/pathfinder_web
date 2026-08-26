"""Kampfmagus (Magus) and its four archetypes (Kensai, Seelenschmied,
Skirnir, Zauberstreiter) — each archetype's "Vermindertes Zauberwirken"
(Diminished Spellcasting, `SPELL_SLOT_DELTA` below), Kensai's own free
weapon choice (`KENSAI_WEAPON_CHOICE_ABILITY_ID`/`KENSAI_WEAPON_FOCUS_ABILITY_ID`),
and Kensai's "Gewitzte Verteidigung" (Canny Defense, `HANDLERS` below) — the
three Kampfmagus-archetype features with a real mechanical hook.
"Vermindertes Zauberwirken" now that `spells_per_day` exists to adjust
(`import_kampfmagus_archetypes.py`'s docstring flagged this ability as "no
schema hook to replace" at the time it was seeded, back when this app had no
spell-slot-per-day tracking at all for any prepared caster —
`rules/spells.py`'s `spells_per_day`/`total_spell_slots` is that hook now).

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

# Both of the two ids above have a real, computed effect — `sheet.py`'s
# `_build_weapon_attacks` reads them directly (`chosen_weapon_ids`/
# `weapon_focus_weapon_ids`) — but neither is a `HANDLERS`/`NATURAL_ATTACK_HANDLERS`/
# `WEAPON_BONUS_DAMAGE_HANDLERS` entry: a weapon *choice* isn't a `Modifier`
# at all, and the free Weapon Focus grant is the same per-weapon-slot
# decision `rules/feats.py`'s `WAFFENFOKUS`/`COMPUTED_OUTSIDE_HANDLERS_FEAT_IDS`
# documents for the player-picked version of the same feat. Merged into
# `rules/handlers.py`'s `has_mechanical_effect` (via `rules/classes/__init__.py`'s
# `APPLIED_OUTSIDE_HANDLERS_IDS`) so the sheet's "Nur Text" badge doesn't
# mislabel either as flavor-only merely for not being a typed registry entry.
APPLIED_OUTSIDE_HANDLERS_IDS = frozenset({KENSAI_WEAPON_CHOICE_ABILITY_ID, KENSAI_WEAPON_FOCUS_ABILITY_ID})

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


HANDLERS: dict[UUID, Callable[[CharacterContext], list[Modifier]]] = {
    GEWITZTE_VERTEIDIGUNG_KENSAI_ABILITY_ID: _gewitzte_verteidigung_kensai,
}
