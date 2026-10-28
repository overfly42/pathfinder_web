"""Effective master level per companion track — roadmap slice 10, step 1
(`rules/companions.py`, `BaseCompanionLevelSource`, the sheet's
`companionLevels`)."""

from collections import Counter
from types import SimpleNamespace
from uuid import UUID, uuid4

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.rules.companions import master_effective_level
from app.rules.context import CharacterContext

from test_characters import _character_payload, _create_user, _feat_id, _human_race_id

DRUIDE = UUID(int=1)
WALDLAEUFER = UUID(int=2)
CLASS_NAMES = {DRUIDE: "Druide", WALDLAEUFER: "Waldläufer"}


def _source(**fields) -> SimpleNamespace:
    defaults = {
        "id": uuid4(),
        "track": "animal_companion",
        "label": "Quelle",
        "class_ability_id": uuid4(),
        "feat_id": None,
        "kind": "class_level",
        "root_class_id": DRUIDE,
        "offset": 0,
        "divisor": 1,
        "minimum": None,
        "stack_group": None,
    }
    return SimpleNamespace(**{**defaults, **fields})


def _context(sources: list[SimpleNamespace], levels: dict[UUID, int], feat_ids=frozenset()) -> CharacterContext:
    return CharacterContext(
        granted_ability_ids=Counter(s.class_ability_id for s in sources if s.class_ability_id is not None),
        feat_ids=frozenset(feat_ids),
        level_counts_by_root_id=levels,
        character_level=sum(levels.values()),
    )


def test_sources_of_one_track_add_up_and_explain_themselves() -> None:
    druide = _source(label="Druide")
    waldlaeufer = _source(label="Waldläufer", root_class_id=WALDLAEUFER, offset=-3)
    context = _context([druide, waldlaeufer], {DRUIDE: 4, WALDLAEUFER: 6})

    result = master_effective_level("animal_companion", [druide, waldlaeufer], context, CLASS_NAMES)

    assert result.level == 7
    assert [(c.label, c.value, c.detail) for c in result.contributions] == [
        ("Druide", 4, "Druide 4"),
        ("Waldläufer", 3, "Waldläufer 6 − 3"),
    ]


def test_level_is_capped_at_character_level_after_flat_bonuses() -> None:
    druide = _source(label="Druide")
    stallmeister = _source(label="Stallmeister", class_ability_id=None, feat_id=uuid4(), kind="flat_bonus", offset=1)
    context = _context([druide], {DRUIDE: 3}, feat_ids={stallmeister.feat_id})

    result = master_effective_level("animal_companion", [druide, stallmeister], context, CLASS_NAMES)

    assert result.uncapped == 4
    assert result.level == 3


def test_flat_bonus_alone_gives_no_companion() -> None:
    stallmeister = _source(class_ability_id=None, feat_id=uuid4(), kind="flat_bonus", offset=1)
    untriggered = _source()
    context = CharacterContext(feat_ids=frozenset({stallmeister.feat_id}), character_level=5)

    assert master_effective_level("animal_companion", [stallmeister, untriggered], context, CLASS_NAMES) is None


def test_negative_contribution_floors_at_zero_and_minimum_applies() -> None:
    plain = _source(root_class_id=WALDLAEUFER, offset=-3)
    with_minimum = _source(offset=-3, minimum=1)
    context = _context([plain, with_minimum], {WALDLAEUFER: 1, DRUIDE: 2})

    result = master_effective_level("animal_companion", [plain, with_minimum], context, CLASS_NAMES)

    assert [c.value for c in result.contributions] == [0, 1]
    assert result.contributions[1].detail == "Druide 2 − 3, mind. 1"


def test_stack_group_counts_only_the_highest() -> None:
    first = _source(stack_group="g")
    second = _source(root_class_id=WALDLAEUFER, stack_group="g")
    context = _context([first, second], {DRUIDE: 2, WALDLAEUFER: 5})

    result = master_effective_level("animal_companion", [first, second], context, CLASS_NAMES)

    assert result.level == 5
    assert len(result.contributions) == 1


def test_other_tracks_are_ignored() -> None:
    familiar = _source(track="familiar")
    context = _context([familiar], {DRUIDE: 3})

    assert master_effective_level("animal_companion", [familiar], context, CLASS_NAMES) is None
    assert master_effective_level("familiar", [familiar], context, CLASS_NAMES).level == 3


# ---- against the seeded sources, through the sheet ----


def _sheet(client: TestClient, db_session: Session, classes: list[dict], **overrides) -> dict:
    payload = _character_payload(_create_user(client), _human_race_id(client, db_session), db_session, classes=classes)
    payload.update({"flex_ability": "CH", **overrides})
    response = client.post("/api/characters", json=payload)
    assert response.status_code == 201, response.text
    return client.get(f"/api/characters/{response.json()['id']}").json()


def _track(sheet: dict, track: str) -> dict | None:
    return next((t for t in sheet["companionLevels"] if t["track"] == track), None)


def test_druide_and_waldlaeufer_companion_levels_stack(client: TestClient, db_session: Session) -> None:
    sheet = _sheet(
        client,
        db_session,
        [
            {"class_name": "Druide", "level": 4, "options": {"bond": ["Tiergefährte"]}},
            {"class_name": "Waldläufer", "level": 6, "options": {"hunter_bond": ["Tiergefährte"]}},
        ],
    )

    track = _track(sheet, "animal_companion")
    assert track["level"] == 7
    assert sorted((b["label"], b["value"], b["detail"]) for b in track["breakdown"]) == [
        ("Druide", 4, "Druide 4"),
        ("Waldläufer", 3, "Waldläufer 6 − 3"),
    ]
    assert _track(sheet, "familiar") is None


def test_druide_with_domain_bond_has_no_companion_until_the_tiere_domain(
    client: TestClient, db_session: Session
) -> None:
    def druide(level: int, domain: str) -> dict:
        return _sheet(
            client,
            db_session,
            [{"class_name": "Druide", "level": level, "options": {"bond": ["Domäne (Natur)"], "nature_domain": [domain]}}],
        )

    assert druide(6, "Domäne der Erde")["companionLevels"] == []
    track = _track(druide(6, "Domäne der Tiere"), "animal_companion")
    # Druide level − 3, not Kleriker level − 3 (the domain's own text).
    assert track["level"] == 3
    assert track["breakdown"][0]["detail"] == "Druide 6 − 3"


def test_kleriker_tiere_domain_counts_kleriker_level(client: TestClient, db_session: Session) -> None:
    sheet = _sheet(
        client,
        db_session,
        [{"class_name": "Kleriker", "level": 5, "options": {"domain": ["Domäne der Tiere", "Domäne der Erde"]}}],
    )

    track = _track(sheet, "animal_companion")
    assert track["level"] == 2
    assert track["breakdown"][0]["detail"] == "Kleriker 5 − 3"


def test_magier_familiar_only_with_the_familiar_bond(client: TestClient, db_session: Session) -> None:
    familiar = _sheet(client, db_session, [{"class_name": "Magier", "level": 3, "options": {"arcane_bond": ["Vertrauter"]}}])
    focus = _sheet(client, db_session, [{"class_name": "Magier", "level": 3, "options": {"arcane_bond": ["Fokus"]}}])

    assert _track(familiar, "familiar")["level"] == 3
    assert "Vertrauter (Magier)" in {f["name"] for f in familiar["classFeatures"]}
    assert focus["companionLevels"] == []


def test_paladin_mount_counts_from_level_5(client: TestClient, db_session: Session) -> None:
    sheet = _sheet(
        client, db_session, [{"class_name": "Paladin", "level": 7, "options": {"divine_bond": ["Reittier"]}}], alignment="LG"
    )

    assert _track(sheet, "animal_companion")["level"] == 7


def test_stallmeister_adds_one_but_never_past_character_level(client: TestClient, db_session: Session) -> None:
    stallmeister_id = _feat_id(client, db_session, "Stallmeister")
    sheet = _sheet(
        client,
        db_session,
        [
            {"class_name": "Waldläufer", "level": 4, "options": {"hunter_bond": ["Tiergefährte"]}},
        ],
        feats=[{"feat_id": stallmeister_id}],
    )

    track = _track(sheet, "animal_companion")
    assert track["level"] == 2  # Waldläufer 4 − 3 + Stallmeister 1
    assert {b["label"] for b in track["breakdown"]} == {"Waldläufer", "Stallmeister"}


def test_hexenmeister_sekundaerklasse_feeds_the_companion_level(client: TestClient, db_session: Session) -> None:
    """Merro-Mercat-style: Sylvanische Blutlinie through the Sekundärklasse
    rule — its tier ability and synthetic Hexenmeister level reach the
    normal source, no Sekundärklasse-specific source needed."""
    sheet = _sheet(
        client,
        db_session,
        [{"class_name": "Kämpfer", "level": 3}],
        secondary_class_name="Hexenmeister",
        secondary_class_options={"bloodline": ["Sylvanische Blutlinie"]},
    )

    track = _track(sheet, "animal_companion")
    assert track is not None
    assert track["breakdown"][0]["label"] == "Hexenmeister (Sylvanische Blutlinie)"
    assert track["level"] == 1  # Hexenmeister 3 − 3, mind. 1


def test_druide_sekundaerklasse_companion_from_7th_level(client: TestClient, db_session: Session) -> None:
    """Druide as Sekundärklasse: Tiergefährte at 7th with character level −4,
    full character level from 11th; Tierempathie keeps the full level."""
    at_6 = _sheet(client, db_session, [{"class_name": "Kämpfer", "level": 6}], secondary_class_name="Druide")
    at_7 = _sheet(client, db_session, [{"class_name": "Kämpfer", "level": 7}], secondary_class_name="Druide")
    at_11 = _sheet(client, db_session, [{"class_name": "Kämpfer", "level": 11}], secondary_class_name="Druide")

    assert _track(at_6, "animal_companion") is None
    assert _track(at_7, "animal_companion")["level"] == 3
    assert len(_track(at_7, "animal_companion")["slots"][0]["species"]) == 19  # 17 + Säbelzahnkatze/Grizzlybär (Hausregel)
    assert _track(at_11, "animal_companion")["level"] == 11
    empathy = next(f for f in at_7["classFeatures"] if f["name"] == "Tierempathie")
    assert "7" in empathy["summary"]


def test_magier_sekundaerklasse_familiar_from_3rd_level(client: TestClient, db_session: Session) -> None:
    sheet = _sheet(
        client,
        db_session,
        [{"class_name": "Kämpfer", "level": 3}],
        secondary_class_name="Magier",
        secondary_class_options={"school": ["Hervorrufung"]},
    )
    track = _track(sheet, "familiar")
    assert track["level"] == 3
    assert len(track["slots"][0]["species"]) == 11
