"""Builds `base_spell_components.json` rows from the raw PRD `Komponenten:`
strings in `zauber_prd_details.json` (`fetch_zauber_prd_details.py` kept them
as raw text on purpose — see that script's docstring; this is the follow-up
build step it and `build_spells_seed.py` both point to).

`BaseSpellComponent` is keyed by `(spell_id, tradition)`, so one raw string
can produce an arcane and a divine row that differ:

- `M/GF (...)` (also `M / GF`): arcane needs the Material component (the
  parenthesised text is its description), divine only needs the Göttlicher
  Fokus.
- `F/GF (...)`: same split, with Fokus instead of Material.
- plain `GF`: every tradition that casts the spell needs it.
- `V`, `G`, `M`, `F` apply to every tradition.

Göttlicher Fokus is stored as `focus=True` with `focus_description`
"Göttlicher Fokus" (joined with `; ` onto a real Fokus' own description if
the spell has both), since the table has no separate divine-focus flag; the
sheet's `_spell_components_payload` therefore exposes a plain one as a
separate `divineFocus` flag (GF/DF per UI language).

Which traditions a spell has comes from the classes that cast it
(`base_class_spells.json` + `base_classes.json`'s `spell_tradition`).

Deliberately not guessed (reported at the end, no row written): alternatives
("V oder G"), a stat-block field that isn't a component list at all
("1 Standard-Aktion"), spells on no class's list, and any (spell, tradition)
pair the hand-curated seed already has (kept as is, e.g. its "Heiliges
Symbol" divine focus). Parenthesised "siehe Text"-style tails and "nur
Barden"-style notes on V/G are dropped; descriptions longer than the 255-char
column are truncated with "...".

Spells are matched to the PRD detail rows by id, falling back to an
unambiguous name match for the early hand-seeded ones.

Merges into `base_spell_components.json` by id (`uuid5`, stable across
runs), so re-running is idempotent.

Usage (from backend/scripts):
    python build_spell_components_seed.py
"""

from __future__ import annotations

import json
import re
import uuid
from collections import defaultdict
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
SEED_DIR = BACKEND / "app" / "fixtures" / "seed"
DETAILS_PATH = BACKEND / "app" / "fixtures" / "imported" / "zauber_prd_details.json"
SEED_PATH = SEED_DIR / "base_spell_components.json"

NAMESPACE = uuid.UUID("3d8a6c1e-52f7-4b9a-8e14-7c0d9a5b2f63")
DIVINE_FOCUS = "Göttlicher Fokus"
MAX_DESCRIPTION = 255

TOKEN_RE = re.compile(r"^(?P<code>[A-Za-z/ ]+?)\s*(?P<rest>\(.*)?$", re.DOTALL)
VALID_CODES = {"V", "G", "M", "F", "GF", "M/GF", "F/GF"}


def split_top_level(raw: str) -> list[str]:
    parts, current, depth = [], "", 0
    for char in raw:
        depth += char == "("
        depth -= char == ")"
        if char == "," and depth == 0:
            parts.append(current.strip())
            current = ""
        else:
            current += char
    parts.append(current.strip())
    return [p for p in parts if p]


def first_group(rest: str | None) -> str | None:
    """Contents of the first balanced "(...)" group (a few PRD strings have a
    second "(siehe Text)" group after it, or an unclosed one)."""
    if not rest:
        return None
    depth, start = 0, None
    for i, char in enumerate(rest):
        if char == "(":
            if depth == 0:
                start = i + 1
            depth += 1
        elif char == ")":
            depth -= 1
            if depth == 0 and start is not None:
                return rest[start:i].strip() or None
    return rest[1:].strip() or None  # unclosed group (e.g. "Benommenheit")


def parse(raw: str) -> list[tuple[str, str | None]] | None:
    """[(code, description)] or None if the string isn't a plain component
    list."""
    raw = re.sub(r"\.\s*m\b", ", M", raw)  # "G. m (ein Dorn)" typo
    tokens = []
    for part in split_top_level(raw):
        if re.fullmatch(r"siehe Text", part, re.IGNORECASE):
            continue
        match = TOKEN_RE.match(part)
        if match is None:
            return None
        code = match.group("code").replace(" ", "").upper()
        if code not in VALID_CODES:
            return None
        tokens.append((code, first_group(match.group("rest"))))
    return tokens or None


def clip(text: str | None) -> str | None:
    if text is None or len(text) <= MAX_DESCRIPTION:
        return text
    return text[: MAX_DESCRIPTION - 3] + "..."


def build_row(spell_id: str, tradition: str, tokens: list[tuple[str, str | None]]) -> dict:
    verbal = somatic = material = focus = False
    material_description = None
    focus_descriptions: list[str] = []
    for code, description in tokens:
        if code == "V":
            verbal = True
        elif code == "G":
            somatic = True
        elif code == "M" or (code == "M/GF" and tradition == "arcane"):
            material, material_description = True, description
        elif code == "F" or (code == "F/GF" and tradition == "arcane"):
            focus = True
            if description:
                focus_descriptions.append(description)
        else:  # GF, or the divine half of M/GF / F/GF
            focus = True
            focus_descriptions.append(DIVINE_FOCUS)
    return {
        "id": str(uuid.uuid5(NAMESPACE, f"spell-component-{spell_id}-{tradition}")),
        "spell_id": spell_id,
        "tradition": tradition,
        "verbal": verbal,
        "somatic": somatic,
        "material": material,
        "material_description": clip(material_description),
        "focus": focus,
        "focus_description": clip("; ".join(focus_descriptions)) if focus_descriptions else None,
    }


def main() -> None:
    spells = json.loads((SEED_DIR / "base_spells.json").read_text(encoding="utf-8"))
    classes = json.loads((SEED_DIR / "base_classes.json").read_text(encoding="utf-8"))
    class_spells = json.loads((SEED_DIR / "base_class_spells.json").read_text(encoding="utf-8"))
    detail_rows = json.loads(DETAILS_PATH.read_text(encoding="utf-8"))
    details = {d["id"]: d for d in detail_rows}
    # The ~100 hand-seeded early spells carry different ids than the PRD
    # import's; fall back to an unambiguous name match for those.
    details_by_name: dict[str, list[dict]] = defaultdict(list)
    for d in detail_rows:
        details_by_name[d["name"]].append(d)
    existing = json.loads(SEED_PATH.read_text(encoding="utf-8"))

    tradition_by_class = {c["id"]: c["spell_tradition"] for c in classes if c.get("spell_tradition")}
    traditions_by_spell: dict[str, set[str]] = defaultdict(set)
    for row in class_spells:
        tradition = tradition_by_class.get(row["base_class_id"])
        if tradition:
            traditions_by_spell[row["spell_id"]].add(tradition)

    taken = {(row["spell_id"], row["tradition"]) for row in existing if not is_generated(row)}
    new_rows: list[dict] = []
    skipped: dict[str, list[str]] = defaultdict(list)
    for spell in spells:
        detail = details.get(spell["id"])
        if detail is None and len(details_by_name.get(spell["name"], [])) == 1:
            detail = details_by_name[spell["name"]][0]
        raw = (detail or {}).get("components")
        if not raw:
            skipped["no raw component text"].append(spell["name"])
            continue
        tokens = parse(raw)
        if tokens is None:
            skipped["unparseable"].append(f"{spell['name']} ({raw})")
            continue
        traditions = traditions_by_spell.get(spell["id"])
        if not traditions:
            skipped["on no class list"].append(spell["name"])
            continue
        for tradition in sorted(traditions):
            if (spell["id"], tradition) in taken:
                skipped["hand-curated row kept"].append(f"{spell['name']} ({tradition})")
                continue
            new_rows.append(build_row(spell["id"], tradition, tokens))

    by_id = {row["id"]: row for row in existing}
    for row in new_rows:
        by_id[row["id"]] = row
    SEED_PATH.write_text(json.dumps(list(by_id.values()), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"Wrote {len(new_rows)} generated rows; {SEED_PATH.name} now has {len(by_id)} rows.")
    for reason, names in skipped.items():
        shown = ", ".join(names[:8]) + (" ..." if len(names) > 8 else "")
        print(f"- {reason}: {len(names)}  [{shown}]")


def is_generated(row: dict) -> bool:
    return row["id"] == str(uuid.uuid5(NAMESPACE, f"spell-component-{row['spell_id']}-{row['tradition']}"))


if __name__ == "__main__":
    main()
