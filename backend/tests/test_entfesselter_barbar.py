"""Entfesselter Barbar (Unchained Barbarian) import -
http://prd.5footstep.de/Alternativregeln/Klassen/Barbar, see
scripts/import_entfesselter_barbar.py and todos.md for the full writeup.
Modeled as a second, standalone root `BaseClass` (own id, `arch_class_of=
None`) rather than a Barbar archetype - the page frames it as a full
"Alternativklasse" a character can't mix levels with, same relationship
Mystiker has to Kleriker."""

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import BaseClass, BaseClassAbility, BaseClassAbilityGrant, BaseClassOptionChoice, BaseClassOptionGroup
from app.seed.class_ability_seed import seed_class_abilities
from app.seed.class_option_seed import seed_class_options
from app.seed.class_seed import seed_classes
from app.seed.skill_seed import seed_skills

from test_characters import _character_payload, _create_user, _elf_race_id


def _entfesselter_barbar(db_session: Session) -> BaseClass:
    return db_session.query(BaseClass).filter_by(name="Entfesselter Barbar").one()


def _kampfrauschkraft_group(db_session: Session, entfesselter_barbar: BaseClass) -> BaseClassOptionGroup:
    return (
        db_session.query(BaseClassOptionGroup)
        .filter_by(base_class_id=entfesselter_barbar.id, key="kampfrauschkraft")
        .one()
    )


def test_entfesselter_barbar_base_class_fields_match_the_page(client: TestClient, db_session: Session) -> None:
    seed_classes(db_session)

    response = client.get("/api/classes")
    barbar = next(c for c in response.json() if c["name"] == "Entfesselter Barbar")

    barbar_row = _entfesselter_barbar(db_session)
    assert barbar_row.hit_dice == 12
    assert barbar_row.arch_class_of is None
    assert barbar["castingAbility"] is None
    assert barbar["babProgression"] == 1.0
    assert barbar["fortSave"] is True
    assert barbar["refSave"] is False
    assert barbar["willSave"] is False
    assert barbar["skillPointsBase"] == 4


def test_entfesselter_barbar_class_skills_are_the_full_10(client: TestClient, db_session: Session) -> None:
    seed_classes(db_session)
    seed_class_options(db_session)
    seed_skills(db_session)

    response = client.get("/api/classes")
    barbar = next(c for c in response.json() if c["name"] == "Entfesselter Barbar")
    skills = {s["id"]: s["name"] for s in client.get("/api/skills").json()}
    names = {skills[sid] for sid in barbar["classSkills"]}

    assert names == {
        "Akrobatik",
        "Einschüchtern",
        "Handwerk",
        "Klettern",
        "Mit Tieren umgehen",
        "Reiten",
        "Schwimmen",
        "Überlebenskunst",
        "Wahrnehmung",
        "Wissen (Natur)",
    }


def test_entfesselter_barbar_kampfrauschkraft_group_has_54_rage_powers(
    client: TestClient, db_session: Session
) -> None:
    seed_classes(db_session)
    seed_class_options(db_session)

    barbar = _entfesselter_barbar(db_session)
    group = _kampfrauschkraft_group(db_session, barbar)
    assert group.max_choices == 10

    names = {c.name for c in db_session.query(BaseClassOptionChoice).filter_by(group_id=group.id)}
    assert len(names) == 54
    assert {"Aberglaube", "Zielsichere Kampfhaltung", "Machtvolle Kampfhaltung"} <= names


def test_entfesselter_barbar_kampfrauschkraft_slot_grants_every_even_level_through_20(
    client: TestClient, db_session: Session
) -> None:
    seed_classes(db_session)
    seed_class_options(db_session)
    seed_class_abilities(db_session)

    barbar = _entfesselter_barbar(db_session)
    ability = db_session.query(BaseClassAbility).filter_by(name="Kampfrauschkraft").one()
    levels = sorted(
        g.level
        for g in db_session.query(BaseClassAbilityGrant).filter_by(
            base_class_id=barbar.id, ability_id=ability.id, option_choice_id=None
        )
    )
    assert levels == [2, 4, 6, 8, 10, 12, 14, 16, 18, 20]


def test_entfesselter_barbar_rage_power_prerequisite_is_choice_gated(
    client: TestClient, db_session: Session
) -> None:
    """Bodenbrecher, Mächtiger requires the Bodenbrecher rage power and 8th
    level - both expressible with the existing schema
    (`requires_choice_id` + `min_level`), unlike Nachtsicht's racial-trait-
    or-rage-power OR (see todos.md)."""
    seed_classes(db_session)
    seed_class_options(db_session)

    barbar = _entfesselter_barbar(db_session)
    group = _kampfrauschkraft_group(db_session, barbar)
    bodenbrecher = db_session.query(BaseClassOptionChoice).filter_by(group_id=group.id, name="Bodenbrecher").one()
    maechtiger = (
        db_session.query(BaseClassOptionChoice).filter_by(group_id=group.id, name="Bodenbrecher, Mächtiger").one()
    )

    assert maechtiger.min_level == 8
    assert maechtiger.requires_choice_id == bodenbrecher.id

    nachtsicht = db_session.query(BaseClassOptionChoice).filter_by(group_id=group.id, name="Nachtsicht").one()
    assert nachtsicht.requires_choice_id is None


def test_entfesselter_barbar_rage_power_choice_surfaces_matching_ability_in_character_sheet(
    client: TestClient, db_session: Session
) -> None:
    """Same bet already proven for Kleriker's Domäne/Schurke's Trick: a
    picked rage power is just a `CharacterClassOption` plus `option_choice_id`
    -gated grant, no sheet.py change needed for it to show up correctly."""
    user_id = _create_user(client)
    race_id = _elf_race_id(client, db_session)

    response = client.post(
        "/api/characters",
        json=_character_payload(
            user_id,
            race_id,
            db_session,
            classes=[
                {
                    "class_name": "Entfesselter Barbar",
                    "level": 2,
                    "options": {"kampfrauschkraft": ["Aberglaube"]},
                }
            ],
        ),
    )
    assert response.status_code == 201
    character_id = response.json()["id"]

    body = client.get(f"/api/characters/{character_id}").json()
    feature_names = {f["name"] for f in body["classFeatures"]}

    assert {"Aberglaube", "Kampfrausch", "Schnelle Bewegung", "Reflexbewegung"} <= feature_names
    # A rage power that wasn't picked shouldn't leak in.
    assert "Animalische Wut" not in feature_names
