"""Animal companions as `Character` rows — roadmap slice 10, step 2b
(`app/companions.py`, `scripts/import_companion_species.py`)."""

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import CharacterClassOption

from test_characters import _character_payload, _create_user, _human_race_id, _race_id


def _master(client: TestClient, db_session: Session, classes: list[dict], race: str = "Mensch", **overrides) -> dict:
    race_id = _human_race_id(client, db_session) if race == "Mensch" else _race_id(client, db_session, race)
    payload = _character_payload(_create_user(client), race_id, db_session, classes=classes, **overrides)
    if race == "Mensch":
        payload["flex_ability"] = "CH"
    response = client.post("/api/characters", json=payload)
    assert response.status_code == 201, response.text
    return client.get(f"/api/characters/{response.json()['id']}").json()


def _druide(client: TestClient, db_session: Session, level: int) -> dict:
    return _master(client, db_session, [{"class_name": "Druide", "level": level, "options": {"bond": ["Tiergefährte"]}}])


def _slot(sheet: dict) -> dict:
    track = next(t for t in sheet["companionLevels"] if t["track"] == "animal_companion")
    return track["slots"][0]


def _species_id(slot: dict, name: str) -> str:
    return next(s["id"] for s in slot["species"] if s["name"].startswith(name))


def _add(client: TestClient, master: dict, species: str, hit_points: list[int] | None = None, **extra):
    slot = _slot(master)
    body = {
        "species_id": _species_id(slot, species),
        "name": species,
        "hit_points": hit_points if hit_points is not None else [5] * slot["hitDice"],
        **extra,
    }
    return client.post(f"/api/characters/{master['id']}/companions", json=body)


def _companion(client: TestClient, master: dict, species: str, **extra) -> dict:
    response = _add(client, master, species, **extra)
    assert response.status_code == 201, response.text
    return client.get(f"/api/characters/{response.json()['id']}").json()


def _attack(sheet: dict, name: str) -> dict:
    return next(a for a in sheet["weaponAttacks"] if a["name"] == name)


def _value(entries: list[dict], key: str) -> str:
    return next(e for e in entries if e["key"] == key)["value"]


def test_species_and_pseudo_class_stay_out_of_player_choices(client: TestClient, db_session: Session) -> None:
    races = client.get("/api/races").json()
    assert "Wolf" not in {r["name"] for r in races}
    classes = client.get("/api/classes").json()
    assert "Tiergefährte" not in {c["name"] for c in classes}

    payload = _character_payload(
        _create_user(client), _human_race_id(client, db_session), db_session, classes=[{"class_name": "Tiergefährte", "level": 1}]
    )
    payload["flex_ability"] = "CH"
    assert client.post("/api/characters", json=payload).status_code == 422


def test_druide_has_one_companion_slot_with_all_species(client: TestClient, db_session: Session) -> None:
    slot = _slot(_druide(client, db_session, 1))

    assert slot["level"] == 1
    assert slot["hitDice"] == 2
    # The PRD's 17 plus the house-rule Säbelzahnkatze.
    assert len(slot["species"]) == 18
    assert slot["companion"] is None


def test_level_1_wolf_companion_sheet(client: TestClient, db_session: Session) -> None:
    master = _druide(client, db_session, 1)
    wolf = _companion(client, master, "Wolf")

    assert wolf["kind"] == "companion"
    assert wolf["companion"]["master"] == {"id": master["id"], "name": master["name"]}
    assert wolf["companion"]["effectiveLevel"] == 1
    assert wolf["companion"]["hitDice"] == 2
    assert wolf["companion"]["expectedHitDice"] == 2
    assert wolf["companion"]["bonusTricks"] == 1
    assert wolf["companion"]["breakdown"][0]["detail"] == "Druide 1"
    assert {"Verbindung", "Zauber teilen"} <= {f["name"] for f in wolf["classFeatures"]}
    assert "Entrinnen" not in {f["name"] for f in wolf["classFeatures"]}
    assert "Geruchssinn" in {r["name"] for r in wolf["raceAbilities"]}
    assert wolf["speed"] == "15 m"
    assert wolf["hp"]["max"] == 5 + 5 + 2 * 2  # two HD, KO 15
    # ¾ BAB of 2 HD, good Fort/Ref, poor Will.
    assert _value(wolf["combat"], "bab") == "+1"
    assert _value(wolf["saves"], "fort") == "+5"
    assert _value(wolf["saves"], "ref") == "+5"
    assert _value(wolf["saves"], "will") == "+1"
    assert wolf["armorClass"] == 10 + 2 + 2
    bite = _attack(wolf, "Biss")
    # Sole natural attack: full BAB, 1½ × ST (+1 -> +1).
    assert bite["attackBonus"] == "+2"
    assert bite["damage"] == "1W6+1 H/S/W"
    assert bite["note"] == "Zu Fall bringen"
    assert _value(wolf["combat"], "size").startswith("Mittelgroß")

    master_again = client.get(f"/api/characters/{master['id']}").json()
    assert _slot(master_again)["companion"] == {"id": wolf["id"], "name": "Wolf"}


def test_wolf_advancement_at_7_or_dex_con_instead(client: TestClient, db_session: Session) -> None:
    advanced = _companion(client, _druide(client, db_session, 7), "Wolf")
    plain = _companion(client, _druide(client, db_session, 7), "Wolf", advancement_choice="dex_con")

    def score(sheet: dict, key: str) -> int:
        return next(a for a in sheet["abilities"] if a["key"] == key)["score"]

    assert advanced["companion"]["advanced"] is True
    assert _value(advanced["combat"], "size").startswith("Groß")
    assert score(advanced, "ST") == 13 + 8 + 2  # species advancement + table ST/GE
    assert _attack(advanced, "Biss")["damage"].startswith("1W8")
    natural = next(e for e in advanced["armorClassBreakdown"] if e["label"] == "Natürliche Rüstung")
    assert natural["value"] == 2 + 2 + 4

    assert plain["companion"]["advanced"] is False
    assert _value(plain["combat"], "size").startswith("Mittelgroß")
    assert score(plain, "GE") == 15 + 2 + 2
    assert score(plain, "KO") == 15 + 2
    assert _attack(plain, "Biss")["damage"].startswith("1W6")


def test_pony_hooves_are_primary_horse_hooves_secondary(client: TestClient, db_session: Session) -> None:
    pony = _companion(client, _druide(client, db_session, 1), "Pony")
    horse = _companion(client, _druide(client, db_session, 1), "Pferd")

    # Pony: one kind of attack -> primary despite hooves; BAB 1 + ST 13 (+1).
    assert _attack(pony, "Hufe")["attackBonus"] == "+2/+2"
    # Pferd (Groß, −1): bite primary, hooves secondary (−5, ½ ST); ST 16 (+3).
    assert _attack(horse, "Biss")["attackBonus"] == "+3"
    assert _attack(horse, "Hufe")["attackBonus"] == "-2/-2"
    assert _attack(horse, "Hufe")["damage"] == "1W6+1 W"
    assert _attack(horse, "Hufe")["hand"] == "Naturangriff (sekundär)"


def test_companion_creation_is_validated(client: TestClient, db_session: Session) -> None:
    master = _druide(client, db_session, 1)
    assert _add(client, master, "Wolf", hit_points=[5]).status_code == 422
    assert _add(client, master, "Wolf", hit_points=[9, 5]).status_code == 422
    assert _add(client, master, "Wolf").status_code == 201
    # The slot is taken now.
    assert _add(client, master, "Hund").status_code == 422

    fighter = _master(client, db_session, [{"class_name": "Kämpfer", "level": 1}])
    response = client.post(
        f"/api/characters/{fighter['id']}/companions",
        json={"species_id": _species_id(_slot(master), "Hund"), "name": "Rex", "hit_points": [5, 5]},
    )
    assert response.status_code == 422


def test_small_paladin_gets_a_pony_not_a_horse(client: TestClient, db_session: Session) -> None:
    paladin = _master(
        client, db_session, [{"class_name": "Paladin", "level": 5, "options": {"divine_bond": ["Reittier"]}}], race="Halbling"
    )
    names = {s["name"] for s in _slot(paladin)["species"]}

    assert {"Pony", "Wildschwein", "Hund", "Kamel"} <= names
    assert "Pferd" not in names
    assert _slot(paladin)["level"] == 5


def test_companion_is_listed_with_its_master_and_deleted_with_it(client: TestClient, db_session: Session) -> None:
    master = _druide(client, db_session, 1)
    wolf = _companion(client, master, "Wolf")

    characters = client.get(f"/api/users/{_owner(client, master['id'])}/characters").json()
    by_id = {c["id"]: c for c in characters}
    assert by_id[wolf["id"]]["master_character_id"] == master["id"]
    assert by_id[master["id"]]["master_character_id"] is None

    assert client.delete(f"/api/characters/{master['id']}").status_code == 204
    assert client.get(f"/api/characters/{wolf['id']}").status_code == 404


def _owner(client: TestClient, character_id: str) -> str:
    """The user id of a character (the sheet payload doesn't carry it)."""
    for user in client.get("/api/users").json():
        if any(c["id"] == character_id for c in client.get(f"/api/users/{user['id']}/characters").json()):
            return user["id"]
    raise AssertionError("owner not found")


def test_companion_without_entitlement_is_kept_and_flagged(client: TestClient, db_session: Session) -> None:
    master = _druide(client, db_session, 3)
    wolf = _companion(client, master, "Wolf")

    for option in db_session.scalars(select(CharacterClassOption).where(CharacterClassOption.group_key == "bond")):
        db_session.delete(option)
    db_session.flush()

    sheet = client.get(f"/api/characters/{wolf['id']}").json()
    assert sheet["companion"]["orphaned"] is True
    assert sheet["companion"]["effectiveLevel"] is None
    # Stats from the highest table row its 3 HD still match (level 3).
    assert "Entrinnen" in {f["name"] for f in sheet["classFeatures"]}


# ---- step 3: open HD, HD sync, companion level-up, monster feats, channel ----

_SKILL_IDS: dict[str, str] = {}


def _skill_id(client: TestClient, name: str) -> str:
    if not _SKILL_IDS:
        _SKILL_IDS.update({skill["name"]: skill["id"] for skill in client.get("/api/skills").json()})
    return _SKILL_IDS[name]


def _feat_id(client: TestClient, name: str) -> str:
    return next(f["id"] for f in client.get("/api/feats").json() if f["name"] == name)


def _progression(client: TestClient, character_id: str) -> dict:
    return client.get(f"/api/characters/{character_id}/progression").json()


def _complete(client: TestClient, companion_id: str, **body) -> object:
    progression = _progression(client, companion_id)
    payload = {"target": {"mode": "existing", "base_class_id": progression["classes"][0]["id"]}, **body}
    return client.post(f"/api/characters/{companion_id}/level-up", json=payload)


def _fill_open_hit_dice(client: TestClient, companion_id: str, feats_by_hit_die: dict[int, list[dict]] | None = None):
    """Completes every open HD with one Wahrnehmung rank, HP 5 where still
    open, ST increases and the given feats (`{hit_die: [FeatSelection]}`)."""
    feats_by_hit_die = feats_by_hit_die or {}
    while (progression := _progression(client, companion_id))["companion"]["openHitDie"] is not None:
        hit_die = progression["companion"]["openHitDie"]
        response = _complete(
            client,
            companion_id,
            hit_points=5 if progression["companion"]["hitPointsOpen"] else None,
            ability_increase="ST" if hit_die % 4 == 0 else None,
            skill_ranks=[{"skill_id": _skill_id(client, "Wahrnehmung"), "ranks": 1}],
            feats=feats_by_hit_die.get(hit_die, []),
        )
        assert response.status_code == 201, (hit_die, response.text)


def test_new_companion_starts_with_open_hit_dice(client: TestClient, db_session: Session) -> None:
    wolf = _companion(client, _druide(client, db_session, 1), "Wolf")

    assert wolf["companion"]["openHitDice"] == 2
    assert wolf["companion"]["openHitPoints"] == 0
    progression = _progression(client, wolf["id"])
    assert progression["classes"][0]["className"] == "Tiergefährte"
    assert progression["classes"][0]["level"] == 0
    assert progression["companion"]["openHitDie"] == 1
    assert progression["companion"]["firstFeat"] is True
    assert progression["companion"]["hitPointsOpen"] is False
    # IN 2: only the nine "Tierfertigkeiten".
    allowed = set(progression["companion"]["allowedSkillIds"])
    assert len(allowed) == 9
    assert _skill_id(client, "Überlebenskunst") in allowed
    assert _skill_id(client, "Diplomatie") not in allowed
    assert set(progression["companion"]["classDef"]["classSkills"]) < allowed
    assert len(progression["companion"]["recommendedFeatIds"]) == 29


def test_completing_open_hit_dice_in_order(client: TestClient, db_session: Session) -> None:
    wolf = _companion(client, _druide(client, db_session, 1), "Wolf")
    wahrnehmung = [{"skill_id": _skill_id(client, "Wahrnehmung"), "ranks": 1}]

    # HD 1 already has its HP from creation; 1 skill point (2 + IN −4, min. 1).
    assert _complete(client, wolf["id"], hit_points=5, skill_ranks=wahrnehmung).status_code == 422
    too_many = [{"skill_id": _skill_id(client, "Wahrnehmung"), "ranks": 2}]
    assert _complete(client, wolf["id"], skill_ranks=too_many).status_code == 422
    diplomatie = [{"skill_id": _skill_id(client, "Diplomatie"), "ranks": 1}]
    assert _complete(client, wolf["id"], skill_ranks=diplomatie).status_code == 422
    # First feat: no GAB +1 prerequisite (Heftiger Angriff).
    power_attack = [{"feat_id": _feat_id(client, "Heftiger Angriff")}]
    assert _complete(client, wolf["id"], skill_ranks=wahrnehmung, feats=power_attack).status_code == 422
    dodge = [{"feat_id": _feat_id(client, "Ausweichen")}]
    assert _complete(client, wolf["id"], skill_ranks=wahrnehmung, feats=dodge).status_code == 201

    # HD 2: no new feat.
    assert _complete(client, wolf["id"], skill_ranks=wahrnehmung, feats=dodge).status_code == 422
    assert _complete(client, wolf["id"], skill_ranks=wahrnehmung).status_code == 201
    assert _complete(client, wolf["id"], skill_ranks=wahrnehmung).status_code == 422  # nothing open

    sheet = client.get(f"/api/characters/{wolf['id']}").json()
    assert sheet["companion"]["openHitDice"] == 0
    assert "Ausweichen" in {f["name"] for f in sheet["feats"]}
    perception = next(s for s in sheet["skills"] if s["label"] == "Wahrnehmung")
    assert {"label": "Ränge", "value": 2} in perception["breakdown"]


def test_companion_feat_list_uses_the_open_hit_die(client: TestClient, db_session: Session) -> None:
    wolf = _companion(client, _druide(client, db_session, 1), "Wolf")
    feats = {f["name"]: f for f in client.get(f"/api/feats?character_id={wolf['id']}").json()}

    # GAB at HD 1 is +0 although the wolf already has 2 HD (GAB +1).
    assert "Heftiger Angriff" not in feats
    assert feats["Ausweichen"]["recommended"] is True
    assert feats["Verbesserte Natürliche Rüstung"]["recommended"] is True
    assert feats["Verbesserte Natürliche Rüstung"]["isRepeatable"] is True
    assert feats["Kampfreflexe"]["recommended"] is True
    assert feats["Wachsamkeit"]["recommended"] is False
    # Verbesserter Natürlicher Angriff needs GAB +4, Mehrfachangriff three attacks.
    assert "Verbesserter Natürlicher Angriff" not in feats
    assert "Mehrfachangriff" not in feats


def test_master_level_up_syncs_companion_hit_dice(client: TestClient, db_session: Session) -> None:
    master = _druide(client, db_session, 1)
    wolf = _companion(client, master, "Wolf")
    druide_id = next(c["id"] for c in _progression(client, master["id"])["classes"])

    response = client.post(
        f"/api/characters/{master['id']}/level-up",
        json={"target": {"mode": "existing", "base_class_id": druide_id}, "hit_points": 4, "favored_class_bonus": "hp"},
    )
    assert response.status_code == 201, response.text

    sheet = client.get(f"/api/characters/{wolf['id']}").json()
    assert sheet["companion"]["hitDice"] == 3
    assert sheet["companion"]["expectedHitDice"] == 3
    assert sheet["companion"]["openHitDice"] == 3
    assert sheet["companion"]["openHitPoints"] == 1
    assert _value(sheet["combat"], "bab") == "+2"

    _fill_open_hit_dice(client, wolf["id"], {1: [{"feat_id": _feat_id(client, "Ausweichen")}],
                                             3: [{"feat_id": _feat_id(client, "Heftiger Angriff")}]})
    sheet = client.get(f"/api/characters/{wolf['id']}").json()
    assert sheet["hp"]["max"] == 5 + 5 + 5 + 3 * 2
    assert {"Ausweichen", "Heftiger Angriff"} <= {f["name"] for f in sheet["feats"]}


def test_improved_natural_armor_is_repeatable(client: TestClient, db_session: Session) -> None:
    wolf = _companion(client, _druide(client, db_session, 4), "Wolf")  # 4 HD, natural armor 2 + 2
    armor = {"feat_id": _feat_id(client, "Verbesserte Natürliche Rüstung")}
    _fill_open_hit_dice(client, wolf["id"], {1: [armor], 3: [armor]})

    sheet = client.get(f"/api/characters/{wolf['id']}").json()
    entry = next(e for e in sheet["armorClassBreakdown"] if e["label"] == "Verbesserte Natürliche Rüstung")
    assert entry["value"] == 2


def test_improved_natural_attack_and_multiattack(client: TestClient, db_session: Session) -> None:
    # Druide 8: 7 HD, GAB +5 at HD 7 -> Verbesserter Natürlicher Angriff (GAB +4).
    horse = _companion(client, _druide(client, db_session, 8), "Pferd", advancement_choice="dex_con")
    assert _attack(horse, "Biss")["damage"].startswith("1W4")
    improved = {"feat_id": _feat_id(client, "Verbesserter Natürlicher Angriff"), "chosen_manifestation": "Biss"}
    wrong = {"feat_id": improved["feat_id"], "chosen_manifestation": "Schwanz"}
    progression = _progression(client, horse["id"])
    while progression["companion"]["openHitDie"] < 7:
        _complete(client, horse["id"], skill_ranks=[{"skill_id": _skill_id(client, "Wahrnehmung"), "ranks": 1}],
                  ability_increase="ST" if progression["companion"]["openHitDie"] % 4 == 0 else None)
        progression = _progression(client, horse["id"])
    names = next(f for f in client.get(f"/api/feats?character_id={horse['id']}").json()
                 if f["name"] == "Verbesserter Natürlicher Angriff")["manifestationOptions"]
    assert names == ["Biss", "Hufe"]
    rank = [{"skill_id": _skill_id(client, "Wahrnehmung"), "ranks": 1}]
    assert _complete(client, horse["id"], skill_ranks=rank, feats=[wrong]).status_code == 422
    assert _complete(client, horse["id"], skill_ranks=rank, feats=[improved]).status_code == 201
    sheet = client.get(f"/api/characters/{horse['id']}").json()
    assert _attack(sheet, "Biss")["damage"].startswith("1W6")
    assert _attack(sheet, "Hufe")["damage"].startswith("1W6")  # unchanged

    # Druide 9: the companion's Mehrfachangriff, horse has bite + 2 hooves.
    horse9 = client.get(f"/api/characters/{_companion(client, _druide(client, db_session, 9), 'Pferd')['id']}").json()
    bite, hooves = _attack(horse9, "Biss"), _attack(horse9, "Hufe")
    assert int(bite["attackBonus"]) - int(hooves["attackBonus"].split("/")[0]) == 2
    summary = next(f for f in horse9["classFeatures"] if f["name"] == "Mehrfachangriff")["summary"]
    assert summary.startswith("Bonustalent Mehrfachangriff")
    wolf9 = client.get(f"/api/characters/{_companion(client, _druide(client, db_session, 9), 'Wolf')['id']}").json()
    summary = next(f for f in wolf9["classFeatures"] if f["name"] == "Mehrfachangriff")["summary"]
    assert summary.startswith("1 zusätzlicher Angriff")


def test_hingabe_and_verbindung_summaries(client: TestClient, db_session: Session) -> None:
    wolf = _companion(client, _druide(client, db_session, 6), "Wolf")
    features = {f["name"]: f for f in wolf["classFeatures"]}
    assert features["Verbindung"]["summary"].startswith("Meister: +4")
    assert features["Hingabe"]["summary"] == "+4 Moral auf Willenswürfe gegen Verzauberungen"
    assert features["Hingabe"]["hasHandler"] is True


def test_katzenvolk_and_ork_druide_favored_class_bonuses_reach_the_companion(
    client: TestClient, db_session: Session
) -> None:
    cat_master = _master(
        client, db_session, [{"class_name": "Druide", "level": 2, "options": {"bond": ["Tiergefährte"]}}],
        race="Katzenvolk", favored_class_bonus={"1": "Katzenvolk (Druide)", "2": "Katzenvolk (Druide)"},
    )
    cat_wolf = _companion(client, cat_master, "Wolf")
    plain_wolf = _companion(client, _druide(client, db_session, 2), "Wolf")
    assert cat_wolf["hp"]["max"] == plain_wolf["hp"]["max"] + 2

    ork_master = _master(
        client, db_session, [{"class_name": "Druide", "level": 2, "options": {"bond": ["Tiergefährte"]}}],
        race="Ork", favored_class_bonus={"1": "Ork (Druide)", "2": "Ork (Druide)"},
    )
    ork_wolf = _companion(client, ork_master, "Wolf")
    # +½ per pick: 2 picks -> +1 on the bite (1W6+1 -> 1W6+2).
    assert _attack(ork_wolf, "Biss")["damage"] == "1W6+2 H/S/W"
    assert _attack(plain_wolf, "Biss")["damage"] == "1W6+1 H/S/W"


def test_waldlaeufer_companion_shares_favored_enemies(client: TestClient, db_session: Session) -> None:
    ranger = _master(
        client,
        db_session,
        [{"class_name": "Waldläufer", "level": 4, "options": {"hunter_bond": ["Tiergefährte"], "enemy": ["Tiere"],
                                                               "terrain": ["Ebene"]}}],
    )
    wolf = _companion(client, ranger, "Wolf")
    notes = wolf["companion"]["masterNotes"]
    assert "Erzfeinde des Waldläufers (Boni geteilt): Tiere" in notes
    assert "Bevorzugtes Gelände des Waldläufers (Boni geteilt): Ebene" in notes


def test_paladin_mount_has_at_least_in_6_and_may_learn_any_skill(client: TestClient, db_session: Session) -> None:
    paladin = _master(client, db_session, [{"class_name": "Paladin", "level": 5, "options": {"divine_bond": ["Reittier"]}}])
    horse = _companion(client, paladin, "Pferd")

    assert next(a for a in horse["abilities"] if a["key"] == "IN")["score"] == 6
    assert _progression(client, horse["id"])["companion"]["allowedSkillIds"] is None


def test_mystiker_mount_has_at_least_in_6(client: TestClient, db_session: Session) -> None:
    mystiker = _master(
        client,
        db_session,
        [{"class_name": "Mystiker", "level": 1, "options": {"mystery": ["Natur"], "revelation": ["Gebundenes Reittier"]}}],
    )
    track = next(t for t in mystiker["companionLevels"] if t["track"] == "animal_companion")
    species_id = next(s["id"] for s in track["slots"][0]["species"] if s["name"] == "Pferd")
    response = client.post(
        f"/api/characters/{mystiker['id']}/companions",
        json={"species_id": species_id, "name": "Pferd", "hit_points": [5, 5]},
    )
    assert response.status_code == 201, response.text
    horse = client.get(f"/api/characters/{response.json()['id']}").json()
    assert next(a for a in horse["abilities"] if a["key"] == "IN")["score"] == 6


def _equip_armor(client: TestClient, character_id: str, armor_name: str) -> dict:
    item_id = next(i["id"] for i in client.get("/api/items").json() if i["name"] == armor_name)
    added = client.post(f"/api/characters/{character_id}/gear", json={"item_id": item_id, "quantity": 1})
    assert added.status_code == 201, added.text
    response = client.put(f"/api/characters/{character_id}/slots/ruestung", json={"item_id": item_id})
    assert response.status_code == 200, response.text
    return client.get(f"/api/characters/{character_id}").json()


def test_barding_slows_a_mount_and_grounds_a_flyer(client: TestClient, db_session: Session) -> None:
    horse = _companion(client, _druide(client, db_session, 1), "Pferd")
    assert horse["speed"] == "15 m"
    light = _equip_armor(client, horse["id"], "Lederrüstung")
    assert light["speed"] == "15 m"
    medium = _equip_armor(client, horse["id"], "Schuppenpanzer")
    assert medium["speed"] == "10,5 m"
    armor = next(e for e in medium["armorClassBreakdown"] if e["label"] == "Schuppenpanzer")
    assert armor["value"] == 5

    bird = _companion(client, _druide(client, db_session, 1), "Vogel")
    assert bird["flySpeed"] is not None
    assert _equip_armor(client, bird["id"], "Schuppenpanzer")["flySpeed"] is None


def test_tiny_wearer_gets_half_the_armor_bonus(client: TestClient, db_session: Session) -> None:
    from test_familiars import _familiar, _magier

    cat = _familiar(client, _magier(client, db_session, 1), "Katze")
    armored = _equip_armor(client, cat["id"], "Kettenhemd")
    entry = next(e for e in armored["armorClassBreakdown"] if e["label"] == "Kettenhemd")
    assert entry["value"] == 2  # 4 halved


def test_saebelzahnkatze_house_rule(client: TestClient, db_session: Session) -> None:
    """House rule (requirements_v2.md, "Hausregeln"): the Säbelzahnkatze
    from Ausbauregeln X: Wildnis is a companion species."""
    cat = _companion(client, _druide(client, db_session, 1), "Säbelzahnkatze")
    claws = _attack(cat, "Klauen")
    assert claws["attackBonus"] == "+3/+3"  # GAB 1 + ST 15 (+2)
    assert claws["damage"] == "1W4+2 H/W"
    assert claws["note"] == "plus Ergreifen"
    bite = _attack(cat, "Säbelzahnbiss")
    assert bite["hand"] == "Naturangriff (alternativ)"
    assert bite["damage"].startswith("1W10")
    assert {"Ergreifen", "Säbelzahnbiss", "Geruchssinn"} <= {r["name"] for r in cat["raceAbilities"]}

    advanced = _companion(client, _druide(client, db_session, 7), "Säbelzahnkatze")
    assert _attack(advanced, "Säbelzahnbiss")["damage"].startswith("2W8")
    assert "Anspringen" in {r["name"] for r in advanced["raceAbilities"]}
