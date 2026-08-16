"""Import the "Seeräuber" (Sea Reaver) archetype from
http://prd.5footstep.de/AusbauregelnIIKampf/Archetypen/Barbar/Seeraeuber,
scoped to Entfesselter Barbar (unchained Barbarian) only, per the project
owner's request — the PRD page itself is written against the core
(Grundregelwerk) Barbar.

Adapted onto Entfesselter Barbar rather than transcribed verbatim: the
unchained Barbar's own trap-sense-equivalent is "Gefahreninstinkt", not
"Fallengespür" (see `rules/classes/barbarian.py`'s
`BARBAR_ENTFESSELTER_ROOT_CLASS_ID` docstring — Entfesselter Barbar is
seeded as its own root class here, not an archetype of Barbar). Official
errata for archetypes written against the core Barbar states any class
feature they replace that isn't itself present on the unchained chassis
maps onto the unchained feature that plays the same role — "replaces trap
sense" becomes "replaces danger sense" for an unchained-Barbar archetype.
Applied here: "Wilder Seemann" replaces Gefahreninstinkt (not Fallengespür).
Every other replaced feature (Schnelle Bewegung, Verbesserte
Reflexbewegung) already shares one id between Barbar and Entfesselter
Barbar, so no adaptation was needed there.

What this script does:
- Adds one new archetype `BaseClass` row ("Seeräuber", `arch_class_of` =
  Entfesselter Barbar's root id) — same shape as the existing
  Zwei-Waffen-Kämpfer/Schildkämpfer Kämpfer archetypes.
- Adds 5 new `BaseClassAbility` rows (Umgang mit Waffen und Rüstungen,
  Schrecken des Meeres, Augen des Sturms, Wilder Seemann, Sicherer Tritt)
  with their own `BaseClassAbilityGrant` rows under the archetype's own
  class id.
- Adds `BaseClassAbilityReplacement` rows scoping Umgang mit Waffen und
  Rüstungen/Schrecken des Meeres/Wilder Seemann/Sicherer Tritt to the
  specific Entfesselter-Barbar grants they replace (proficiency and
  Schnelle Bewegung at 1; Gefahreninstinkt at 3/6/9/12/15/18; Verbesserte
  Reflexbewegung at 5). Augen des Sturms doesn't replace anything — the
  PRD text never says it does.

Proficiency, corrected per project-owner review (2026-08-16): the PRD's
proficiency line ("Ein Seeräuber ist nicht geübt im Umgang mit
Mittelschweren Rüstungen") isn't a description-text footnote, it's its own
class feature that replaces Entfesselter Barbar's level-1 "Umgang mit
Waffen und Rüstungen" grant — same weapon/shield proficiency as the base
class, light-armor proficiency kept, medium-armor proficiency dropped. This
is the first archetype in this catalog to touch a proficiency ability
(Zwei-Waffen-Kämpfer/Schildkämpfer don't), so there's no prior grant-shape
to reuse; it uses the exact same `BaseClassAbilityGrant`/
`BaseClassAbilityReplacement` shape every other replacement here does.

Deliberately still out of scope (see CLAUDE.md's composition-vs-computation
split and this script's companion `import_barbar.py`'s own scoping notes):
- No handler-side computation for Umgang mit Waffen und Rüstungen/
  Schrecken des Meeres/Augen des Sturms/Sicherer Tritt — confirmed with
  the project owner as pure player-facing information, no further
  modeling needed. Wilder Seemann's skill bonus IS computed (see
  `rules/classes/barbarian.py`'s `wilder_seemann_skill_bonus` and
  `sheet.py`'s `_build_skills`), same situational-note treatment as
  `rules/speed.py`'s `jump_skill_bonus`.
- The "Kampfrauschkräfte" list (8 named rage powers) is a *recommendation*
  per the project owner, not a restriction — confirmed nothing needs
  modeling here at all, not even as a future gap.

Run with the project venv active (this only writes the fixture JSON files,
it doesn't touch the database — run the normal seed scripts afterward):
    cd backend && python scripts/import_barbar_seereauber.py
    cd backend && python -m app.seed.class_seed
    cd backend && python -m app.seed.class_ability_seed
"""

from __future__ import annotations

import json
import uuid
from pathlib import Path

FIXTURES = Path(__file__).resolve().parent.parent / "app" / "fixtures"
SEED_DIR = FIXTURES / "seed"

ID_NAMESPACE = uuid.UUID("5a6e9c3b-2d7f-4b1a-8e4c-1f9b6a2d7c5e")

ENTFESSELTER_BARBAR_ID = "332f742d-d2a1-5375-8bff-0924f92d2b9d"

# Entfesselter-Barbar grants this archetype replaces (from
# `base_class_ability_grants.json`, `base_class_id` = Entfesselter Barbar).
UMGANG_MIT_WAFFEN_UND_RUESTUNGEN_GRANT_ID = "63f4f5e2-3ff8-5fdb-9020-f759425e377f"
SCHNELLE_BEWEGUNG_GRANT_ID = "4ae53700-845c-5afc-8965-b41d2ad9fd72"
GEFAHRENINSTINKT_GRANT_IDS = [
    "f182a2c5-1873-5937-bd2d-abcec4525c50",  # level 3
    "1f9db2fe-37f7-552b-95df-0ea6f1605a63",  # level 6
    "9308366a-36c3-587e-961d-b5465ca1c8bb",  # level 9
    "91e568d4-9451-537a-970a-c8beec5651e0",  # level 12
    "1333566c-18aa-5f36-bbae-a01b1da1392c",  # level 15
    "edadf840-7ef7-5c67-b6b4-5e2aca6b2b04",  # level 18
]
VERBESSERTE_REFLEXBEWEGUNG_GRANT_ID = "d9ef537b-5fc2-5258-8782-f4cb4d68e473"

WILDER_SEEMANN_LEVELS = [3, 6, 9, 12, 15, 18]

# (name, levels, description, replaces_grant_ids)
CLASS_FEATURES: list[tuple[str, list[int], str, list[str]]] = [
    (
        "Umgang mit Waffen und Rüstungen",
        [1],
        "Ein Seeräuber ist im Umgang mit allen einfachen Waffen und allen Kriegswaffen, leichten "
        "Rüstungen und Schilden (außer Turmschilden) geübt, jedoch nicht mit Mittelschweren "
        "Rüstungen. Dieses Klassenmerkmal ersetzt Entfesselter Barbars Umgang mit Waffen und "
        "Rüstungen.",
        [UMGANG_MIT_WAFFEN_UND_RUESTUNGEN_GRANT_ID],
    ),
    (
        "Schrecken des Meeres",
        [1],
        "(AF) Ein Seeräuber kann seinen Atem für eine Anzahl von Runden in Höhe des Vierfachen "
        "seiner Konstitution anhalten. Ferner kann er sich normal durch Felder stehenden Wassers "
        "oder Sumpfes mit einer Tiefe von bis zu 0,30 m hindurch bewegen, ohne dass ihn dies "
        "zusätzliche Bewegung kostet. Schlussendlich ignoriert ein Seeräuber bei seinem Angriff den "
        "normalen Deckungsbonus auf die RK von Kreaturen, die teilweise unter Wasser sind. Dieses "
        "Klassenmerkmal ersetzt Schnelle Bewegung.",
        [SCHNELLE_BEWEGUNG_GRANT_ID],
    ),
    (
        "Augen des Sturms",
        [2],
        "(AF) Mit Beginn der 2. Stufe ignoriert ein Seeräuber Tarnung aufgrund von Nebel, Regen, Wind "
        "oder anderen Wettereffekten, die nicht Vollständige Tarnung verleihen. Ferner werden alle "
        "Mali auf Fertigkeitswürfe für Wahrnehmung aufgrund von Wetterbedingungen halbiert.",
        [],
    ),
    (
        "Wilder Seemann",
        WILDER_SEEMANN_LEVELS,
        "(AF) Mit Beginn der 3. Stufe erhält ein Seeräuber einen Bonus von +1 auf seine "
        "Fertigkeitswürfe für Akrobatik, Beruf (Seemann), Klettern, Schwimmen und Überlebenskunst im "
        "Wasser, auf Schiffen und an der Küste. Diese Boni steigen alle weiteren drei Stufen als "
        "Barbar um zusätzliche +1 (d.h. auf der 6., 9. usw.). Dieses Klassenmerkmal ersetzt "
        "Gefahreninstinkt (Entfesselter Barbars Entsprechung zu Fallengespür, das dieses Klassenmerkmal "
        "beim Grundregelwerk-Barbaren ersetzt).",
        GEFAHRENINSTINKT_GRANT_IDS,
    ),
    (
        "Sicherer Tritt",
        [5],
        "(AF) Mit Beginn der 5. Stufe erleidet ein Seeräuber keine Nachteile mehr, wenn er sich über "
        "übernatürliche oder magische rutschige Oberflächen bewegt (z.B. Schmieren, Eissturm oder "
        "Schneesturm). Er riskiert nicht zu stürzen und verliert auch seinen GE-Bonus auf die RK "
        "nicht, wenn er sich durch solche Gebiete bewegt; er behandelt sie auch nicht als Schwieriges "
        "Gelände. Dieses Klassenmerkmal ersetzt Verbesserte Reflexbewegung.",
        [VERBESSERTE_REFLEXBEWEGUNG_GRANT_ID],
    ),
]


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


def main() -> None:
    archetype_id = uid("seereauber-archetype", ENTFESSELTER_BARBAR_ID)

    # ---- base_classes.json ----
    classes = load("base_classes.json")
    if not any(c["id"] == archetype_id for c in classes):
        classes.append(
            {
                "id": archetype_id,
                "name": "Seeräuber",
                "hit_dice": None,
                "arch_class_of": ENTFESSELTER_BARBAR_ID,
                "casting_ability": None,
                "spell_tradition": None,
                "bab_progression": None,
                "fort_save": None,
                "ref_save": None,
                "wil_save": None,
                "skill_points_base": None,
            }
        )
    save("base_classes.json", classes)

    # ---- base_class_abilities.json + base_class_ability_grants.json + base_class_ability_replacements.json ----
    abilities = load("base_class_abilities.json")
    own_ability_ids = {uid("seereauber-ability", name) for name, _levels, _description, _replaces in CLASS_FEATURES}
    abilities = [a for a in abilities if a["id"] not in own_ability_ids]

    grants = load("base_class_ability_grants.json")
    own_grant_ids = {
        uid("seereauber-grant", uid("seereauber-ability", name), str(level))
        for name, levels, _description, _replaces in CLASS_FEATURES
        for level in levels
    }
    grants = [g for g in grants if g["id"] not in own_grant_ids]

    replacements = load("base_class_ability_replacements.json")
    own_replacement_ids = {
        uid("seereauber-replacement", uid("seereauber-ability", name), replaced_grant_id)
        for name, _levels, _description, replaces in CLASS_FEATURES
        for replaced_grant_id in replaces
    }
    replacements = [r for r in replacements if r["id"] not in own_replacement_ids]

    def add_ability(name: str, description: str) -> str:
        aid = uid("seereauber-ability", name)
        abilities.append({"id": aid, "name": name, "description": description})
        return aid

    def add_grant(ability_id: str, level: int) -> None:
        grants.append(
            {
                "id": uid("seereauber-grant", ability_id, str(level)),
                "base_class_id": archetype_id,
                "ability_id": ability_id,
                "option_choice_id": None,
                "level": level,
            }
        )

    def add_replacement(ability_id: str, replaced_grant_id: str) -> None:
        replacements.append(
            {
                "id": uid("seereauber-replacement", ability_id, replaced_grant_id),
                "archetype_class_id": archetype_id,
                "ability_id": ability_id,
                "replaces_grant_id": replaced_grant_id,
            }
        )

    for name, levels, description, replaces in CLASS_FEATURES:
        aid = add_ability(name, description)
        for level in levels:
            add_grant(aid, level)
        for replaced_grant_id in replaces:
            add_replacement(aid, replaced_grant_id)

    save("base_class_abilities.json", abilities)
    save("base_class_ability_grants.json", grants)
    save("base_class_ability_replacements.json", replacements)

    print("Archetype class id:", archetype_id)
    print("Class features imported:", len(CLASS_FEATURES))
    print("Total grants (this archetype):", len([g for g in grants if g["base_class_id"] == archetype_id]))
    print("Total replacements (this archetype):", len([r for r in replacements if r["archetype_class_id"] == archetype_id]))
    print("Done.")


if __name__ == "__main__":
    main()
