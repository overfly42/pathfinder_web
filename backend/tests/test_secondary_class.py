"""Sekundärklasse alternate rule (http://prd.5footstep.de/Alternativregeln/
Fertigkeiten/AlternativesSystemfuerCharakteremitKlassenkombinationen) —
architecture pass only, see roadmap.md: no per-class content is seeded yet
(`base_secondary_class_ability_grants.json` is empty), so the end-to-end
test below adds one ad hoc `BaseSecondaryClassAbilityGrant` row directly
(same "exercise the mechanism against synthetic data" convention
`test_option_choice_min_level_and_requires_choice_id_round_trip`
(test_entfesselter_barbar.py) already uses) rather than depending on real
content existing. Entfesselter Barbar is the one class actually reused here
because it's one of only two classes with a real `HANDLERS`/`DAILY_LIMITS`
entry today (`rules/classes/barbarian.py` — the plain "Barbar" root has no
handler for its own Kampfrausch, only Entfesselter Barbar does)."""

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import BaseClass, BaseSecondaryClassAbilityGrant
from app.rules.classes.barbarian import (
    BARBAR_ENTFESSELTER_ROOT_CLASS_ID,
    KAMPFRAUSCH_ENTFESSELTER_BARBAR_ABILITY_ID,
)
from app.rules.feat_slots import SECONDARY_CLASS_FEATURE_LEVELS, secondary_class_suppressed_feat_count
from app.rules.secondary_class import secondary_effective_level

from test_characters import _character_payload, _create_user, _elf_race_id, _feat_id


def test_secondary_effective_level_formula() -> None:
    assert secondary_effective_level(10) == 10
    assert secondary_effective_level(10, offset=-4) == 6
    assert secondary_effective_level(1, offset=-6, minimum=1) == 1  # floored, never negative
    assert secondary_effective_level(11, divisor=2) == 5  # floor division, not rounded


def test_secondary_class_suppressed_feat_count_counts_reached_milestones() -> None:
    assert secondary_class_suppressed_feat_count(1) == 0
    assert secondary_class_suppressed_feat_count(3) == 1
    assert secondary_class_suppressed_feat_count(6) == 1
    assert secondary_class_suppressed_feat_count(7) == 2
    assert secondary_class_suppressed_feat_count(20) == len(SECONDARY_CLASS_FEATURE_LEVELS) == 5


def test_create_character_with_secondary_class_replaces_the_3rd_level_talent(
    client: TestClient, db_session: Session
) -> None:
    """Waldläufer 3 normally grants 2 feats (1st + 3rd level). With an
    active Sekundärklasse, the 3rd-level slot is replaced by a
    Sekundärklasse feature instead — only 1 feat should be accepted."""
    user_id = _create_user(client)
    race_id = _elf_race_id(client, db_session)
    ausweichen_id = _feat_id(client, db_session, "Ausweichen")
    kampfreflexe_id = _feat_id(client, db_session, "Kampfreflexe")

    base_payload = _character_payload(
        user_id,
        race_id,
        db_session,
        classes=[{"class_name": "Waldläufer", "level": 3}],
        secondary_class_name="Entfesselter Barbar",
    )

    too_many = {**base_payload, "feats": [{"feat_id": ausweichen_id}, {"feat_id": kampfreflexe_id}]}
    response = client.post("/api/characters", json=too_many)
    assert response.status_code == 422

    ok = {**base_payload, "feats": [{"feat_id": ausweichen_id}]}
    response = client.post("/api/characters", json=ok)
    assert response.status_code == 201
    body = response.json()
    assert body["secondary_base_class_id"] is not None


def test_create_character_without_secondary_class_keeps_both_feats(
    client: TestClient, db_session: Session
) -> None:
    """Control for the test above: without opting into the rule, Waldläufer
    3 still grants both feats normally."""
    user_id = _create_user(client)
    race_id = _elf_race_id(client, db_session)
    ausweichen_id = _feat_id(client, db_session, "Ausweichen")
    kampfreflexe_id = _feat_id(client, db_session, "Kampfreflexe")

    payload = _character_payload(
        user_id,
        race_id,
        db_session,
        classes=[{"class_name": "Waldläufer", "level": 3}],
        feats=[{"feat_id": ausweichen_id}, {"feat_id": kampfreflexe_id}],
    )
    response = client.post("/api/characters", json=payload)
    assert response.status_code == 201
    assert response.json()["secondary_base_class_id"] is None


def test_secondary_class_name_cannot_be_one_of_the_characters_own_classes(
    client: TestClient, db_session: Session
) -> None:
    user_id = _create_user(client)
    race_id = _elf_race_id(client, db_session)

    payload = _character_payload(
        user_id,
        race_id,
        db_session,
        classes=[{"class_name": "Waldläufer", "level": 1}],
        secondary_class_name="Waldläufer",
    )
    response = client.post("/api/characters", json=payload)
    assert response.status_code == 422
    assert "own primary" in response.json()["detail"]


def test_unknown_secondary_class_name_is_rejected(client: TestClient, db_session: Session) -> None:
    user_id = _create_user(client)
    race_id = _elf_race_id(client, db_session)

    payload = _character_payload(
        user_id,
        race_id,
        db_session,
        classes=[{"class_name": "Waldläufer", "level": 1}],
        secondary_class_name="Nichtklasse",
    )
    response = client.post("/api/characters", json=payload)
    assert response.status_code == 422


def test_secondary_class_grant_resolves_through_the_real_handler_end_to_end(
    client: TestClient, db_session: Session
) -> None:
    """The whole point of feeding a synthetic `level_counts_by_root_id` entry
    (`rules/secondary_class.py`): Entfesselter Barbar's *real*, unmodified
    Kampfrausch handler (`rules/classes/barbarian.py`) computes correctly for
    a character who has never taken a single real level in that class."""
    user_id = _create_user(client)
    race_id = _elf_race_id(client, db_session)

    payload = _character_payload(
        user_id,
        race_id,
        db_session,
        classes=[{"class_name": "Waldläufer", "level": 3}],
        secondary_class_name="Entfesselter Barbar",
        ability_scores={"ST": 10, "GE": 12, "KO": 13, "IN": 10, "WE": 10, "CH": 8},
    )
    response = client.post("/api/characters", json=payload)
    assert response.status_code == 201
    character_id = response.json()["id"]

    entfesselter_barbar = db_session.query(BaseClass).filter_by(name="Entfesselter Barbar").one()
    assert entfesselter_barbar.id == BARBAR_ENTFESSELTER_ROOT_CLASS_ID

    db_session.add(
        BaseSecondaryClassAbilityGrant(
            secondary_base_class_id=entfesselter_barbar.id,
            character_level=3,
            ability_id=KAMPFRAUSCH_ENTFESSELTER_BARBAR_ABILITY_ID,
        )
    )
    db_session.commit()

    sheet = client.get(f"/api/characters/{character_id}").json()

    kampfrausch_feature = next(f for f in sheet["classFeatures"] if f["key"] == str(KAMPFRAUSCH_ENTFESSELTER_BARBAR_ABILITY_ID))
    assert kampfrausch_feature["isSecondary"] is True

    kampfrausch_activatable = next(
        a for a in sheet["activatableClassAbilities"] if a["key"] == str(KAMPFRAUSCH_ENTFESSELTER_BARBAR_ABILITY_ID)
    )
    # con_mod(0, KO 13 - Elf's own -2 racial mod = 11) + 2 +
    # 2*effective_level(3) = 8 - the real handler's own formula, fed the
    # character's total level via the synthetic level_counts_by_root_id
    # entry rather than a real per-class level. Kampfrausch is
    # `is_persistent_effect`, so its daily-limit numbers are rendered into
    # `description` text (`_build_activatable_class_abilities`), not a raw
    # `usesPerDay` field (that shape is only for non-persistent, once-a-day
    # abilities).
    assert kampfrausch_activatable["description"] == "8 von 8 Runden heute übrig"


def test_cannot_take_a_real_level_in_ones_own_secondary_class(client: TestClient, db_session: Session) -> None:
    user_id = _create_user(client)
    race_id = _elf_race_id(client, db_session)

    payload = _character_payload(
        user_id,
        race_id,
        db_session,
        classes=[{"class_name": "Waldläufer", "level": 1}],
        secondary_class_name="Entfesselter Barbar",
    )
    response = client.post("/api/characters", json=payload)
    assert response.status_code == 201
    character_id = response.json()["id"]

    response = client.post(
        f"/api/characters/{character_id}/level-up",
        json={"target": {"mode": "new", "class_name": "Entfesselter Barbar"}, "hit_points": 6},
    )
    assert response.status_code == 422
    assert "Sekundärklasse" in response.json()["detail"]
