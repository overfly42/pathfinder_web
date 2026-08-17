"""Import the nine Orc-specific feats from
http://prd.5footstep.de/AusbauregelnIIIVoelker/UngewoehnlicheVoelker/Orks
("Talente der Orks") into `base_feats.json` and the `BaseFeatRequired*`
prerequisite tables, following `build_feats_seed.py`'s row shapes.

Feat types were not given on the German PRD page (all nine are listed under
one flat "Talente der Orks" heading with no per-feat type tag) — each type
below was instead cross-checked against the feat's official English name/
type on the Advanced Race Guide Orc page (d20pfsrd/aonprd): Blöße geben =
Reverse-Feint (Combat), Blut kochen lassen = Foment the Blood (General),
Einschüchternder Schlag = Bullying Blow (Combat), Einzelkind = Born Alone
(General), Entschlossener Wüter = Resolute Rager (General), Fallenbrecher =
Trap Wrecker (General), Nachtragender Kämpfer = Grudge Fighter (Combat),
Orkische Waffenexpertise = Orc Weapon Expertise (Combat), Wilder Angriff =
Ferocious Action (General) — same source cross-check confirmed every
prerequisite transcribed below against the official English "Prerequisites"
line, not just the German wiki text.

"Entschlossener Wüter" requires "Klassenmerkmal Kampfrausch" — Kampfrausch
is seeded as two distinct `BaseClassAbility` rows (one for Barbar, one for
Entfesselter Barbar, since both classes track their own rage resource) —
OR-grouped via a shared `group_id` so either satisfies the prerequisite,
per `BaseFeatRequiredClassAbility`'s documented OR-group semantics.

Run with the project venv active (this only writes the fixture JSON files,
it doesn't touch the database — run the seed script afterward):
    cd backend && python scripts/import_ork_feats.py
    python -m app.seed.feat_seed
"""

from __future__ import annotations

import json
import uuid
from pathlib import Path

FIXTURES = Path(__file__).resolve().parent.parent / "app" / "fixtures"
SEED_DIR = FIXTURES / "seed"

ID_NAMESPACE = uuid.UUID("2f8a5e6d-9c3b-4a7e-8d1f-6b2c4e9a7d53")

ORK_RACE_ID = "3d007d77-60e2-4f01-b682-8a3a129a49da"

ABHAERTUNG_FEAT_ID = "83419823-fd94-4ef4-b44e-e3645cc88bbc"  # Toughness
HEFTIGER_ANGRIFF_FEAT_ID = "4696cb39-3218-4f95-9d61-d0cef28b4ac0"  # Power Attack

EINSCHUECHTERN_SKILL_ID = "3c60b6e1-8c58-4ed0-9c3a-5e003b9da1cf"
MECHANISMUS_AUSSCHALTEN_SKILL_ID = "6d850adc-a635-418f-8d72-e7dcbb878225"

ENERGIE_FOKUSSIEREN_KLERIKER_ABILITY_ID = "8a562605-e6d6-5093-88ea-20b50de6e597"
KAMPFRAUSCH_BARBAR_ABILITY_ID = "e9414145-7bff-5900-8e07-9174cf937346"
KAMPFRAUSCH_ENTFESSELTER_BARBAR_ABILITY_ID = "ad985f6f-3b03-5861-bccf-a016ebaba4ec"


def uid(*parts: str) -> str:
    return str(uuid.uuid5(ID_NAMESPACE, "|".join(parts)))


# Requirement rows, keyed by kind: "feat", "skill" (ranks), "class_ability",
# "race", "bab". Each entry is (feat_name, kwargs-dict); "group" (optional)
# lets several rows for the same feat OR together.
FEATS: list[dict] = [
    {
        "name": "Blöße geben",
        "description": "Du kannst einen Gegner zu einem Angriff verleiten und dann einen mächtigen "
        "Gegenangriff führen. Als Bewegungsaktion kannst du deine Verteidigung für einen angrenzenden "
        "Gegner offen lassen. Sollte der Gegner dich während seines nächsten Zuges angreifen, erhält "
        "er einen Bonus von +4 auf seinen Angriffswurf. Egal ob er trifft oder nicht, kannst du als "
        "Augenblickliche Aktion einen einzelnen Nahkampfangriff mit einem Bonus von +2 auf den "
        "Angriffswurf gegen ihn ausführen.",
        "type": "combat",
        "prerequisite_text": "Abhärtung, GAB +1, Ork.",
        "requirements": [
            {"kind": "feat", "required_feat_id": ABHAERTUNG_FEAT_ID},
            {"kind": "bab", "minimum_bab": 1},
            {"kind": "race", "race_id": ORK_RACE_ID},
        ],
    },
    {
        "name": "Blut kochen lassen",
        "description": "Du kannst eine Energiewelle entfesseln, welche Orks in einen Blutrausch "
        "treibt. Wenn du Energie fokussierst, kannst du anstelle des normalen Effekts Orks bis zum "
        "Beginn deines nächsten Zuges einen Bonus auf Waffenschadens- und Kritische-"
        "Treffer-Bestätigungswürfe verleihen. Dieser Bonus entspricht der Anzahl an Würfeln, die du "
        "beim Energie fokussieren nutzt. Auf andere Kreaturen im Wirkungsbereich entfaltet dein "
        "Energie fokussieren den normalen Effekt.",
        "type": "general",
        "prerequisite_text": "Klassenmerkmal Energie fokussieren, Ork.",
        "requirements": [
            {"kind": "class_ability", "ability_id": ENERGIE_FOKUSSIEREN_KLERIKER_ABILITY_ID},
            {"kind": "race", "race_id": ORK_RACE_ID},
        ],
    },
    {
        "name": "Einschüchternder Schlag",
        "description": "Du kannst mit einem einfachen Schlag deinen Gegner leichter einschüchtern. Du "
        "kannst als Standard-Aktion einen Nahkampfangriff mit einem Malus von -2 auf den Angriffswurf "
        "ausführen; solltest du deinem Gegner dabei Schaden zufügen, kannst du als Freie Aktion einen "
        "Fertigkeitswurf für Einschüchtern ablegen, um diesen Gegner zu demoralisieren.",
        "type": "combat",
        "prerequisite_text": "Einschüchtern 1 Fertigkeitsrang, Ork.",
        "requirements": [
            {"kind": "skill", "skill_id": EINSCHUECHTERN_SKILL_ID, "minimum_ranks": 1},
            {"kind": "race", "race_id": ORK_RACE_ID},
        ],
    },
    {
        "name": "Einzelkind",
        "description": "Du bist so zäh und bösartig, dass du den Rest deines Wurfes noch im "
        "Mutterleib getötet und verspeist hast. Wenn du einen Gegner mit einem Nahkampfangriff tötest "
        "oder bewusstlos schlägst, erhältst du temporäre Trefferpunkte in Höhe deines KO-Bonus "
        "(Minimum 1) bis zum Beginn deines nächsten Zuges. Dein Gegner darf dabei nicht hilflos sein "
        "oder weniger als die Hälfte deiner Trefferwürfel besitzen.",
        "type": "general",
        "prerequisite_text": "Ork.",
        "requirements": [
            {"kind": "race", "race_id": ORK_RACE_ID},
        ],
    },
    {
        "name": "Entschlossener Wüter",
        "description": "Während du dich im Kampfrausch befindest, befreist du dich schnell von jeder "
        "Angst. Wenn du dich im Kampfrausch befindest, während du einem Furchteffekt unterliegst, der "
        "einen Rettungswurf gestattet, kannst du zu Beginn jedes deiner Züge einen neuen Rettungswurf "
        "gegen diesen Furchteffekt ablegen. Gelingt der Rettungswurf, endet der Furchteffekt.",
        "type": "general",
        "prerequisite_text": "Klassenmerkmal Kampfrausch, Ork.",
        "requirements": [
            {
                "kind": "class_ability",
                "ability_id": KAMPFRAUSCH_BARBAR_ABILITY_ID,
                "group": "kampfrausch",
            },
            {
                "kind": "class_ability",
                "ability_id": KAMPFRAUSCH_ENTFESSELTER_BARBAR_ABILITY_ID,
                "group": "kampfrausch",
            },
            {"kind": "race", "race_id": ORK_RACE_ID},
        ],
    },
    {
        "name": "Fallenbrecher",
        "description": "Du zertrümmerst Fallen, statt sie zu entschärfen. Du kannst versuchen, eine "
        "Falle zu entschärfen, indem du sie mit einer Nahkampfwaffe triffst, anstelle einen "
        "Fertigkeitswurf für Mechanismus ausschalten auszuführen. Führe als Volle Aktion einen "
        "Nahkampfangriff gegen einen RK-Wert in Höhe des Mechanismus-ausschalten-SG der Falle aus. "
        "Verfehlst du, löst dies die Falle aus. Triffst du, dann würfle den Schaden aus; sollte dieser "
        "wenigstens die Hälfte des Mechanismus-ausschalten-SG der Falle betragen, entschärfst du die "
        "Falle, andernfalls löst du sie aus. Du kannst dies nur bei nichtmagischen Fallen versuchen. Du "
        "musst in der Lage sein, einen Teil der Falle mit deinem Angriff zu erreichen, um dieses "
        "Talent einzusetzen. Der SL kann festlegen, dass manche Fallen gegen dieses Talent immun sind.",
        "type": "general",
        "prerequisite_text": "Heftiger Angriff, Mechanismus ausschalten 1 Fertigkeitsrang, Ork.",
        "requirements": [
            {"kind": "feat", "required_feat_id": HEFTIGER_ANGRIFF_FEAT_ID},
            {"kind": "skill", "skill_id": MECHANISMUS_AUSSCHALTEN_SKILL_ID, "minimum_ranks": 1},
            {"kind": "race", "race_id": ORK_RACE_ID},
        ],
    },
    {
        "name": "Nachtragender Kämpfer",
        "description": "Du verspürst großen Zorn auf jeden, der es wagt dich anzugreifen. Diese Wut "
        "verleiht deinen Angriffen Kraft. Du erhältst einen Moralbonus von +1 auf Angriffs- und "
        "Schadenswürfe gegen jede Kreatur, die dich im aktuellen Kampf angegriffen hat.",
        "type": "combat",
        "prerequisite_text": "Ork.",
        "requirements": [
            {"kind": "race", "race_id": ORK_RACE_ID},
        ],
    },
    {
        "name": "Orkische Waffenexpertise",
        "description": "Du kannst mit den Lieblingswaffen der Orks mehr ausrichten. Wenn du dieses "
        "Talent wählst, wähle auch einen der folgenden Vorteile. Wenn du eine Waffe führst, die „Ork“ "
        "im Namen trägt, erhältst du den Vorteil, sofern du auch im Umgang mit dieser Waffe geübt bist: "
        "Mörder: Erhalte einen Kompetenzbonus von +2 auf Angriffswürfe zum Bestätigen Kritischer "
        "Treffer. Schinder: Erhalte einen Bonus von +1 auf Schadenswürfe gegen Kreaturen, die "
        "mindestens eine Größenkategorie kleiner sind als du. Schläger: Verursache mit der Waffe +1 "
        "Punkt nichttödlichen Schadens. Trickser: Erhalte einen Bonus von +2 auf eine Art "
        "Kampfmanöver, das du mit dieser Waffe ausführen kannst. Verteidiger: Erhalte einen "
        "Schildbonus von +1 auf deine RK (oder von +2, so du eine Zweihandwaffe führst). Zauberstörer: "
        "Addiere +3 auf den SG des Konzentrationswurfs eines Gegners, der im von dir bedrohten Bereich "
        "zaubern will; du musst dazu um die Position des Gegners wissen und zu einem "
        "Gelegenheitsangriff in der Lage sein. Dieses Talent ist wirkungslos, wenn du mit der "
        "benutzten Waffe nicht geübt bist. Speziell: Du kannst dieses Talent mehrmals wählen, musst "
        "dich aber immer für andere Vorteile entscheiden. Du kannst nur einen dieser Vorteile pro "
        "Runde einsetzen, die Wahl erfolgt als Freie Aktion zu Beginn deiner Runde.",
        "type": "combat",
        "prerequisite_text": "GAB +1, Ork.",
        "requirements": [
            {"kind": "bab", "minimum_bab": 1},
            {"kind": "race", "race_id": ORK_RACE_ID},
        ],
    },
    {
        "name": "Wilder Angriff",
        "description": "Deine Wildheit überkommt dich schnell, ist aber kurzlebig. Wenn du auf 0 TP "
        "oder weniger fällst, verlierst du jetzt pro Runde 2 TP, bist aber nicht wankend. Solltest du "
        "dich in einem Kampfrausch befinden, verlierst du nur 1 TP pro Runde.",
        "type": "general",
        "prerequisite_text": "Volksmerkmal Wildheit, Ork.",
        "requirements": [
            {"kind": "race", "race_id": ORK_RACE_ID},
        ],
    },
]


def load(filename: str) -> list[dict]:
    return json.loads((SEED_DIR / filename).read_text(encoding="utf-8"))


def save(filename: str, rows: list[dict]) -> None:
    deduped: dict[str, dict] = {}
    for row in rows:
        deduped[row["id"]] = row
    (SEED_DIR / filename).write_text(
        json.dumps(list(deduped.values()), ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def main() -> None:
    feats = load("base_feats.json")
    req_feats = load("base_feat_required_feats.json")
    req_skills = load("base_feat_required_skills.json")
    req_class_abilities = load("base_feat_required_class_abilities.json")
    req_races = load("base_feat_required_races.json")
    req_babs = load("base_feat_required_babs.json")

    own_feat_ids = {uid("ork-feat", f["name"]) for f in FEATS}
    feats = [f for f in feats if f["id"] not in own_feat_ids]
    req_feats = [r for r in req_feats if r["feat_id"] not in own_feat_ids]
    req_skills = [r for r in req_skills if r["feat_id"] not in own_feat_ids]
    req_class_abilities = [r for r in req_class_abilities if r["feat_id"] not in own_feat_ids]
    req_races = [r for r in req_races if r["feat_id"] not in own_feat_ids]
    req_babs = [r for r in req_babs if r["feat_id"] not in own_feat_ids]

    for feat in FEATS:
        feat_id = uid("ork-feat", feat["name"])
        feats.append(
            {
                "id": feat_id,
                "name": feat["name"],
                "description": feat["description"],
                "type": feat["type"],
                "prerequisite_text": feat["prerequisite_text"],
            }
        )

        for req in feat["requirements"]:
            group_id = uid("ork-feat-group", feat_id, req["group"]) if "group" in req else None
            if req["kind"] == "feat":
                req_feats.append(
                    {
                        "id": uid("ork-feat-req-feat", feat_id, req["required_feat_id"]),
                        "feat_id": feat_id,
                        "group_id": group_id,
                        "required_feat_id": req["required_feat_id"],
                    }
                )
            elif req["kind"] == "skill":
                req_skills.append(
                    {
                        "id": uid("ork-feat-req-skill", feat_id, req["skill_id"]),
                        "feat_id": feat_id,
                        "group_id": group_id,
                        "skill_id": req["skill_id"],
                        "minimum_ranks": req["minimum_ranks"],
                    }
                )
            elif req["kind"] == "class_ability":
                req_class_abilities.append(
                    {
                        "id": uid("ork-feat-req-class-ability", feat_id, req["ability_id"]),
                        "feat_id": feat_id,
                        "group_id": group_id,
                        "ability_id": req["ability_id"],
                    }
                )
            elif req["kind"] == "race":
                req_races.append(
                    {
                        "id": uid("ork-feat-req-race", feat_id, req["race_id"]),
                        "feat_id": feat_id,
                        "group_id": group_id,
                        "race_id": req["race_id"],
                    }
                )
            elif req["kind"] == "bab":
                req_babs.append(
                    {
                        "id": uid("ork-feat-req-bab", feat_id),
                        "feat_id": feat_id,
                        "group_id": group_id,
                        "minimum_bab": req["minimum_bab"],
                    }
                )
            else:
                raise ValueError(f"unknown requirement kind {req['kind']!r}")

    save("base_feats.json", feats)
    save("base_feat_required_feats.json", req_feats)
    save("base_feat_required_skills.json", req_skills)
    save("base_feat_required_class_abilities.json", req_class_abilities)
    save("base_feat_required_races.json", req_races)
    save("base_feat_required_babs.json", req_babs)

    print("Feats imported:", len(FEATS))
    print("Done.")


if __name__ == "__main__":
    main()
