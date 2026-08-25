"""Kampfmagus (Magus) and its four archetypes (Kensai, Seelenschmied,
Skirnir, Zauberstreiter) — each archetype's "Vermindertes Zauberwirken"
(Diminished Spellcasting, `SPELL_SLOT_DELTA` below) plus Kensai's own free
weapon choice (`KENSAI_WEAPON_CHOICE_ABILITY_ID`/`KENSAI_WEAPON_FOCUS_ABILITY_ID`),
the two Kampfmagus-archetype features with a real mechanical hook.
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

from uuid import UUID

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
