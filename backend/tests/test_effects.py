from uuid import UUID

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    BaseClassAbility,
    BaseClassAbilityGrant,
    BaseCondition,
    BaseItem,
    BaseSpell,
    Character,
    CharacterEffect,
    CharacterSpell,
)

from test_characters import _item_id, _spells_by_class
from test_items import _create_character


def _make_condition(db_session: Session, name: str = "Gift: Riesenspinnengift", type_: str = "condition") -> str:
    condition = BaseCondition(
        name=name, description="1W2 STÄ-Schaden, Häufigkeit 1/Runde für 4 Runden.", type=type_
    )
    db_session.add(condition)
    db_session.commit()
    return str(condition.id)


def _persistent_spell_id(client: TestClient, db_session: Session) -> str:
    _, spells_by_name = _spells_by_class(client, db_session, "Magier")
    spell_id = next(iter(spells_by_name.values()))
    spell = db_session.get(BaseSpell, spell_id)
    spell.is_persistent_effect = True
    db_session.commit()
    return spell_id


def _persistent_class_ability_id(character_id: str, db_session: Session) -> str:
    ability = db_session.scalars(select(BaseClassAbility)).first()
    ability.is_persistent_effect = True
    db_session.commit()
    return str(ability.id)


def test_activate_condition_effect_creates_row(client: TestClient, db_session: Session) -> None:
    character_id = _create_character(client, db_session)
    condition_id = _make_condition(db_session)

    response = client.post(
        f"/api/characters/{character_id}/effects",
        json={"source_type": "condition", "source_id": condition_id, "level": 3, "duration_remaining": 10},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["source_type"] == "condition"
    assert body["level"] == 3
    assert body["duration_remaining"] == 10


def test_activate_unknown_condition_is_rejected(client: TestClient, db_session: Session) -> None:
    character_id = _create_character(client, db_session)
    response = client.post(
        f"/api/characters/{character_id}/effects",
        json={"source_type": "condition", "source_id": "00000000-0000-0000-0000-000000000000"},
    )
    assert response.status_code == 422


def test_activate_non_persistent_spell_is_rejected(client: TestClient, db_session: Session) -> None:
    character_id = _create_character(client, db_session)
    _, spells_by_name = _spells_by_class(client, db_session, "Magier")
    spell_id = next(iter(spells_by_name.values()))

    response = client.post(
        f"/api/characters/{character_id}/effects",
        json={"source_type": "spell", "source_id": spell_id},
    )
    assert response.status_code == 422


def test_activate_persistent_spell_is_accepted(client: TestClient, db_session: Session) -> None:
    character_id = _create_character(client, db_session)
    spell_id = _persistent_spell_id(client, db_session)

    response = client.post(
        f"/api/characters/{character_id}/effects",
        json={"source_type": "spell", "source_id": spell_id, "level": 5, "duration_remaining": 5},
    )
    assert response.status_code == 201


def test_activate_persistent_class_ability_is_accepted(client: TestClient, db_session: Session) -> None:
    character_id = _create_character(client, db_session)
    ability_id = _persistent_class_ability_id(character_id, db_session)

    response = client.post(
        f"/api/characters/{character_id}/effects",
        json={"source_type": "class_ability", "source_id": ability_id},
    )
    assert response.status_code == 201


def test_same_effect_can_be_active_twice_from_independent_instances(client: TestClient, db_session: Session) -> None:
    character_id = _create_character(client, db_session)
    condition_id = _make_condition(db_session)

    first = client.post(
        f"/api/characters/{character_id}/effects",
        json={"source_type": "condition", "source_id": condition_id, "duration_remaining": 3},
    )
    second = client.post(
        f"/api/characters/{character_id}/effects",
        json={"source_type": "condition", "source_id": condition_id, "duration_remaining": 8},
    )
    assert first.status_code == 201
    assert second.status_code == 201
    assert first.json()["id"] != second.json()["id"]

    rows = db_session.scalars(select(CharacterEffect)).all()
    assert len(rows) == 2


def test_remove_effect_deletes_it(client: TestClient, db_session: Session) -> None:
    character_id = _create_character(client, db_session)
    condition_id = _make_condition(db_session)
    effect_id = client.post(
        f"/api/characters/{character_id}/effects",
        json={"source_type": "condition", "source_id": condition_id, "duration_remaining": 3},
    ).json()["id"]

    response = client.delete(f"/api/characters/{character_id}/effects/{effect_id}")
    assert response.status_code == 204
    assert db_session.get(CharacterEffect, effect_id) is None


def test_advance_time_round_decrements_duration_and_expires_at_zero(client: TestClient, db_session: Session) -> None:
    character_id = _create_character(client, db_session)
    condition_id = _make_condition(db_session, "Verängstigt")
    effect_id = client.post(
        f"/api/characters/{character_id}/effects",
        json={"source_type": "condition", "source_id": condition_id, "duration_remaining": 2},
    ).json()["id"]

    response = client.post(f"/api/characters/{character_id}/advance-time", json={"unit": "round"})
    assert response.status_code == 200
    remaining = response.json()
    assert len(remaining) == 1
    assert remaining[0]["id"] == effect_id
    assert remaining[0]["duration_remaining"] == 1

    response = client.post(f"/api/characters/{character_id}/advance-time", json={"unit": "round"})
    assert response.json() == []
    assert db_session.get(CharacterEffect, effect_id) is None


def test_advance_time_day_clears_plain_effect_but_not_frequency_tracked_one(
    client: TestClient, db_session: Session
) -> None:
    character_id = _create_character(client, db_session)
    buff_id = _make_condition(db_session, "Gesegnet")
    poison_id = _make_condition(db_session, "Gift", type_="poison")

    buff_effect_id = client.post(
        f"/api/characters/{character_id}/effects",
        json={"source_type": "condition", "source_id": buff_id, "duration_remaining": 50},
    ).json()["id"]
    poison_effect_id = client.post(
        f"/api/characters/{character_id}/effects",
        json={
            "source_type": "condition",
            "source_id": poison_id,
            "incubation_remaining": 10,
            "frequency_rounds": 1,
            "successes_required": 2,
        },
    ).json()["id"]

    response = client.post(f"/api/characters/{character_id}/advance-time", json={"unit": "day"})
    assert response.status_code == 200
    remaining_ids = {row["id"] for row in response.json()}
    assert remaining_ids == {poison_effect_id}
    assert db_session.get(CharacterEffect, buff_effect_id) is None
    assert db_session.get(CharacterEffect, poison_effect_id) is not None


def test_save_result_success_increments_and_cures_at_threshold(client: TestClient, db_session: Session) -> None:
    character_id = _create_character(client, db_session)
    poison_id = _make_condition(db_session, "Gift", type_="poison")
    effect_id = client.post(
        f"/api/characters/{character_id}/effects",
        json={
            "source_type": "condition",
            "source_id": poison_id,
            "level": 4,
            "frequency_rounds": 1,
            "successes_required": 2,
        },
    ).json()["id"]

    first = client.post(f"/api/characters/{character_id}/effects/{effect_id}/save-result", json={"success": True})
    assert first.status_code == 200
    body = first.json()
    assert body["successes_current"] == 1
    assert db_session.get(CharacterEffect, effect_id) is not None

    second = client.post(f"/api/characters/{character_id}/effects/{effect_id}/save-result", json={"success": True})
    assert second.status_code == 200
    assert db_session.get(CharacterEffect, effect_id) is None


def test_save_result_failure_resets_successes_without_changing_level(client: TestClient, db_session: Session) -> None:
    character_id = _create_character(client, db_session)
    poison_id = _make_condition(db_session, "Gift", type_="poison")
    effect_id = client.post(
        f"/api/characters/{character_id}/effects",
        json={
            "source_type": "condition",
            "source_id": poison_id,
            "level": 4,
            "frequency_rounds": 1,
            "successes_required": 2,
        },
    ).json()["id"]
    client.post(f"/api/characters/{character_id}/effects/{effect_id}/save-result", json={"success": True})

    response = client.post(f"/api/characters/{character_id}/effects/{effect_id}/save-result", json={"success": False})
    assert response.status_code == 200
    body = response.json()
    assert body["successes_current"] == 0
    assert body["level"] == 4


def test_save_result_rejected_for_effect_without_frequency(client: TestClient, db_session: Session) -> None:
    character_id = _create_character(client, db_session)
    condition_id = _make_condition(db_session, "Gesegnet")
    effect_id = client.post(
        f"/api/characters/{character_id}/effects",
        json={"source_type": "condition", "source_id": condition_id, "duration_remaining": 5},
    ).json()["id"]

    response = client.post(f"/api/characters/{character_id}/effects/{effect_id}/save-result", json={"success": True})
    assert response.status_code == 422


def test_sheet_lists_active_effects_and_activatable_sources(client: TestClient, db_session: Session) -> None:
    character_id = _create_character(client, db_session)
    condition_id = _make_condition(db_session, "Verängstigt")
    client.post(
        f"/api/characters/{character_id}/effects",
        json={"source_type": "condition", "source_id": condition_id, "level": 2, "duration_remaining": 4},
    )

    # A spell only counts as "activatable" once it's both flagged
    # is_persistent_effect *and* actually known by this character - inserted
    # directly (like a level-up spell pick) rather than via the creation
    # wizard's budget validation, which isn't what this test is about.
    character = db_session.get(Character, UUID(character_id))
    level = character.levels[0]
    _, spells_by_name = _spells_by_class(client, db_session, "Magier")
    spell_id = next(iter(spells_by_name.values()))
    spell = db_session.get(BaseSpell, spell_id)
    spell.is_persistent_effect = True
    db_session.add(CharacterSpell(level_id=level.id, base_class_id=level.base_class_id, spell_id=UUID(spell_id)))
    db_session.commit()

    grant = db_session.scalar(
        select(BaseClassAbilityGrant).where(
            BaseClassAbilityGrant.base_class_id == level.base_class_id, BaseClassAbilityGrant.level <= 1
        )
    )
    ability = db_session.get(BaseClassAbility, grant.ability_id)
    ability.is_persistent_effect = True
    ability.activation_scope = "self"
    db_session.commit()

    sheet = client.get(f"/api/characters/{character_id}").json()

    assert len(sheet["activeEffects"]) == 1
    active = sheet["activeEffects"][0]
    assert active["sourceType"] == "condition"
    assert active["conditionType"] == "condition"
    assert active["name"] == "Verängstigt"
    assert active["level"] == 2
    assert active["durationRemaining"] == 4
    assert active["successesCurrent"] == 0

    assert any(s["key"] == spell_id for s in sheet["activatableSpells"])
    assert any(a["key"] == str(ability.id) for a in sheet["activatableClassAbilities"])


def test_sheet_lists_actions_from_activatable_sources(client: TestClient, db_session: Session) -> None:
    """Aktionen panel (roadmap slice 6, thin cut) — `sheet.py`'s `_build_actions`
    reuses the same "activatable" data already computed for the Effects
    panel (persistent-effect spells known, persistent-effect class abilities
    granted, activatable gear) rather than a new data source. No action-cost
    field exists anywhere in the schema, so every entry's `tag` stays `None`
    (`Berührung des Schicksals` and its worked-example siblings above are
    exactly this shape: real duration, no real action-cost data)."""
    character_id = _create_character(client, db_session)
    character = db_session.get(Character, UUID(character_id))
    level = character.levels[0]

    _, spells_by_name = _spells_by_class(client, db_session, "Magier")
    spell_id = next(iter(spells_by_name.values()))
    spell = db_session.get(BaseSpell, spell_id)
    spell.is_persistent_effect = True
    db_session.add(CharacterSpell(level_id=level.id, base_class_id=level.base_class_id, spell_id=UUID(spell_id)))
    db_session.commit()

    grant = db_session.scalar(
        select(BaseClassAbilityGrant).where(
            BaseClassAbilityGrant.base_class_id == level.base_class_id, BaseClassAbilityGrant.level <= 1
        )
    )
    ability = db_session.get(BaseClassAbility, grant.ability_id)
    ability.is_persistent_effect = True
    ability.activation_scope = "self"
    db_session.commit()

    ring_id = _item_id(client, db_session, "Chamäleonring")
    item = db_session.get(BaseItem, ring_id)
    item.activation = "activatable"
    item.uses_per_day = 2
    db_session.commit()
    client.post(f"/api/characters/{character_id}/gear", json={"item_id": ring_id, "quantity": 1})

    toggle_ring_id = _item_id(client, db_session, "Energieschildring")
    toggle_item = db_session.get(BaseItem, toggle_ring_id)
    toggle_item.activation = "activatable"
    db_session.commit()
    client.post(f"/api/characters/{character_id}/gear", json={"item_id": toggle_ring_id, "quantity": 1})

    dolch_id = _item_id(client, db_session, "Dolch")
    client.post(f"/api/characters/{character_id}/gear", json={"item_id": dolch_id, "quantity": 1})

    sheet = client.get(f"/api/characters/{character_id}").json()
    actions_by_id = {a["id"]: a for a in sheet["actions"]}

    spell_action = actions_by_id[f"spell-{spell_id}"]
    assert spell_action["tag"] is None
    assert spell_action["description"] == spell.description
    assert spell_action["sourceType"] == "spell"
    assert spell_action["sourceId"] == spell_id

    ability_action = actions_by_id[f"ability-{ability.id}"]
    assert ability_action["tag"] is None
    assert ability_action["sourceType"] == "class_ability"
    assert ability_action["sourceId"] == str(ability.id)

    gear_action = actions_by_id[f"gear-{ring_id}"]
    assert gear_action["tag"] is None
    assert "2/2 Anwendungen heute übrig" in gear_action["description"]
    assert gear_action["sourceType"] == "gear"
    assert gear_action["sourceId"] == ring_id
    assert gear_action["gearActionKind"] == "use"

    toggle_action = actions_by_id[f"gear-{toggle_ring_id}"]
    assert toggle_action["gearActionKind"] == "toggle"

    assert f"gear-{dolch_id}" not in actions_by_id


def test_sheet_class_ability_activation_scope_filtering(client: TestClient, db_session: Session) -> None:
    """`activation_scope` (roadmap slice 5, Barbar/Barde classification pass)
    splits persistent-effect class abilities into the character's own
    activation list (`self`/`both`, gated by ownership) and a catalog-wide
    list anyone can pick from (`external`/`both`, e.g. a Barde's Lied des
    Erfolgs on an ally who never learned Bardenauftritt)."""
    character_id = _create_character(client, db_session)
    character = db_session.get(Character, UUID(character_id))
    level = character.levels[0]

    grant = db_session.scalar(
        select(BaseClassAbilityGrant).where(
            BaseClassAbilityGrant.base_class_id == level.base_class_id, BaseClassAbilityGrant.level <= 1
        )
    )
    granted_self_only = db_session.get(BaseClassAbility, grant.ability_id)
    granted_self_only.is_persistent_effect = True
    granted_self_only.activation_scope = "self"

    external_only = BaseClassAbility(
        name="Lied des Erfolgs (Test)", description="Kann nicht auf sich selbst gewirkt werden.",
        is_persistent_effect=True, activation_scope="external",
    )
    db_session.add(external_only)
    db_session.commit()

    sheet = client.get(f"/api/characters/{character_id}").json()

    # Granted + self-scoped: shows up in the character's own list, not the external one.
    assert any(a["key"] == str(granted_self_only.id) for a in sheet["activatableClassAbilities"])
    assert not any(a["key"] == str(granted_self_only.id) for a in sheet["externalClassAbilities"])

    # External-scoped, never granted to this character: only in the external list.
    assert not any(a["key"] == str(external_only.id) for a in sheet["activatableClassAbilities"])


def test_entfesselter_barbar_kampfrausch_applies_ac_penalty_and_will_bonus(
    client: TestClient, db_session: Session
) -> None:
    """First `EFFECT_HANDLERS` content (roadmap.md, `rules/effects.py`) —
    activating it should move the sheet's `armorClass`/Will save, not just
    create a countdown row (see `test_activate_persistent_class_ability_is_accepted`
    for the pre-handler behavior this builds on). Entfesselter Barbar's
    Kampfrausch (this id) is real seeded content
    (`base_class_abilities.json`), already `is_persistent_effect`/
    `activation_scope="self"` — no need to insert a stand-in row."""
    character_id = _create_character(client, db_session)
    ability_id = "ad985f6f-3b03-5861-bccf-a016ebaba4ec"

    baseline = client.get(f"/api/characters/{character_id}").json()
    baseline_ac = baseline["armorClass"]
    baseline_will = int(next(s["value"] for s in baseline["saves"] if s["key"] == "will"))

    response = client.post(
        f"/api/characters/{character_id}/effects",
        json={"source_type": "class_ability", "source_id": ability_id},
    )
    assert response.status_code == 201

    raging = client.get(f"/api/characters/{character_id}").json()
    assert raging["armorClass"] == baseline_ac - 2
    assert int(next(s["value"] for s in raging["saves"] if s["key"] == "will")) == baseline_will + 2
    # Unaffected: no attack/damage-roll endpoint, no temp-HP pool (see the
    # handler's own docstring for why those stay unmodeled).
    assert raging["hp"] == baseline["hp"]
