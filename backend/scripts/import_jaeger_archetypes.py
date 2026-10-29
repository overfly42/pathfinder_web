"""The five Jäger archetypes from
https://prd.5footstep.de/Ausbauregeln-VI-Klassen/Archetypen/Jäger — Bruder
des Urzeitgefährten, Bruder des Ungeziefergefährten, Göttlicher Jäger,
Rudelführer, Wilder Jäger. Texts parsed from the live page at run time
(checked 2026-10-26), like `import_jaeger.py`; run that first (this script
looks up the Jäger's own grants by ability name and level).

Every "ersetzt X" is a `BaseClassAbilityReplacement` of the Jäger's grant(s)
of X — Tieraspekt means both Tieraspekt entries (the Jäger's own and the
companion's; the aspects are options, not grants). "Modifiziert
X" leaves X granted and adds the archetype's text as its own ability.

Per archetype:
- **Bruder des Urzeitgefährten**: Urzeitliche Verwandlung (1st, a pool of
  Jäger-level minutes; the evolutions themselves are text — no eidolon
  evolutions in the catalog), Urzeitlicher Kraftschub (8th, 1/day), Meister
  der Urzeit (20th).
- **Bruder des Ungeziefergefährten**: Ungeziefergefährte replaces
  "Tiergefährte (Jäger)" without a companion slot of its own — there are no
  vermin companion species in the catalog yet, so the companion can't be
  created (text only). Ungezieferempathie replaces the Tierempathie grant.
  Ungezieferaspekt (pool + effect with 15 aspect options, no companion
  entry) replaces Tieraspekt.
  Schwärme durchqueren replaces Unterholz durchqueren.
- **Göttlicher Jäger**: any alignment (`allowed_alignments` on the archetype
  row replaces the Jäger's "jede Neutrale"; the one-step-from-the-deity rule
  needs a deity model, same open item as the Kleriker). Wissen (Religion) as
  a class skill (`rules/classes/jaeger.py`'s `CLASS_SKILL_GRANTS`; removing
  Wissen (Gewölbekunde) has no mechanism — partial). Domäne (3rd) replaces
  all six Gemeinschaftstalente grants: a root-level option group
  `divine_hunter_domain` whose 33 choices (the Kleriker's domains — "eine
  der Domänen, die seine Gottheit verfügbar macht", no deity model) are
  `only_for_archetype_ids` the Göttlicher Jäger with `min_level` 3, so the
  wizards only show it to him from 3rd level; each choice mirrors the
  Kleriker domain's grants two levels later ("Jägerstufe -2"). The Tiere
  domain's 4th-level companion is replaced by its PRD substitute (two +1
  ability increases for the companion, text). The domain spells added to
  the known spells are text: a domain spell off the Jäger's list would have
  no grade to cast it at. Außerweltlicher Gefährte replaces Jägertaktiken.
- **Rudelführer**: Rudelbindung replaces "Tiergefährte (Jäger)" with its
  own trigger, companion slot (the Druide's species) and level source
  (`build_companion_level_sources.py`, Jäger level) — one companion at the
  full level works; splitting the level across several companions isn't
  modeled. Rudelaspekt "ersetzt Tieraspekt" but changes only what the
  companions get, so the Jäger keeps his Tieraspekt pool and aspects and
  Rudelaspekt is added as text. Gemeinschaftstalent (Rudelführer) modifies
  (text). Zweiter Rudelaspekt and Herr des Rudels replace their features.
- **Wilder Jäger**: Tiergefährtenlos replaces the companion trigger. Wilder
  Aspekt replaces Tieraspekt (pool and aspects), Jägertaktiken and Mit
  Meister sprechen; its twelve aspects are activatable with no duration and
  no pool. Genaues Ausmanövrieren (Wilder Jäger) modifies (text).
  Tiergestalt (4th, Druide Tiergestalt at Jäger level, animals only)
  replaces the three Bonustricks grants, both empathic links, Toten
  Tiergefährten erwecken and Nimrod. Rudel herbeizaubern replaces the
  Gemeinschaftstalente grants of 6th–18th (not 3rd).

Run with the project venv active (writes fixtures only; seed afterwards):
    cd backend && python scripts/import_jaeger_archetypes.py
    python scripts/build_companion_level_sources.py
    python -m app.seed.class_seed && python -m app.seed.class_option_seed
    python -m app.seed.class_ability_seed && python -m app.seed.class_ability_option_seed
    python -m app.seed.companion_seed
"""

from __future__ import annotations

import json
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from import_jaeger import ASPECTS, JAEGER_ID, apply_fixes, fetch_text, split_labeled  # noqa: E402

SEED_DIR = Path(__file__).resolve().parent.parent / "app" / "fixtures" / "seed"
URL = "https://prd.5footstep.de/Ausbauregeln-VI-Klassen/Archetypen/J%C3%A4ger"
ID_NAMESPACE = uuid.UUID("b5d81f3a-6c27-4e90-8a4d-1f7e3c9b2a68")

KLERIKER_ID = "1e6e60de-d72f-4910-b19d-55ca11e14190"
KLERIKER_DOMAIN_GROUP_ID = "7b82d11f-eae8-4e79-bb43-aaad60d728ff"
# The Kleriker's Tiere-domain companion ("Tiergefährte", granted at 4th).
TIERE_DOMAIN_COMPANION_ABILITY_ID = "38fe2b58-a26e-5733-b9db-3a61baf89508"
DRUIDE_COMPANION_ABILITY_ID = "1e421552-622f-583b-a8f9-62944ace3dc5"
ALL_ALIGNMENTS = ["LG", "NG", "CG", "LN", "N", "CN", "LE", "NE", "CE"]
DIVINE_HUNTER_DOMAIN_LEVEL_OFFSET = 2

TEXT_FIXES = [
    ("Wissen (/Grundregelwerk/Umgebung/Gewölbe Gewölbe)]]", "Wissen (Gewölbekunde)"),
    ("Diese Fähigkeit ersetzt Unterholz durchqueren?.", "Diese Fähigkeit ersetzt Unterholz durchqueren."),
    ("welche sie entfalten,. entspricht", "welche sie entfalten, entspricht"),
    ("Ein Rudelführer der 4.Stufe", "Ein Rudelführer der 4. Stufe"),
]

ARCHETYPES = [
    ("urzeit", "Bruder des Urzeitgefährten"),
    ("ungeziefer", "Bruder des Ungeziefergefährten"),
    ("goettlich", "Göttlicher Jäger"),
    ("rudel", "Rudelführer"),
    ("wild", "Wilder Jäger"),
]

# Per archetype: the page's feature labels in order -> (ability name,
# levels). A label shared with the base class gets the archetype's name as
# a suffix, so it doesn't collide with the Jäger's own row.
FEATURES: dict[str, list[tuple[str, str, list[int]]]] = {
    "urzeit": [
        ("Urzeitliche Verwandlung", "Urzeitliche Verwandlung", [1]),
        ("Urzeitlicher Kraftschub", "Urzeitlicher Kraftschub", [8]),
        ("Meister der Urzeit", "Meister der Urzeit", [20]),
    ],
    "ungeziefer": [
        ("Ungeziefergefährte", "Ungeziefergefährte", [1]),
        ("Ungezieferempathie", "Ungezieferempathie", [1]),
        ("Ungezieferaspekt", "Ungezieferaspekt", [1]),
        ("Schwärme durchqueren", "Schwärme durchqueren", [5]),
    ],
    "goettlich": [
        ("Gesinnung", "Gesinnung (Göttlicher Jäger)", [1]),
        ("Klassenfertigkeiten", "Klassenfertigkeiten (Göttlicher Jäger)", [1]),
        ("Domäne", "Domäne (Göttlicher Jäger)", [3]),
        ("Außerweltlicher Gefährte", "Außerweltlicher Gefährte", [3]),
    ],
    "rudel": [
        ("Rudelbindung", "Rudelbindung", [1]),
        ("Rudelaspekt", "Rudelaspekt", [1]),
        ("Gemeinschaftstalent", "Gemeinschaftstalent (Rudelführer)", [3]),
        ("Zweiter Rudelaspekt", "Zweiter Rudelaspekt", [8]),
        ("Herr des Rudels", "Herr des Rudels", [20]),
    ],
    "wild": [
        ("Tiergefährtenlos", "Tiergefährtenlos", [1]),
        ("Wilder Aspekt", "Wilder Aspekt", [1]),
        ("Genaues Ausmanövrieren", "Genaues Ausmanövrieren (Wilder Jäger)", [2]),
        ("Tiergestalt", "Tiergestalt (Wilder Jäger)", [4]),
        ("Rudel herbeizaubern", "Rudel herbeizaubern", [6]),
    ],
}

TIERASPEKT_GRANTS = [("Tieraspekt", 1), ("Tieraspekt (Tiergefährte)", 1)]
# Archetype features that are activatable effects themselves.
ACTIVATABLE: dict[str, dict] = {
    "Ungezieferaspekt": {"is_persistent_effect": True, "activation_scope": "self", "default_duration_rounds": 10},
}
GEMEINSCHAFTSTALENTE = [("Gemeinschaftstalente", level) for level in (3, 6, 9, 12, 15, 18)]

# ability name -> the Jäger grants (ability name, level) it replaces.
REPLACES: dict[str, list[tuple[str, int]]] = {
    "Urzeitliche Verwandlung": TIERASPEKT_GRANTS,
    "Urzeitlicher Kraftschub": [("Zweiter Tieraspekt", 8)],
    "Meister der Urzeit": [("Nimrod", 20)],
    "Ungeziefergefährte": [("Tiergefährte (Jäger)", 1)],
    "Ungezieferempathie": [("Tierempathie", 1)],
    "Ungezieferaspekt": TIERASPEKT_GRANTS,
    "Schwärme durchqueren": [("Unterholz durchqueren", 5)],
    "Domäne (Göttlicher Jäger)": GEMEINSCHAFTSTALENTE,
    "Außerweltlicher Gefährte": [("Jägertaktiken", 3)],
    "Rudelbindung": [("Tiergefährte (Jäger)", 1)],
    "Zweiter Rudelaspekt": [("Zweiter Tieraspekt", 8)],
    "Herr des Rudels": [("Nimrod", 20)],
    "Tiergefährtenlos": [("Tiergefährte (Jäger)", 1)],
    "Wilder Aspekt": TIERASPEKT_GRANTS + [("Jägertaktiken", 3), ("Mit Meister sprechen", 11)],
    "Tiergestalt (Wilder Jäger)": [
        ("Bonustricks", 7),
        ("Bonustricks", 13),
        ("Bonustricks", 19),
        ("Verbesserte Empathische Verbindung", 4),
        ("Mächtige Empathische Verbindung", 14),
        ("Nimrod", 20),
        ("Toten Tiergefährten erwecken", 10),
    ],
    "Rudel herbeizaubern": GEMEINSCHAFTSTALENTE[1:],
}

VERMIN_ASPECTS = [
    "Ameise", "Egel", "Fliege", "Floh", "Gottesanbeterin", "Käfer", "Krabbe", "Motte", "Phasmid", "Schabe",
    "Skorpion", "Spinne", "Tausendfüßler", "Wespe", "Wurm",
]

DOMAIN_GROUP = {
    "key": "divine_hunter_domain",
    "label": "Domäne (Göttlicher Jäger)",
    "max_choices": 1,
    "is_secondary_class_initial_pick": False,
}
TIERE_DOMAIN_SUBSTITUTE_DESC = (
    "(AF) Der Göttliche Jäger mit der Domäne der Tiere erhält keinen zweiten Tiergefährten, sobald er eine "
    "effektive Klerikerstufe von 4 erreicht; stattdessen erhält sein Tiergefährte zwei Attributswertanstiege "
    "von jeweils +1 (entweder +1 auf zwei unterschiedliche Attribute oder +2 auf ein Attribut). Sollte der "
    "Tiergefährte sterben oder aus den Diensten des Jägers entlassen werden, erhält sein nächster Tiergefährte "
    "ebenfalls diese Attributswertanstiege."
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


def fetch_sections() -> dict[str, tuple[str, dict[str, str]]]:
    """archetype key -> (intro text, feature label -> description)."""
    lines = apply_fixes(fetch_text(URL), TEXT_FIXES).split("\n")
    headings = [f"{name} (Archetyp)" for _key, name in ARCHETYPES]
    # Each heading appears in the table of contents first, then as the
    # section's own heading.
    starts = [len(lines) - 1 - lines[::-1].index(heading) for heading in headings]
    ends = starts[1:] + [next(i for i, line in enumerate(lines) if line.startswith("Regelwerke"))]
    sections = {}
    for (key, _name), start, end in zip(ARCHETYPES, starts, ends):
        body = lines[start + 1 : end]
        labels = [label for label, _ability, _levels in FEATURES[key]]
        first = next(i for i, line in enumerate(body) if any(line.startswith(label) for label in labels))
        sections[key] = (" ".join(body[:first]), split_labeled(body[first:], labels))
    return sections


def main() -> None:
    sections = fetch_sections()
    classes = load("base_classes.json")
    abilities = load("base_class_abilities.json")
    abilities_by_id = {a["id"]: a for a in abilities}
    grants = load("base_class_ability_grants.json")
    replacements = load("base_class_ability_replacements.json")
    groups = load("base_class_option_groups.json")
    choices = load("base_class_option_choices.json")
    slot_grants = load("base_companion_slot_grants.json")
    slot_species = load("base_companion_slot_species.json")
    ability_name_by_id = {a["id"]: a["name"] for a in abilities}

    def jaeger_grant(ability_name: str, level: int) -> str:
        matches = [
            g["id"]
            for g in grants
            if g["base_class_id"] == JAEGER_ID
            and g["level"] == level
            and g["option_choice_id"] is None
            and ability_name_by_id.get(g["ability_id"]) == ability_name
        ]
        assert len(matches) == 1, (ability_name, level, matches)
        return matches[0]

    archetype_ids = {key: uid("archetype", key) for key, _name in ARCHETYPES}
    own_ids = set(archetype_ids.values())
    grants = [g for g in grants if g["base_class_id"] not in own_ids]
    replacements = [r for r in replacements if r["archetype_class_id"] not in own_ids]

    def add_ability(key: str, name: str, description: str, extra: dict | None = None) -> str:
        aid = uid("ability", key, name)
        row = {"id": aid, "name": name, "description": description, **(extra or {})}
        if aid in abilities_by_id:
            abilities_by_id[aid].clear()
            abilities_by_id[aid].update(row)
        else:
            abilities.append(row)
            abilities_by_id[aid] = row
        ability_name_by_id[aid] = name
        return aid

    def add_grant(archetype_id: str, ability_id: str, level: int) -> None:
        grants.append(
            {
                "id": uid("grant", archetype_id, ability_id, str(level)),
                "base_class_id": archetype_id,
                "ability_id": ability_id,
                "option_choice_id": None,
                "level": level,
            }
        )

    def add_companion_slot(trigger_id: str) -> None:
        druide_slot = next(s for s in slot_grants if s["class_ability_id"] == DRUIDE_COMPANION_ABILITY_ID)
        slot_id = uid("slot", trigger_id)
        slot_grants[:] = [s for s in slot_grants if s["id"] != slot_id]
        slot_grants.append(
            {"id": slot_id, "class_ability_id": trigger_id, "track": "animal_companion", "slot_key": "primary",
             "level_offset": 0, "divisor": 1, "minimum": None}
        )
        for row in [s for s in slot_species if s["slot_grant_id"] == druide_slot["id"]]:
            slot_species.append(
                {"id": uid("slot-species", slot_id, row["race_id"]), "slot_grant_id": slot_id, "race_id": row["race_id"],
                 "master_sizes": row["master_sizes"], "min_level": row["min_level"]}
            )

    effect_options = load("base_class_ability_effect_options.json")
    vermin_option_ids: list[str] = []
    printed: dict[str, str] = {}
    for key, name in ARCHETYPES:
        archetype_id = archetype_ids[key]
        intro, features = sections[key]
        classes = [c for c in classes if c["id"] != archetype_id]
        classes.append(
            {
                "id": archetype_id,
                "name": name,
                "hit_dice": None,
                "arch_class_of": JAEGER_ID,
                "casting_ability": None,
                "spell_tradition": None,
                "bab_progression": None,
                "fort_save": None,
                "ref_save": None,
                "wil_save": None,
                "skill_points_base": None,
                **({"allowed_alignments": ALL_ALIGNMENTS} if key == "goettlich" else {}),
            }
        )
        for label, ability_name, levels in FEATURES[key]:
            description = features[label]
            if label == "Ungezieferaspekt":
                # The aspect list follows the feature's first paragraph and
                # ends with its "ersetzt Tieraspekt" line.
                _pool_text, *aspect_lines = description.split("\n\n")
                vermin = split_labeled([line for line in aspect_lines if ":" in line], VERMIN_ASPECTS)
                for aspect in VERMIN_ASPECTS:
                    aspect_id = add_ability(
                        key, f"Ungezieferaspekt: {aspect}", f"(ÜF) Aspekt des Ungezieferaspekts: {vermin[aspect]}"
                    )
                    vermin_option_ids.append(aspect_id)
                    printed[f"Ungezieferaspekt: {aspect}"] = aspect_id
            aid = add_ability(key, ability_name, description, ACTIVATABLE.get(ability_name))
            if label == "Ungezieferaspekt":
                effect_options = [o for o in effect_options if o["parent_ability_id"] != aid]
                effect_options += [
                    {"id": uid("effect-option", aid, option_id), "parent_ability_id": aid, "option_ability_id": option_id}
                    for option_id in vermin_option_ids
                ]
            printed[ability_name] = aid
            for level in levels:
                add_grant(archetype_id, aid, level)
            for replaced_name, replaced_level in REPLACES.get(ability_name, []):
                grant_id = jaeger_grant(replaced_name, replaced_level)
                replacements.append(
                    {
                        "id": uid("replacement", archetype_id, aid, grant_id),
                        "archetype_class_id": archetype_id,
                        "ability_id": aid,
                        "replaces_grant_id": grant_id,
                    }
                )
            if ability_name == "Rudelbindung":
                add_companion_slot(aid)
            if ability_name == "Wilder Aspekt":
                for aspect in ASPECTS:
                    jaeger_aspect = next(a for a in abilities if a["name"] == f"Tieraspekt: {aspect}")
                    text = jaeger_aspect["description"].split(": ", 1)[1]
                    aspect_id = add_ability(
                        key,
                        f"Wilder Aspekt: {aspect}",
                        f"(ÜF) Aspekt des Wilden Aspekts, ohne Wirkungsdauer: {text}",
                        {"is_persistent_effect": True, "activation_scope": "self"},
                    )
                    add_grant(archetype_id, aspect_id, 1)
                    printed[f"Wilder Aspekt: {aspect}"] = aspect_id
        print(f"{name}: {archetype_id} — {intro[:60]}…")

    # ---- Göttlicher Jäger: domain group mirroring the Kleriker's grants ----
    goettlich_id = archetype_ids["goettlich"]
    group_id = uid("group", DOMAIN_GROUP["key"])
    groups = [g for g in groups if g["id"] != group_id]
    groups.append({"id": group_id, "base_class_id": JAEGER_ID, **DOMAIN_GROUP})
    kleriker_domains = [c for c in choices if c["group_id"] == KLERIKER_DOMAIN_GROUP_ID]
    choices = [c for c in choices if c["group_id"] != group_id]
    grants = [g for g in grants if not (g["base_class_id"] == JAEGER_ID and g["option_choice_id"] is not None)]
    tiere_substitute_id = add_ability("goettlich", "Tiergefährte (Göttlicher Jäger, Domäne der Tiere)", TIERE_DOMAIN_SUBSTITUTE_DESC)
    mirrored = 0
    for domain in kleriker_domains:
        choice_id = uid("domain", domain["name"])
        choices.append(
            {
                "id": choice_id,
                "group_id": group_id,
                "name": domain["name"],
                "min_level": 3,
                "requires_choice_id": None,
                "race_id": None,
                "only_for_archetype_ids": [goettlich_id],
            }
        )
        for grant in [g for g in load("base_class_ability_grants.json") if g["base_class_id"] == KLERIKER_ID and g["option_choice_id"] == domain["id"]]:
            ability_id = grant["ability_id"]
            if ability_id == TIERE_DOMAIN_COMPANION_ABILITY_ID:
                ability_id = tiere_substitute_id
            level = grant["level"] + DIVINE_HUNTER_DOMAIN_LEVEL_OFFSET
            grants.append(
                {
                    "id": uid("domain-grant", ability_id, str(level), choice_id),
                    "base_class_id": JAEGER_ID,
                    "ability_id": ability_id,
                    "option_choice_id": choice_id,
                    "level": level,
                }
            )
            mirrored += 1

    save("base_classes.json", classes)
    save("base_class_abilities.json", abilities)
    save("base_class_ability_grants.json", grants)
    save("base_class_ability_replacements.json", replacements)
    save("base_class_ability_effect_options.json", effect_options)
    save("base_class_option_groups.json", groups)
    save("base_class_option_choices.json", choices)
    save("base_companion_slot_grants.json", slot_grants)
    save("base_companion_slot_species.json", slot_species)

    print("Domain choices:", len(kleriker_domains), "grants mirrored:", mirrored)
    for ability_name, aid in printed.items():
        print(f"{ability_name}: {aid}")


if __name__ == "__main__":
    main()
