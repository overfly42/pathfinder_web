"""The Druide archetypes Bärenschamane and Löwenschamane (Expertenregeln,
http://prd.5footstep.de/Expertenregeln/Klassen/Grundklassen/Druide/
Tierschamanen/{Baerenschamane,Loewenschamane}; the shared rules are spelled
out under the Bärenschamane, the others say "funktioniert wie beim
Bärenschamanen"). Fetched 2026-10-17; texts quoted below.

Per archetype (`SHAMANS`):
- **Bund mit der Natur**: a companion must be the totem animal — the
  archetype's own trigger "Tiergefährte (<Archetyp>)" replaces the Druide's
  "Tiergefährte (Druide)" grant on the same `bond` choice, with its own
  companion slot (only the totem species) and level source
  (`build_companion_level_sources.py`, Druide level). A domain must come
  from the archetype's list: the Naturdomäne choices are scoped with the
  new `only_for_archetype_ids`/`excluded_for_archetype_ids`; domains the
  Druide doesn't have (Schutz, Stärke, Adel, Herrlichkeit, Sonne) are added
  as Naturdomäne choices mirroring the Kleriker domain's grants, like
  `import_druide.py` does for the seven nature domains.
- **Tierempathie**: +4 with the totem animals — a descriptive addition.
- **Totemverwandlung** (2nd): a pool of Druide-level minutes per day
  ("Totemverwandlung (<Archetyp>)") plus one activatable ability per aspect
  that spends one minute (`rules/classes/druide.py`: `POOL_SOURCE_ID`,
  `POOL_COST_AT_ACTIVATION`, 10 rounds).
- **Totemtier herbeizaubern** (5th): descriptive, replaces Tausend Gesichter.
- **Tiergestalt** (6th, Druide level −2): replaces the Druide's Tiergestalt.
- **Bonustalent** (9th, 13th, 17th): a closed list, prerequisites still
  required; replaces Immunität gegen Gifte. The Löwenschamane's
  "Fertigkeitsfokus (Akrobatik)" can only be offered as Fertigkeitsfokus
  (a closed-list option names a feat, not its sub-choice).

Run after `import_druide.py`, `import_companion_species.py` and
`import_kleriker.py` (it reads their rows), then rebuild the level sources:
    cd backend && python scripts/import_druide_tierschamanen.py
    python scripts/build_companion_level_sources.py
    python -m app.seed.class_seed && python -m app.seed.class_option_seed
    python -m app.seed.class_ability_seed && python -m app.seed.class_ability_option_seed
    python -m app.seed.companion_seed
"""

from __future__ import annotations

import json
import uuid
from pathlib import Path

SEED_DIR = Path(__file__).resolve().parent.parent / "app" / "fixtures" / "seed"
ID_NAMESPACE = uuid.UUID("8a3d5f7b-1c9e-4b2a-8d6f-4e0c2a9b7d31")

DRUIDE_ID = "2835c712-7129-41fe-a61e-8ef05de2e0cf"
KLERIKER_ID = "1e6e60de-d72f-4910-b19d-55ca11e14190"
KLERIKER_DOMAIN_GROUP_ID = "7b82d11f-eae8-4e79-bb43-aaad60d728ff"
NATURE_DOMAIN_GROUP_ID = "8439dd24-4d87-537b-9b0e-3ef0c338d656"
BOND_TIERGEFAEHRTE_CHOICE_ID = "dbea3f3f-b0e0-42c2-8a49-52f6f4bc67df"
BOND_DOMAENE_CHOICE_ID = "bde0d2ad-a8b4-4c13-9153-bbcd60238cfb"
NATURE_DOMAINS = [
    "Domäne der Erde", "Domäne des Feuers", "Domäne der Luft", "Domäne der Pflanzen", "Domäne der Tiere",
    "Domäne des Wassers", "Domäne des Wetters",
]

TOTEMTIER_HERBEIZAUBERN_BAER = (
    "(ÜF) Ab der 5. Stufe kann der Bärenschamane den Zauber Verbündeten der Natur herbeizaubern als "
    "Standard-Aktion wirken, wenn er Bären herbeizaubert. Herbei gezauberte Bären erhalten temporäre "
    "Trefferpunkte in Höhe seiner Stufe als Druide. Er kann die Schablone Junge Kreatur auf seine Bären anwenden, "
    "um den Grad der erforderlichen Herbeizauberung um -1 zu senken. Ebenso kann er Bären mit der Schablone "
    "Verbesserte Kreatur oder Riesige Kreatur herbeizaubern, indem er den Grad der Herbeizauberung um +1 erhöht. "
    "Er kann auch Bären mit beiden Schablonen herbeizaubern, indem er eine Herbeizauberung wirkt, deren Grad um "
    "+2 höher ist. Dieses Klassenmerkmal ersetzt Tausend Gesichter."
)
TOTEMVERWANDLUNG_RULES = (
    "Während er der Totemverwandlung untersteht, kann er normal sprechen und beliebig oft Mit Tieren sprechen "
    "({speak}) wirken. Auf der 2. Stufe ist der Einsatz dieser Fähigkeit eine Standard-Aktion, ab der 7. Stufe "
    "eine Bewegungsaktion und ab der 12. Stufe eine Schnelle Aktion. Er kann diese Fähigkeit täglich für eine "
    "Anzahl von Minuten in Höhe seiner Stufe als Druide einsetzen. Diese Minuten müssen nicht aufeinander folgen, "
    "werden aber in Einheiten von jeweils 1 Minute berechnet. Dies ist ein Verwandlungseffekt und kann nicht "
    "benutzt werden, wenn der Druide einen anderen Verwandlungseffekt wie beispielsweise Tiergestalt einsetzt."
)

SHAMANS = [
    {
        "key": "baer",
        "name": "Bärenschamane",
        "totem": "Bären",  # genitive: "einen Aspekt des Bären"
        "species": ["Bär"],
        "domains": ["Domäne der Erde", "Domäne des Schutzes", "Domäne der Stärke", "Domäne der Tiere"],
        "bond_text": (
            "Ein Bärenschamane, der einen Tierbegleiter erwählt, muss einen Bären wählen. Falls er eine Domäne "
            "wählt, stehen ihm Erde, Schutz, Stärke und Tiere zur Auswahl."
        ),
        "empathy_text": "(AF) Der Bärenschamane kann Tierempathie bei Bären und Vielfraßen als Volle Aktion mit "
        "einem Bonus von +4 nutzen.",
        "speak": "nur Säugetiere",
        "aspects": [
            ("Bewegung", "Verbesserungsbonus von +3 m auf die Bewegungsrate an Land, Volksbonus von +4 auf "
                         "Fertigkeitswürfe für Schwimmen."),
            ("Sinne", "Dämmersicht, Geruchssinn."),
            ("Abhärtung", "Bonus von +2 auf natürliche RK, Talent Ausdauer."),
            ("Natürliche Waffen", "Biss [1W6] und 2 Klauen [1W4] bei einem Mittelgroßen Schamanen, KMB +2 im "
                                  "Ringkampf."),
        ],
        "summon_text": TOTEMTIER_HERBEIZAUBERN_BAER,
        "wild_shape_text": (
            "(ÜF) Der Bärenschamane erhält diese Fähigkeit erst auf der 6. Stufe. Seine effektive Druidenstufe für "
            "diese Fähigkeit ist seine Stufe als Druide -2. Sollte er sich in einen Bären verwandeln, zählt seine "
            "Stufe als Druide +2."
        ),
        "feats": ["Abhärtung", "Ausdauer", "Große Zähigkeit", "Unverwüstlich", "Verbesserte Große Zähigkeit"],
        "feat_text": (
            "Auf der 9. Stufe und dann alle weiteren vier Stufen als Druide erhält der Bärenschamane eines der "
            "folgenden Talente: Abhärtung, Ausdauer, Große Zähigkeit, Unverwüstlich, Verbesserte Große Zähigkeit. "
            "Er muss die Voraussetzungen des jeweiligen Bonustalentes erfüllen. Dieses Klassenmerkmal ersetzt "
            "Immunität gegen Gift."
        ),
    },
    {
        "key": "loewe",
        "name": "Löwenschamane",
        "totem": "Löwen",
        "species": ["Raubkatze, Groß (Löwe, Tiger)"],
        "domains": ["Domäne des Adels", "Domäne der Herrlichkeit", "Domäne der Sonne", "Domäne der Tiere"],
        "bond_text": (
            "Ein Löwenschamane, der einen Tierbegleiter erwählt, muss einen Löwen wählen. Falls er eine Domäne "
            "wählt, stehen ihm Adel, Herrlichkeit, Sonne und Tiere zur Auswahl."
        ),
        "empathy_text": "(AF) Der Löwenschamane kann Tierempathie bei katzenartigen Wesen als Volle Aktion mit "
        "einem Bonus von +4 nutzen.",
        "speak": "nur katzenartige Wesen",
        "aspects": [
            ("Bewegung", "Bewegungsrate +6 m an Land."),
            ("Sinne", "Dämmersicht, Geruchssinn."),
            ("Natürliche Waffen", "Biss [1W4] und 2 Klauen [1W4] bei einem Mittelgroßen Schamanen, Krallen, Bonus "
                                  "von +2 im Ringkampf."),
        ],
        "summon_text": (
            "(ÜF) Ab der 5. Stufe kann der Löwenschamane den Zauber Verbündeten der Natur herbeizaubern als "
            "Standard-Aktion wirken, wenn er Katzen herbeizaubert. Diese herbeigezauberten Kreaturen erhalten "
            "temporäre Trefferpunkte in Höhe der Stufe des Druiden. Ansonsten funktioniert die Fähigkeit wie beim "
            "Bärenschamanen (Schablonen Junge/Verbesserte/Riesige Kreatur); sie ersetzt Tausend Gesichter."
        ),
        "wild_shape_text": (
            "(ÜF) Der Löwenschamane erhält diese Fähigkeit erst auf der 6. Stufe. Seine effektive Druidenstufe für "
            "diese Fähigkeit ist seine Stufe als Druide -2. Sollte er sich in eine katzenartige Form verwandeln, "
            "zählt seine Stufe als Druide +2."
        ),
        "feats": ["Ausfallschritt", "Ausweichen", "Eiserner Wille", "Fertigkeitsfokus", "Verbesserter Eiserner Wille"],
        "feat_text": (
            "Auf der 9. Stufe und dann alle weiteren vier Stufen als Druide erhält der Löwenschamane eines der "
            "folgenden Talente: Ausfallschritt, Ausweichen, Eiserner Wille, Fertigkeitsfokus (Akrobatik) oder "
            "Verbesserter Eiserner Wille. Er muss die Voraussetzungen des jeweiligen Bonustalentes erfüllen. Dieses "
            "Klassenmerkmal ersetzt Immunität gegen Gift."
        ),
    },
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
    classes = load("base_classes.json")
    abilities = load("base_class_abilities.json")
    grants = load("base_class_ability_grants.json")
    replacements = load("base_class_ability_replacements.json")
    feat_options = load("base_class_ability_feat_options.json")
    choices = load("base_class_option_choices.json")
    slot_grants = load("base_companion_slot_grants.json")
    slot_species = load("base_companion_slot_species.json")
    races = load("base_races.json")
    feat_id_by_name = {f["name"]: f["id"] for f in load("base_feats.json")}
    ability_name_by_id = {a["id"]: a["name"] for a in abilities}

    def druide_grant(ability_name: str, level: int, option_choice_id: str | None = None) -> str:
        matches = [
            g["id"]
            for g in grants
            if g["base_class_id"] == DRUIDE_ID
            and g["level"] == level
            and g["option_choice_id"] == option_choice_id
            and ability_name_by_id.get(g["ability_id"]) == ability_name
        ]
        assert len(matches) == 1, (ability_name, level, matches)
        return matches[0]

    # ---- Naturdomäne: archetype-only domains, mirrored from the Kleriker ----
    kleriker_choice_by_name = {c["name"]: c["id"] for c in choices if c["group_id"] == KLERIKER_DOMAIN_GROUP_ID}
    druide_choice_by_name = {c["name"]: c for c in choices if c["group_id"] == NATURE_DOMAIN_GROUP_ID}
    archetype_ids = {shaman["key"]: uid("archetype", shaman["key"]) for shaman in SHAMANS}
    all_domains = sorted(set(NATURE_DOMAINS) | {d for shaman in SHAMANS for d in shaman["domains"]})
    for domain in all_domains:
        allowed = [archetype_ids[s["key"]] for s in SHAMANS if domain in s["domains"]]
        excluded = [archetype_ids[s["key"]] for s in SHAMANS if domain not in s["domains"]]
        if domain in NATURE_DOMAINS:
            druide_choice_by_name[domain]["excluded_for_archetype_ids"] = excluded or None
            continue
        choice_id = uid("nature-domain", domain)
        choices.append(
            {
                "id": choice_id,
                "group_id": NATURE_DOMAIN_GROUP_ID,
                "name": domain,
                "min_level": None,
                "requires_choice_id": BOND_DOMAENE_CHOICE_ID,
                "race_id": None,
                "only_for_archetype_ids": allowed,
            }
        )
        kleriker_choice_id = kleriker_choice_by_name[domain]
        for grant in [g for g in grants if g["base_class_id"] == KLERIKER_ID and g["option_choice_id"] == kleriker_choice_id]:
            grants.append(
                {
                    "id": uid("domain-grant", grant["ability_id"], str(grant["level"]), choice_id),
                    "base_class_id": DRUIDE_ID,
                    "ability_id": grant["ability_id"],
                    "option_choice_id": choice_id,
                    "level": grant["level"],
                }
            )

    for shaman in SHAMANS:
        archetype_id = archetype_ids[shaman["key"]]
        name = shaman["name"]
        classes = [c for c in classes if c["id"] != archetype_id]
        classes.append(
            {
                "id": archetype_id,
                "name": name,
                "hit_dice": None,
                "arch_class_of": DRUIDE_ID,
                "casting_ability": None,
                "spell_tradition": None,
                "bab_progression": None,
                "fort_save": None,
                "ref_save": None,
                "wil_save": None,
                "skill_points_base": None,
            }
        )

        def ability(label: str, description: str, **extra) -> str:
            ability_id = uid("ability", shaman["key"], label)
            abilities[:] = [a for a in abilities if a["id"] != ability_id]
            abilities.append({"id": ability_id, "name": label, "description": description, **extra})
            ability_name_by_id[ability_id] = label
            return ability_id

        def grant(ability_id: str, level: int, option_choice_id: str | None = None) -> None:
            grants.append(
                {
                    "id": uid("grant", ability_id, str(level)),
                    "base_class_id": archetype_id,
                    "ability_id": ability_id,
                    "option_choice_id": option_choice_id,
                    "level": level,
                }
            )

        def replace(ability_id: str, replaced_grant_id: str) -> None:
            replacements.append(
                {
                    "id": uid("replacement", ability_id, replaced_grant_id),
                    "archetype_class_id": archetype_id,
                    "ability_id": ability_id,
                    "replaces_grant_id": replaced_grant_id,
                }
            )

        companion_id = ability(
            f"Tiergefährte ({name})",
            f"(AF) Der Tiergefährte des {name}n — nur {', '.join(shaman['species'])} — funktioniert wie der "
            "Tiergefährte des Druiden (effektive Druidenstufe = Druidenstufe).",
        )
        grant(companion_id, 1, BOND_TIERGEFAEHRTE_CHOICE_ID)
        replace(companion_id, druide_grant("Tiergefährte (Druide)", 1, BOND_TIERGEFAEHRTE_CHOICE_ID))
        grant(ability(f"Bund mit der Natur ({name})", shaman["bond_text"]), 1)
        grant(ability(f"Tierempathie ({name})", shaman["empathy_text"]), 1)

        pool_id = ability(
            f"Totemverwandlung ({name})",
            f"(AF) Ab der 2. Stufe kann der {name} einen Aspekt des {shaman['totem']} annehmen, dabei aber seine normale "
            "Gestalt beibehalten. Er erhält einen der folgenden Boni: "
            + "; ".join(f"{aspect} ({text.rstrip('.')})" for aspect, text in shaman["aspects"])
            + ". "
            + TOTEMVERWANDLUNG_RULES.format(speak=shaman["speak"]),
        )
        grant(pool_id, 2)
        for aspect, text in shaman["aspects"]:
            aspect_id = ability(
                f"Totemverwandlung: {aspect} ({name})",
                f"(AF) Aspekt der Totemverwandlung, 1 Minute aus dem Vorrat: {text}",
                is_persistent_effect=True,
                activation_scope="self",
                default_duration_rounds=10,
            )
            grant(aspect_id, 2)
            print(f"  aspect {aspect}: {aspect_id}")
        print(f"  pool: {pool_id}")

        summon_id = ability(f"Totemtier herbeizaubern ({name})", shaman["summon_text"])
        grant(summon_id, 5)
        replace(summon_id, druide_grant("Tausend Gesichter", 13))

        wild_shape_id = ability(f"Tiergestalt ({name})", shaman["wild_shape_text"])
        grant(wild_shape_id, 6)
        replace(wild_shape_id, druide_grant("Tiergestalt", 4))
        print(f"  wild shape: {wild_shape_id}")

        feat_id = ability(f"Bonustalent ({name})", shaman["feat_text"])
        for level in (9, 13, 17):
            grant(feat_id, level)
        replace(feat_id, druide_grant("Immunität gegen Gifte", 9))
        for feat_name in shaman["feats"]:
            feat_options.append(
                {
                    "id": uid("feat-option", feat_id, feat_name),
                    "ability_id": feat_id,
                    "option_choice_id": None,
                    "feat_type": None,
                    "feat_id": feat_id_by_name[feat_name],
                }
            )
        print(f"  bonus feat: {feat_id}")

        # The totem companion: own slot with only the totem species.
        slot_id = uid("slot", companion_id)
        slot_grants.append(
            {"id": slot_id, "class_ability_id": companion_id, "track": "animal_companion", "slot_key": "primary",
             "level_offset": 0, "divisor": 1, "minimum": None}
        )
        for species in shaman["species"]:
            race_id = next(r["id"] for r in races if r["name"] == species and r.get("companion_kind") == "animal_companion")
            slot_species.append(
                {"id": uid("slot-species", slot_id, race_id), "slot_grant_id": slot_id, "race_id": race_id,
                 "master_sizes": None, "min_level": None}
            )
        print(f"{name}: {archetype_id}, companion trigger {companion_id}")

    save("base_classes.json", classes)
    save("base_class_abilities.json", abilities)
    save("base_class_ability_grants.json", grants)
    save("base_class_ability_replacements.json", replacements)
    save("base_class_ability_feat_options.json", feat_options)
    save("base_class_option_choices.json", choices)
    save("base_companion_slot_grants.json", slot_grants)
    save("base_companion_slot_species.json", slot_species)


if __name__ == "__main__":
    main()
