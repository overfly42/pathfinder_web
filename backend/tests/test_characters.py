from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    Character,
    CharacterFeat,
    CharacterGear,
    CharacterRacialChoice,
    CharacterSkillRank,
    CharacterTrait,
)
from app.rules.context import CharacterContext
from app.rules.race_abilities import HANDLERS
from app.seed.class_ability_seed import seed_class_abilities
from app.seed.class_option_seed import seed_class_options
from app.seed.class_seed import seed_classes
from app.seed.feat_seed import seed_feats
from app.seed.item_seed import seed_items
from app.seed.race_seed import seed_races
from app.seed.skill_seed import seed_skills
from app.seed.spell_seed import seed_spells
from app.seed.trait_seed import seed_traits

DEFAULT_ABILITY_SCORES = {"ST": 10, "GE": 12, "KO": 13, "IN": 10, "WE": 10, "CH": 8}


def _create_user(client: TestClient, name: str = "Anna") -> str:
    return client.post("/api/users", json={"name": name}).json()["id"]


def _race_id(client: TestClient, db_session: Session, name: str) -> str:
    seed_races(db_session)
    races = client.get("/api/races").json()
    return next(r["id"] for r in races if r["name"] == name)


def _elf_race_id(client: TestClient, db_session: Session) -> str:
    return _race_id(client, db_session, "Elf")


def _human_race_id(client: TestClient, db_session: Session) -> str:
    return _race_id(client, db_session, "Mensch")


def _skill_id(client: TestClient, db_session: Session, name: str) -> str:
    seed_classes(db_session)  # base_class_skills FKs into base_classes
    seed_class_options(db_session)  # base_class_skills.option_choice_id FKs here
    seed_skills(db_session)
    skills = client.get("/api/skills").json()
    return next(s["id"] for s in skills if s["name"] == name)


def _feat_id(client: TestClient, db_session: Session, name: str) -> str:
    # base_feat_required_* FKs into base_races/base_classes/base_class_abilities/base_skills.
    seed_races(db_session)
    seed_classes(db_session)
    seed_class_options(db_session)  # base_class_ability_grants.option_choice_id FKs here
    seed_class_abilities(db_session)
    seed_skills(db_session)
    seed_feats(db_session)
    feats = client.get("/api/feats").json()
    return next(f["id"] for f in feats if f["name"] == name)


def _feat_selection(feat_id: str, **sub_choice) -> dict:
    """Builds one `CharacterCreate.feats` entry (`FeatSelection`) — `sub_choice`
    is `chosen_weapon_id=...`/`chosen_skill_id=...`/`chosen_spell_school=...`
    for feats whose `BaseFeat.sub_choice_type` requires one, omitted otherwise."""
    return {"feat_id": feat_id, **sub_choice}


def _trait_id(client: TestClient, db_session: Session, name: str) -> str:
    seed_traits(db_session)
    traits = client.get("/api/traits").json()
    return next(t["id"] for t in traits if t["name"] == name)


def _item_id(client: TestClient, db_session: Session, name: str) -> str:
    seed_items(db_session)
    items = client.get("/api/items").json()
    return next(i["id"] for i in items if i["name"] == name)


def _spells_by_class(client: TestClient, db_session: Session, class_name: str) -> tuple[str, dict[str, str]]:
    """(base_class_id, {spell_name: spell_id}) for a spontaneous/arcane-prepared class."""
    seed_classes(db_session)  # base_class_spells FKs into base_classes
    seed_class_options(db_session)  # base_class_spell_grants.option_choice_id FKs here
    seed_spells(db_session)
    classes = client.get("/api/classes").json()
    base_class_id = next(c["id"] for c in classes if c["name"] == class_name)
    by_class = client.get("/api/spells-by-class").json()
    name_to_id = {s["name"]: s["id"] for s in by_class[class_name]}
    return base_class_id, name_to_id


def _cantrip_ids(client: TestClient, class_name: str) -> list[str]:
    """All grade-0 spell ids for a class, straight off `/api/spells-by-class`
    (call after `_spells_by_class` has already seeded). An arcane-prepared
    spellbook (Magier) must contain every grade-0 spell on its list, not a
    fixed sample — same real PF1e rule that `create_character` enforces —
    so tests need the full, current set rather than a couple of hardcoded
    names that happened to be the entire cantrip list before the PRD import."""
    by_class = client.get("/api/spells-by-class").json()
    return [s["id"] for s in by_class[class_name] if s["grade"] == 0]


def _character_payload(user_id: str, race_id: str, db_session: Session, **overrides) -> dict:
    seed_classes(db_session)  # base_class_option_groups/base_class_ability_grants FK into base_classes
    seed_class_options(db_session)
    seed_class_abilities(db_session)
    classes = overrides.get("classes", [{"class_name": "Waldläufer", "level": 1}])
    total_level = sum(selection["level"] for selection in classes)

    # Every level whose class_name matches the first submitted class (the
    # favored class, see create_character's favored_root_id) - mirrors that
    # same function's own favored_levels computation, string-matched since
    # a `classes` entry's class_name is always a root class name (never an
    # archetype, resolve_root_class rejects those).
    favored_class_name = classes[0]["class_name"]
    favored_levels: list[int] = []
    running_level = 0
    for selection in classes:
        for _ in range(selection["level"]):
            running_level += 1
            if selection["class_name"] == favored_class_name:
                favored_levels.append(running_level)

    payload = {
        "name": "Elyra",
        "user_id": user_id,
        "race_id": race_id,
        "classes": classes,
        # Player-entered HP roll for every level past the first (see
        # CharacterCreate.hit_points) - a flat 1 per level by default (always
        # in-range for any class's hit die), overridable by tests that care
        # about the actual HP total.
        "hit_points": {str(level): 1 for level in range(2, total_level + 1)},
        # Favored-class bonus for every level in the favored class (see
        # CharacterCreate.favored_class_bonus) - the universal "+1 HP" pick
        # by default, overridable by tests that care about the actual value
        # (e.g. a race-scoped alternate bonus).
        "favored_class_bonus": {str(level): "hp" for level in favored_levels},
        "ability_scores": DEFAULT_ABILITY_SCORES,
        "point_budget": 20,
    }
    payload.update(overrides)
    return payload


def test_create_character(client: TestClient, db_session: Session) -> None:
    user_id = _create_user(client)
    race_id = _elf_race_id(client, db_session)

    response = client.post("/api/characters", json=_character_payload(user_id, race_id, db_session))
    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "Elyra"
    assert body["race_id"] == race_id
    assert body["level"] == 1
    assert body["classes"] == [
        {"class_name": "Waldläufer", "level": 1, "archetypes": [], "is_favored": True, "options": {}}
    ]
    # A freshly created character is undamaged - max HP itself isn't
    # returned by this endpoint (see Character.damage_taken's docstring),
    # only checked below via the sheet endpoint.
    assert body["damage_taken"] == 0
    assert body["bab"] == 1
    assert body["saves"] == {"fort": 2, "ref": 2, "will": 0}
    assert body["ability_scores"] == DEFAULT_ABILITY_SCORES
    assert body["point_budget"] == 20
    assert body["flex_ability"] is None

    # Waldläufer (d10, full BAB, good fort/ref, poor will) at char level 1,
    # max HP for the character's first level (10), + 1 favored-class HP
    # bonus (_character_payload's default level-1 favored_class_bonus pick),
    # Elf's -2 KO (13 -> 11, mod 0).
    sheet = client.get(f"/api/characters/{body['id']}").json()
    assert sheet["hp"] == {"current": 11, "max": 11, "temporary": 0}


def test_create_character_with_unknown_race_is_rejected(client: TestClient, db_session: Session) -> None:
    user_id = _create_user(client)
    response = client.post(
        "/api/characters",
        json=_character_payload(user_id, "00000000-0000-0000-0000-000000000000", db_session),
    )
    assert response.status_code == 422


def test_create_character_with_unknown_class_name_is_rejected(client: TestClient, db_session: Session) -> None:
    user_id = _create_user(client)
    race_id = _elf_race_id(client, db_session)

    response = client.post(
        "/api/characters",
        json=_character_payload(user_id, race_id, db_session, classes=[{"class_name": "Nichtklasse", "level": 1}]),
    )
    assert response.status_code == 422


def test_create_character_with_multiple_classes_persists_per_level_history(
    client: TestClient, db_session: Session
) -> None:
    user_id = _create_user(client)
    race_id = _elf_race_id(client, db_session)

    response = client.post(
        "/api/characters",
        json=_character_payload(
            user_id,
            race_id,
            db_session,
            classes=[{"class_name": "Kämpfer", "level": 2}, {"class_name": "Schurke", "level": 1}],
            # Player-entered HP rolls for Kämpfer's 2nd level and Schurke's
            # 1st level (character levels 2 and 3 - level 1 is auto-maxed).
            hit_points={"2": 6, "3": 5},
        ),
    )
    assert response.status_code == 201
    body = response.json()
    assert body["level"] == 3
    assert body["classes"] == [
        {"class_name": "Kämpfer", "level": 2, "archetypes": [], "is_favored": True, "options": {}},
        {"class_name": "Schurke", "level": 1, "archetypes": [], "is_favored": False, "options": {}},
    ]
    # A freshly created character is undamaged, regardless of computed max.
    assert body["damage_taken"] == 0
    # BAB: Kämpfer floor(2*1.0)=2, Schurke floor(1*0.75)=0.
    assert body["bab"] == 2
    # Fort: Kämpfer good (2+1)=3, Schurke poor (0)=0 -> 3.
    # Ref: Kämpfer poor (0), Schurke good (2+0)=2 -> 2.
    # Will: Kämpfer poor (0), Schurke poor (0) -> 0.
    assert body["saves"] == {"fort": 3, "ref": 2, "will": 0}

    # HP/BAB/saves are each class's own contribution against its own level
    # count, summed - not the total level against one averaged progression
    # (requirements_v2.md §2). Char level 1 (Kämpfer's 1st) auto-maxes its
    # d10 (10); the other two rolls are the player-entered values above (6,
    # 5); Kämpfer is the favored class (classes[0]), so both its levels (1
    # and 2) also get _character_payload's default +1 HP favored-class
    # bonus. Elf's -2 KO (13 -> 11) is a +0 modifier, so total HP is
    # (10+1)+(6+1)+5=23.
    sheet = client.get(f"/api/characters/{body['id']}").json()
    assert sheet["hp"] == {"current": 23, "max": 23, "temporary": 0}


def test_create_character_missing_hit_points_for_a_higher_level_is_rejected(
    client: TestClient, db_session: Session
) -> None:
    user_id = _create_user(client)
    race_id = _elf_race_id(client, db_session)

    response = client.post(
        "/api/characters",
        json=_character_payload(
            user_id, race_id, db_session, classes=[{"class_name": "Waldläufer", "level": 2}], hit_points={}
        ),
    )
    assert response.status_code == 422


def test_create_character_hit_points_out_of_hit_die_range_is_rejected(
    client: TestClient, db_session: Session
) -> None:
    user_id = _create_user(client)
    race_id = _elf_race_id(client, db_session)

    response = client.post(
        "/api/characters",
        json=_character_payload(
            user_id,
            race_id,
            db_session,
            classes=[{"class_name": "Waldläufer", "level": 2}],
            hit_points={"2": 11},  # Waldläufer is a d10 - 11 is out of range.
        ),
    )
    assert response.status_code == 422


def test_create_character_hit_points_for_level_one_is_rejected(client: TestClient, db_session: Session) -> None:
    """Level 1 is always auto-maxed - the player can't submit (or override) a
    roll for it."""
    user_id = _create_user(client)
    race_id = _elf_race_id(client, db_session)

    response = client.post(
        "/api/characters",
        json=_character_payload(
            user_id, race_id, db_session, classes=[{"class_name": "Waldläufer", "level": 1}], hit_points={"1": 5}
        ),
    )
    assert response.status_code == 422


def test_create_character_with_archetype_persists_and_round_trips(client: TestClient, db_session: Session) -> None:
    user_id = _create_user(client)
    race_id = _elf_race_id(client, db_session)

    response = client.post(
        "/api/characters",
        json=_character_payload(
            user_id,
            race_id,
            db_session,
            classes=[{"class_name": "Kämpfer", "level": 2, "archetypes": ["Zwei-Waffen-Kämpfer"]}],
        ),
    )
    assert response.status_code == 201
    body = response.json()
    assert body["classes"] == [
        {
            "class_name": "Kämpfer",
            "level": 2,
            "archetypes": ["Zwei-Waffen-Kämpfer"],
            "is_favored": True,
            "options": {},
        }
    ]

    # GET /api/characters/{id} now returns the sheet's display shape
    # (app/sheet.py), not a composition echo — verify persistence directly
    # against the ORM instead. The ORM property also carries an "id" (root
    # BaseClass id, for the level-up wizard's target picker) that
    # CharacterRead's ClassSelection schema doesn't declare and so drops.
    db_character = db_session.get(Character, body["id"])
    assert [{k: v for k, v in c.items() if k != "id"} for c in db_character.classes] == body["classes"]


def test_create_character_with_unknown_archetype_is_rejected(client: TestClient, db_session: Session) -> None:
    user_id = _create_user(client)
    race_id = _elf_race_id(client, db_session)

    response = client.post(
        "/api/characters",
        json=_character_payload(
            user_id,
            race_id,
            db_session,
            classes=[{"class_name": "Kämpfer", "level": 1, "archetypes": ["Nichtexistenter Archetyp"]}],
        ),
    )
    assert response.status_code == 422


def test_create_character_with_multiple_archetypes_on_one_class_succeeds(
    client: TestClient, db_session: Session
) -> None:
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
                    "class_name": "Kämpfer",
                    "level": 1,
                    "archetypes": ["Zwei-Waffen-Kämpfer", "Schildkämpfer"],
                }
            ],
        ),
    )
    assert response.status_code == 201
    body = response.json()
    assert set(body["classes"][0]["archetypes"]) == {"Zwei-Waffen-Kämpfer", "Schildkämpfer"}


def test_create_character_with_same_class_across_rows_merges_archetypes(
    client: TestClient, db_session: Session
) -> None:
    user_id = _create_user(client)
    race_id = _elf_race_id(client, db_session)

    response = client.post(
        "/api/characters",
        json=_character_payload(
            user_id,
            race_id,
            db_session,
            classes=[
                {"class_name": "Kämpfer", "level": 1, "archetypes": ["Zwei-Waffen-Kämpfer"]},
                {"class_name": "Schurke", "level": 1},
                {"class_name": "Kämpfer", "level": 1, "archetypes": ["Schildkämpfer"]},
            ],
        ),
    )
    assert response.status_code == 201
    body = response.json()
    assert len(body["classes"]) == 2
    kaempfer = next(c for c in body["classes"] if c["class_name"] == "Kämpfer")
    assert kaempfer["level"] == 2
    assert set(kaempfer["archetypes"]) == {"Zwei-Waffen-Kämpfer", "Schildkämpfer"}


def test_create_character_with_option_group_choice_persists(client: TestClient, db_session: Session) -> None:
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
                    "class_name": "Kleriker",
                    "level": 1,
                    "options": {"domain": ["Domäne der Sonne", "Domäne des Todes"]},
                }
            ],
        ),
    )
    assert response.status_code == 201
    body = response.json()
    assert body["classes"][0]["options"] == {"domain": ["Domäne der Sonne", "Domäne des Todes"]}


def test_create_character_with_invalid_option_choice_is_rejected(client: TestClient, db_session: Session) -> None:
    user_id = _create_user(client)
    race_id = _elf_race_id(client, db_session)

    response = client.post(
        "/api/characters",
        json=_character_payload(
            user_id,
            race_id,
            db_session,
            classes=[{"class_name": "Kleriker", "level": 1, "options": {"domain": ["Nichtdomäne"]}}],
        ),
    )
    assert response.status_code == 422


def test_create_character_exceeding_option_group_max_is_rejected(client: TestClient, db_session: Session) -> None:
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
                    "class_name": "Kleriker",
                    "level": 1,
                    "options": {
                        "domain": ["Domäne der Sonne", "Domäne des Todes", "Domäne des Wissens"]
                    },
                }
            ],
        ),
    )
    assert response.status_code == 422


def test_create_character_over_point_buy_budget_is_rejected(client: TestClient, db_session: Session) -> None:
    user_id = _create_user(client)
    race_id = _elf_race_id(client, db_session)

    response = client.post(
        "/api/characters",
        json=_character_payload(
            user_id, race_id, db_session, ability_scores={"ST": 18, "GE": 18, "KO": 18, "IN": 18, "WE": 18, "CH": 18}
        ),
    )
    assert response.status_code == 422


def test_create_character_with_ability_score_out_of_range_is_rejected(client: TestClient, db_session: Session) -> None:
    user_id = _create_user(client)
    race_id = _elf_race_id(client, db_session)

    response = client.post(
        "/api/characters",
        json=_character_payload(user_id, race_id, db_session, ability_scores={**DEFAULT_ABILITY_SCORES, "ST": 19}),
    )
    assert response.status_code == 422


def test_create_character_for_flex_race_requires_flex_ability(client: TestClient, db_session: Session) -> None:
    user_id = _create_user(client)
    race_id = _human_race_id(client, db_session)

    response = client.post("/api/characters", json=_character_payload(user_id, race_id, db_session))
    assert response.status_code == 422


def test_create_character_for_flex_race_with_flex_ability_succeeds(client: TestClient, db_session: Session) -> None:
    user_id = _create_user(client)
    race_id = _human_race_id(client, db_session)

    response = client.post("/api/characters", json=_character_payload(user_id, race_id, db_session, flex_ability="GE"))
    assert response.status_code == 201
    assert response.json()["flex_ability"] == "GE"


def test_create_character_for_flex_race_persists_choice_via_replacement_system(
    client: TestClient, db_session: Session
) -> None:
    user_id = _create_user(client)
    race_id = _human_race_id(client, db_session)

    created = client.post(
        "/api/characters", json=_character_payload(user_id, race_id, db_session, flex_ability="ST")
    ).json()

    character = db_session.get(Character, created["id"])
    choices = db_session.scalars(
        select(CharacterRacialChoice).where(CharacterRacialChoice.character_id == character.id)
    ).all()
    assert len(choices) == 1
    # The stored row is an ability_id resolved through RaceAbilityReplacement,
    # not a raw "ST" string — resolving it back through HANDLERS must agree
    # with what was requested.
    modifier = HANDLERS[choices[0].ability_id](CharacterContext())[0]
    assert (modifier.target_id, modifier.value) == ("ST", 2)


def test_create_character_for_non_flex_race_rejects_flex_ability(client: TestClient, db_session: Session) -> None:
    user_id = _create_user(client)
    race_id = _elf_race_id(client, db_session)

    response = client.post("/api/characters", json=_character_payload(user_id, race_id, db_session, flex_ability="GE"))
    assert response.status_code == 422


def test_create_character_persists_alt_traits(client: TestClient, db_session: Session) -> None:
    user_id = _create_user(client)
    race_id = _elf_race_id(client, db_session)

    # "Dunkelsicht" replaces Dämmersicht, "Traumdeuter" replaces Elfische
    # Immunität — two real, non-conflicting Elf alternates (see
    # test_elf_standard_traits_and_alternates_are_real).
    response = client.post(
        "/api/characters",
        json=_character_payload(user_id, race_id, db_session, alt_traits=["Dunkelsicht", "Traumdeuter"]),
    )
    assert response.status_code == 201
    body = response.json()
    assert set(body["alt_traits"]) == {"Dunkelsicht", "Traumdeuter"}

    character = db_session.get(Character, body["id"])
    choices = db_session.scalars(
        select(CharacterRacialChoice).where(CharacterRacialChoice.character_id == character.id)
    ).all()
    assert len(choices) == 2


def test_create_character_rejects_unknown_alt_trait(client: TestClient, db_session: Session) -> None:
    user_id = _create_user(client)
    race_id = _elf_race_id(client, db_session)

    response = client.post(
        "/api/characters", json=_character_payload(user_id, race_id, db_session, alt_traits=["Nicht Existent"])
    )
    assert response.status_code == 422


def test_create_character_rejects_flex_only_alternate_as_alt_trait(client: TestClient, db_session: Session) -> None:
    """The flex "+2 to any attribute" alternates share the ability catalog
    with real alt-traits (both are `is_alternate=True` grants) but must only
    be pickable via `flex_ability`, never via `alt_traits`."""
    user_id = _create_user(client)
    race_id = _human_race_id(client, db_session)

    response = client.post(
        "/api/characters",
        json=_character_payload(
            user_id, race_id, db_session, flex_ability="GE", alt_traits=["+2 auf Geschicklichkeit"]
        ),
    )
    assert response.status_code == 422


def test_create_character_rejects_conflicting_alt_traits(client: TestClient, db_session: Session) -> None:
    race_id = _elf_race_id(client, db_session)

    # "Arkane Konzentration" and "Leichtfüßig" both genuinely replace
    # "Elfische Waffenvertrautheit" (see race_ability_replacements.json) —
    # a real conflict, no manual setup needed.
    user_id = _create_user(client)
    response = client.post(
        "/api/characters",
        json=_character_payload(user_id, race_id, db_session, alt_traits=["Arkane Konzentration", "Leichtfüßig"]),
    )
    assert response.status_code == 422


def test_create_character_persists_skill_ranks_on_highest_level(client: TestClient, db_session: Session) -> None:
    user_id = _create_user(client)
    race_id = _human_race_id(client, db_session)
    klettern_id = _skill_id(client, db_session, "Klettern")
    reiten_id = _skill_id(client, db_session, "Reiten")

    response = client.post(
        "/api/characters",
        json=_character_payload(
            user_id,
            race_id,
            db_session,
            flex_ability="ST",
            classes=[{"class_name": "Waldläufer", "level": 3}],
            skill_ranks={klettern_id: 3, reiten_id: 2},
        ),
    )
    assert response.status_code == 201
    body = response.json()
    assert body["skill_ranks"] == {klettern_id: 3, reiten_id: 2}

    character = db_session.get(Character, body["id"])
    # No per-level breakdown for multi-level creation: both skills land as a
    # single audit row each, tied to the highest CharacterLevel created.
    highest_level = max(character.levels, key=lambda level: level.level)
    ranks = db_session.scalars(
        select(CharacterSkillRank).where(CharacterSkillRank.level_id == highest_level.id)
    ).all()
    assert {(str(r.skill_id), r.ranks) for r in ranks} == {(klettern_id, 3), (reiten_id, 2)}


def test_create_character_skill_ranks_exceeding_level_are_rejected(client: TestClient, db_session: Session) -> None:
    user_id = _create_user(client)
    race_id = _human_race_id(client, db_session)
    klettern_id = _skill_id(client, db_session, "Klettern")

    response = client.post(
        "/api/characters",
        json=_character_payload(
            user_id,
            race_id,
            db_session,
            flex_ability="ST",
            classes=[{"class_name": "Waldläufer", "level": 1}],
            skill_ranks={klettern_id: 2},
        ),
    )
    assert response.status_code == 422


def test_create_character_human_geschult_adds_one_skill_point_per_level(
    client: TestClient, db_session: Session
) -> None:
    """Human's "Geschult" racial trait (rules/skill_points.py) grants +1
    skill rank per character level on top of the class's own budget —
    Waldläufer's skillPointsBase 6 + INT mod 0 + 1 (Geschult) = 7 at level 1,
    one more than a race without the trait would allow."""
    user_id = _create_user(client)
    race_id = _human_race_id(client, db_session)
    skill_names = [
        "Akrobatik", "Fingerfertigkeit", "Entfesselungskunst", "Heimlichkeit", "Reiten", "Mechanismus ausschalten", "Klettern",
    ]
    skill_ranks = {_skill_id(client, db_session, name): 1 for name in skill_names}

    response = client.post(
        "/api/characters",
        json=_character_payload(
            user_id,
            race_id,
            db_session,
            flex_ability="ST",
            classes=[{"class_name": "Waldläufer", "level": 1}],
            skill_ranks=skill_ranks,
        ),
    )
    assert response.status_code == 201


def test_create_character_skill_ranks_exceeding_budget_are_rejected(client: TestClient, db_session: Session) -> None:
    user_id = _create_user(client)
    race_id = _human_race_id(client, db_session)
    # Waldläufer's skillPointsBase is 6; INT modifier is 0 for these scores;
    # Human's "Geschult" adds +1/level -> budget 7. 8 skills at 1 rank each
    # (level cap at level 1) overspends it.
    skill_names = [
        "Akrobatik", "Fingerfertigkeit", "Entfesselungskunst", "Heimlichkeit", "Reiten", "Mechanismus ausschalten", "Klettern",
        "Schwimmen",
    ]
    skill_ranks = {_skill_id(client, db_session, name): 1 for name in skill_names}

    response = client.post(
        "/api/characters",
        json=_character_payload(
            user_id,
            race_id,
            db_session,
            flex_ability="ST",
            classes=[{"class_name": "Waldläufer", "level": 1}],
            skill_ranks=skill_ranks,
        ),
    )
    assert response.status_code == 422


def test_create_character_with_unknown_skill_id_is_rejected(client: TestClient, db_session: Session) -> None:
    user_id = _create_user(client)
    race_id = _human_race_id(client, db_session)

    response = client.post(
        "/api/characters",
        json=_character_payload(
            user_id,
            race_id,
            db_session,
            flex_ability="ST",
            skill_ranks={"00000000-0000-0000-0000-000000000000": 1},
        ),
    )
    assert response.status_code == 422


BACKGROUND_SKILL_NAMES = [
    "Auftreten", "Beruf", "Handwerk", "Mit Tieren umgehen", "Schätzen",
    "Wissen (Adel)", "Wissen (Baukunst)", "Wissen (Geographie)", "Wissen (Geschichte)",
]


def test_create_character_background_skills_allow_overflow_into_regular_budget(
    client: TestClient, db_session: Session
) -> None:
    """http://prd.5footstep.de/Alternativregeln/Fertigkeiten/Hintergrundfertigkeiten:
    with `use_background_skills` on, a level-1 Elf Waldläufer has a regular
    budget of 7 (skillPointsBase 6 + Elf's +1 INT mod) and a background
    budget of 2 (flat, `background_skill_points_total`). All 9 background
    skills at 1 rank each (level cap at level 1) spends 9 - more than the
    regular budget alone allows, but within 7 regular + 2 background once
    the 7-rank overflow beyond the background budget draws on the regular
    one (`_skill_ranks_exceed_budget`)."""
    user_id = _create_user(client)
    race_id = _elf_race_id(client, db_session)
    skill_ranks = {_skill_id(client, db_session, name): 1 for name in BACKGROUND_SKILL_NAMES}

    response = client.post(
        "/api/characters",
        json=_character_payload(
            user_id, race_id, db_session, use_background_skills=True, skill_ranks=skill_ranks
        ),
    )
    assert response.status_code == 201
    assert response.json()["use_background_skills"] is True


def test_create_character_background_skills_still_enforce_combined_budget(
    client: TestClient, db_session: Session
) -> None:
    """Same setup as the overflow test above (7 regular + 2 background = 9
    total), plus one more rank in an adventure skill - now 10 spent, over
    the combined budget even with `use_background_skills` on."""
    user_id = _create_user(client)
    race_id = _elf_race_id(client, db_session)
    skill_ranks = {_skill_id(client, db_session, name): 1 for name in BACKGROUND_SKILL_NAMES}
    skill_ranks[_skill_id(client, db_session, "Klettern")] = 1

    response = client.post(
        "/api/characters",
        json=_character_payload(
            user_id, race_id, db_session, use_background_skills=True, skill_ranks=skill_ranks
        ),
    )
    assert response.status_code == 422


def test_create_character_background_skill_points_cannot_cover_adventure_skills(
    client: TestClient, db_session: Session
) -> None:
    """The alternate rule is one-directional: background skill points can
    never be spent on adventure skills, even with `use_background_skills`
    on. A level-1 Elf Waldläufer's regular budget is 7; 8 adventure skills
    at 1 rank each overspends it regardless of the unused 2-point
    background budget."""
    user_id = _create_user(client)
    race_id = _elf_race_id(client, db_session)
    adventure_skill_names = [
        "Akrobatik", "Fingerfertigkeit", "Entfesselungskunst", "Heimlichkeit", "Reiten", "Mechanismus ausschalten",
        "Klettern", "Schwimmen",
    ]
    skill_ranks = {_skill_id(client, db_session, name): 1 for name in adventure_skill_names}

    response = client.post(
        "/api/characters",
        json=_character_payload(
            user_id, race_id, db_session, use_background_skills=True, skill_ranks=skill_ranks
        ),
    )
    assert response.status_code == 422


def test_create_character_background_skill_tag_is_inert_without_opting_in(
    client: TestClient, db_session: Session
) -> None:
    """Without `use_background_skills` (the default), `BaseSkill.is_background`
    changes nothing - the same 9-skill spend the overflow test above accepts
    is rejected here by the plain single-pool budget (7)."""
    user_id = _create_user(client)
    race_id = _elf_race_id(client, db_session)
    skill_ranks = {_skill_id(client, db_session, name): 1 for name in BACKGROUND_SKILL_NAMES}

    response = client.post(
        "/api/characters",
        json=_character_payload(user_id, race_id, db_session, skill_ranks=skill_ranks),
    )
    assert response.status_code == 422


def test_create_character_persists_feats_on_highest_level(client: TestClient, db_session: Session) -> None:
    user_id = _create_user(client)
    race_id = _human_race_id(client, db_session)
    ausweichen_id = _feat_id(client, db_session, "Ausweichen")
    kampfreflexe_id = _feat_id(client, db_session, "Kampfreflexe")

    response = client.post(
        "/api/characters",
        json=_character_payload(
            user_id,
            race_id,
            db_session,
            flex_ability="ST",
            classes=[{"class_name": "Waldläufer", "level": 3}],
            feats=[_feat_selection(ausweichen_id), _feat_selection(kampfreflexe_id)],
        ),
    )
    assert response.status_code == 201
    body = response.json()
    assert {f["feat_id"] for f in body["feats"]} == {ausweichen_id, kampfreflexe_id}

    character = db_session.get(Character, body["id"])
    highest_level = max(character.levels, key=lambda level: level.level)
    feats = db_session.scalars(select(CharacterFeat).where(CharacterFeat.level_id == highest_level.id)).all()
    assert {str(f.feat_id) for f in feats} == {ausweichen_id, kampfreflexe_id}


def test_create_character_feats_exceeding_level_cap_are_rejected(client: TestClient, db_session: Session) -> None:
    user_id = _create_user(client)
    race_id = _elf_race_id(client, db_session)
    langschwert_id = _item_id(client, db_session, "Langschwert")
    feats = [
        _feat_selection(_feat_id(client, db_session, name))
        for name in ["Ausweichen", "Kampfreflexe"]
    ] + [_feat_selection(_feat_id(client, db_session, "Waffenfokus"), chosen_weapon_id=langschwert_id)]

    # Elf (no race bonus feat) Waldläufer (no class bonus feats) at level 1 ->
    # featMax = base_feat_count(1) = 1, so three feats is over budget.
    response = client.post(
        "/api/characters",
        json=_character_payload(
            user_id,
            race_id,
            db_session,
            classes=[{"class_name": "Waldläufer", "level": 1}],
            feats=feats,
        ),
    )
    assert response.status_code == 422


def test_create_character_feat_max_includes_human_bonus_feat(client: TestClient, db_session: Session) -> None:
    user_id = _create_user(client)
    race_id = _human_race_id(client, db_session)
    langschwert_id = _item_id(client, db_session, "Langschwert")
    feats = [_feat_selection(_feat_id(client, db_session, name)) for name in ["Ausweichen", "Kampfreflexe"]]

    # Human grants a bonus feat at 1st level ("Bonustalent"): base_feat_count(1)
    # + 1 = 2, so two feats fit even though the base progression alone is 1.
    response = client.post(
        "/api/characters",
        json=_character_payload(
            user_id,
            race_id,
            db_session,
            flex_ability="ST",
            classes=[{"class_name": "Waldläufer", "level": 1}],
            feats=feats,
        ),
    )
    assert response.status_code == 201

    third_feat_id = _feat_id(client, db_session, "Waffenfokus")
    response = client.post(
        "/api/characters",
        json=_character_payload(
            user_id,
            race_id,
            db_session,
            flex_ability="ST",
            classes=[{"class_name": "Waldläufer", "level": 1}],
            feats=feats + [_feat_selection(third_feat_id, chosen_weapon_id=langschwert_id)],
        ),
    )
    assert response.status_code == 422


def test_create_character_feat_max_includes_fighter_bonus_feats(client: TestClient, db_session: Session) -> None:
    user_id = _create_user(client)
    race_id = _elf_race_id(client, db_session)
    langschwert_id = _item_id(client, db_session, "Langschwert")
    feats = [_feat_selection(_feat_id(client, db_session, name)) for name in ["Ausweichen", "Kampfreflexe"]]

    # Elf (no race bonus) Kämpfer at level 1: base_feat_count(1) = 1 +
    # class_bonus_feat_slot_count (Kämpfer's 1st-level bonus combat feat
    # grant) = 1 -> max 2.
    response = client.post(
        "/api/characters",
        json=_character_payload(
            user_id,
            race_id,
            db_session,
            classes=[{"class_name": "Kämpfer", "level": 1}],
            feats=feats,
        ),
    )
    assert response.status_code == 201

    third_feat_id = _feat_id(client, db_session, "Waffenfokus")
    response = client.post(
        "/api/characters",
        json=_character_payload(
            user_id,
            race_id,
            db_session,
            classes=[{"class_name": "Kämpfer", "level": 1}],
            feats=feats + [_feat_selection(third_feat_id, chosen_weapon_id=langschwert_id)],
        ),
    )
    assert response.status_code == 422


def test_create_character_feat_max_for_human_fighter_at_level_1_is_three(
    client: TestClient, db_session: Session
) -> None:
    user_id = _create_user(client)
    race_id = _human_race_id(client, db_session)
    langschwert_id = _item_id(client, db_session, "Langschwert")
    feats = [
        _feat_selection(_feat_id(client, db_session, name)) for name in ["Ausweichen", "Kampfreflexe"]
    ] + [_feat_selection(_feat_id(client, db_session, "Waffenfokus"), chosen_weapon_id=langschwert_id)]

    response = client.post(
        "/api/characters",
        json=_character_payload(
            user_id,
            race_id,
            db_session,
            flex_ability="ST",
            classes=[{"class_name": "Kämpfer", "level": 1}],
            feats=feats,
        ),
    )
    assert response.status_code == 201
    assert {f["feat_id"] for f in response.json()["feats"]} == {selection["feat_id"] for selection in feats}

    fourth_feat_id = _feat_id(client, db_session, "Kernschuss")
    response = client.post(
        "/api/characters",
        json=_character_payload(
            user_id,
            race_id,
            db_session,
            flex_ability="ST",
            classes=[{"class_name": "Kämpfer", "level": 1}],
            feats=feats + [_feat_selection(fourth_feat_id)],
        ),
    )
    assert response.status_code == 422


def test_create_character_with_unknown_feat_id_is_rejected(client: TestClient, db_session: Session) -> None:
    user_id = _create_user(client)
    race_id = _human_race_id(client, db_session)

    response = client.post(
        "/api/characters",
        json=_character_payload(
            user_id,
            race_id,
            db_session,
            flex_ability="ST",
            feats=[_feat_selection("00000000-0000-0000-0000-000000000000")],
        ),
    )
    assert response.status_code == 422


def test_create_character_with_duplicate_feat_ids_is_rejected(client: TestClient, db_session: Session) -> None:
    user_id = _create_user(client)
    race_id = _human_race_id(client, db_session)
    ausweichen_id = _feat_id(client, db_session, "Ausweichen")

    response = client.post(
        "/api/characters",
        json=_character_payload(
            user_id,
            race_id,
            db_session,
            flex_ability="ST",
            feats=[_feat_selection(ausweichen_id), _feat_selection(ausweichen_id)],
        ),
    )
    assert response.status_code == 422


def test_create_character_allows_the_same_open_choice_feat_twice_with_different_weapons(
    client: TestClient, db_session: Session
) -> None:
    user_id = _create_user(client)
    race_id = _human_race_id(client, db_session)
    waffenfokus_id = _feat_id(client, db_session, "Waffenfokus")
    langschwert_id = _item_id(client, db_session, "Langschwert")
    kurzschwert_id = _item_id(client, db_session, "Kurzschwert")

    # Human at level 1 gets base_feat_count(1)=1 + bonus feat = 2 slots, so
    # both Waffenfokus picks fit even though it's the same feat both times.
    response = client.post(
        "/api/characters",
        json=_character_payload(
            user_id,
            race_id,
            db_session,
            flex_ability="ST",
            feats=[
                _feat_selection(waffenfokus_id, chosen_weapon_id=langschwert_id),
                _feat_selection(waffenfokus_id, chosen_weapon_id=kurzschwert_id),
            ],
        ),
    )
    assert response.status_code == 201
    body = response.json()
    assert {f["chosen_weapon_id"] for f in body["feats"]} == {langschwert_id, kurzschwert_id}


def test_create_character_rejects_weapon_focus_without_a_weapon(client: TestClient, db_session: Session) -> None:
    user_id = _create_user(client)
    race_id = _human_race_id(client, db_session)
    waffenfokus_id = _feat_id(client, db_session, "Waffenfokus")

    response = client.post(
        "/api/characters",
        json=_character_payload(
            user_id,
            race_id,
            db_session,
            flex_ability="ST",
            feats=[_feat_selection(waffenfokus_id)],
        ),
    )
    assert response.status_code == 422


def test_create_character_rejects_weapon_focus_with_a_non_weapon_item(client: TestClient, db_session: Session) -> None:
    user_id = _create_user(client)
    race_id = _human_race_id(client, db_session)
    waffenfokus_id = _feat_id(client, db_session, "Waffenfokus")
    non_weapon_id = _item_id(client, db_session, "Fackel")

    response = client.post(
        "/api/characters",
        json=_character_payload(
            user_id,
            race_id,
            db_session,
            flex_ability="ST",
            feats=[_feat_selection(waffenfokus_id, chosen_weapon_id=non_weapon_id)],
        ),
    )
    assert response.status_code == 422


def test_create_character_rejects_a_sub_choice_on_a_feat_that_does_not_take_one(
    client: TestClient, db_session: Session
) -> None:
    user_id = _create_user(client)
    race_id = _human_race_id(client, db_session)
    ausweichen_id = _feat_id(client, db_session, "Ausweichen")
    langschwert_id = _item_id(client, db_session, "Langschwert")

    response = client.post(
        "/api/characters",
        json=_character_payload(
            user_id,
            race_id,
            db_session,
            flex_ability="ST",
            feats=[_feat_selection(ausweichen_id, chosen_weapon_id=langschwert_id)],
        ),
    )
    assert response.status_code == 422


def test_create_character_persists_skill_focus_and_spell_focus_sub_choices(
    client: TestClient, db_session: Session
) -> None:
    user_id = _create_user(client)
    race_id = _human_race_id(client, db_session)
    fertigkeitsfokus_id = _feat_id(client, db_session, "Fertigkeitsfokus")
    zauberfokus_id = _feat_id(client, db_session, "Zauberfokus")
    heimlichkeit_id = _skill_id(client, db_session, "Heimlichkeit")
    seed_spells(db_session)
    schools = client.get("/api/spell-schools").json()
    school = schools[0]

    response = client.post(
        "/api/characters",
        json=_character_payload(
            user_id,
            race_id,
            db_session,
            flex_ability="ST",
            classes=[{"class_name": "Waldläufer", "level": 3}],
            feats=[
                _feat_selection(fertigkeitsfokus_id, chosen_skill_id=heimlichkeit_id),
                _feat_selection(zauberfokus_id, chosen_spell_school=school),
            ],
        ),
    )
    assert response.status_code == 201
    body = response.json()
    by_feat_id = {f["feat_id"]: f for f in body["feats"]}
    assert by_feat_id[fertigkeitsfokus_id]["chosen_skill_id"] == heimlichkeit_id
    assert by_feat_id[zauberfokus_id]["chosen_spell_school"] == school


def test_create_character_persists_traits_on_highest_level(client: TestClient, db_session: Session) -> None:
    user_id = _create_user(client)
    race_id = _elf_race_id(client, db_session)
    reaktionsschnell_id = _trait_id(client, db_session, "Reaktionsschnell")
    adoptiert_id = _trait_id(client, db_session, "Adoptiert")

    response = client.post(
        "/api/characters",
        json=_character_payload(
            user_id,
            race_id,
            db_session,
            classes=[{"class_name": "Waldläufer", "level": 3}],
            trait_ids=[reaktionsschnell_id, adoptiert_id],
        ),
    )
    assert response.status_code == 201
    body = response.json()
    assert set(body["trait_ids"]) == {reaktionsschnell_id, adoptiert_id}

    character = db_session.get(Character, body["id"])
    highest_level = max(character.levels, key=lambda level: level.level)
    traits = db_session.scalars(select(CharacterTrait).where(CharacterTrait.level_id == highest_level.id)).all()
    assert {str(t.trait_id) for t in traits} == {reaktionsschnell_id, adoptiert_id}


def test_create_character_with_more_than_two_traits_is_rejected(client: TestClient, db_session: Session) -> None:
    user_id = _create_user(client)
    race_id = _elf_race_id(client, db_session)
    trait_ids = [
        _trait_id(client, db_session, name)
        for name in ["Reaktionsschnell", "Adoptiert", "Disziplinierter Gläubiger"]
    ]

    response = client.post(
        "/api/characters",
        json=_character_payload(user_id, race_id, db_session, trait_ids=trait_ids),
    )
    assert response.status_code == 422


def test_create_character_with_unknown_trait_id_is_rejected(client: TestClient, db_session: Session) -> None:
    user_id = _create_user(client)
    race_id = _elf_race_id(client, db_session)

    response = client.post(
        "/api/characters",
        json=_character_payload(
            user_id, race_id, db_session, trait_ids=["00000000-0000-0000-0000-000000000000"]
        ),
    )
    assert response.status_code == 422


def test_create_character_with_duplicate_trait_ids_is_rejected(client: TestClient, db_session: Session) -> None:
    user_id = _create_user(client)
    race_id = _elf_race_id(client, db_session)
    reaktionsschnell_id = _trait_id(client, db_session, "Reaktionsschnell")

    response = client.post(
        "/api/characters",
        json=_character_payload(user_id, race_id, db_session, trait_ids=[reaktionsschnell_id, reaktionsschnell_id]),
    )
    assert response.status_code == 422


def test_create_character_with_two_traits_from_the_same_area_is_rejected(
    client: TestClient, db_session: Session
) -> None:
    user_id = _create_user(client)
    race_id = _elf_race_id(client, db_session)
    # "Reaktionsschnell" and "Anatom" are both "combat" traits.
    reaktionsschnell_id = _trait_id(client, db_session, "Reaktionsschnell")
    verteidiger_id = _trait_id(client, db_session, "Anatom")

    response = client.post(
        "/api/characters",
        json=_character_payload(user_id, race_id, db_session, trait_ids=[reaktionsschnell_id, verteidiger_id]),
    )
    assert response.status_code == 422


def test_create_character_requires_skill_choice_for_gewitztes_wortspiel(
    client: TestClient, db_session: Session
) -> None:
    """`BaseTrait.skill_choice_ability` (set on "Gewitztes Wortspiel"):
    taking the trait without a matching `trait_skill_choices` entry is
    rejected, same as an open-choice feat missing its sub-choice
    (`_validate_trait_skill_choice`, `routers/characters.py`)."""
    user_id = _create_user(client)
    race_id = _elf_race_id(client, db_session)
    trait_id = _trait_id(client, db_session, "Gewitztes Wortspiel")

    response = client.post(
        "/api/characters",
        json=_character_payload(user_id, race_id, db_session, trait_ids=[trait_id]),
    )
    assert response.status_code == 422


def test_create_character_rejects_non_charisma_skill_for_gewitztes_wortspiel(
    client: TestClient, db_session: Session
) -> None:
    """"Wähle eine charismabasierte Fertigkeit" — Klettern (ST-based) is not
    a legal `trait_skill_choices` value for this trait."""
    user_id = _create_user(client)
    race_id = _elf_race_id(client, db_session)
    trait_id = _trait_id(client, db_session, "Gewitztes Wortspiel")
    klettern_id = _skill_id(client, db_session, "Klettern")

    response = client.post(
        "/api/characters",
        json=_character_payload(
            user_id,
            race_id,
            db_session,
            trait_ids=[trait_id],
            trait_skill_choices={trait_id: klettern_id},
        ),
    )
    assert response.status_code == 422


def test_create_character_persists_gewitztes_wortspiel_skill_choice(
    client: TestClient, db_session: Session
) -> None:
    user_id = _create_user(client)
    race_id = _elf_race_id(client, db_session)
    trait_id = _trait_id(client, db_session, "Gewitztes Wortspiel")
    bluffen_id = _skill_id(client, db_session, "Bluffen")

    response = client.post(
        "/api/characters",
        json=_character_payload(
            user_id,
            race_id,
            db_session,
            trait_ids=[trait_id],
            trait_skill_choices={trait_id: bluffen_id},
        ),
    )
    assert response.status_code == 201

    character = db_session.get(Character, response.json()["id"])
    highest_level = max(character.levels, key=lambda level: level.level)
    trait = db_session.scalars(select(CharacterTrait).where(CharacterTrait.level_id == highest_level.id)).one()
    assert str(trait.trait_id) == trait_id
    assert str(trait.chosen_skill_id) == bluffen_id


def test_create_character_persists_gear(client: TestClient, db_session: Session) -> None:
    user_id = _create_user(client)
    race_id = _elf_race_id(client, db_session)
    dolch_id = _item_id(client, db_session, "Dolch")
    fackel_id = _item_id(client, db_session, "Fackel")

    response = client.post(
        "/api/characters",
        json=_character_payload(
            user_id,
            race_id,
            db_session,
            gear=[{"item_id": dolch_id, "quantity": 1}, {"item_id": fackel_id, "quantity": 5}],
        ),
    )
    assert response.status_code == 201
    body = response.json()
    assert {(g["item_id"], g["quantity"]) for g in body["gear"]} == {(dolch_id, 1), (fackel_id, 5)}

    character = db_session.get(Character, body["id"])
    gear = db_session.scalars(select(CharacterGear).where(CharacterGear.character_id == character.id)).all()
    assert {(str(g.item_id), g.quantity) for g in gear} == {(dolch_id, 1), (fackel_id, 5)}


def test_create_character_with_unknown_item_id_is_rejected(client: TestClient, db_session: Session) -> None:
    user_id = _create_user(client)
    race_id = _elf_race_id(client, db_session)

    response = client.post(
        "/api/characters",
        json=_character_payload(
            user_id,
            race_id,
            db_session,
            gear=[{"item_id": "00000000-0000-0000-0000-000000000000", "quantity": 1}],
        ),
    )
    assert response.status_code == 422


def test_create_character_with_duplicate_item_ids_is_rejected(client: TestClient, db_session: Session) -> None:
    user_id = _create_user(client)
    race_id = _elf_race_id(client, db_session)
    dolch_id = _item_id(client, db_session, "Dolch")

    response = client.post(
        "/api/characters",
        json=_character_payload(
            user_id,
            race_id,
            db_session,
            gear=[{"item_id": dolch_id, "quantity": 1}, {"item_id": dolch_id, "quantity": 2}],
        ),
    )
    assert response.status_code == 422


def test_create_character_with_zero_quantity_gear_is_rejected(client: TestClient, db_session: Session) -> None:
    user_id = _create_user(client)
    race_id = _elf_race_id(client, db_session)
    dolch_id = _item_id(client, db_session, "Dolch")

    response = client.post(
        "/api/characters",
        json=_character_payload(user_id, race_id, db_session, gear=[{"item_id": dolch_id, "quantity": 0}]),
    )
    assert response.status_code == 422


def test_get_character(client: TestClient, db_session: Session) -> None:
    user_id = _create_user(client)
    race_id = _elf_race_id(client, db_session)
    created = client.post("/api/characters", json=_character_payload(user_id, race_id, db_session)).json()

    response = client.get(f"/api/characters/{created['id']}")
    assert response.status_code == 200
    # GET now returns the sheet's display shape (app/sheet.py); the raw
    # persisted ability scores are covered by test_character_sheet.py and
    # by db_session assertions elsewhere in this file.
    assert response.json()["name"] == "Elyra"
    assert response.json()["race"] == "Elf"


def test_get_unknown_character_returns_404(client: TestClient) -> None:
    response = client.get("/api/characters/00000000-0000-0000-0000-000000000000")
    assert response.status_code == 404


def test_rename_character(client: TestClient, db_session: Session) -> None:
    user_id = _create_user(client)
    race_id = _elf_race_id(client, db_session)
    created = client.post("/api/characters", json=_character_payload(user_id, race_id, db_session)).json()

    response = client.patch(f"/api/characters/{created['id']}", json={"name": "Elyra Silberauge"})
    assert response.status_code == 200
    assert response.json()["name"] == "Elyra Silberauge"


def test_delete_character(client: TestClient, db_session: Session) -> None:
    user_id = _create_user(client)
    race_id = _elf_race_id(client, db_session)
    created = client.post("/api/characters", json=_character_payload(user_id, race_id, db_session)).json()

    response = client.delete(f"/api/characters/{created['id']}")
    assert response.status_code == 204

    response = client.get(f"/api/characters/{created['id']}")
    assert response.status_code == 404


def test_delete_character_with_a_racial_choice_does_not_crash(client: TestClient, db_session: Session) -> None:
    """Regression test: `Character.racial_choices` used to have no cascade,
    so deleting any character with a `CharacterRacialChoice` row (a flex
    ability bonus, e.g. Human's, or an alt trait) 500'd instead of deleting -
    SQLAlchemy tried to null out CharacterRacialChoice.character_id, which
    isn't nullable, rather than deleting the row."""
    user_id = _create_user(client)
    race_id = _human_race_id(client, db_session)
    created = client.post(
        "/api/characters", json=_character_payload(user_id, race_id, db_session, flex_ability="ST")
    ).json()

    response = client.delete(f"/api/characters/{created['id']}")
    assert response.status_code == 204

    response = client.get(f"/api/characters/{created['id']}")
    assert response.status_code == 404


def test_adjust_hp_damage_and_heal(client: TestClient, db_session: Session) -> None:
    user_id = _create_user(client)
    race_id = _elf_race_id(client, db_session)
    # Waldläufer (d10) at level 1 is always auto-maxed (10) + 1 favored-class
    # HP bonus (_character_payload's default level-1 pick); Elf's -2 KO
    # (13 -> 11) is a +0 modifier, so hp_max == 11.
    created = client.post("/api/characters", json=_character_payload(user_id, race_id, db_session)).json()

    response = client.patch(f"/api/characters/{created['id']}/hp", json={"delta": -4})
    assert response.status_code == 200
    assert response.json()["damage_taken"] == 4
    assert client.get(f"/api/characters/{created['id']}").json()["hp"] == {"current": 7, "max": 11, "temporary": 0}

    response = client.patch(f"/api/characters/{created['id']}/hp", json={"delta": 2})
    assert response.status_code == 200
    assert response.json()["damage_taken"] == 2
    assert client.get(f"/api/characters/{created['id']}").json()["hp"] == {"current": 9, "max": 11, "temporary": 0}


def test_adjust_hp_damage_is_capped_at_negative_con_score_death_floor(
    client: TestClient, db_session: Session
) -> None:
    # Same character as test_adjust_hp_damage_and_heal: hp_max == 11, effective
    # KO == 11 (Elf's -2 applied to base 13) — PF1e RAW death floor is -con
    # score, so current HP should bottom out at -11, not 0.
    user_id = _create_user(client)
    race_id = _elf_race_id(client, db_session)
    created = client.post("/api/characters", json=_character_payload(user_id, race_id, db_session)).json()

    response = client.patch(f"/api/characters/{created['id']}/hp", json={"delta": -100})
    assert response.status_code == 200
    assert response.json()["damage_taken"] == 22
    assert client.get(f"/api/characters/{created['id']}").json()["hp"]["current"] == -11


def test_adjust_hp_healing_past_max_is_wasted(client: TestClient, db_session: Session) -> None:
    user_id = _create_user(client)
    race_id = _elf_race_id(client, db_session)
    created = client.post("/api/characters", json=_character_payload(user_id, race_id, db_session)).json()

    response = client.patch(f"/api/characters/{created['id']}/hp", json={"delta": 5})
    assert response.status_code == 200
    assert response.json()["damage_taken"] == 0
    assert client.get(f"/api/characters/{created['id']}").json()["hp"] == {"current": 11, "max": 11, "temporary": 0}


def test_adjust_hp_temporary_hit_points_absorb_damage_before_real_hp(
    client: TestClient, db_session: Session
) -> None:
    # Same character as test_adjust_hp_damage_and_heal: hp_max == 11.
    user_id = _create_user(client)
    race_id = _elf_race_id(client, db_session)
    created = client.post("/api/characters", json=_character_payload(user_id, race_id, db_session)).json()

    response = client.patch(f"/api/characters/{created['id']}/hp", json={"temporary_hit_points": 5})
    assert response.status_code == 200
    assert response.json()["temporary_hit_points"] == 5
    sheet = client.get(f"/api/characters/{created['id']}").json()
    assert sheet["hp"] == {"current": 11, "max": 11, "temporary": 5}

    # 3 damage is fully absorbed by the temporary pool, real HP untouched.
    response = client.patch(f"/api/characters/{created['id']}/hp", json={"delta": -3})
    assert response.status_code == 200
    assert response.json()["temporary_hit_points"] == 2
    assert response.json()["damage_taken"] == 0
    sheet = client.get(f"/api/characters/{created['id']}").json()
    assert sheet["hp"] == {"current": 11, "max": 11, "temporary": 2}

    # 5 more damage: drains the remaining 2 temporary HP, the other 3 spills onto real HP.
    response = client.patch(f"/api/characters/{created['id']}/hp", json={"delta": -5})
    assert response.status_code == 200
    assert response.json()["temporary_hit_points"] == 0
    assert response.json()["damage_taken"] == 3
    sheet = client.get(f"/api/characters/{created['id']}").json()
    assert sheet["hp"] == {"current": 8, "max": 11, "temporary": 0}

    # Real healing never refills/changes the temporary pool.
    client.patch(f"/api/characters/{created['id']}/hp", json={"temporary_hit_points": 4})
    response = client.patch(f"/api/characters/{created['id']}/hp", json={"delta": 1})
    assert response.status_code == 200
    assert response.json()["temporary_hit_points"] == 4
    sheet = client.get(f"/api/characters/{created['id']}").json()
    assert sheet["hp"]["temporary"] == 4


def test_adjust_hp_unknown_character_is_404(client: TestClient) -> None:
    response = client.patch(
        "/api/characters/00000000-0000-0000-0000-000000000000/hp", json={"delta": -1}
    )
    assert response.status_code == 404


def test_mock_character_fixtures_still_served(client: TestClient) -> None:
    response = client.get("/api/characters/1")
    assert response.status_code == 200
    assert response.json()["name"] == "Elyra Silberauge"


def test_create_character_persists_known_spells_for_spontaneous_class(
    client: TestClient, db_session: Session
) -> None:
    user_id = _create_user(client)
    race_id = _elf_race_id(client, db_session)
    base_class_id, spells = _spells_by_class(client, db_session, "Hexenmeister")

    picked = [spells["Licht"], spells["Kleiner Trick"], spells["Magisches Geschoss"], spells["Schild"]]
    response = client.post(
        "/api/characters",
        json=_character_payload(
            user_id,
            race_id,
            db_session,
            classes=[{"class_name": "Hexenmeister", "level": 1}],
            spell_ids={base_class_id: picked},
        ),
    )
    assert response.status_code == 201
    assert set(response.json()["spell_ids"][base_class_id]) == set(picked)


def test_create_character_rejects_spontaneous_spell_over_grade_budget(
    client: TestClient, db_session: Session
) -> None:
    user_id = _create_user(client)
    race_id = _elf_race_id(client, db_session)
    base_class_id, spells = _spells_by_class(client, db_session, "Hexenmeister")

    # Hexenmeister known-count cap at level 1 is 2 grade-1 spells; picking 3.
    picked = [spells["Magisches Geschoss"], spells["Schild"], spells["Farbenstrahl"]]
    response = client.post(
        "/api/characters",
        json=_character_payload(
            user_id,
            race_id,
            db_session,
            classes=[{"class_name": "Hexenmeister", "level": 1}],
            spell_ids={base_class_id: picked},
        ),
    )
    assert response.status_code == 422


def test_create_character_persists_arcane_prepared_spellbook_with_all_cantrips(
    client: TestClient, db_session: Session
) -> None:
    user_id = _create_user(client)
    race_id = _elf_race_id(client, db_session)
    base_class_id, spells = _spells_by_class(client, db_session, "Magier")

    cantrips = _cantrip_ids(client, "Magier")
    grade1_picks = [spells["Magisches Geschoss"], spells["Schild"]]
    ability_scores = dict(DEFAULT_ABILITY_SCORES, IN=14)  # +2 mod -> budget 2+2=4
    response = client.post(
        "/api/characters",
        json=_character_payload(
            user_id,
            race_id,
            db_session,
            classes=[{"class_name": "Magier", "level": 1}],
            ability_scores=ability_scores,
            spell_ids={base_class_id: cantrips + grade1_picks},
        ),
    )
    assert response.status_code == 201
    assert set(response.json()["spell_ids"][base_class_id]) == set(cantrips + grade1_picks)


def test_create_character_rejects_arcane_prepared_missing_cantrip(
    client: TestClient, db_session: Session
) -> None:
    user_id = _create_user(client)
    race_id = _elf_race_id(client, db_session)
    base_class_id, spells = _spells_by_class(client, db_session, "Magier")

    incomplete_cantrips = [spells["Licht"]]  # missing Kleiner Trick / Widerstand
    response = client.post(
        "/api/characters",
        json=_character_payload(
            user_id,
            race_id,
            db_session,
            classes=[{"class_name": "Magier", "level": 1}],
            spell_ids={base_class_id: incomplete_cantrips},
        ),
    )
    assert response.status_code == 422


def test_create_character_rejects_arcane_prepared_over_budget(client: TestClient, db_session: Session) -> None:
    user_id = _create_user(client)
    race_id = _elf_race_id(client, db_session)
    base_class_id, spells = _spells_by_class(client, db_session, "Magier")

    cantrips = _cantrip_ids(client, "Magier")
    # Elf grants +2 IN (mod +1) -> budget 2+1=3 grade-1 picks; submitting 4.
    grade1_picks = [
        spells["Magisches Geschoss"],
        spells["Schild"],
        spells["Farbenstrahl"],
        spells["Schlaf"],
    ]
    response = client.post(
        "/api/characters",
        json=_character_payload(
            user_id,
            race_id,
            db_session,
            classes=[{"class_name": "Magier", "level": 1}],
            spell_ids={base_class_id: cantrips + grade1_picks},
        ),
    )
    assert response.status_code == 422


def test_create_character_rejects_arcane_prepared_inaccessible_grade(
    client: TestClient, db_session: Session
) -> None:
    user_id = _create_user(client)
    race_id = _elf_race_id(client, db_session)
    base_class_id, spells = _spells_by_class(client, db_session, "Magier")

    cantrips = _cantrip_ids(client, "Magier")
    # Nebelwolke is grade 2, not accessible until class level 3.
    response = client.post(
        "/api/characters",
        json=_character_payload(
            user_id,
            race_id,
            db_session,
            classes=[{"class_name": "Magier", "level": 1}],
            spell_ids={base_class_id: cantrips + [spells["Nebelwolke"]]},
        ),
    )
    assert response.status_code == 422


def test_create_character_rejects_spell_not_on_class_list(client: TestClient, db_session: Session) -> None:
    user_id = _create_user(client)
    race_id = _elf_race_id(client, db_session)
    base_class_id, spells = _spells_by_class(client, db_session, "Magier")
    _, mystiker_spells = _spells_by_class(client, db_session, "Mystiker")

    response = client.post(
        "/api/characters",
        json=_character_payload(
            user_id,
            race_id,
            db_session,
            classes=[{"class_name": "Magier", "level": 1}],
            spell_ids={base_class_id: [mystiker_spells["Segnen"]]},
        ),
    )
    assert response.status_code == 422


def test_create_character_rejects_spell_ids_for_divine_prepared_class(
    client: TestClient, db_session: Session
) -> None:
    user_id = _create_user(client)
    race_id = _elf_race_id(client, db_session)
    _, mystiker_spells = _spells_by_class(client, db_session, "Mystiker")
    # Waldläufer (the default payload class) is divine-prepared -- full list,
    # no known-spell picking at all.
    classes = client.get("/api/classes").json()
    waldlaeufer_id = next(c["id"] for c in classes if c["name"] == "Waldläufer")

    response = client.post(
        "/api/characters",
        json=_character_payload(
            user_id, race_id, db_session, spell_ids={waldlaeufer_id: [mystiker_spells["Segnen"]]}
        ),
    )
    assert response.status_code == 422


def _magier_character(client: TestClient, db_session: Session, extra_grade1: list[str] | None = None) -> tuple[dict, str, dict[str, str]]:
    user_id = _create_user(client)
    race_id = _elf_race_id(client, db_session)
    base_class_id, spells = _spells_by_class(client, db_session, "Magier")
    cantrips = _cantrip_ids(client, "Magier")
    picked = cantrips + (extra_grade1 or [spells["Magisches Geschoss"]])
    created = client.post(
        "/api/characters",
        json=_character_payload(
            user_id,
            race_id,
            db_session,
            classes=[{"class_name": "Magier", "level": 1}],
            spell_ids={base_class_id: picked},
        ),
    ).json()
    return created, base_class_id, spells


def test_add_spell_to_spellbook(client: TestClient, db_session: Session) -> None:
    character, base_class_id, spells = _magier_character(client, db_session)

    response = client.post(
        f"/api/characters/{character['id']}/spellbook",
        json={"base_class_id": base_class_id, "spell_id": spells["Schild"]},
    )
    assert response.status_code == 201
    assert spells["Schild"] in response.json()["spell_ids"][base_class_id]


def test_add_spell_to_spellbook_rejects_already_known(client: TestClient, db_session: Session) -> None:
    character, base_class_id, spells = _magier_character(client, db_session)

    response = client.post(
        f"/api/characters/{character['id']}/spellbook",
        json={"base_class_id": base_class_id, "spell_id": spells["Magisches Geschoss"]},
    )
    assert response.status_code == 422


def test_add_spell_to_spellbook_rejects_inaccessible_grade(client: TestClient, db_session: Session) -> None:
    character, base_class_id, spells = _magier_character(client, db_session)

    response = client.post(
        f"/api/characters/{character['id']}/spellbook",
        json={"base_class_id": base_class_id, "spell_id": spells["Nebelwolke"]},
    )
    assert response.status_code == 422


def test_add_spell_to_spellbook_rejects_non_arcane_prepared_class(client: TestClient, db_session: Session) -> None:
    user_id = _create_user(client)
    race_id = _elf_race_id(client, db_session)
    base_class_id, spells = _spells_by_class(client, db_session, "Hexenmeister")
    picked = [spells["Licht"], spells["Kleiner Trick"], spells["Magisches Geschoss"]]
    character = client.post(
        "/api/characters",
        json=_character_payload(
            user_id,
            race_id,
            db_session,
            classes=[{"class_name": "Hexenmeister", "level": 1}],
            spell_ids={base_class_id: picked},
        ),
    ).json()

    response = client.post(
        f"/api/characters/{character['id']}/spellbook",
        json={"base_class_id": base_class_id, "spell_id": spells["Schild"]},
    )
    assert response.status_code == 422


def test_remove_spell_from_spellbook(client: TestClient, db_session: Session) -> None:
    character, base_class_id, spells = _magier_character(client, db_session)

    response = client.delete(f"/api/characters/{character['id']}/spellbook/{spells['Licht']}")
    assert response.status_code == 204

    # GET /api/characters/{id} now returns the sheet's display shape (app/
    # sheet.py) rather than a composition echo — verify persistence directly.
    db_character = db_session.get(Character, character["id"])
    assert spells["Licht"] not in db_character.spell_ids[base_class_id]


def test_remove_unknown_spell_from_spellbook_is_404(client: TestClient, db_session: Session) -> None:
    character, _, spells = _magier_character(client, db_session)

    response = client.delete(f"/api/characters/{character['id']}/spellbook/{spells['Nebelwolke']}")
    assert response.status_code == 404
