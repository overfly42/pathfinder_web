"""The three monster feats the PRD's "Tiertalente" list names but
`build_feats_seed.py` left out (it only takes Grundregelwerk feats plus
race/class-scoped ones) — roadmap slice 10 step 3. Fetched from
http://prd.5footstep.de/Monsterhandbuch/MonsterTalente/<Name>; ids reused
from `imported/talente_prd_import.json` (same as `import_feat_magisches_erbe.py`)
so a wider rerun of `build_feats_seed.py` can't mint duplicates.

- Mehrfachangriff (Kampf): secondary natural attacks at −2 instead of −5.
- Verbesserte Natürliche Rüstung: +1 natural armor, repeatable
  (`is_repeatable`, every pick adds up).
- Verbesserter Natürlicher Angriff: one natural attack's damage dice one
  size step up; repeatable for a *different* attack each time, so the
  attack is its sub-choice (`sub_choice_type` "natural_attack").

Only the ordinary prerequisites are rows (KO 13, GAB +4); "Natürliche
Rüstung", "Natürliche Waffe" and "Drei oder mehr natürliche Angriffe" are
checked by `rules/feats.py`'s `PREREQUISITE_CHECKS` against the creature's
natural armor/attacks.

Run with the project venv active (writes fixtures only; seed afterwards),
*before* `import_companion_species.py` — that script resolves the
"Tiertalente" names against `base_feats.json`:
    cd backend && python scripts/import_monster_feats.py
    python -m app.seed.feat_seed
"""

from __future__ import annotations

import json
import re
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from import_companion_species import fetch_text  # noqa: E402

SEED_DIR = Path(__file__).resolve().parent.parent / "app" / "fixtures" / "seed"
ID_NAMESPACE = uuid.UUID("b2d6f0a4-3c8e-4b1a-9f7d-5e2c8a0b6d14")
BASE_URL = "http://prd.5footstep.de/Monsterhandbuch/MonsterTalente/"

MEHRFACHANGRIFF_FEAT_ID = "b4b8c4c7-63eb-5a29-ba24-74298d785da5"
VERBESSERTE_NATUERLICHE_RUESTUNG_FEAT_ID = "14479bf3-1065-5cba-8384-bfed0ad35127"
VERBESSERTER_NATUERLICHER_ANGRIFF_FEAT_ID = "77e13c2b-c21d-5fcb-be2a-a5a54e930504"

# (id, page slug, type, sub_choice_type, is_repeatable)
FEATS = [
    (MEHRFACHANGRIFF_FEAT_ID, "Mehrfachangriff", "combat", None, False),
    (VERBESSERTE_NATUERLICHE_RUESTUNG_FEAT_ID, "VerbesserteNatuerlicheRuestung", "general", None, True),
    (VERBESSERTER_NATUERLICHER_ANGRIFF_FEAT_ID, "VerbesserterNatuerlicherAngriff", "general", "natural_attack", False),
]
ABILITY_SCORE_REQUIREMENTS = [(VERBESSERTE_NATUERLICHE_RUESTUNG_FEAT_ID, "KO", 13)]
BAB_REQUIREMENTS = [(VERBESSERTER_NATUERLICHER_ANGRIFF_FEAT_ID, 4)]


def uid(*parts: str) -> str:
    return str(uuid.uuid5(ID_NAMESPACE, "|".join(parts)))


def load(filename: str) -> list[dict]:
    return json.loads((SEED_DIR / filename).read_text(encoding="utf-8"))


def save(filename: str, rows: list[dict]) -> None:
    (SEED_DIR / filename).write_text(json.dumps(rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def parse_feat_page(text: str) -> tuple[str, str, str]:
    """(name, description, prerequisite text) of one feat page: the title
    line (minus a "(Kampf)" tag), then everything from the flavor line up
    to "Referenz:" as the description."""
    lines = text.split("\n")
    name = re.sub(r"\s*\(Kampf\)$", "", lines[0]).strip()
    body = [line for line in lines[1:] if not line.startswith("Referenz:")]
    prerequisite = next(line for line in body if line.startswith("Voraussetzungen:"))
    return name, "\n".join(body), prerequisite.removeprefix("Voraussetzungen:").strip()


def main() -> None:
    ids = {feat_id for feat_id, *_ in FEATS}
    feats = [f for f in load("base_feats.json") if f["id"] not in ids]
    for feat_id, slug, feat_type, sub_choice_type, is_repeatable in FEATS:
        name, description, prerequisite = parse_feat_page(fetch_text(BASE_URL + slug))
        feats.append(
            {
                "id": feat_id,
                "name": name,
                "description": description,
                "type": feat_type,
                "prerequisite_text": prerequisite,
                "sub_choice_type": sub_choice_type,
                "is_repeatable": is_repeatable,
            }
        )
        print(f"{name}: {prerequisite}")
    save("base_feats.json", feats)

    scores = [r for r in load("base_feat_required_ability_scores.json") if r["feat_id"] not in ids]
    for feat_id, ability, minimum in ABILITY_SCORE_REQUIREMENTS:
        scores.append(
            {
                "id": uid("req-ability-score", feat_id, ability),
                "feat_id": feat_id,
                "group_id": None,
                "ability": ability,
                "minimum_score": minimum,
            }
        )
    save("base_feat_required_ability_scores.json", scores)

    babs = [r for r in load("base_feat_required_babs.json") if r["feat_id"] not in ids]
    for feat_id, minimum in BAB_REQUIREMENTS:
        babs.append({"id": uid("req-bab", feat_id), "feat_id": feat_id, "group_id": None, "minimum_bab": minimum})
    save("base_feat_required_babs.json", babs)


if __name__ == "__main__":
    main()
