"""Kleriker (Cleric) import - http://prd.5footstep.de/Grundregelwerk/Klassen/
Kleriker, see scripts/import_kleriker.py and todos.md's Kleriker Nachtrag
for the full story. Unlike Mystiker, Kleriker's `base_classes` row and 9 of
13 class skills were already correct - this import replaced 8 LLM-guessed
domain names (only 8 of the real 33 domains, e.g. "Kriegsdomäne"/"Leben")
with the full real domain list and added every class ability/grant (there
were none at all before this: no Energie fokussieren, no domain powers)."""

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import BaseClass, BaseClassAbility, BaseClassAbilityGrant, BaseClassOptionChoice, BaseClassOptionGroup
from app.seed.class_ability_seed import seed_class_abilities
from app.seed.class_option_seed import seed_class_options
from app.seed.class_seed import seed_classes
from app.seed.skill_seed import seed_skills

from test_characters import _character_payload, _create_user, _elf_race_id


def _kleriker(db_session: Session) -> BaseClass:
    return db_session.query(BaseClass).filter_by(name="Kleriker").one()


def _domain_group(db_session: Session, kleriker: BaseClass) -> BaseClassOptionGroup:
    return db_session.query(BaseClassOptionGroup).filter_by(base_class_id=kleriker.id, key="domain").one()


def test_kleriker_base_class_fields_match_the_page(client: TestClient, db_session: Session) -> None:
    seed_classes(db_session)

    response = client.get("/api/classes")
    kleriker = next(c for c in response.json() if c["name"] == "Kleriker")

    kleriker_row = _kleriker(db_session)
    assert kleriker_row.hit_dice == 8
    assert kleriker["castingAbility"] == "WE"
    assert kleriker["spellTradition"] == "divine"
    assert kleriker["babProgression"] == 0.75
    assert kleriker["fortSave"] is True
    assert kleriker["refSave"] is False
    assert kleriker["willSave"] is True
    assert kleriker["skillPointsBase"] == 2


def test_kleriker_class_skills_are_the_full_13(client: TestClient, db_session: Session) -> None:
    seed_classes(db_session)
    seed_class_options(db_session)
    seed_skills(db_session)

    response = client.get("/api/classes")
    kleriker = next(c for c in response.json() if c["name"] == "Kleriker")
    skills = {s["id"]: s["name"] for s in client.get("/api/skills").json()}
    names = {skills[sid] for sid in kleriker["classSkills"]}

    assert names == {
        "Beruf",
        "Diplomatie",
        "Handwerk",
        "Heilkunde",
        "Motiv erkennen",
        "Schätzen",
        "Sprachenkunde",
        "Wissen (Adel)",
        "Wissen (Arkanes)",
        "Wissen (Geschichte)",
        "Wissen (Die Ebenen)",
        "Wissen (Religion)",
        "Zauberkunde",
    }


def test_kleriker_domain_group_has_all_33_real_domains(client: TestClient, db_session: Session) -> None:
    seed_classes(db_session)
    seed_class_options(db_session)

    kleriker = _kleriker(db_session)
    group = _domain_group(db_session, kleriker)
    assert group.max_choices == 2

    names = {c.name for c in db_session.query(BaseClassOptionChoice).filter_by(group_id=group.id)}
    assert len(names) == 33
    # Guessed placeholder names from before this import must be gone.
    assert "Kriegsdomäne" not in names
    assert "Leben" not in names
    assert "List" not in names
    # Spot-check real names, in the exact "Domäne X" form used on the page.
    assert {"Domäne der Sonne", "Domäne des Todes", "Domäne des Krieges", "Domäne des Wissens"} <= names


def test_kleriker_energie_fokussieren_grants_every_odd_level_through_19(
    client: TestClient, db_session: Session
) -> None:
    seed_classes(db_session)
    seed_class_options(db_session)
    seed_class_abilities(db_session)

    kleriker = _kleriker(db_session)
    ability = db_session.query(BaseClassAbility).filter_by(name="Energie fokussieren").one()
    levels = sorted(
        g.level
        for g in db_session.query(BaseClassAbilityGrant).filter_by(
            base_class_id=kleriker.id, ability_id=ability.id, option_choice_id=None
        )
    )
    assert levels == [1, 3, 5, 7, 9, 11, 13, 15, 17, 19]


def test_kleriker_domain_powers_are_choice_gated_at_the_right_level(client: TestClient, db_session: Session) -> None:
    seed_classes(db_session)
    seed_class_options(db_session)
    seed_class_abilities(db_session)

    kleriker = _kleriker(db_session)
    group = _domain_group(db_session, kleriker)
    sonne = db_session.query(BaseClassOptionChoice).filter_by(group_id=group.id, name="Domäne der Sonne").one()

    segnung = db_session.query(BaseClassAbility).filter_by(name="Segnung der Sonne").one()
    nimbus = db_session.query(BaseClassAbility).filter_by(name="Nimbus des Lichts").one()

    segnung_grant = db_session.query(BaseClassAbilityGrant).filter_by(
        base_class_id=kleriker.id, ability_id=segnung.id
    ).one()
    nimbus_grant = db_session.query(BaseClassAbilityGrant).filter_by(
        base_class_id=kleriker.id, ability_id=nimbus.id
    ).one()

    assert segnung_grant.option_choice_id == sonne.id
    assert segnung_grant.level == 1
    assert nimbus_grant.option_choice_id == sonne.id
    assert nimbus_grant.level == 8


def test_kleriker_domain_choice_surfaces_matching_powers_in_character_sheet(
    client: TestClient, db_session: Session
) -> None:
    """End-to-end proof (same bet already proven for Schurke's Trick and
    Waldläufer's Bund des Jägers): a picked domain is just a
    `CharacterClassOption` plus `option_choice_id`-gated grants, so no
    sheet.py change was needed for domain powers to show up correctly."""
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
                    "class_name": "Kleriker",
                    "level": 1,
                    "options": {"domain": ["Domäne der Sonne", "Domäne des Todes"]},
                }
            ],
        ),
    )
    assert response.status_code == 201
    character_id = response.json()["id"]

    body = client.get(f"/api/characters/{character_id}").json()
    feature_names = {f["name"] for f in body["classFeatures"]}

    # 1st-level powers of the two picked domains, plus unconditional 1st-level features.
    assert {"Segnung der Sonne", "Blutige Hand", "Energie fokussieren", "Domänen"} <= feature_names
    # 8th-level domain powers not available yet at character level 1.
    assert "Nimbus des Lichts" not in feature_names
    assert "Umarmung des Todes" not in feature_names
    # A domain that wasn't picked shouldn't leak in.
    assert "Wort der Begeisterung" not in feature_names
