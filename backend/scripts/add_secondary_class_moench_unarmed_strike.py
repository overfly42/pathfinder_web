"""Adds Mönch's one clean "Talentauswahl"-shaped Sekundärklasse tier
("Waffenloser Schlag", milestone 3) to the shared `base_secondary_class_ability_grants.json`
(see `build_secondary_class_hexenmeister_seed.py` for the file's general
shape and merge-by-id convention this script follows too).

Source text (http://prd.5footstep.de/Alternativregeln/Fertigkeiten/
AlternativesSystemfuerCharakteremitKlassenkombinationen, Mönch section):

    Waffenloser Schlag: Ab der 3. Stufe erhält er das Bonustalent
    Verbesserter waffenloser Schlag und den Waffenlosen Schaden eines
    Mönchs; seine effektive Mönchsstufe entspricht hierbei seiner
    Charakterstufe -2.

Despite being called a "Bonustalent", this tier is *not* a player choice —
it's always exactly "Verbesserter waffenloser Schlag" (Improved Unarmed
Strike), unlike Hexenmeister's "Talent des Blutes" or Magier's "Entdeckung"
(a real pick among several options, not seedable without the still-open
level-up-picker wiring). A fixed feat grant needs no new schema at all: it
reuses the *existing* `BaseClassAbilityGrantedFeat` mechanism (ability id ->
feat id, unconditional) the same way real classes' weapon/armor proficiency
abilities already do (see `class_ability_granted_feat_seed.py`) — a fresh
`BaseClassAbility` wrapper row carries the flavor text and is what
`BaseSecondaryClassAbilityGrant.ability_id` points at; the feat comes along
automatically via `rules/proficiency.py`'s `class_granted_proficiency_feat_ids`
(misleadingly proficiency-scoped by name only — the lookup itself doesn't
care what kind of feat it is).

The unarmed-damage-progression half of this tier ("den Waffenlosen Schaden
eines Mönchs") is *not* modeled — Mönch has no `rules/classes/moench.py`
handler yet (no real class content exists for it at all, see roadmap.md),
so there's nothing for the correctly-computed `effective_level_offset=-2`
to feed into yet. The wrapper ability's own description says so; nothing
here claims otherwise.

Run with the project venv active and the database up (reads base_classes/
base_feats, writes only to the seed JSON files — no direct DB writes):
    cd backend && python scripts/add_secondary_class_moench_unarmed_strike.py
"""

import json
from pathlib import Path

from sqlalchemy import select

from app.db import SessionLocal
from app.models import BaseClass, BaseFeat

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "app" / "fixtures" / "seed"

ABILITY_ID = "5301612f-8bc8-5c02-979a-b919937fd5b8"
GRANTED_FEAT_ROW_ID = "f2d5bc8a-f10e-55ea-ab72-356e60e473ce"
GRANT_ROW_ID = "e5c809a1-5570-517c-9070-2c9b4a019879"


def _upsert(path: Path, row: dict) -> None:
    rows = json.loads(path.read_text(encoding="utf-8"))
    by_id = {r["id"]: r for r in rows}
    by_id[row["id"]] = row
    path.write_text(json.dumps(list(by_id.values()), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main() -> None:
    db = SessionLocal()
    try:
        moench = db.scalar(select(BaseClass).where(BaseClass.name == "Mönch"))
        feat = db.scalar(select(BaseFeat).where(BaseFeat.name == "Verbesserter waffenloser Schlag"))
        assert moench is not None and feat is not None
        moench_id, feat_id = str(moench.id), str(feat.id)
    finally:
        db.close()

    _upsert(
        FIXTURES_DIR / "base_class_abilities.json",
        {
            "id": ABILITY_ID,
            "name": "Waffenloser Schlag (Sekundärklasse)",
            "description": (
                "Erhält das Talent Verbesserter waffenloser Schlag sowie den Waffenlosen Schaden eines Mönchs mit "
                "einer effektiven Mönchsstufe in Höhe seiner Charakterstufe -2 (nur als Sekundärklassenmerkmal "
                "vergeben; der Waffenlose-Schaden-Fortschritt selbst ist noch nicht mechanisch berechnet, da Mönch "
                "noch keinen eigenen HANDLERS-Eintrag hat)."
            ),
        },
    )
    _upsert(
        FIXTURES_DIR / "base_class_ability_granted_feats.json",
        {"id": GRANTED_FEAT_ROW_ID, "ability_id": ABILITY_ID, "feat_id": feat_id},
    )
    _upsert(
        FIXTURES_DIR / "base_secondary_class_ability_grants.json",
        {
            "id": GRANT_ROW_ID,
            "secondary_base_class_id": moench_id,
            "character_level": 3,
            "ability_id": ABILITY_ID,
            "effective_level_offset": -2,
            "effective_level_divisor": 1,
            "effective_level_minimum": None,
            "option_group_key": None,
            "option_choice_id": None,
        },
    )
    print("wrote Mönch's Waffenloser Schlag (Sekundärklasse) content")


if __name__ == "__main__":
    main()
