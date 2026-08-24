"""Kampfmagus (Magus) and its four archetypes (Kensai, Seelenschmied,
Skirnir, Zauberstreiter) — currently just each archetype's "Vermindertes
Zauberwirken" (Diminished Spellcasting), the one Kampfmagus-archetype
feature with a real mechanical hook now that `spells_per_day` exists to
adjust (`import_kampfmagus_archetypes.py`'s docstring flagged this ability
as "no schema hook to replace" at the time it was seeded, back when this
app had no spell-slot-per-day tracking at all for any prepared caster —
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
