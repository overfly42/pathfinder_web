"""Character creation must not accept a recurring option-group pick
(Kampfrauschkraft, Trick, Offenbarung, ...) before the character has
actually reached one of that group's own occurrence levels, nor more picks
than the number of occurrences reached — `routers/characters.py`'s
`_validate_options`, using `rules/class_options.py`'s
`group_occurrence_levels` (2026-08-16, closing the gap reported while
testing the Seeräuber archetype: a level-1 Entfesselter Barbar could submit
Kampfrauschkraft picks even though the class's earliest occurrence is
level 2, up to the group's *lifetime* max of 10 rather than however many
occurrences the character's starting level had actually reached)."""

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from test_characters import _character_payload, _create_user, _elf_race_id


def test_kampfrauschkraft_rejected_below_its_first_occurrence(client: TestClient, db_session: Session) -> None:
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
                    "level": 1,
                    "options": {"kampfrauschkraft": ["Zertrümmerer"]},
                }
            ],
        ),
    )
    assert response.status_code == 422
    assert "kampfrauschkraft" in response.json()["detail"]
    assert "level 2" in response.json()["detail"]


def test_kampfrauschkraft_allowed_once_occurrence_reached(client: TestClient, db_session: Session) -> None:
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
                    "options": {"kampfrauschkraft": ["Zertrümmerer"]},
                }
            ],
        ),
    )
    assert response.status_code == 201


def test_kampfrauschkraft_capped_at_occurrences_reached_not_lifetime_max(
    client: TestClient, db_session: Session
) -> None:
    user_id = _create_user(client)
    race_id = _elf_race_id(client, db_session)

    # Level 5 has reached exactly 2 occurrences (2nd, 4th) - a 3rd pick must
    # be rejected even though the group's lifetime max_choices is 10.
    response = client.post(
        "/api/characters",
        json=_character_payload(
            user_id,
            race_id,
            db_session,
            classes=[
                {
                    "class_name": "Entfesselter Barbar",
                    "level": 5,
                    "options": {"kampfrauschkraft": ["Zertrümmerer", "Wuterfülltes Klettern", "Wuterfülltes Schwimmen"]},
                }
            ],
        ),
    )
    assert response.status_code == 422
    assert "2 occurrence(s) reached" in response.json()["detail"]

    response = client.post(
        "/api/characters",
        json=_character_payload(
            user_id,
            race_id,
            db_session,
            classes=[
                {
                    "class_name": "Entfesselter Barbar",
                    "level": 5,
                    "options": {"kampfrauschkraft": ["Zertrümmerer", "Wuterfülltes Klettern"]},
                }
            ],
        ),
    )
    assert response.status_code == 201
