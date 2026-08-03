"""Import the (Grundregelwerk core) Barbar's class shell from
http://prd.5footstep.de/Grundregelwerk/Klassen/Barbar — everything except
the rage powers themselves, which `import_barbar_rage_powers.py` already
covers separately (that script's 28 powers were transcribed by the project
owner before this page was fetched; cross-checked word-for-word against this
page's own rage-power section while writing this script — identical, no
corrections needed).

`hit_dice`/`bab_progression`/`fort_save`/`ref_save`/`wil_save`/
`skill_points_base` on `base_classes.json`'s existing Barbar row were
already correct (W12, full BAB, good Fort only, 4 + IN) — verified against
the page's "Tabelle: Barbar", not re-written.

What this script does:
- Fixes `base_class_skills.json`: the existing 7 rows were missing 3 real
  class skills (Akrobatik, Mit Tieren umgehen, Wissen (Natur)) — noted but
  deliberately left uncorrected during the Entfesselter Barbar pass
  (unrelated work at the time, see todos.md); fixed here since this pass IS
  about the core Barbar.
- Adds the 11 non-rage-power class features as `BaseClassAbility`/
  `BaseClassAbilityGrant` rows, gated at the levels from "Tabelle: Barbar":
  Umgang mit Waffen und Rüstungen (1), Schnelle Bewegung (1), Kampfrausch
  (1), Reflexbewegung (2), Fallengespür (3/6/9/12/15/18, one ability with
  six grants, same repeated-grant shape as Kämpfer's Bonus-Kampftalent),
  Verbesserte Reflexbewegung (5), Schadensreduzierung (7/10/13/16/19, five
  grants), Stärkerer Kampfrausch (11), Unbeugsamer Wille (14), Unermüdlicher
  Kampfrausch (17), Mächtiger Kampfrausch (20).

Why none of these reuse Entfesselter Barbar's already-seeded rows, even
where a name is close (checked before writing, same reasoning as the rage
powers script): Entfesselter Barbar's "Kampfrausch" gives flat +2 melee
attack/damage and 2 temp HP/HD with no ability-score change at all, versus
core's +4 STR/CON and +2 Will here — a fundamentally different mechanic,
not a rewording. Its trap-sense equivalent is even named differently
("Gefahreninstinkt" vs. this page's "Fallengespür"). "Stärkerer Kampfrausch"
here vs. Entfesselter's "Starker Kampfrausch" is a different name for a
different numeric progression on top of an already-different base rage.
Every ability below therefore gets its own fresh id.

Deliberately out of scope, same "don't guess, don't migrate unrelated
content" principle as every other class pass (CLAUDE.md):
- "Ehemaliger Barbar" (losing rage access on becoming lawful) is prose
  about a consequence, not a granted class feature at a level — no
  `BaseClassAbilityGrant` shape fits it, and no alignment field exists on
  `characters` to check against anyway. Left unmodeled, same as every other
  class's flavor/restriction prose (e.g. "Rolle").
- No handler-side computation (rage's numeric bonuses, trap sense stacking
  with a Rogue's trap sense, DR) — composition only, per CLAUDE.md.
- Archetypes beyond Zwei-Waffen-Kämpfer/Schildkämpfer-style sourced ones are
  out of scope here entirely; Barbar has none seeded and none are added by
  this script.

Run with the project venv active (this only writes the fixture JSON files,
it doesn't touch the database — run the normal seed scripts afterward):
    cd backend && python scripts/import_barbar.py
"""

from __future__ import annotations

import json
import uuid
from pathlib import Path

FIXTURES = Path(__file__).resolve().parent.parent / "app" / "fixtures"
SEED_DIR = FIXTURES / "seed"

ID_NAMESPACE = uuid.UUID("2f6b8d1a-7c4e-4a9b-9d3f-6a1c8e5b2d4f")

BARBAR_ID = "4558a936-bc38-4e40-afd8-bb85a7a03438"

MISSING_CLASS_SKILLS = ["Akrobatik", "Mit Tieren umgehen", "Wissen (Natur)"]

FALLENGESPUER_LEVELS = [3, 6, 9, 12, 15, 18]
SCHADENSREDUZIERUNG_LEVELS = [7, 10, 13, 16, 19]

# (name, levels, description)
CLASS_FEATURES: list[tuple[str, list[int], str]] = [
    (
        "Umgang mit Waffen und Rüstungen",
        [1],
        "Ein Barbar ist im Umgang mit allen einfachen Waffen und Kriegswaffen, leichten Rüstungen, "
        "mittelschweren Rüstungen und Schilden (außer Turmschilden) geübt.",
    ),
    (
        "Schnelle Bewegung",
        [1],
        "(AF) Die Bewegung zu Land ist bei einem Barbaren höher als für sein Volk üblich. Er kann "
        "sich 3 m weiter bewegen. Dies gilt nur, wenn er gar keine, leichte oder mittelschwere "
        "Rüstung trägt und keine schwere Last mit sich führt. Dieser Bonus wird angewandt, ehe die "
        "Bewegungsrate des Barbaren durch getragene Lasten oder Rüstungen modifiziert wird, und er "
        "addiert sich mit jeglichen anderen Boni des Barbaren auf die Bewegung zu Land.",
    ),
    (
        "Kampfrausch",
        [1],
        "(AF) Ein Barbar kann seine innere Kraft und Wildheit freisetzen, um zusätzliche Kampfkraft "
        "zu gewinnen. Ab der 1. Stufe kann ein Barbar für eine Anzahl von Runden am Tag in "
        "Kampfrausch verfallen, welche der Höhe seines KO-Modifikators +4 entspricht. Beim Erreichen "
        "jeder weiteren Stufe verlängert sich der Kampfrausch um 2 zusätzliche Runden. Kurzfristige "
        "Erhöhungen des Konstitutionsattributs durch den Kampfrausch oder durch Zauber wie Ausdauer "
        "des Ochsen, erhöhen die Anzahl von Runden jedoch nicht, die der Barbar am Tag in Kampfrausch "
        "verfallen kann. Der Barbar kann sich mit Hilfe einer freien Aktion in den Kampfrausch "
        "versetzten. Die Gesamtzahl der Runden, die der Barbar am Tag in Kampfrausch sein kann, "
        "erneuert sich nach 8 Stunden Rast, wobei diese Rast nicht unbedingt an einem Stück gehalten "
        "werden muss. Während des Kampfrauschs erhält der Barbar einen Moralbonus von +4 auf Stärke "
        "und Konstitution, ebenso wie einen Moralbonus von +2 auf alle Willenswürfe. Dafür muss er "
        "einen Malus von -2 auf die Rüstungsklasse hinnehmen. Die Erhöhung des Konstitutionsattributs "
        "gibt dem Barbaren +2 zusätzliche Trefferpunkte pro Stufe, die jedoch am Ende des Rauschs "
        "wieder verschwinden und nicht wie temporäre Trefferpunkte zuerst abgezogen werden. Während "
        "des Kampfrauschs kann der Barbar weder Fertigkeiten benutzen, die auf Geschicklichkeit, "
        "Intelligenz oder Charisma basieren (außer Akrobatik, Einschüchtern, Fliegen oder Reiten), "
        "noch Fähigkeiten die besonderer Ruhe und Konzentration bedürfen. Der Barbar kann den "
        "Kampfrausch mit einer freien Aktion beenden und ist dann eine Anzahl von Runden erschöpft, "
        "die doppelt so hoch ist, wie die Anzahl der Runden, die der Barbar in Kampfrausch gewesen "
        "ist. Während der Barbar erschöpft ist, kann er nicht in einen weiteren Kampfrausch "
        "verfallen. Ansonsten ist es aber durchaus möglich, innerhalb des gleichen Kampfs mehrfach "
        "in den Kampfrausch zu gehen. Wenn ein Barbar ohnmächtig wird, endet sein Kampfrausch "
        "automatisch, wodurch er in Todesgefahr gerät.",
    ),
    (
        "Reflexbewegung",
        [2],
        "(AF) Ab der 2. Stufe kann der Barbar schon auf Bedrohungen reagieren, bevor seine Sinne es "
        "ihm eigentlich erlauben. Er kann nicht mehr auf dem falschen Fuß erwischt werden und "
        "verliert auch nicht seinen Geschicklichkeitsbonus auf die RK, wenn der Angreifer unsichtbar "
        "ist. Ein Barbar mit dieser Fähigkeit kann dennoch seinen Geschicklichkeitsbonus auf die "
        "Rüstungsklasse verlieren, wenn er bewegungsunfähig ist oder der Gegner erfolgreich eine "
        "Finte gegen ihn ausführt. Besitzt der Barbar schon die Fähigkeit Reflexbewegung durch eine "
        "andere Klasse, erhält er stattdessen Verbesserte Reflexbewegung. (Diese klassenübergreifende "
        "Sonderregel wird aktuell nicht ausgewertet - siehe todos.md.)",
    ),
    (
        "Fallengespür",
        FALLENGESPUER_LEVELS,
        "(AF) Auf der 3. Stufe erhält der Barbar einen Bonus von +1 auf seine Reflexwürfe, um Fallen "
        "auszuweichen, und einen Bonus von +1 auf seine Rüstungsklasse für Angriffe von Fallen. "
        "Dieser Bonus erhöht sich alle weiteren drei Barbarenstufen um +1 (6., 9., 12., 15., 18.). "
        "Die Boni für Fallengespür von verschiedenen Klassen addieren sich.",
    ),
    (
        "Verbesserte Reflexbewegung",
        [5],
        "(AF) Ab der 5. Stufe kann der Barbar nicht mehr in die Zange genommen werden. Ein Schurke "
        "kann den Barbaren nicht mit einem hinterhältigen Angriff betreffen, der ihm durch das in "
        "die Zange nehmen möglich wird, es sei denn, seine Schurkenstufe ist vier Stufen höher als "
        "die Stufe des Barbaren. Hat der Barbar schon die Fähigkeit Reflexbewegung durch eine andere "
        "Klasse, addieren sich für den Vergleich die Stufen in dieser Klasse zu seiner Stufe als "
        "Barbar.",
    ),
    (
        "Schadensreduzierung",
        SCHADENSREDUZIERUNG_LEVELS,
        "(AF) Auf der 7. Stufe kann der Barbar einen Punkt Schaden von jedem Angriff mit einer Waffe "
        "oder einer natürlichen Waffe abziehen. Ab der 10. Stufe und dann allen drei weiteren (13., "
        "16., 19.) erhöht sich die Schadensreduzierung um eins. Die Schadensreduzierung kann einen "
        "Schaden auf 0, aber nicht unter 0 senken.",
    ),
    (
        "Stärkerer Kampfrausch",
        [11],
        "(AF) Ab der 11. Stufe erhöhen sich die Boni zu seiner Stärke und seiner Konstitution auf +6 "
        "und der Bonus auf Willenswürfe steigt auf +3, wenn der Barbar in einen Kampfrausch verfällt.",
    ),
    (
        "Unbeugsamer Wille",
        [14],
        "(AF) Ab der 14. Stufe erhält der Barbar während seines Kampfrauschs einen Bonus von +4 auf "
        "Willenswürfe gegen Verzauberungen. Dieser Bonus addiert sich mit anderen Modifikatoren, wie "
        "dem Moralbonus durch den Kampfrausch.",
    ),
    (
        "Unermüdlicher Kampfrausch",
        [17],
        "(AF) Auf der 17. Stufe ist der Barbar nach dem Ende seines Kampfrauschs nicht mehr erschöpft.",
    ),
    (
        "Mächtiger Kampfrausch",
        [20],
        "(AF) Auf der 20. Stufe erhöhen sich die Boni zu seiner Stärke und seiner Konstitution auf +8 "
        "und der Bonus auf Willenswürfe steigt auf +4, wenn der Barbar in einen Kampfrausch verfällt.",
    ),
]


def uid(*parts: str) -> str:
    return str(uuid.uuid5(ID_NAMESPACE, "|".join(parts)))


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
    class_id = BARBAR_ID

    # ---- base_class_skills.json ----
    skills = load("base_skills.json")
    skill_id_by_name = {row["name"]: row["id"] for row in skills}
    for name in MISSING_CLASS_SKILLS:
        assert name in skill_id_by_name, f"missing skill: {name}"

    class_skills = load("base_class_skills.json")
    existing_skill_ids = {row["skill_id"] for row in class_skills if row["base_class_id"] == class_id}
    for name in MISSING_CLASS_SKILLS:
        skill_id = skill_id_by_name[name]
        if skill_id in existing_skill_ids:
            continue
        class_skills.append(
            {
                "id": uid("barbar-classskill", name),
                "base_class_id": class_id,
                "skill_id": skill_id,
                "option_choice_id": None,
            }
        )
    save("base_class_skills.json", class_skills)

    # ---- base_class_abilities.json + base_class_ability_grants.json ----
    abilities = load("base_class_abilities.json")
    existing_ability_ids = {a["id"] for a in abilities}

    grants = load("base_class_ability_grants.json")
    own_grant_ids = {
        uid("barbar-shell-grant", uid("barbar-shell-ability", name), str(level))
        for name, levels, _description in CLASS_FEATURES
        for level in levels
    }
    grants = [g for g in grants if g["id"] not in own_grant_ids]

    def add_ability(name: str, description: str) -> str:
        aid = uid("barbar-shell-ability", name)
        if aid not in existing_ability_ids:
            abilities.append({"id": aid, "name": name, "description": description})
            existing_ability_ids.add(aid)
        return aid

    def add_grant(ability_id: str, level: int) -> None:
        grants.append(
            {
                "id": uid("barbar-shell-grant", ability_id, str(level)),
                "base_class_id": class_id,
                "ability_id": ability_id,
                "option_choice_id": None,
                "level": level,
            }
        )

    for name, levels, description in CLASS_FEATURES:
        aid = add_ability(name, description)
        for level in levels:
            add_grant(aid, level)

    save("base_class_abilities.json", abilities)
    save("base_class_ability_grants.json", grants)

    print("Class skills added:", len(MISSING_CLASS_SKILLS))
    print("Class features imported:", len(CLASS_FEATURES))
    print("Total grants (this class):", len([g for g in grants if g["base_class_id"] == class_id]))
    print("Done.")


if __name__ == "__main__":
    main()
