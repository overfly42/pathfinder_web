"""Seeräuber archetype (Entfesselter Barbar) - import_barbar_seereauber.py
adds it as an archetype of Entfesselter Barbar, not core Barbar (the PRD
page's own chassis), per the project owner's request. This is the same
proof-by-test pattern as
test_character_sheet.py::test_class_features_apply_archetype_replacements:
by 18th level every one of the archetype's replaced grants (Umgang mit
Waffen und Rüstungen at 1, Schnelle Bewegung at 1, Gefahreninstinkt at
3/6/9/12/15/18, Verbesserte Reflexbewegung at 5) has been superseded, so
the base proficiency text (still mentioning medium armor) and Schnelle
Bewegung/Gefahreninstinkt/Verbesserte Reflexbewegung by name shouldn't show
up anymore, while the archetype's own five features do (including its own,
medium-armor-less "Umgang mit Waffen und Rüstungen"), and unaffected base
features (Kampfrausch, Starker Kampfrausch) still show.

Also covers Wilder Seemann's skill bonus (`rules/classes/barbarian.py`'s
`_wilder_seemann_notes`, registered under `SITUATIONAL_SKILL_HANDLERS` and
resolved by `rules/handlers.py`'s `situational_skill_notes`): at 18th level
all 6 of its grants (3rd/6th/9th/12th/15th/18th) are met, so the bonus is
+6, surfaced as a situational note (not folded into the base value) on each
of its five skills."""

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.seed.skill_seed import seed_skills

from test_characters import _character_payload, _create_user, _elf_race_id


def test_class_features_apply_seereauber_replacements(client: TestClient, db_session: Session) -> None:
    user_id = _create_user(client)
    race_id = _elf_race_id(client, db_session)

    payload = _character_payload(
        user_id,
        race_id,
        db_session,
        classes=[{"class_name": "Entfesselter Barbar", "level": 18, "archetypes": ["Seeräuber"]}],
    )
    seed_skills(db_session)  # body["skills"] is empty otherwise - _character_payload seeds classes but not skills

    response = client.post("/api/characters", json=payload)
    assert response.status_code == 201
    character_id = response.json()["id"]

    body = client.get(f"/api/characters/{character_id}").json()
    features_by_name = {f["name"]: f["description"] for f in body["classFeatures"]}

    assert {
        "Umgang mit Waffen und Rüstungen",
        "Schrecken des Meeres",
        "Augen des Sturms",
        "Wilder Seemann",
        "Sicherer Tritt",
    } <= features_by_name.keys()
    assert "Schnelle Bewegung" not in features_by_name
    assert "Gefahreninstinkt" not in features_by_name
    assert "Verbesserte Reflexbewegung" not in features_by_name
    assert {"Kampfrausch", "Starker Kampfrausch"} <= features_by_name.keys()

    # The surviving "Umgang mit Waffen und Rüstungen" is the archetype's own
    # (no medium-armor proficiency), not the base Entfesselter-Barbar text.
    assert "nicht mit Mittelschweren Rüstungen" in features_by_name["Umgang mit Waffen und Rüstungen"]

    # "Beruf" is trained-only (`BaseSkill.trained_only`) and this character has
    # no ranks in it, so it's correctly absent from the sheet entirely — same
    # display rule as every other trained-only skill, not archetype-specific.
    skills_by_label = {s["label"]: s for s in body["skills"]}
    for label in ("Akrobatik", "Klettern", "Schwimmen", "Überlebenskunst"):
        note = skills_by_label[label].get("note", "")
        assert "Wilder Seemann" in note
        assert "+ Wilder Seemann +6)" in note
