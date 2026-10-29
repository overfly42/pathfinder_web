"""The five Jäger archetypes (`scripts/import_jaeger_archetypes.py`,
`rules/classes/jaeger.py`), plus the archetype-aware bonus feat slots and
alignment they needed (`rules/feat_slots.py`, `rules/alignment.py`)."""

from collections import Counter
from types import SimpleNamespace
from uuid import UUID

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.rules.classes.jaeger import GOETTLICHER_JAEGER_KLASSENFERTIGKEITEN_ID, WISSEN_RELIGION_SKILL_ID
from app.rules.context import CharacterContext
from app.rules.feat_slots import class_bonus_feat_slot_count
from app.rules.handlers import granted_class_skill_ids

from test_characters import _character_payload, _create_user, _human_race_id

WILDER_STIER = "16b68d67-1f10-5f8c-948c-3aa9428b6231"
KAEFER = "39a039a0-1219-5e7f-b72f-500011a84a04"
UNGEZIEFERASPEKT = "ab2648ba-67a1-5317-bae7-b170589818bc"


def _create(client: TestClient, db_session: Session, archetype: str | None, level: int, **overrides):
    selection = {"class_name": "Jäger", "level": level, "options": overrides.pop("options", {})}
    if archetype:
        selection["archetypes"] = [archetype]
    payload = _character_payload(
        _create_user(client), _human_race_id(client, db_session), db_session, classes=[selection], flex_ability="CH"
    )
    payload.update(overrides)
    return client.post("/api/characters", json=payload)


def _sheet(client: TestClient, db_session: Session, archetype: str | None, level: int, **overrides) -> dict:
    response = _create(client, db_session, archetype, level, **overrides)
    assert response.status_code == 201, response.text
    return client.get(f"/api/characters/{response.json()['id']}").json()


def _features(sheet: dict) -> dict[str, dict]:
    return {f["name"]: f for f in sheet["classFeatures"]}


def _activate(client: TestClient, sheet: dict, ability_id: str, *options: str) -> dict:
    response = client.post(
        f"/api/characters/{sheet['id']}/effects",
        json={"source_type": "class_ability", "source_id": ability_id, "option_ids": list(options)},
    )
    assert response.status_code == 201, response.text
    return client.get(f"/api/characters/{sheet['id']}").json()


def _companion_tracks(sheet: dict) -> list[dict]:
    return [t for t in sheet["companionLevels"] if t["track"] == "animal_companion"]


def _slots(db_session: Session, class_name: str, level: int, archetype: str | None = None) -> int:
    selection = SimpleNamespace(class_name=class_name, level=level, archetypes=[archetype] if archetype else [])
    return class_bonus_feat_slot_count(db_session, [selection])


def test_archetype_feat_slot_deltas(client: TestClient, db_session: Session) -> None:
    _character_payload(_create_user(client), _human_race_id(client, db_session), db_session)
    jaeger = next(c for c in client.get("/api/classes").json() if c["name"] == "Jäger")

    assert jaeger["archetypeBonusFeatLevels"] == {"Göttlicher Jäger": [2], "Wilder Jäger": [2, 3]}
    assert _slots(db_session, "Jäger", 9) == 4
    assert _slots(db_session, "Jäger", 9, "Wilder Jäger") == 2
    assert _slots(db_session, "Jäger", 9, "Göttlicher Jäger") == 1
    # An archetype's own slots count too (they didn't before): the
    # Bärenschamane's Bonustalent at 9th.
    assert _slots(db_session, "Druide", 9, "Bärenschamane") == 1
    druide = next(c for c in client.get("/api/classes").json() if c["name"] == "Druide")
    assert druide["archetypeBonusFeatLevels"]["Bärenschamane"] == [9, 13, 17]


def test_bruder_des_urzeitgefaehrten(client: TestClient, db_session: Session) -> None:
    sheet = _sheet(client, db_session, "Bruder des Urzeitgefährten", 8)
    features = _features(sheet)

    assert {"Urzeitliche Verwandlung", "Urzeitlicher Kraftschub"} <= set(features)
    assert not {"Tieraspekt", "Tieraspekt (Tiergefährte)", "Zweiter Tieraspekt"} & set(features)
    assert features["Urzeitliche Verwandlung"]["summary"] == "8 Minuten/Tag; 4 Evolutionspunkte"
    assert len(_companion_tracks(sheet)) == 1


def test_bruder_des_ungeziefergefaehrten(client: TestClient, db_session: Session) -> None:
    sheet = _sheet(client, db_session, "Bruder des Ungeziefergefährten", 5)
    features = _features(sheet)

    assert {"Ungeziefergefährte", "Ungezieferempathie", "Ungezieferaspekt", "Schwärme durchqueren"} <= set(features)
    assert not {
        "Tiergefährte (Jäger)", "Tierempathie", "Tieraspekt", "Tieraspekt (Tiergefährte)", "Unterholz durchqueren"
    } & set(features)
    # No vermin species in the catalog yet: no companion slot.
    assert _companion_tracks(sheet) == []
    assert features["Ungezieferempathie"]["summary"] == "1W20 + 5 (nur Ungeziefer)"

    entry = next(a for a in sheet["activatableClassAbilities"] if a["key"] == UNGEZIEFERASPEKT)
    assert (len(entry["options"]), entry["optionLimit"]) == (15, 1)
    natural = [e for e in _activate(client, sheet, UNGEZIEFERASPEKT, KAEFER)["armorClassBreakdown"] if "Käfer" in e["label"]]
    assert [e["value"] for e in natural] == [2]


def test_goettlicher_jaeger_alignment_skill_and_domain(client: TestClient, db_session: Session) -> None:
    assert _create(client, db_session, None, 3, alignment="LG").status_code == 422
    sheet = _sheet(
        client, db_session, "Göttlicher Jäger", 3, alignment="LG", options={"divine_hunter_domain": ["Domäne des Krieges"]}
    )
    features = _features(sheet)

    assert {"Domäne (Göttlicher Jäger)", "Außerweltlicher Gefährte", "Verliehene Fähigkeiten (Domäne des Krieges)"} <= set(features)
    assert not {"Gemeinschaftstalente", "Jägertaktiken"} & set(features)
    assert features["Klassenfertigkeiten (Göttlicher Jäger)"]["partialNote"] == "Wissen (Gewölbekunde) bleibt Klassenfertigkeit"
    context = CharacterContext(granted_ability_ids=Counter({GOETTLICHER_JAEGER_KLASSENFERTIGKEITEN_ID: 1}))
    assert WISSEN_RELIGION_SKILL_ID in granted_class_skill_ids(context)


def test_domain_needs_the_archetype_and_3rd_level(client: TestClient, db_session: Session) -> None:
    options = {"divine_hunter_domain": ["Domäne des Krieges"]}
    assert _create(client, db_session, None, 3, options=options).status_code == 422
    assert _create(client, db_session, "Göttlicher Jäger", 2, options=options).status_code == 422


def test_domain_powers_come_two_levels_later(client: TestClient, db_session: Session) -> None:
    options = {"divine_hunter_domain": ["Domäne der Tiere"]}
    at_5 = _features(_sheet(client, db_session, "Göttlicher Jäger", 5, options=options))
    assert "Tiergefährte (Göttlicher Jäger, Domäne der Tiere)" not in at_5
    at_6 = _features(_sheet(client, db_session, "Göttlicher Jäger", 6, options=options))
    # Kleriker 4 = Jäger 6: the substitute, not a second companion.
    assert "Tiergefährte (Göttlicher Jäger, Domäne der Tiere)" in at_6
    assert "Tiergefährte" not in at_6


def test_rudelfuehrer_keeps_one_companion_at_full_level(client: TestClient, db_session: Session) -> None:
    sheet = _sheet(client, db_session, "Rudelführer", 4)
    features = _features(sheet)

    assert {"Rudelbindung", "Rudelaspekt", "Tieraspekt", "Tieraspekt (Tiergefährte)"} <= set(features)
    assert "Tiergefährte (Jäger)" not in features
    (track,) = _companion_tracks(sheet)
    assert track["level"] == 4


def test_wilder_jaeger(client: TestClient, db_session: Session) -> None:
    sheet = _sheet(client, db_session, "Wilder Jäger", 8)
    features = _features(sheet)

    assert {
        "Tiergefährtenlos", "Wilder Aspekt", "Wilder Aspekt: Stier", "Tiergestalt (Wilder Jäger)", "Rudel herbeizaubern",
    } <= set(features)
    assert not {
        "Tiergefährte (Jäger)", "Tieraspekt", "Tieraspekt (Tiergefährte)", "Jägertaktiken", "Bonustricks",
        "Verbesserte Empathische Verbindung",
    } & set(features)
    assert _companion_tracks(sheet) == []
    assert features["Tiergestalt (Wilder Jäger)"]["summary"] == "3/Tag, Dauer 8 Std.; wie Bestiengestalt III (nur Tiere)"

    base = next(a for a in sheet["abilities"] if a["key"] == "ST")["score"]
    active = _activate(client, sheet, WILDER_STIER)
    assert next(a for a in active["abilities"] if a["key"] == "ST")["score"] == base + 4
    # No pool behind the Wilder Aspekt.
    assert not any(a.get("name") == "Tieraspekt" for a in active["actions"])


def test_archetype_ids_are_registered(client: TestClient, db_session: Session) -> None:
    _character_payload(_create_user(client), _human_race_id(client, db_session), db_session)
    jaeger = next(c for c in client.get("/api/classes").json() if c["name"] == "Jäger")
    assert jaeger["archetypeAllowedAlignments"] == {
        "Göttlicher Jäger": ["LG", "NG", "CG", "LN", "N", "CN", "LE", "NE", "CE"]
    }
    assert UUID(jaeger["id"])


def test_domain_is_picked_at_the_level_up_to_3rd(client: TestClient, db_session: Session) -> None:
    sheet = _sheet(client, db_session, "Göttlicher Jäger", 2, alignment="LG")
    jaeger_id = next(c["id"] for c in client.get("/api/classes").json() if c["name"] == "Jäger")

    response = client.post(
        f"/api/characters/{sheet['id']}/level-up",
        json={
            "target": {"mode": "existing", "base_class_id": jaeger_id},
            "hit_points": 5,
            "favored_class_bonus": "hp",
            "existing_level_options": {"divine_hunter_domain": ["Domäne des Krieges"]},
        },
    )
    assert response.status_code == 201, response.text
    sheet = client.get(f"/api/characters/{sheet['id']}").json()
    assert "Verliehene Fähigkeiten (Domäne des Krieges)" in _features(sheet)
