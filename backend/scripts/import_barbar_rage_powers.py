"""Import a first batch of the (Grundregelwerk) Barbar's Kampfrauschkräfte
(rage powers) into the seed JSON files, scoped to exactly the 28 powers
hand-transcribed from the core rulebook and supplied by the project owner
in-conversation (2026-08-03) — not fetched from prd.5footstep.de by this
script, unlike the class-page imports (`import_kleriker.py` etc.).

Why this needed its own script instead of reusing Entfesselter Barbar's
already-seeded rage powers (`import_entfesselter_barbar.py`): checked several
same-named powers against Entfesselter Barbar's existing catalog text before
writing this, and found real mechanical differences, not just rewording —
e.g. Erhöhte Schadensreduzierung is +1/- per pick here vs. +2/- there,
Mächtiger Schlag is once-per-rage here vs. once-per-day there, and Wachsame
Kampfhaltung/Verteidigungshaltung are two separate ranged/melee powers here
vs. one combined power there (which also has no ranged counterpart at all).
Pathfinder Unchained deliberately rebalanced a chunk of rage powers under
the same names, so reusing those rows for the core Barbar would have been
factually wrong, not just redundant. Every ability/choice below therefore
gets its own fresh id — no row is shared with Entfesselter Barbar's catalog
entries, even where the name matches exactly. The one exception is the
"Kampfrauschkraft" *slot* ability (grants at level 2, 4, ... 20) — that
text is genuinely class-agnostic ("jeder weiteren geraden Klassenstufe als
Barbar") and describes a rule identical between core and unchained, so it's
reused by id rather than duplicated.

Deliberately out of scope here, same "don't migrate unrelated mock/gap
content as a side effect" principle as every other class pass (CLAUDE.md):
- The rest of the core Barbar's class shell (Kampfrausch itself, Schnelle
  Bewegung, Reflexbewegung, Gefahreninstinkt, Schadensreduzierung, Umgang
  mit Waffen und Rüstungen, ...) is *not* added here — no sourced text for
  it was supplied in this pass, and inventing it would be exactly the
  guessed-content problem `todos.md` already flags elsewhere. A Barbar
  character today has rage-power *choices* wired up without a "Kampfrausch"
  ability of its own describing the base rage mechanic — tracked as a known
  gap in `todos.md`, not fixed here.
- Barbar's `base_class_skills` gap (7 of 10 real class skills present,
  noted but not fixed during the Entfesselter Barbar pass) — unrelated to
  this change, left alone.
- Only 28 of Barbarian's real Core Rulebook rage powers are covered (the
  ones supplied this pass) — the rest of the real list remains unimported;
  the roadmap/todos entries for this note that a second pass is needed.
- Repeatable-pick powers (Erhöhte Schadensreduzierung ×3, Schneller Schritt
  ×3) get one `BaseClassOptionChoice` row each, same known limitation as
  every other repeatable rage power in this project (see
  `import_entfesselter_barbar.py`) — the schema has no "may be picked more
  than once" concept yet.
- Nachtsicht's prerequisite ("Dämmersicht racial trait OR the Dämmersicht
  rage power") is a 3-way OR across a `BaseRaceAbility` and a
  `BaseClassOptionChoice` — `requires_choice_id` can only express one
  in-class choice, so it points at the Dämmersicht rage-power choice only;
  the racial branch stays text-only, unenforced (same limitation as
  Entfesselter Barbar's equivalent).
- No handler-side computation (scaling numbers, action economy, DR
  stacking, stance mutual exclusion) — composition only, per CLAUDE.md.

Run with the project venv active (this only writes the fixture JSON files,
it doesn't touch the database — run the normal seed scripts afterward):
    cd backend && python scripts/import_barbar_rage_powers.py
"""

from __future__ import annotations

import json
import uuid
from pathlib import Path

FIXTURES = Path(__file__).resolve().parent.parent / "app" / "fixtures"
SEED_DIR = FIXTURES / "seed"

ID_NAMESPACE = uuid.UUID("b7e4c1a2-9f3d-4e6b-8c1a-5d2e9f7b3c6a")

BARBAR_ID = "4558a936-bc38-4e40-afd8-bb85a7a03438"

# Shared, class-agnostic "you get a new rage power" slot ability, reused
# by id from Entfesselter Barbar's catalog — see module docstring.
KAMPFRAUSCHKRAFT_SLOT_ABILITY_ID = "cd254c1a-052f-5417-b4fa-bce74e727e4e"
KAMPFRAUSCHKRAFT_SLOT_LEVELS = list(range(2, 21, 2))

# (name, min_level, requires-rage-power-name, description) — description
# includes the leading "(AF)" tag verbatim, matching every other rage
# power's convention in this project's catalog.
RAGE_POWERS: list[tuple[str, int | None, str | None, str]] = [
    (
        "Aberglaube",
        None,
        None,
        "(AF) Der Barbar erhält einen Moralbonus von +2 auf Rettungswürfe, um Zaubern, übernatürlichen "
        "und zauberähnlichen Fähigkeiten zu widerstehen. Dieser Bonus erhöht sich um +1 für alle vier "
        "Stufen, die der Barbar erreicht hat. Im Kampfrausch kann der Barbar kein williges Ziel für "
        "einen Zauberspruch sein und muss den Rettungswurf gegen alle Zauber durchführen, auch gegen "
        "die von Verbündeten.",
    ),
    (
        "Animalische Wut",
        None,
        None,
        "(AF) Im Kampfrausch kann der Barbar einen Bissangriff durchführen. Wenn der Bissangriff im "
        "Zuge eines vollen Angriffs eingesetzt wird, wird der Bissangriff mit dem vollen "
        "Grund-Angriffsbonus – 5 durchgeführt. Wenn der Angriff trifft, verursacht er 1W4 Punkte "
        "Schaden (vorausgesetzt der Barbar ist mittelgroß, 1W3 Punkte Schaden wenn er klein ist) plus "
        "die Hälfte des ST-Modifikators. Er kann den Bissangriff auch in einem Ringkampf als Teil der "
        "Aktion zum Weiterführen oder Entkommen einsetzen. Dieser Angriff wird durchgeführt, bevor der "
        "Wurf für den Ringkampf ausgeführt wird. Trifft der Biss, erhalten alle Ringkampfwürfe in "
        "dieser Runde gegen das Ziel des Bissangriffes einen Bonus von +2.",
    ),
    (
        "Dämmersicht",
        None,
        None,
        "(AF) Die Sinne des Barbaren schärfen sich und er erhält während des Kampfrauschs Dämmersicht.",
    ),
    (
        "Einschüchterndes Niederstarren",
        None,
        None,
        "(AF) Als Bewegungsaktion kann der Barbar einen Einschüchterungsversuch gegen einen "
        "angrenzenden Gegner machen. Ist er erfolgreich, demoralisiert er sein Opfer. Der Gegner ist "
        "für 1W4 Runden lang erschüttert +1 Runde für je 5 Punkte, die der Barbar beim Wurf über den "
        "SG kommt.",
    ),
    (
        "Erhöhte Schadensreduzierung",
        8,
        None,
        "(AF) Die Schadensreduzierung des Barbaren erhöht sich um 1/-. Diese Schadensreduzierung wirkt "
        "nur im Kampfrausch. Ein Barbar kann diese Kraft bis zu drei Mal wählen. Ihre Auswirkungen "
        "addieren sich. Ein Barbar kann diese Kraft erst ab der 8. Stufe wählen.",
    ),
    (
        "Erneuerte Lebenskraft",
        4,
        None,
        "(AF) Der Barbar kann als Standard-Aktion 1W8 + seinen KO-Modifikator an Trefferpunkten "
        "heilen. Für alle vier Stufen, die der Barbar jenseits der 4. Stufe erreicht hat, erhöht sich "
        "die Menge des geheilten Schadens um 1W8 Punkte, bis zu einer Menge von 5W8 auf der 20. Stufe. "
        "Um diese Kraft wählen zu können, muss der Barbar mindestens auf der 4. Stufe sein. Diese "
        "Kraft kann nur einmal am Tag und nur im Kampfrausch eingesetzt werden.",
    ),
    (
        "Furchtlose Wut",
        12,
        None,
        "(AF) Im Kampfrausch ist der Barbar immun gegen die Zustände verängstigt und erschüttert. Der "
        "Barbar muss mindestens 12. Stufe sein, um diese Kraft zu wählen.",
    ),
    (
        "Geruchssinn",
        None,
        None,
        "(AF) Der Barbar erhält während des Kampfrauschs die Eigenschaft Geruchssinn und kann diese "
        "einsetzen, um unsichtbare Feinde aufzuspüren. (Für Regeln zur Fähigkeit Geruchssinn siehe "
        "Kapitel Anhang.)",
    ),
    (
        "Geweckte Wut",
        None,
        None,
        "(AF) Der Barbar kann sich in einen Kampfrausch begeben, obwohl er erschöpft ist. Solange er "
        "mit Hilfe dieser Fähigkeit im Kampfrausch ist, kann er nicht erschöpft sein. Sobald der "
        "Kampfrausch schwindet, ist der Barbar für 10 Minuten je Runde entkräftet, die er im "
        "Kampfrausch gewesen ist.",
    ),
    (
        "Innere Zähigkeit",
        8,
        None,
        "(AF) Im Kampfrausch ist der Barbar immun gegen die Zustände kränkelnd und Übelkeit. Der "
        "Barbar muss mindestens auf der 8. Stufe sein, um diese Kraft zu wählen.",
    ),
    (
        "Kampfschrei",
        8,
        "Einschüchterndes Niederstarren",
        "(AF) Der Barbar kann als Standard-Aktion einen Kampfschrei ausstoßen. Alle Feinde innerhalb "
        "von 9 m müssen einen Willenswurf (SG entspricht 10 + ½ Stufe des Barbaren + seinem "
        "ST-Modifikator) bestehen oder sind 1W4+1 Runden in Panik. Musste ein Gegner einen "
        "Willenswurf gegen den Kampfschrei würfeln, kann er unabhängig vom Ergebnis für 24 Stunden "
        "nicht mehr Ziel derselben Kraft werden. Um diese Kraft zu wählen, muss der Barbar mindestens "
        "auf der 8. Stufe sein und schon über die Kraft Einschüchterndes Niederstarren verfügen.",
    ),
    (
        "Kein Entkommen",
        None,
        None,
        "(AF) Der Barbar kann sich als Augenblickliche Aktion bis zum Doppelten seiner Bewegungsrate "
        "bewegen. Der Barbar kann diese Fähigkeit nur dann einsetzen, wenn ein benachbarter Gegner "
        "sich mit einer Rückzugsaktion aus dem Kampf entfernt. Der Barbar muss die Bewegung neben dem "
        "Feind beenden, der sich zurückgezogen hat. Die Bewegung des Barbaren verursacht normal "
        "Gelegenheitsangriffe. Diese Kraft kann nur einmal je Kampfrausch eingesetzt werden.",
    ),
    (
        "Klarer Augenblick",
        None,
        None,
        "(AF) Für eine Runde erleidet der Barbar weder Vorteile noch Nachteile durch seinen "
        "Kampfrausch. Dies gilt auch für den Rüstungsklassenmalus und die beschränkte Auswahl an "
        "Aktionen. Das Aktivieren dieser Kraft ist eine Schnelle Aktion. Diese Runde zählt aber als "
        "Runde in Hinsicht auf die Gesamtrundenzahl, die dem Barbaren am Tag zur Verfügung stehen. "
        "Diese Kraft kann nur einmal im Kampfrausch eingesetzt werden.",
    ),
    (
        "Kraftrausch",
        None,
        None,
        "(AF) Der Barbar addiert seine Barbarenstufe zu einer Stärke- oder Kampfmanöverprobe oder zu "
        "seiner Kampfmanöververteidigung, wenn ein Gegner ein Manöver gegen ihn versucht. Die Kraft "
        "wird als Augenblickliche Aktion genutzt. Diese Kraft kann nur einmal je Kampfrausch "
        "eingesetzt werden.",
    ),
    (
        "Kraftvoller Schlag",
        None,
        None,
        "(AF) Der Barbar erhält einen Bonus von +1 auf einen Schadenswurf. Dieser Bonus erhöht sich "
        "um +1 für alle vier Stufen, die der Barbar erreicht hat. Die Kraft wird als Schnelle Aktion "
        "eingesetzt, bevor der Angriff gewürfelt wurde. Diese Kraft kann nur einmal je Kampfrausch "
        "eingesetzt werden.",
    ),
    (
        "Mächtiger Schlag",
        12,
        None,
        "(AF) Der Barbar kann einen Kritischen Treffer automatisch bestätigen. Diese Kraft kann als "
        "Augenblickliche Aktion genutzt werden, sobald der Barbar bei einem Angriff eine "
        "Bedrohungschance würfelt. Der Barbar muss auf der 12. Stufe sein, um diese Kraft auswählen "
        "zu können. Er kann diese Kraft nur einmal im Kampfrausch einsetzen.",
    ),
    (
        "Nachtsicht",
        None,
        "Dämmersicht",
        "(AF) Während des Rausches werden die Sinne des Barbaren außergewöhnlich geschärft und er "
        "erhält dann Dunkelsicht (18 m). Um diese Kraft wählen zu können, muss der Barbar entweder "
        "durch sein Volk Dämmersicht haben oder die Kraft Dämmersicht gewählt haben. (Diese "
        "Voraussetzung ist eine OR-Verknüpfung aus einem Volksmerkmal und einer Kampfrauschkraft und "
        "wird aktuell nur für den Kampfrauschkraft-Zweig erzwungen, nicht für den Volksmerkmal-Zweig "
        "- siehe todos.md.)",
    ),
    (
        "Schnelle Reflexe",
        None,
        None,
        "(AF) Während des Kampfrausches kann der Barbar einen zusätzlichen Gelegenheitsangriff pro "
        "Runde durchführen.",
    ),
    (
        "Schneller Schritt",
        None,
        None,
        "(AF) Der Barbar erhält einen Verbesserungsbonus auf seine Bewegungsrate von 1,5 m. Diese "
        "Erhöhung ist im Kampfrausch immer aktiv. Der Barbar kann diese Kampfrauschkraft bis zu drei "
        "Mal wählen. Ihre Auswirkungen addieren sich.",
    ),
    (
        "Spontane Treffsicherheit",
        None,
        None,
        "(AF) Der Barbar addiert einen Moralbonus von +1 zu einem Angriffswurf. Dieser Bonus erhöht "
        "sich um +1 für alle vier Stufen, die der Barbar erreicht hat. Diese Kraft muss er als "
        "Schnelle Aktion vor dem Angriff einsetzen. Die Kraft kann nur einmal je Kampfrausch "
        "eingesetzt werden.",
    ),
    (
        "Starker Geist",
        8,
        None,
        "(AF) Der Barbar kann einen misslungenen Willenswurf wiederholen. Diese Kraft wird als "
        "Augenblickliche Aktion eingesetzt, nachdem der Wurf gemacht worden ist, aber bevor der SL "
        "das Ergebnis bekannt gemacht hat. Der Barbar muss das Ergebnis des zweiten Wurfes nehmen, "
        "auch wenn es schlechter ist. Ein Barbar muss mindestens die 8. Stufe erreicht haben, um "
        "diese Kraft auswählen zu können. Diese Kraft kann nur einmal je Kampfrausch eingesetzt "
        "werden.",
    ),
    (
        "Unerwarteter Schlag",
        8,
        None,
        "(AF) Der Barbar kann einen Gelegenheitsangriff gegen einen Gegner ausführen, der sich in ein "
        "Feld bewegt, das von dem Barbaren bedroht wird, unabhängig davon, ob diese Bewegung "
        "normalerweise einen Gelegenheitsangriff verursachen würde oder nicht. Diese Kraft kann nur "
        "einmal je Kampfrausch eingesetzt werden. Der Barbar muss mindestens auf der 8. Stufe sein, "
        "um diese Kraft zu wählen.",
    ),
    (
        "Verteidigungshaltung",
        None,
        None,
        "(AF) Der Barbar erhält einen Ausweichbonus von +1 auf seine Rüstungsklasse gegen "
        "Fernkampfangriffe für eine Anzahl von Runden, die dem aktuellen KO-Modifikator entspricht "
        "(Minimum 1). Dieser Bonus erhöht sich um +1 für alle sechs Stufen, die der Barbar erreicht "
        "hat. Das Aktivieren dieser Eigenschaft ist eine Bewegungsaktion, die keinen "
        "Gelegenheitsangriff verursacht.",
    ),
    (
        "Wachsame Kampfhaltung",
        None,
        None,
        "(AF) Der Barbar erhält einen Ausweichbonus von +1 auf seine Rüstungsklasse gegen "
        "Nahkampfangriffe für eine Anzahl von Runden, die dem aktuellen KO-Modifikator entspricht "
        "(Minimum 1). Dieser Bonus erhöht sich um +1 für alle sechs Stufen, die der Barbar erreicht "
        "hat. Das Aktivieren dieser Eigenschaft ist eine Bewegungsaktion, die keinen "
        "Gelegenheitsangriff verursacht.",
    ),
    (
        "Wuterfüllter Sprung",
        None,
        None,
        "(AF) Im Kampfrausch addiert der Barbar seine Stufe als Verbesserungsbonus zu allen "
        "Fertigkeitswürfen in Akrobatik, die sich aufs Springen beziehen, und wird beim Sprung "
        "behandelt, als hätte er genügend Anlauf gehabt.",
    ),
    (
        "Wuterfülltes Klettern",
        None,
        None,
        "(AF) Im Kampfrausch addiert der Barbar seine Stufe als Verbesserungsbonus zu allen "
        "Fertigkeitswürfen in Klettern.",
    ),
    (
        "Wuterfülltes Schwimmen",
        None,
        None,
        "(AF) Im Kampfrausch addiert der Barbar seine Stufe als Verbesserungsbonus zu allen "
        "Fertigkeitswürfen in Schwimmen.",
    ),
    (
        "Zurücktreiben",
        None,
        None,
        "(AF) Einmal pro Runde kann der Barbar anstelle eines Nahkampfangriffs versuchen, einen "
        "Ansturm zu unternehmen. Ist er erfolgreich, erleidet das Ziel Schaden in Höhe des "
        "ST-Modifikators des Barbaren und wird wie normal zurück geschoben. Der Barbar braucht sich "
        "nicht mit dem Ziel zurück zu bewegen, wenn er erfolgreich ist. Der Einsatz dieser Kraft "
        "verursacht keinen Gelegenheitsangriff.",
    ),
]

assert len(RAGE_POWERS) == 28, len(RAGE_POWERS)


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

    # ---- base_class_option_groups.json ----
    groups = load("base_class_option_groups.json")
    group_id = uid("barbar-group", "kampfrauschkraft")
    groups = [g for g in groups if g["id"] != group_id]
    groups.append(
        {
            "id": group_id,
            "base_class_id": class_id,
            "key": "kampfrauschkraft",
            "label": "Kampfrauschkraft",
            "max_choices": len(KAMPFRAUSCHKRAFT_SLOT_LEVELS),
        }
    )
    save("base_class_option_groups.json", groups)

    # ---- base_class_option_choices.json ----
    choices = load("base_class_option_choices.json")
    choices = [c for c in choices if c["group_id"] != group_id]

    choice_id_by_power: dict[str, str] = {name: uid("barbar-choice", name) for name, _, _, _ in RAGE_POWERS}

    for name, min_level, requires, _description in RAGE_POWERS:
        choices.append(
            {
                "id": choice_id_by_power[name],
                "group_id": group_id,
                "name": name,
                "min_level": min_level,
                "requires_choice_id": choice_id_by_power[requires] if requires else None,
            }
        )
    save("base_class_option_choices.json", choices)

    # ---- base_class_abilities.json + base_class_ability_grants.json ----
    abilities = load("base_class_abilities.json")
    existing_ability_ids = {a["id"] for a in abilities}

    grants = load("base_class_ability_grants.json")
    # Drop and re-add only this script's own grants (identified by their
    # deterministic ids), leaving every other class's grants (including
    # Entfesselter Barbar's) untouched.
    own_grant_ids = {
        uid("barbar-grant", KAMPFRAUSCHKRAFT_SLOT_ABILITY_ID, str(level), "") for level in KAMPFRAUSCHKRAFT_SLOT_LEVELS
    } | {
        uid("barbar-grant", uid("barbar-ability", name), "1", choice_id_by_power[name]) for name, _, _, _ in RAGE_POWERS
    }
    grants = [g for g in grants if g["id"] not in own_grant_ids]

    def add_ability(name: str, description: str) -> str:
        aid = uid("barbar-ability", name)
        if aid not in existing_ability_ids:
            abilities.append({"id": aid, "name": name, "description": description})
            existing_ability_ids.add(aid)
        return aid

    def add_grant(ability_id: str, level: int, option_choice_id: str | None = None) -> None:
        grants.append(
            {
                "id": uid("barbar-grant", ability_id, str(level), option_choice_id or ""),
                "base_class_id": class_id,
                "ability_id": ability_id,
                "option_choice_id": option_choice_id,
                "level": level,
            }
        )

    # Reuse the shared, class-agnostic "you get a new rage power" slot
    # ability by id (see module docstring) rather than duplicating it.
    for level in KAMPFRAUSCHKRAFT_SLOT_LEVELS:
        add_grant(KAMPFRAUSCHKRAFT_SLOT_ABILITY_ID, level)

    for name, _min_level, _requires, description in RAGE_POWERS:
        aid = add_ability(name, description)
        add_grant(aid, 1, choice_id_by_power[name])

    save("base_class_abilities.json", abilities)
    save("base_class_ability_grants.json", grants)

    print("Rage powers imported:", len(RAGE_POWERS))
    print("Slot grants added:", len(KAMPFRAUSCHKRAFT_SLOT_LEVELS))
    print("Total grants (this class):", len([g for g in grants if g["base_class_id"] == class_id]))
    print("Done.")


if __name__ == "__main__":
    main()
