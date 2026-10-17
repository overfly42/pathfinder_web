"""Add the "Magisches Erbe" feat (Eldritch Heritage) from
http://prd.5footstep.de/AusbauregelnMagie/Talente/MagischesErbe to
`base_feats.json` and its `BaseFeatRequired*` prerequisite rows.

`build_feats_seed.py` left it out (it only takes Grundregelwerk feats plus
other-sourcebook feats whose prerequisite names a seeded race/class), but
the bulk PRD import already has it — its id is reused from
`imported/talente_prd_import.json` (prd_id 5578), the same id
`build_feats_seed.py` would have given it, so a later rerun of that script
over a wider scope can't mint a duplicate.

Prerequisites: "CH 13, Fertigkeitsfokus mit der Klassenfertigkeit der mit
diesem Talent gewählten Blutlinie, Charakterstufe 3+". Only CH 13 and
Fertigkeitsfokus (any skill) are recorded — no requirement table models a
minimum character level, nor a Fertigkeitsfokus tied to the skill of a
bloodline picked by this very feat. Under-enforced rather than guessed,
same rule as `build_feats_seed.py`. The feat's effect (pick a Hexenmeister
bloodline, gain its 1st-level bloodline power at Hexenmeister level =
character level - 2) has no handler yet — description-only for now.

Run with the project venv active (this only writes the fixture JSON files,
it doesn't touch the database — run the seed script afterward):
    cd backend && python scripts/import_feat_magisches_erbe.py
    python -m app.seed.feat_seed
"""

from __future__ import annotations

import json
import uuid
from pathlib import Path

SEED_DIR = Path(__file__).resolve().parent.parent / "app" / "fixtures" / "seed"

ID_NAMESPACE = uuid.UUID("a4c7e2d9-6b1f-4f3a-8e5c-2d9b7a1c4e60")

MAGISCHES_ERBE_FEAT_ID = "278d994a-4035-5dc4-a030-fc9f5e656ed5"
FERTIGKEITSFOKUS_FEAT_ID = "4a9d8e09-9aa5-44d0-b34e-f23ec5491fed"

FEAT = {
    "id": MAGISCHES_ERBE_FEAT_ID,
    "name": "Magisches Erbe",
    "description": "Du entstammst einer langen Reihe von Hexenmeistern und ein Teil ihrer Macht fließt in "
    "deinen Adern. Wähle eine Hexenmeisterblutlinie. Du musst das Talent Fertigkeitsfokus für die "
    "Klassenfertigkeit besitzen, welche diese Blutlinie einem Hexenmeister auf der 1. Stufe gibt "
    "(beispielsweise Heilkunde bei der Himmlischen Blutlinie). Du erhältst die Blutlinienkraft der 1. Stufe "
    "dieser Blutlinie. Hinsichtlich dieser Kraft entspricht deine effektive Stufe als Hexenmeister deiner "
    "Charakterstufe -2, selbst wenn du über Stufen als Hexenmeister verfügen solltest. Du erhältst keine "
    "anderen Blutlinienkräfte.",
    "type": "general",
    "prerequisite_text": "CH 13, Fertigkeitsfokus mit der Klassenfertigkeit der mit diesem Talent gewählten "
    "Blutlinie, Charakterstufe 3+.",
}


def uid(*parts: str) -> str:
    return str(uuid.uuid5(ID_NAMESPACE, "|".join(parts)))


def load(filename: str) -> list[dict]:
    return json.loads((SEED_DIR / filename).read_text(encoding="utf-8"))


def save(filename: str, rows: list[dict]) -> None:
    (SEED_DIR / filename).write_text(json.dumps(rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    feats = [f for f in load("base_feats.json") if f["id"] != MAGISCHES_ERBE_FEAT_ID]
    feats.append(FEAT)
    save("base_feats.json", feats)

    req_feats = [r for r in load("base_feat_required_feats.json") if r["feat_id"] != MAGISCHES_ERBE_FEAT_ID]
    req_feats.append(
        {
            "id": uid("req-feat", MAGISCHES_ERBE_FEAT_ID, FERTIGKEITSFOKUS_FEAT_ID),
            "feat_id": MAGISCHES_ERBE_FEAT_ID,
            "group_id": None,
            "required_feat_id": FERTIGKEITSFOKUS_FEAT_ID,
        }
    )
    save("base_feat_required_feats.json", req_feats)

    req_scores = [
        r for r in load("base_feat_required_ability_scores.json") if r["feat_id"] != MAGISCHES_ERBE_FEAT_ID
    ]
    req_scores.append(
        {
            "id": uid("req-ability-score", MAGISCHES_ERBE_FEAT_ID, "CH"),
            "feat_id": MAGISCHES_ERBE_FEAT_ID,
            "group_id": None,
            "ability": "CH",
            "minimum_score": 13,
        }
    )
    save("base_feat_required_ability_scores.json", req_scores)

    print("Magisches Erbe feat id:", MAGISCHES_ERBE_FEAT_ID)


if __name__ == "__main__":
    main()
