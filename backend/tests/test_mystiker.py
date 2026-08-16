"""Mystiker (Oracle) import - http://prd.5footstep.de/Expertenregeln/Klassen/
Basisklassen/Mystiker, see scripts/import_mystiker.py and todos.md's
2026-08-02 Nachtrag for the full story (this replaced a wrong placeholder
"Orakel" entry: fake mysteries/curses, incomplete known-spell table, wrong
save/skill-point values)."""

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import (
    BaseClass,
    BaseClassAbility,
    BaseClassAbilityGrant,
    BaseClassOptionChoice,
    BaseClassOptionGroup,
    BaseClassSkill,
    BaseClassSpellsKnown,
    BaseSkill,
)
from app.seed.class_ability_seed import seed_class_abilities
from app.seed.class_option_seed import seed_class_options
from app.seed.class_seed import seed_classes
from app.seed.skill_seed import seed_skills
from app.seed.spell_seed import seed_spells

from test_characters import _character_payload, _create_user, _elf_race_id


def _mystiker(db_session: Session) -> BaseClass:
    return db_session.query(BaseClass).filter_by(name="Mystiker").one()


def test_mystiker_base_class_fields_are_real_not_placeholder(client: TestClient, db_session: Session) -> None:
    seed_classes(db_session)

    response = client.get("/api/classes")
    assert response.status_code == 200
    mystiker = next(c for c in response.json() if c["name"] == "Mystiker")

    # Trefferwürfel W8, GAB 3/4, Fertigkeitspunkte 4 + IN-Modifikator, gute
    # Willensrettungswürfe (schlechte Zähigkeit/Reflex - the previous
    # placeholder had fort_save wrongly set to True).
    assert _mystiker(db_session).hit_dice == 8
    assert mystiker["castingAbility"] == "CH"
    assert mystiker["spellTradition"] == "divine"
    assert mystiker["babProgression"] == 0.75
    assert mystiker["fortSave"] is False
    assert mystiker["refSave"] is False
    assert mystiker["willSave"] is True
    assert mystiker["skillPointsBase"] == 4


def test_mystiker_base_class_skills_are_real_and_unconditional_only(
    client: TestClient, db_session: Session
) -> None:
    seed_classes(db_session)
    seed_class_options(db_session)
    seed_skills(db_session)

    response = client.get("/api/classes")
    mystiker = next(c for c in response.json() if c["name"] == "Mystiker")
    skills = {s["id"]: s["name"] for s in client.get("/api/skills").json()}
    names = {skills[sid] for sid in mystiker["classSkills"]}

    # The 9 base class skills - mystery-conditional bonus skills must NOT
    # leak into this unconditional list (that was the case before main.py
    # was taught to filter on option_choice_id IS NULL).
    assert names == {
        "Beruf",
        "Diplomatie",
        "Handwerk",
        "Heilkunde",
        "Motiv erkennen",
        "Wissen (Die Ebenen)",
        "Wissen (Geschichte)",
        "Wissen (Religion)",
        "Zauberkunde",
    }


def test_mystiker_mystery_bonus_skills_are_option_choice_scoped(client: TestClient, db_session: Session) -> None:
    seed_classes(db_session)
    seed_class_options(db_session)
    seed_skills(db_session)

    mystiker = _mystiker(db_session)
    firmament = db_session.query(BaseClassOptionChoice).filter_by(group_id=_group(db_session, mystiker, "mystery").id, name="Firmament").one()
    wissen = db_session.query(BaseClassOptionChoice).filter_by(group_id=_group(db_session, mystiker, "mystery").id, name="Wissen").one()

    skills_by_id = {s.id: s.name for s in db_session.query(BaseSkill).all()}

    firmament_skills = {
        skills_by_id[r.skill_id]
        for r in db_session.query(BaseClassSkill).filter_by(base_class_id=mystiker.id, option_choice_id=firmament.id)
    }
    assert firmament_skills == {"Fliegen", "Überlebenskunst", "Wahrnehmung", "Wissen (Arkanes)"}

    # "Schätzen und alle Wissensfertigkeiten" - 11 skills.
    wissen_skills = {
        skills_by_id[r.skill_id]
        for r in db_session.query(BaseClassSkill).filter_by(base_class_id=mystiker.id, option_choice_id=wissen.id)
    }
    assert len(wissen_skills) == 11
    assert "Schätzen" in wissen_skills
    assert all(name == "Schätzen" or name.startswith("Wissen (") for name in wissen_skills)


def _group(db_session: Session, mystiker: BaseClass, key: str) -> BaseClassOptionGroup:
    return db_session.query(BaseClassOptionGroup).filter_by(base_class_id=mystiker.id, key=key).one()


def test_mystiker_mystery_and_curse_and_heilfokus_choices_are_real(
    client: TestClient, db_session: Session
) -> None:
    seed_classes(db_session)
    seed_class_options(db_session)

    mystiker = _mystiker(db_session)
    mystery_group = _group(db_session, mystiker, "mystery")
    curse_group = _group(db_session, mystiker, "curse")
    heilfokus_group = _group(db_session, mystiker, "heilfokus")

    assert mystery_group.max_choices == 1
    assert curse_group.max_choices == 1
    assert heilfokus_group.max_choices == 1

    mystery_names = {c.name for c in db_session.query(BaseClassOptionChoice).filter_by(group_id=mystery_group.id)}
    curse_names = {c.name for c in db_session.query(BaseClassOptionChoice).filter_by(group_id=curse_group.id)}
    heilfokus_names = {c.name for c in db_session.query(BaseClassOptionChoice).filter_by(group_id=heilfokus_group.id)}

    assert mystery_names == {
        "Firmament", "Flammen", "Gebeine", "Leben", "Natur", "Schlacht", "Stein", "Wellen", "Wind", "Wissen",
    }
    assert curse_names == {"Getrübte Sicht", "Heimgesucht", "Lahm", "Schwindsüchtig", "Taub", "Zungen"}
    assert heilfokus_names == {"Wunden heilen", "Wunden verursachen"}


def test_mystiker_revelation_choices_are_scoped_to_their_mystery_with_min_level(
    client: TestClient, db_session: Session
) -> None:
    """The whole reason `BaseClassOptionChoice.min_level`/`requires_choice_id`
    were added (see the conversation this was scoped from): 100 revelations
    across 10 mysteries share one repeated-pick "revelation" group, but each
    is only legal for its own mystery, and ~25 have their own minimum
    Mystiker level independent of which of the 6 Offenbarung slots fills
    them."""
    seed_classes(db_session)
    seed_class_options(db_session)

    mystiker = _mystiker(db_session)
    mystery_group = _group(db_session, mystiker, "mystery")
    revelation_group = _group(db_session, mystiker, "revelation")
    assert revelation_group.max_choices == 6

    mystery_choice_by_name = {
        c.name: c for c in db_session.query(BaseClassOptionChoice).filter_by(group_id=mystery_group.id)
    }
    revelations = db_session.query(BaseClassOptionChoice).filter_by(group_id=revelation_group.id).all()
    assert len(revelations) == 100

    # Every revelation requires exactly one of the 10 mystery choices.
    mystery_choice_ids = {c.id for c in mystery_choice_by_name.values()}
    assert all(r.requires_choice_id in mystery_choice_ids for r in revelations)

    # 10 revelations per mystery.
    from collections import Counter

    by_mystery = Counter(r.requires_choice_id for r in revelations)
    assert set(by_mystery.values()) == {10}

    # "Kampfheiler" is disambiguated per mystery (Leben and Schlacht both
    # have a revelation with this exact name and text).
    kampfheiler_leben = next(r for r in revelations if r.name == "Kampfheiler (Leben)")
    kampfheiler_schlacht = next(r for r in revelations if r.name == "Kampfheiler (Schlacht)")
    assert kampfheiler_leben.requires_choice_id == mystery_choice_by_name["Leben"].id
    assert kampfheiler_schlacht.requires_choice_id == mystery_choice_by_name["Schlacht"].id
    assert kampfheiler_leben.min_level == 7
    assert kampfheiler_schlacht.min_level == 7

    # Spot-check a handful of the ~25 gated revelations against the page.
    by_name = {r.name: r for r in revelations}
    assert by_name["Bewohner der Dunkelheit"].min_level == 11
    assert by_name["Unsichtbarkeit"].min_level == 3
    assert by_name["Sternenkarte"].min_level == 7
    # Most revelations have no minimum beyond the Offenbarung slot itself.
    assert by_name["Sternenmantel"].min_level is None


def test_create_mystiker_accepts_revelation_matching_the_chosen_mystery(
    client: TestClient, db_session: Session
) -> None:
    """`requires_choice_id` (this file's own "the whole reason it was added"
    docstring above) is `routers/characters.py`'s `_validate_options` -
    cross-group here, unlike Entfesselter Barbar's same-group totem chains:
    "Feuerodem" requires the *separate* "mystery" group's "Flammen" choice,
    not another "revelation" choice. Both are submitted in the same
    creation request, so this must resolve `known_ids` globally across
    every group in the submission, not per group_key."""
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
                    "class_name": "Mystiker",
                    "level": 1,
                    "options": {"mystery": ["Flammen"], "revelation": ["Feuerodem"]},
                }
            ],
        ),
    )
    assert response.status_code == 201
    mystiker = next(c for c in response.json()["classes"] if c["class_name"] == "Mystiker")
    assert mystiker["options"]["mystery"] == ["Flammen"]
    assert mystiker["options"]["revelation"] == ["Feuerodem"]


def test_create_mystiker_rejects_revelation_without_its_mystery(client: TestClient, db_session: Session) -> None:
    user_id = _create_user(client)
    race_id = _elf_race_id(client, db_session)

    response = client.post(
        "/api/characters",
        json=_character_payload(
            user_id,
            race_id,
            db_session,
            classes=[{"class_name": "Mystiker", "level": 1, "options": {"revelation": ["Feuerodem"]}}],
        ),
    )
    assert response.status_code == 422
    assert "Flammen" in response.json()["detail"]


def test_mystiker_offenbarung_and_mysteriumszauber_grant_occurrences(
    client: TestClient, db_session: Session
) -> None:
    seed_classes(db_session)
    seed_class_options(db_session)
    seed_class_abilities(db_session)

    mystiker = _mystiker(db_session)
    offenbarung = db_session.query(BaseClassAbility).filter_by(name="Offenbarung").one()
    mysteriumszauber = db_session.query(BaseClassAbility).filter_by(name="Mysteriumszauber").one()

    offenbarung_levels = sorted(
        g.level
        for g in db_session.query(BaseClassAbilityGrant).filter_by(
            base_class_id=mystiker.id, ability_id=offenbarung.id, option_choice_id=None
        )
    )
    assert offenbarung_levels == [1, 3, 7, 11, 15, 19]

    mysteriumszauber_levels = sorted(
        g.level
        for g in db_session.query(BaseClassAbilityGrant).filter_by(
            base_class_id=mystiker.id, ability_id=mysteriumszauber.id, option_choice_id=None
        )
    )
    assert mysteriumszauber_levels == [2, 4, 6, 8, 10, 12, 14, 16, 18]


def test_mystiker_curses_are_choice_gated_abilities(client: TestClient, db_session: Session) -> None:
    seed_classes(db_session)
    seed_class_options(db_session)
    seed_class_abilities(db_session)

    mystiker = _mystiker(db_session)
    curse_group = _group(db_session, mystiker, "curse")
    curse_choices = {c.name: c for c in db_session.query(BaseClassOptionChoice).filter_by(group_id=curse_group.id)}

    taub = db_session.query(BaseClassAbility).filter_by(name="Taub").one()
    grant = db_session.query(BaseClassAbilityGrant).filter_by(base_class_id=mystiker.id, ability_id=taub.id).one()
    assert grant.option_choice_id == curse_choices["Taub"].id
    assert "Lautlos zaubern" in taub.description


def test_mystiker_final_revelations_are_gated_per_mystery_at_level_20(
    client: TestClient, db_session: Session
) -> None:
    seed_classes(db_session)
    seed_class_options(db_session)
    seed_class_abilities(db_session)

    mystiker = _mystiker(db_session)
    mystery_group = _group(db_session, mystiker, "mystery")
    firmament = db_session.query(BaseClassOptionChoice).filter_by(group_id=mystery_group.id, name="Firmament").one()

    ability = db_session.query(BaseClassAbility).filter_by(name="Letzte Offenbarung (Firmament)").one()
    grant = db_session.query(BaseClassAbilityGrant).filter_by(base_class_id=mystiker.id, ability_id=ability.id).one()
    assert grant.level == 20
    assert grant.option_choice_id == firmament.id
    assert "Sternenkind" in ability.description


def test_mystiker_known_spells_table_is_complete_through_level_20(client: TestClient, db_session: Session) -> None:
    seed_classes(db_session)
    seed_class_options(db_session)  # base_class_spell_grants.option_choice_id FKs here
    seed_spells(db_session)  # base_class_spells_known FKs into base_classes, loaded alongside base_spells

    mystiker = _mystiker(db_session)
    rows = db_session.query(BaseClassSpellsKnown).filter_by(base_class_id=mystiker.id).all()
    by_level_grade = {(r.level, r.grade): r.count for r in rows}

    # Tabelle: Dem Mystiker bekannte Zauber - spot-check the boundaries the
    # old placeholder got wrong (it stopped at level 6 and was missing that
    # level's grade-3 row entirely).
    assert by_level_grade[(1, 0)] == 4
    assert by_level_grade[(1, 1)] == 2
    assert (1, 2) not in by_level_grade  # grade 2 not accessible yet at level 1
    assert by_level_grade[(6, 3)] == 1
    assert by_level_grade[(20, 0)] == 9
    assert by_level_grade[(20, 9)] == 3
    assert len({level for level, _ in by_level_grade}) == 20
