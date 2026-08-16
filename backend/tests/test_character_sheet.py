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
    _feat_selection,
    _item_id,
    _race_id,
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
            feats=[_feat_selection(ausweichen_id)],
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

    assert {f["name"] for f in body["feats"]} == {"Ausweichen"}
    assert {t["key"] for t in body["traits"]} == {reaktionsschnell_id}
    assert any(r["name"] for r in body["raceAbilities"])

    gear = body["gear"]
    assert len(gear) == 1
    assert gear[0]["name"] == "Dolch"
    assert gear[0]["qty"] == 1

    # Subsystems that genuinely don't exist yet stay honest empty defaults,
    # not fabricated content — this is what used to trip the frontend's
    # "not available yet" placeholder (`!('effectsActive' in character)`).
    # equipmentSlots (roadmap slice 4) is real for armor/shield/weapons now —
    # see test_items.py/test_weapon_slots.py — this character equipped
    # nothing, so every slot's `selected` stays empty; owning the Dolch
    # (unequipped) does make it a candidate *option* for both weapon slots
    # (same as an owned-but-unequipped armor/shield item would be) — the
    # other 12 wondrous-item slots still have no real catalog content, so
    # their options stay empty too.
    assert len(body["equipmentSlots"]) == 17
    assert all(slot["selected"] == "" for slot in body["equipmentSlots"])
    slots_by_key = {slot["key"]: slot for slot in body["equipmentSlots"]}
    assert {option["label"] for option in slots_by_key["hauptwaffe"]["options"]} == {"Dolch"}
    assert {option["label"] for option in slots_by_key["nebenwaffe"]["options"]} == {"Dolch"}
    assert all(
        slot["options"] == [] for key, slot in slots_by_key.items() if key not in ("hauptwaffe", "nebenwaffe")
    )
    assert body["actions"] == []
    assert body["effectsActive"] == []


def test_akrobatik_note_shows_the_full_ready_to_roll_jump_total(client: TestClient, db_session: Session) -> None:
    """The info-note on Akrobatik's skill row should surface a single usable
    jump-check number (this character's Akrobatik total + the Springen
    Volksbonus/-malus), not just the isolated racial component — see
    rules/speed.py's jump_skill_bonus and sheet.py's _build_skills."""
    user_id = _create_user(client)
    akrobatik_id = _skill_id(client, db_session, "Akrobatik")

    # Elf: normal 9 m speed -> Volksbonus/-malus is +0. Default GE 12 +2
    # (Elf) -> mod +2, no ranks, not a Waldläufer class skill -> Akrobatik
    # total is just the +2 ability mod.
    elf_id = _elf_race_id(client, db_session)
    elf_character = client.post(
        "/api/characters", json=_character_payload(user_id, elf_id, db_session)
    ).json()
    elf_akrobatik = next(s for s in client.get(f"/api/characters/{elf_character['id']}").json()["skills"] if s["key"] == akrobatik_id)
    assert elf_akrobatik["value"] == "+2"
    assert "gesamt" in elf_akrobatik["note"]
    assert elf_akrobatik["note"].startswith("Sprung (Hoch-/Weitsprung): +2 gesamt (Akrobatik +2 + Volksbonus/-malus +0")

    # Halbling: slower speed -> a negative Volksbonus/-malus, so the jump
    # total should be lower than the plain Akrobatik value shown on the row.
    halbling_id = _race_id(client, db_session, "Halbling")
    halbling_character = client.post(
        "/api/characters", json=_character_payload(user_id, halbling_id, db_session)
    ).json()
    halbling_akrobatik = next(
        s for s in client.get(f"/api/characters/{halbling_character['id']}").json()["skills"] if s["key"] == akrobatik_id
    )
    assert "Volksbonus/-malus -" in halbling_akrobatik["note"]


def test_character_sheet_for_character_without_extras_has_empty_lists(
    client: TestClient, db_session: Session
) -> None:
    user_id = _create_user(client)
    race_id = _elf_race_id(client, db_session)

    # Druide has no `BaseClassAbilityGrant` data yet (unlike Kämpfer/
    # Waldläufer/Magier/Barbar) — the default Waldläufer payload now has real
    # level-1 class features (Erzfeind, Spuren lesen, ...), Magier now has
    # its own (Arkane Schule, Arkane Verbindung, ...), and Barbar now has its
    # own too (Kampfrausch, Schnelle Bewegung, ...), so none of those three
    # can stand in for "no class features" anymore.
    create_response = client.post(
        "/api/characters",
        json=_character_payload(
            user_id, race_id, db_session, classes=[{"class_name": "Druide", "level": 1}]
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
    `damage_taken`/`CharacterLevel.hit_points` (see `Character.damage_taken`'s
    docstring) — the sheet must still render (HP falls back to 0) rather
    than 500."""
    user_id = _create_user(client)
    race_id = _elf_race_id(client, db_session)

    create_response = client.post("/api/characters", json=_character_payload(user_id, race_id, db_session))
    assert create_response.status_code == 201
    character_id = create_response.json()["id"]

    character = db_session.get(Character, character_id)
    character.damage_taken = None
    for level in character.levels:
        level.hit_points = None
    db_session.commit()

    response = client.get(f"/api/characters/{character_id}")
    assert response.status_code == 200
    assert response.json()["hp"] == {"current": 0, "max": 0, "temporary": 0}


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


def test_class_features_include_picked_hunter_bond_branch(client: TestClient, db_session: Session) -> None:
    """Same proof as the Trick test above, for Waldläufer's Bund des Jägers
    (a newly split overview + two option-gated branch abilities): picking
    "Bund mit Gefährten" at 4th level should surface both the always-on
    overview ability and that specific branch's text, but not the
    Tiergefährte branch's."""
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
                    "class_name": "Waldläufer",
                    "level": 4,
                    "options": {"hunter_bond": ["Bund mit Gefährten"]},
                }
            ],
        ),
    )
    assert response.status_code == 201
    character_id = response.json()["id"]

    body = client.get(f"/api/characters/{character_id}").json()
    feature_names = {f["name"] for f in body["classFeatures"]}

    assert "Bund des Jägers" in feature_names  # always-on overview
    assert "Bund mit Gefährten" in feature_names
    assert "Tiergefährte (Bund des Jägers)" not in feature_names
    # A fixed, ungated 1st-level feature is unaffected.
    assert "Erzfeind" in feature_names


def test_einschuechternde_kraft_adds_str_mod_to_intimidate(client: TestClient, db_session: Session) -> None:
    """`rules/feats.py`'s first `HANDLERS` entry: Einschüchternde Kraft adds
    the ST modifier on top of Einschüchtern's own CH-based value (GRW S.
    121)."""
    user_id = _create_user(client)
    race_id = _elf_race_id(client, db_session)  # doesn't touch ST

    einschuechtern_id = _skill_id(client, db_session, "Einschüchtern")
    feat_id = _feat_id(client, db_session, "Einschüchternde Kraft")

    create_response = client.post(
        "/api/characters",
        json=_character_payload(
            user_id,
            race_id,
            db_session,
            ability_scores={**DEFAULT_ABILITY_SCORES, "ST": 16},
            feats=[_feat_selection(feat_id)],
        ),
    )
    assert create_response.status_code == 201
    character_id = create_response.json()["id"]

    body = client.get(f"/api/characters/{character_id}").json()
    skills_by_key = {s["key"]: s for s in body["skills"]}
    # CH mod (-1) + class skill bonus (+3, Waldläufer) + ST mod (+3) = +5.
    assert skills_by_key[einschuechtern_id]["value"] == "+5"

    breakdown = skills_by_key[einschuechtern_id]["breakdown"]
    assert {"label": "Attributsbonus (CHA)", "value": -1} in breakdown
    assert {"label": "Klassenfertigkeit", "value": 3} in breakdown
    assert {"label": "Einschüchternde Kraft", "value": 3} in breakdown
    assert sum(entry["value"] for entry in breakdown) == 5


def test_halbork_einschuechternd_adds_racial_bonus_to_intimidate(
    client: TestClient, db_session: Session
) -> None:
    """`rules/race_abilities.py`'s `EINSCHUECHTERND` handler: Halb-Ork's
    Einschüchternd grants a +2 Volksbonus (racial) on Einschüchtern."""
    user_id = _create_user(client)
    race_id = _race_id(client, db_session, "Halb-Ork")

    einschuechtern_id = _skill_id(client, db_session, "Einschüchtern")

    create_response = client.post(
        "/api/characters",
        json=_character_payload(user_id, race_id, db_session, flex_ability="ST"),
    )
    assert create_response.status_code == 201
    character_id = create_response.json()["id"]

    body = client.get(f"/api/characters/{character_id}").json()
    skills_by_key = {s["key"]: s for s in body["skills"]}
    # CH mod (-1) + class skill bonus (+3, Waldläufer) + racial (+2) = +4.
    assert skills_by_key[einschuechtern_id]["value"] == "+4"

    breakdown = skills_by_key[einschuechtern_id]["breakdown"]
    assert {"label": "Einschüchternd", "value": 2} in breakdown
    assert sum(entry["value"] for entry in breakdown) == 4


def test_armor_class_breakdown_sums_to_armor_class(client: TestClient, db_session: Session) -> None:
    """`sheet.py`'s `_ac_breakdown`: base 10 + Dex mod + every equipped
    gear's own AC `Modifier` (`source=item.name`), summing to `armorClass`."""
    user_id = _create_user(client)
    race_id = _elf_race_id(client, db_session)
    lederruestung_id = _item_id(client, db_session, "Lederrüstung")  # +2 AC

    create_response = client.post(
        "/api/characters",
        json=_character_payload(
            user_id, race_id, db_session, gear=[{"item_id": lederruestung_id, "quantity": 1}]
        ),
    )
    assert create_response.status_code == 201
    character_id = create_response.json()["id"]

    client.put(f"/api/characters/{character_id}/slots/ruestung", json={"item_id": lederruestung_id})

    body = client.get(f"/api/characters/{character_id}").json()
    breakdown = body["armorClassBreakdown"]
    assert {"label": "Basis", "value": 10} in breakdown
    assert {"label": "Lederrüstung", "value": 2} in breakdown
    assert sum(entry["value"] for entry in breakdown) == body["armorClass"]


def test_fixture_character_sheet_is_unaffected(client: TestClient, db_session: Session) -> None:
    """The two hardcoded mock fixtures (character_1/2) must keep working
    exactly as before — this endpoint's fixture branch is untouched."""
    response = client.get("/api/characters/1")
    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "Elyra Silberauge"
