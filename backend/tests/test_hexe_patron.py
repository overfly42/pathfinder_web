"""Hexe's "Schutzherr" (Patron) option group (2026-08-30,
`scripts/import_hexe_patrons.py`) and the `BaseClassSpellGrant` ->
`CharacterSpell` wiring (`rules/spells.py`'s `granted_option_choice_spells`)
that turns a chosen patron's bonus spells into real spellbook candidates —
same mechanism Hexenmeister's Blutlinie data will use once spontaneous
casters get a spellbook (see `sheet.py`'s module docstring)."""

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.seed.class_ability_seed import seed_class_abilities
from app.seed.class_option_seed import seed_class_options
from app.seed.class_seed import seed_classes
from app.seed.spell_seed import seed_spells
from test_characters import _character_payload, _create_user, _elf_race_id
from test_level_up import _class_id, _level_up_payload


def _spellbook_names(character: dict) -> set[str]:
    return {spell["name"] for grade in character["spellbook"] for spell in grade["spells"]}


def test_hexe_has_patron_option_group_with_18_choices(client: TestClient, db_session: Session) -> None:
    seed_classes(db_session)
    seed_class_options(db_session)

    classes = client.get("/api/classes").json()
    hexe = next(c for c in classes if c["name"] == "Hexe")
    patron_group = next(g for g in hexe["optionGroups"] if g["key"] == "patron")

    assert patron_group["label"] == "Schutzherr"
    assert patron_group["max"] == 1
    names = {c["name"] for c in patron_group["choices"]}
    assert names == {
        "Ausdauer", "Beweglichkeit", "Elemente", "Schatten", "Seuche", "Stärke",
        "Täuschung", "Tiere", "Trickserei", "Verwandlung", "Wasser", "Weisheit",
        "Ahnen", "Tod", "Heilung", "Pflanzen", "Zeit", "Winter",
    }


def test_kraeuterhexe_description_visible_via_api(client: TestClient, db_session: Session) -> None:
    """Kräuterhexe's "only nature-aligned Schutzherren"/Kessel-at-2nd-level
    restrictions were only ever prose inside a BaseClassAbility.description
    — never surfaced anywhere. `archetypeDescriptions` (`main.py`) now
    exposes it generically for every archetype, not just Kräuterhexe."""
    seed_classes(db_session)
    seed_class_options(db_session)
    seed_class_abilities(db_session)  # archetypeDescriptions reads BaseClassAbilityGrant

    classes = client.get("/api/classes").json()
    hexe = next(c for c in classes if c["name"] == "Hexe")
    description = hexe["archetypeDescriptions"]["Kräuterhexe"]
    assert "Natur verbunden" in description
    assert "Kessel" in description

    narbiger = hexe["archetypeDescriptions"]["Narbiger Hexendoktor"]
    assert "Fetischmaske" in narbiger or "Narbenschild" in narbiger


def test_patron_bonus_spells_granted_at_creation(client: TestClient, db_session: Session) -> None:
    user_id = _create_user(client)
    race_id = _elf_race_id(client, db_session)

    payload = _character_payload(
        user_id,
        race_id,
        db_session,
        classes=[{"class_name": "Hexe", "level": 3, "options": {"patron": ["Elemente"]}}],
    )
    # base_class_spell_grants FKs into base_classes/base_class_option_choices,
    # both already seeded by _character_payload above.
    seed_spells(db_session)

    response = client.post("/api/characters", json=payload)
    assert response.status_code == 201
    character_id = response.json()["id"]

    sheet = client.get(f"/api/characters/{character_id}").json()
    names = _spellbook_names(sheet)
    # Elemente grants Schockgriff at 2nd level (reached) but not Flammenkugel
    # (4th level, not reached yet at class level 3).
    assert "Schockgriff" in names
    assert "Flammenkugel" not in names


def test_patron_bonus_spell_granted_on_level_up_without_duplicating(
    client: TestClient, db_session: Session
) -> None:
    race_id = _elf_race_id(client, db_session)
    hexe_id = _class_id(client, db_session, "Hexe")  # seeds classes
    seed_class_options(db_session)  # base_class_spell_grants.option_choice_id FKs here
    seed_spells(db_session)

    response = client.post(
        "/api/characters",
        json=_character_payload(
            _create_user(client),
            race_id,
            db_session,
            classes=[{"class_name": "Hexe", "level": 3, "options": {"patron": ["Elemente"]}}],
        ),
    )
    assert response.status_code == 201
    character_id = response.json()["id"]

    level_up = client.post(
        f"/api/characters/{character_id}/level-up",
        json=_level_up_payload(hexe_id, hit_points=4, ability_increase="IN"),
    )
    assert level_up.status_code == 201

    sheet = client.get(f"/api/characters/{character_id}").json()
    names_by_spell = [spell["name"] for grade in sheet["spellbook"] for spell in grade["spells"]]
    # Reaching level 4 grants Flammenkugel; Schockgriff (already granted at
    # creation) must not be duplicated.
    assert names_by_spell.count("Schockgriff") == 1
    assert names_by_spell.count("Flammenkugel") == 1
