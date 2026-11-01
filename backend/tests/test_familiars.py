"""Familiars — roadmap slice 10, step 4 (`app/companions.py`'s
`_familiar_state`, `scripts/import_familiars.py`)."""

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from test_companions import _attack, _master, _value


def _magier(client: TestClient, db_session: Session, level: int, **overrides) -> dict:
    return _master(
        client, db_session, [{"class_name": "Magier", "level": level, "options": {"arcane_bond": ["Vertrauter"]}}],
        **overrides,
    )


def _familiar_slot(sheet: dict) -> dict:
    track = next(t for t in sheet["companionLevels"] if t["track"] == "familiar")
    return track["slots"][0]


def _add_familiar(client: TestClient, master: dict, species: str, **extra):
    slot = _familiar_slot(master)
    species_id = next(s["id"] for s in slot["species"] if s["name"] == species)
    return client.post(
        f"/api/characters/{master['id']}/companions",
        json={"track": "familiar", "species_id": species_id, "name": species, **extra},
    )


def _familiar(client: TestClient, master: dict, species: str) -> dict:
    response = _add_familiar(client, master, species)
    assert response.status_code == 201, response.text
    return client.get(f"/api/characters/{response.json()['id']}").json()


def _skill(sheet: dict, label: str) -> dict:
    return next(s for s in sheet["skills"] if s["label"] == label)


def test_magier_has_a_familiar_slot_with_eleven_species(client: TestClient, db_session: Session) -> None:
    slot = _familiar_slot(_magier(client, db_session, 1))

    assert slot["level"] == 1
    assert slot["hitDice"] == 0
    assert {s["name"] for s in slot["species"]} == {
        "Affe", "Echse", "Eule", "Falke", "Fledermaus", "Katze", "Kröte", "Rabe", "Ratte", "Viper", "Wiesel"
    }


def test_familiar_creation_takes_no_hit_points(client: TestClient, db_session: Session) -> None:
    master = _magier(client, db_session, 1)
    assert _add_familiar(client, master, "Katze", hit_points=[3]).status_code == 422
    assert _add_familiar(client, master, "Katze").status_code == 201
    assert _add_familiar(client, master, "Rabe").status_code == 422  # slot taken


def test_cat_familiar_sheet_derives_from_its_master(client: TestClient, db_session: Session) -> None:
    master = _magier(client, db_session, 5)
    cat = _familiar(client, master, "Katze")
    master_sheet = client.get(f"/api/characters/{master['id']}").json()

    assert cat["kind"] == "companion"
    assert cat["companion"]["track"] == "familiar"
    assert cat["companion"]["effectiveLevel"] == 5
    assert cat["level"] == 5
    assert cat["hp"]["max"] == master_sheet["hp"]["max"] // 2
    # GAB of a Magier 5 (+2); saves: better of familiar (Ref/Zäh +2) and master base.
    assert _value(cat["combat"], "bab") == "+2"
    assert _value(cat["saves"], "ref") == "+4"  # 2 + GE 15 (+2)
    assert _value(cat["saves"], "will") == "+5"  # Magier 5: +4, WE 12 (+1)
    # Table row 5-6: natural armor +3, IN 8; Sehr klein: +2 AC.
    natural = next(e for e in cat["armorClassBreakdown"] if e["label"] == "Natürliche Rüstung")
    assert natural["value"] == 3
    assert next(a for a in cat["abilities"] if a["key"] == "IN")["score"] == 8
    assert _value(cat["combat"], "size").startswith("Sehr klein")
    # Waffenfinesse: GAB 2 + GE 2 + size 2.
    assert _attack(cat, "Klauen")["attackBonus"] == "+6/+6"
    assert "Waffenfinesse" in {f["name"] for f in cat["feats"]}
    # Heimlichkeit: Volksmodifikator +4, size +8, GE +2; class skill, no ranks.
    assert _skill(cat, "Heimlichkeit")["value"] == "+14"
    features = {f["name"]: f for f in cat["classFeatures"]}
    assert {"Wachsamkeit", "Empathische Verbindung", "Berührungszauber übermitteln", "Mit Meister sprechen"} <= set(features)
    assert "Zauberresistenz" not in features
    assert "Bonus für den Meister" in {r["name"] for r in cat["raceAbilities"]}


def test_familiar_uses_masters_skill_ranks(client: TestClient, db_session: Session) -> None:
    master = _magier(client, db_session, 1)
    skills = {s["name"]: s["id"] for s in client.get("/api/skills").json()}
    master_with_ranks = _magier(
        client, db_session, 1, skill_ranks=[{"skill_id": skills["Wahrnehmung"], "ranks": 1}]
    )
    plain = _familiar(client, master, "Ratte")
    trained = _familiar(client, master_with_ranks, "Ratte")
    # One rank + class skill +3.
    assert int(_skill(trained, "Wahrnehmung")["value"]) == int(_skill(plain, "Wahrnehmung")["value"]) + 4


def test_familiar_spell_resistance_from_master_level_11(client: TestClient, db_session: Session) -> None:
    falcon = _familiar(client, _magier(client, db_session, 11), "Falke")
    features = {f["name"]: f for f in falcon["classFeatures"]}
    assert features["Zauberresistenz"]["summary"] == "ZR 16"
    assert next(a for a in falcon["abilities"] if a["key"] == "IN")["score"] == 11


def test_familiar_grants_its_master_a_bonus(client: TestClient, db_session: Session) -> None:
    master = _magier(client, db_session, 1)
    before = client.get(f"/api/characters/{master['id']}").json()
    _familiar(client, master, "Katze")
    after = client.get(f"/api/characters/{master['id']}").json()

    assert int(_skill(after, "Heimlichkeit")["value"]) == int(_skill(before, "Heimlichkeit")["value"]) + 3
    assert "Wachsamkeit (Vertrauter in Armeslänge)" in _skill(after, "Wahrnehmung")["note"]
    assert "Wachsamkeit" in _skill(after, "Motiv erkennen")["note"]

    toad_master = _magier(client, db_session, 1)
    toad_before = client.get(f"/api/characters/{toad_master['id']}").json()["hp"]["max"]
    _familiar(client, toad_master, "Kröte")
    assert client.get(f"/api/characters/{toad_master['id']}").json()["hp"]["max"] == toad_before + 3


def test_hexe_gets_a_familiar(client: TestClient, db_session: Session) -> None:
    hexe = _master(client, db_session, [{"class_name": "Hexe", "level": 3}])
    assert "Hexenvertrauter" in {f["name"] for f in hexe["classFeatures"]}
    assert _familiar_slot(hexe)["level"] == 3


def test_druide_magier_has_companion_and_familiar(client: TestClient, db_session: Session) -> None:
    master = _master(
        client,
        db_session,
        [
            {"class_name": "Druide", "level": 1, "options": {"bond": ["Tiergefährte"]}},
            {"class_name": "Magier", "level": 1, "options": {"arcane_bond": ["Vertrauter"]}},
        ],
    )
    wolf_species = next(
        s["id"]
        for t in master["companionLevels"] if t["track"] == "animal_companion"
        for s in t["slots"][0]["species"] if s["name"] == "Wolf"
    )
    wolf = client.post(
        f"/api/characters/{master['id']}/companions",
        json={"species_id": wolf_species, "name": "Wolf", "hit_points": [5, 5]},
    )
    assert wolf.status_code == 201, wolf.text
    assert _add_familiar(client, master, "Rabe").status_code == 201


def test_companion_bonuses_from_the_master_skip_the_familiar(client: TestClient, db_session: Session) -> None:
    """"Katzenvolk (Druide)": +1 HP for the Tiergefährte — not for the
    familiar (it has half the master's HP, nothing more)."""
    master = _master(
        client,
        db_session,
        [
            {"class_name": "Druide", "level": 1, "options": {"bond": ["Tiergefährte"]}},
            {"class_name": "Magier", "level": 1, "options": {"arcane_bond": ["Vertrauter"]}},
        ],
        race="Katzenvolk",
        favored_class_bonus={"1": "Katzenvolk (Druide)"},
    )
    wolf_species = next(
        s["id"]
        for t in master["companionLevels"] if t["track"] == "animal_companion"
        for s in t["slots"][0]["species"] if s["name"] == "Wolf"
    )
    response = client.post(
        f"/api/characters/{master['id']}/companions",
        json={"species_id": wolf_species, "name": "Wolf", "hit_points": [5, 5]},
    )
    assert response.status_code == 201, response.text
    wolf = client.get(f"/api/characters/{response.json()['id']}").json()
    raven = _familiar(client, master, "Rabe")

    assert wolf["hp"]["max"] == 5 + 5 + 2 * 2 + 1  # two HD, KO 15, +1 from the master's pick
    assert raven["hp"]["max"] == master["hp"]["max"] // 2
    assert raven["companion"]["masterNotes"] == []
