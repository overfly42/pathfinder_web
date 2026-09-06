"""Katzenvolk's "Kletterer" alternate racial trait (replaces "Spurter"):
grants a 6 m climb speed and the flat +8 Volksbonus on Klettern checks that
comes with it (`rules/speed.py`'s `_kletterer`). Also covers the
`race_skill_modifiers` fix this needed: as an alternate trait, Kletterer
(and Katzenvolk's other alternate skill-bonus trait, "Kluge Katze") was
previously never applied at all — that function only ever read a race's
*default* (non-alternate) grants, so a chosen alternate's own bonus was
silently dropped while the base trait it replaced kept applying regardless
of the player's actual pick."""

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from test_characters import _character_payload, _create_user, _race_id, _skill_id


def _katzenvolk_race_id(client: TestClient, db_session: Session) -> str:
    return _race_id(client, db_session, "Katzenvolk")


def test_kletterer_grants_climb_speed_and_its_skill_bonus(client: TestClient, db_session: Session) -> None:
    user_id = _create_user(client)
    race_id = _katzenvolk_race_id(client, db_session)
    klettern_id = _skill_id(client, db_session, "Klettern")

    character = client.post(
        "/api/characters",
        json=_character_payload(user_id, race_id, db_session, alt_traits=["Kletterer"]),
    ).json()

    sheet = client.get(f"/api/characters/{character['id']}").json()
    assert sheet["climbSpeed"] == "6 m"

    # ST 10 -> +0 mod, no ranks -> the whole value is Kletterer's own +8
    # Volksbonus.
    klettern = next(s for s in sheet["skills"] if s["key"] == klettern_id)
    assert klettern["value"] == "+8"


def test_character_without_kletterer_has_no_climb_speed(client: TestClient, db_session: Session) -> None:
    user_id = _create_user(client)
    race_id = _katzenvolk_race_id(client, db_session)

    character = client.post("/api/characters", json=_character_payload(user_id, race_id, db_session)).json()

    sheet = client.get(f"/api/characters/{character['id']}").json()
    assert sheet["climbSpeed"] is None


def test_kluge_katze_alt_trait_applies_its_own_bonus_not_natuerlicher_jaegers(
    client: TestClient, db_session: Session
) -> None:
    """Regression for the same `race_skill_modifiers` gap Kletterer hit:
    picking "Kluge Katze" (replaces "Natürlicher Jäger") must grant its own
    +2 Bluffen/Diplomatie/Motiv erkennen, and must NOT also keep
    Natürlicher Jäger's +2 Heimlichkeit/Überlebenskunst/Wahrnehmung — the
    previous non-alternate-only scope did the opposite of both."""
    user_id = _create_user(client)
    race_id = _katzenvolk_race_id(client, db_session)
    bluffen_id = _skill_id(client, db_session, "Bluffen")
    heimlichkeit_id = _skill_id(client, db_session, "Heimlichkeit")

    character = client.post(
        "/api/characters",
        json=_character_payload(user_id, race_id, db_session, alt_traits=["Kluge Katze"]),
    ).json()

    sheet = client.get(f"/api/characters/{character['id']}").json()
    skills_by_key = {s["key"]: s for s in sheet["skills"]}
    # Katzenvolk's own +2 CH -> CH 8+2=10 -> +0 mod, +2 Kluge Katze -> +2.
    assert skills_by_key[bluffen_id]["value"] == "+2"
    # Katzenvolk's own +2 GE -> GE 12+2=14 -> +2 mod, no Natürlicher Jäger
    # anymore -> +2, not +4.
    assert skills_by_key[heimlichkeit_id]["value"] == "+2"


def test_default_katzenvolk_still_gets_natuerlicher_jaegers_bonus(client: TestClient, db_session: Session) -> None:
    """Baseline for the fix above: a character who picks no alternate trait
    at all must still get Natürlicher Jäger's default +2, unaffected by
    `race_skill_modifiers` now resolving via the character's actual
    (rather than always-default) ability set."""
    user_id = _create_user(client)
    race_id = _katzenvolk_race_id(client, db_session)
    heimlichkeit_id = _skill_id(client, db_session, "Heimlichkeit")

    character = client.post("/api/characters", json=_character_payload(user_id, race_id, db_session)).json()

    sheet = client.get(f"/api/characters/{character['id']}").json()
    heimlichkeit = next(s for s in sheet["skills"] if s["key"] == heimlichkeit_id)
    # Katzenvolk's own +2 GE -> GE 12+2=14 -> +2 mod, +2 Natürlicher Jäger -> +4.
    assert heimlichkeit["value"] == "+4"
