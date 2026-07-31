"""The character sheet's paperdoll layout — pure UI layout data (key/label/
side/row), not rule content, same class as `sheet.py`'s `ABILITY_LABELS`/
`SAVE_LABELS`. The 14 wondrous-item slots are copied from the original mock
fixtures (`character_1.json`) so the frontend's existing `EquipmentSlots`
component needs no changes to its slot keys; "schild" (shield) is new here —
the original mocks never modeled a shield slot at all — appended as its own
row (the paperdoll grid has no fixed row count, see `CharacterSheetPage.css`
`.paperdoll`).

`SLOT_CATEGORY` is the roadmap slice 4 subset with a real mechanical effect:
only armor ("ruestung") and shield ("schild") have `BaseItem.ac_bonus` data
behind them today (see `rules/modifiers.py`). The other 12 slots (wondrous
items — rings, belts, amulets, ...) have no real catalog content yet (no
`BaseItem` rows exist for them), so they're listed for display only and
can't be equipped via the backend endpoints."""

SLOT_DEFINITIONS = [
    {"key": "kopf", "label": "Kopf", "side": "left", "row": 1},
    {"key": "stirnband", "label": "Stirnband", "side": "left", "row": 2},
    {"key": "augen", "label": "Augen", "side": "left", "row": 3},
    {"key": "hals", "label": "Hals", "side": "left", "row": 4},
    {"key": "schultern", "label": "Schultern", "side": "left", "row": 5},
    {"key": "brust", "label": "Brust", "side": "left", "row": 6},
    {"key": "handgelenke", "label": "Handgelenke", "side": "left", "row": 7},
    {"key": "koerper", "label": "Körper", "side": "right", "row": 1},
    {"key": "ruestung", "label": "Rüstung", "side": "right", "row": 2},
    {"key": "guertel", "label": "Gürtel", "side": "right", "row": 3},
    {"key": "ring-links", "label": "Ring (links)", "side": "right", "row": 4},
    {"key": "ring-rechts", "label": "Ring (rechts)", "side": "right", "row": 5},
    {"key": "haende", "label": "Hände", "side": "right", "row": 6},
    {"key": "fuesse", "label": "Füße", "side": "right", "row": 7},
    {"key": "schild", "label": "Schild", "side": "right", "row": 8},
]

# slot key -> the BaseItem.category that fits it.
SLOT_CATEGORY = {
    "ruestung": "armor",
    "schild": "shield",
}
