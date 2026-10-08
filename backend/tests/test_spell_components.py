"""Spell component seed (`scripts/build_spell_components_seed.py`): the PRD's
raw `Komponenten:` strings split per tradition, shown by `sheet.py`'s
`_spell_components_payload`."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import BaseSpell, BaseSpellComponent
from app.seed.class_option_seed import seed_class_options
from app.seed.class_seed import seed_classes
from app.seed.skill_seed import seed_skills
from app.seed.spell_seed import seed_spells
from app.sheet import _spell_components_payload


def _components(db: Session, spell_name: str) -> dict[str, BaseSpellComponent]:
    spell = db.scalars(select(BaseSpell).where(BaseSpell.name == spell_name)).one()
    rows = db.scalars(select(BaseSpellComponent).where(BaseSpellComponent.spell_id == spell.id)).all()
    return {row.tradition: row for row in rows}


def test_slash_group_splits_into_arcane_material_and_divine_focus(db_session: Session) -> None:
    seed_classes(db_session)
    seed_class_options(db_session)
    seed_skills(db_session)
    seed_spells(db_session)

    # PRD: "V, G, M/GF (ein kurzes Schilfrohr oder ein Strohhalm)"
    by_tradition = _components(db_session, "Wasser atmen")
    arcane = _spell_components_payload(by_tradition["arcane"])
    assert (arcane["verbal"], arcane["somatic"], arcane["material"]) == (True, True, True)
    assert arcane["materialDescription"] == "ein kurzes Schilfrohr oder ein Strohhalm"
    assert not arcane["divineFocus"]
    divine = _spell_components_payload(by_tradition["divine"])
    assert divine["divineFocus"] and not divine["focus"] and divine["focusDescription"] is None
    assert not divine["material"]


def test_plain_components_apply_to_every_tradition_and_hand_curated_rows_are_kept(db_session: Session) -> None:
    seed_classes(db_session)
    seed_class_options(db_session)
    seed_skills(db_session)
    seed_spells(db_session)

    # PRD: "V, G, M (...), F (...), GF" -> one Fokus description plus the divine focus
    buße = _components(db_session, "Buße")["divine"]
    assert buße.material_description == "brennender Weihrauch"
    assert buße.focus_description.endswith("; Göttlicher Fokus")

    # Hand-curated early row (not regenerated): Heiliges Symbol, not "GF".
    segnen = _spell_components_payload(_components(db_session, "Segnen")["divine"])
    assert segnen["focus"] and segnen["focusDescription"] == "Heiliges Symbol" and not segnen["divineFocus"]


def test_format_without_row_stays_dash() -> None:
    assert _spell_components_payload(None) is None
