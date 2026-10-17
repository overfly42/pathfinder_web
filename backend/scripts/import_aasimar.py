"""Import the Aasimar ("Aasimare") race, including its alternate racial
traits and favored-class-bonus options, from
http://prd.5footstep.de/AusbauregelnIIIVoelker/UngewoehnlicheVoelker/Aasimare
into the seed JSON files.

Scope: same as `import_ork.py` — race + racial traits + alternate racial
traits + favored-class-bonus options only. The page's two racial archetypes
(Besonnener Wächter/Paladin, Läuterer/Mystiker) and its "Neue Volksregeln"
section (equipment, eight feats, three magic items, three spells) are out
of scope for this pass.

Racial traits: fixed +2 WE/+2 CH, reusing the shared `ABILITY_WE_PLUS2`/
`ABILITY_CH_PLUS2` catalog rows (and handlers) every flex race's alternates
already use. Mittelgroß/Normale Bewegungsrate/Dunkelsicht reuse the rows
Ork already grants. `BaseRace.creature_type` is set to "Externar" (the
first player race that isn't Humanoid); nothing computes against it yet.

Modeled in `rules/race_abilities.py` (see that module): Bewandert's flat
+2 Diplomatie/Wahrnehmung, the flat skill-bonus clause of Sprachenmeister/
Himmelsgeboren/Unsterblicher Lebensfunke, and Heiligenschein's at-will
*Licht*. Everything else (energy resistances, Zauberresistenz, the once-a-
day spell-like abilities, bonuses against evil outsiders, caster-level
increases) stays flavor-only — no lever to hook into yet, same as e.g.
Elf's Elfische Immunität.

Alternate racial traits: Celestischer Kreuzfahrer, Himmelsgeboren and
Unsterblicher Lebensfunke each replace two traits — two
`RaceAbilityReplacement` rows per trait, same shape as Ork's Schnüffler.
Spross der Menschheit replaces "die Sprache Celestisch" (languages aren't
modeled for any race, see `import_ork.py`) and changes the Einheimischer
subtype; it's recorded as replacing "Einheimischer Externar", since an
alternate with no replacement row isn't pickable at all
(`routers/races.py`'s `resolve_alt_trait`) and its own description restates
that it still counts as Externar (Einheimischer).

Favored class bonus: the source page lists eight classes. Inquisitor,
Paktmagier and Ritter have no seeded `BaseClass` row — skipped, not
guessed, same precedent `import_ork.py` set.

Run with the project venv active (this only writes the fixture JSON files,
it doesn't touch the database — run the seed scripts afterward):
    cd backend && python scripts/import_aasimar.py
    python -m app.seed.race_seed
    python -m app.seed.class_option_seed
    python -m app.seed.class_ability_seed
"""

from __future__ import annotations

import json
import uuid
from pathlib import Path

FIXTURES = Path(__file__).resolve().parent.parent / "app" / "fixtures"
SEED_DIR = FIXTURES / "seed"

# Grant/replacement/choice row ids only — derived, not hand-frozen. The race
# id and every `BaseRaceAbility` id below ARE hand-frozen; the ones with a
# handler match `rules/race_abilities.py`'s own constants.
ID_NAMESPACE = uuid.UUID("5e1f0c7a-2b8d-4c3e-9a6f-0d4b7e2c9a18")

AASIMAR_RACE_ID = "c8c2eba3-43f6-4bf8-9dd6-0a531d6f66ec"

# ---- reused catalog rows (already seeded for other races) ----
ABILITY_WE_PLUS2 = "f4278c92-0328-476d-818a-ae0ce9e0aaef"
ABILITY_CH_PLUS2 = "1dfff0e2-95a6-4635-a76e-639a2dab82af"
ABILITY_MITTELGROSS = "c98915e3-0ade-4fd4-a203-baed02fdfc7e"
ABILITY_NORMALE_BEWEGUNGSRATE = "2e0186d5-e532-4532-b7f7-b4c6f4834bde"
ABILITY_DUNKELSICHT = "6670c6fd-ac89-468b-8072-3f6c68d43a35"

# ---- new catalog rows (own to Aasimar) ----
ABILITY_EINHEIMISCHER_EXTERNAR = "3b31195f-c408-4352-8f73-fa2247f6654a"
ABILITY_BEWANDERT = "c6ba1c4e-2587-48dc-9de8-7a8aa235cf44"
ABILITY_CELESTISCHE_RESISTENZ = "9c5f9478-53db-4937-9dcc-6aab0e0cabc4"
ABILITY_TAGESLICHT = "908a5a57-89d5-421a-a012-42ec4a6b230f"

# ---- alternate racial traits ----
ABILITY_CHARAKTERSTARK = "2a5cf4e9-fe62-4592-baa2-3670632fe3d8"
ABILITY_CELESTISCHER_KREUZFAHRER = "63b583c8-38ec-4202-b719-e9d8a24f216b"
ABILITY_ERHABENE_RESISTENZ = "4b9ec209-479a-4372-8bfd-d973b9979cf1"
ABILITY_HEILIGENSCHEIN = "b95e1855-157d-489f-aa72-7abd7e190eba"
ABILITY_HIMMELSGEBOREN = "6580a1af-8d2f-40fb-8628-ceb9882aac6f"
ABILITY_SPROSS_DER_MENSCHHEIT = "8f8d29f6-5687-45f8-bca1-d2aa048e23c2"
ABILITY_SPRACHENMEISTER = "67a751f6-2b89-4852-9d91-f369fe991749"
ABILITY_UNSTERBLICHER_GEIST = "599ef5d8-9890-4887-8753-b09a94e94f2b"
ABILITY_UNSTERBLICHER_LEBENSFUNKE = "07425573-7c5c-4f65-881b-8fbd0a5381d3"

NEW_ABILITIES: list[tuple[str, str, str]] = [
    (
        ABILITY_EINHEIMISCHER_EXTERNAR,
        "Einheimischer Externar",
        "Aasimare sind Externare mit der Unterart Einheimisch.",
    ),
    (
        ABILITY_BEWANDERT,
        "Bewandert",
        "Erhält einen Volksbonus von +2 auf Fertigkeitswürfe für Diplomatie und Wahrnehmung.",
    ),
    (
        ABILITY_CELESTISCHE_RESISTENZ,
        "Celestische Resistenz",
        "Hat Resistenz Elektrizität 5, Kälte 5 und Säure 5.",
    ),
    (
        ABILITY_TAGESLICHT,
        "Zauberähnliche Fähigkeit (Tageslicht)",
        "Kann einmal am Tag Tageslicht als zauberähnliche Fähigkeit benutzen (die Zauberstufe entspricht "
        "der Klassenstufe des Aasimar).",
    ),
    (
        ABILITY_CHARAKTERSTARK,
        "Charakterstark",
        "Kann einmal am Tag als zauberähnliche Fähigkeit Oppositionsresistenz gegen Böses wirken. Wendet "
        "der Aasimar diese Fähigkeit auf sich selbst an, steigt die Wirkungsdauer auf 1 Stunde pro Stufe. "
        "Dieses Volksmerkmal ersetzt Zauberähnliche Fähigkeit.",
    ),
    (
        ABILITY_CELESTISCHER_KREUZFAHRER,
        "Celestischer Kreuzfahrer",
        "Erhält einen Verständnisbonus von +1 auf Angriffswürfe und RK gegen böse Externare und einen "
        "Volksbonus von +2 auf Fertigkeitswürfe für Wissen (Die Ebenen) und Zauberkunde, um böse Externare "
        "oder von ihnen erschaffene Gegenstände und Effekte zu identifizieren; kann diese Fertigkeiten dazu "
        "ungeübt nutzen. Dieses Volksmerkmal ersetzt Bewandert und Celestische Resistenz.",
    ),
    (
        ABILITY_ERHABENE_RESISTENZ,
        "Erhabene Resistenz",
        "Erhält Zauberresistenz 5 + Stufe gegen Zauber und zauberähnliche Fähigkeiten der Kategorie Böses "
        "sowie gegen alle Zauber und zauberähnlichen Fähigkeiten böser Externare. Dieses Volksmerkmal "
        "ersetzt Celestische Resistenz.",
    ),
    (
        ABILITY_HEILIGENSCHEIN,
        "Heiligenschein",
        "Kann beliebig oft als zauberähnliche Fähigkeit Licht auf den eigenen Kopf zentriert erschaffen und "
        "erhält dabei einen Situationsbonus auf Fertigkeitswürfe für Einschüchtern gegenüber bösen Kreaturen "
        "und auf Rettungswürfe gegen Blindheit, Blind und Geblendet. Dieses Volksmerkmal ersetzt Dunkelsicht.",
    ),
    (
        ABILITY_HIMMELSGEBOREN,
        "Himmelsgeboren",
        "Erhält einen Bonus von +2 auf Fertigkeitswürfe für Wissen (Die Ebenen) und wirkt Zauber der "
        "Kategorien Gutes oder Licht mit ZS +1. Dieses Volksmerkmal ersetzt Bewandert und Zauberähnliche "
        "Fähigkeit.",
    ),
    (
        ABILITY_SPROSS_DER_MENSCHHEIT,
        "Spross der Menschheit",
        "Zählt als Externar (Einheimischer) und Humanoider (Mensch) hinsichtlich aller Effekte, die sich auf "
        "die Volkszugehörigkeit beziehen, einschließlich Talentvoraussetzungen und Zaubern, welche Humanoide "
        "betreffen. Kann als Mensch durchgehen, ohne sich verkleiden zu müssen. Dieses Volksmerkmal ersetzt "
        "die Sprache Celestisch und verändert die Unterart Einheimischer.",
    ),
    (
        ABILITY_SPRACHENMEISTER,
        "Sprachenmeister",
        "Erhält einen Bonus von +2 auf Fertigkeitswürfe für Motiv erkennen und Sprachenkunde. Für jeden "
        "Fertigkeitsrang in Sprachenkunde erlernt er zwei Sprachen. Dieses Volksmerkmal ersetzt Bewandert.",
    ),
    (
        ABILITY_UNSTERBLICHER_GEIST,
        "Unsterblicher Geist",
        "Erhält Resistenz 5 gegen negativen Energieschaden, verliert keine TP durch negative Stufen und "
        "erhält einen Volksbonus von +2 auf Rettungswürfe gegen Todeseffekte, Lebenskraftentzug, negative "
        "Energie und Zauber oder zauberähnliche Fähigkeiten der Schule der Nekromantie. Dieses Volksmerkmal "
        "ersetzt Celestische Resistenz.",
    ),
    (
        ABILITY_UNSTERBLICHER_LEBENSFUNKE,
        "Unsterblicher Lebensfunke",
        "Erhält einen Bonus von +2 auf Fertigkeitswürfe für Wissen (Geschichte) und auf Rettungswürfe gegen "
        "Todeseffekte. Kann einmal am Tag als zauberähnliche Fähigkeit Schwächere Resistenz gegen Alterung "
        "wirken. Dieses Volksmerkmal ersetzt Bewandert und Zauberähnliche Fähigkeit.",
    ),
]

# (ability_id, is_alternate)
BASE_GRANTS: list[tuple[str, bool]] = [
    (ABILITY_WE_PLUS2, False),
    (ABILITY_CH_PLUS2, False),
    (ABILITY_EINHEIMISCHER_EXTERNAR, False),
    (ABILITY_MITTELGROSS, False),
    (ABILITY_NORMALE_BEWEGUNGSRATE, False),
    (ABILITY_BEWANDERT, False),
    (ABILITY_CELESTISCHE_RESISTENZ, False),
    (ABILITY_DUNKELSICHT, False),
    (ABILITY_TAGESLICHT, False),
    (ABILITY_CHARAKTERSTARK, True),
    (ABILITY_CELESTISCHER_KREUZFAHRER, True),
    (ABILITY_ERHABENE_RESISTENZ, True),
    (ABILITY_HEILIGENSCHEIN, True),
    (ABILITY_HIMMELSGEBOREN, True),
    (ABILITY_SPROSS_DER_MENSCHHEIT, True),
    (ABILITY_SPRACHENMEISTER, True),
    (ABILITY_UNSTERBLICHER_GEIST, True),
    (ABILITY_UNSTERBLICHER_LEBENSFUNKE, True),
]

# (alternate ability_id, replaced ability_id)
REPLACEMENTS: list[tuple[str, str]] = [
    (ABILITY_CHARAKTERSTARK, ABILITY_TAGESLICHT),
    (ABILITY_CELESTISCHER_KREUZFAHRER, ABILITY_BEWANDERT),
    (ABILITY_CELESTISCHER_KREUZFAHRER, ABILITY_CELESTISCHE_RESISTENZ),
    (ABILITY_ERHABENE_RESISTENZ, ABILITY_CELESTISCHE_RESISTENZ),
    (ABILITY_HEILIGENSCHEIN, ABILITY_DUNKELSICHT),
    (ABILITY_HIMMELSGEBOREN, ABILITY_BEWANDERT),
    (ABILITY_HIMMELSGEBOREN, ABILITY_TAGESLICHT),
    (ABILITY_SPROSS_DER_MENSCHHEIT, ABILITY_EINHEIMISCHER_EXTERNAR),
    (ABILITY_SPRACHENMEISTER, ABILITY_BEWANDERT),
    (ABILITY_UNSTERBLICHER_GEIST, ABILITY_CELESTISCHE_RESISTENZ),
    (ABILITY_UNSTERBLICHER_LEBENSFUNKE, ABILITY_BEWANDERT),
    (ABILITY_UNSTERBLICHER_LEBENSFUNKE, ABILITY_TAGESLICHT),
]

# (class_name, description) — verbatim PRD text.
FAVORED_CLASS_BONUS_ENTRIES: list[tuple[str, str]] = [
    ("Barde", "Wähle einen Bardenauftritt, dessen Effekte einen Bonus von +1/2 auf die effektive Bardenstufe erhalten."),
    ("Hexenmeister", "Addiere +1/4 auf die Zauberstufe des Hexenmeisters, wenn er Zauber der Kategorie Gutes wirkt."),
    (
        "Kleriker",
        "Addiere +1/2 auf den Schaden positiver Energie, die der Kleriker gegen Untote einsetzt, sowie auf den "
        "Schaden von Gesinnung fokussieren gegenüber bösen Externaren.",
    ),
    ("Mystiker", "Addiere +1/2 auf die effektive Mystikerstufe hinsichtlich der Effekte einer seiner Offenbarungen."),
    ("Paladin", "Addiere +1/6 auf den Moralbonus auf Rettungswürfe, den die Auren des Paladins generieren."),
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
    # ---- base_races.json ----
    races = load("base_races.json")
    races = [r for r in races if r["id"] != AASIMAR_RACE_ID]
    races.append(
        {
            "id": AASIMAR_RACE_ID,
            "code": "aasimar",
            "name": "Aasimar",
            "short_description": "+2 WE, +2 CHA; Einheimischer Externar; Bewandert; Celestische Resistenz; "
            "Dunkelsicht; Tageslicht.",
            "creature_type": "Externar",
            "source": "Ausbauregeln III: Völker",
        }
    )
    save("base_races.json", races)

    # ---- base_race_abilities.json ----
    abilities = load("base_race_abilities.json")
    new_ability_ids = {aid for aid, _name, _desc in NEW_ABILITIES}
    abilities = [a for a in abilities if a["id"] not in new_ability_ids]
    for aid, name, desc in NEW_ABILITIES:
        abilities.append({"id": aid, "name": name, "description": desc})
    save("base_race_abilities.json", abilities)

    # ---- race_ability_grants.json ----
    grants = load("race_ability_grants.json")
    grants = [g for g in grants if g["race_id"] != AASIMAR_RACE_ID]
    for ability_id, is_alternate in BASE_GRANTS:
        grants.append(
            {
                "id": uid("aasimar-grant", ability_id),
                "race_id": AASIMAR_RACE_ID,
                "ability_id": ability_id,
                "is_alternate": is_alternate,
            }
        )
    save("race_ability_grants.json", grants)

    # ---- race_ability_replacements.json ----
    replacements = load("race_ability_replacements.json")
    replacements = [r for r in replacements if r["base_race_id"] != AASIMAR_RACE_ID]
    for ability_id, replaces_id in REPLACEMENTS:
        replacements.append(
            {
                "id": uid("aasimar-replacement", ability_id, replaces_id),
                "base_race_id": AASIMAR_RACE_ID,
                "ability_id": ability_id,
                "replaces_ability_id": replaces_id,
            }
        )
    save("race_ability_replacements.json", replacements)

    # ---- favored class bonus: same shape as `import_ork.py` ----
    classes = load("base_classes.json")
    class_id_by_name = {c["name"]: c["id"] for c in classes}
    for name, _description in FAVORED_CLASS_BONUS_ENTRIES:
        assert name in class_id_by_name, f"no seeded BaseClass named {name!r}"

    groups = load("base_class_option_groups.json")
    choices = load("base_class_option_choices.json")
    fcb_abilities = load("base_class_abilities.json")
    fcb_grants = load("base_class_ability_grants.json")
    existing_ability_ids = {a["id"] for a in fcb_abilities}

    # Reuse a class's existing `favored_class_bonus` group (another race may
    # already have created it) — unique on `(base_class_id, key)`.
    existing_group_id_by_class = {
        g["base_class_id"]: g["id"] for g in groups if g["key"] == "favored_class_bonus"
    }

    own_grant_ids = {uid("aasimar-fcb-grant", class_id_by_name[name]) for name, _ in FAVORED_CLASS_BONUS_ENTRIES}
    fcb_grants = [g for g in fcb_grants if g["id"] not in own_grant_ids]
    own_choice_ids = {uid("aasimar-fcb-choice", class_id_by_name[name]) for name, _ in FAVORED_CLASS_BONUS_ENTRIES}
    choices = [c for c in choices if c["id"] not in own_choice_ids]

    for class_name, description in FAVORED_CLASS_BONUS_ENTRIES:
        class_id = class_id_by_name[class_name]
        group_id = existing_group_id_by_class.get(class_id)
        if group_id is None:
            group_id = uid("aasimar-fcb-group", class_id)
            groups.append(
                {
                    "id": group_id,
                    "base_class_id": class_id,
                    "key": "favored_class_bonus",
                    "label": "Bevorzugte Klasse",
                    "max_choices": 20,
                }
            )
            existing_group_id_by_class[class_id] = group_id

        choice_id = uid("aasimar-fcb-choice", class_id)
        choices.append(
            {
                "id": choice_id,
                "group_id": group_id,
                "name": f"Aasimar ({class_name})",
                "min_level": None,
                "requires_choice_id": None,
                "race_id": AASIMAR_RACE_ID,
            }
        )

        ability_id = uid("aasimar-fcb-ability", class_name)
        fcb_abilities = [a for a in fcb_abilities if a["id"] != ability_id]
        fcb_abilities.append({"id": ability_id, "name": f"Aasimar ({class_name})", "description": description})
        existing_ability_ids.add(ability_id)

        fcb_grants.append(
            {
                "id": uid("aasimar-fcb-grant", class_id),
                "base_class_id": class_id,
                "ability_id": ability_id,
                "option_choice_id": choice_id,
                "level": 1,
            }
        )

    save("base_class_option_groups.json", groups)
    save("base_class_option_choices.json", choices)
    save("base_class_abilities.json", fcb_abilities)
    save("base_class_ability_grants.json", fcb_grants)

    print("Aasimar race id:", AASIMAR_RACE_ID)
    print("Race abilities imported:", len(NEW_ABILITIES))
    print("Race ability grants:", len(BASE_GRANTS))
    print("Race ability replacements:", len(REPLACEMENTS))
    print("Favored-class-bonus entries imported:", len(FAVORED_CLASS_BONUS_ENTRIES))
    print("Done.")


if __name__ == "__main__":
    main()
