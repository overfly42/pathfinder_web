"""Companion level sources — roadmap slice 10, step 1 (thin: no companions
yet, only the effective master level per track).

1. Seeds the one missing trigger ability: the Magier's `arcane_bond` choice
   "Vertrauter" had no choice-scoped `BaseClassAbilityGrant`, so nothing
   reached `granted_ability_ids` for a Magier with a familiar. Adds
   "Vertrauter (Magier)" + its level-1 grant gated on that choice (same
   pattern as the Druide's "Tiergefährte (Druide)", `import_druide.py`).
   The Magier's unconditional "Arkane Verbindung" stays the bond's general
   text; it isn't a familiar source itself because a Fokus doesn't grant one.

2. Writes `base_companion_level_sources.json`, one row per source, each
   checked against the trigger ability's own text:
   - animal_companion: Druide "Tiergefährte (Druide)" (Druide level);
     Waldläufer "Tiergefährte (Bund des Jägers)" (Waldläufer level −3);
     Kleriker Tier-Domäne "Tiergefährte" (Kleriker level −3 — a Druide who
     took it via "Bund mit der Natur" counts Druide level −3, handled by
     `rules/companions.py`'s `COMPANION_LEVEL_HANDLERS`); Hexenmeister
     Sylvanische Blutlinie "Tiergefährte" (Hexenmeister level −3, min 1);
     Mystiker "Gebundenes Reittier" (Mystiker level); Paladin
     "Göttlicher Bund: Reittier" (Paladin level); feat "Stallmeister" (+1).
   - familiar: Magier "Vertrauter (Magier)" (Magier level); Hexenmeister
     Arkane Blutlinie "Arkane Verbindung" (Hexenmeister level, "addieren
     sich seine Stufen als Hexenmeister und Magier"); Kampfmagus Arkanum
     "Vertrauter" (Kampfmagus level as Magier level); Hexe "Hexenvertrauter"
     (Hexe level as Magier level, step 4 — the Hexe's own trigger ability is
     seeded here too, an unconditional level-1 grant).
   - Druide as Sekundärklasse: "Tiergefährte (Sekundärklasse Druide)"
     (character level −4) and "Verbesserter Tiergefährte (Sekundärklasse
     Druide)" (character level), one stack group. The Magier as
     Sekundärklasse needs no source of its own (its "Vertrauter (Magier)"
     tier counts as Magier level = character level).

Deliberately not sources:
- Entfesselter Barbar "Wildes Reittier"/"Wildes Reittier, Mächtiges": their
  text only shares the Barbar's rage with whatever mount he rides — they
  don't grant a companion or an effective druid level (the roadmap had
  listed them as sources to add; checked 2026-10-17, they aren't).
- Waldläufer "Bund mit Gefährten" (the allies variant of Bund des Jägers).

Run with the project venv active (writes fixture JSON only):
    cd backend && python scripts/build_companion_level_sources.py
    python -m app.seed.class_ability_seed
    python -m app.seed.companion_seed
"""

from __future__ import annotations

import json
import uuid
from pathlib import Path

SEED_DIR = Path(__file__).resolve().parent.parent / "app" / "fixtures" / "seed"

ID_NAMESPACE = uuid.UUID("c0a7f1e2-5b3d-4e6f-8a9b-0c1d2e3f4a5b")

VERTRAUTER_MAGIER_DESC = (
    "(AF) Der Magier hat für seine Arkane Verbindung einen Vertrauten gewählt. Ein Vertrauter ist ein magisches "
    "Haustier, das die Fähigkeiten des Magiers verbessert und ihm als Begleiter und Diener dient. Die "
    "Magierstufe bestimmt die Fähigkeiten des Vertrauten; Stufen in anderen Klassen, die einen Vertrauten "
    "gewähren, addieren sich dabei."
)

# (key, track, label, trigger: ("ability", class name, ability name, option choice name or None) |
#  ("feat", feat name), kind, root class name or None, offset, divisor, minimum)
# PRD Expertenregeln/Klassen/Basisklassen/Hexe, "Hexenvertrauter (AF)".
HEXENVERTRAUTER_DESC = (
    "(AF) Auf der 1. Stufe formt die Hexe eine enge Verbindung zu einem Vertrauten, der sie Magie lehrt und auf "
    "ihrem Pfad begleitet und sie anleitet. Ebenfalls unterstützt der Vertraute sie, in dem er ihr Boni auf ihre "
    "Fertigkeiten verleiht, ihr zusätzliche Zauber gewährt und ihr den Umgang mit einigen Magiearten erleichtert. "
    "Dies funktioniert wie das Klassenmerkmal Arkane Verbindung eines Magiers, wobei Ausnahmen im Abschnitt zum "
    "Hexenvertrauten zu finden sind.\n"
    "Die Hexe muss jeden Tag mit ihrem Vertrauten kommunizieren, um ihre Zauber vorbereiten zu können. Alle "
    "Zauber welche die Hexe kennt, befinden sich innewohnend in ihrem Vertrauten. Die Hexe kann somit keine "
    "Zauber vorbereiten, die nicht in ihrem Vertrauten gespeichert sind. Die Stufe als Hexe entspricht der "
    "effektiven Stufe des Magiers, um die Fähigkeiten des Vertrauten der Hexe zu ermitteln; Stufen in anderen "
    "Klassen mit Vertrauten addieren sich."
)

SOURCES: list[tuple] = [
    ("druide", "animal_companion", "Druide", ("ability", "Druide", "Tiergefährte (Druide)", "Tiergefährte"),
     "class_level", "Druide", 0, 1, None),
    ("waldlaeufer", "animal_companion", "Waldläufer",
     ("ability", "Waldläufer", "Tiergefährte (Bund des Jägers)", "Tiergefährte"),
     "class_level", "Waldläufer", -3, 1, None),
    ("kleriker-tiere", "animal_companion", "Kleriker (Domäne der Tiere)",
     ("ability", "Kleriker", "Tiergefährte", "Domäne der Tiere"),
     "class_level", "Kleriker", -3, 1, None),
    ("hexenmeister-sylvanisch", "animal_companion", "Hexenmeister (Sylvanische Blutlinie)",
     ("ability", "Hexenmeister", "Tiergefährte", "Sylvanische Blutlinie"),
     "class_level", "Hexenmeister", -3, 1, 1),
    ("mystiker-reittier", "animal_companion", "Mystiker (Gebundenes Reittier)",
     ("ability", "Mystiker", "Gebundenes Reittier", "Gebundenes Reittier"),
     "class_level", "Mystiker", 0, 1, None),
    ("paladin-reittier", "animal_companion", "Paladin (Göttlicher Bund)",
     ("ability", "Paladin", "Göttlicher Bund: Reittier", "Reittier"),
     "class_level", "Paladin", 0, 1, None),
    ("stallmeister", "animal_companion", "Stallmeister", ("feat", "Stallmeister"),
     "flat_bonus", None, 1, 1, None),
    ("magier", "familiar", "Magier", ("ability", "Magier", "Vertrauter (Magier)", "Vertrauter"),
     "class_level", "Magier", 0, 1, None),
    ("hexenmeister-arkan", "familiar", "Hexenmeister (Arkane Blutlinie)",
     ("ability", "Hexenmeister", "Arkane Verbindung", "Arkane Blutlinie"),
     "class_level", "Hexenmeister", 0, 1, None),
    ("kampfmagus", "familiar", "Kampfmagus (Arkanum Vertrauter)",
     ("ability", "Kampfmagus", "Vertrauter", "Vertrauter"),
     "class_level", "Kampfmagus", 0, 1, None),
    ("hexe", "familiar", "Hexe", ("ability", "Hexe", "Hexenvertrauter", None),
     "class_level", "Hexe", 0, 1, None),
    # Druide as Sekundärklasse (`build_secondary_class_druide_magier_seed.py`,
    # run that first): character level −4 from 7th, full character level
    # from 11th — one stack group, the better one counts.
    ("druide-sekundaer", "animal_companion", "Druide (Sekundärklasse)",
     ("named", "Tiergefährte (Sekundärklasse Druide)"), "character_level", None, -4, 1, None),
    ("druide-sekundaer-verbessert", "animal_companion", "Druide (Sekundärklasse, verbessert)",
     ("named", "Verbesserter Tiergefährte (Sekundärklasse Druide)"), "character_level", None, 0, 1, None),
    # Druide archetypes whose own companion trigger replaces "Tiergefährte
    # (Druide)" (`import_druide_tierschamanen.py`, run that first).
    ("baerenschamane", "animal_companion", "Druide (Bärenschamane)",
     ("named", "Tiergefährte (Bärenschamane)"), "class_level", "Druide", 0, 1, None),
    ("loewenschamane", "animal_companion", "Druide (Löwenschamane)",
     ("named", "Tiergefährte (Löwenschamane)"), "class_level", "Druide", 0, 1, None),
]
STACK_GROUPS = {"druide-sekundaer": "druide-sekundaer", "druide-sekundaer-verbessert": "druide-sekundaer"}


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
    class_id_by_name = {c["name"]: c["id"] for c in load("base_classes.json") if c["arch_class_of"] is None}
    groups = load("base_class_option_groups.json")
    choices = load("base_class_option_choices.json")
    group_class_by_id = {g["id"]: g["base_class_id"] for g in groups}
    choice_id_by_class_and_name = {
        (group_class_by_id[c["group_id"]], c["name"]): c["id"] for c in choices if c["group_id"] in group_class_by_id
    }

    # ---- 1. Magier's missing familiar trigger ----
    magier_id = class_id_by_name["Magier"]
    abilities = load("base_class_abilities.json")
    grants = load("base_class_ability_grants.json")
    vertrauter_id = uid("ability", "Vertrauter (Magier)")
    abilities.append({"id": vertrauter_id, "name": "Vertrauter (Magier)", "description": VERTRAUTER_MAGIER_DESC})
    vertrauter_choice_id = choice_id_by_class_and_name[(magier_id, "Vertrauter")]
    grants.append(
        {
            "id": uid("grant", vertrauter_id, vertrauter_choice_id),
            "base_class_id": magier_id,
            "ability_id": vertrauter_id,
            "option_choice_id": vertrauter_choice_id,
            "level": 1,
        }
    )
    # The Hexe's familiar is not a choice: an unconditional level-1 grant.
    hexe_id = class_id_by_name["Hexe"]
    hexenvertrauter_id = uid("ability", "Hexenvertrauter")
    abilities.append({"id": hexenvertrauter_id, "name": "Hexenvertrauter", "description": HEXENVERTRAUTER_DESC})
    grants.append(
        {
            "id": uid("grant", hexenvertrauter_id),
            "base_class_id": hexe_id,
            "ability_id": hexenvertrauter_id,
            "option_choice_id": None,
            "level": 1,
        }
    )
    save("base_class_abilities.json", abilities)
    save("base_class_ability_grants.json", grants)

    # ---- 2. sources ----
    ability_name_by_id = {a["id"]: a["name"] for a in abilities}
    feat_id_by_name = {f["name"]: f["id"] for f in load("base_feats.json")}
    rows = []
    for key, track, label, trigger, kind, root_name, offset, divisor, minimum in SOURCES:
        class_ability_id = feat_id = None
        if trigger[0] == "ability":
            _, class_name, ability_name, choice_name = trigger
            class_id = class_id_by_name[class_name]
            choice_id = choice_id_by_class_and_name[(class_id, choice_name)] if choice_name else None
            matches = [
                g["ability_id"]
                for g in grants
                if g["base_class_id"] == class_id
                and g["option_choice_id"] == choice_id
                and ability_name_by_id[g["ability_id"]] == ability_name
            ]
            assert len(set(matches)) == 1, (key, matches)
            class_ability_id = matches[0]
        elif trigger[0] == "named":
            # A Sekundärklasse tier's own ability: unique by name, no class grant.
            matches = [a["id"] for a in abilities if a["name"] == trigger[1]]
            assert len(matches) == 1, (key, matches)
            class_ability_id = matches[0]
        else:
            feat_id = feat_id_by_name[trigger[1]]
        rows.append(
            {
                "id": uid("source", key),
                "track": track,
                "label": label,
                "class_ability_id": class_ability_id,
                "feat_id": feat_id,
                "kind": kind,
                "root_class_id": class_id_by_name[root_name] if root_name else None,
                "offset": offset,
                "divisor": divisor,
                "minimum": minimum,
                "stack_group": STACK_GROUPS.get(key),
            }
        )
    save("base_companion_level_sources.json", rows)
    for row in rows:
        print(row["id"], row["track"], row["label"])


if __name__ == "__main__":
    main()
