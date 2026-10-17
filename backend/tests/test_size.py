"""Creature size — roadmap slice 10, step 2a (`rules/size.py`): size
modifiers through the normal stacking, damage dice by size, size-changing
effects, natural attacks (primary/secondary, size-scaled)."""

from collections import Counter
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.rules.context import CharacterContext
from app.rules.modifiers import NaturalAttack
from app.rules.size import (
    PERSON_VERGROESSERN_SPELL_ID,
    PERSON_VERKLEINERN_SPELL_ID,
    resolve_size,
    step_damage,
    weapon_damage,
)
import app.sheet as sheet_module

from test_characters import _character_payload, _create_user, _human_race_id, _item_id, _race_id
from test_weapon_slots import _equip, _weapon_attack

@pytest.mark.parametrize(
    ("dice", "steps", "expected"),
    [
        ("1W8", 1, "2W6"),
        ("1W8", -1, "1W6"),
        ("1W6", -1, "1W4"),
        ("1W4", -2, "1W2"),
        ("2W6", -1, "1W8"),
        ("1W10", -1, "1W8"),
        ("1W10", 1, "2W8"),
        ("2W8", -1, "1W10"),
        ("1W12", 1, "3W6"),
        ("2W4", 1, "2W6"),
        ("1W6/1W6", 1, "1W8/1W8"),
        ("1W20", 1, "1W20"),
        ("1W6", 0, "1W6"),
    ],
)
def test_step_damage(dice: str, steps: int, expected: str) -> None:
    assert step_damage(dice, steps) == expected


def test_weapon_damage_by_wielder_size() -> None:
    assert weapon_damage("1W8", "1W6", "Klein") == "1W6"
    assert weapon_damage("1W8", None, "Klein") == "1W6"
    assert weapon_damage("1W8", "1W6", "Mittelgroß") == "1W8"
    assert weapon_damage("1W8", "1W6", "Groß") == "2W6"
    assert weapon_damage(None, None, "Groß") is None


def _effect(source_id) -> SimpleNamespace:
    return SimpleNamespace(source_id=source_id)


def test_size_effects_shift_and_clamp() -> None:
    enlarged = CharacterContext(active_effects=[_effect(PERSON_VERGROESSERN_SPELL_ID)])
    reduced = CharacterContext(active_effects=[_effect(PERSON_VERKLEINERN_SPELL_ID)])
    both = CharacterContext(active_effects=[_effect(PERSON_VERGROESSERN_SPELL_ID), _effect(PERSON_VERKLEINERN_SPELL_ID)])

    assert resolve_size("Mittelgroß", enlarged) == "Groß"
    assert resolve_size("Klein", reduced) == "Sehr klein"
    assert resolve_size("Mittelgroß", both) == "Mittelgroß"
    assert resolve_size("Mini", reduced) == "Mini"
    assert resolve_size("Kolossal", enlarged) == "Kolossal"


def _combat(sheet: dict, key: str) -> str:
    return next(c for c in sheet["combat"] if c["key"] == key)["value"]


def _skill_total(sheet: dict, name: str) -> int:
    return int(next(s for s in sheet["skills"] if s["label"] == name)["value"])


def _create(client: TestClient, db_session: Session, race_id: str, **overrides) -> dict:
    payload = _character_payload(_create_user(client), race_id, db_session, classes=[{"class_name": "Kämpfer", "level": 1}])
    payload.update(overrides)
    response = client.post("/api/characters", json=payload)
    assert response.status_code == 201, response.text
    return client.get(f"/api/characters/{response.json()['id']}").json()


def test_small_race_gets_its_size_modifiers(client: TestClient, db_session: Session) -> None:
    human = _create(client, db_session, _human_race_id(client, db_session), flex_ability="CH")
    halfling = _create(client, db_session, _race_id(client, db_session, "Halbling"))

    assert _combat(halfling, "size") == "Klein (1,5 m / 1,5 m)"
    assert _combat(human, "size") == "Mittelgroß (1,5 m / 1,5 m)"
    assert any(e["label"] == "Größe (Klein)" and e["value"] == 1 for e in halfling["armorClassBreakdown"])
    # CMB/CMD carry the inverse (−1); compared to the same character's BAB/ST/GE parts.
    bab = int(_combat(halfling, "bab"))
    st = next(a for a in halfling["abilities"] if a["key"] == "ST")
    ge = next(a for a in halfling["abilities"] if a["key"] == "GE")
    assert int(_combat(halfling, "cmb")) == bab + int(st["mod"]) - 1
    assert int(_combat(halfling, "cmd")) == 10 + bab + int(st["mod"]) + int(ge["mod"]) - 1
    heimlichkeit = next(s for s in halfling["skills"] if s["label"] == "Heimlichkeit")
    assert any(b["label"] == "Größe (Klein)" and b["value"] == 4 for b in heimlichkeit["breakdown"])
    size_trait = next(r for r in halfling["raceAbilities"] if r["name"] == "Klein")
    assert size_trait["hasHandler"] is True


def test_small_wielder_uses_small_weapon_damage_and_gets_plus_one_to_hit(
    client: TestClient, db_session: Session
) -> None:
    halfling = _create(client, db_session, _race_id(client, db_session, "Halbling"))
    human = _create(client, db_session, _human_race_id(client, db_session), flex_ability="CH")
    sword_id = _item_id(client, db_session, "Langschwert")
    attacks = {}
    for name, sheet in (("halfling", halfling), ("human", human)):
        client.post(f"/api/characters/{sheet['id']}/gear", json={"item_id": sword_id, "quantity": 1})
        _equip(client, sheet["id"], "hauptwaffe", sword_id)
        attacks[name] = _weapon_attack(client.get(f"/api/characters/{sheet['id']}").json(), "hauptwaffe")

    assert attacks["halfling"]["damage"].startswith("1W6")
    assert attacks["human"]["damage"].startswith("1W8")
    halfling_st = int(next(a for a in halfling["abilities"] if a["key"] == "ST")["mod"])
    human_st = int(next(a for a in human["abilities"] if a["key"] == "ST")["mod"])
    assert int(attacks["halfling"]["attackBonus"]) - halfling_st == int(attacks["human"]["attackBonus"]) - human_st + 1


def test_person_vergroessern_makes_a_medium_character_large(client: TestClient, db_session: Session) -> None:
    sheet = _create(client, db_session, _human_race_id(client, db_session), flex_ability="CH")
    character_id = sheet["id"]
    sword_id = _item_id(client, db_session, "Langschwert")
    client.post(f"/api/characters/{character_id}/gear", json={"item_id": sword_id, "quantity": 1})
    _equip(client, character_id, "hauptwaffe", sword_id)
    before = client.get(f"/api/characters/{character_id}").json()

    response = client.post(
        f"/api/characters/{character_id}/effects",
        json={"source_type": "spell", "source_id": str(PERSON_VERGROESSERN_SPELL_ID), "duration_remaining": 10},
    )
    assert response.status_code == 201, response.text
    after = client.get(f"/api/characters/{character_id}").json()

    def score(sheet: dict, key: str) -> int:
        return next(a for a in sheet["abilities"] if a["key"] == key)["score"]

    assert _combat(after, "size") == "Groß (3 m / 3 m)"
    assert score(after, "ST") == score(before, "ST") + 2
    assert score(after, "GE") == score(before, "GE") - 2
    assert _weapon_attack(after, "hauptwaffe")["damage"].startswith("2W6")
    # −1 size on AC on top of the −1 Dex modifier change.
    assert after["armorClass"] == before["armorClass"] - 1 - 1
    assert _skill_total(after, "Heimlichkeit") == _skill_total(before, "Heimlichkeit") - 4 - 1


def _natural(
    monkeypatch: pytest.MonkeyPatch,
    attacks: list[NaturalAttack],
    *,
    size: str = "Mittelgroß",
    wields: bool = False,
) -> list[dict]:
    """`_build_natural_attacks` for BAB +5, ST +4 and these attacks as the
    only natural-attack handlers."""
    handlers = {uuid4(): attack for attack in attacks}
    monkeypatch.setattr(
        sheet_module, "NATURAL_ATTACK_HANDLERS", {key: (lambda ctx, a=a: a) for key, a in handlers.items()}
    )
    return sheet_module._build_natural_attacks(
        {"sword": SimpleNamespace(category="weapon")},
        {"hauptwaffe": SimpleNamespace(item_id="sword")} if wields else {},
        set(handlers),
        Counter(),
        CharacterContext(),
        5,
        4,
        0,
        0,
        0,
        size=size,
    )


def test_sole_primary_natural_attack_adds_one_and_a_half_strength(monkeypatch: pytest.MonkeyPatch) -> None:
    [bite] = _natural(monkeypatch, [NaturalAttack(name="Biss", count=1, damage_dice="1W6", damage_type="S")])

    assert bite["attackBonus"] == "+9"
    assert bite["damage"] == "1W6+6 S"


def test_secondary_natural_attack_is_minus_five_and_half_strength(monkeypatch: pytest.MonkeyPatch) -> None:
    results = _natural(
        monkeypatch,
        [
            NaturalAttack(name="Biss", count=1, damage_dice="1W6", damage_type="S"),
            NaturalAttack(name="Schwanzschlag", count=1, damage_dice="1W4", damage_type="W", is_secondary=True),
        ]
    )
    by_name = {r["name"]: r for r in results}

    assert by_name["Biss"]["damage"] == "1W6+4 S"  # two attacks: no 1½
    assert by_name["Schwanzschlag"]["attackBonus"] == "+4"
    assert by_name["Schwanzschlag"]["damage"] == "1W4+2 W"
    assert by_name["Schwanzschlag"]["hand"] == "Naturangriff (sekundär)"


def test_wielding_a_weapon_makes_natural_attacks_secondary(monkeypatch: pytest.MonkeyPatch) -> None:
    [bite] = _natural(monkeypatch, [NaturalAttack(name="Biss", count=1, damage_dice="1W6", damage_type="S")], wields=True)

    assert bite["attackBonus"] == "+4"
    assert bite["damage"] == "1W6+2 S"


def test_natural_attack_dice_scale_with_size(monkeypatch: pytest.MonkeyPatch) -> None:
    claws = NaturalAttack(name="Klauen", count=2, damage_dice="1W4", damage_type="H")

    assert _natural(monkeypatch, [claws], size="Klein")[0]["damage"].startswith("1W3")
    assert _natural(monkeypatch, [claws], size="Groß")[0]["damage"].startswith("1W6")
    small_based = NaturalAttack(name="Biss", count=2, damage_dice="1W4", damage_type="S", base_size="Klein")
    assert _natural(monkeypatch, [small_based], size="Klein")[0]["damage"].startswith("1W4")
