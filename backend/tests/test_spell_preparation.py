"""Prepare/cast mechanics for arcane- and divine-prepared casters (roadmap
slice 6) — `POST`/`DELETE .../spells/{spell_id}/prepare`,
`POST .../spells/{spell_id}/cast`, and the day-tick/rest reset
(`rules/daily_limits.py`'s `reset_spell_preparations`). Spontaneous casters
(no preparation step at all) are out of scope, see `rules/spells.py`'s
module docstring."""

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.seed.class_option_seed import seed_class_options
from app.seed.class_seed import seed_classes
from app.seed.spell_seed import seed_spells

from test_characters import _cantrip_ids, _character_payload, _create_user, _elf_race_id, _spells_by_class


def _magier_character(client: TestClient, db_session: Session) -> tuple[dict, str, dict[str, str]]:
    user_id = _create_user(client)
    race_id = _elf_race_id(client, db_session)
    base_class_id, spells = _spells_by_class(client, db_session, "Magier")
    cantrips = _cantrip_ids(client, "Magier")
    picked = cantrips + [spells["Magisches Geschoss"], spells["Schild"]]
    created = client.post(
        "/api/characters",
        json=_character_payload(
            user_id,
            race_id,
            db_session,
            classes=[{"class_name": "Magier", "level": 1}],
            spell_ids={base_class_id: picked},
        ),
    ).json()
    return created, base_class_id, spells


def _kleriker_character(client: TestClient, db_session: Session) -> tuple[dict, str, dict[str, str]]:
    user_id = _create_user(client)
    race_id = _elf_race_id(client, db_session)
    base_class_id, spells = _spells_by_class(client, db_session, "Kleriker")
    created = client.post(
        "/api/characters",
        json=_character_payload(
            user_id, race_id, db_session, classes=[{"class_name": "Kleriker", "level": 1}]
        ),
    ).json()
    return created, base_class_id, spells


def _kensai_character(client: TestClient, db_session: Session) -> tuple[dict, str, dict[str, str]]:
    """A level-1 Kensai (Kampfmagus archetype) with average IN (mod 0), so
    the grade-1 slot count isolates the archetype's "Vermindertes
    Zauberwirken" reduction from any ability-modifier bonus."""
    user_id = _create_user(client)
    race_id = _elf_race_id(client, db_session)
    base_class_id, spells = _spells_by_class(client, db_session, "Kampfmagus")
    cantrips = _cantrip_ids(client, "Kampfmagus")
    picked = cantrips + [spells["Schild"]]
    created = client.post(
        "/api/characters",
        json=_character_payload(
            user_id,
            race_id,
            db_session,
            classes=[{"class_name": "Kampfmagus", "level": 1, "archetypes": ["Kensai"]}],
            spell_ids={base_class_id: picked},
            ability_scores={"ST": 10, "GE": 12, "KO": 13, "IN": 8, "WE": 10, "CH": 8},
        ),
    ).json()
    return created, base_class_id, spells


def _sheet(client: TestClient, character_id: str) -> dict:
    return client.get(f"/api/characters/{character_id}").json()


def _grade1(sheet: dict, key: str) -> dict:
    return next(g for g in sheet[key] if g["grade"] == 1)


def test_prepare_spell_for_arcane_prepared_character(client: TestClient, db_session: Session) -> None:
    character, base_class_id, spells = _magier_character(client, db_session)

    response = client.post(
        f"/api/characters/{character['id']}/spells/{spells['Magisches Geschoss']}/prepare",
        json={"base_class_id": base_class_id},
    )
    assert response.status_code == 200

    sheet = _sheet(client, character["id"])
    spell = next(s for s in _grade1(sheet, "spellbook")["spells"] if s["key"] == spells["Magisches Geschoss"])
    assert spell["preparedCount"] == 1
    assert spell["usedCount"] == 0
    known_spell = next(s for s in _grade1(sheet, "spellsKnown")["spells"] if s["key"] == spells["Magisches Geschoss"])
    assert known_spell["preparedCount"] == 1


def test_prepare_same_spell_twice_increments_count(client: TestClient, db_session: Session) -> None:
    character, base_class_id, spells = _magier_character(client, db_session)

    for _ in range(2):
        response = client.post(
            f"/api/characters/{character['id']}/spells/{spells['Magisches Geschoss']}/prepare",
            json={"base_class_id": base_class_id},
        )
        assert response.status_code == 200

    sheet = _sheet(client, character["id"])
    spell = next(s for s in _grade1(sheet, "spellbook")["spells"] if s["key"] == spells["Magisches Geschoss"])
    assert spell["preparedCount"] == 2


def test_prepare_spell_not_in_spellbook_is_rejected(client: TestClient, db_session: Session) -> None:
    character, base_class_id, spells = _magier_character(client, db_session)

    response = client.post(
        f"/api/characters/{character['id']}/spells/{spells['Nebelwolke']}/prepare",
        json={"base_class_id": base_class_id},
    )
    assert response.status_code == 422


def test_prepare_spell_respects_grade_slot_cap(client: TestClient, db_session: Session) -> None:
    character, base_class_id, spells = _magier_character(client, db_session)
    # A level-1 Magier gets 1 base grade-1 slot/day; the default payload's Elf
    # race gives +2 IN (base 10 -> 12, mod +1), which is enough for the
    # standard bonus-spells table's grade-1 threshold (mod >= +1) to add one
    # more -- so the real cap here is 2, not 1.
    sheet = _sheet(client, character["id"])
    assert _grade1(sheet, "spellbook")["perDay"] == 2

    for _ in range(2):
        response = client.post(
            f"/api/characters/{character['id']}/spells/{spells['Magisches Geschoss']}/prepare",
            json={"base_class_id": base_class_id},
        )
        assert response.status_code == 200

    third = client.post(
        f"/api/characters/{character['id']}/spells/{spells['Schild']}/prepare",
        json={"base_class_id": base_class_id},
    )
    assert third.status_code == 422


def test_unprepare_spell_decrements_count(client: TestClient, db_session: Session) -> None:
    character, base_class_id, spells = _magier_character(client, db_session)
    client.post(
        f"/api/characters/{character['id']}/spells/{spells['Magisches Geschoss']}/prepare",
        json={"base_class_id": base_class_id},
    )

    response = client.delete(
        f"/api/characters/{character['id']}/spells/{spells['Magisches Geschoss']}/prepare",
        params={"base_class_id": base_class_id},
    )
    assert response.status_code == 204

    sheet = _sheet(client, character["id"])
    # A grade with nothing prepared doesn't appear in spellsKnown at all (the
    # cast bar), unlike spellbook which always lists every accessible grade.
    assert all(g["grade"] != 1 for g in sheet["spellsKnown"])


def test_unprepare_already_cast_copy_is_rejected(client: TestClient, db_session: Session) -> None:
    character, base_class_id, spells = _magier_character(client, db_session)
    client.post(
        f"/api/characters/{character['id']}/spells/{spells['Magisches Geschoss']}/prepare",
        json={"base_class_id": base_class_id},
    )
    client.post(
        f"/api/characters/{character['id']}/spells/{spells['Magisches Geschoss']}/cast",
        json={"base_class_id": base_class_id},
    )

    response = client.delete(
        f"/api/characters/{character['id']}/spells/{spells['Magisches Geschoss']}/prepare",
        params={"base_class_id": base_class_id},
    )
    assert response.status_code == 422


def test_cast_spell_consumes_a_prepared_copy_and_rejects_once_exhausted(
    client: TestClient, db_session: Session
) -> None:
    character, base_class_id, spells = _magier_character(client, db_session)
    client.post(
        f"/api/characters/{character['id']}/spells/{spells['Magisches Geschoss']}/prepare",
        json={"base_class_id": base_class_id},
    )

    first_cast = client.post(
        f"/api/characters/{character['id']}/spells/{spells['Magisches Geschoss']}/cast",
        json={"base_class_id": base_class_id},
    )
    assert first_cast.status_code == 200

    sheet = _sheet(client, character["id"])
    spell = next(s for s in _grade1(sheet, "spellsKnown")["spells"] if s["key"] == spells["Magisches Geschoss"])
    assert spell["usedCount"] == 1
    assert spell["preparedCount"] == 1

    second_cast = client.post(
        f"/api/characters/{character['id']}/spells/{spells['Magisches Geschoss']}/cast",
        json={"base_class_id": base_class_id},
    )
    assert second_cast.status_code == 422


def test_cast_unprepared_spell_is_rejected(client: TestClient, db_session: Session) -> None:
    character, base_class_id, spells = _magier_character(client, db_session)

    response = client.post(
        f"/api/characters/{character['id']}/spells/{spells['Magisches Geschoss']}/cast",
        json={"base_class_id": base_class_id},
    )
    assert response.status_code == 422


def test_advance_time_by_day_clears_all_preparations(client: TestClient, db_session: Session) -> None:
    character, base_class_id, spells = _magier_character(client, db_session)
    client.post(
        f"/api/characters/{character['id']}/spells/{spells['Magisches Geschoss']}/prepare",
        json={"base_class_id": base_class_id},
    )
    client.post(
        f"/api/characters/{character['id']}/spells/{spells['Magisches Geschoss']}/cast",
        json={"base_class_id": base_class_id},
    )

    response = client.post(f"/api/characters/{character['id']}/advance-time", json={"unit": "day"})
    assert response.status_code == 200

    sheet = _sheet(client, character["id"])
    spell = next(s for s in _grade1(sheet, "spellbook")["spells"] if s["key"] == spells["Magisches Geschoss"])
    assert spell["preparedCount"] == 0
    assert spell["usedCount"] == 0
    assert all(g["grade"] != 1 for g in sheet["spellsKnown"])


def test_rest_clears_all_preparations(client: TestClient, db_session: Session) -> None:
    character, base_class_id, spells = _magier_character(client, db_session)
    client.post(
        f"/api/characters/{character['id']}/spells/{spells['Magisches Geschoss']}/prepare",
        json={"base_class_id": base_class_id},
    )

    response = client.post(f"/api/characters/{character['id']}/rest")
    assert response.status_code == 200

    sheet = _sheet(client, character["id"])
    spell = next(s for s in _grade1(sheet, "spellbook")["spells"] if s["key"] == spells["Magisches Geschoss"])
    assert spell["preparedCount"] == 0


def test_prepare_divine_prepared_from_full_class_list_without_a_spellbook(
    client: TestClient, db_session: Session
) -> None:
    character, base_class_id, spells = _kleriker_character(client, db_session)

    response = client.post(
        f"/api/characters/{character['id']}/spells/{spells['Segnen']}/prepare",
        json={"base_class_id": base_class_id},
    )
    assert response.status_code == 200

    sheet = _sheet(client, character["id"])
    spell = next(s for s in _grade1(sheet, "spellbook")["spells"] if s["key"] == spells["Segnen"])
    assert spell["preparedCount"] == 1


def test_prepare_divine_prepared_rejects_inaccessible_grade(client: TestClient, db_session: Session) -> None:
    character, base_class_id, spells = _kleriker_character(client, db_session)
    grade2_spell = next(
        s["id"]
        for s in client.get("/api/spells-by-class").json()["Kleriker"]
        if s["grade"] == 2
    )

    response = client.post(
        f"/api/characters/{character['id']}/spells/{grade2_spell}/prepare",
        json={"base_class_id": base_class_id},
    )
    assert response.status_code == 422


def test_cantrip_can_be_cast_any_number_of_times_once_prepared(client: TestClient, db_session: Session) -> None:
    """PF1e RAW: a prepared cantrip/orison is never expended — `usedCount`
    is neither checked nor incremented for grade 0."""
    character, base_class_id, spells = _magier_character(client, db_session)
    cantrip_id = _cantrip_ids(client, "Magier")[0]
    client.post(
        f"/api/characters/{character['id']}/spells/{cantrip_id}/prepare",
        json={"base_class_id": base_class_id},
    )

    for _ in range(5):
        response = client.post(
            f"/api/characters/{character['id']}/spells/{cantrip_id}/cast",
            json={"base_class_id": base_class_id},
        )
        assert response.status_code == 200

    sheet = _sheet(client, character["id"])
    grade0 = next(g for g in sheet["spellbook"] if g["grade"] == 0)
    spell = next(s for s in grade0["spells"] if s["key"] == cantrip_id)
    assert spell["preparedCount"] == 1
    assert spell["usedCount"] == 0


def test_folding_applies_generally_not_just_to_kensai(client: TestClient, db_session: Session) -> None:
    """The "fold a still-locked grade's bonus spell into the highest
    accessible grade" house rule applies to any prepared caster, not just
    an archetype with diminished spellcasting — a plain level-1 Magier with
    a high enough INT already hits it: grade 2/3 are locked at level 1
    regardless of archetype, so their bonus spells (from `bonus_spells_from_mod`)
    fold into grade 1 the same way."""
    user_id = _create_user(client)
    race_id = _elf_race_id(client, db_session)
    base_class_id, spells = _spells_by_class(client, db_session, "Magier")
    cantrips = _cantrip_ids(client, "Magier")
    picked = cantrips + [spells["Magisches Geschoss"]]
    character = client.post(
        "/api/characters",
        json=_character_payload(
            user_id,
            race_id,
            db_session,
            classes=[{"class_name": "Magier", "level": 1}],
            spell_ids={base_class_id: picked},
            # Elf +2 IN -> effective 14, mod +2: grade-1 bonus is 1, grade-2's
            # own bonus (also 1, mod >= grade) is locked at level 1 and folds
            # into grade 1. Total grade-1 slots: base 1 + own bonus 1 +
            # folded grade-2 bonus 1 = 3.
            ability_scores={"ST": 10, "GE": 12, "KO": 13, "IN": 12, "WE": 10, "CH": 8},
        ),
    ).json()

    sheet = _sheet(client, character["id"])
    assert _grade1(sheet, "spellbook")["perDay"] == 3


def test_kensai_archetype_reduces_spell_slots_by_one_per_grade(client: TestClient, db_session: Session) -> None:
    """Kensai's "Vermindertes Zauberwirken": one fewer base slot per grade
    (before the ability-modifier bonus) — with average INT (no bonus spell
    at grade 1), a level-1 Kensai's base grade-1 slot (normally 1) is
    reduced to 0 entirely, while grade 0 (base 3, never eligible for a bonus
    spell) drops to 2."""
    character, _, _ = _kensai_character(client, db_session)

    sheet = _sheet(client, character["id"])
    grade0 = next(g for g in sheet["spellbook"] if g["grade"] == 0)
    grade1 = next(g for g in sheet["spellbook"] if g["grade"] == 1)
    assert grade0["perDay"] == 2
    assert grade1["perDay"] == 0


def test_kensai_can_still_prepare_a_grade_reduced_to_zero_if_a_bonus_spell_applies(
    client: TestClient, db_session: Session
) -> None:
    """RAW's explicit carve-out: "kann er nur dann Zauber dieses Grades
    wirken, wenn er Bonuszauber aufgrund seiner Intelligenz für diesen Grad
    erhält" — a high enough INT still grants grade-1 slots even though the
    archetype reduces the base to 0. Also exercises the "fold a still-locked
    grade's bonus into the highest accessible grade" house rule: at mod +3,
    grade 2 and grade 3 (both locked at level 1) would each grant their own
    +1 bonus spell (`bonus_spells_from_mod`); since the class can't actually
    reach those grades yet, both fold into grade 1's total instead of being
    lost — grade 1 ends up with 0 (reduced base) + 1 (its own bonus) + 1
    (folded from grade 2) + 1 (folded from grade 3) = 3."""
    user_id = _create_user(client)
    race_id = _elf_race_id(client, db_session)
    base_class_id, spells = _spells_by_class(client, db_session, "Kampfmagus")
    cantrips = _cantrip_ids(client, "Kampfmagus")
    picked = cantrips + [spells["Schild"]]
    character = client.post(
        "/api/characters",
        json=_character_payload(
            user_id,
            race_id,
            db_session,
            classes=[{"class_name": "Kampfmagus", "level": 1, "archetypes": ["Kensai"]}],
            spell_ids={base_class_id: picked},
            # Elf +2 IN -> effective 16, mod +3.
            ability_scores={"ST": 10, "GE": 12, "KO": 13, "IN": 14, "WE": 10, "CH": 8},
        ),
    ).json()

    sheet = _sheet(client, character["id"])
    assert _grade1(sheet, "spellbook")["perDay"] == 3

    for _ in range(3):
        response = client.post(
            f"/api/characters/{character['id']}/spells/{spells['Schild']}/prepare",
            json={"base_class_id": base_class_id},
        )
        assert response.status_code == 200

    fourth = client.post(
        f"/api/characters/{character['id']}/spells/{spells['Schild']}/prepare",
        json={"base_class_id": base_class_id},
    )
    assert fourth.status_code == 422
