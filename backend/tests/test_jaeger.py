"""Jäger as a complete class (https://prd.5footstep.de/Ausbauregeln-VI-Klassen/
Klassen/Jäger, `scripts/import_jaeger.py`, `rules/classes/jaeger.py`)."""

from collections import Counter
from types import SimpleNamespace

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.rules.classes.druide import tierempathie_bonus
from app.rules.classes.jaeger import JAEGER_ROOT_CLASS_ID
from app.rules.context import CharacterContext
from app.rules.feat_slots import class_bonus_feat_slot_count

from test_characters import _character_payload, _create_user, _human_race_id, _race_id
from test_companions import _companion, _master

STIER = "42ceecf5-0cae-5f11-976a-f3fa43bc14cc"
HIRSCH = "bb58fd3b-9ede-5a48-aa59-92347cf4bc53"
SUMMON_I = "88d2ce0b-535f-507e-a226-8351d81c5e30"
SUMMON_II = "d24a3e2e-cd91-59a1-ad39-cb1e826ee8e2"
SUMMON_III = "511b7dea-0cec-555a-8eae-f4d6ac1288af"


def _create(client: TestClient, db_session: Session, level: int, **overrides):
    """Human with the flex +2 on CH (CH 10, mod +0)."""
    payload = _character_payload(
        _create_user(client),
        _human_race_id(client, db_session),
        db_session,
        classes=[{"class_name": "Jäger", "level": level}],
        flex_ability="CH",
        **overrides,
    )
    return client.post("/api/characters", json=payload)


def _jaeger(client: TestClient, db_session: Session, level: int, **overrides) -> dict:
    response = _create(client, db_session, level, **overrides)
    assert response.status_code == 201, response.text
    return client.get(f"/api/characters/{response.json()['id']}").json()


def _features(sheet: dict) -> dict[str, dict]:
    return {f["name"]: f for f in sheet["classFeatures"]}


def _jaeger_class(client: TestClient) -> dict:
    return next(c for c in client.get("/api/classes").json() if c["name"] == "Jäger")


def _activate(client: TestClient, sheet: dict, ability_id: str) -> dict:
    response = client.post(
        f"/api/characters/{sheet['id']}/effects", json={"source_type": "class_ability", "source_id": ability_id}
    )
    assert response.status_code == 201, response.text
    return client.get(f"/api/characters/{sheet['id']}").json()


def _score(sheet: dict, key: str) -> int:
    return next(a for a in sheet["abilities"] if a["key"] == key)["score"]


def test_class_row_matches_the_table(client: TestClient, db_session: Session) -> None:
    _character_payload(_create_user(client), _human_race_id(client, db_session), db_session)
    jaeger = _jaeger_class(client)
    skills = {s["id"]: s["name"] for s in client.get("/api/skills").json()}

    assert (jaeger["hitDice"], jaeger["babProgression"]) == (8, 0.75)
    assert (jaeger["fortSave"], jaeger["refSave"], jaeger["willSave"]) == (True, True, False)
    assert (jaeger["skillPointsBase"], jaeger["castingAbility"], jaeger["spellType"]) == (6, "WE", "spontaneous")
    assert set(jaeger["allowedAlignments"]) == {"NG", "LN", "N", "CN", "NE"}
    assert len(jaeger["classSkills"]) == 15
    assert {"Heimlichkeit", "Wissen (Gewölbekunde)", "Einschüchtern"} <= {skills[s] for s in jaeger["classSkills"]}
    assert jaeger["archetypes"] == [
        "Keiner",
        "Bruder des Ungeziefergefährten",
        "Bruder des Urzeitgefährten",
        "Göttlicher Jäger",
        "Rudelführer",
        "Wilder Jäger",
    ]


def test_bonus_feat_slots(client: TestClient, db_session: Session) -> None:
    _character_payload(_create_user(client), _human_race_id(client, db_session), db_session)
    jaeger = _jaeger_class(client)

    assert jaeger["bonusFeatLevels"] == [2, 3, 6, 9, 12, 15, 18]
    # Genaues Ausmanövrieren: closed list, prerequisites waived.
    assert {f["name"] for f in jaeger["bonusFeatOptionsByLevel"]["2"]["feats"]} == {"Präzisionsschuss", "Ausmanövrieren"}
    assert jaeger["bonusFeatOptionsByLevel"]["3"] == {"types": ["teamwork"], "feats": []}
    selections = [SimpleNamespace(class_name="Jäger", level=9, archetypes=[])]
    assert class_bonus_feat_slot_count(db_session, selections) == 4


def test_teamwork_feats_are_in_the_catalog(client: TestClient, db_session: Session) -> None:
    _character_payload(_create_user(client), _human_race_id(client, db_session), db_session)
    feats = {f["name"]: f for f in client.get("/api/feats").json()}

    teamwork = {name for name, f in feats.items() if f["type"] == "teamwork"}
    assert len(teamwork) == 41  # 40 imported + Hordensturmangriff
    assert {"Ausmanövrieren", "Rudelangriff", "Rücken an Rücken", "Flankierender Tiergefährte"} <= teamwork
    assert "Befreiender Schlag" not in feats


def test_level_20_has_every_class_feature(client: TestClient, db_session: Session) -> None:
    features = _features(_jaeger(client, db_session, 20))

    assert {
        "Umgang mit Waffen und Rüstungen",
        "Zauber",
        "Stoßgebete",
        "Tieraspekt",
        "Tieraspekt: Wolf",
        "Tierempathie",
        "Tiergefährte (Jäger)",
        "Naturausbildung",
        "Genaues Ausmanövrieren",
        "Spuren lesen",
        "Gemeinschaftstalente",
        "Jägertaktiken",
        "Verbesserte Empathische Verbindung",
        "Unterholz durchqueren",
        "Bonustricks",
        "Schneller Verfolger",
        "Zweiter Tieraspekt",
        "Toten Tiergefährten erwecken",
        "Mit Meister sprechen",
        "Mächtige Empathische Verbindung",
        "Eins mit der Wildnis",
        "Nimrod",
    } <= set(features)
    assert features["Tieraspekt"]["summary"] == "20 Minuten/Tag; Fertigkeitsaspekte +8, Attributsaspekte +6"
    assert features["Bonustricks"]["summary"] == "Tiergefährte: +3 Bonustricks"
    assert features["Tierempathie"]["summary"].startswith("1W20 + 20")


def test_tierempathie_sums_jaeger_with_druide_levels() -> None:
    context = CharacterContext(level_counts_by_root_id={JAEGER_ROOT_CLASS_ID: 3}, ability_scores={"CH": 12})
    assert tierempathie_bonus(context) == 4


def test_spell_list_takes_the_lower_grade(client: TestClient, db_session: Session) -> None:
    _character_payload(_create_user(client), _human_race_id(client, db_session), db_session)
    spells = {s["name"]: s["grade"] for s in client.get("/api/spells-by-class").json()["Jäger"]}

    # The page's own examples: Tier verkleinern (Druide 2, Waldläufer 3) and
    # Gift entdecken (Druide 0, Waldläufer 2).
    assert spells["Tier verkleinern"] == 2
    assert spells["Gift entdecken"] == 0
    assert spells["Aspekt des Hirsches"] == 3  # Waldläufer 3, Druide 4
    assert max(spells.values()) == 6
    assert "Verbündeten der Natur herbeizaubern VII" not in spells


def test_summon_spells_are_known_automatically(client: TestClient, db_session: Session) -> None:
    sheet = _jaeger(client, db_session, 7)
    known = {spell["key"] for grade in sheet["spellsKnown"] for spell in grade["spells"]}

    assert {SUMMON_I, SUMMON_II, SUMMON_III} <= known
    granted = client.get("/api/granted-spells-by-choice").json()["Jäger"]["*"]
    assert [(s["name"], s["level"]) for s in granted][:3] == [
        ("Verbündeten der Natur herbeizaubern I", 1),
        ("Verbündeten der Natur herbeizaubern II", 4),
        ("Verbündeten der Natur herbeizaubern III", 7),
    ]


def test_summon_spell_cant_be_picked_manually(client: TestClient, db_session: Session) -> None:
    _character_payload(_create_user(client), _human_race_id(client, db_session), db_session)
    jaeger_id = _jaeger_class(client)["id"]

    response = _create(client, db_session, 1, spell_ids={jaeger_id: [SUMMON_I]})

    assert response.status_code == 422
    assert "already known automatically" in response.json()["detail"]


def test_level_up_grants_the_next_summon_spell(client: TestClient, db_session: Session) -> None:
    sheet = _jaeger(client, db_session, 3)
    jaeger_id = _jaeger_class(client)["id"]

    response = client.post(
        f"/api/characters/{sheet['id']}/level-up",
        json={
            "target": {"mode": "existing", "base_class_id": jaeger_id},
            "hit_points": 5,
            "favored_class_bonus": "hp",
            "ability_increase": "ST",
        },
    )
    assert response.status_code == 201, response.text
    sheet = client.get(f"/api/characters/{sheet['id']}").json()
    known = {spell["key"] for grade in sheet["spellsKnown"] for spell in grade["spells"]}
    assert {SUMMON_I, SUMMON_II} <= known


def test_tieraspekt_spends_minutes_and_scales_with_level(client: TestClient, db_session: Session) -> None:
    low = _jaeger(client, db_session, 1)
    base = _score(low, "ST")
    low = _activate(client, low, STIER)
    assert _score(low, "ST") == base + 2
    pool = next(a for a in low["actions"] if a.get("name") == "Tieraspekt")
    assert (pool["usesRemainingToday"], pool["usesPerDay"]) == (0, 1)

    high = _jaeger(client, db_session, 8)
    base = _score(high, "ST")
    assert _score(_activate(client, high, STIER), "ST") == base + 4


def test_hirsch_only_counts_from_8th_level(client: TestClient, db_session: Session) -> None:
    low = _jaeger(client, db_session, 5)
    assert _features(low)["Tieraspekt: Hirsch"]["partialNote"].startswith("+1,5 m")
    assert _activate(client, low, HIRSCH)["speed"] == "9 m"

    high = _jaeger(client, db_session, 8)
    assert _activate(client, high, HIRSCH)["speed"] == "12 m"


def test_spuren_lesen_is_a_survival_note(client: TestClient, db_session: Session) -> None:
    sheet = _jaeger(client, db_session, 6)
    survival = next(s for s in sheet["skills"] if s["label"] == "Überlebenskunst")
    assert "Spuren lesen (um Spuren zu folgen)" in survival["note"]
    assert "Spuren lesen +3" in survival["note"]


def test_companion_at_full_jaeger_level_with_extra_bonus_tricks(client: TestClient, db_session: Session) -> None:
    master = _jaeger(client, db_session, 7)
    track = next(t for t in master["companionLevels"] if t["track"] == "animal_companion")
    assert track["level"] == 7
    assert "Wolf" in {s["name"] for s in track["slots"][0]["species"]}

    wolf = _companion(client, master, "Wolf")
    druide_wolf_bonus_tricks = 3  # progression table, effective level 7
    assert wolf["companion"]["trickLimits"]["bonus"]["max"] == druide_wolf_bonus_tricks + 1
    assert any("Jägertaktiken" in note for note in wolf["companion"]["masterNotes"])


def test_bonus_trick_count_follows_the_grants() -> None:
    from app.rules.companions import master_bonus_tricks
    from app.rules.classes.jaeger import BONUSTRICKS_ID

    assert master_bonus_tricks(Counter({BONUSTRICKS_ID: 2})) == 2
    assert master_bonus_tricks(Counter()) == 0


def test_halbork_favored_class_bonus_reaches_the_companion(client: TestClient, db_session: Session) -> None:
    params = {"base_class_name": "Jäger", "race_id": _race_id(client, db_session, "Halb-Ork")}
    options = client.get("/api/favored-class-bonus-options", params=params).json()
    assert "Halb-Ork (Jäger)" in options["options"]
    assert options["shortLabels"]["Halb-Ork (Jäger)"] == "+1 TP Gefährte"

    master = _master(
        client, db_session, [{"class_name": "Jäger", "level": 2}],
        race="Halb-Ork", flex_ability="ST", favored_class_bonus={"1": "Halb-Ork (Jäger)", "2": "Halb-Ork (Jäger)"},
    )
    wolf = _companion(client, master, "Wolf")
    plain_wolf = _companion(client, _jaeger(client, db_session, 2), "Wolf")
    assert wolf["hp"]["max"] == plain_wolf["hp"]["max"] + 2
