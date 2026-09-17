"""Builds Hexenmeister's rows of `../app/fixtures/seed/
base_secondary_class_ability_grants.json` — the "Sekundärklasse" alternate
rule's per-class content (http://prd.5footstep.de/Alternativregeln/
Fertigkeiten/AlternativesSystemfuerCharakteremitKlassenkombinationen), which
has been empty since the architecture pass (roadmap.md §9). Hexenmeister is
the first class filled in.

Source text for Hexenmeister (fetched 2026-09-17, quoted here since it's
prose with no datatable):

    Blutlinie: Auf der 1. Stufe muss er eine Hexenmeisterblutlinie wählen.
    Hinsichtlich aller Blutlinienfähigkeiten entspricht seine effektive
    Hexenmeisterstufe seiner Charakterstufe.
    Blutlinienfähigkeit: Mit der 3. Stufe erhält er die Blutlinienfähigkeit
    der 1. Stufe seiner Blutlinie.
    Verbesserte Blutlinienfähigkeit: Auf der 7. Stufe erhält er die
    Blutlinienfähigkeit der 3. Stufe seiner Blutlinie.
    Talent des Blutes: Mit der 11. Stufe erhält er eines der Talente seiner
    Blutlinie oder das Talent Materialkomponentenlos zaubern.
    Mächtige Blutlinienfähigkeit: Auf der 15. Stufe erhält er die
    Blutlinienfähigkeit der 9. Stufe seiner Blutlinie.
    Wahre Blutlinienfähigkeit: Mit der 19. Stufe erhält er die
    Blutlinienfähigkeit der 15. Stufe seiner Blutlinie.

"Blutlinie" itself (the 1st-level pick) isn't a grant row — it's the
`is_secondary_class_initial_pick` requirement already wired up (see
`test_secondary_class_initial_pick_is_required_immediately_at_level_1`).
The four remaining tiers (3/7/15/19) each depend on which bloodline was
picked, so each becomes *one row per bloodline* sharing the same
`character_level`, `option_group_key="bloodline"`, and its own
`option_choice_id` — `rules/secondary_class.py`'s
`_resolve_sub_choice_ability_id` filters these down at read time to the one
matching the character's actual pick. `option_choice_id` is its own column
(2026-09-17 migration) rather than resolved via `BaseClassAbilityGrant`:
several bloodlines' powers are the *same* catalog row (e.g. "Klauen",
"Kalter Stahl" each shared by two bloodlines), which would otherwise
collide on this table's own `(secondary_base_class_id, character_level,
ability_id)` uniqueness.

"Blutlinienfähigkeit der Nten Stufe" maps directly onto the primary
Hexenmeister's own `BaseClassAbilityGrant.level` column (a real Hexenmeister
gets bloodline powers at class levels 1/3/9/15/20) — level 1 has *two* rows
per bloodline (the bloodline arcana "Geheimnis des Blutes (X)" and the
actual 1st power); only the latter is "die Blutlinienfähigkeit", so arcana
rows are excluded by name.

**11th-level "Talent des Blutes" is deliberately not seeded here**: it
grants a *feat* choice (one of the bloodline's bonus feats, or Materialkomponentenlos
zaubern), not a `BaseClassAbility` — `BaseSecondaryClassAbilityGrant.
ability_id` has no equivalent for feats, so this tier needs its own schema
extension (or a feat-flavored sibling table) before it can be seeded
correctly. Tracked as a follow-up, not silently guessed at here.

Ids are deterministic (`uuid5` off the tier name + bloodline name,
`ID_NAMESPACE` below), so reruns upsert cleanly via
`app.seed.secondary_class_seed` instead of minting duplicates.

Usage (project venv active, database up — reads only, no writes):
    cd backend && python scripts/build_secondary_class_hexenmeister_seed.py
"""

import json
import uuid
from pathlib import Path

from sqlalchemy import select

from app.db import SessionLocal
from app.models import BaseClass, BaseClassAbility, BaseClassAbilityGrant, BaseClassOptionChoice, BaseClassOptionGroup

SEED_PATH = Path(__file__).resolve().parent.parent / "app" / "fixtures" / "seed" / "base_secondary_class_ability_grants.json"

ID_NAMESPACE = uuid.UUID("3f6b8e0a-7c2d-4e1a-9b5f-6a1d8c4b2e9f")

# Sekundärklasse character-level milestone -> real Hexenmeister class level
# whose BaseClassAbilityGrant row supplies "die Blutlinienfähigkeit der Nten
# Stufe seiner Blutlinie".
MILESTONE_TO_REAL_LEVEL = {3: 1, 7: 3, 15: 9, 19: 15}


def build_rows() -> list[dict]:
    db = SessionLocal()
    try:
        hexenmeister = db.scalar(select(BaseClass).where(BaseClass.name == "Hexenmeister"))
        assert hexenmeister is not None

        bloodline_group = db.scalar(
            select(BaseClassOptionGroup).where(
                BaseClassOptionGroup.base_class_id == hexenmeister.id, BaseClassOptionGroup.key == "bloodline"
            )
        )
        assert bloodline_group is not None

        bloodlines = db.scalars(
            select(BaseClassOptionChoice).where(BaseClassOptionChoice.group_id == bloodline_group.id)
        ).all()

        rows: list[dict] = []
        for bloodline in bloodlines:
            for character_level, real_level in MILESTONE_TO_REAL_LEVEL.items():
                candidates = db.execute(
                    select(BaseClassAbility.id, BaseClassAbility.name)
                    .join(BaseClassAbilityGrant, BaseClassAbilityGrant.ability_id == BaseClassAbility.id)
                    .where(
                        BaseClassAbilityGrant.base_class_id == hexenmeister.id,
                        BaseClassAbilityGrant.option_choice_id == bloodline.id,
                        BaseClassAbilityGrant.level == real_level,
                        ~BaseClassAbility.name.startswith("Geheimnis des Blutes"),
                    )
                ).all()
                if len(candidates) != 1:
                    print(
                        f"skip {bloodline.name} @ real level {real_level}: "
                        f"expected exactly 1 non-arcana ability, found {len(candidates)} {[c.name for c in candidates]}"
                    )
                    continue
                ability_id, ability_name = candidates[0]
                row_id = uuid.uuid5(ID_NAMESPACE, f"hexenmeister-bloodline|{character_level}|{bloodline.name}")
                rows.append(
                    {
                        "id": str(row_id),
                        "secondary_base_class_id": str(hexenmeister.id),
                        "character_level": character_level,
                        "ability_id": str(ability_id),
                        "effective_level_offset": 0,
                        "effective_level_divisor": 1,
                        "effective_level_minimum": None,
                        "option_group_key": "bloodline",
                        "option_choice_id": str(bloodline.id),
                    }
                )
        return rows
    finally:
        db.close()


def main() -> None:
    """Merges this class's rows into the shared seed file by `id` rather
    than overwriting it outright — other classes' content (added by their
    own, separate builder scripts, e.g. Mönch's hand-written row) lives in
    the same file and must survive a rerun of this one."""
    new_rows = {row["id"]: row for row in build_rows()}
    existing_rows = {row["id"]: row for row in json.loads(SEED_PATH.read_text(encoding="utf-8"))} if SEED_PATH.exists() else {}
    merged = {**existing_rows, **new_rows}
    rows = sorted(merged.values(), key=lambda r: (r["character_level"], r["id"]))
    SEED_PATH.write_text(json.dumps(rows, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"wrote {len(rows)} rows to {SEED_PATH} ({len(new_rows)} from this run)")


if __name__ == "__main__":
    main()
