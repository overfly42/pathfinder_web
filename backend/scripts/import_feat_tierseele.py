"""Add the "Tierseele" feat (Animal Soul) from
https://prd.5footstep.de/Ausbauregeln-VI-Klassen/Talente/Tierseele to
`base_feats.json` and its `BaseFeatRequiredClassAbility` prerequisite rows.

`build_feats_seed.py` left it out (Ausbauregeln VI, prerequisite names no
seeded race/class), but the bulk PRD import already has it — its id is
reused from `imported/talente_prd_import.json` (prd_id 13922), same reasoning
as `import_feat_magisches_erbe.py`.

Prerequisite "Klassenmerkmal Reittier oder Tiergefährte" is one OR-group over
every class ability that grants an `animal_companion`-track companion slot
(`base_companion_slot_grants.json`) — each class/archetype seeds its own
Tiergefährte/Reittier row, so naming just one would lock out the others.
Familiar-track abilities (Vertrauter, Arkane Verbindung, ...) are excluded,
and so are abilities that only modify an existing mount (Wildes Reittier,
Reittier herbeirufen) — their class already has the granting row in the group.
The feat's effect (opt into spells/effects that only target animals) is a
player-side choice at the table with no sheet impact — description-only.

Run with the project venv active (this only writes the fixture JSON files,
it doesn't touch the database — run the seed script afterward):
    cd backend && python scripts/import_feat_tierseele.py
    python -m app.seed.feat_seed
"""

from __future__ import annotations

import json
import uuid
from pathlib import Path

SEED_DIR = Path(__file__).resolve().parent.parent / "app" / "fixtures" / "seed"

ID_NAMESPACE = uuid.UUID("c3e81f4a-2d7b-4b96-a5e0-8f1d6c2b9e47")

TIERSEELE_FEAT_ID = "078f0df2-c5b5-5c26-985d-e3a3ae0a65f1"

FEAT = {
    "id": TIERSEELE_FEAT_ID,
    "name": "Tierseele",
    "description": "Deine enge Bindung zu einem Tier erlaubt dir, schädliche Magie zu ignorieren, welche deine "
    "wilde Seite nicht betreffen kann. Du kannst Zauber und Effekte, welche Tiere, Tiergefährten und besondere "
    "Reittiere betreffen, auch dich betreffen lassen, selbst wenn sie normalerweise Kreaturen deiner "
    "Kreaturenart nicht betreffen. So könntest du Tier verkleinern oder Tierwachstum auf dich selbst wirken, "
    "obwohl diese Zauber normalerweise nur auf Tiere wirken. Ein Verbündeter könnte Toten Tiergefährten "
    "erwecken auf dich wirken, um dich von den Toten zurückzuholen. Dabei obliegt es dir im Einzelfall zu "
    "entscheiden, ob du von solchen Zaubern betroffen werden willst, so dass ein Gegner nicht ohne deine "
    "Zustimmung Tier bezaubern oder Tier beherrschen auf dich wirken könnte. Du kannst dich entscheiden, "
    "Zauber und Effekte zu ignorieren, welche nicht zugleich auf deine ursprüngliche Kreaturenart und die "
    "Kreaturenart Tier wirken.",
    "type": "general",
    "prerequisite_text": "Klassenmerkmal Reittier oder Tiergefährte.",
}

COMPANION_ABILITY_IDS = [
    "1e421552-622f-583b-a8f9-62944ace3dc5",  # Tiergefährte (Druide)
    "38fe2b58-a26e-5733-b9db-3a61baf89508",  # Tiergefährte
    "ed50152f-572e-5ef2-9a67-1f9f3f399c4e",  # Tiergefährte
    "a98d91f5-2dff-506e-8bcc-03b3166ae731",  # Tiergefährte (Bund des Jägers)
    "0028e0bb-6d8f-5051-bdb8-3f960dcf1009",  # Göttlicher Bund: Reittier
    "399600a9-0ff4-5988-a3dd-f94d88427bb7",  # Gebundenes Reittier
    "099a403b-5551-579d-b438-c8d47fa0afff",  # Tiergefährte (Sekundärklasse Druide)
    "17ed3bd4-4828-5413-9755-5ac92605266f",  # Tiergefährte (Bärenschamane)
    "40573a63-983a-5895-b467-a622dbe886ec",  # Tiergefährte (Löwenschamane)
    "8d2f4782-0cfe-5064-bd79-15860dec8e5b",  # Tiergefährte (Jäger)
    "d8473cd2-cdac-5326-961b-ee39d8149d1d",  # Rudelbindung
]


def uid(*parts: str) -> str:
    return str(uuid.uuid5(ID_NAMESPACE, "|".join(parts)))


def load(filename: str) -> list[dict]:
    return json.loads((SEED_DIR / filename).read_text(encoding="utf-8"))


def save(filename: str, rows: list[dict]) -> None:
    (SEED_DIR / filename).write_text(json.dumps(rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    feats = [f for f in load("base_feats.json") if f["id"] != TIERSEELE_FEAT_ID]
    feats.append(FEAT)
    save("base_feats.json", feats)

    group_id = uid("group", TIERSEELE_FEAT_ID, "companion")
    req_abilities = [
        r for r in load("base_feat_required_class_abilities.json") if r["feat_id"] != TIERSEELE_FEAT_ID
    ]
    for ability_id in COMPANION_ABILITY_IDS:
        req_abilities.append(
            {
                "id": uid("req-class-ability", TIERSEELE_FEAT_ID, ability_id),
                "feat_id": TIERSEELE_FEAT_ID,
                "group_id": group_id,
                "ability_id": ability_id,
            }
        )
    save("base_feat_required_class_abilities.json", req_abilities)

    print("Tierseele feat id:", TIERSEELE_FEAT_ID)


if __name__ == "__main__":
    main()
