"""Turns the PRD spell import (`zauber_prd_import.json`'s per-class grades +
`zauber_prd_details.json`'s Grundregelwerk stat blocks) into DB-shaped seed
data for `base_spells`/`base_class_spells`, scoped to Grundregelwerk spells
accessible to at least one of the 8 classes currently modeled with a
`spell_tradition` (Barde, Druide, Hexenmeister, Kleriker, Magier, Mystiker,
Waldläufer, Hexe) — same "only currently relevant" scoping call as
`build_feats_seed.py`'s race/class-mention filter. Of 623 fetched
Grundregelwerk spells, 3 (Heiliges Schwert, Reittier heilen, Waffe weihen)
are Paladin-only and dropped, since Paladin has no `spell_tradition` yet.

Reconciles against the 103 already hand-seeded `base_spells.json` rows so
existing ids (and any `character_spells`/`base_class_spells` rows pointing
at them) stay stable: 88 match the PRD's canonical name exactly; 3 more use
a non-canonical translation (`RECONCILE_BY_NAME`, found by comparing
descriptions — e.g. "Command"'s old blurb, "Zwingt einem Ziel für eine Runde
ein einzelnes Wort-Kommando auf.", is unmistakably the PRD's "Befehl"). The
other 12 existing spells (Kleiner Trick, Widerstand, Reinigen, Farbenstrahl,
Sprung, "Unsichtbare Hand: Diener", Beschwichtigen, Verzaubern, Tarnung,
Furchtlosigkeit, Heiliger Schild, Waffensegen) have no confident PRD match
and are left untouched rather than guessed at — **note "Reinigen" in
particular looks mislabeled**: its existing description ("Gibt eine leise
Ahnung, wie eine bevorstehende Aufgabe zu meistern ist.") is Guidance's
effect, not Purify Food and Drink's, but that's a pre-existing data issue,
not something this script's reconciliation should silently paper over by
merging it into the wrong PRD spell.

Every reconciled/new spell's `school` is overwritten with the PRD's own
term, which incidentally fixes some pre-existing inconsistency in the hand
seed (e.g. "Bannmagie" vs "Bannzauber", "Weissagung" vs "Erkenntnis" both
used for the same school across different rows).

Component text (`Komponenten:`) is deliberately NOT turned into
`BaseSpellComponent` rows here — that table is keyed by (spell_id,
tradition) because arcane/divine versions of a cross-list spell can need
different components (e.g. "M/GF (eine Wasserfläche)" is arcane-Material vs
divine-Divine-Focus), which needs slash-group parsing plus a tradition
lookup per class; left for a follow-up pass rather than rushed into this one.

Usage (from backend/scripts, project venv active):
    python build_spells_seed.py
"""

from __future__ import annotations

import json
import re
import uuid
from pathlib import Path

SEED_DIR = Path(__file__).resolve().parent.parent / "app" / "fixtures" / "seed"
IMPORTED_DIR = Path(__file__).resolve().parent.parent / "app" / "fixtures" / "imported"

RELEVANT_CLASS_NAMES = ["Barde", "Druide", "Hexenmeister", "Kleriker", "Magier", "Mystiker", "Waldläufer", "Hexe"]

# Old hand-seeded name -> PRD canonical name, confirmed by matching
# description content (see module docstring).
RECONCILE_BY_NAME = {
    "Person betören": "Person bezaubern",
    "Command": "Befehl",
    "Wunden heilen, leicht": "Leichte Wunden heilen",
}

# One-off PRD site typo (1 occurrence, vs. 49 for the correct spelling) —
# not worth a general normalization pass, just this single known case.
SCHOOL_ALIASES = {"Erkenntniszauber": "Erkenntnis"}

SCHOOL_PREFIX_RE = re.compile(r"[\(\[]")

# Deterministic namespace for base_class_spells row ids not already present
# in the existing seed, so reruns upsert instead of duplicating (same
# _stable_id trick as build_feats_seed.py's ID_NAMESPACE).
CLASS_SPELL_NAMESPACE = uuid.UUID("f1b3c9d4-8e2a-4c6b-9f3d-2a7e5c9b1d4f")


def _load(filename: str, directory: Path) -> list[dict]:
    return json.loads((directory / filename).read_text(encoding="utf-8"))


def _dump(filename: str, rows: list[dict]) -> None:
    (SEED_DIR / filename).write_text(json.dumps(rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def primary_school(school_text: str | None) -> str:
    if not school_text:
        return ""
    name = SCHOOL_PREFIX_RE.split(school_text)[0].strip()
    return SCHOOL_ALIASES.get(name, name)


def main() -> None:
    imported = _load("zauber_prd_import.json", IMPORTED_DIR)
    details = _load("zauber_prd_details.json", IMPORTED_DIR)

    import_by_id: dict[str, dict] = {}
    for row in imported:
        import_by_id.setdefault(row["id"], row)

    classes = _load("base_classes.json", SEED_DIR)
    class_id_by_name = {c["name"]: c["id"] for c in classes if c["name"] in RELEVANT_CLASS_NAMES}

    existing_spells = _load("base_spells.json", SEED_DIR)
    existing_by_id = {s["id"]: s for s in existing_spells}
    existing_by_name = {s["name"]: s for s in existing_spells}
    reconcile_target_to_old = {v: k for k, v in RECONCILE_BY_NAME.items()}

    existing_class_spells = _load("base_class_spells.json", SEED_DIR)
    class_spells_by_key: dict[tuple[str, str], dict] = {
        (row["base_class_id"], row["spell_id"]): row for row in existing_class_spells
    }

    final_spells_by_id: dict[str, dict] = dict(existing_by_id)
    touched_ids: set[str] = set()

    included = 0
    excluded_no_relevant_class = []
    grade_mismatches = []

    for detail in details:
        imp = import_by_id.get(detail["id"])
        if imp is None:
            continue
        grades = {name: grade for name, grade in imp["grades_by_class"].items() if name in class_id_by_name}
        if not grades:
            excluded_no_relevant_class.append(detail["name"])
            continue

        name = detail["name"]
        if name in existing_by_name:
            spell_id = existing_by_name[name]["id"]
        elif name in reconcile_target_to_old:
            spell_id = existing_by_name[reconcile_target_to_old[name]]["id"]
        else:
            spell_id = detail["id"]

        old_row = existing_by_id.get(spell_id)
        spell_row = {
            "id": spell_id,
            "name": name,
            "school": primary_school(detail.get("school_text")),
            "description": detail["full_description"],
            "casting_time": detail.get("casting_time"),
            "range": detail.get("range"),
            "target_or_area": detail.get("target_or_area"),
            "duration": detail.get("duration"),
            "saving_throw": detail.get("saving_throw"),
            "spell_resistance": detail.get("spell_resistance"),
        }
        if old_row is not None and old_row.get("is_persistent_effect"):
            spell_row["is_persistent_effect"] = True
        final_spells_by_id[spell_id] = spell_row
        touched_ids.add(spell_id)
        included += 1

        for class_name, grade in grades.items():
            base_class_id = class_id_by_name[class_name]
            key = (base_class_id, spell_id)
            existing_row = class_spells_by_key.get(key)
            if existing_row is not None:
                if existing_row["grade"] != grade:
                    grade_mismatches.append((name, class_name, existing_row["grade"], grade))
                row_id = existing_row["id"]
            else:
                row_id = str(uuid.uuid5(CLASS_SPELL_NAMESPACE, f"{base_class_id}|{spell_id}"))
            class_spells_by_key[key] = {"id": row_id, "base_class_id": base_class_id, "spell_id": spell_id, "grade": grade}

    class_name_by_id = {v: k for k, v in class_id_by_name.items()}
    final_spells = sorted(final_spells_by_id.values(), key=lambda s: s["name"])
    final_class_spells = sorted(
        class_spells_by_key.values(),
        key=lambda r: (class_name_by_id.get(r["base_class_id"], r["base_class_id"]), r["grade"]),
    )

    _dump("base_spells.json", final_spells)
    _dump("base_class_spells.json", final_class_spells)

    untouched_legacy = len(existing_by_id) - len(touched_ids & existing_by_id.keys())
    print(f"base_spells: {len(final_spells)} ({included} from PRD, {untouched_legacy} untouched legacy)")
    print(f"base_class_spells: {len(final_class_spells)}")
    print(f"excluded (no relevant-class grade): {len(excluded_no_relevant_class)} -> {excluded_no_relevant_class}")
    if grade_mismatches:
        print(f"grade mismatches vs. existing seed ({len(grade_mismatches)}), PRD value used:")
        for name, class_name, old_grade, new_grade in grade_mismatches:
            print(f"  {name!r} / {class_name}: {old_grade} -> {new_grade}")


if __name__ == "__main__":
    main()
