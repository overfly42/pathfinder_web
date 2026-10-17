"""Paladin as a complete class — roadmap slice 10, step 0b
(http://prd.5footstep.de/Grundregelwerk/Klassen/Paladin,
`scripts/import_paladin.py`, `rules/classes/paladin.py`), plus the
character alignment it needs (`rules/alignment.py`)."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.rules.classes.paladin import (
    PALADIN_ROOT_CLASS_ID,
    divine_bond_uses_per_day,
    divine_bond_weapon_bonus,
    lay_on_hands_uses_per_day,
    smite_uses_per_day,
)
from app.rules.context import CharacterContext
from app.seed.class_option_seed import seed_class_options
from app.seed.class_seed import seed_classes
from app.seed.skill_seed import seed_skills
from app.seed.spell_seed import seed_spells

from test_characters import _character_payload, _create_user, _human_race_id, _item_id
from test_weapon_slots import _equip, _weapon_attack

BOESES_NIEDERSTRECKEN_ABILITY_ID = "e6a08f37-293c-5f74-a0d8-dd46898f9507"
HANDAUFLEGEN_ABILITY_ID = "d76a1967-add5-5759-9545-846f8c099ebb"
POSITIVE_ENERGIE_FOKUSSIEREN_ABILITY_ID = "281d97af-1d40-58b2-a628-6099669060f0"
GOETTLICHER_BUND_WAFFE_ABILITY_ID = "61ef7479-f6f8-5e0a-86da-eeddd4949d44"
REITTIER_HERBEIRUFEN_ABILITY_ID = "4d1f8309-3afd-5df9-a341-3af26025fee9"

# ST 14 (+2), CH 14 + the human flex +2 = 16 (+3); 5+0+2-2+0+5 = 10 points.
PALADIN_SCORES = {"ST": 14, "GE": 10, "KO": 12, "IN": 8, "WE": 10, "CH": 14}


def _payload(client: TestClient, db_session: Session, classes: list[dict], **overrides) -> dict:
    user_id = _create_user(client)
    race_id = _human_race_id(client, db_session)
    fields = {"flex_ability": "CH", "ability_scores": PALADIN_SCORES, "alignment": "LG", **overrides}
    return _character_payload(user_id, race_id, db_session, classes=classes, **fields)


def _create_paladin(client: TestClient, db_session: Session, level: int, options: dict | None = None, **overrides) -> dict:
    payload = _payload(
        client, db_session, [{"class_name": "Paladin", "level": level, "options": options or {}}], **overrides
    )
    response = client.post("/api/characters", json=payload)
    assert response.status_code == 201, response.text
    return client.get(f"/api/characters/{response.json()['id']}").json()


def _feature(sheet: dict, name: str) -> dict | None:
    return next((f for f in sheet["classFeatures"] if f["name"] == name), None)


def _action(sheet: dict, source_id: str) -> dict:
    return next(a for a in sheet["actions"] if a["sourceId"] == source_id)


def _save(sheet: dict, key: str) -> int:
    return int(next(s for s in sheet["saves"] if s["key"] == key)["value"])


def _paladin_class(client: TestClient, db_session: Session) -> dict:
    seed_classes(db_session)
    seed_class_options(db_session)
    seed_skills(db_session)
    return next(c for c in client.get("/api/classes").json() if c["name"] == "Paladin")


def test_paladin_class_skills_are_the_pages_10(client: TestClient, db_session: Session) -> None:
    paladin = _paladin_class(client, db_session)
    skills = {s["id"]: s["name"] for s in client.get("/api/skills").json()}

    assert {skills[sid] for sid in paladin["classSkills"]} == {
        "Beruf",
        "Diplomatie",
        "Handwerk",
        "Heilkunde",
        "Mit Tieren umgehen",
        "Motiv erkennen",
        "Reiten",
        "Wissen (Adel)",
        "Wissen (Religion)",
        "Zauberkunde",
    }


def test_paladin_casts_divine_from_charisma_from_level_4(client: TestClient, db_session: Session) -> None:
    seed_spells(db_session)
    paladin = _paladin_class(client, db_session)

    assert paladin["castingAbility"] == "CH"
    assert paladin["spellTradition"] == "divine"
    assert paladin["spellType"] == "divine-prepared"
    assert "3" not in paladin["spellsKnownByLevel"]
    assert set(paladin["spellsKnownByLevel"]["4"]) == {"1"}
    assert set(paladin["spellsKnownByLevel"]["13"]) == {"1", "2", "3", "4"}

    spells = client.get("/api/spells-by-class").json()
    names = {s["name"] for s in spells["Paladin"]}
    # A spell already on other lists and one only the Paladin casts.
    assert {"Segnen", "Böses herausfordern"} <= names


def test_paladin_level_20_has_every_class_feature(client: TestClient, db_session: Session) -> None:
    sheet = _create_paladin(
        client,
        db_session,
        20,
        {"divine_bond": ["Reittier"], "mercy": ["Erschöpft", "Erschüttert", "Krank", "Entkräftet", "Blind", "Taub"]},
    )
    names = {f["name"] for f in sheet["classFeatures"]}

    assert {
        "Umgang mit Waffen und Rüstungen",
        "Aura des Guten",
        "Böses entdecken",
        "Böses niederstrecken",
        "Göttliche Würde",
        "Handauflegen",
        "Aura der Tapferkeit",
        "Göttliche Gesundheit",
        "Gnade",
        "Positive Energie fokussieren",
        "Zauber",
        "Göttlicher Bund",
        "Aura der Entschlossenheit",
        "Aura der Gerechtigkeit",
        "Aura des Glaubens",
        "Aura der Rechtschaffenheit",
        "Heiliger Streiter",
        "Göttlicher Bund: Reittier",
        "Reittier herbeirufen",
        "Gnade: Erschöpft",
        "Gnade: Entkräftet",
        "Gnade: Taub",
    } <= names
    assert "Göttlicher Bund: Waffe" not in names
    assert "Gnade: Kränkelnd" not in names
    assert _feature(sheet, "Göttlicher Bund: Reittier")["summary"] == (
        "effektive Druidenstufe 20, IN mind. 6, Celestische Schablone, ZR 31"
    )


def test_mercy_group_recurs_every_three_levels_with_tiers(client: TestClient, db_session: Session) -> None:
    paladin = _paladin_class(client, db_session)
    mercy = next(g for g in paladin["optionGroups"] if g["key"] == "mercy")
    bond = next(g for g in paladin["optionGroups"] if g["key"] == "divine_bond")

    assert mercy["occurrenceLevels"] == [3, 6, 9, 12, 15, 18]
    choices = {c["name"]: c for c in mercy["choices"]}
    assert len(choices) == 15
    assert choices["Kränkelnd"]["minLevel"] == 3
    assert choices["Wankend"]["minLevel"] == 6
    assert choices["Verängstigt"]["requiresChoice"] == {"groupKey": "mercy", "name": "Erschüttert"}
    assert choices["Taub"]["minLevel"] == 12
    assert bond["occurrenceLevels"] == [5]
    assert {c["name"] for c in bond["choices"]} == {"Waffe", "Reittier"}


@pytest.mark.parametrize(
    ("level", "options", "detail"),
    [
        (9, {"mercy": ["Erschüttert", "Krank", "Entkräftet"]}, "requires 'Erschöpft'"),
        (6, {"mercy": ["Erschöpft", "Entkräftet"]}, "requires Paladin level 9"),
        (4, {"divine_bond": ["Waffe"]}, "isn't available until Paladin level 5"),
    ],
)
def test_invalid_paladin_choices_are_rejected(
    client: TestClient, db_session: Session, level: int, options: dict, detail: str
) -> None:
    payload = _payload(client, db_session, [{"class_name": "Paladin", "level": level, "options": options}])

    response = client.post("/api/characters", json=payload)

    assert response.status_code == 422
    assert detail in response.json()["detail"]


def test_goettliche_wuerde_adds_charisma_to_every_save(client: TestClient, db_session: Session) -> None:
    level_1 = _create_paladin(client, db_session, 1)
    level_2 = _create_paladin(client, db_session, 2)

    # Level 2 base: Fort/Will +3, Ref +0 (vs +2/+2/+0 at level 1), plus CH +3.
    assert _save(level_2, "fort") - _save(level_1, "fort") == 1 + 3
    assert _save(level_2, "ref") - _save(level_1, "ref") == 0 + 3
    assert _save(level_2, "will") - _save(level_1, "will") == 1 + 3


def test_smite_adds_charisma_to_attack_level_to_damage_and_deflection(
    client: TestClient, db_session: Session
) -> None:
    sheet = _create_paladin(client, db_session, 1)
    character_id = sheet["id"]
    for weapon_name in ("Langschwert", "Langbogen"):
        item_id = _item_id(client, db_session, weapon_name)
        client.post(f"/api/characters/{character_id}/gear", json={"item_id": item_id, "quantity": 1})
    _equip(client, character_id, "hauptwaffe", _item_id(client, db_session, "Langschwert"))
    baseline = client.get(f"/api/characters/{character_id}").json()
    sword = _weapon_attack(baseline, "hauptwaffe")
    assert sword["attackBonus"] == "+3"  # BAB 1 + ST 2
    assert sword["damage"] == "1W8+2 H"
    assert _action(baseline, BOESES_NIEDERSTRECKEN_ABILITY_ID)["dailyLimitTotal"] == 1

    response = client.post(
        f"/api/characters/{character_id}/effects",
        json={"source_type": "class_ability", "source_id": BOESES_NIEDERSTRECKEN_ABILITY_ID},
    )
    assert response.status_code == 201, response.text

    smiting = client.get(f"/api/characters/{character_id}").json()
    sword = _weapon_attack(smiting, "hauptwaffe")
    assert sword["attackBonus"] == "+6"  # + CH 3
    assert sword["damage"] == "1W8+3 H"  # + Paladin level 1
    assert smiting["armorClass"] == baseline["armorClass"] + 3
    assert _action(smiting, BOESES_NIEDERSTRECKEN_ABILITY_ID)["dailyLimitRemaining"] == 0
    # Ranged weapons get it too ("zu allen Angriffswürfen").
    _equip(client, character_id, "hauptwaffe", _item_id(client, db_session, "Langbogen"))
    bow = _weapon_attack(client.get(f"/api/characters/{character_id}").json(), "hauptwaffe")
    assert bow["attackBonus"] == "+4"  # BAB 1 + GE 0 + CH 3
    assert bow["damage"].startswith("1W8+1")

    second = client.post(
        f"/api/characters/{character_id}/effects",
        json={"source_type": "class_ability", "source_id": BOESES_NIEDERSTRECKEN_ABILITY_ID},
    )
    assert second.status_code == 422


def test_channel_energy_spends_two_lay_on_hands_uses(client: TestClient, db_session: Session) -> None:
    sheet = _create_paladin(client, db_session, 4)
    character_id = sheet["id"]

    lay_on_hands = _action(sheet, HANDAUFLEGEN_ABILITY_ID)
    assert lay_on_hands["usesPerDay"] == 5  # 4 // 2 + CH 3
    assert _action(sheet, POSITIVE_ENERGIE_FOKUSSIEREN_ABILITY_ID)["usesPerDay"] == 2
    assert _feature(sheet, "Handauflegen")["summary"] == "5/Tag, heilt 2W6 (Untoten: 2W6 Schaden)"
    assert _feature(sheet, "Positive Energie fokussieren")["summary"] == "2W6, SG 15; kostet 2 Anwendungen Handauflegen"

    response = client.patch(f"/api/characters/{character_id}/class-abilities/{POSITIVE_ENERGIE_FOKUSSIEREN_ABILITY_ID}/use")
    assert response.status_code == 200, response.text

    sheet = client.get(f"/api/characters/{character_id}").json()
    assert _action(sheet, HANDAUFLEGEN_ABILITY_ID)["usesRemainingToday"] == 3
    assert _action(sheet, POSITIVE_ENERGIE_FOKUSSIEREN_ABILITY_ID)["usesRemainingToday"] == 1

    for _ in range(3):
        client.patch(f"/api/characters/{character_id}/class-abilities/{HANDAUFLEGEN_ABILITY_ID}/use")
    response = client.patch(f"/api/characters/{character_id}/class-abilities/{POSITIVE_ENERGIE_FOKUSSIEREN_ABILITY_ID}/use")
    assert response.status_code == 422


def test_divine_bond_weapon_enhances_the_chosen_weapon(client: TestClient, db_session: Session) -> None:
    sheet = _create_paladin(client, db_session, 8, {"divine_bond": ["Waffe"]})
    character_id = sheet["id"]
    sword_id = _item_id(client, db_session, "Langschwert")
    client.post(f"/api/characters/{character_id}/gear", json={"item_id": sword_id, "quantity": 1})
    _equip(client, character_id, "hauptwaffe", sword_id)
    baseline = _weapon_attack(client.get(f"/api/characters/{character_id}").json(), "hauptwaffe")

    response = client.post(
        f"/api/characters/{character_id}/effects",
        json={"source_type": "class_ability", "source_id": GOETTLICHER_BUND_WAFFE_ABILITY_ID, "target_item_id": sword_id},
    )
    assert response.status_code == 201, response.text

    sheet = client.get(f"/api/characters/{character_id}").json()
    weapon = _weapon_attack(sheet, "hauptwaffe")
    assert int(weapon["attackBonus"].split("/")[0]) == int(baseline["attackBonus"].split("/")[0]) + 2
    assert _feature(sheet, "Göttlicher Bund: Waffe")["summary"].startswith("1/Tag, +2 für 8 Min.")


def test_mount_bond_grants_the_call_mount_action(client: TestClient, db_session: Session) -> None:
    sheet = _create_paladin(client, db_session, 9, {"divine_bond": ["Reittier"]})

    assert _action(sheet, REITTIER_HERBEIRUFEN_ABILITY_ID)["usesPerDay"] == 2
    assert _feature(sheet, "Göttlicher Bund: Reittier") is not None
    assert _feature(sheet, "Göttlicher Bund: Waffe") is None


@pytest.mark.parametrize(("level", "expected"), [(1, 1), (3, 1), (4, 2), (7, 3), (16, 6), (19, 7), (20, 7)])
def test_smite_uses_per_day(level: int, expected: int) -> None:
    assert smite_uses_per_day(CharacterContext(level_counts_by_root_id={PALADIN_ROOT_CLASS_ID: level})) == expected


@pytest.mark.parametrize(("level", "uses", "bonus"), [(4, 0, 0), (5, 1, 1), (8, 1, 2), (9, 2, 2), (17, 4, 5), (20, 4, 6)])
def test_divine_bond_progression(level: int, uses: int, bonus: int) -> None:
    context = CharacterContext(level_counts_by_root_id={PALADIN_ROOT_CLASS_ID: level})
    assert divine_bond_uses_per_day(context) == uses
    assert divine_bond_weapon_bonus(context) == bonus


def test_lay_on_hands_never_negative() -> None:
    context = CharacterContext(ability_scores={"CH": 6}, level_counts_by_root_id={PALADIN_ROOT_CLASS_ID: 2})
    assert lay_on_hands_uses_per_day(context) == 0


# ---- alignment ----


def test_classes_expose_allowed_alignments(client: TestClient, db_session: Session) -> None:
    seed_classes(db_session)
    classes = {c["name"]: c for c in client.get("/api/classes").json()}

    assert classes["Paladin"]["allowedAlignments"] == ["LG"]
    assert set(classes["Druide"]["allowedAlignments"]) == {"NG", "LN", "N", "CN", "NE"}
    assert classes["Mönch"]["allowedAlignments"] == ["LG", "LN", "LE"]
    assert classes["Barbar"]["allowedAlignments"] == ["NG", "CG", "N", "CN", "NE", "CE"]
    assert classes["Entfesselter Barbar"]["allowedAlignments"] == ["NG", "CG", "N", "CN", "NE", "CE"]
    assert classes["Kämpfer"]["allowedAlignments"] is None


@pytest.mark.parametrize(("alignment", "detail"), [(None, "Alignment required"), ("NG", "isn't allowed for Paladin")])
def test_paladin_creation_requires_lawful_good(
    client: TestClient, db_session: Session, alignment: str | None, detail: str
) -> None:
    payload = _payload(client, db_session, [{"class_name": "Paladin", "level": 1}], alignment=alignment)

    response = client.post("/api/characters", json=payload)

    assert response.status_code == 422
    assert detail in response.json()["detail"]


def test_unknown_alignment_code_is_rejected(client: TestClient, db_session: Session) -> None:
    payload = _payload(client, db_session, [{"class_name": "Kämpfer", "level": 1}], alignment="XX")
    assert client.post("/api/characters", json=payload).status_code == 422


def test_alignment_is_stored_and_changeable_within_the_class_rules(client: TestClient, db_session: Session) -> None:
    payload = _payload(client, db_session, [{"class_name": "Kämpfer", "level": 1}], alignment=None)
    created = client.post("/api/characters", json=payload)
    assert created.status_code == 201, created.text
    character_id = created.json()["id"]
    assert created.json()["alignment"] is None

    response = client.patch(f"/api/characters/{character_id}/alignment", json={"alignment": "CN"})
    assert response.status_code == 200
    assert client.get(f"/api/characters/{character_id}").json()["alignment"] == "CN"

    paladin = _create_paladin(client, db_session, 1)
    response = client.patch(f"/api/characters/{paladin['id']}/alignment", json={"alignment": "N"})
    assert response.status_code == 422
    response = client.patch(f"/api/characters/{paladin['id']}/alignment", json={"alignment": None})
    assert response.status_code == 422


def test_multiclassing_into_paladin_checks_the_alignment(client: TestClient, db_session: Session) -> None:
    def multiclass(alignment: str | None) -> int:
        payload = _payload(client, db_session, [{"class_name": "Kämpfer", "level": 1}], alignment=alignment)
        character_id = client.post("/api/characters", json=payload).json()["id"]
        response = client.post(
            f"/api/characters/{character_id}/level-up",
            json={"target": {"mode": "new", "class_name": "Paladin"}, "hit_points": 5},
        )
        return response.status_code

    assert multiclass("CG") == 422
    assert multiclass("LG") == 201
    # A character without any alignment (everyone created before it existed)
    # can still level up.
    assert multiclass(None) == 201
