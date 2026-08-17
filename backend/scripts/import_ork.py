"""Import the Orc ("Ork") race, including its Advanced Race Guide alternate
racial traits and alternate favored-class-bonus options, from
http://prd.5footstep.de/AusbauregelnIIIVoelker/UngewoehnlicheVoelker/Orks
into the seed JSON files.

Scope (per project owner decision, 2026-08-17): race + racial traits +
alternate racial traits + favored-class-bonus options only. The page's
"Neue Volksregeln" section (new equipment, a weapon special ability, a
wondrous item, four new spells) is explicitly out of scope for this pass.
The page's two racial archetypes (Narbiger Hexendoktor/Hexe, Raufbold/
Kämpfer) and nine racial feats are imported separately, by
`import_ork_archetypes.py`/`import_ork_feats.py` — this script only needs
the race's own id, which both of those also depend on.

Racial traits, fixed (not flex) ability score modifiers: unlike Halb-Ork
(free +2 to any one score) and every other race seeded so far, the PRD gives
Orcs a fixed +4 STÄ/-2 IN/-2 WE/-2 CHA, the same shape Elf/Halbling already
use for their own fixed modifiers. This needed three new ability-score
catalog rows/handlers (`rules/race_abilities.py`: `ABILITY_ST_PLUS4`,
`ABILITY_IN_MINUS2`, `ABILITY_WE_MINUS2`) plus filling in the
`ABILITY_CH_MINUS2` catalog row, whose handler already existed in that
module but had no matching `base_race_abilities.json` row yet (nothing
seeded had used it until now).

Not modeled (consistent with every other seeded race, not a gap specific to
Orcs): languages (no race's bonus-language list is tracked anywhere in this
schema yet) and Lichtempfindlichkeit's actual combat penalty (no
lighting/vision system exists to compute it against yet) — both stay
flavor-only `BaseRaceAbility` rows with no `HANDLERS` entry, same as e.g.
Elf's Dämmersicht.

Alternate racial traits: Bestialisch and Schnüffler each replace two of the
race's own traits (Waffenvertrautheit and/or Wildheit) — modeled as two
`RaceAbilityReplacement` rows per trait pointing at the same `ability_id`,
the same "one ability, multiple replaced things" shape
`import_barbar_seereauber.py` uses at the class-ability level for
Zweifacher Trick. Bestialisch's text also says it replaces "Sprachen", which
isn't modeled for any race yet (see above) — only its Waffenvertrautheit
replacement is recorded.

Favored class bonus: the source page lists seven classes (Alchemist,
Barbar, Druide, Hexe, Kämpfer, Ritter, Waldläufer). Alchemist and Ritter
have no seeded `BaseClass` row in this app at all — skipped, not guessed,
same precedent `import_favored_class_bonus_halbork.py` set. Unlike that
script, "Entfesselter Barbar" is deliberately NOT duplicated alongside
Barbar here — that duplication was done for Half-Orc on the project owner's
explicit instruction, not a standing convention, and the Orc source page
itself only ever says "Barbar".

Run with the project venv active (this only writes the fixture JSON files,
it doesn't touch the database — run the seed scripts afterward):
    cd backend && python scripts/import_ork.py
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

# Grant/replacement/choice row ids only — derived, not hand-frozen (nothing
# outside the fixtures links to these). The race id and every
# `BaseRaceAbility` id below (including the three new ability-score ids and
# the pre-existing `ABILITY_CH_MINUS2` id) ARE hand-frozen, matching
# `rules/race_abilities.py`'s own constants — see that module.
ID_NAMESPACE = uuid.UUID("d3b3a3d1-0c1a-4e9a-9c3a-1f6f9a2b7e41")

ORK_RACE_ID = "3d007d77-60e2-4f01-b682-8a3a129a49da"

# ---- ability-score bonuses (fixed, not flex) ----
ABILITY_ST_PLUS4 = "c73e6c2e-6d66-459e-8789-bd5510d2a155"
ABILITY_IN_MINUS2 = "900f8f27-d0d8-43ec-a8a8-8e2473e8b2c8"
ABILITY_WE_MINUS2 = "71cd3345-96eb-4b2d-9d43-365a4d25af77"
ABILITY_CH_MINUS2 = "15891f93-77b5-4ee2-85c2-3486fc7365e5"  # pre-existing handler, new catalog row

# ---- reused catalog rows (already seeded for other races) ----
ABILITY_MITTELGROSS = "c98915e3-0ade-4fd4-a203-baed02fdfc7e"
ABILITY_NORMALE_BEWEGUNGSRATE = "2e0186d5-e532-4532-b7f7-b4c6f4834bde"
ABILITY_DUNKELSICHT = "6670c6fd-ac89-468b-8072-3f6c68d43a35"

# ---- new flavor-only catalog rows (own to Orc) ----
ABILITY_ORK_UNTERART = "313b33b4-9e3f-4b77-a6ee-6b64e9dd5510"
ABILITY_LICHTEMPFINDLICHKEIT = "105c39ed-5e6b-4f9c-b2fa-d34e2a33c670"
ABILITY_WAFFENVERTRAUTHEIT_ORKS = "c22e9e02-b756-4dcb-85a5-e05882034027"
ABILITY_WILDHEIT = "c99b58d6-e782-4934-b315-36ae31fb7342"

# ---- alternate racial traits ----
ABILITY_BESTIALISCH = "9da791dd-edd6-4d84-ae97-2494b37acfe4"
ABILITY_BESUDELT = "f9cc6a0d-7fd7-44ee-b0ae-8a75894eb3b0"
ABILITY_SCHNUEFFLER = "487e7964-3812-4297-af19-ed74a8d7d968"
ABILITY_SONNENANBETER = "7f163f65-01bf-46cc-86d4-e0e1d5bb95ec"

NEW_ABILITIES: list[tuple[str, str, str]] = [
    (ABILITY_ST_PLUS4, "+4 auf Stärke", "+4 auf Stärke."),
    (ABILITY_IN_MINUS2, "-2 auf Intelligenz", "-2 auf Intelligenz."),
    (ABILITY_WE_MINUS2, "-2 auf Weisheit", "-2 auf Weisheit."),
    (ABILITY_CH_MINUS2, "-2 auf Charisma", "-2 auf Charisma."),
    (ABILITY_ORK_UNTERART, "Ork (Unterart)", "Orks sind Humanoide der Unterart Ork."),
    (
        ABILITY_LICHTEMPFINDLICHKEIT,
        "Lichtempfindlichkeit",
        "Orks sind im hellen Sonnenlicht und dem Wirkungsradius von Tageslicht geblendet.",
    ),
    (
        ABILITY_WAFFENVERTRAUTHEIT_ORKS,
        "Waffenvertrautheit (Orks)",
        "Ist geübt im Umgang mit der Zweihändigen Axt und dem Krummschwert und behandelt jede Waffe, "
        "die als orkisch bezeichnet wird, als Kriegswaffe.",
    ),
    (
        ABILITY_WILDHEIT,
        "Wildheit",
        "Kann bei Bewusstsein bleiben und sogar noch weiterkämpfen, wenn die Trefferpunkte unter 0 TP "
        "fallen. Bei 0 TP oder weniger ist der Charakter wankend und verliert pro Runde den üblichen 1 TP.",
    ),
    (
        ABILITY_BESTIALISCH,
        "Bestialisch",
        "Erhält Überlebenskunst als Klassenfertigkeit und einen Volksbonus von +1 auf "
        "Nahkampfwaffenangriffe und -schadenswürfe, wenn er sich im negativen Trefferpunktebereich "
        "befindet. Dieses Volksmerkmal ersetzt Waffenvertrautheit und Sprachen.",
    ),
    (
        ABILITY_BESUDELT,
        "Besudelt",
        "Erhält einen Volksbonus von +2 auf Rettungswürfe gegen Kränkelnd, Übelkeit und Krankheit. "
        "Dieses Volksmerkmal ersetzt Wildheit.",
    ),
    (
        ABILITY_SCHNUEFFLER,
        "Schnüffler",
        "Erhält eine schwächere Version der Fähigkeit Geruchssinn – die Reichweite beträgt nur die "
        "Hälfte. Dieses Volksmerkmal ersetzt Waffenvertrautheit und Wildheit.",
    ),
    (
        ABILITY_SONNENANBETER,
        "Sonnenanbeter",
        "Erleidet einen Malus von -2 auf alle Fernkampfangriffswürfe. Dieses Volksmerkmal ersetzt "
        "Lichtempfindlichkeit.",
    ),
]

# (ability_id, is_alternate)
BASE_GRANTS: list[tuple[str, bool]] = [
    (ABILITY_ST_PLUS4, False),
    (ABILITY_IN_MINUS2, False),
    (ABILITY_WE_MINUS2, False),
    (ABILITY_CH_MINUS2, False),
    (ABILITY_ORK_UNTERART, False),
    (ABILITY_MITTELGROSS, False),
    (ABILITY_NORMALE_BEWEGUNGSRATE, False),
    (ABILITY_DUNKELSICHT, False),
    (ABILITY_LICHTEMPFINDLICHKEIT, False),
    (ABILITY_WAFFENVERTRAUTHEIT_ORKS, False),
    (ABILITY_WILDHEIT, False),
    (ABILITY_BESTIALISCH, True),
    (ABILITY_BESUDELT, True),
    (ABILITY_SCHNUEFFLER, True),
    (ABILITY_SONNENANBETER, True),
]

# (alternate ability_id, replaced ability_id)
REPLACEMENTS: list[tuple[str, str]] = [
    (ABILITY_BESTIALISCH, ABILITY_WAFFENVERTRAUTHEIT_ORKS),
    (ABILITY_BESUDELT, ABILITY_WILDHEIT),
    (ABILITY_SCHNUEFFLER, ABILITY_WAFFENVERTRAUTHEIT_ORKS),
    (ABILITY_SCHNUEFFLER, ABILITY_WILDHEIT),
    (ABILITY_SONNENANBETER, ABILITY_LICHTEMPFINDLICHKEIT),
]

# (class_name, description) — verbatim PRD text, same convention
# `import_favored_class_bonus_halbork.py` uses.
FAVORED_CLASS_BONUS_ENTRIES: list[tuple[str, str]] = [
    ("Barbar", "Addiere +1 Runde zur Anzahl der täglichen Runden an Kampfrausch."),
    (
        "Druide",
        "Addiere +1/2 auf den Schaden der natürlichen Angriffe des Tiergefährten des Druiden.",
    ),
    (
        "Hexe",
        "Addiere einen Zauber der Zauberliste der Hexe zum Hexenvertrauten. Der Grad dieses Zaubers "
        "muss niedriger sein als der höchstgradigste Hexenzauber, den die Hexe wirken kann. Sollte die "
        "Hexe jemals ihren Vertrauten ersetzen, kennt auch der neue Vertraute diese Bonuszauber.",
    ),
    (
        "Kämpfer",
        "Addiere +2 auf den effektiven Konstitutionswert des Kämpfers, um zu bestimmen, wann er "
        "aufgrund negativer Trefferpunkte stirbt.",
    ),
    (
        "Waldläufer",
        "Addiere +1 TP zu den Trefferpunkten des Tiergefährten des Waldläufers. Sollte er jemals seinen "
        "Tiergefährten ersetzen, erhält der neue Tiergefährte diese zusätzlichen Trefferpunkte.",
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
    # ---- base_races.json ----
    races = load("base_races.json")
    races = [r for r in races if r["id"] != ORK_RACE_ID]
    races.append(
        {
            "id": ORK_RACE_ID,
            "code": "ork",
            "name": "Ork",
            "short_description": "+4 STÄ, −2 IN, −2 WE, −2 CHA; Dunkelsicht; Lichtempfindlichkeit; "
            "Wildheit; Waffenvertrautheit.",
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
    grants = [g for g in grants if g["race_id"] != ORK_RACE_ID]
    for ability_id, is_alternate in BASE_GRANTS:
        grants.append(
            {
                "id": uid("ork-grant", ability_id),
                "race_id": ORK_RACE_ID,
                "ability_id": ability_id,
                "is_alternate": is_alternate,
            }
        )
    save("race_ability_grants.json", grants)

    # ---- race_ability_replacements.json ----
    replacements = load("race_ability_replacements.json")
    own_replacement_ids = {uid("ork-replacement", aid, rid) for aid, rid in REPLACEMENTS}
    replacements = [r for r in replacements if r["id"] not in own_replacement_ids]
    for ability_id, replaces_id in REPLACEMENTS:
        replacements.append(
            {
                "id": uid("ork-replacement", ability_id, replaces_id),
                "base_race_id": ORK_RACE_ID,
                "ability_id": ability_id,
                "replaces_ability_id": replaces_id,
            }
        )
    save("race_ability_replacements.json", replacements)

    # ---- favored class bonus: base_class_option_groups/choices,
    # base_class_abilities, base_class_ability_grants ----
    classes = load("base_classes.json")
    class_id_by_name = {c["name"]: c["id"] for c in classes}
    for name, _description in FAVORED_CLASS_BONUS_ENTRIES:
        assert name in class_id_by_name, f"no seeded BaseClass named {name!r}"

    groups = load("base_class_option_groups.json")
    choices = load("base_class_option_choices.json")
    fcb_abilities = load("base_class_abilities.json")
    fcb_grants = load("base_class_ability_grants.json")
    existing_ability_ids = {a["id"] for a in fcb_abilities}

    # `favored_class_bonus` is one shared `BaseClassOptionGroup` per class
    # (unique on `(base_class_id, key)`) — Halb-Ork's import already created
    # it for several of these classes, so reuse that row instead of adding a
    # second, colliding group; only classes with no favored-class-bonus
    # group at all yet (from any race) get a newly created one here.
    existing_group_id_by_class = {
        g["base_class_id"]: g["id"] for g in groups if g["key"] == "favored_class_bonus"
    }

    own_grant_ids = {uid("ork-fcb-grant", class_id_by_name[name]) for name, _ in FAVORED_CLASS_BONUS_ENTRIES}
    fcb_grants = [g for g in fcb_grants if g["id"] not in own_grant_ids]

    for class_name, description in FAVORED_CLASS_BONUS_ENTRIES:
        class_id = class_id_by_name[class_name]
        group_id = existing_group_id_by_class.get(class_id)
        if group_id is None:
            group_id = uid("ork-fcb-group", class_id)
            groups.append(
                {
                    "id": group_id,
                    "base_class_id": class_id,
                    "key": "favored_class_bonus",
                    "label": "Bevorzugte Klasse",
                    "max_choices": 20,
                }
            )

        choice_id = uid("ork-fcb-choice", class_id)
        choices.append(
            {
                "id": choice_id,
                "group_id": group_id,
                "name": f"Ork ({class_name})",
                "min_level": None,
                "requires_choice_id": None,
                "race_id": ORK_RACE_ID,
            }
        )

        ability_id = uid("ork-fcb-ability", class_name)
        if ability_id not in existing_ability_ids:
            fcb_abilities.append({"id": ability_id, "name": f"Ork ({class_name})", "description": description})
            existing_ability_ids.add(ability_id)

        fcb_grants.append(
            {
                "id": uid("ork-fcb-grant", class_id),
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

    print("Ork race id:", ORK_RACE_ID)
    print("Race abilities imported:", len(NEW_ABILITIES))
    print("Race ability grants:", len(BASE_GRANTS))
    print("Race ability replacements:", len(REPLACEMENTS))
    print("Favored-class-bonus entries imported:", len(FAVORED_CLASS_BONUS_ENTRIES))
    print("Done.")


if __name__ == "__main__":
    main()
