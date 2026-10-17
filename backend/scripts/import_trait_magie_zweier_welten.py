"""Add the "Magie zweier Welten" trait (Two-World Magic) from
http://prd.5footstep.de/AndereBaende/Wesenszuege/MagiezweierWelten
("Sargava - Die verlorene Kolonie") to `base_traits.json` — not on the
general Wesenszüge page `build_traits_seed.py` imported.

Description is the PRD text verbatim. `area`: "magic" — the PRD page gives
no category; the English original is a Magic trait. The effect (one
0th-level spell from another class's list joins the character's own class
list) has no handler yet — description-only, like most traits.

Same deterministic id scheme as `build_traits_seed.py`
(`uuid5(ID_NAMESPACE, name)`, same `ID_NAMESPACE`), same as
`import_trait_clever_wordplay.py`.

Run with the project venv active (this only writes the fixture JSON file,
it doesn't touch the database - run the normal seed script afterward):
    cd backend && python scripts/import_trait_magie_zweier_welten.py
    python -m app.seed.trait_seed
"""

from __future__ import annotations

import json
import uuid
from pathlib import Path

SEED_DIR = Path(__file__).resolve().parent.parent / "app" / "fixtures" / "seed"

ID_NAMESPACE = uuid.UUID("7d3c9a6e-4b1f-4e2a-9c5d-6a1f3e9c7d3c")

NAME = "Magie zweier Welten"
DESCRIPTION = (
    "Du hast die Kluft zwischen der natürlichen Magie der Ureinwohner und der verfeinerten Magie der "
    "Kolonisten überbrückt. Such dir einen Zauber der Stufe 0 aus einer Liste der Klassenzauber aus, die nicht "
    "deine ist. Dieser Zauber ist nun ein Zauber der Stufe 0 auf deiner Klassenzauberliste (oder ein Zauber "
    "der 1. Stufe, wenn deine Klasse keine Zauber der Stufe 0 besitzt). Bist du zum Beispiel ein Druide, "
    "könntest du Magierhand auswählen und ihn danach als Druidenzauber der Stufe 0 vorbereiten. Bist du ein "
    "Hexenmeister, könntest du Richtung wissen als einen dir nun bekannten Hexenmeisterzauber auswählen."
)
AREA = "magic"


def main() -> None:
    path = SEED_DIR / "base_traits.json"
    traits = json.loads(path.read_text(encoding="utf-8"))

    trait_id = str(uuid.uuid5(ID_NAMESPACE, NAME))
    traits[:] = [t for t in traits if t["id"] != trait_id]
    traits.append({"id": trait_id, "name": NAME, "description": DESCRIPTION, "area": AREA})

    path.write_text(json.dumps(traits, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("Magie zweier Welten trait id:", trait_id)
    print("Done.")


if __name__ == "__main__":
    main()
