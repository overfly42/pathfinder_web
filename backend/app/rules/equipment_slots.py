"""The character sheet's paperdoll layout — pure UI layout data (key/label/
side/row), not rule content, same class as `sheet.py`'s `ABILITY_LABELS`/
`SAVE_LABELS`. The 14 wondrous-item slots are copied from the original mock
fixtures (`character_1.json`) so the frontend's existing `EquipmentSlots`
component needs no changes to its slot keys; "schild" (shield) is new here —
the original mocks never modeled a shield slot at all — appended as its own
row (the paperdoll grid has no fixed row count, see `CharacterSheetPage.css`
`.paperdoll`).

`SLOT_CATEGORY` is slot key -> the `BaseItem.category` that fits it. Armor
("ruestung") and shield ("schild") were roadmap slice 4's real-mechanical-
effect subset (`BaseItem.ac_bonus`, see `rules/modifiers.py`); the other 12
slots map to category "wondrous", except the two ring slots, which map to
"ring" (roadmap.md's "Wondrous-Item-Katalog mit echter Attributsboni-
Wirkung", decided 2026-08-04).

`SLOT_TO_ITEM_SLOT` is slot key -> the `BaseItem.slot` value a candidate
item must carry — needed because several paperdoll slots share one category
("wondrous"), so category alone can't tell a Gürtel-item from a Hals-item;
both ring slots map to the single generic value "ring" since a ring catalog
row doesn't distinguish left/right (`routers/characters.py`'s `update_slot`
checks both dicts)."""

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

SLOT_CATEGORY = {
    "ruestung": "armor",
    "schild": "shield",
    "kopf": "wondrous",
    "stirnband": "wondrous",
    "augen": "wondrous",
    "hals": "wondrous",
    "schultern": "wondrous",
    "brust": "wondrous",
    "handgelenke": "wondrous",
    "koerper": "wondrous",
    "guertel": "wondrous",
    "haende": "wondrous",
    "fuesse": "wondrous",
    "ring-links": "ring",
    "ring-rechts": "ring",
}

# slot key -> the BaseItem.slot value a candidate item must carry (only
# checked for category "wondrous"/"ring" — armor/shield have no BaseItem.slot).
SLOT_TO_ITEM_SLOT = {
    "kopf": "kopf",
    "stirnband": "stirnband",
    "augen": "augen",
    "hals": "hals",
    "schultern": "schultern",
    "brust": "brust",
    "handgelenke": "handgelenke",
    "koerper": "koerper",
    "guertel": "guertel",
    "haende": "haende",
    "fuesse": "fuesse",
    "ring-links": "ring",
    "ring-rechts": "ring",
}
