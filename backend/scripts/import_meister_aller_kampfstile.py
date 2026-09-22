"""Import the "Meister aller Kampfstile" (Master of Many Styles) Mönch
archetype from http://prd.5footstep.de/AusbauregelnIIKampf/Archetypen/Moench/
MeisterallerKampfstile.

Must run after `import_moench.py` (this script resolves the Mönch grant rows
it replaces by loading the already-written `base_class_abilities.json`/
`base_class_ability_grants.json`, not by recomputing that script's own
id-hashing scheme).

Three named, replacing class features:
- **Bonustalente** (1st, 2nd, then every 4th level — same six levels as the
  core Mönch's own Bonustalent): the source text lets the archetype pick
  from any "Kampfkunsttalent" (style feat) or Elementarfaust instead of the
  base class's closed list. Modeled as `feat_type="kampfkunst"` (the open
  category `BaseFeat.type` already uses for the 7 style feats currently
  seeded — Kranichstil, Tigerstil, Schnappschildkrötenstil, Boxkampfbeinarbeit/
  -meister, Ringkampfexperte/-zerren), same "pure data change, no per-feat
  enumeration" shape as Kämpfer's own `feat_type="combat"` slot. Elementarfaust
  is *not* wired: it doesn't exist in `base_feats.json` at all yet (checked
  before writing this script) — same "don't guess a missing catalog row"
  policy as every other import here; the ability's own description still
  names it as a source-text option. Replaces all six of the base Mönch's
  Bonustalent grants.
- **Kampfstile verschmelzen** (1st level, scaling at 8th/15th folded into one
  ability's prose, same "one grant, later levels described in text" shape
  `import_moench.py` used for Schlaghagel/Rüstungsklassenbonus/Ki-Vorrat):
  replaces the base Mönch's Schlaghagel.
- **Perfekter Stil** (20th level): replaces the base Mönch's Perfektes
  Selbst.

Deliberately out of scope, same "composition only" principle as every other
class/archetype pass (CLAUDE.md): no stance-tracking mechanism exists in this
app at all (a character's active "Kampfstil"/Haltung, how many can be active
at once, activation as a Schnelle/Freie Aktion) — nothing here computes it,
same as the base Mönch's own Ki-Vorrat/Schlaghagel numbers being left
uncomputed.

Run with the project venv active (writes fixture JSON only, run the seed
scripts afterward):
    cd backend && python scripts/import_moench.py
    python scripts/import_meister_aller_kampfstile.py
    python -m app.seed.class_seed
    python -m app.seed.class_ability_seed
    python -m app.seed.class_ability_option_seed
"""

from __future__ import annotations

import json
import uuid
from pathlib import Path

FIXTURES = Path(__file__).resolve().parent.parent / "app" / "fixtures"
SEED_DIR = FIXTURES / "seed"

ID_NAMESPACE = uuid.UUID("6f2e6a2d-6a7b-4a5b-9a1a-3b2c9e8d7f6a")

MOENCH_ID = "4ed3adcc-31e6-408d-a554-5e76a368df9d"

BONUSTALENTE_DESC = (
    "Mit Beginn der 1. Stufe und der 2. Stufe und dann alle weiteren vier Stufen als Mönch kann ein Meister aller "
    "Kampfstile ein Bonuskampfkunsttalent oder das Talent Elementarfaust auswählen. Abgesehen von Elementarfaust "
    "muss er die Voraussetzungen dieser Talente nicht erfüllen. Alternativ kann er auch anstatt eines dieser "
    "Bonustalente ein Kampfkunsttalent eines Kampfstils auswählen, sofern er das passende Kampfkunsttalent für die "
    "Kampfhaltung besitzt (bspw. Erdkindgriff); der Meister aller Kampfstile muss ansonsten keine Voraussetzungen "
    "erfüllen. Dieses Klassenmerkmal ersetzt die Bonustalente, welche ein Mönch normalerweise erhält."
)

KAMPFSTILE_VERSCHMELZEN_DESC = (
    "(AF) Mit Beginn der 1. Stufe kann ein Meister aller Kampfstile zwei der ihm bekannten Kampfstile zu einem "
    "perfekteren Stil vereinen. Der Meister aller Kampfstile kann die Haltungen zweier Kampfstile zugleich "
    "aktivieren. Das Aktivieren einer Haltung erfordert immer noch eine Schnelle Aktion. Sollte der Meister aller "
    "Kampfstile seine Haltung wechseln, kann er währenddessen nur eine aktive Haltung aufrechterhalten. Er kann nur "
    "Haltungen zweier Kampfstile gleichzeitig aktiv haben.\n\n"
    "Mit Beginn der 8. Stufe kann der Meister aller Kampfstile drei Kampfkünste miteinander vereinen. Er kann "
    "ferner die Haltungen von bis zu drei Kampfstilen mit einer Schnellen Aktion aktivieren.\n\n"
    "Mit Beginn der 15. Stufe kann der Meister aller Kampfstile vier Kampfkünste miteinander verschmelzen. Er kann "
    "die Haltungen von vier Kampfstilen gleichzeitig aktiv haben und die Haltungen von bis zu vier Kampfstilen mit "
    "einer Freien Aktion aktivieren, indem er 1 Punkt seines Ki-Vorrats aufwendet. Dieses Klassenmerkmal ersetzt "
    "Schlaghagel."
)

PERFEKTER_STIL_DESC = (
    "(AF) Mit Beginn der 20. Stufe kann ein Meister aller Kampfstile die Haltung von bis zu fünf Kampfstilen aktiv "
    "haben und mit einer Freien Aktion ändern. Dieses Klassenmerkmal ersetzt Perfektes Selbst."
)


def uid(*parts: str) -> str:
    return str(uuid.uuid5(ID_NAMESPACE, "|".join(parts)))


def load(filename: str) -> list[dict]:
    return json.loads((SEED_DIR / filename).read_text(encoding="utf-8"))


def save(filename: str, rows: list[dict]) -> None:
    deduped: dict[str, dict] = {}
    for row in rows:
        deduped[row["id"]] = row
    (SEED_DIR / filename).write_text(
        json.dumps(list(deduped.values()), ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def moench_grant_ids(*, abilities: list[dict], grants: list[dict], ability_name: str, levels: list[int]) -> list[str]:
    name_by_ability_id = {a["id"]: a["name"] for a in abilities}
    matches = {
        g["level"]: g["id"]
        for g in grants
        if g["base_class_id"] == MOENCH_ID
        and g["level"] in levels
        and name_by_ability_id.get(g["ability_id"]) == ability_name
    }
    missing = [level for level in levels if level not in matches]
    assert not missing, f"Mönch grant not found for {ability_name!r} at level(s) {missing} — run import_moench.py first"
    return [matches[level] for level in levels]


def main() -> None:
    classes = load("base_classes.json")
    abilities = load("base_class_abilities.json")
    grants = load("base_class_ability_grants.json")
    replacements = load("base_class_ability_replacements.json")
    feat_options = load("base_class_ability_feat_options.json")

    archetype_id = uid("meister-aller-kampfstile-archetype", MOENCH_ID)
    classes = [c for c in classes if c["id"] != archetype_id]
    classes.append(
        {
            "id": archetype_id,
            "name": "Meister aller Kampfstile",
            "hit_dice": None,
            "arch_class_of": MOENCH_ID,
            "casting_ability": None,
            "spell_tradition": None,
            "bab_progression": None,
            "fort_save": None,
            "ref_save": None,
            "wil_save": None,
            "skill_points_base": None,
        }
    )

    ability_ids_by_id = {a["id"] for a in abilities}

    def add_ability(name: str, description: str) -> str:
        aid = uid("meister-aller-kampfstile-ability", archetype_id, name)
        if aid not in ability_ids_by_id:
            abilities.append({"id": aid, "name": name, "description": description})
            ability_ids_by_id.add(aid)
        return aid

    def add_grant(ability_id: str, level: int) -> str:
        grant_id = uid("meister-aller-kampfstile-grant", ability_id, str(level))
        grants[:] = [g for g in grants if g["id"] != grant_id]
        grants.append(
            {
                "id": grant_id,
                "base_class_id": archetype_id,
                "ability_id": ability_id,
                "option_choice_id": None,
                "level": level,
            }
        )
        return grant_id

    def add_replacement(ability_id: str, replaces_grant_id: str) -> None:
        replacement_id = uid("meister-aller-kampfstile-replacement", ability_id, replaces_grant_id)
        replacements[:] = [r for r in replacements if r["id"] != replacement_id]
        replacements.append(
            {
                "id": replacement_id,
                "archetype_class_id": archetype_id,
                "ability_id": ability_id,
                "replaces_grant_id": replaces_grant_id,
            }
        )

    # ---- Bonustalente: replaces all six of the base Mönch's Bonustalent grants ----
    bonustalent_levels = [1, 2, 6, 10, 14, 18]
    bonustalente_id = add_ability("Bonustalente (Meister aller Kampfstile)", BONUSTALENTE_DESC)
    for level in bonustalent_levels:
        add_grant(bonustalente_id, level)
    for replaced_grant_id in moench_grant_ids(
        abilities=abilities, grants=grants, ability_name="Bonustalent", levels=bonustalent_levels
    ):
        add_replacement(bonustalente_id, replaced_grant_id)

    feat_option_ids = {row["id"] for row in feat_options}
    kampfkunst_option_id = uid("meister-aller-kampfstile-feat-option", bonustalente_id, "kampfkunst")
    if kampfkunst_option_id not in feat_option_ids:
        feat_options.append(
            {
                "id": kampfkunst_option_id,
                "ability_id": bonustalente_id,
                "option_choice_id": None,
                "feat_type": "kampfkunst",
                "feat_id": None,
                "min_level": None,
            }
        )

    # ---- Kampfstile verschmelzen: replaces the base Mönch's Schlaghagel ----
    kampfstile_id = add_ability("Kampfstile verschmelzen", KAMPFSTILE_VERSCHMELZEN_DESC)
    add_grant(kampfstile_id, 1)
    (schlaghagel_grant_id,) = moench_grant_ids(
        abilities=abilities, grants=grants, ability_name="Schlaghagel", levels=[1]
    )
    add_replacement(kampfstile_id, schlaghagel_grant_id)

    # ---- Perfekter Stil: replaces the base Mönch's Perfektes Selbst ----
    perfekter_stil_id = add_ability("Perfekter Stil", PERFEKTER_STIL_DESC)
    add_grant(perfekter_stil_id, 20)
    (perfektes_selbst_grant_id,) = moench_grant_ids(
        abilities=abilities, grants=grants, ability_name="Perfektes Selbst", levels=[20]
    )
    add_replacement(perfekter_stil_id, perfektes_selbst_grant_id)

    save("base_classes.json", classes)
    save("base_class_abilities.json", abilities)
    save("base_class_ability_grants.json", grants)
    save("base_class_ability_replacements.json", replacements)
    save("base_class_ability_feat_options.json", feat_options)

    print("Meister aller Kampfstile class id:", archetype_id)
    print("Done.")


if __name__ == "__main__":
    main()
