"""Import the 66 Kleriker subdomains ("Unterdomänen") from
https://prd.5footstep.de/Expertenregeln/Klassen/Grundklassen/Kleriker/Unterdomänen
into the seed JSON files. Texts are parsed from the live page at run time
(checked 2026-10-28), like `import_jaeger.py`.

Every subdomain names one main domain (four name two: Archonten, Azata,
Dämonen, Teufel) and replaces exactly one of that domain's powers
("Ersatzfähigkeit") plus some of its domain spells ("Ersatzdomänenzauber").
Same shape as `import_hexenmeister_wildblooded.py`'s wildblooded bloodlines:
each subdomain is one more `BaseClassOptionChoice` in the group its main
domain sits in, whose grants copy the main domain choice's grants (same
`ability_id`s, same levels — so the Tier-Domäne's Tiergefährte keeps working
for Federn/Felle) with the replaced power swapped for the new one. A
subdomain under two main domains becomes one choice per main domain
("Unterdomäne der Archonten (Gutes)"), since each replaces a different power.

Three groups get them, per the page ("Charaktere, denen Zugang zu Domänen
gewährt wird ..."): the Kleriker's `domain`, the Göttlicher Jäger's
`divine_hunter_domain` and the Druide's `nature_domain` (only subdomains of
its own Naturdomänen, never Metalle — "bis auf die Unterdomäne der
Metalle"). Each copied choice keeps its main domain's `min_level`/
`requires_choice_id`/archetype scoping (a Bärenschamane's Schutz domain ->
only his Reinheit/Verteidigung).

"Die Unterdomäne ersetzt die mit ihr verbundene Hauptdomäne" and "nur eine
davon" are `BaseClassOptionChoice.exclusion_keys`: every domain choice
carries its own name, every subdomain choice its main domain's name plus
its own subdomain name.

Also per subdomain: one "Verliehene Fähigkeiten (Unterdomäne der X)" row
(main domain, what it replaces, extra rules, replacement domain spells as
text — domain spells aren't modeled yet, roadmap "Domänenzauber (Kleriker)"),
granted next to the main domain's own overview. Federn's "Füge Fliegen zur
Liste deiner Klassenfertigkeiten hinzu" is `rules/classes/kleriker.py`'s
`CLASS_SKILL_GRANTS` on that overview row. The deity checks ("Zugang zur
Domäne wie auch zur Unterdomäne") need a deity model — same open item as
the Kleriker's alignment (todos.md).

Run with the project venv active (writes fixtures only; seed afterwards):
    cd backend && python scripts/import_kleriker_unterdomaenen.py
    python -m app.seed.class_option_seed
    python -m app.seed.class_ability_seed
"""

from __future__ import annotations

import json
import re
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from import_jaeger import fetch_text  # noqa: E402

SEED_DIR = Path(__file__).resolve().parent.parent / "app" / "fixtures" / "seed"
URL = "https://prd.5footstep.de/Expertenregeln/Klassen/Grundklassen/Kleriker/Unterdom%C3%A4nen"

ID_NAMESPACE = uuid.UUID("5e2c8a71-3f4d-4b9e-a6c0-9d1b7e3f2a58")

# group key -> the class that owns it
GROUP_KEYS = ("domain", "divine_hunter_domain", "nature_domain")
NOT_FOR_DRUIDE = {"Unterdomäne der Metalle"}

# "Hauptdomäne:" short name -> domain choice name
MAIN_DOMAINS = {
    "Adel": "Domäne des Adels",
    "Befreiung": "Domäne der Befreiung",
    "Böses": "Domäne des Bösen",
    "Chaos": "Domäne des Chaos",
    "Dunkelheit": "Domäne der Dunkelheit",
    "Erde": "Domäne der Erde",
    "Feuer": "Domäne des Feuers",
    "Gemeinschaft": "Domäne der Gemeinschaft",
    "Glück": "Domäne des Glücks",
    "Gutes": "Domäne des Guten",
    "Handwerk": "Domäne des Handwerks",
    "Heilung": "Domäne der Heilung",
    "Herrlichkeit": "Domäne der Herrlichkeit",
    "Krieg": "Domäne des Krieges",
    "Luft": "Domäne der Luft",
    "Magie": "Domäne der Magie",
    "Ordnung": "Domäne der Ordnung",
    "Pflanzen": "Domäne der Pflanzen",
    "Reisen": "Domäne der Reisen",
    "Ruhe": "Domäne der Ruhe",
    "Runen": "Domäne der Runen",
    "Schutz": "Domäne des Schutzes",
    "Sonne": "Domäne der Sonne",
    "Stärke": "Domäne der Stärke",
    "Tiere": "Domäne der Tiere",
    "Tod": "Domäne des Todes",
    "Tricks": "Domäne der Tricks",
    "Verzauberung": "Domäne der Verzauberung",
    "Wahnsinn": "Domäne des Wahnsinns",
    "Wasser": "Domäne des Wassers",
    "Wetter": "Domäne des Wetters",
    "Wissen": "Domäne des Wissens",
    "Zerstörung": "Domäne der Zerstörung",
}

# Replaced-power names as the page spells them -> the seeded ability name.
REPLACED_NAME_FIXES = {
    "Tanzende Waffe": "Tanzende Waffen",
    "Mit Tieren sprechen": "Mit-Tieren-sprechen",
}

# New-power names that would clash with an existing class ability on the
# sheet (a Barbar/Kleriker multiclass) -> the seeded name.
POWER_NAME_FIXES = {
    "Kampfrausch": "Kampfrausch (Unterdomäne der Wut)",
}

OVERVIEW_PREFIX = "Verliehene Fähigkeiten"
POWER_LINE = re.compile(r"^(?P<name>[^:()]{2,60}?)\s*\((?P<tag>AF|ÜF|ZF)\)\s*:\s*(?P<text>.*)$")


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


def replaced_names(sentence: str) -> list[str]:
    """"Die folgende Fähigkeit ersetzt Heilige Lanze der Domäne des Guten
    oder Stab der Ordnung der Domäne der Ordnung. Archonten sind …" ->
    ["Heilige Lanze", "Stab der Ordnung"], in the order of the main domains."""
    target = sentence.split(" ersetzt ", 1)[1]
    target = re.split(r"\.\s|:$|\.$", target)[0]
    names = []
    for part in target.split(" oder "):
        part = re.sub(r"^(den|die|das) ", "", part.strip())
        part = re.sub(r" der Domäne (des|der) \S+$", "", part)
        names.append(REPLACED_NAME_FIXES.get(part, part))
    return names


def parse_subdomains() -> list[dict]:
    lines = fetch_text(URL).split("\n")
    starts = [i for i, line in enumerate(lines) if line.startswith("Unterdomäne de")]
    end_marker = next(i for i, line in enumerate(lines) if line.startswith("Regelwerke, Expertenregeln"))
    subdomains = []
    for k, start in enumerate(starts):
        body = lines[start + 1 : starts[k + 1] if k + 1 < len(starts) else end_marker]
        mains = [m.strip() for m in body[0].split(":", 1)[1].strip(" .").split(",")]
        assert body[0].startswith("Hauptdomäne") and all(m in MAIN_DOMAINS for m in mains), body[0]
        replace_line = next(line for line in body if line.startswith("Ersatzfähigkeit:"))
        spells_line = next(line for line in body if line.startswith("Ersatzdomänenzauber:"))
        power_index = next(i for i, line in enumerate(body) if POWER_LINE.match(line))
        power = POWER_LINE.match(body[power_index])
        spells_index = body.index(spells_line)
        extra = [line for line in body[1:power_index] if line != replace_line]
        replaced = replaced_names(replace_line)
        assert len(replaced) == len(mains), (lines[start], replaced, mains)
        subdomains.append(
            {
                "name": lines[start],
                "mains": mains,
                "replaced": dict(zip(mains, replaced)),
                "replace_line": replace_line,
                "extra": extra,
                "spells_line": spells_line,
                "power_name": POWER_NAME_FIXES.get(power["name"], power["name"]),
                "power_text": "\n\n".join(
                    [f"({power['tag']}) {power['text']}", *body[power_index + 1 : spells_index]]
                ),
            }
        )
    assert len(subdomains) == 66, len(subdomains)
    return subdomains


def main() -> None:
    subdomains = parse_subdomains()

    groups = {g["key"]: g for g in load("base_class_option_groups.json") if g["key"] in GROUP_KEYS}
    group_ids = {g["id"] for g in groups.values()}
    choices = load("base_class_option_choices.json")
    abilities = load("base_class_abilities.json")
    grants = load("base_class_ability_grants.json")
    ability_by_id = {a["id"]: a for a in abilities}

    # Drop this script's own earlier output, then tag every domain choice.
    choices = [c for c in choices if not (c["group_id"] in group_ids and c["name"].startswith("Unterdomäne"))]
    own_choice_ids = {
        uid("choice", key, s["name"], main) for key in GROUP_KEYS for s in subdomains for main in s["mains"]
    }
    grants = [g for g in grants if g["option_choice_id"] not in own_choice_ids]
    for choice in choices:
        if choice["group_id"] in group_ids:
            choice["exclusion_keys"] = [choice["name"]]

    for s in subdomains:
        power_id = uid("ability", s["name"], s["power_name"])
        abilities.append({"id": power_id, "name": s["power_name"], "description": s["power_text"]})
        overview_id = uid("ability", s["name"], OVERVIEW_PREFIX)
        overview_text = "\n\n".join(
            [f"Hauptdomäne: {', '.join(s['mains'])}.", s["replace_line"], *s["extra"], s["spells_line"]]
        )
        abilities.append({"id": overview_id, "name": f"{OVERVIEW_PREFIX} ({s['name']})", "description": overview_text})

        for key, group in groups.items():
            if key == "nature_domain" and s["name"] in NOT_FOR_DRUIDE:
                continue
            for main in s["mains"]:
                main_choice = next(
                    (c for c in choices if c["group_id"] == group["id"] and c["name"] == MAIN_DOMAINS[main]), None
                )
                if main_choice is None:  # not one of the Druide's Naturdomänen
                    continue
                name = s["name"] if len(s["mains"]) == 1 else f"{s['name']} ({main})"
                choice_id = uid("choice", key, s["name"], main)
                choices.append(
                    {
                        **{k: v for k, v in main_choice.items() if k not in ("id", "name", "exclusion_keys")},
                        "id": choice_id,
                        "name": name,
                        "exclusion_keys": [main_choice["name"], s["name"]],
                    }
                )
                main_grants = [g for g in grants if g["option_choice_id"] == main_choice["id"]]
                replaced = [g for g in main_grants if ability_by_id[g["ability_id"]]["name"] == s["replaced"][main]]
                assert len(replaced) == 1, (key, name, s["replaced"][main])
                overview = [g for g in main_grants if ability_by_id[g["ability_id"]]["name"].startswith(OVERVIEW_PREFIX)]
                assert len(overview) == 1, (key, name)
                for grant in main_grants:
                    ability_id = power_id if grant is replaced[0] else grant["ability_id"]
                    grants.append(
                        {**grant, "id": uid("grant", choice_id, grant["id"]), "ability_id": ability_id, "option_choice_id": choice_id}
                    )
                grants.append(
                    {
                        **overview[0],
                        "id": uid("grant", choice_id, OVERVIEW_PREFIX),
                        "ability_id": overview_id,
                        "option_choice_id": choice_id,
                    }
                )

    assert len({(c["group_id"], c["name"]) for c in choices}) == len(choices), "duplicate (group_id, name)"
    save("base_class_option_choices.json", choices)
    save("base_class_abilities.json", abilities)
    save("base_class_ability_grants.json", grants)

    for key, group in groups.items():
        count = sum(1 for c in choices if c["group_id"] == group["id"] and c["name"].startswith("Unterdomäne"))
        print(f"{key}: {count} subdomain choices")
    federn = next(s for s in subdomains if s["name"] == "Unterdomäne der Federn")
    print("Federn overview ability id:", uid("ability", federn["name"], OVERVIEW_PREFIX))


if __name__ == "__main__":
    main()
