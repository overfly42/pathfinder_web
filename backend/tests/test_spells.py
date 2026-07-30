from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.seed.class_seed import seed_classes
from app.seed.spell_seed import seed_spells


def test_list_spells_is_database_backed(client: TestClient, db_session: Session) -> None:
    seed_classes(db_session)  # base_class_spells FKs into base_classes
    seed_spells(db_session)

    response = client.get("/api/spells")
    assert response.status_code == 200
    spells = response.json()

    assert len(spells) == 23
    assert all({"id", "name", "school", "description"} <= set(spell) for spell in spells)
    magic_missile = next(s for s in spells if s["name"] == "Magisches Geschoss")
    assert magic_missile["school"] == "Hervorrufung"


def test_spells_by_class_groups_by_root_class_with_grades(client: TestClient, db_session: Session) -> None:
    seed_classes(db_session)  # base_class_spells FKs into base_classes
    seed_spells(db_session)

    response = client.get("/api/spells-by-class")
    assert response.status_code == 200
    by_class = response.json()

    assert set(by_class) == {"Magier", "Hexenmeister", "Barde", "Orakel"}
    magier = by_class["Magier"]
    assert all({"id", "name", "grade"} <= set(s) for s in magier)
    schild = next(s for s in magier if s["name"] == "Schild")
    assert schild["grade"] == 1
    nebelwolke = next(s for s in magier if s["name"] == "Nebelwolke")
    assert nebelwolke["grade"] == 2


def test_classes_expose_casting_ability_tradition_and_known_table(client: TestClient, db_session: Session) -> None:
    seed_classes(db_session)
    seed_spells(db_session)

    response = client.get("/api/classes")
    assert response.status_code == 200
    classes = {c["name"]: c for c in response.json()}

    magier = classes["Magier"]
    assert magier["castingAbility"] == "IN"
    assert magier["spellTradition"] == "arcane"
    assert magier["id"] is not None
    # Grade 0/1 accessible from level 1, grade 2 only from level 3 (count is
    # null for arcane-prepared -- presence-only gate, see rules/spells.py).
    assert magier["spellsKnownByLevel"]["1"]["0"] is None
    assert magier["spellsKnownByLevel"]["1"]["1"] is None
    assert "2" not in magier["spellsKnownByLevel"]["1"]
    assert "2" in magier["spellsKnownByLevel"]["3"]

    hexenmeister = classes["Hexenmeister"]
    assert hexenmeister["castingAbility"] == "CH"
    assert hexenmeister["spellTradition"] == "arcane"
    assert hexenmeister["spellsKnownByLevel"]["1"]["0"] == 4
    assert hexenmeister["spellsKnownByLevel"]["1"]["1"] == 2

    krieger = classes["Krieger"]
    assert krieger["castingAbility"] is None
    assert krieger["spellTradition"] is None
