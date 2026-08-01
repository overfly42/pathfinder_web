"""GET /api/characters/{id} for a real (non-fixture) character should return
the frontend's full `Character` sheet shape (`build_character_sheet`,
app/sheet.py) instead of the thin `CharacterRead` composition shape — see
roadmap.md/todos.md's "Charakterbogen... noch nicht verdrahtet" gap this
closes."""

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import Character

from test_characters import (
    DEFAULT_ABILITY_SCORES,
    _character_payload,
    _create_user,
    _elf_race_id,
    _feat_id,
    _item_id,
    _skill_id,
    _trait_id,
)


def test_character_sheet_has_full_shape(client: TestClient, db_session: Session) -> None:
    user_id = _create_user(client)
    race_id = _elf_race_id(client, db_session)

    heimlichkeit_id = _skill_id(client, db_session, "Heimlichkeit")
    ausweichen_id = _feat_id(client, db_session, "Ausweichen")
    reaktionsschnell_id = _trait_id(client, db_session, "Reaktionsschnell")
    dolch_id = _item_id(client, db_session, "Dolch")

    create_response = client.post(
        "/api/characters",
        json=_character_payload(
            user_id,
            race_id,
            db_session,
            skill_ranks={heimlichkeit_id: 1},
            feat_ids=[ausweichen_id],
            trait_ids=[reaktionsschnell_id],
            gear=[{"item_id": dolch_id, "quantity": 1}],
        ),
    )
    assert create_response.status_code == 201
    character_id = create_response.json()["id"]

    response = client.get(f"/api/characters/{character_id}")
    assert response.status_code == 200
    body = response.json()

    # Identity/display fields the thin CharacterRead never had.
    assert body["race"] == "Elf"
    assert body["className"] == "Waldläufer"
    assert body["archetype"] == "Keiner"
    assert body["speed"] == "9 m"

    # Elf: +2 GE, +2 IN, -2 KO applied on top of the base scores.
    abilities_by_key = {a["key"]: a for a in body["abilities"]}
    assert abilities_by_key["GE"]["score"] == DEFAULT_ABILITY_SCORES["GE"] + 2
    assert abilities_by_key["GE"]["mod"] == "+2"
    assert abilities_by_key["KO"]["score"] == DEFAULT_ABILITY_SCORES["KO"] - 2

    dex_mod = int(abilities_by_key["GE"]["mod"])
    assert body["armorClass"] == 10 + dex_mod
    assert body["initiative"] == abilities_by_key["GE"]["mod"]

    assert body["hp"]["current"] == body["hp"]["max"]

    skill = next(s for s in body["skills"] if s["key"] == heimlichkeit_id)
    assert skill["label"] == "Heimlichkeit"

    assert {f["key"] for f in body["feats"]} == {ausweichen_id}
    assert {t["key"] for t in body["traits"]} == {reaktionsschnell_id}
    assert any(r["name"] for r in body["raceAbilities"])

    gear = body["gear"]
    assert len(gear) == 1
    assert gear[0]["name"] == "Dolch"
    assert gear[0]["qty"] == 1

    # Subsystems that genuinely don't exist yet stay honest empty defaults,
    # not fabricated content — this is what used to trip the frontend's
    # "not available yet" placeholder (`!('effectsActive' in character)`).
    # equipmentSlots (roadmap slice 4) is real for armor/shield now — see
    # test_items.py — but this character equipped nothing, and the other 12
    # wondrous-item slots have no real catalog content yet, so every slot's
    # options/selected stay empty here.
    assert len(body["equipmentSlots"]) == 15
    assert all(slot["options"] == [] and slot["selected"] == "" for slot in body["equipmentSlots"])
    assert body["actions"] == []
    assert body["effectsActive"] == []


def test_character_sheet_for_character_without_extras_has_empty_lists(
    client: TestClient, db_session: Session
) -> None:
    user_id = _create_user(client)
    race_id = _elf_race_id(client, db_session)

    # Barbar has no `BaseClassAbilityGrant` data yet (unlike Kämpfer/
    # Waldläufer/Magier) — the default Waldläufer payload now has real
    # level-1 class features (Erzfeind, Spuren lesen, ...) and Magier now has
    # its own (Arkane Schule, Arkane Verbindung, ...), so neither can stand
    # in for "no class features" anymore.
    create_response = client.post(
        "/api/characters",
        json=_character_payload(
            user_id, race_id, db_session, classes=[{"class_name": "Barbar", "level": 1}]
        ),
    )
    assert create_response.status_code == 201
    character_id = create_response.json()["id"]

    response = client.get(f"/api/characters/{character_id}")
    assert response.status_code == 200
    body = response.json()

    assert body["skills"] == []
    assert body["feats"] == []
    assert body["traits"] == []
    assert body["classFeatures"] == []
    assert body["spellsKnown"] == []
    assert body["spellbook"] == []
    assert body["gear"] == []


def test_character_sheet_for_legacy_character_without_hit_points_does_not_crash(
    client: TestClient, db_session: Session
) -> None:
    """Characters created before hit-die data existed may have a `None`
    `current_hit_points`/`CharacterLevel.hit_points` (see
    `Character.current_hit_points`'s docstring) — the sheet must still
    render (HP falls back to 0) rather than 500."""
    user_id = _create_user(client)
    race_id = _elf_race_id(client, db_session)

    create_response = client.post("/api/characters", json=_character_payload(user_id, race_id, db_session))
    assert create_response.status_code == 201
    character_id = create_response.json()["id"]

    character = db_session.get(Character, character_id)
    character.current_hit_points = None
    for level in character.levels:
        level.hit_points = None
    db_session.commit()

    response = client.get(f"/api/characters/{character_id}")
    assert response.status_code == 200
    assert response.json()["hp"] == {"current": 0, "max": 0}


def test_class_features_for_waldlaeufer_match_source(client: TestClient, db_session: Session) -> None:
    """http://prd.5footstep.de/Grundregelwerk/Klassen/Waldlaeufer - a level-20
    Waldläufer should have unlocked every class feature in the "Tabelle:
    Waldläufer" progression, including the recurring ones (Erzfeind,
    Kampfstiltalent, Bevorzugtes Gelände) at their final grant."""
    user_id = _create_user(client)
    race_id = _elf_race_id(client, db_session)

    response = client.post(
        "/api/characters",
        json=_character_payload(
            user_id, race_id, db_session, classes=[{"class_name": "Waldläufer", "level": 20}]
        ),
    )
    assert response.status_code == 201
    character_id = response.json()["id"]

    body = client.get(f"/api/characters/{character_id}").json()
    feature_names = {f["name"] for f in body["classFeatures"]}

    assert feature_names == {
        "Umgang mit Waffen und Rüstungen (Waldläufer)",
        "Erzfeind",
        "Spuren lesen",
        "Tierempathie",
        "Kampfstiltalent",
        "Ausdauer",
        "Bevorzugtes Gelände",
        "Bund des Jägers",
        "Unterholz durchqueren",
        "Schneller Verfolger",
        "Entrinnen",
        "Beute",
        "Tarnung",
        "Verbessertes Entrinnen",
        "Meisterliches Verstecken",
        "Verbesserte Beute",
        "Meisterjäger",
    }


def test_class_features_apply_archetype_replacements(client: TestClient, db_session: Session) -> None:
    """Zwei-Waffen-Kämpfer replaces Rüstungstraining 1/2 (levels 3/7) with
    Defensiver Wirbel, Waffentraining 1/2 (levels 5/9) with Zwillingsklingen/
    Doppelangriff, and Rüstungstraining 3 (level 11) with Verbesserte Balance
    — by level 11 every unlocked Rüstungstraining/Waffentraining grant has
    been superseded, so neither base ability should show up anymore, while
    unaffected base features (Bonus-Kampftalent, Tapferkeit, ...) still do."""
    user_id = _create_user(client)
    race_id = _elf_race_id(client, db_session)

    response = client.post(
        "/api/characters",
        json=_character_payload(
            user_id,
            race_id,
            db_session,
            classes=[{"class_name": "Kämpfer", "level": 11, "archetypes": ["Zwei-Waffen-Kämpfer"]}],
        ),
    )
    assert response.status_code == 201
    character_id = response.json()["id"]

    body = client.get(f"/api/characters/{character_id}").json()
    feature_names = {f["name"] for f in body["classFeatures"]}

    assert {"Defensiver Wirbel", "Zwillingsklingen", "Doppelangriff", "Verbesserte Balance"} <= feature_names
    assert "Rüstungstraining" not in feature_names
    assert "Waffentraining" not in feature_names
    assert {"Umgang mit Waffen und Rüstungen", "Tapferkeit", "Bonus-Kampftalent"} <= feature_names


def test_class_features_include_picked_trick_via_option_group(client: TestClient, db_session: Session) -> None:
    """Schurke's Trick is modeled as just another `BaseClassOptionGroup`
    (roadmap.md's "pick from a restricted list" plan, §2) rather than a
    dedicated pool mechanism — the design bet was that this needs zero
    changes to `_build_class_features`, since a picked trick is only a
    `CharacterClassOption` row plus an `option_choice_id`-gated grant, same
    as a Kleriker domain. This is the test that actually proves that bet:
    picking "Aufspringen" at 2nd level should surface it in classFeatures
    exactly like a domain power does, with no sheet.py changes involved."""
    user_id = _create_user(client)
    race_id = _elf_race_id(client, db_session)

    response = client.post(
        "/api/characters",
        json=_character_payload(
            user_id,
            race_id,
            db_session,
            classes=[{"class_name": "Schurke", "level": 2, "options": {"trick": ["Aufspringen"]}}],
        ),
    )
    assert response.status_code == 201
    character_id = response.json()["id"]

    body = client.get(f"/api/characters/{character_id}").json()
    feature_names = {f["name"] for f in body["classFeatures"]}

    assert "Aufspringen" in feature_names
    # A trick never picked shouldn't appear just because it exists in the pool.
    assert "Blutende Wunde" not in feature_names
    # Fixed, ungated 1st/2nd-level features are unaffected.
    assert {"Fallen finden", "Hinterhältiger Angriff", "Entrinnen"} <= feature_names


def test_fixture_character_sheet_is_unaffected(client: TestClient, db_session: Session) -> None:
    """The two hardcoded mock fixtures (character_1/2) must keep working
    exactly as before — this endpoint's fixture branch is untouched."""
    response = client.get("/api/characters/1")
    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "Elyra Silberauge"
