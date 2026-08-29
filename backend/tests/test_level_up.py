from uuid import UUID

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Character, CharacterSkillRank
from app.seed.class_seed import seed_classes
from test_characters import (
    DEFAULT_ABILITY_SCORES,
    _cantrip_ids,
    _character_payload,
    _create_user,
    _elf_race_id,
    _feat_id,
    _feat_selection,
    _human_race_id,
    _item_id,
    _race_id,
    _skill_id,
    _skill_specialization_id,
    _spells_by_class,
    _to_skill_rank_selections,
)


def _class_id(client: TestClient, db_session: Session, name: str) -> str:
    seed_classes(db_session)
    classes = client.get("/api/classes").json()
    return next(c["id"] for c in classes if c["name"] == name)


def _level_up_payload(base_class_id: str, hit_points: int, **overrides) -> dict:
    """`favored_class_bonus` defaults to "hp" since every single-class test
    character in this file levels up in its one (and therefore favored)
    class — override to `None` only for a genuinely non-favored target
    (e.g. a fresh multiclass pick, which builds its own payload dict
    instead of using this helper)."""
    payload = {
        "target": {"mode": "existing", "base_class_id": base_class_id},
        "hit_points": hit_points,
        "favored_class_bonus": "hp",
    }
    payload.update(overrides)
    return payload


def _create_level_n_character(
    client: TestClient, db_session: Session, race_id: str, class_name: str, level: int, **overrides
) -> str:
    """Creates a level-`level` single-class character and returns its id."""
    response = client.post(
        "/api/characters",
        json=_character_payload(
            _create_user(client),
            race_id,
            db_session,
            classes=[{"class_name": class_name, "level": level}],
            **overrides,
        ),
    )
    assert response.status_code == 201
    return response.json()["id"]


def test_level_up_persists_new_level_on_existing_class(client: TestClient, db_session: Session) -> None:
    race_id = _elf_race_id(client, db_session)
    base_class_id = _class_id(client, db_session, "Waldläufer")
    character_id = _create_level_n_character(client, db_session, race_id, "Waldläufer", 1)

    # Waldläufer is a d10; character level 2 grants no new feat (base_feat_count(2) == base_feat_count(1)).
    response = client.post(f"/api/characters/{character_id}/level-up", json=_level_up_payload(base_class_id, 6))
    assert response.status_code == 201
    body = response.json()
    assert body["level"] == 2
    assert body["classes"] == [{"class_name": "Waldläufer", "level": 2, "archetypes": [], "is_favored": True, "options": {}}]

    sheet = client.get(f"/api/characters/{character_id}").json()
    # Level 1 (auto-maxed d10 + 1 favored-class HP bonus, _character_payload's
    # default level-1 pick) + rolled 6 + 1 more favored-class HP bonus (this
    # level-up's own pick, _level_up_payload's default), no CON mod (KO 13 ->
    # +1, elf -2 KO -> 11 -> +0).
    assert sheet["hp"]["max"] == 18


def test_level_up_rejects_hit_points_out_of_range(client: TestClient, db_session: Session) -> None:
    race_id = _elf_race_id(client, db_session)
    base_class_id = _class_id(client, db_session, "Waldläufer")
    character_id = _create_level_n_character(client, db_session, race_id, "Waldläufer", 1)

    response = client.post(f"/api/characters/{character_id}/level-up", json=_level_up_payload(base_class_id, 11))
    assert response.status_code == 422


def test_level_up_unknown_character_is_404(client: TestClient, db_session: Session) -> None:
    base_class_id = _class_id(client, db_session, "Waldläufer")
    response = client.post(
        "/api/characters/00000000-0000-0000-0000-000000000000/level-up",
        json=_level_up_payload(base_class_id, 5),
    )
    assert response.status_code == 404


def test_level_up_rejects_base_class_id_not_owned_by_character(client: TestClient, db_session: Session) -> None:
    race_id = _elf_race_id(client, db_session)
    other_class_id = _class_id(client, db_session, "Kämpfer")
    character_id = _create_level_n_character(client, db_session, race_id, "Waldläufer", 1)

    response = client.post(f"/api/characters/{character_id}/level-up", json=_level_up_payload(other_class_id, 5))
    assert response.status_code == 422


def test_level_up_grants_a_feat_on_an_odd_level(client: TestClient, db_session: Session) -> None:
    race_id = _elf_race_id(client, db_session)
    base_class_id = _class_id(client, db_session, "Waldläufer")
    # Level 1 -> 2 grants no feat; level 2 -> 3 does (base_feat_count(3) - base_feat_count(2) == 1).
    character_id = _create_level_n_character(client, db_session, race_id, "Waldläufer", 2, hit_points={"2": 5})

    ausweichen_id = _feat_id(client, db_session, "Ausweichen")
    response = client.post(
        f"/api/characters/{character_id}/level-up",
        json=_level_up_payload(base_class_id, 5, feats=[_feat_selection(ausweichen_id)]),
    )
    assert response.status_code == 201
    body = response.json()
    assert {f["feat_id"] for f in body["feats"]} == {ausweichen_id}


def test_level_up_rejects_a_feat_on_an_even_level(client: TestClient, db_session: Session) -> None:
    race_id = _elf_race_id(client, db_session)
    base_class_id = _class_id(client, db_session, "Waldläufer")
    character_id = _create_level_n_character(client, db_session, race_id, "Waldläufer", 1)

    ausweichen_id = _feat_id(client, db_session, "Ausweichen")
    response = client.post(
        f"/api/characters/{character_id}/level-up",
        json=_level_up_payload(base_class_id, 5, feats=[_feat_selection(ausweichen_id)]),
    )
    assert response.status_code == 422


def test_level_up_rejects_a_feat_already_known(client: TestClient, db_session: Session) -> None:
    race_id = _elf_race_id(client, db_session)
    base_class_id = _class_id(client, db_session, "Waldläufer")
    ausweichen_id = _feat_id(client, db_session, "Ausweichen")
    character_id = _create_level_n_character(
        client, db_session, race_id, "Waldläufer", 2, hit_points={"2": 5}, feats=[_feat_selection(ausweichen_id)]
    )

    response = client.post(
        f"/api/characters/{character_id}/level-up",
        json=_level_up_payload(base_class_id, 5, feats=[_feat_selection(ausweichen_id)]),
    )
    assert response.status_code == 422


def test_level_up_rejects_too_many_feats_for_the_delta(client: TestClient, db_session: Session) -> None:
    race_id = _elf_race_id(client, db_session)
    base_class_id = _class_id(client, db_session, "Waldläufer")
    character_id = _create_level_n_character(client, db_session, race_id, "Waldläufer", 2, hit_points={"2": 5})

    langschwert_id = _item_id(client, db_session, "Langschwert")
    feats = [
        _feat_selection(_feat_id(client, db_session, "Ausweichen")),
        _feat_selection(_feat_id(client, db_session, "Waffenfokus"), chosen_weapon_id=langschwert_id),
    ]
    response = client.post(f"/api/characters/{character_id}/level-up", json=_level_up_payload(base_class_id, 5, feats=feats))
    assert response.status_code == 422


def test_level_up_fighter_bonus_feat_on_even_level(client: TestClient, db_session: Session) -> None:
    """Kämpfer grants a bonus combat feat at 1st and every even level - level 1 -> 2
    grants no *regular* feat slot (base_feat_count(2) == base_feat_count(1)) but does
    grant the class bonus slot, so exactly one feat still fits."""
    race_id = _elf_race_id(client, db_session)
    base_class_id = _class_id(client, db_session, "Kämpfer")
    character_id = _create_level_n_character(client, db_session, race_id, "Kämpfer", 1)

    ausweichen_id = _feat_id(client, db_session, "Ausweichen")
    response = client.post(
        f"/api/characters/{character_id}/level-up",
        json=_level_up_payload(base_class_id, 6, feats=[_feat_selection(ausweichen_id)]),
    )
    assert response.status_code == 201


def test_level_up_requires_ability_increase_on_4th_level(client: TestClient, db_session: Session) -> None:
    race_id = _elf_race_id(client, db_session)
    base_class_id = _class_id(client, db_session, "Waldläufer")
    character_id = _create_level_n_character(
        client, db_session, race_id, "Waldläufer", 3, hit_points={"2": 5, "3": 5}
    )

    without_increase = client.post(
        f"/api/characters/{character_id}/level-up", json=_level_up_payload(base_class_id, 5)
    )
    assert without_increase.status_code == 422

    with_increase = client.post(
        f"/api/characters/{character_id}/level-up",
        json=_level_up_payload(base_class_id, 5, ability_increase="ST"),
    )
    assert with_increase.status_code == 201
    body = with_increase.json()
    assert body["ability_scores"]["ST"] == DEFAULT_ABILITY_SCORES["ST"] + 1


def test_level_up_rejects_ability_increase_on_an_ineligible_level(client: TestClient, db_session: Session) -> None:
    race_id = _elf_race_id(client, db_session)
    base_class_id = _class_id(client, db_session, "Waldläufer")
    character_id = _create_level_n_character(client, db_session, race_id, "Waldläufer", 1)

    response = client.post(
        f"/api/characters/{character_id}/level-up",
        json=_level_up_payload(base_class_id, 5, ability_increase="ST"),
    )
    assert response.status_code == 422


def test_level_up_skill_ranks_within_and_over_budget(client: TestClient, db_session: Session) -> None:
    race_id = _elf_race_id(client, db_session)
    base_class_id = _class_id(client, db_session, "Waldläufer")
    character_id = _create_level_n_character(client, db_session, race_id, "Waldläufer", 1)
    skill_id = _skill_id(client, db_session, "Akrobatik")

    response = client.post(
        f"/api/characters/{character_id}/level-up",
        json=_level_up_payload(base_class_id, 5, skill_ranks=_to_skill_rank_selections(client, db_session, {skill_id: 1})),
    )
    assert response.status_code == 201
    assert response.json()["skill_ranks"][skill_id] == 1

    # Absurdly oversized request - guaranteed to exceed any class's per-level budget.
    character_id_2 = _create_level_n_character(client, db_session, race_id, "Waldläufer", 1)
    other_skill_ids = [
        _skill_id(client, db_session, name)
        for name in [
            "Akrobatik",
            "Mit Tieren umgehen",
            "Klettern",
            "Fingerfertigkeit",
            "Fliegen",
            "Heilkunde",
            "Heimlichkeit",
            "Reiten",
            "Schwimmen",
            "Wahrnehmung",
        ]
    ]
    response = client.post(
        f"/api/characters/{character_id_2}/level-up",
        json=_level_up_payload(base_class_id, 5, skill_ranks=_to_skill_rank_selections(client, db_session, {sid: 1 for sid in other_skill_ids})),
    )
    assert response.status_code == 422


def test_level_up_skill_budget_includes_equipped_ability_boosting_item(
    client: TestClient, db_session: Session
) -> None:
    """A belt/headband-style ability-boosting item (`rules/effective_scores.py`'s
    `gear_ability_bonuses`) must count toward the level-up skill-point budget
    the same way it already counts toward the character sheet's own
    displayed ability score — otherwise the level-up endpoint silently
    under-grants skill points to a character wearing e.g. a "Stirnreif der
    enormen Intelligenz" (regression test for the bug fixed alongside
    `routers/characters.py`'s level-up `_effective_ability_mod`, which used
    to read only race/flex, not equipped gear). Halbling has no INT
    modifier and no bonus-skill-point trait of its own, isolating the
    item's effect."""
    race_id = _race_id(client, db_session, "Halbling")
    base_class_id = _class_id(client, db_session, "Magier")
    skill_a = _skill_id(client, db_session, "Zauberkunde")
    skill_b = _skill_id(client, db_session, "Wissen (Arkanes)")
    stirnreif_id = _item_id(client, db_session, "Stirnreif der enormen Intelligenz +2")
    # 2 ranks each (both within the level-2 per-skill cap) so only the
    # overall budget, not the "ranks <= character level" cap, is at stake.
    four_ranks_across_two_skills = _to_skill_rank_selections(client, db_session, {skill_a: 2, skill_b: 2})

    # Magier skillPointsBase 2 + base INT mod +1 (score 12) = 3 without the item.
    without_item_id = _create_level_n_character(
        client, db_session, race_id, "Magier", 1, ability_scores={**DEFAULT_ABILITY_SCORES, "IN": 12}
    )
    response = client.post(
        f"/api/characters/{without_item_id}/level-up",
        json=_level_up_payload(base_class_id, 4, skill_ranks=four_ranks_across_two_skills),
    )
    assert response.status_code == 422

    # Same character shape, but wearing the headband: effective INT 14 (mod
    # +2) -> budget 2 + 2 = 4, now enough for the same 4 skill ranks.
    with_item_id = _create_level_n_character(
        client, db_session, race_id, "Magier", 1, ability_scores={**DEFAULT_ABILITY_SCORES, "IN": 12}
    )
    client.post(f"/api/characters/{with_item_id}/gear", json={"item_id": stirnreif_id, "quantity": 1})
    client.put(f"/api/characters/{with_item_id}/slots/stirnband", json={"item_id": stirnreif_id})
    response = client.post(
        f"/api/characters/{with_item_id}/level-up",
        json=_level_up_payload(base_class_id, 4, skill_ranks=four_ranks_across_two_skills),
    )
    assert response.status_code == 201


def test_level_up_ability_increase_grants_retroactive_skill_points(
    client: TestClient, db_session: Session
) -> None:
    """PF1e ability-score bonuses are retroactive (unlike 3.5e's skill-point
    exception — http://paizo.com/threads/rzs2kpru&page=1?Int-and-Skills#9,
    James Jacobs: "Skill ranks not being retroactive are a 3.5 convention we
    specifically removed from the game"). A permanent INT increase at
    level-up must therefore recompute the skill points already-completed
    levels are owed, not just grant the new level its own points at the
    higher mod. Halbling has no INT racial mod, isolating the ability
    score's own effect."""
    race_id = _race_id(client, db_session, "Halbling")
    base_class_id = _class_id(client, db_session, "Magier")
    skill_a = _skill_id(client, db_session, "Zauberkunde")
    skill_b = _skill_id(client, db_session, "Wissen (Arkanes)")

    # Magier skillPointsBase 2. Level 1-3 at INT 13 (mod +1); level 4 raises
    # INT to 14 (mod +2) via ability_increase. Non-retroactive budget for
    # just the new level would be 2+2=4; the correct retroactive budget also
    # back-corrects levels 1-3 from mod +1 to +2 (+1*3), for 4+3=7 total.
    over_budget_id = _create_level_n_character(
        client, db_session, race_id, "Magier", 3, ability_scores={**DEFAULT_ABILITY_SCORES, "IN": 13}
    )
    response = client.post(
        f"/api/characters/{over_budget_id}/level-up",
        json=_level_up_payload(
            base_class_id,
            4,
            ability_increase="IN",
            skill_ranks=_to_skill_rank_selections(client, db_session, {skill_a: 4, skill_b: 4}),
        ),
    )
    assert response.status_code == 422

    within_budget_id = _create_level_n_character(
        client, db_session, race_id, "Magier", 3, ability_scores={**DEFAULT_ABILITY_SCORES, "IN": 13}
    )
    response = client.post(
        f"/api/characters/{within_budget_id}/level-up",
        json=_level_up_payload(
            base_class_id,
            4,
            ability_increase="IN",
            skill_ranks=_to_skill_rank_selections(client, db_session, {skill_a: 4, skill_b: 3}),
        ),
    )
    assert response.status_code == 201


BACKGROUND_SKILL_NAMES = [
    "Auftreten", "Beruf", "Handwerk", "Mit Tieren umgehen", "Schätzen",
    "Wissen (Adel)", "Wissen (Baukunst)", "Wissen (Geographie)", "Wissen (Geschichte)",
]


def test_level_up_background_skills_flag_persists_from_creation(client: TestClient, db_session: Session) -> None:
    """`use_background_skills` is a one-time creation choice
    (models/character.py's docstring) - never resubmitted at level-up, but
    still enforced there. A level-2 Elf Waldläufer gains a regular delta of
    7 (skillPointsBase 6 + Elf's +1 INT mod) and, with the flag on, a
    background delta of 2 (`background_skill_points_total`); all 9
    background skills at 1 new rank each spends 9, over the regular delta
    alone but within the combined 9 once the overflow draws on it."""
    race_id = _elf_race_id(client, db_session)
    base_class_id = _class_id(client, db_session, "Waldläufer")
    background_skill_ids = _to_skill_rank_selections(
        client, db_session, {_skill_id(client, db_session, name): 1 for name in BACKGROUND_SKILL_NAMES}
    )

    with_flag_id = _create_level_n_character(
        client, db_session, race_id, "Waldläufer", 1, use_background_skills=True
    )
    response = client.post(
        f"/api/characters/{with_flag_id}/level-up",
        json=_level_up_payload(base_class_id, 5, skill_ranks=background_skill_ids),
    )
    assert response.status_code == 201

    without_flag_id = _create_level_n_character(client, db_session, race_id, "Waldläufer", 1)
    response = client.post(
        f"/api/characters/{without_flag_id}/level-up",
        json=_level_up_payload(base_class_id, 5, skill_ranks=background_skill_ids),
    )
    assert response.status_code == 422


def test_level_up_allows_investing_more_than_one_rank_in_a_previously_untrained_skill(
    client: TestClient, db_session: Session
) -> None:
    """Per http://prd.5footstep.de/Grundregelwerk/Fertigkeiten-erwerben, the
    only cap on a single skill is total ranks <= character level - a skill
    with 0 prior ranks may legally gain more than 1 new rank in one
    level-up, not just +1 (this was bug 2 - see the conversation)."""
    race_id = _elf_race_id(client, db_session)
    base_class_id = _class_id(client, db_session, "Waldläufer")
    # Level 1 -> 5: Waldläufer's skill_points_base (6) + IN mod (0) per level
    # * 4 new levels = 24 budget, comfortably more than the 3 ranks below.
    character_id = _create_level_n_character(
        client, db_session, race_id, "Waldläufer", 4, hit_points={"2": 5, "3": 5, "4": 5}
    )
    skill_id = _skill_id(client, db_session, "Akrobatik")

    response = client.post(
        f"/api/characters/{character_id}/level-up",
        json=_level_up_payload(base_class_id, 5, skill_ranks=_to_skill_rank_selections(client, db_session, {skill_id: 3})),
    )
    assert response.status_code == 201
    assert response.json()["skill_ranks"][skill_id] == 3


def test_level_up_rejects_skill_ranks_exceeding_the_new_character_level(
    client: TestClient, db_session: Session
) -> None:
    race_id = _elf_race_id(client, db_session)
    base_class_id = _class_id(client, db_session, "Waldläufer")
    character_id = _create_level_n_character(client, db_session, race_id, "Waldläufer", 1)
    skill_id = _skill_id(client, db_session, "Akrobatik")

    # Level 1 -> 2: even though the skill-point budget could cover 3 ranks,
    # total ranks in one skill can never exceed the new character level (2).
    response = client.post(
        f"/api/characters/{character_id}/level-up",
        json=_level_up_payload(base_class_id, 5, skill_ranks=_to_skill_rank_selections(client, db_session, {skill_id: 3})),
    )
    assert response.status_code == 422


def test_level_up_adds_ranks_to_an_existing_specialization_and_a_new_one(
    client: TestClient, db_session: Session
) -> None:
    """Two specializations of the same has_specialization skill (Beruf) are
    capped independently by character level — adding ranks to an existing
    specialization and starting a brand-new one in the same level-up both
    respect their own <= character level cap, not a shared per-skill one."""
    race_id = _elf_race_id(client, db_session)
    base_class_id = _class_id(client, db_session, "Waldläufer")
    beruf_id = _skill_id(client, db_session, "Beruf")
    seemann_id = _skill_specialization_id(client, db_session, "Beruf", "Seemann")

    character_id = _create_level_n_character(
        client,
        db_session,
        race_id,
        "Waldläufer",
        1,
        skill_ranks=[{"skill_id": beruf_id, "specialization_id": seemann_id, "ranks": 1}],
    )

    response = client.post(
        f"/api/characters/{character_id}/level-up",
        json=_level_up_payload(
            base_class_id,
            5,
            skill_ranks=[
                {"skill_id": beruf_id, "specialization_id": seemann_id, "ranks": 1},
                {"skill_id": beruf_id, "custom_specialization": "Schmied", "ranks": 2},
            ],
        ),
    )
    assert response.status_code == 201

    rows = db_session.scalars(select(CharacterSkillRank).where(CharacterSkillRank.skill_id == UUID(beruf_id))).all()
    totals: dict[tuple, int] = {}
    for row in rows:
        key = (row.specialization_id, row.custom_specialization)
        totals[key] = totals.get(key, 0) + row.ranks
    assert totals == {(UUID(seemann_id), None): 2, (None, "Schmied"): 2}


def test_level_up_multiclass_into_a_new_class_with_archetype(client: TestClient, db_session: Session) -> None:
    race_id = _elf_race_id(client, db_session)
    character_id = _create_level_n_character(client, db_session, race_id, "Waldläufer", 1)

    response = client.post(
        f"/api/characters/{character_id}/level-up",
        json={
            "target": {
                "mode": "new",
                "class_name": "Kämpfer",
                "archetypes": ["Zwei-Waffen-Kämpfer"],
            },
            "hit_points": 6,
        },
    )
    assert response.status_code == 201
    body = response.json()
    assert body["level"] == 2
    kaempfer = next(c for c in body["classes"] if c["class_name"] == "Kämpfer")
    assert kaempfer["level"] == 1
    assert kaempfer["archetypes"] == ["Zwei-Waffen-Kämpfer"]
    assert kaempfer["is_favored"] is False


def test_level_up_multiclass_into_a_new_class_with_option_group(client: TestClient, db_session: Session) -> None:
    race_id = _elf_race_id(client, db_session)
    character_id = _create_level_n_character(client, db_session, race_id, "Waldläufer", 1)

    response = client.post(
        f"/api/characters/{character_id}/level-up",
        json={
            "target": {
                "mode": "new",
                "class_name": "Kleriker",
                "options": {"domain": ["Domäne der Sonne", "Domäne des Todes"]},
            },
            "hit_points": 6,
        },
    )
    assert response.status_code == 201
    body = response.json()
    kleriker = next(c for c in body["classes"] if c["class_name"] == "Kleriker")
    assert kleriker["options"] == {"domain": ["Domäne der Sonne", "Domäne des Todes"]}


def test_level_up_rejects_multiclassing_into_an_already_owned_class(client: TestClient, db_session: Session) -> None:
    race_id = _elf_race_id(client, db_session)
    character_id = _create_level_n_character(client, db_session, race_id, "Waldläufer", 1)

    response = client.post(
        f"/api/characters/{character_id}/level-up",
        json={"target": {"mode": "new", "class_name": "Waldläufer"}, "hit_points": 6},
    )
    assert response.status_code == 422


def test_level_up_spontaneous_caster_rejects_new_spell_when_grade_budget_unchanged(
    client: TestClient, db_session: Session
) -> None:
    """Hexenmeister's grade-1 known-spell cap is 2 at both character level 1
    and 2 (no delta) - a character who already knows 2 grade-1 spells can't
    pick a 3rd just by leveling up to 2."""
    race_id = _elf_race_id(client, db_session)
    base_class_id, spells = _spells_by_class(client, db_session, "Hexenmeister")
    grade1_known = [spells["Magisches Geschoss"], spells["Schild"]]
    character_id = _create_level_n_character(
        client, db_session, race_id, "Hexenmeister", 1, spell_ids={base_class_id: grade1_known}
    )

    response = client.post(
        f"/api/characters/{character_id}/level-up",
        json=_level_up_payload(base_class_id, 1, spell_ids=[spells["Farbenstrahl"]]),
    )
    assert response.status_code == 422


def test_level_up_spontaneous_caster_grants_new_spell_when_grade_budget_grows(
    client: TestClient, db_session: Session
) -> None:
    """Hexenmeister's grade-1 known-spell cap grows from 2 to 3 between
    character level 2 and 3."""
    race_id = _elf_race_id(client, db_session)
    base_class_id, spells = _spells_by_class(client, db_session, "Hexenmeister")
    grade1_known = [spells["Magisches Geschoss"], spells["Schild"]]
    character_id = _create_level_n_character(
        client, db_session, race_id, "Hexenmeister", 2, hit_points={"2": 1}, spell_ids={base_class_id: grade1_known}
    )

    response = client.post(
        f"/api/characters/{character_id}/level-up",
        json=_level_up_payload(base_class_id, 1, spell_ids=[spells["Farbenstrahl"]]),
    )
    assert response.status_code == 201
    assert spells["Farbenstrahl"] in response.json()["spell_ids"][base_class_id]


def test_level_up_arcane_prepared_new_spell_within_and_over_grade(client: TestClient, db_session: Session) -> None:
    race_id = _elf_race_id(client, db_session)
    base_class_id, spells = _spells_by_class(client, db_session, "Magier")
    cantrips = _cantrip_ids(client, "Magier")

    character_id_a = _create_level_n_character(
        client, db_session, race_id, "Magier", 1, spell_ids={base_class_id: cantrips}
    )
    # Level 1 -> 2 still only unlocks grades {0, 1} (grade 2 opens at level 3).
    ok_response = client.post(
        f"/api/characters/{character_id_a}/level-up",
        json=_level_up_payload(base_class_id, 3, spell_ids=[spells["Magisches Geschoss"]]),
    )
    assert ok_response.status_code == 201

    character_id_b = _create_level_n_character(
        client, db_session, race_id, "Magier", 1, spell_ids={base_class_id: cantrips}
    )
    rejected_response = client.post(
        f"/api/characters/{character_id_b}/level-up",
        json=_level_up_payload(base_class_id, 3, spell_ids=[spells["Nebelwolke"]]),
    )
    assert rejected_response.status_code == 422


def test_level_up_arcane_prepared_allows_multiple_new_spells_up_to_delta_budget(
    client: TestClient, db_session: Session
) -> None:
    """Regression test: the level-up wizard used to accept only one new
    spellbook spell per level-up (`LevelUp.spell_id` was a single field),
    even though `arcane_prepared_budget` grants +2 non-grade0 picks per
    level for an arcane-prepared caster like Magier — a real gap, not RAW
    behavior (see todos.md). `spell_ids` now accepts the full delta in one
    call, but still rejects a submission that exceeds it."""
    race_id = _elf_race_id(client, db_session)
    base_class_id, spells = _spells_by_class(client, db_session, "Magier")
    cantrips = _cantrip_ids(client, "Magier")
    # Elf's effective INT mod is +1 (DEFAULT_ABILITY_SCORES IN 10, +2 racial).
    # arcane_prepared_budget: level 1 -> 3 (2+1), fully spent at creation
    # below; level 2 -> 5 (3+2), leaving exactly 2 rooms for this level-up.
    grade1_at_creation = [spells["Magisches Geschoss"], spells["Schild"], spells["Farbenstrahl"]]

    character_id = _create_level_n_character(
        client, db_session, race_id, "Magier", 1, spell_ids={base_class_id: cantrips + grade1_at_creation}
    )
    response = client.post(
        f"/api/characters/{character_id}/level-up",
        json=_level_up_payload(base_class_id, 3, spell_ids=[spells["Schlaf"], spells["Identifizieren"]]),
    )
    assert response.status_code == 201
    known = set(response.json()["spell_ids"][base_class_id])
    assert spells["Schlaf"] in known
    assert spells["Identifizieren"] in known

    # A 3rd spell in the same call exceeds the remaining room (2).
    character_id_2 = _create_level_n_character(
        client, db_session, race_id, "Magier", 1, spell_ids={base_class_id: cantrips + grade1_at_creation}
    )
    rejected = client.post(
        f"/api/characters/{character_id_2}/level-up",
        json=_level_up_payload(
            base_class_id, 3, spell_ids=[spells["Schlaf"], spells["Identifizieren"], spells["Sprung"]]
        ),
    )
    assert rejected.status_code == 422


def test_progression_and_history_reflect_a_real_level_up(client: TestClient, db_session: Session) -> None:
    race_id = _elf_race_id(client, db_session)
    base_class_id = _class_id(client, db_session, "Waldläufer")
    character_id = _create_level_n_character(client, db_session, race_id, "Waldläufer", 1)

    before = client.get(f"/api/characters/{character_id}/progression").json()
    assert before["classes"][0]["level"] == 1
    assert before["history"] == []

    response = client.post(f"/api/characters/{character_id}/level-up", json=_level_up_payload(base_class_id, 6))
    assert response.status_code == 201

    after = client.get(f"/api/characters/{character_id}/progression").json()
    assert after["classes"][0]["level"] == 2
    assert len(after["history"]) == 1
    assert "Waldläufer" in after["history"][0]["description"]

    history = client.get(f"/api/characters/{character_id}/history").json()
    assert history == after["history"]


def test_mock_progression_and_history_fixtures_still_served(client: TestClient) -> None:
    assert client.get("/api/characters/1/progression").status_code == 200
    assert client.get("/api/characters/1/history").json() == []


def test_level_up_rejects_option_choice_below_min_level(client: TestClient, db_session: Session) -> None:
    """"Innere Zähigkeit" (Kampfrauschkraft) needs Barbar level 8 -
    shouldn't be offered/accepted at level 2."""
    race_id = _elf_race_id(client, db_session)
    base_class_id = _class_id(client, db_session, "Barbar")
    character_id = _create_level_n_character(client, db_session, race_id, "Barbar", 1)

    response = client.post(
        f"/api/characters/{character_id}/level-up",
        json=_level_up_payload(
            base_class_id, 5, existing_level_options={"kampfrauschkraft": ["Innere Zähigkeit"]}
        ),
    )
    assert response.status_code == 422


def test_level_up_accepts_option_choice_meeting_min_level(client: TestClient, db_session: Session) -> None:
    race_id = _elf_race_id(client, db_session)
    base_class_id = _class_id(client, db_session, "Barbar")
    character_id = _create_level_n_character(
        client, db_session, race_id, "Barbar", 7, hit_points={str(lvl): 5 for lvl in range(2, 8)}
    )

    # Level 7 -> 8 is also a 4th-level ability-increase level.
    response = client.post(
        f"/api/characters/{character_id}/level-up",
        json=_level_up_payload(
            base_class_id,
            5,
            existing_level_options={"kampfrauschkraft": ["Innere Zähigkeit"]},
            ability_increase="ST",
        ),
    )
    assert response.status_code == 201


def test_level_up_rejects_more_than_one_recurring_option_pick_per_level_up(
    client: TestClient, db_session: Session
) -> None:
    """The group's own max_choices (10, a lifetime career total) must not be
    mistaken for "picks allowed at this one occurrence" (always 1) - this
    was a real regression, not just a gap."""
    race_id = _elf_race_id(client, db_session)
    base_class_id = _class_id(client, db_session, "Barbar")
    character_id = _create_level_n_character(client, db_session, race_id, "Barbar", 1)

    response = client.post(
        f"/api/characters/{character_id}/level-up",
        json=_level_up_payload(
            base_class_id, 5, existing_level_options={"kampfrauschkraft": ["Aberglaube", "Animalische Wut"]}
        ),
    )
    assert response.status_code == 422


def test_level_up_favored_class_bonus_accepts_halbork_barbar_alternate(
    client: TestClient, db_session: Session
) -> None:
    """Half-Orc's Advanced Race Guide alternate favored-class bonus for
    Barbarian (+1 rage round/day per pick, flat) - real accumulation via
    `rules/favored_class_bonuses.py`'s `HANDLERS`, not just composition."""
    race_id = _race_id(client, db_session, "Halb-Ork")
    base_class_id = _class_id(client, db_session, "Barbar")
    character_id = _create_level_n_character(client, db_session, race_id, "Barbar", 1, flex_ability="ST")

    response = client.post(
        f"/api/characters/{character_id}/level-up",
        json=_level_up_payload(base_class_id, 5, favored_class_bonus="Halb-Ork (Barbar)"),
    )
    assert response.status_code == 201

    sheet = client.get(f"/api/characters/{character_id}").json()
    entry = next(e for e in sheet["favoredClassBonuses"] if e["name"] == "Halb-Ork (Barbar)")
    assert entry["pickCount"] == 1
    assert entry["currentBonus"] == 1
    assert "Halb-Ork (Barbar)" in sheet["favoredClassBonusOptions"]
    assert {"hp", "skill"} <= set(sheet["favoredClassBonusOptions"])


def test_level_up_favored_class_bonus_fraction_accumulates_and_floors(
    client: TestClient, db_session: Session
) -> None:
    """Half-Orc Rogue's alternate (+1/3 per pick, capped at +5) only becomes
    a whole bonus once enough picks accumulate - exactly `hit_points`'
    "raw value per level, aggregated at read time" shape, per the user's
    own framing for this feature."""
    race_id = _race_id(client, db_session, "Halb-Ork")
    base_class_id = _class_id(client, db_session, "Schurke")
    character_id = _create_level_n_character(client, db_session, race_id, "Schurke", 1, flex_ability="ST")

    for _ in range(2):
        response = client.post(
            f"/api/characters/{character_id}/level-up",
            json=_level_up_payload(base_class_id, 5, favored_class_bonus="Halb-Ork (Schurke)"),
        )
        assert response.status_code == 201

    sheet = client.get(f"/api/characters/{character_id}").json()
    entry = next(e for e in sheet["favoredClassBonuses"] if e["name"] == "Halb-Ork (Schurke)")
    assert entry["pickCount"] == 2
    assert entry["currentBonus"] == 0  # floor(2/3) = 0, no whole bonus yet

    # Level 3 -> 4 is also a 4th-level ability-increase level.
    response = client.post(
        f"/api/characters/{character_id}/level-up",
        json=_level_up_payload(
            base_class_id, 5, favored_class_bonus="Halb-Ork (Schurke)", ability_increase="ST"
        ),
    )
    assert response.status_code == 201

    sheet = client.get(f"/api/characters/{character_id}").json()
    entry = next(e for e in sheet["favoredClassBonuses"] if e["name"] == "Halb-Ork (Schurke)")
    assert entry["pickCount"] == 3
    assert entry["currentBonus"] == 1  # floor(3/3) = 1


def test_level_up_favored_class_bonus_rejects_wrong_race(client: TestClient, db_session: Session) -> None:
    race_id = _elf_race_id(client, db_session)
    base_class_id = _class_id(client, db_session, "Barbar")
    character_id = _create_level_n_character(client, db_session, race_id, "Barbar", 1)

    response = client.post(
        f"/api/characters/{character_id}/level-up",
        json=_level_up_payload(base_class_id, 5, favored_class_bonus="Halb-Ork (Barbar)"),
    )
    assert response.status_code == 422


def test_level_up_accepts_one_recurring_option_pick(client: TestClient, db_session: Session) -> None:
    race_id = _elf_race_id(client, db_session)
    base_class_id = _class_id(client, db_session, "Barbar")
    character_id = _create_level_n_character(client, db_session, race_id, "Barbar", 1)

    response = client.post(
        f"/api/characters/{character_id}/level-up",
        json=_level_up_payload(base_class_id, 5, existing_level_options={"kampfrauschkraft": ["Aberglaube"]}),
    )
    assert response.status_code == 201
    barbar = next(c for c in response.json()["classes"] if c["class_name"] == "Barbar")
    assert "Aberglaube" in barbar["options"].get("kampfrauschkraft", [])


def test_level_up_rejects_chain_rage_power_without_its_prerequisite(
    client: TestClient, db_session: Session
) -> None:
    """Entfesselter Barbar's "Bestientotem" (min_level 6) also requires
    "Bestientotem, Schwächeres" to already have been taken - not just the
    level threshold (routers/characters.py's `_validate_options`,
    `BaseClassOptionChoice.requires_choice_id`). Regression test: this
    prerequisite used to be stored in the seed data but never actually
    enforced anywhere, so a level-6+ character could pick the mid tier
    without ever taking the entry tier."""
    race_id = _elf_race_id(client, db_session)
    base_class_id = _class_id(client, db_session, "Entfesselter Barbar")
    character_id = _create_level_n_character(client, db_session, race_id, "Entfesselter Barbar", 5)

    response = client.post(
        f"/api/characters/{character_id}/level-up",
        json=_level_up_payload(base_class_id, 5, existing_level_options={"kampfrauschkraft": ["Bestientotem"]}),
    )
    assert response.status_code == 422
    assert "Bestientotem, Schwächeres" in response.json()["detail"]


def test_level_up_accepts_chain_rage_power_once_its_prerequisite_was_taken(
    client: TestClient, db_session: Session
) -> None:
    race_id = _elf_race_id(client, db_session)
    base_class_id = _class_id(client, db_session, "Entfesselter Barbar")
    create_response = client.post(
        "/api/characters",
        json=_character_payload(
            _create_user(client),
            race_id,
            db_session,
            classes=[
                {
                    "class_name": "Entfesselter Barbar",
                    "level": 5,
                    "options": {"kampfrauschkraft": ["Bestientotem, Schwächeres"]},
                }
            ],
        ),
    )
    assert create_response.status_code == 201
    character_id = create_response.json()["id"]

    response = client.post(
        f"/api/characters/{character_id}/level-up",
        json=_level_up_payload(base_class_id, 5, existing_level_options={"kampfrauschkraft": ["Bestientotem"]}),
    )
    assert response.status_code == 201
    barbar = next(c for c in response.json()["classes"] if c["class_name"] == "Entfesselter Barbar")
    assert {"Bestientotem, Schwächeres", "Bestientotem"} <= set(barbar["options"].get("kampfrauschkraft", []))


def test_level_up_requires_favored_class_bonus_for_the_favored_class(
    client: TestClient, db_session: Session
) -> None:
    race_id = _elf_race_id(client, db_session)
    base_class_id = _class_id(client, db_session, "Waldläufer")
    character_id = _create_level_n_character(client, db_session, race_id, "Waldläufer", 1)

    response = client.post(
        f"/api/characters/{character_id}/level-up",
        json=_level_up_payload(base_class_id, 6, favored_class_bonus=None),
    )
    assert response.status_code == 422


def test_level_up_rejects_favored_class_bonus_for_a_non_favored_class(
    client: TestClient, db_session: Session
) -> None:
    race_id = _elf_race_id(client, db_session)
    character_id = _create_level_n_character(client, db_session, race_id, "Waldläufer", 1)

    response = client.post(
        f"/api/characters/{character_id}/level-up",
        json={"target": {"mode": "new", "class_name": "Kämpfer"}, "hit_points": 6, "favored_class_bonus": "hp"},
    )
    assert response.status_code == 422


def test_level_up_favored_class_bonus_skill_adds_one_extra_skill_point(
    client: TestClient, db_session: Session
) -> None:
    """Barbar's base skill budget (4 + IN mod 0 = 4) can only fit 5 different
    skill picks if the favored-class bonus is spent on a skill rank. Uses
    Half-Ork (no fixed ability mods, unlike Elf's +2 IN) with the flex bonus
    on ST so the IN modifier - and therefore the base budget of exactly 4 -
    stays unambiguous."""
    race_id = _race_id(client, db_session, "Halb-Ork")
    base_class_id = _class_id(client, db_session, "Barbar")
    character_id = _create_level_n_character(
        client, db_session, race_id, "Barbar", 1, flex_ability="ST"
    )
    skill_ids = [
        _skill_id(client, db_session, name)
        for name in ["Akrobatik", "Klettern", "Schwimmen", "Einschüchtern", "Wahrnehmung"]
    ]

    response = client.post(
        f"/api/characters/{character_id}/level-up",
        json=_level_up_payload(
            base_class_id,
            5,
            favored_class_bonus="skill",
            skill_ranks=_to_skill_rank_selections(client, db_session, {sid: 1 for sid in skill_ids}),
        ),
    )
    assert response.status_code == 201
    assert len(response.json()["skill_ranks"]) == 5


def test_level_up_favored_class_bonus_hp_does_not_grant_the_extra_skill_point(
    client: TestClient, db_session: Session
) -> None:
    race_id = _race_id(client, db_session, "Halb-Ork")
    base_class_id = _class_id(client, db_session, "Barbar")
    character_id = _create_level_n_character(
        client, db_session, race_id, "Barbar", 1, flex_ability="ST"
    )
    skill_ids = [
        _skill_id(client, db_session, name)
        for name in ["Akrobatik", "Klettern", "Schwimmen", "Einschüchtern", "Wahrnehmung"]
    ]

    response = client.post(
        f"/api/characters/{character_id}/level-up",
        json=_level_up_payload(
            base_class_id,
            5,
            favored_class_bonus="hp",
            skill_ranks=_to_skill_rank_selections(client, db_session, {sid: 1 for sid in skill_ids}),
        ),
    )
    assert response.status_code == 422
