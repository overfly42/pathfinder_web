"""Add the "Clever Wordplay" trait (not on the German PRD's general
Wesenszüge page, http://prd.5footstep.de/AusbauregelnIVKampagnen/
Charakterhintergrund/Wesenszuege, which `build_traits_seed.py` already
imported in full — this one is a Pathfinder Society Primer trait, outside
that book's scope) to `base_traits.json`.

Source: https://www.d20pfsrd.com/traits/social-traits/clever-wordplay/
("Pathfinder Player Companion: Pathfinder Society Primer"). English text:
"Choose one Charisma-based skill. You attempt checks with that skill using
your Intelligence modifier instead of your Charisma modifier." No source
book has this trait's own German PRD page, so the name/description below
are this project's own translation, not a transcription — kept literal
(no invented enumeration of which skills count as Charisma-based, since the
source itself doesn't list them either) rather than paraphrased. `area`:
"social", per d20pfsrd's own category (its URL path is
`/traits/social-traits/...`), matching this catalog's existing social
traits (Schlagfertig, Charmeur, ...).

Same deterministic id scheme as `build_traits_seed.py`
(`uuid5(ID_NAMESPACE, name)`, same `ID_NAMESPACE`) so this row is
indistinguishable from one that script would have produced, even though
it's added independently here.

Run with the project venv active (this only writes the fixture JSON file,
it doesn't touch the database - run the normal seed script afterward):
    cd backend && python scripts/import_trait_clever_wordplay.py
    python -m app.seed.trait_seed
"""

from __future__ import annotations

import json
import uuid
from pathlib import Path

SEED_DIR = Path(__file__).resolve().parent.parent / "app" / "fixtures" / "seed"

ID_NAMESPACE = uuid.UUID("7d3c9a6e-4b1f-4e2a-9c5d-6a1f3e9c7d3c")

NAME = "Gewitztes Wortspiel"
DESCRIPTION = (
    "Wähle eine charismabasierte Fertigkeit. Du legst Fertigkeitswürfe für diese Fertigkeit mit deinem "
    "IN-Modifikator anstelle deines CH-Modifikators ab."
)
AREA = "social"
# "charismabasierte Fertigkeit" -> BaseTrait.skill_choice_ability (2026-08-21,
# see that column's docstring): restricts the character's skill sub-choice to
# BaseSkill rows whose own `ability == "CH"`.
SKILL_CHOICE_ABILITY = "CH"


def main() -> None:
    path = SEED_DIR / "base_traits.json"
    traits = json.loads(path.read_text(encoding="utf-8"))

    trait_id = str(uuid.uuid5(ID_NAMESPACE, NAME))
    traits[:] = [t for t in traits if t["id"] != trait_id]
    traits.append(
        {
            "id": trait_id,
            "name": NAME,
            "description": DESCRIPTION,
            "area": AREA,
            "skill_choice_ability": SKILL_CHOICE_ABILITY,
        }
    )

    path.write_text(json.dumps(traits, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("Clever Wordplay trait id:", trait_id)
    print("Done.")


if __name__ == "__main__":
    main()
