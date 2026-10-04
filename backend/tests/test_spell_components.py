"""Spell component seed (`scripts/build_spell_components_seed.py`): the PRD's
raw `Komponenten:` strings split per tradition, shown by `sheet.py`'s
`_format_spell_components`."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import BaseSpell, BaseSpellComponent
from app.seed.class_option_seed import seed_class_options
from app.seed.class_seed import seed_classes
from app.seed.skill_seed import seed_skills
from app.seed.spell_seed import seed_spells
from app.sheet import _format_spell_components


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
    assert _format_spell_components(by_tradition["arcane"]) == "V, S, M (ein kurzes Schilfrohr oder ein Strohhalm)"
    assert _format_spell_components(by_tradition["divine"]) == "V, S, GF"


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
    assert _format_spell_components(_components(db_session, "Segnen")["divine"]) == "V, S, F (Heiliges Symbol)"


def test_format_without_row_stays_dash() -> None:
    assert _format_spell_components(None) == "—"
