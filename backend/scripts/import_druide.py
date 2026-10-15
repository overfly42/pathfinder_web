"""Import the (Grundregelwerk core) Druide's class shell from
http://prd.5footstep.de/Grundregelwerk/Klassen/Druide — roadmap slice 10,
step 0a ("Druide as a complete class"), the prerequisite for animal
companions.

`hit_dice`/`bab_progression`/`fort_save`/`ref_save`/`wil_save`/
`skill_points_base`/`casting_ability`/`spell_tradition` on
`base_classes.json`'s existing Druide row were already correct (W8, 3/4 GAB,
good Fort/Will, 4 + IN, WE, divine) — verified against "Tabelle: Druide",
not re-written. The per-day spell table (`base_class_spells_known.json`) and
the `bond`/`favored_class_bonus` option groups already existed too.

What this script does:
- Fixes `base_class_skills.json`: the existing 9 rows wrongly included
  Entfesselungskunst and were missing Beruf, Fliegen, Handwerk, Wissen
  (Geographie) and Zauberkunde — corrected to the page's own 13-skill list.
  The 8 rows that were already correct keep their row ids (same "look up by
  skill name, don't regenerate" shape as `import_moench.py`). The dropped
  Entfesselungskunst row (`50620e7d-…`) is NOT deleted from an already-seeded
  database by `skill_seed.py`'s upsert — delete it by hand there.
- Adds the class features as `BaseClassAbility`/`BaseClassAbilityGrant`
  rows: Umgang mit Waffen und Rüstungen, Zauber, Spontanes Zaubern, Böse/
  Chaotische/Gute/Rechtschaffene Zauber, Gebete, Bonussprachen, Bund mit der
  Natur, Naturgespür (1), Unterholz durchqueren (2), Spurloser Schritt (3),
  Lockruf der Natur widerstehen (4), Tiergestalt (4), Immunität gegen Gifte
  (9), Tausend Gesichter (13), Zeitloser Körper (15), Ehemalige Druiden (1,
  same descriptive row the Kleriker has).
- Tierempathie: **no new row** (decided 2026-10-14) — the Druide gets a
  level-1 grant of the Waldläufer's existing row `ebd5060b-…`, whose
  description is rewritten class-neutrally here since it's now shared;
  `rules/classes/druide.py` computes the summed Druide + Waldläufer bonus.
- Unterholz durchqueren: a new row, because the Waldläufer's existing one
  (`2b7b62b2-…`) says "Ab der 7. Stufe … ein Waldläufer" — not identical.
- `bond` choices get their choice-scoped grants (`option_choice_id`):
  "Tiergefährte" -> a new "Tiergefährte (Druide)" trigger ability (the hook
  slice 10's `BaseCompanionLevelSource` will key on), "Domäne (Natur)" -> a
  "Domäne (Natur)" ability describing the bond. The domain itself is a new
  one-time option group `nature_domain` ("Naturdomäne") whose 7 choices
  (Erde, Feuer, Luft, Pflanzen, Tiere, Wasser, Wetter) each `requires_choice_id`
  the "Domäne (Natur)" bond choice; every grant the Kleriker gets for the
  same-named domain (overview + both powers, same levels) is duplicated as a
  Druide grant gated on the Druide's choice — the ability rows themselves are
  reused, so the Druide level counts as Kleriker level for the powers simply
  because the grants hang off the Druide class (PRD: "zählt die Stufe des
  Druiden wie die Stufe des Klerikers").
- Proficiencies: light/medium armor and shields via
  `BaseClassAbilityGrantedFeat` (the existing category path); the weapon
  list (Dolch, Kampfstab, Keule, Krummsäbel, Kurzspeer, Schleuder, Sichel,
  Sense, Speer, Wurfpfeil) doesn't line up with a category feat, so it's a
  named-weapon entry in `rules/classes/druide.py`'s
  `WEAPON_PROFICIENCY_HANDLERS` slice instead (same shape as Elf's
  "Elfische Waffenvertrautheit").

Deliberately out of scope (descriptive text only for now, see roadmap
slice 10 / todos.md):
- The domain bonus spell slot ("zusätzlicher Zauberplatz für
  Domänenzauber") — shared open mechanism with the Kleriker's
  "Domänenzauber" item (slice 6), built once for both, separately.
- The alignment restriction (any neutral component) — no alignment field on
  characters exists yet; the Paladin (step 0b) needs the same field.
- Tiergestalt's actual form stats (Bestiengestalt/Elementargestalt/
  Pflanzengestalt) — daily uses are computed, the forms are text.
- The no-metal-armor/wood-only-shield restriction — a rule warning, not a
  proficiency gap.
- Druide archetypes.

Run with the project venv active (this only writes the fixture JSON files,
it doesn't touch the database — run the normal seed scripts afterward):
    cd backend && python scripts/import_druide.py
    python -m app.seed.skill_seed
    python -m app.seed.class_option_seed
    python -m app.seed.class_ability_seed
    python -m app.seed.class_ability_granted_feat_seed
"""

from __future__ import annotations

import json
import uuid
from pathlib import Path

FIXTURES = Path(__file__).resolve().parent.parent / "app" / "fixtures"
SEED_DIR = FIXTURES / "seed"

ID_NAMESPACE = uuid.UUID("5b0f8a51-3c1e-4d7a-9f62-d2e1b7c4a903")

DRUIDE_ID = "2835c712-7129-41fe-a61e-8ef05de2e0cf"
KLERIKER_ID = "1e6e60de-d72f-4910-b19d-55ca11e14190"
KLERIKER_DOMAIN_GROUP_ID = "7b82d11f-eae8-4e79-bb43-aaad60d728ff"
BOND_TIERGEFAEHRTE_CHOICE_ID = "dbea3f3f-b0e0-42c2-8a49-52f6f4bc67df"
BOND_DOMAENE_CHOICE_ID = "bde0d2ad-a8b4-4c13-9153-bbcd60238cfb"

# Shared with the Waldläufer (decided 2026-10-14).
TIEREMPATHIE_ABILITY_ID = "ebd5060b-066a-4bc0-bdfa-064222de85bf"
TIEREMPATHIE_SHARED_DESC = (
    "Der Charakter kann die Einstellung eines Tieres ihm gegenüber verbessern. Diese Fähigkeit funktioniert "
    "genau wie ein Wurf auf Diplomatie, um die Einstellung einer Person zu verändern. Er würfelt 1W20 und "
    "addiert sowohl seine Stufe in der Klasse, die ihm Tierempathie gewährt (Druide bzw. Waldläufer; Stufen "
    "in mehreren solchen Klassen addieren sich), als auch seinen CH-Modifikator zu dem Wurf. Ein zahmes Tier "
    "beginnt mit einer gleichgültigen Einstellung, während ein wildes Tier zunächst unfreundlich ist.\n\n"
    "Um Tierempathie einsetzen zu können, dürfen sich unter normalen Umständen Tier und Charakter nicht "
    "weiter als 9 m voneinander entfernt befinden. Im Allgemeinen dauert das Beeinflussen eines Tieres eine "
    "Minute, im Einzelfall kann es aber auch schneller oder langsamer gehen.\n\n"
    "Mit dieser Fähigkeit kann er auch versuchen, magische Bestien mit einem Intelligenzwert von 1 oder 2 zu "
    "beeinflussen, nimmt dabei jedoch einen Malus von -4 auf seinen Wurf in Kauf."
)

CORRECT_CLASS_SKILLS = [
    "Beruf",
    "Fliegen",
    "Handwerk",
    "Heilkunde",
    "Klettern",
    "Mit Tieren umgehen",
    "Reiten",
    "Schwimmen",
    "Wahrnehmung",
    "Wissen (Geographie)",
    "Wissen (Natur)",
    "Überlebenskunst",
    "Zauberkunde",
]

# Bund mit der Natur's domain sub-choice: Druide-side choice name -> the
# Kleriker domain choice whose grants it mirrors.
NATURE_DOMAINS: list[tuple[str, str]] = [
    ("Domäne der Erde", "Domäne der Erde"),
    ("Domäne des Feuers", "Domäne des Feuers"),
    ("Domäne der Luft", "Domäne der Luft"),
    ("Domäne der Pflanzen", "Domäne der Pflanzen"),
    ("Domäne der Tiere", "Domäne der Tiere"),
    ("Domäne des Wassers", "Domäne des Wassers"),
    ("Domäne des Wetters", "Domäne des Wetters"),
]

PROFICIENCY_FEATS = [
    "Umgang mit Rüstungen (leichte)",
    "Umgang mit Rüstungen (mittelschwere)",
    "Umgang mit Schilden",
]

TIERGESTALT_DESC = (
    "(ÜF) Ab der 4. Stufe erhält der Druide die Fähigkeit, sich ein Mal pro Tag in ein kleines oder "
    "mittelgroßes Tier und wieder zurück zu verwandeln. Er kann sich hierbei für jede Kreatur mit der "
    "Bezeichnung Tier entscheiden. Diese Fähigkeit funktioniert, bis auf folgende Ausnahmen, genau wie der "
    "Zauber Bestiengestalt I. Die Verwandlung hält für eine Stunde pro Druidenstufe an, es sei denn, er "
    "verwandelt sich vorher zurück. Die Verwandlung (in ein Tier oder wieder zurück) ist eine Standard-Aktion "
    "und provoziert keine Gelegenheitsangriffe. Der Druide kann nur eine Tiergestalt wählen, die er kennt.\n\n"
    "In Tiergestalt verliert der Druide seine Fähigkeit zu sprechen und ist auf die Geräusche des "
    "untrainierten Tieres begrenzt. Er kann sich aber sehr wohl mit anderen Tieren seiner neuen Form "
    "verständigen.\n\n"
    "Der Druide kann diese Fähigkeit ab der 6. und dann allen weiteren zwei Stufen ein weiteres Mal pro Tag "
    "nutzen, bis zu einem Maximum von acht Mal auf der 18. Stufe. Mit dem Erreichen der 20. Stufe kann sich "
    "der Druide jederzeit entscheiden, seine Gestalt zu ändern. Jede Verwandlung verbraucht, unabhängig von "
    "der Form, eine Anwendung der Fähigkeit.\n\n"
    "Ab der 6. Stufe kann der Druide sich in ein großes oder sehr kleines Tier verwandeln oder die Gestalt "
    "eines kleinen Elementars annehmen (Bestiengestalt II bzw. Elementargestalt I).\n\n"
    "Auf der 8. Stufe kann er sich in ein riesiges oder winziges Tier verwandeln, oder in einen mittelgroßen "
    "Elementar oder eine kleine oder mittelgroße Pflanzenkreatur (Bestiengestalt III, Elementargestalt II "
    "bzw. Pflanzengestalt I).\n\n"
    "Ab der 10. Stufe kann sich der Druide für eine große Elementargestalt oder die einer großen "
    "Pflanzenkreatur entscheiden (Elementargestalt III bzw. Pflanzengestalt II).\n\n"
    "Ab der 12. Stufe kann sich der Druide für eine riesige Elementargestalt oder die einer riesigen "
    "Pflanzenkreatur entscheiden (Elementargestalt IV bzw. Pflanzengestalt III)."
)

# (name, levels, description)
CLASS_FEATURES: list[tuple[str, list[int], str]] = [
    (
        "Umgang mit Waffen und Rüstungen",
        [1],
        "Der Druide ist im Umgang mit folgenden Waffen geübt: Dolch, Kampfstab, Keule, Krummsäbel, Kurzspeer, "
        "Schleuder, Sichel, Sense, Speer und Wurfpfeil. Er ist ebenfalls mit jeder natürlichen Waffe geübt, die "
        "ihm in Tiergestalt zur Verfügung steht. Druiden sind mit dem Umgang leichter und mittelschwerer "
        "Rüstungen vertraut, dürfen aber keine Metallrüstung tragen, so dass sie die Auswahl zwischen "
        "Waffenrock, Lederrüstung oder Fellrüstung haben. Ein Druide kann auch hölzerne Panzerung tragen, die "
        "mit einem Zauber Eisenholz verändert wurde. Druiden können mit Schilden, außer Turmschilden, umgehen, "
        "dürfen aber nur Schilde einsetzen, die aus Holz hergestellt wurden.\n\n"
        "Ein Druide, der eine verbotene Rüstung trägt oder ein verbotenes Schild einsetzt, kann währenddessen "
        "und danach für weitere 24 Stunden weder zaubern, noch seine übernatürlichen und zauberähnlichen "
        "Klassenmerkmale anwenden.",
    ),
    (
        "Zauber",
        [1],
        "Ein Druide wirkt göttliche Zauber, die er aus der Zauberliste für Druiden auswählt. Ein Druide muss "
        "seine Zauber vorher auswählen und vorbereiten. Um einen Zauber vorbereiten und wirken zu können, muss "
        "der Druide mindestens eine Weisheit von 10 + Grad des Zaubers besitzen. Der SG des Rettungswurfs gegen "
        "die Zauber des Druiden ist 10 + Grad des Zaubers + WE-Modifikator des Druiden. Zusätzlich erhält er "
        "Bonuszauber für eine hohe Weisheit.\n\n"
        "Der Druide verbringt eine Stunde am Tag in einer tranceähnlichen Meditation über die Mysterien der "
        "Natur, um seine Zauber wieder zu erlangen. Er kann jeden Zauber aus der Druidenliste wählen, "
        "vorausgesetzt ihm steht der Grad des Zaubers schon zur Verfügung.",
    ),
    (
        "Spontanes Zaubern",
        [1],
        "Ein Druide kann vorbereitete Zauberkraft nutzen, um Verbündete herbei zu zaubern. Der Druide kann "
        "einen seiner vorbereiteten Zauber aufgeben, um im gleichen oder einem niedrigeren Grad einen "
        "Verbündeten der Natur herbeizaubern zu wirken.",
    ),
    (
        "Böse, Chaotische, Gute und Rechtschaffene Zauber",
        [1],
        "Ein Druide kann keinen Zauber wirken, dessen Gesinnung seiner oder der seiner Gottheit (wenn er einer "
        "folgt) entgegensteht. Zauber, die eine bestimmte Gesinnung voraussetzen, tragen eine entsprechende "
        "Bezeichnung in der Zauberbeschreibung.",
    ),
    (
        "Gebete",
        [1],
        "Der Druide kann jeden Tag eine Anzahl von Gebeten, oder Zaubern des 0. Grades, vorbereiten, wie es der "
        "Angabe in der Tabelle: Druide unter Zauber pro Tag entspricht. Diese Zauber werden wie andere Zauber "
        "gewirkt, nur dass sie keinen Zauberplatz verbrauchen und wieder verwendet werden dürfen.",
    ),
    (
        "Bonussprachen",
        [1],
        "Ein Druide kann, zusätzlich zu der Auswahl seines Volks, Sylvanisch, die Sprache der Waldkreaturen, "
        "lernen.\n\n"
        "Der Druide lernt auf der 1. Stufe zudem die geheime Sprache Druidisch. Diese Sprache erhält der Druide "
        "zusätzlich zu seinen sonstigen Sprachen. Druiden ist es verboten, diese Sprache an andere "
        "weiterzugeben. Druidisch verfügt über ein eigenes Alphabet.",
    ),
    (
        "Bund mit der Natur",
        [1],
        "(AF) Ein Druide der 1. Stufe geht einen Bund mit der Natur ein. Dieser kann zwei verschiedene Formen "
        "haben und der Druide muss sich für eine entscheiden: entweder einen engen Bund mit der Natur, der ihm "
        "Zugriff auf eine der Klerikerdomänen Erde, Feuer, Luft, Pflanzen, Tiere, Wasser oder Wetter gewährt, "
        "oder einen Tiergefährten.",
    ),
    (
        "Naturgespür",
        [1],
        "(AF) Der Druide erhält einen Fertigkeitsbonus von +2 auf Würfe für Wissen (Natur) und "
        "Überlebenskunst.",
    ),
    (
        "Unterholz durchqueren",
        [2],
        "(AF) Ab der 2. Stufe kann sich ein Druide mit seiner vollen Bewegungsrate durch jede Art von Unterholz "
        "(wie natürliche Dornen, Gestrüpp, verwilderte Landschaften und ähnliches Terrain) bewegen, ohne "
        "Verletzungen oder Behinderungen zu erleiden. Dornen und anderes Unterholz, das magisch verändert "
        "wurde, um die Bewegung zu erschweren, betreffen den Druiden jedoch normal.",
    ),
    (
        "Spurloser Schritt",
        [3],
        "(AF) Ab der 3. Stufe hinterlässt der Druide in natürlicher Umgebung keine Spuren und kann auch mit "
        "Spurenlesen nicht verfolgt werden. Er kann sich aber durchaus dazu entscheiden, Spuren zu "
        "hinterlassen.",
    ),
    (
        "Lockruf der Natur widerstehen",
        [4],
        "(AF) Ab der 4. Stufe erhält der Druide einen Bonus von +4 auf Rettungswürfe gegen zauberähnliche und "
        "übernatürliche Fähigkeiten von Feenwesen. Dieser Bonus wirkt auch bei Zaubern, die Pflanzen "
        "betreffen, wie Dornenwuchs, Dürre, Holz krümmen und Verstricken.",
    ),
    ("Tiergestalt", [4], TIERGESTALT_DESC),
    ("Immunität gegen Gifte", [9], "(AF) Ab der 9. Stufe wird der Druide immun gegen jedes Gift."),
    (
        "Tausend Gesichter",
        [13],
        "(ÜF) Ab der 13. Stufe kann der Druide sein Aussehen jederzeit ändern. Die Fähigkeit wirkt wie der "
        "Zauber Gestalt verändern. Er kann dieses nur, solange er in seiner natürlichen Form ist.",
    ),
    (
        "Zeitloser Körper",
        [15],
        "(AF) Mit dem Erreichen der 15. Stufe nimmt der Druide keine Abzüge auf die Attribute durch das Altern "
        "mehr in Kauf und kann auch nicht auf magische Weise altern. Veränderungen, die er vorher erhalten hat, "
        "werden hiervon nicht betroffen. Boni für das Alter erhält er weiterhin und er stirbt auch, wenn seine "
        "Zeit gekommen ist.",
    ),
    (
        "Ehemalige Druiden",
        [1],
        "Ein Druide, der aufhört, die Natur zu verehren, zu einer verbotenen Gesinnung wechselt oder einem "
        "Nicht-Druiden Druidisch beibringt, verliert sowohl seine Zauber und Druidenfähigkeiten als auch seinen "
        "Tiergefährten. Die Fähigkeiten im Umgang mit Waffen und Rüstungen sind nicht betroffen. Er kann auch "
        "nicht weiter als Druide aufsteigen, bis er Buße getan hat (siehe den Zauber Buße).",
    ),
]

# Choice-scoped abilities for the existing `bond` group's two choices.
BOND_ABILITIES: list[tuple[str, str, str]] = [
    (
        BOND_TIERGEFAEHRTE_CHOICE_ID,
        "Tiergefährte (Druide)",
        "(AF) Der Druide beginnt das Spiel mit einem Tiergefährten. Der Gefährte ist dem Druiden gegenüber "
        "loyal und begleitet ihn auf seine Abenteuer, wie es für seine Tierart angemessen ist.\n\n"
        "Anders als bei normalen Tieren steigen bei einem Tiergefährten die Trefferwürfel, seine Attribute, "
        "seine Fertigkeiten und seine Talente in einem ähnlichem Maße, wie auch der Druide neue Stufen erlangt. "
        "Sollte ein Charakter einen Tiergefährten aus mehr als einer Quelle erhalten, addieren sich seine "
        "effektiven Druidenstufen, wenn es darum geht, die Spielwerte und Fähigkeiten des Gefährten zu "
        "ermitteln. Die meisten Tiergefährten wachsen in ihrer Größe, wenn der Druide die 4. oder 7. Stufe "
        "erreicht, abhängig von der Tierart des Gefährten. Entlässt ein Druide einen Tiergefährten aus seinem "
        "Dienst, kann er nach einem Ritual von 24 Stunden ununterbrochenen Gebets in der Umgebung, wo die "
        "Tierart des neuen Gefährten normalerweise seinen Lebensraum hat, einen neuen Gefährten an sich binden. "
        "Mit einem solchen Ritual kann der Druide auch einen neuen Gefährten erlangen, wenn sein bisheriger "
        "Tiergefährte gestorben ist.",
    ),
    (
        BOND_DOMAENE_CHOICE_ID,
        "Domäne (Natur)",
        "(AF) Der Druide geht einen engen Bund mit der Natur ein, der ihm Zugriff auf eine der Klerikerdomänen "
        "Erde, Feuer, Luft, Pflanzen, Tiere, Wasser oder Wetter gewährt (Auswahl unter „Naturdomäne“). Um die "
        "Kräfte und Zauber dieser Domäne zu bestimmen, zählt die Stufe des Druiden wie die Stufe des Klerikers. "
        "Ein Druide, der diese Form des Bundes wählt, erhält außerdem einen zusätzlichen Zauberplatz für "
        "Domänenzauber, genau wie ein Kleriker. Er muss einen Domänenzauber in diesem Zauberplatz vorbereiten "
        "und kann diesen Zauber nicht einsetzen, um einen spontanen Zauber zu wirken.",
    ),
]

NATURE_DOMAIN_GROUP = {
    "key": "nature_domain",
    "label": "Naturdomäne",
    "max_choices": 1,
    "is_secondary_class_initial_pick": False,
}


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
    class_id = DRUIDE_ID

    # ---- base_class_skills.json ----
    skills = load("base_skills.json")
    skill_id_by_name = {row["name"]: row["id"] for row in skills}
    skill_name_by_id = {row["id"]: row["name"] for row in skills}
    for name in CORRECT_CLASS_SKILLS:
        assert name in skill_id_by_name, f"missing skill: {name}"

    class_skills = load("base_class_skills.json")
    existing_row_id_by_skill_name = {
        skill_name_by_id[row["skill_id"]]: row["id"]
        for row in class_skills
        if row["base_class_id"] == class_id and row.get("option_choice_id") is None and row["skill_id"] in skill_name_by_id
    }
    class_skills = [
        row for row in class_skills if not (row["base_class_id"] == class_id and row.get("option_choice_id") is None)
    ]
    for name in CORRECT_CLASS_SKILLS:
        class_skills.append(
            {
                "id": existing_row_id_by_skill_name.get(name) or uid("druide-classskill", name),
                "base_class_id": class_id,
                "skill_id": skill_id_by_name[name],
                "option_choice_id": None,
            }
        )
    save("base_class_skills.json", class_skills)

    # ---- base_class_option_groups.json / base_class_option_choices.json ----
    groups = load("base_class_option_groups.json")
    group_id = uid("druide-group", NATURE_DOMAIN_GROUP["key"])
    groups.append({"id": group_id, "base_class_id": class_id, **NATURE_DOMAIN_GROUP})
    save("base_class_option_groups.json", groups)

    choices = load("base_class_option_choices.json")
    kleriker_choice_id_by_name = {c["name"]: c["id"] for c in choices if c["group_id"] == KLERIKER_DOMAIN_GROUP_ID}
    druide_choice_id_by_name: dict[str, str] = {}
    for name, kleriker_name in NATURE_DOMAINS:
        assert kleriker_name in kleriker_choice_id_by_name, f"missing Kleriker domain: {kleriker_name}"
        choice_id = uid("druide-nature-domain", name)
        druide_choice_id_by_name[name] = choice_id
        choices.append(
            {
                "id": choice_id,
                "group_id": group_id,
                "name": name,
                "min_level": None,
                "requires_choice_id": BOND_DOMAENE_CHOICE_ID,
                "race_id": None,
            }
        )
    save("base_class_option_choices.json", choices)

    # ---- base_class_abilities.json + base_class_ability_grants.json ----
    abilities = load("base_class_abilities.json")
    abilities_by_id = {a["id"]: a for a in abilities}
    grants = load("base_class_ability_grants.json")

    def add_ability(key: str, name: str, description: str) -> str:
        aid = uid("druide-ability", key)
        if aid in abilities_by_id:
            abilities_by_id[aid].update(name=name, description=description)
        else:
            row = {"id": aid, "name": name, "description": description}
            abilities.append(row)
            abilities_by_id[aid] = row
        return aid

    def add_grant(ability_id: str, level: int, option_choice_id: str | None = None) -> None:
        grants.append(
            {
                "id": uid("druide-grant", ability_id, str(level), option_choice_id or ""),
                "base_class_id": class_id,
                "ability_id": ability_id,
                "option_choice_id": option_choice_id,
                "level": level,
            }
        )

    ability_id_by_name: dict[str, str] = {}
    for name, levels, description in CLASS_FEATURES:
        aid = add_ability(name, name, description)
        ability_id_by_name[name] = aid
        for level in levels:
            add_grant(aid, level)

    abilities_by_id[TIEREMPATHIE_ABILITY_ID]["description"] = TIEREMPATHIE_SHARED_DESC
    add_grant(TIEREMPATHIE_ABILITY_ID, 1)

    for choice_id, name, description in BOND_ABILITIES:
        add_grant(add_ability(name, name, description), 1, choice_id)

    kleriker_domain_grants = [
        g for g in grants if g["base_class_id"] == KLERIKER_ID and g["option_choice_id"] is not None
    ]
    mirrored = 0
    for name, kleriker_name in NATURE_DOMAINS:
        kleriker_choice_id = kleriker_choice_id_by_name[kleriker_name]
        for grant in kleriker_domain_grants:
            if grant["option_choice_id"] == kleriker_choice_id:
                add_grant(grant["ability_id"], grant["level"], druide_choice_id_by_name[name])
                mirrored += 1

    save("base_class_abilities.json", abilities)
    save("base_class_ability_grants.json", grants)

    # ---- base_class_ability_granted_feats.json ----
    feat_id_by_name = {row["name"]: row["id"] for row in load("base_feats.json")}
    proficiency_ability_id = ability_id_by_name["Umgang mit Waffen und Rüstungen"]
    granted_feats = load("base_class_ability_granted_feats.json")
    for feat_name in PROFICIENCY_FEATS:
        feat_id = feat_id_by_name[feat_name]
        granted_feats.append(
            {
                "id": uid("druide-grantedfeat", proficiency_ability_id, feat_id),
                "ability_id": proficiency_ability_id,
                "feat_id": feat_id,
            }
        )
    save("base_class_ability_granted_feats.json", granted_feats)

    print("Class skills:", len(CORRECT_CLASS_SKILLS))
    print("Class features:", len(CLASS_FEATURES), "+ shared Tierempathie")
    print("Nature domain grants mirrored from Kleriker:", mirrored)
    for name in ("Umgang mit Waffen und Rüstungen", "Naturgespür", "Tiergestalt"):
        print(f"{name}: {ability_id_by_name[name]}")
    for _choice_id, name, _description in BOND_ABILITIES:
        print(f"{name}: {uid('druide-ability', name)}")
    print("Done.")


if __name__ == "__main__":
    main()
