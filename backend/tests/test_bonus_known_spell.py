"""The "add one known spell, grade < highest castable" favored-class-bonus
family — Mystiker's (Halb-Ork/Katzenvolk) and Hexe's (Ork/Elf), now one
shared `BaseClassAbility` row per class (`base_class_abilities.json`'s
"Zusätzlicher Mystikerzauber"/"Zusätzlicher Hexenvertraut-Zauber"). Covers
`rules/spells.py`'s `bonus_known_spell_slot`/`spontaneous_grade_overflow`/
`arcane_prepared_overflows_budget` wiring in `routers/characters.py`, both
at creation and at level-up — see `todos.md`'s "Bevorzugte-Klasse-Bonus
'Zusätzlicher Zauber'" entry for the design this implements."""

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from test_characters import _character_payload, _create_user, _race_id, _spells_by_class
from test_level_up import _level_up_payload


def _spells_by_grade(client: TestClient, class_name: str) -> dict[int, list[str]]:
    by_class = client.get("/api/spells-by-class").json()[class_name]
    result: dict[int, list[str]] = {}
    for spell in by_class:
        result.setdefault(spell["grade"], []).append(spell["id"])
    return result


def test_mystiker_bonus_grants_one_extra_grade0_spell_at_creation(
    client: TestClient, db_session: Session
) -> None:
    user_id = _create_user(client)
    race_id = _race_id(client, db_session, "Katzenvolk")
    mystiker_id, _ = _spells_by_class(client, db_session, "Mystiker")
    by_grade = _spells_by_grade(client, "Mystiker")

    # Level 1 normal budget: grade 0 -> 4, grade 1 -> 2. Highest known grade
    # at level 1 is 1, so the bonus (grade < highest) can only cover grade 0.
    spell_ids = by_grade[0][:5] + by_grade[1][:2]
    payload = _character_payload(
        user_id,
        race_id,
        db_session,
        classes=[{"class_name": "Mystiker", "level": 1}],
        favored_class_bonus={"1": "Katzenvolk (Mystiker)"},
        spell_ids={mystiker_id: spell_ids},
    )
    response = client.post("/api/characters", json=payload)
    assert response.status_code == 201, response.json()
    granted = set(response.json()["spell_ids"][mystiker_id])
    assert granted == set(spell_ids)


def test_mystiker_bonus_cannot_cover_a_spell_at_or_above_the_current_highest_grade(
    client: TestClient, db_session: Session
) -> None:
    user_id = _create_user(client)
    race_id = _race_id(client, db_session, "Katzenvolk")
    mystiker_id, _ = _spells_by_class(client, db_session, "Mystiker")
    by_grade = _spells_by_grade(client, "Mystiker")

    # Normal budget covers 4 grade-0 + 2 grade-1 at level 1; the bonus can
    # only extend grade 0 (< highest known grade 1), never grade 1 itself.
    spell_ids = by_grade[0][:4] + by_grade[1][:3]
    payload = _character_payload(
        user_id,
        race_id,
        db_session,
        classes=[{"class_name": "Mystiker", "level": 1}],
        favored_class_bonus={"1": "Katzenvolk (Mystiker)"},
        spell_ids={mystiker_id: spell_ids},
    )
    response = client.post("/api/characters", json=payload)
    assert response.status_code == 422


def test_mystiker_extra_spell_rejected_without_the_favored_class_bonus(
    client: TestClient, db_session: Session
) -> None:
    user_id = _create_user(client)
    race_id = _race_id(client, db_session, "Katzenvolk")
    mystiker_id, _ = _spells_by_class(client, db_session, "Mystiker")
    by_grade = _spells_by_grade(client, "Mystiker")

    spell_ids = by_grade[0][:5] + by_grade[1][:2]
    payload = _character_payload(
        user_id,
        race_id,
        db_session,
        classes=[{"class_name": "Mystiker", "level": 1}],
        favored_class_bonus={"1": "hp"},
        spell_ids={mystiker_id: spell_ids},
    )
    response = client.post("/api/characters", json=payload)
    assert response.status_code == 422


def test_mystiker_favored_class_bonus_grants_extra_spell_only_the_level_its_picked(
    client: TestClient, db_session: Session
) -> None:
    """Regression for the deliberate "no leftover balance" design
    (`rules/spells.py`'s `bonus_known_spell_slot` docstring): picking the
    bonus at level 4 without spending it that same level-up must not leave
    a usable credit for level 5."""
    user_id = _create_user(client)
    race_id = _race_id(client, db_session, "Katzenvolk")
    mystiker_id, _ = _spells_by_class(client, db_session, "Mystiker")
    by_grade = _spells_by_grade(client, "Mystiker")

    # Level 1, no bonus: exactly the normal budget (4 grade0 + 2 grade1).
    payload = _character_payload(
        user_id,
        race_id,
        db_session,
        classes=[{"class_name": "Mystiker", "level": 1}],
        favored_class_bonus={"1": "hp"},
        spell_ids={mystiker_id: by_grade[0][:4] + by_grade[1][:2]},
    )
    character_id = client.post("/api/characters", json=payload).json()["id"]

    # Level 2: +1 grade0 slot only (budget 5/2), no bonus picked.
    resp = client.post(
        f"/api/characters/{character_id}/level-up",
        json=_level_up_payload(mystiker_id, 4, spell_ids=[by_grade[0][4]]),
    )
    assert resp.status_code == 201, resp.json()

    # Level 3: +1 grade1 slot only (budget 5/3), no bonus picked.
    resp = client.post(
        f"/api/characters/{character_id}/level-up",
        json=_level_up_payload(mystiker_id, 4, spell_ids=[by_grade[1][2]]),
    )
    assert resp.status_code == 201, resp.json()

    # Level 4: budget becomes 6/3/1 (grade 2 unlocks). Pick the favored
    # class bonus but only submit the normal +1 grade0 delta — the bonus
    # goes unused this level-up.
    resp = client.post(
        f"/api/characters/{character_id}/level-up",
        json=_level_up_payload(
            mystiker_id,
            4,
            favored_class_bonus="Katzenvolk (Mystiker)",
            spell_ids=[by_grade[0][5]],
            ability_increase="ST",
        ),
    )
    assert resp.status_code == 201, resp.json()

    # Level 5: budget stays 6/4/1 (+1 grade1 delta only). No bonus picked
    # this level, so trying to also grab a 2nd grade-1 spell (using what
    # would be a leftover bonus credit from level 4) must fail.
    resp = client.post(
        f"/api/characters/{character_id}/level-up",
        json=_level_up_payload(mystiker_id, 4, spell_ids=[by_grade[1][3], by_grade[1][4]]),
    )
    assert resp.status_code == 422


def test_mystiker_favored_class_bonus_at_level_up_grants_a_grade_below_the_new_highest(
    client: TestClient, db_session: Session
) -> None:
    user_id = _create_user(client)
    race_id = _race_id(client, db_session, "Halb-Ork")
    mystiker_id, _ = _spells_by_class(client, db_session, "Mystiker")
    by_grade = _spells_by_grade(client, "Mystiker")

    payload = _character_payload(
        user_id,
        race_id,
        db_session,
        classes=[{"class_name": "Mystiker", "level": 3}],
        favored_class_bonus={str(lvl): "hp" for lvl in (1, 2, 3)},
        hit_points={"2": 1, "3": 1},
        flex_ability="CH",
        spell_ids={mystiker_id: by_grade[0][:5] + by_grade[1][:3]},
    )
    character_id = client.post("/api/characters", json=payload).json()["id"]

    # Level 4: budget 6/3/1 -> normal delta is +1 grade0, +0 grade1, +1
    # grade2 (all mandatory-none, player picks it). Highest known grade
    # becomes 2, so the bonus (grade < 2) can cover an *extra* grade-1 pick
    # on top of the normal delta.
    resp = client.post(
        f"/api/characters/{character_id}/level-up",
        json=_level_up_payload(
            mystiker_id,
            4,
            favored_class_bonus="Halb-Ork (Mystiker)",
            spell_ids=[by_grade[0][5], by_grade[1][3]],
            ability_increase="ST",
        ),
    )
    assert resp.status_code == 201, resp.json()

    # Same level-up, but trying to spend the bonus on the new *top* grade
    # (grade 2) instead must fail — RAW requires strictly below the highest.
    payload2 = _character_payload(
        user_id,
        race_id,
        db_session,
        classes=[{"class_name": "Mystiker", "level": 3}],
        favored_class_bonus={str(lvl): "hp" for lvl in (1, 2, 3)},
        hit_points={"2": 1, "3": 1},
        flex_ability="CH",
        spell_ids={mystiker_id: by_grade[0][:5] + by_grade[1][:3]},
    )
    character_id2 = client.post("/api/characters", json=payload2).json()["id"]
    resp2 = client.post(
        f"/api/characters/{character_id2}/level-up",
        json=_level_up_payload(
            mystiker_id,
            4,
            favored_class_bonus="Halb-Ork (Mystiker)",
            spell_ids=[by_grade[2][0], by_grade[2][1]] if len(by_grade.get(2, [])) > 1 else [by_grade[0][5]],
            ability_increase="ST",
        ),
    )
    # Only meaningful if grade 2 actually has >= 2 distinct spells to pick
    # two of (guards against a thin fixture); otherwise this collapses to
    # the same normal-budget-only pick already covered above.
    if len(by_grade.get(2, [])) > 1:
        assert resp2.status_code == 422


def test_hexe_bonus_grants_one_extra_spellbook_slot_at_creation(client: TestClient, db_session: Session) -> None:
    user_id = _create_user(client)
    race_id = _race_id(client, db_session, "Elf")
    hexe_id, _ = _spells_by_class(client, db_session, "Hexe")
    by_grade = _spells_by_grade(client, "Hexe")

    # Level 3: grade 2 unlocks here (highest known grade 2, so the bonus,
    # grade < highest, can reach grade 1 - unlike level 1/2 where grade 0 is
    # already free/mandatory and thus not a meaningful bonus target). Elf's
    # own +2 IN -> casting mod +1 -> arcane_prepared_budget(3, 1) =
    # (2+1) + 2*2 = 7. Every grade-0 spell is mandatory/free and excluded
    # from the budget; the bonus adds 1 more grade-1 slot on top of the
    # normal 7.
    grade0_ids = by_grade[0]
    payload = _character_payload(
        user_id,
        race_id,
        db_session,
        classes=[{"class_name": "Hexe", "level": 3}],
        favored_class_bonus={"1": "hp", "2": "hp", "3": "Elf (Hexe)"},
        hit_points={"2": 1, "3": 1},
        spell_ids={hexe_id: grade0_ids + by_grade[1][:8]},
    )
    response = client.post("/api/characters", json=payload)
    assert response.status_code == 201, response.json()


def test_hexe_extra_spellbook_slot_rejected_without_the_favored_class_bonus(
    client: TestClient, db_session: Session
) -> None:
    user_id = _create_user(client)
    race_id = _race_id(client, db_session, "Elf")
    hexe_id, _ = _spells_by_class(client, db_session, "Hexe")
    by_grade = _spells_by_grade(client, "Hexe")

    grade0_ids = by_grade[0]
    payload = _character_payload(
        user_id,
        race_id,
        db_session,
        classes=[{"class_name": "Hexe", "level": 3}],
        favored_class_bonus={"1": "hp", "2": "hp", "3": "hp"},
        hit_points={"2": 1, "3": 1},
        spell_ids={hexe_id: grade0_ids + by_grade[1][:8]},
    )
    response = client.post("/api/characters", json=payload)
    assert response.status_code == 422
