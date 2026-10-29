"""Import the Jäger (Hunter) base class from
https://prd.5footstep.de/Ausbauregeln-VI-Klassen/Klassen/Jäger — a brand-new
root class (no placeholder row existed). The feature texts are parsed from
the live page at run time (`fetch_features`, checked 2026-10-26) instead of
being transcribed by hand, so the descriptions stay verbatim; `TEXT_FIXES`
repairs the page's few markup leftovers.

"Tabelle Jäger": W8, 3/4 GAB, good Ref/Fort, poor Will, 6 + IN, WE, divine
spontaneous, any neutral alignment. Verified cell for cell against the page
(2026-10-26): spells per day and "Tabelle: Bekannte Jägerzauber" are
identical to the Barde's tables, so `build_spells_per_day_seed.py` lists the
Jäger with the Barde and `SPELLS_KNOWN` here is the Barde's table.

What this script writes:
- `base_classes.json` row, `classes.json` entry (`spellType` "spontaneous"),
  class skills (15), a `favored_class_bonus` group with the generic hp/skill
  choices (under `add_generic_favored_class_bonus_choices.py`'s ids — that
  script, when run, rewrites every class's pair in place of appending),
  plus the race-scoped alternates in `RACE_FAVORED_CLASS_BONUSES` (choice +
  `BaseClassAbility`/grant pair, same shape as
  `import_favored_class_bonus_halbork.py`; the numbers are
  `rules/favored_class_bonuses.py`'s/`rules/companions.py`'s).
- Every class feature as `BaseClassAbility` + grants (1st–20th).
  "Tieraspekt" is a pool of Jäger-level minutes per day and one activatable
  effect whose aspects are options picked on the effect
  (`base_class_ability_effect_options.json`, `rules/classes/jaeger.py`;
  roadmap slice 10 step 6) — the aspect rows aren't granted themselves.
  "Tieraspekt (Tiergefährte)" (1st, own text) is the companion's aspect,
  the same options.
- Tierempathie: a grant of the shared Druide/Waldläufer row (decided
  2026-10-14 for the Druide); its description now names the Jäger too.
- "Tiergefährte (Jäger)": the companion trigger, with its own companion slot
  allowing every species the Druide's slot allows ("jedes Tier, welches
  auch ein Druide mit der 1. Stufe wählen könnte"); its level source (Jäger
  level) is in `build_companion_level_sources.py`.
- "Genaues Ausmanövrieren" (2nd): a bonus feat slot, closed list
  Präzisionsschuss/Ausmanövrieren, prerequisites waived ("muss die
  Voraussetzungen ... nicht erfüllen"). "Gemeinschaftstalente" (3rd, every
  three levels): a bonus feat slot for any teamwork feat, prerequisites
  required. Both ids are in `rules/feat_slots.py`'s
  `BONUS_FEAT_SLOT_ABILITY_IDS`. Run `import_gemeinschaftstalente.py` first.
- Proficiencies: simple + martial weapons, light/medium armor, shields.
- Spell list: the rule is "Waldläuferzauber und Druidenzauber des maximal 6.
  Grades ... den niedrigeren der beiden Grade" — built from the app's own
  Druide/Waldläufer `base_class_spells.json` rows (both match the PRD index
  exactly). Not from the PRD index's own "Jäger" column: it contradicts the
  class text in 22 cases (e.g. Tier verkleinern at 3, the page's own example
  says 2) and lacks 40 spells on either list.
- "Kenntnis von allen Verbündeten der Natur herbeizaubern-Zaubern": class-wide
  `BaseClassSpellGrant` rows (`option_choice_id` null) for I–VI at the level
  each grade unlocks; they don't count against the known-spell budget
  (`rules/spells.py`'s `granted_spell_ids_for_choices`).

Descriptive only (see the feature texts; `rules/classes/jaeger.py` lists
what is computed):
- The companion's own aspect, Jagdtricks (Plänkler tricks aren't in the
  trick catalog), Naturausbildung, the empathic links, Toten Tiergefährten
  erwecken, Eins mit der Wildnis, Nimrod.
- Swapping a known spell at 5th/8th/... and swapping the latest teamwork
  feat per day — no swap mechanism exists for either.

Run with the project venv active (writes fixtures only; seed afterwards):
    cd backend && python scripts/import_gemeinschaftstalente.py
    python scripts/import_jaeger.py
    python scripts/build_spells_per_day_seed.py
    python scripts/build_companion_level_sources.py
    python -m app.seed.feat_seed && python -m app.seed.class_seed && python -m app.seed.skill_seed
    python -m app.seed.class_option_seed && python -m app.seed.class_ability_seed
    python -m app.seed.class_ability_granted_feat_seed && python -m app.seed.class_ability_option_seed
    python -m app.seed.spell_seed && python -m app.seed.companion_seed
"""

from __future__ import annotations

import html
import json
import re
import urllib.request
import uuid
from pathlib import Path

FIXTURES = Path(__file__).resolve().parent.parent / "app" / "fixtures"
SEED_DIR = FIXTURES / "seed"

URL = "https://prd.5footstep.de/Ausbauregeln-VI-Klassen/Klassen/J%C3%A4ger"
ID_NAMESPACE = uuid.UUID("7c4e2b91-0d6a-4f38-a5e1-9b3f6c2d8e47")

JAEGER_ID = str(uuid.uuid5(ID_NAMESPACE, "class|Jäger"))
DRUIDE_ID = "2835c712-7129-41fe-a61e-8ef05de2e0cf"
WALDLAEUFER_ID = "91ab69e8-7ab5-46de-af7f-292f585645b4"
DRUIDE_COMPANION_ABILITY_ID = "1e421552-622f-583b-a8f9-62944ace3dc5"  # "Tiergefährte (Druide)"

ALIGNMENTS = ["NG", "LN", "N", "CN", "NE"]
# `add_generic_favored_class_bonus_choices.py`'s namespace.
FCB_ID_NAMESPACE = uuid.UUID("f0a681a3-8b99-4c58-bcfd-3ee0cb6aea72")

# (race name, race id, description): Advanced Race Guide alternate
# favored-class bonuses for the Jäger — given by the project owner
# (2026-10-27), the PRD race pages don't list the Jäger.
RACE_FAVORED_CLASS_BONUSES = [
    (
        "Halb-Ork",
        "88d38c58-be34-42e6-b4a5-08704bc97cb8",
        "Der Tiergefährte des Jägers erhält 1 zusätzlichen Trefferpunkt. Sollte der Jäger später seinen "
        "Tiergefährten ersetzen, erhält der neue Tiergefährte diese Bonustrefferpunkte.",
    ),
]

CLASS_SKILLS = [
    "Beruf",
    "Einschüchtern",
    "Handwerk",
    "Heilkunde",
    "Heimlichkeit",
    "Klettern",
    "Mit Tieren umgehen",
    "Reiten",
    "Schwimmen",
    "Überlebenskunst",
    "Wahrnehmung",
    "Wissen (Geographie)",
    "Wissen (Gewölbekunde)",
    "Wissen (Natur)",
    "Zauberkunde",
]

PROFICIENCY_FEATS = [
    "Umgang mit einfachen Waffen",
    "Umgang mit Kriegswaffen",
    "Umgang mit Rüstungen (leichte)",
    "Umgang mit Rüstungen (mittelschwere)",
    "Umgang mit Schilden",
]

# Shared with Druide and Waldläufer (`import_druide.py`); now names the Jäger.
TIEREMPATHIE_ABILITY_ID = "ebd5060b-066a-4bc0-bdfa-064222de85bf"
TIEREMPATHIE_SHARED_DESC = (
    "Der Charakter kann die Einstellung eines Tieres ihm gegenüber verbessern. Diese Fähigkeit funktioniert "
    "genau wie ein Wurf auf Diplomatie, um die Einstellung einer Person zu verändern. Er würfelt 1W20 und "
    "addiert sowohl seine Stufe in der Klasse, die ihm Tierempathie gewährt (Druide, Jäger bzw. Waldläufer; "
    "Stufen in mehreren solchen Klassen addieren sich), als auch seinen CH-Modifikator zu dem Wurf. Ein zahmes "
    "Tier beginnt mit einer gleichgültigen Einstellung, während ein wildes Tier zunächst unfreundlich ist.\n\n"
    "Um Tierempathie einsetzen zu können, dürfen sich unter normalen Umständen Tier und Charakter nicht "
    "weiter als 9 m voneinander entfernt befinden. Im Allgemeinen dauert das Beeinflussen eines Tieres eine "
    "Minute, im Einzelfall kann es aber auch schneller oder langsamer gehen.\n\n"
    "Mit dieser Fähigkeit kann er auch versuchen, magische Bestien mit einem Intelligenzwert von 1 oder 2 zu "
    "beeinflussen, nimmt dabei jedoch einen Malus von -4 auf seinen Wurf in Kauf."
)

# The page's feature labels in order, as they open their paragraph
# ("Tieraspekt (ÜF): ..."), with the levels each is granted at. "Tierempathie"
# is parsed only to check the page still has it (the shared row is granted
# instead). "Tiergefährte" becomes "Tiergefährte (Jäger)".
FEATURES: list[tuple[str, list[int]]] = [
    ("Umgang mit Waffen und Rüstungen", [1]),
    ("Zauber", [1]),
    ("Stoßgebete", [1]),
    ("Böse, chaotische, gute und rechtschaffene Zauber", [1]),
    ("Tieraspekt", [1]),
    ("Tierempathie", [1]),
    ("Tiergefährte", [1]),
    ("Naturausbildung", [1]),
    ("Genaues Ausmanövrieren", [2]),
    ("Spuren lesen", [2]),
    ("Gemeinschaftstalente", [3, 6, 9, 12, 15, 18]),
    ("Jägertaktiken", [3]),
    ("Verbesserte Empathische Verbindung", [4]),
    ("Unterholz durchqueren", [5]),
    ("Bonustricks", [7, 13, 19]),
    ("Schneller Verfolger", [8]),
    ("Zweiter Tieraspekt", [8]),
    ("Toten Tiergefährten erwecken", [10]),
    ("Mit Meister sprechen", [11]),
    ("Mächtige Empathische Verbindung", [14]),
    ("Eins mit der Wildnis", [17]),
    ("Nimrod", [20]),
]
# Class features that are activatable effects themselves.
ACTIVATABLE: dict[str, dict] = {
    "Tieraspekt": {"is_persistent_effect": True, "activation_scope": "self", "default_duration_rounds": 10},
}
COMPANION_ASPECT_NAME = "Tieraspekt (Tiergefährte)"
COMPANION_ASPECT_DESC = (
    "(ÜF) Der Tieraspekt, den der Jäger seinem Tiergefährten verleiht: ein Aspekt, ab der 8. Stufe "
    "(Zweiter Tieraspekt) zwei, derselbe oder ein anderer als der eigene. Er unterliegt keiner "
    "Wirkungsdauer und zählt nicht gegen die Minuten am Tag, bis der Jäger ihn ändert."
)

ASPECTS = [
    "Affe", "Bär", "Eule", "Falke", "Fledermaus", "Hirsch", "Frosch", "Maus", "Schlange", "Stier", "Tiger", "Wolf",
]
RENAMED = {"Tiergefährte": "Tiergefährte (Jäger)"}

# (wrong, right) literal repairs of the page text — each must occur.
TEXT_FIXES = [
    ("Toten Tiergefährten erweckenABR", "Toten Tiergefährten erwecken (ABR)"),
    ("seiner Stufe.Der Jäger", "seiner Stufe. Der Jäger"),
    ("Die Die Kreatur", "Die Kreatur"),
    ("Malus von – 5", "Malus von –5"),
    ("Malus von – 10 (anstelle von – 20)", "Malus von –10 (anstelle von –20)"),
    ("Malus von – 4", "Malus von –4"),
]

GENAUES_AUSMANOEVRIEREN_FEATS = ["Präzisionsschuss", "Ausmanövrieren"]

# "Tabelle: Bekannte Jägerzauber" — identical to the Barde's (verified).
SPELLS_KNOWN = {
    1: {0: 4, 1: 2},
    2: {0: 5, 1: 3},
    3: {0: 6, 1: 4},
    4: {0: 6, 1: 4, 2: 2},
    5: {0: 6, 1: 4, 2: 3},
    6: {0: 6, 1: 4, 2: 4},
    7: {0: 6, 1: 5, 2: 4, 3: 2},
    8: {0: 6, 1: 5, 2: 4, 3: 3},
    9: {0: 6, 1: 5, 2: 4, 3: 4},
    10: {0: 6, 1: 5, 2: 5, 3: 4, 4: 2},
    11: {0: 6, 1: 6, 2: 5, 3: 4, 4: 3},
    12: {0: 6, 1: 6, 2: 5, 3: 4, 4: 4},
    13: {0: 6, 1: 6, 2: 5, 3: 5, 4: 4, 5: 2},
    14: {0: 6, 1: 6, 2: 6, 3: 5, 4: 4, 5: 3},
    15: {0: 6, 1: 6, 2: 6, 3: 5, 4: 4, 5: 4},
    16: {0: 6, 1: 6, 2: 6, 3: 5, 4: 5, 5: 4, 6: 2},
    17: {0: 6, 1: 6, 2: 6, 3: 6, 4: 5, 5: 4, 6: 3},
    18: {0: 6, 1: 6, 2: 6, 3: 6, 4: 5, 5: 4, 6: 4},
    19: {0: 6, 1: 6, 2: 6, 3: 6, 4: 5, 5: 5, 6: 4},
    20: {0: 6, 1: 6, 2: 6, 3: 6, 4: 6, 5: 5, 6: 5},
}
MAX_GRADE = 6
SUMMON_SPELLS = [f"Verbündeten der Natur herbeizaubern {numeral}" for numeral in ("I", "II", "III", "IV", "V", "VI")]


def fetch_text(url: str) -> str:
    """The page's content block as plain text lines (the site's 2026-10-25
    layout, same as `import_companion_tricks.fetch_text`)."""
    raw = urllib.request.urlopen(url, timeout=30).read().decode("utf-8")
    block = re.search(r'<article id="page-show">(.*?)</article>', raw, re.S).group(1)
    text = re.sub(r"<br\s*/?>", "\n", block)
    text = re.sub(r"</(p|h\d|tr|li|div)>", "\n", text)
    text = re.sub(r"</t[dh]>", " | ", text)
    text = html.unescape(re.sub(r"<[^>]+>", "", text).replace("&nbsp;", " ")).replace("\xa0", " ")
    text = re.sub(r"[ \t]+", " ", text)
    return "\n".join(line.strip() for line in text.split("\n") if line.strip())


def apply_fixes(text: str, fixes: list[tuple[str, str]]) -> str:
    for wrong, right in fixes:
        assert wrong in text, f"text fix no longer applies: {wrong!r}"
        text = text.replace(wrong, right)
    return text


def split_labeled(lines: list[str], labels: list[str]) -> dict[str, str]:
    """Paragraphs grouped under the label that opens them ("Label (AF): …" or
    "Label: …"); following lines without a label belong to the previous one.
    The type tag becomes the description's prefix, like every other class
    ability row ("(AF) Ab der 4. Stufe …")."""
    pattern = re.compile(
        r"^(" + "|".join(re.escape(label) for label in labels) + r")\s*(\((?:AF|ÜF|ZF)\))?\s*:\s*(.*)$"
    )
    result: dict[str, list[str]] = {}
    current: str | None = None
    for line in lines:
        match = pattern.match(line)
        if match:
            current = match.group(1)
            assert current not in result, f"label twice: {current}"
            tag = f"{match.group(2)} " if match.group(2) else ""
            result[current] = [tag + match.group(3)]
        elif current is not None:
            result[current].append(line)
    missing = set(labels) - set(result)
    assert not missing, f"labels not found: {missing}"
    return {label: "\n\n".join(paragraphs) for label, paragraphs in result.items()}


def fetch_features() -> tuple[dict[str, str], dict[str, str]]:
    """(feature name -> description, aspect name -> description)."""
    text = apply_fixes(fetch_text(URL), TEXT_FIXES)
    lines = text.split("\n")
    start = lines.index("Der Jäger besitzt die folgenden Klassenmerkmale:") + 1
    features = split_labeled(lines[start:], [name for name, _levels in FEATURES])
    aspect_lines = features["Tieraspekt"].split("\n\n")
    aspects = split_labeled(aspect_lines, ASPECTS)
    return features, aspects


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
    features, aspects = fetch_features()
    class_id = JAEGER_ID

    # ---- base_classes.json / classes.json ----
    base_classes = [c for c in load("base_classes.json") if c["id"] != class_id]
    base_classes.append(
        {
            "id": class_id,
            "name": "Jäger",
            "hit_dice": 8,
            "arch_class_of": None,
            "casting_ability": "WE",
            "spell_tradition": "divine",
            "bab_progression": 0.75,
            "fort_save": True,
            "ref_save": True,
            "wil_save": False,
            "skill_points_base": 6,
            "allowed_alignments": ALIGNMENTS,
        }
    )
    save("base_classes.json", base_classes)

    class_defs = [c for c in json.loads((FIXTURES / "classes.json").read_text(encoding="utf-8")) if c["name"] != "Jäger"]
    class_defs.append(
        {"name": "Jäger", "skillPointsBase": 6, "spellType": "spontaneous", "classSkills": [], "optionGroups": []}
    )
    (FIXTURES / "classes.json").write_text(json.dumps(class_defs, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    # ---- base_class_skills.json ----
    skill_id_by_name = {row["name"]: row["id"] for row in load("base_skills.json")}
    class_skills = [row for row in load("base_class_skills.json") if row["base_class_id"] != class_id]
    for name in CLASS_SKILLS:
        class_skills.append(
            {
                "id": uid("classskill", name),
                "base_class_id": class_id,
                "skill_id": skill_id_by_name[name],
                "option_choice_id": None,
            }
        )
    save("base_class_skills.json", class_skills)

    # ---- favored_class_bonus group + its generic hp/skill choices ----
    # The choice ids are `add_generic_favored_class_bonus_choices.py`'s own,
    # so rerunning that script doesn't duplicate them.
    groups = load("base_class_option_groups.json")
    fcb_group_id = uid("group", "favored_class_bonus")
    groups.append(
        {
            "id": fcb_group_id,
            "base_class_id": class_id,
            "key": "favored_class_bonus",
            "label": "Bevorzugte Klasse",
            "max_choices": 20,
            "is_secondary_class_initial_pick": False,
        }
    )
    save("base_class_option_groups.json", groups)
    choices = load("base_class_option_choices.json")
    for value in ("hp", "skill"):
        choices.append(
            {
                "id": str(uuid.uuid5(FCB_ID_NAMESPACE, f"generic-fcb-choice|{value}|{class_id}")),
                "group_id": fcb_group_id,
                "name": value,
                "min_level": None,
                "requires_choice_id": None,
                "race_id": None,
            }
        )
    for race_name, race_id, _description in RACE_FAVORED_CLASS_BONUSES:
        choices.append(
            {
                "id": uid("fcb-choice", race_name),
                "group_id": fcb_group_id,
                "name": f"{race_name} (Jäger)",
                "min_level": None,
                "requires_choice_id": None,
                "race_id": race_id,
            }
        )
    save("base_class_option_choices.json", choices)

    # ---- base_class_abilities.json + base_class_ability_grants.json ----
    abilities = load("base_class_abilities.json")
    abilities_by_id = {a["id"]: a for a in abilities}
    grants = [g for g in load("base_class_ability_grants.json") if g["base_class_id"] != class_id]

    def add_ability(name: str, description: str, extra: dict | None = None) -> str:
        aid = uid("ability", name)
        row = {"id": aid, "name": name, "description": description, **(extra or {})}
        if aid in abilities_by_id:
            abilities_by_id[aid].clear()
            abilities_by_id[aid].update(row)
        else:
            abilities.append(row)
            abilities_by_id[aid] = row
        return aid

    def add_grant(ability_id: str, level: int) -> None:
        grants.append(
            {
                "id": uid("grant", ability_id, str(level)),
                "base_class_id": class_id,
                "ability_id": ability_id,
                "option_choice_id": None,
                "level": level,
            }
        )

    ability_id_by_name: dict[str, str] = {}
    for name, levels in FEATURES:
        if name == "Tierempathie":
            continue
        ability_name = RENAMED.get(name, name)
        aid = add_ability(ability_name, features[name], ACTIVATABLE.get(ability_name))
        ability_id_by_name[ability_name] = aid
        for level in levels:
            add_grant(aid, level)
        if ability_name == "Tieraspekt":
            companion_aid = add_ability(
                COMPANION_ASPECT_NAME, COMPANION_ASPECT_DESC, {"is_persistent_effect": True, "activation_scope": "self"}
            )
            ability_id_by_name[COMPANION_ASPECT_NAME] = companion_aid
            add_grant(companion_aid, 1)
    # The aspects: options of Tieraspekt and Tieraspekt (Tiergefährte), not granted.
    aspect_ids = []
    for aspect in ASPECTS:
        aid = add_ability(f"Tieraspekt: {aspect}", f"(ÜF) Aspekt des Tieraspekts: {aspects[aspect]}")
        ability_id_by_name[f"Tieraspekt: {aspect}"] = aid
        aspect_ids.append(aid)
    parents = [ability_id_by_name["Tieraspekt"], ability_id_by_name[COMPANION_ASPECT_NAME]]
    effect_options = [o for o in load("base_class_ability_effect_options.json") if o["parent_ability_id"] not in parents]
    effect_options += [
        {"id": uid("effect-option", parent, aid), "parent_ability_id": parent, "option_ability_id": aid}
        for parent in parents
        for aid in aspect_ids
    ]
    save("base_class_ability_effect_options.json", effect_options)

    abilities_by_id[TIEREMPATHIE_ABILITY_ID]["description"] = TIEREMPATHIE_SHARED_DESC
    add_grant(TIEREMPATHIE_ABILITY_ID, 1)
    for race_name, _race_id, description in RACE_FAVORED_CLASS_BONUSES:
        choice_id = uid("fcb-choice", race_name)
        grants.append(
            {
                "id": uid("grant", choice_id),
                "base_class_id": class_id,
                "ability_id": add_ability(f"{race_name} (Jäger)", description),
                "option_choice_id": choice_id,
                "level": 1,
            }
        )
    save("base_class_abilities.json", abilities)
    save("base_class_ability_grants.json", grants)

    # ---- proficiencies + bonus feat options ----
    feat_id_by_name = {row["name"]: row["id"] for row in load("base_feats.json")}
    proficiency_ability_id = ability_id_by_name["Umgang mit Waffen und Rüstungen"]
    granted_feats = load("base_class_ability_granted_feats.json")
    for feat_name in PROFICIENCY_FEATS:
        feat_id = feat_id_by_name[feat_name]
        granted_feats.append(
            {"id": uid("grantedfeat", proficiency_ability_id, feat_id), "ability_id": proficiency_ability_id, "feat_id": feat_id}
        )
    save("base_class_ability_granted_feats.json", granted_feats)

    feat_options = load("base_class_ability_feat_options.json")
    precise_id = ability_id_by_name["Genaues Ausmanövrieren"]
    for feat_name in GENAUES_AUSMANOEVRIEREN_FEATS:
        feat_options.append(
            {
                "id": uid("featoption", precise_id, feat_name),
                "ability_id": precise_id,
                "option_choice_id": None,
                "feat_type": None,
                "feat_id": feat_id_by_name[feat_name],
            }
        )
    teamwork_id = ability_id_by_name["Gemeinschaftstalente"]
    feat_options.append(
        {
            "id": uid("featoption", teamwork_id, "teamwork"),
            "ability_id": teamwork_id,
            "option_choice_id": None,
            "feat_type": "teamwork",
            "feat_id": None,
        }
    )
    save("base_class_ability_feat_options.json", feat_options)

    # ---- spell list, spells known, granted summon spells ----
    class_spells = load("base_class_spells.json")
    druide_grades = {r["spell_id"]: r["grade"] for r in class_spells if r["base_class_id"] == DRUIDE_ID}
    ranger_grades = {r["spell_id"]: r["grade"] for r in class_spells if r["base_class_id"] == WALDLAEUFER_ID}
    grade_by_spell: dict[str, int] = {}
    for spell_id, grade in [*druide_grades.items(), *ranger_grades.items()]:
        if grade <= MAX_GRADE:
            grade_by_spell[spell_id] = min(grade, grade_by_spell.get(spell_id, grade))
    class_spells = [r for r in class_spells if r["base_class_id"] != class_id]
    for spell_id, grade in sorted(grade_by_spell.items()):
        class_spells.append({"id": uid("spell", spell_id), "base_class_id": class_id, "spell_id": spell_id, "grade": grade})
    save("base_class_spells.json", class_spells)

    spells_known = [r for r in load("base_class_spells_known.json") if r["base_class_id"] != class_id]
    for level, counts in SPELLS_KNOWN.items():
        for grade, count in counts.items():
            spells_known.append(
                {
                    "id": uid("spellsknown", str(level), str(grade)),
                    "base_class_id": class_id,
                    "level": level,
                    "grade": grade,
                    "count": count,
                    "spells_per_day": None,
                }
            )
    save("base_class_spells_known.json", spells_known)

    spell_id_by_name = {s["name"]: s["id"] for s in load("base_spells.json")}
    unlock_level = {grade: min(lvl for lvl, counts in SPELLS_KNOWN.items() if grade in counts) for grade in range(1, 7)}
    spell_grants = [g for g in load("base_class_spell_grants.json") if g["base_class_id"] != class_id]
    for name in SUMMON_SPELLS:
        spell_id = spell_id_by_name[name]
        level = unlock_level[grade_by_spell[spell_id]]
        spell_grants.append(
            {"id": uid("spellgrant", spell_id), "base_class_id": class_id, "option_choice_id": None, "spell_id": spell_id, "level": level}
        )
    save("base_class_spell_grants.json", spell_grants)

    # ---- companion slot: the Druide's species ----
    companion_id = ability_id_by_name["Tiergefährte (Jäger)"]
    slot_grants = load("base_companion_slot_grants.json")
    druide_slot = next(s for s in slot_grants if s["class_ability_id"] == DRUIDE_COMPANION_ABILITY_ID)
    slot_id = uid("slot", companion_id)
    slot_grants.append(
        {"id": slot_id, "class_ability_id": companion_id, "track": "animal_companion", "slot_key": "primary",
         "level_offset": 0, "divisor": 1, "minimum": None}
    )
    save("base_companion_slot_grants.json", slot_grants)
    slot_species = [s for s in load("base_companion_slot_species.json") if s["slot_grant_id"] != slot_id]
    for row in [s for s in slot_species if s["slot_grant_id"] == druide_slot["id"]]:
        slot_species.append(
            {"id": uid("slot-species", slot_id, row["race_id"]), "slot_grant_id": slot_id, "race_id": row["race_id"],
             "master_sizes": row["master_sizes"], "min_level": row["min_level"]}
        )
    save("base_companion_slot_species.json", slot_species)

    print("Jäger:", class_id)
    print("Spells:", len(grade_by_spell), "by grade", {g: list(grade_by_spell.values()).count(g) for g in range(7)})
    for name in sorted(ability_id_by_name):
        print(f"{name}: {ability_id_by_name[name]}")


if __name__ == "__main__":
    main()
