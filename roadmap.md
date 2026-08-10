# Backend build-out roadmap

Sequencing plan for turning the mock endpoints in `backend/app/main.py` and the
frontend-only `AppStateContext` state into a real, database-backed system. See
`todos.md` for the current endpoint-by-endpoint status; this document is the
*order* in which that gap gets closed, not a replacement for that inventory.

## Guiding decisions

- **Vertical slices, not horizontal layers.** Never "stub every endpoint, then
  swap the whole UI, then add the database, then add logic." Each slice below
  goes UI → schema → backend → database → tests, for one feature, before
  moving to the next.
- **Ordered by the character lifecycle**: user → character creation → items →
  effects → possible actions → level-up. This lets each slice double as an
  automated end-to-end test scenario (create user → create character → equip
  item → apply effect → level up → assert state).
- **Thin pass first, thick pass later, per stage.** Every lifecycle stage
  below is split into a minimal "thin" version (prove the full stack works)
  and one or more "thick" follow-up iterations (add rule depth). No stage is
  a single atomic slice — "character creation" and "level-up" in particular
  are each their own multi-iteration mini-roadmap.
- **Reference data stays in JSON fixtures** (`backend/app/fixtures/*.json`)
  through all of the slices below, with three exceptions: **races** were
  pulled forward into slice 2 as a real, normalized set of tables (see
  `readme.md`'s ER diagram — `BaseRace`, `BaseRaceAbility`, `RaceAbilityGrant`,
  `RaceAbilityReplacement`), because `characters.race_id` needs a real FK
  target from the start rather than a loose fixture-string reference; **classes**
  got a real `BaseClass` table in slice 3 for the same FK reason
  (`CharacterLevel.base_class_id`), and — unlike races — this was
  deliberately *not* kept identity-only: `BaseClass` also carries `hit_dice`
  and the `arch_class_of` self-FK (root class vs. archetype variant), by
  explicit decision that class is central/complex enough to warrant earlier
  DB investment than race, with more class-mechanical fields expected to
  migrate in over time; and **skills** got real `BaseSkill`/`BaseClassSkill`
  tables, also in slice 3, so `classSkills` has a real FK target instead of
  fixture-key strings and skill names have a stable id a future translation
  layer can key off of (`name` stays a single unlocalized string for now —
  DE/EN is still an open item, see `todos.md`). Skill points, spell type, and
  archetype/option-group *definitions* still stay in `classes.json` for now.
  Migrating the rest of feats/spells/items/effects (and the remaining class
  content) into the database remains a later slice (#8), done once the
  schemas that consume this data have stabilized — not designed
  speculatively now.
- **Shared modifier/bonus-stacking design**: items and effects are both
  fundamentally "things that apply modifiers to character stats." Design
  that mechanism once, in slice 5 (Items), and reuse it in slice 6 (Effects)
  rather than building two separate systems.
- **Uniform `CharacterContext` handler signature (decided 2026-08-10, refined
  2026-08-10 — no privileged targets/phases after all).** Every
  `HANDLERS`/`EFFECT_HANDLERS` entry, across every rule-element family (race
  abilities, class abilities, effects, weapon abilities with real computed
  state), should end up called exactly once, all in one flat pass, with the
  same one typed `CharacterContext` dataclass — raw ability scores,
  `skill_ranks`, levels/classes, feat/trait/granted-ability/active-effect
  ids, gear — and always returning `list[Modifier]`, never a mutated
  character. Every returned `Modifier` (from every family) then gets grouped
  by target and `stack()`-ed once; `sheet.py`'s own final-assembly arithmetic
  (computing `ability_mods` before the line that builds `saves`, total speed
  before `jump_skill_bonus`, ...) consumes those stacked values in whatever
  order its formulas need — ordinary sequential code, not a rule the
  handler-calling contract itself has to encode. An earlier version of this
  decision proposed resolving `SCORE`/`SPEED` handlers in a privileged first
  phase before everything else, on the theory that other handlers might need
  their *stacked* result as input; checked against every handler that
  actually exists (`race_abilities.py`, `speed.py`, `effects.py`) and none of
  them do — Skill Focus's +3-vs-+6 threshold needs raw skill ranks, not a
  computed ability mod, and `jump_skill_bonus` was never a `HANDLERS` entry
  to begin with (its own docstring already says so). No two-phase split is
  needed today; full reasoning in `readme.md`'s "Request pipeline" section,
  including the explicit caveat for if a future handler ever *does* need a
  resolved value as input (not built for speculatively now). Motivated by a
  real gap `CLAUDE.md`'s own Skill Focus example already implied but no
  handler signature ever actually supported: a conditional handler (+3
  normally, +6 at 10+ ranks) needs to read the character's skill ranks, and
  today's `HANDLERS` (zero arguments) and `EFFECT_HANDLERS` (only that
  effect's own instances) can't give it that.
  **Document-only for now, no batch refactor**: `rules/race_abilities.py`/
  `rules/speed.py`'s zero-arg `HANDLERS` and `rules/effects.py`'s
  instances-only `EFFECT_HANDLERS` (its first content, Entfesselter
  Barbar's Kampfrausch, landed 2026-08-09) stay as they are until a handler
  that's actually conditional on something outside "does the character have
  this ability" needs writing — most of `todos.md`'s "Effekt-Handler-
  Inventar" and the still-unbuilt `rules/class_abilities.py` (roadmap Slice
  3's "Class-ability computation" item) will hit this soon. Once every
  family is migrated, `rules/effects.py`'s current "kept separate because
  the call signature differs" rationale no longer holds and it should merge
  into `rules/handlers.py`'s unified registry.

## Beispielcharakter (Referenz-Charakter für Vollständigkeitsprüfung)

Tracking section, added 2026-08-03 after trying to model a concrete
level-12 Mensch/Barbar through the app (Talente: Heftiger Angriff,
Waffenfokus [Zweihänder], Abhärtung, Meisterhandwerker, Magische Waffen und
Rüstungen herstellen, Ausdauer; Kampfrauschkräfte: Erneuerte Lebenskraft,
Kraftvoller Schlag, Einschüchterndes Niederstarren; Ausrüstung: Celestische
Brustplatte, ein benannter magischer Zweihänder, Krummschwert, Streitaxt,
Kompositbogen, drei stat-boostende Wondrous Items; frei eingegebene
Attributswerte; zwei permanente aktive Effekte). No slice reordering turned
out to be structurally necessary — every dependency below already sits in
slice 2–5, in the right relative order — but the gaps found are consolidated
here as the concrete near-term priority within those slices, rather than
left scattered across conversation history. Doubles as the acceptance test
for "can a real, complex character actually be built end-to-end," per the
Guiding decisions' end-to-end-scenario idea above.

Concrete gaps found, each pointing at the slice/bullet that owns it:

- [x] **Barbar — vollständig gegen `prd.5footstep.de` importiert.**
      2026-08-03 in zwei Schritten: zuerst 28 Kampfrauschkräfte
      (`backend/scripts/import_barbar_rage_powers.py`, Text vom
      Projektinhaber bereitgestellt, danach wortgleich gegen
      <http://prd.5footstep.de/Grundregelwerk/Klassen/Barbar> gegengeprüft —
      keine Abweichung), dann die restliche Klassenschale + der
      Klassenfertigkeiten-Fix
      (`backend/scripts/import_barbar.py`, direkt von der Quellseite
      gefetcht). Eigene `BaseClassAbility`/`BaseClassOptionChoice`-Zeilen für
      jede Kraft/Fähigkeit (bewusst *nicht* mit Entfesselter Barbars
      gleichnamigen Zeilen geteilt — Textvergleich vor dem Import zeigte
      echte mechanische Unterschiede, z. B. Kampfrausch +4 ST/KO + 2
      Willensbonus hier vs. Entfesselter Barbars pauschale +2
      Angriff/Schaden + temporäre TP; Fallengespür hier vs. Entfesselter
      Barbars anders benanntes Gefahreninstinkt; Erhöhte Schadensreduzierung
      +1/- vs. +2/-; Mächtiger Schlag einmal pro Kampfrausch vs. einmal pro
      Tag; Wachsame Kampfhaltung/Verteidigungshaltung als zwei getrennte
      Kräfte vs. eine kombinierte). Die generische „Kampfrauschkraft"-Slot-
      Fähigkeit (Level 2, 4, ... 20) wird von Entfesselter Barbar per id
      wiederverwendet, da dieser Text klassenunabhängig ist.

      Klassenschale (`import_barbar.py`): Umgang mit Waffen und Rüstungen,
      Schnelle Bewegung, Kampfrausch (alle Stufe 1), Reflexbewegung (2),
      Fallengespür (3/6/9/12/15/18, eine Katalogzeile mit sechs Grants,
      gleiches Muster wie Schurkes Hinterhältiger Angriff), Verbesserte
      Reflexbewegung (5), Schadensreduzierung (7/10/13/16/19, fünf Grants),
      Stärkerer Kampfrausch (11), Unbeugsamer Wille (14), Unermüdlicher
      Kampfrausch (17), Mächtiger Kampfrausch (20) — 11 neue
      Katalogzeilen, 20 neue Grants. `base_class_skills.json` um die drei
      fehlenden echten Klassenfertigkeiten ergänzt (Akrobatik, Mit Tieren
      umgehen, Wissen (Natur) — bereits in der Entfesselter-Barbar-Runde als
      Lücke notiert, aber bewusst nicht mitkorrigiert, siehe `todos.md`).
      `hit_dice`/`bab_progression`/Rettungswürfe/`skill_points_base` waren
      bereits korrekt (gegen "Tabelle: Barbar" verifiziert, nicht erneut
      geschrieben).

      **Bewusst nicht importiert:** „Ehemaliger Barbar" (Konsequenz bei
      rechtschaffener Gesinnung — reiner Fließtext, keine stufengebundene
      Fähigkeit, kein Gesinnungsfeld im Datenmodell, das es prüfen könnte).
      Keine Berechnungslogik für die Zahlenwerte (Kampfrausch-Boni,
      Schadensreduzierung-Stufen, Fallengespür-Skalierung) — nur
      Katalogzeile + Beschreibungstext, gleiche Tiefe wie jede andere
      Klasse. Archetypen über die bereits vorhandenen Kämpfer-Archetypen
      hinaus nicht angefasst (Barbar hat ohnehin keine archetype-Zeilen).
- [x] **Talent-Sub-Wahl-Schema** — `BaseFeat.sub_choice_type` ("weapon"/
      "skill"/"spell_school", same plain-tag convention as `BaseFeat.type`)
      declares which kind of pick a feat needs; `CharacterFeat` gained
      `chosen_weapon_id`/`chosen_skill_id`/`chosen_spell_school` (exactly one
      set, validated server-side against the feat's own `sub_choice_type` in
      `routers/characters.py`, not by a DB constraint — a CHECK can't reach
      into `base_feats`). The unique constraint now covers the sub-choice
      columns too, so an open-choice feat (Waffenfokus) can legitimately be
      taken twice at the same level for two different weapons — the old
      `(level_id, feat_id)` shape couldn't represent that at all. Tagged the
      7 feats whose own description already names a choice: Waffenfokus,
      Mächtiger Waffenfokus, Waffenspezialisierung, Mächtige
      Waffenspezialisierung ("weapon"), Fertigkeitsfokus ("skill"),
      Zauberfokus, Mächtiger Zauberfokus ("spell_school") — feats like
      Verbesserter Kritischer Treffer/Umgang mit exotischen Waffen that
      really do need a weapon pick per the real rules but whose seeded
      description text doesn't say so were deliberately left untagged (see
      todos.md's placeholder-content caveat) rather than guessed at. Added
      `GET /api/spell-schools` (distinct `BaseSpell.school` values — school
      still isn't its own catalog table) since Zauberfokus needed something
      to pick from. `CharacterCreate`/`CharacterRead`'s `feat_ids: list[UUID]`
      became `feats: list[FeatSelection]`; the creation wizard's
      `FeatsStep.tsx` now shows a weapon/skill/school dropdown for a tagged
      feat, and the character sheet/summary append the choice to the feat's
      display name (e.g. "Waffenfokus (Langschwert)").
- [x] **Waffenkatalog ohne Kampfwerte — Schema und Katalogzeilen ergänzt.**
      `BaseItem` hat jetzt reale Felder für `damage_small`/`damage_medium`
      (Schaden Klein/Mittel), `critical`, `weapon_range`, `damage_type`
      und `weapon_type` (Waffenproficiency einfach/Kriegswaffe/exotisch/
      Feuerwaffe — eigene Taxonomie, nicht zu verwechseln mit `weapon_group`,
      das weiterhin die Kämpfer-Waffengruppen Äxte/Bögen/Hämmer/… meint und
      unbefüllt bleibt), plus generisches `weight_lb`/`description`
      (Migration `alembic/versions/fd9e4b803833_...`, angewendet). Katalog
      per PRD-Import (`backend/scripts/import_waffen_prd.py`/
      `import_ausruestung_prd.py`, README §5) von 16 auf 205 Waffen- und von
      3 auf 45 Werkzeug-Zeilen erweitert — Zweihänder, Krummschwert,
      Streitaxt sind jetzt vorhanden. Bekannte Einschränkungen:
      - **Noch keine Angriffsbonus-/Schadensberechnung, die diese Felder
        liest** — reine Daten, keine Logik. Der Kämpfer-Waffentraining/
        Waffenmeisterschaft-Blocker (§5 der "Pick from a restricted list"-
        Historie) bleibt deshalb unverändert bestehen.
      - Von den 16 alten Platzhalter-Zeilen matchen 9 (Dolch, Kriegshammer,
        Kurzbogen, Kurzschwert, Langbogen, Langschwert, Rapier, Schleuder,
        Speer) exakt einen PRD-Namen und wurden um die neuen Felder
        angereichert (ID/Preis unverändert); 7 (Streitkolben, Handaxt,
        Kompositlangbogen, „Armbrust, leicht"/„Armbrust, schwer",
        Wurfmesser, Wurfnetz) matchen keinen PRD-Namen exakt (z. B.
        „Streitkolben" vs. PRDs „Leichter Streitkolben") und stehen
        unangetastet neben der neuen, korrekt benannten PRD-Zeile — noch ein
        Beleg für die in `todos.md` vermerkte Platzhalter-Namensproblematik,
        bewusst nicht automatisch zusammengeführt/umbenannt.
      - Gleiches gilt für alle 3 alten `tool`-Zeilen (Dietrich,
        Zauberkomponentenbeutel, Schreibfeder und Tinte) — keine matcht
        einen PRD-Namen (Dietrich z. B. heißt dort „Diebeswerkzeug").
      - Ein Preis-Widerspruch: Speer kostet in der alten Platzhalter-Zeile
        5 GM, laut PRD 2 GM — Platzhalterwert bewusst nicht überschrieben.
      - 16 neue Zeilen (14 Waffen, 2 Werkzeuge — u. a. Waffenloser Schlag,
        improvisierte Waffen wie Keule/Holzpflock, Schild-Einträge, deren
        Preis eigentlich in der Rüstungstabelle steht) hatten in der
        PRD-Quelltabelle keinen Preis (Zelle „-"); da `price` nicht
        nullable ist, wurde 0 als markierter Fallback statt einer Schätzung
        eingetragen — vor produktivem Einsatz zu prüfen.
      - Feuerwaffen (21 Zeilen) verlieren `misfire`/`capacity` beim
        Seed-Merge — keine Schema-Spalte dafür, bewusst außerhalb des Scopes
        dieser Erweiterung.
      - Die 250 Abenteuerausrüstungs-Zeilen aus demselben Import sind
        bewusst *nicht* mit übernommen worden (nur Waffen + Werkzeuge waren
        angefragt) — liegen weiterhin nur als Staging-Datei
        (`fixtures/imported/ausruestung_prd_import.json`) vor.
- [x] **Magische Verzauberung/Material als Berechnung statt Freitext —
      strukturierter Katalog umgesetzt, Berechnung bewusst weiterhin nicht.**
      `CharacterGear.enhancement`/`properties` waren rein deskriptiv (roadmap
      slice 4) — ein „+1, aufflammend, einschlagend, Adamant"-Zweihänder
      ließ sich zwar eintippen, hatte aber keine Auswirkung auf
      Angriffs-/Schadensbonus. Baut auf der Waffenkatalog-Erweiterung oben
      auf (keine Berechnung ohne Basis-Kampfwerte).

      Gegen <http://prd.5footstep.de/Ausruestungskompendium/MagischeWaffenundRuestungen/BesondereEigenschaftenvonWaffen>
      geprüft (2026-08-03), um zu sehen, was fürs Verdrahten fehlt: die ~80
      benannten besonderen Waffeneigenschaften (Nahkampf/Fernkampf/Munition,
      Bonusäquivalent +1 bis +5, Gesamtbonus-Deckel +10 aus Verbesserung +
      Eigenschaften) sind mechanisch keine homogene Gruppe, sondern mehrere
      grundverschiedene Effekt-Formen: flacher Elementarschaden on-hit,
      togglebar per Befehlswort (Aufflammen/Blitz/Eis); nur-bei-Krit-Zusatz-
      effekte, die mit dem Kritmultiplikator skalieren (Blitz-/Eis-/
      Flammeninferno, Donner mit permanenter Taubheit bei Rettungswurf-
      Fehlschlag); gesinnungsbedingter Bonusschaden + Fluch für den „falsch"
      gesinnten Träger, inkl. SR-Durchbruch (Heilig/Unheilig/Grundsatz/
      Anarchie); Bevorzugter-Feind-Muster gegen einen gewürfelten Kreaturen-
      typ (Verderben); Krit-Modifikatoren (Schärfe verdoppelt den Bedrohungs-
      bereich, Hinrichtung enthauptet bei bestätigtem Nat-20-Krit); zusätz-
      liche volle Angriffe (Schnelligkeit); Kampfmanöver-Boni (Duell,
      Entgegenwirkend, Bedrohlich als Verbündeten-Aura); SR-/DR-Unterlaufen
      on-hit (Beseitigend, Ausschaltend); Reichweiten-/Utility-Effekte
      (Distanz, Rückkehr, Suchen, Gerufen); eigenständig handelnde Waffen
      (Tanzen); Zauber speichern/stehlen (Zauberspeicher, Zauberraubend,
      Bannend/Bannexplosion); sowie zahlreiche Waffentyp-Restriktionen (nur
      Nahkampf/nur Fernkampf/nur Bögen/nur Feuerwaffen).

      Zwei getrennte, konkrete Lücken (nicht eine) folgen daraus: (a)
      `properties` als Freitext-Liste kann die Eigenschaften nicht
      strukturiert abbilden (Bonusäquivalent/Preis, Waffentyp-Beschränkung,
      gegenseitige Ausschlüsse wie Verlässlich vs. Mächtige Verlässlichkeit);
      (b) es existiert serverseitig noch gar kein Angriffs-/Schadenswurf-
      Endpunkt, an den sich eine Berechnung anschließen ließe —
      `rules/modifiers.py`s `Modifier`/`stack()` ist rein statisch/additiv,
      einmal pro Sheet-Aufbau berechnet, aktuell nur für die Rüstungsklasse
      aufgerufen, und kennt kein „ausgelöst bei Treffer"/„nur bei Krit"/
      „bedingt auf Gesinnung/Kreaturentyp" (deckt sich mit dem Kämpfer-
      Waffentraining-Punkt oben).

      **Entscheidung (2026-08-03, präzisiert): keine Berechnung, aber
      trotzdem durch ein `HANDLERS`-Registry.** Waffeneigenschaften laufen
      der Konsistenz halber durch dasselbe `dict[UUID, Callable]`-Muster wie
      `rules/race_abilities.py` (neues `rules/weapon_abilities.py` o. ä.) —
      jede Fähigkeit/jedes Item am Charakter soll über denselben Mechanismus
      aufgelöst werden, nicht nur die, die tatsächlich etwas berechnen, damit
      `sheet.py` nicht zwischen "Items mit Handler" und "Items ohne Handler"
      unterscheiden muss. Für die ganz überwiegende Mehrheit ist der Handler
      aber trivial: eine generische Factory, die nur den Katalogtext (Name +
      Beschreibung) fürs Sheet zurückgibt, ohne selbst zu rechnen — kein
      Anschluss an `rules/modifiers.py`, kein Angriffs-/Schadenswurf-Pfad
      nötig, exakt wie bei den unten unverdrahteten Rasseneigenschaften.
      Begründung fürs Nicht-Berechnen: die App ist ein Tischhilfsmittel für
      einen Spieler, kein Kampfsimulator. Von den ~35 Angriffs-/Schaden-
      relevanten Eigenschaften hängen ~19 von Gegnerdaten ab, die hier nie
      modelliert werden sollen (Gesinnung/Kreaturentyp/Zustand/
      Verfolgungshistorie des Ziels — Verderben, Heilig/Unheilig/Grundsatz/
      Anarchie, Auftauend/Erdend/Löschend/Neutralisierend, Zerschlagend,
      Planar, Grausam, Jagd/Lauernd/Tapfer, Listig) und weitere ~10 nur an
      den eigenen Krit-Wurf gekoppelt (Blitz-/Eis-/Flammeninferno, Donner,
      Säureexplosion, Hinrichtung, Glorreich, Unheilvoll, Versetzend,
      Zauberraubend) — der Spieler liest die Eigenschaft von der Waffe ab und
      rechnet sie am Tisch selbst dazu. Einzige Ausnahme mit eigenem,
      dünnerem Handler statt der generischen Text-Factory: Zornig/Kräftigend
      (siehe unten), sobald deren Zustands-Hinweis an slice 5 andockt — auch
      der rechnet aber nur einen Aktiv-Status ab, keinen Bonuswert.

      Datenmodell dafür so schlank wie möglich: `BaseWeaponSpecialAbility`
      (Katalog, composition-only wie `BaseFeat`) mit `name`,
      `bonus_equivalent` (1–5 — einzig strukturiert nötig, für Preis- und
      +10-Gesamtbonus-Deckel-Berechnung), `applicable_categories`
      (Nahkampf/Fernkampf/Munition — welche der drei PRD-Tabellen), einem
      kurzen `restriction_note`-Tag für die engeren Fußnoten-Einschränkungen
      (z. B. „nur Hiebwaffen", „nur Kompositbögen", „nur Feuerwaffen" —
      informativ für den Auswahl-Dialog, keine harte DB-Constraint, gleiches
      Muster wie die serverseitige statt DB-Constraint-Prüfung beim
      Talent-Sub-Wahl-Schema oben), und `description` (voller Regeltext, nie
      ausgewertet). Dazu eine Zuordnungstabelle `CharacterGearSpecialAbility`
      (gear_id, ability_id, unique pair — mehrere Eigenschaften pro
      Gegenstand). Keine Gegner-/Encounter-Daten, keine Berechnungs-Engine.

      Die einzigen zwei Eigenschaften, die vom **eigenen** Zustand des
      Trägers abhängen statt von Gegnerdaten (Zornig: nur im Kampfrausch;
      Kräftigend: nur nach Niederstrecken eines Gegners, solange nicht
      erschöpft/entkräftet) sind auch die einzigen, für die ein Zustands-/
      Rundenzähler wie für Kampfrausch überhaupt etwas bringen würde — das
      ist kein neues Konzept, sondern deckt sich mit dem „Aktive Effekte"-
      Punkt unten (slice 5, `ActiveEffect`-Tabelle mit Dauer-Tracking): sobald
      die existiert, könnte die Anzeige z. B. „Zornig: Kampfrausch aktiv,
      noch 4 Runden" neben der Waffe highlighten, dass die Eigenschaft gerade
      greift — weiterhin nur als Hinweis, nicht als eingerechneter Bonus.
      Kein Vorgriff auf slice 5 nötig, um Katalog/Anzeige oben zu bauen.

      **Umgesetzt (2026-08-03):** `BaseWeaponSpecialAbility`
      (`models/item.py`) + Zuordnungstabelle `CharacterGearSpecialAbility`
      genau wie oben entschieden, Migration `8dd1fbfa0f90` angewendet.
      Katalogdaten per neuem `scripts/import_waffeneigenschaften_prd.py`
      gegen die oben verlinkte PRD-Seite gezogen (93 Eigenschaften — die
      ~80er-Schätzung oben war grob; 3 davon ohne eigenen Fließtext auf der
      Quellseite, `description: null`, 2 mit mehrdeutigem `bonus_equivalent`
      aus einer Zwei-Stufen-Tabellensektion, ebenfalls `null` statt geraten
      — Details im Skript-Docstring) und per `build_weapon_abilities_seed.py`
      in die DB-Form transformiert; `app.seed.weapon_ability_seed` lädt sie
      idempotent. `rules/weapon_abilities.py`s `resolve()` löst jede
      Eigenschaft über dieselbe `HANDLERS`-Registry auf wie entschieden
      (aktuell leer, jede Eigenschaft fällt auf die generische Text-Factory
      zurück — kein Bedarf an konkreten Handlern, da noch keine einzige
      Eigenschaft eigenes Rechenverhalten hat). `GET /api/weapon-abilities`
      (Katalog-Listing) und `PATCH .../gear/{item_id}`s neues
      `special_ability_ids` (ersetzt die gesamte Zuordnungsliste, gleiche
      Semantik wie `properties`) verdrahten das bis zum Sheet durch
      (`sheet.py`s `_build_gear`, neues `specialAbilities`-Feld pro
      `GearItem`, Frontend-Typ in `types/character.ts` ergänzt). `properties`
      bleibt parallel bestehen für alles, was (noch) nicht im Katalog steht.
      Zornig/Kräftigend bekommen weiterhin keinen eigenen Handler (siehe
      oben, wartet auf slice 5); Preisberechnung/Angriffs-Endpunkt bleiben
      wie entschieden draußen.
- [x] **Wondrous-Item-Katalog mit echter Attributsboni-Wirkung.** Die 12
      kosmetischen Ausrüstungsplätze (roadmap slice 4) haben keine
      Katalogzeilen und keine Verdrahtung in `sheet.py`s
      Attributsberechnung — ein „Gürtel der großen Konstitution +2" oder
      „Stirnreif der enormen Intelligenz +2" hätte aktuell keine Wirkung.
      Bewusst nicht einfach durch Erfinden generischer Werte lösbar (gleiches
      Rateinhalt-Problem wie in `todos.md` an anderer Stelle beschrieben) —
      braucht echte, gegen eine Quelle geprüfte Item-Daten.

      Gegen <http://prd.5footstep.de/Grundregelwerk/MagischeGegenstaende/WundersameGegenstaende>,
      <http://prd.5footstep.de/Grundregelwerk/MagischeGegenstaende/MagischeRinge>
      und <http://prd.5footstep.de/Grundregelwerk/MagischeGegenstaende/Zauberstaebe>
      geprüft (2026-08-04). Alle drei folgen demselben Stat-Block-Muster
      (`Aura`/`ZS`, `Ausrüstungsplatz`, `Preis`, `Gewicht`, Fließtext
      `BESCHREIBUNG`, `ERSCHAFFUNG` mit Voraussetzungen/Kosten fürs
      Herstellen — Letzteres bleibt außen vor, kein Herstellungs-Feature
      geplant). Ringe haben eine Sonderregel (nur 2 gleichzeitig wirksam
      tragbar), die aber schon strukturell durch die zwei separaten
      `ring-links`/`ring-rechts`-Paperdoll-Slots in `equipment_slots.py`
      abgedeckt ist. Zauberstäbe sind strukturell anders: keine benannten
      Einzel-Katalogzeilen, sondern ein Item, dessen gespeicherter Zauber
      und Preis (Zaubergrad × Erschafferstufe × 750 GM) erst pro
      Charakter-Instanz feststehen.

      **Entscheidung (2026-08-04):** Ausrüstungsplatz/Preis/Beschreibung
      genügen als Katalogfelder nicht — Aktivierungsart und Nutzungs-/
      Ladungslogik sollen als echter Zustand pro Charakter mitgezählt
      werden können (Spieler will N-mal-pro-Tag-Nutzungen und
      Zauberstab-Ladungen tracken, nicht nur nachlesen). Composition/
      Computation-Trennung wie überall: Katalog beschreibt nur das Maximum,
      der veränderliche Zählerstand ist Instanzstatus auf `CharacterGear`
      (gleiche Begründung wie `enhancement` dort: ändert sich im Spiel,
      gehört nicht ins Katalog).

      `BaseItem`, neue nullable Spalten (nur für category
      `wondrous`/`ring`/`wand` befüllt):
      - `slot` — Paperdoll-Slot-Schlüssel aus `equipment_slots.py`
        (`guertel`, `hals`, `ring`, ... — Ringe bekommen den generischen
        Wert `ring`, gültig für beide Ring-Slots, statt zweier fixer
        Katalogzeilen pro Ring).
      - `activation` — `permanent` / `activatable`.
      - `uses_per_day` — die N in „N-mal pro Tag"; 1 deckt „einmal pro Tag"
        mit ab (keine separate Logik dafür, wie entschieden), `null` heißt
        entweder permanent oder unbegrenzt aktivierbar.
      - `max_charges` — Ladungs-Obergrenze (Zauberstab: 50), generisch
        gehalten für die seltenen Nicht-Zauberstab-Ladungsgegenstände
        (z. B. Edelstein des Hellen Scheins), falls die je aufgenommen
        werden.
      - `granted_ability`/`ability_bonus` — nur für die Attributsboni-
        Familie (Gürtel/Stirnreif/Handschuhe/Amulett der/des
        Stärke/Geschicklichkeit/Konstitution/Intelligenz/Weisheit/
        Charisma); jede Bonusstufe (+2/+4/+6) wird eine eigene Katalogzeile
        mit eigenem Preis, statt einer Preis-Tier-Liste in einem Feld —
        gleiches Muster wie `BaseWeaponSpecialAbility.bonus_equivalent` pro
        Zeile statt Tabelle-im-Feld.

      `CharacterGear`, neue nullable Spalten (Instanzstatus):
      - `stored_spell_id` — FK `BaseSpell`, nur bei Zauberstäben; ein
        einziger generischer `BaseItem`-Katalogeintrag „Zauberstab"
        (category `wand`) reicht, der gespeicherte Zauber ist reine
        Instanzsache.
      - `charges_remaining` — Zauberstab-Ladungszähler, zählt runter, wird
        nie automatisch zurückgesetzt.
      - `uses_remaining_today` — N-mal-pro-Tag-Zähler, zählt runter, wird
        nur durch die Rest-Aktion unten zurückgesetzt.
      - `is_active` — Toggle-Zustand für unbegrenzt aktivierbare, aber
        wertverändernde Items (z. B. Energieschildring: +2 RK nur solange
        aktiv) — auch wenn kein Nutzungslimit existiert, muss der
        Aktiv-Zustand gespeichert werden, damit er in eine Berechnung
        einfließen kann. Wird wie Zornig/Kräftigend bei den
        Waffeneigenschaften über `HANDLERS` aufgelöst, sobald ein Item
        tatsächlich etwas berechnet — die große Mehrheit bleibt generische
        Text-Factory ohne Anschluss an `rules/modifiers.py`.

      Neue Endpoints, bewusst schlank: `PATCH .../gear/{item_id}/use`
      (Ladung/Tagesnutzung verbrauchen, oder `is_active` umschalten) und
      ein minimaler Tagesabschluss-Endpoint, der nur
      `uses_remaining_today` auf `uses_per_day` zurücksetzt — **bewusster
      Teil-Vorgriff auf slice 5** (das dort geplante „Rest"-Konzept),
      gleiches Muster wie Rassen/Klassen/Skills, die aus FK-/Nutzungsgründen
      schon früher als geplant reale Tabellen bekamen. Kein Vorgriff auf
      slice 5s volle Dauer-/Effekt-Verfolgung — nur der eine schmale
      Ausschnitt, den dieser Slice selbst braucht.

      Slot-Validierung in `routers/characters.py`s `update_slot` muss dafür
      generalisiert werden: `SLOT_CATEGORY` bildet aktuell slot_key 1:1 auf
      `BaseItem.category` ab (reicht für `ruestung`/`schild`), für die 12
      Wondrous-Slots reicht das nicht (mehrere Slots teilen sich category
      `wondrous`) — zusätzlicher Abgleich gegen `BaseItem.slot` nötig.

      **Umgesetzt (2026-08-04):** Migration + Modellfelder wie oben
      entschieden (`item.py`, `character.py`). `rules/equipment_slots.py`s
      `SLOT_CATEGORY` deckt jetzt alle 14 Slots ab, neues `SLOT_TO_ITEM_SLOT`
      löst das Mehrere-Slots-teilen-sich-eine-category-Problem, in
      `update_slot` und `sheet.py`s Options-Aufbau gleichermaßen verdrahtet.
      `scripts/import_wondrous_items_prd.py` (UTF-8, nicht ISO-8859-1 wie
      die Waffeneigenschaften-Seite — dieselbe Site ist pro Seite
      uneinheitlich kodiert) zieht 176 Wundersame Gegenstände + 32 Ringe;
      `scripts/build_wondrous_items_seed.py` löst Slot-Text und Preis auf
      und mergt in `base_items.json` (286 → 507 Zeilen). Die 6 eindeutigen
      Einzelattribut-Items (Gürtel/Stirnreif für ST/GE/KO/IN/WE/CH) wurden
      in je 3 Zeilen (+2/+4/+6) mit `granted_ability`/`ability_bonus`
      gesplittet; mehrdeutige/mehrfach-attributige Varianten (Körperkraft,
      geistige Stärke/Überlegenheit, perfekter Körper) bewusst nicht
      geraten. Ein einzelner generischer `Zauberstab`-Katalogeintrag
      (category `wand`) deckt alle Zauberstäbe ab. `sheet.py`s neues
      `_gear_ability_bonuses()` addiert die Boni ausgerüsteter Items auf die
      effektiven Attributswerte. Neue Endpoints: `PATCH .../gear/{id}/use`
      (Ladung/Tagesnutzung verbrauchen), `PATCH .../gear/{id}/toggle`
      (`is_active`), `POST .../rest` (setzt `uses_remaining_today` zurück),
      `stored_spell_id` auf `PATCH .../gear/{id}` (nur für category `wand`).
      10 neue Tests in `tests/test_wondrous_items.py`.

      **Bewusste Lücke:** `activation`/`uses_per_day` bleiben beim
      Bulk-Import leer — die Fließtext-Varianz ("einmal pro Tag", "3 Mal pro
      Tag", "immer aktiv", togglebar per Befehlswort, ...) ist zu groß für
      eine zuverlässige Regex-Ableitung ohne falsch-positive Treffer;
      braucht einen manuellen Tagging-Pass wie beim Talent-Sub-Wahl-Schema
      (dort wurden auch nur die 7 eindeutigen Feats getaggt, nicht geraten).
      Bis dahin zeigt das Sheet für diese Items weder Ladungszähler noch
      Aktiv-Toggle an — rein deskriptiv wie zuvor, keine Regression.
- [ ] **Startgold/Vermögen nach Stufe (Wealth by Level).** Keine
      `characters.gold`-Spalte, keine Wealth-by-Level-Tabelle — bei Stufe
      12 wäre nach PF1e deutlich mehr Ausrüstung/Gold vorgesehen als das
      Datenmodell heute überhaupt kennt. Gehört strukturell zu
      Charaktererstellung (slice 2/3), nicht zu Ausrüstung (slice 4) selbst.
- [ ] **Aktive Effekte für permanente Boni außerhalb von Ausrüstung**
      (z. B. permanente Dunkelsicht, ein inhärenter +2-Attributsbonus).
      Deckt sich mit slice 5 (Effects/Conditions/Time), das komplett
      unbebaut ist — keine `ActiveEffect`-Tabelle existiert. Ein
      Beispielcharakter mit nur zwei *permanenten* (nicht rundenbasierten)
      Effekten bräuchte nicht zwingend die volle Zeit-/Dauer-Verfolgung
      dieser Slice, nur ein minimales "dieser Charakter hat dauerhaft
      Fähigkeit X" — eine mögliche thin-first-Reduktion von slice 5,
      genauer zu entscheiden, wenn diese Slice angegangen wird.

## Foundation (one-time, not a lifecycle stage)

Done — DB/ORM/migrations/test harness. Full detail: `roadmap_history.md`.

## Slices

### 1. User lifecycle (thin only)
Done — thin slice, proved the pattern. Full detail: `roadmap_history.md`.

### 2. Character creation — thin
Done — races tables, minimal `characters` table, creation/read/update/
delete endpoints, wizard persists instead of showing a mock banner. Full
detail: `roadmap_history.md`.

### 3. Character creation — thick (its own iterations, not one lump)
Done: ability scores/point-buy, class selection/storage, archetype + class
option-group persistence (`hit_dice`/favored class), skills, feats, traits,
starting spellbook/known spells, fully playable level-1 character (HP/BAB/
save progression), minimal starting gear. Full detail for all of these:
`roadmap_history.md`.

- [ ] Deliberately deferred further: archetype-conflict checking for
      classes (needs a data-model decision on which archetypes mutually
      exclude each other — not yet made; the equivalent question for races
      was resolved in slice 2).

- [ ] **Class-ability computation (`HANDLERS` registry, mirrors
      `rules/race_abilities.py`).** `BaseClassAbility`/`BaseClassAbilityGrant`
      (introduced for Kämpfer's bonus feat, then Waldläufer/Magier/
      Hexenmeister's data corrections — see `todos.md`) are composition-only
      today: which abilities a class/archetype/school/bloodline choice
      grants, and at what level, is real data, gated correctly by level and
      by `option_choice_id` (`sheet.py`'s `_build_class_features`) — but no
      ability's actual mechanical effect is computed anywhere. Concretely
      inert right now: Kämpfer's Rüstungstraining/Waffentraining/Tapferkeit
      numbers, Waldläufer's Erzfeind/Bevorzugtes-Gelände bonuses, all 26 of
      Magier's arcane-school powers (flat bonuses like Bezauberndes
      Lächeln's +2 Bluffen/Diplomatie/Einschüchtern, level-scaling ones like
      Starke Zauber's spell-damage bonus, and per-day-use pools like "3 + IN-
      Modifikator Mal pro Tag" abilities such as Säuregeschoss), and all 60
      of Hexenmeister's bloodline powers across its 10 bloodlines (same
      three shapes again: flat bonuses like Dämonische Blutlinie's Stärke
      des Abyss, level-scaling ones like Abnormale Blutlinie's Ungewöhnliche
      Anatomie, and per-day-use pools like Säurestrahl). Needs a
      `rules/class_abilities.py` `HANDLERS: dict[UUID, Callable]` keyed by
      `BaseClassAbility.id`, same hand-frozen-UUID convention as
      `race_abilities.py` — flat-bonus cases can likely share one generic
      handler factory (per CLAUDE.md's composition-vs-computation split),
      conditional ones (level-scaling, per-day pools) each need their own
      function. Where the effect is a passive numeric bonus (e.g. Bannzauber's
      Resistenz, Verzauberung's Bezauberndes Lächeln), this should feed the
      same `Modifier`/`stack()` design from slice 4/5 rather than a third
      bonus system. Scope this once slice 5 (Effects) has landed, since
      several of these abilities are duration/use-limited in the same way
      active effects are — not a slice-3 concern to retrofit now.
      **Temporary HP is a separate concern from the flat-bonus/Modifier
      shape above** (flagged 2026-08-09 while fixing the `damage_taken`
      clamp bug, see `adjust_hp`'s docstring): Kampfrausch's "2 temporäre
      Trefferpunkte pro Trefferwürfel" (scaling with Starker/Mächtiger
      Kampfrausch) needs its own tracked pool, not a `Modifier` on `hp_max`
      — it must be shown separately from real HP on the sheet, absorb
      damage before `damage_taken` does, and evaporate (not convert to real
      damage) when Kampfrausch ends. No schema for this exists yet
      (`Character` has no temp-HP column); likely a new nullable int
      column or a per-`CharacterEffect` amount, resolved the same
      `HANDLERS`-by-ability-id way as everything else here.
- [ ] **"Pick from a restricted list" unification** (feat pools, ability
      pools, spell pools, deterministic per-choice spell grants — generalizes
      past Kämpfer's hardcoded "combat" filter). Schema and seed data
      (phases 1–4) are fully in; validation/enforcement (phases 5–6) is
      still open. Full design rationale (the four table shapes), the
      per-class seeding history, and bugs found along the way are archived
      in `roadmap_history.md` (section "Pick from a restricted list
      unification — design + phases 1–4"). Still open:
      5. [ ] Backend: extend creation's feat validation to check aggregate
         eligibility counts, not just the total; expose resolved eligibility
         (per-character for Hexenmeister, since it depends on the chosen
         bloodline — same resolution shape as `_build_class_features`'s
         `option_choice_id` filtering). Extend the same validation to
         repeated ability-pool picks (Trick) using `grant_id`.
      6. [ ] Frontend: replace `LevelFeatStep.tsx`'s hardcoded `f.type ===
         'combat'` with a lookup against the resolved eligibility from step
         5; optionally surface a hint in `FeatsStep.tsx` at creation ("must
         include N combat feats").
      **Update (2026-08-04):** fixed a level-up bug found via manual play-
      testing (a Barbar's Kampfrauschkraft picks weren't offered at all) —
      `GET /api/class-level-options` (the level-up wizard's `ClassChoiceStep`
      data source) used to read a static `class_level_options.json` fixture
      that had gone stale against the real seeded tables (wrong group key —
      `"ragepower"` vs the real `"kampfrauschkraft"` — and 6 leftover
      placeholder choices instead of the real 28 imported rage powers). Now
      computed directly from `base_class_option_groups`/`_choices`/
      `_ability_grants` (matching a group's `label` to a `BaseClassAbility`
      name with 2+ distinct per-level grants to tell "recurring" apart from
      a one-time pick) — fixes this for Barbar/Entfesselter Barbar's
      Kampfrauschkraft and, as a side effect, Schurke's Trick and Mystiker's
      Offenbarung, which had the same staleness. The deleted fixture is
      gone; nothing else read it. Doesn't add `min_level` enforcement (a
      level-2 pick can still list a choice meant for level 8+) — still
      phase 5 above, not newly introduced by this fix.
      Also still open, out of scope for this effort: Kämpfer's
      Waffentraining/Waffenmeisterschaft (16 weapon rows exist by now, but
      with no combat-stat fields at all — see "Beispielcharakter" above for
      the fuller writeup), Magier's familiar-type choice under Arkane
      Verbindung, and the animal-companion branch of Waldläufer's Bund des
      Jägers — all three need a new catalog concept (weapon combat stats/
      familiars/animal companions), not just another `BaseClassOptionGroup`.
- [ ] **Class source-page fetch/preprocess tooling.** Every class data pass
      so far (Kämpfer, Waldläufer, Magier, Hexenmeister — see `todos.md`)
      manually curled the class's page from
      <http://prd.5footstep.de/Grundregelwerk/Klassen/…>, converted it with
      `html2text`, and read the result — repeated, ad-hoc, and wasteful: the
      Hexenmeister fetch alone was ~190 KB of HTML that html2text turned
      into 930 lines of plain text, of which the first ~200 were the
      site-wide nav sidebar (`Übersicht > Grundregelwerk > Klassen > …`,
      repeated on every single page) contributing nothing but token cost.
      The site's TLS cert also doesn't match its hostname (shared hosting —
      cert is for `*.your-server.de`), which is why plain `WebFetch` fails
      outright and a raw `curl -k`/`requests(verify=False)` fetch is needed
      instead; worth a one-line comment at the call site noting this is a
      deliberate, scoped skip (a docs mirror, not a service handling
      secrets) rather than a pattern to copy elsewhere.

      A small `scripts/fetch_prd_page.py` (or similar, root-level next to
      `dev.sh`) should: take a page path or full URL, fetch with cert
      verification disabled, decode as ISO-8859-1 (the site's actual
      encoding — `requests`/`curl` autodetection gets this wrong), strip the
      repeated nav sidebar/footer/license boilerplate before running
      `html2text` (or reimplement the bits of it actually needed — table
      layout survives html2text reasonably but is still fragile, see the
      Hexenmeister level-table parsing glitch below), and write the cleaned
      text to a local cache (e.g. `scratchpad/prd_cache/<slug>.txt` or
      similar, gitignored) keyed by page path so a re-run during the same
      data-entry pass doesn't refetch. Should also flag known parser
      footguns rather than silently mis-parsing: the Hexenmeister fetch's
      "Tabelle: Hexenmeister" (BAB/saves) table silently *dropped* the 1st-
      level row entirely (html2text's table-to-text conversion choked on
      that particular row), only caught because the level-1 text elsewhere
      on the page was cross-checked against it — a preprocessing pass
      should at minimum sanity-check that a level/stufe table's row count
      matches the class's expected level range (1–20) and warn if not.
      Same tool should work for the other outstanding source pages this
      project already links to (feats index, spell lists, races, prestige
      classes) so it isn't Klassen-specific.

### 4. Items / Inventory
Done — armor/shield gear table + equip slots, gear CRUD endpoints, shared
modifier/bonus-stacking design, real computed AC. Full detail:
`roadmap_history.md`.

### 5. Effects / Conditions / Time
Data model decided 2026-08-05. This app is play support, not a simulation:
it never tries to detect a real-world trigger itself (an ally being in
range, a poison's onset ticking on its own) — every influence on a
character, including ones the rulebook calls "passive" (a Paladin's aura),
is either applied from outside (a `BaseCondition` the player picks and
applies — poison, disease, curse, a GM-inflicted condition) or activated by
the character (a persistent spell/class ability, which also shows up under
"verfügbare Aktionen"). A wand/potion/scroll doesn't need a third source:
using one is "cast this known spell from a charge," reusing the spell path
— charge bookkeeping already lives in slice 4's `CharacterGear`. Animal
companions/familiars/eidolons don't exist in this app and are out of scope
entirely, not a category here.

- [x] `BaseCondition` catalog (`id`, `name`, `description`, `type`) —
      identity only, for conditions/poisons/diseases/curses that aren't
      already a `BaseSpell`/`BaseClassAbility` row. `type`
      ("condition"/"poison"/"disease") is a plain categorization tag, same
      convention as `BaseFeat.type` — for a future picker UI to group/filter
      by and to pick sensible default activation fields, not a computed
      rule. Seeded 2026-08-05: the ~33
      standard PF1e conditions (Verängstigt, Gelähmt, ...), hand-transcribed
      since that page isn't behind any PRD datatable, plus 35 example
      poisons and 11 example diseases fetched from the PRD's `.../Gebrechen/
      Gifte` and `.../Gebrechen/Krankheiten` pages (`scripts/
      build_conditions_seed.py` → `app/fixtures/seed/base_conditions.json`,
      loaded via `app.seed.condition_seed`). A poison/disease's SG/
      Inkubationszeit/Frequenz/etc. is still one formatted `description`
      block, same as `BaseSpell.description` holds a spell's full text — but
      revised 2026-08-05 (later the same day): where that text states a
      single fixed number rather than a dice roll, `default_incubation_rounds`/
      `default_duration_rounds`/`default_frequency_rounds`/
      `default_successes_required` also parse it out (round-normalized),
      re-derived by `build_conditions_seed.py` on every rerun rather than
      hand-maintained, so the activation popup (below) can pre-fill instead
      of the player retyping numbers already sitting in the description.
      Dice-based/unstated/unsupported-unit (weeks) values still stay `None`
      and are still typed in by hand. Note the `Frequenz` text's trailing
      "für N Rd./Min." clause (e.g. "1/Rd. für 6 Rd.") is deliberately *not*
      parsed into any of these — it reads like a duration cap distinct from
      the `successes_required` cure path, but nothing downstream tracks an
      occurrence count yet (see the open item below), so parsing it now
      would produce a column nothing reads.
- [ ] `BaseSpell`/`BaseClassAbility` each get an `is_persistent_effect`
      boolean — which ones create a tracked `CharacterEffect` row when
      activated (most spells/abilities are instantaneous and don't).
- [ ] `CharacterEffect` — one row per *applied instance*, not one row per
      character+effect: the same effect can be active on a character from
      two independent sources with two independent countdowns, and the
      schema must not block that even though most effects in practice won't
      stack this way (the stacking decision itself belongs to the handler,
      see below, not the schema).
  - `source_type` (`spell`/`class_ability`/`condition`) + `source_id` — a
      discriminated reference instead of three nullable FK columns, the same
      "plain-tag" convention as `BaseFeat.type`/`spell_school`.
  - `level` — the effect's potency/Stufe (e.g. caster level for an
      X/level spell); asked of the player at activation time since nothing
      else in the data model can derive it. Fixed once set — a failed save
      does not escalate it (confirmed 2026-08-05).
  - `incubation_remaining` / `duration_remaining` — plain round-based
      countdowns, both nullable (a buff spell only uses `duration_remaining`;
      a poison/disease uses `incubation_remaining` then switches to the
      frequency fields below).
  - `frequency_rounds` / `next_check_in` / `successes_current` /
      `successes_required` — for effects resolved via repeated saves
      (poison/disease) rather than a flat duration: `next_check_in` counts
      down to the next due save and resets to `frequency_rounds` after
      every save regardless of outcome; `successes_current` resets to 0 on a
      failed save; the row is deleted once `successes_current` reaches
      `successes_required`.
- [ ] Endpoints: activate (`POST .../effects`, picks a known spell/ability
      or a `BaseCondition`, only asks the player for values nothing else can
      supply — level, initial duration/incubation/frequency), remove
      (`DELETE .../effects/{id}`, manual cure/early end), record a save
      result (`POST .../effects/{id}/save-result`, `{success}` — only
      advances the counters above; the resulting stat impact stays
      computed at sheet-read time via `EFFECT_HANDLERS` off the row's
      current state, same composition-vs-computation split as everywhere
      else, not a separate mutation triggered here), and advance time (`POST .../advance-time`, `{unit}`, reusing the mock's
      existing round conversion: round=1, minute=10, hour=600, day=full
      rest). A day clears plain-duration effects (matches the old mock's
      "+1 Tag includes a rest") but *not* frequency-tracked ones — an
      ongoing poison/disease surviving a rest is correct PF1e behavior, so
      blanket-clearing it the way the old mock does would be a regression
      now that real duration tracking exists.
- [ ] Mechanical effect resolved via a new own-module registry,
      `rules/effects.py`'s `EFFECT_HANDLERS: dict[UUID, Callable[[list[
      CharacterEffect]], list[Modifier]]]` — kept separate from
      `rules/handlers.py`'s unified `HANDLERS` rather than merged into it,
      same as `weapon_abilities.py`'s own `HANDLERS` stays separate: the
      call signature differs (needs every one of the character's active
      rows for that `source_id`, not zero args), so it can't share the dict.
      Called once per distinct `source_id` with all of that character's rows
      for it, so the handler itself decides stacking (ability damage from
      two sources sums; the same fear condition from two sources doesn't
      double up) — reuses slice 4's `Modifier`/`stack` (`rules/modifiers.py`)
      rather than a second bonus-stacking implementation. No real
      conditions/handlers seeded yet, infrastructure only.
- [x] Ability damage/drain/burn — schema + plumbing, done 2026-08-06 (no
      handler yet, see open item below). `CharacterAbilityDamage` (table
      created 2026-08-05, `backend/app/models/character.py`, migration
      `f4549f885840`) — one running total per (character, ability, `kind` ∈
      damage/drain/burn; damage heals 1/ability/day of full rest, drain
      needs restoration magic, burn never heals — differ only in recovery,
      so all three subtract from the score the same way). `sheet.py`'s
      `_ability_damage_totals` now sums it per ability and subtracts from
      `effective_scores` before `ability_mods` is computed, so the
      score/save/mod math is already correct the moment something starts
      writing rows; `abilities[].damage` also exposes the raw per-ability
      total (0 for everyone today) so the frontend doesn't have to
      re-derive it. `AbilityScores.tsx` renders it as a small "-N" badge
      under the score when nonzero (`.ability .penalty`,
      `CharacterSheetPage.css`) — the UI shape discussed below, done ahead
      of the handler since it's harmless to ship while every value is 0.
      Fixture characters ('1'/'2', `character_1.json`/`character_2.json`)
      got `"damage": 0` added to each ability entry to match the type.
- [ ] **Generische Gifte pro Attribut + Rettungswurf-Erinnerung fürs UI
      (Entscheidung 2026-08-09, Umsetzung offen).** Anstoß: die meisten
      Bestiary-Gifte auf Monstern folgen immer demselben Muster (Injury/
      Inhaled/Ingested; Rettungswurf-Typ + SG; Frequenz; „X Schaden
      [Attribut]"; Heilung nach N Erfolgen), nur SG/Frequenz/Schadenshöhe
      wechseln pro Kreatur. Dafür braucht es keine eigene benannte
      `BaseCondition`-Zeile pro Monster (wie bei den 35 bereits importierten
      Beispielgiften), sondern sechs wiederverwendbare generische
      Katalogzeilen, eine pro Attribut (ST/GE/KO/IN/WE/CH), deren SG/
      Frequenz/Schaden der Spieler bei jeder Aktivierung frei einträgt —
      gleiches Prinzip wie `level`, das aus genau diesem Grund schon heute
      pro Aktivierung abgefragt statt aus dem Katalog gelesen wird.

      Schema-Erweiterung, minimal:
      - Sechs neue `BaseCondition`-Zeilen (`type: "poison"`, hand-vergebene
        UUIDs) — welches Attribut betroffen ist, steckt in der jeweiligen
        `EFFECT_HANDLERS`-Registrierung (composition-vs-computation wie
        überall sonst in diesem Projekt), keine neue Katalogspalte dafür
        nötig.
      - Neue nullable Spalte `CharacterEffect.ability_damage_fixed_amount:
        int | None` — bei Aktivierung gesetzt, wenn der Schaden pro
        Fehlschlag immer gleich hoch ist (z. B. „1 Schaden"); der Handler
        wendet dann automatisch denselben Wert bei jedem fehlgeschlagenen
        Check an.
      - `EffectSaveResult` (`schemas/character.py`, Body von
        `POST .../effects/{id}/save-result`) bekommt ein neues optionales
        Feld `damage_amount: int | None` — Pflicht genau dann, wenn
        `success=False` **und** `ability_damage_fixed_amount` der Zeile
        `None` ist (gewürfelter statt fixer Schaden, z. B. „1W3").

      **Bewusst keine Würfelformel-Spalte, die der Server selbst auswertet**
      (kein `dice: str`-Feld mit serverseitigem Würfeln) — es gibt in dieser
      Codebase nirgends eine Zufalls-/Würfellogik (`is_valid_rolled_hit_points`
      validiert bei TP-Würfen z. B. nur einen Wertebereich, würfelt nicht
      selbst), passend zur wiederholt getroffenen Haltung „Tischhilfsmittel,
      kein Kampfsimulator" (siehe Waffeneigenschaften-Entscheidung oben). Der
      Spieler würfelt am Tisch und trägt das Ergebnis ein, genau wie bei TP.

      **Gilt nicht nur für die 6 neuen generischen Zeilen**: die meisten der
      schon importierten 35 Gifte/11 Krankheiten (`todos.md`s Gruppe B/C)
      verursachen ebenfalls gewürfelten statt pauschal 1 Punkt Schaden —
      `ability_damage_fixed_amount` bleibt für diese in aller Regel `None`,
      der neue `damage_amount`-Pfad ist der Normalfall, nicht die Ausnahme.

      **Zusätzlich, noch nicht in `todos.md`s Gruppe A–C erfasst — UI-
      Erinnerung für fällige Rettungswürfe.** Sobald `next_check_in` einer
      aktiven Gift-/Krankheits-Effekt-Zeile 0 erreicht (`advance-time`),
      soll das Sheet proaktiv ein Modal zeigen statt den Spieler den
      Effekte-Tab selbst nach fälligen Checks durchsuchen zu lassen — z. B.
      „Reflexwurf oder 1W3 Schaden Geschicklichkeit" bzw. „Zähigkeitswurf
      oder 1W2 Schaden Konstitution". Braucht:
      - Neue Spalte `BaseCondition.save_type` (`"fort"`/`"reflex"`/`"will"`,
        plain-tag-Konvention wie `type`) — welcher Rettungswurf gefordert
        ist, steckt aktuell nur im Freitext von `description`. Nachträglich
        für alle ~79 Zeilen zu befüllen, nicht nur die 6 neuen generischen
        (gleicher Tagging-Durchgang wie die `activation_scope`-
        Klassifizierung in Slice 3).
      - Ein kurzer Anzeige-Text fürs Modal („1W3 Schaden Geschicklichkeit").
        Ob das ein neues geparstes `default_ability_damage_display`-Feld
        wird oder das Modal schlicht die vorhandene `description` zitiert,
        hängt davon ab, wie knapp sich die Beschreibungstexte tatsächlich
        zeigen — bei der Umsetzung zu entscheiden, nicht vorab zu raten.
      - Backend kennt „fällig" bereits (`next_check_in == 0` nach
        `advance-time`) — keine neue Spalte dafür nötig, nur `sheet.py`s
        `activeEffects` muss `save_type` (und den Anzeige-Text) mit
        durchreichen, damit das Frontend ohne Zusatz-Request rendern kann.
      - Frontend: neue Modal-Komponente (vermutlich neben
        `ActivateEffectModal.tsx`), sammelt beim Laden des Sheets alle
        fälligen Effekte ein und fragt sie nacheinander ab (Erfolg/
        Fehlschlag, bei Fehlschlag den gewürfelten Schadenswert), ruft dann
        `POST .../effects/{id}/save-result` mit dem erweiterten Body auf.
      - **Voraussetzung, noch nicht erfüllt**: `record_effect_save_result`
        (`routers/characters.py:829`) bucht bislang nur die Erfolgs-/
        Frequenz-Zähler, ruft `EFFECT_HANDLERS` aber noch gar nicht auf und
        schreibt keine `CharacterAbilityDamage`-Zeilen — diese Verdrahtung
        (nächster Punkt unten) ist Voraussetzung, nicht optional, sonst
        bewirkt das Modal nichts.
- [x] **First `EFFECT_HANDLERS` content, 2026-08-09: Entfesselter Barbar's
      Kampfrausch.** `rules/effects.py` was empty infrastructure until now
      (`todos.md`'s "Effekt-Handler-Inventar" tracks the rest). New
      `active_effect_modifiers()` groups a character's `CharacterEffect`
      rows by `source_id` and resolves each through `EFFECT_HANDLERS` once,
      returning a mixed-target `Modifier` list; `sheet.py`'s
      `build_character_sheet` computes it once and threads it into both
      `_build_equipment` (filtered to `ModifierTarget.AC`, merged into the
      same `stack()` pool as gear) and the `saves` list (filtered per
      save key via a new `SAVE_TARGET` map, added the same way ability mods
      already are). Kampfrausch (Entfesselter Barbar) itself: -2 AC
      (untyped, so it correctly stacks with everything), +2 Will (morale).
      Deliberately *not* modeled: the melee/thrown attack-and-damage bonus
      (no attack/damage-roll endpoint anywhere in this app, project-wide
      scope decision) and the 2-temp-HP-per-HD (needs its own tracked pool,
      see Slice 3's "Class-ability computation" item) — both documented in
      the handler's own docstring, not silently dropped. Regression test:
      `tests/test_effects.py::test_entfesselter_barbar_kampfrausch_applies_ac_penalty_and_will_bonus`.
      Full suite green (226 tests). Barbar's own (non-Entfesselter)
      Kampfrausch has a different id/effect shape (+4 ST/KO, +2 Will,
      temporary HP via the CON bump rather than a separate pool) and still
      needs its own handler — not done here, see `todos.md`.
- [ ] **Open — not wired yet:**
  - The actual `EFFECT_HANDLERS` entries that make a poison/disease
        *apply* ability damage (write/update `CharacterAbilityDamage` rows)
        when its frequency check fails, plus the natural-healing hook for
        temporary damage into `advance-time`'s day tick. The schema and
        display above are ready for this; nothing computes or writes the
        numbers yet — including the fixed-vs-rolled amount now decided in
        the generic-poison bullet just above, which this wiring must read
        (`CharacterEffect.ability_damage_fixed_amount` when set, else the
        `damage_amount` submitted with the save result). A successful save
        only stops *future* damage from that
        effect (see `successes_current`/`successes_required` above) —
        damage already dealt survives the cure and needs this separate
        healing path, not automatic removal when the `CharacterEffect` row
        is deleted (this is also why `AbilityScores.tsx` shows the penalty
        on the score itself rather than only in the Effekte panel — it can
        outlive its source).
  - Occurrence cap: several poisons (e.g. Drachenschleim, `Heilung: -`)
        have no save-based cure at all and only ever stop because the
        source text's `Frequenz` clause caps how many times they fire
        (e.g. "1/Rd. für 6 Rd." = 6 total). `CharacterEffect` has no counter
        for this, and `default_*` parsing above deliberately didn't extract
        it (see that bullet) since nothing would read it yet. Needs a
        `default_max_occurrences` column on `BaseCondition` (re-parsed the
        same way) and an `occurrences_remaining` column on `CharacterEffect`
        that decrements alongside `next_check_in` and clears the row at 0 —
        independent of, not a replacement for, the existing
        `successes_required` cure path, since some poisons have both and
        whichever condition is met first ends the effect.
  - Source breakdown on the ability-damage badge (e.g. "-2 von Arsen" on
        hover) isn't possible yet either — `CharacterAbilityDamage` only
        stores the summed total per ability+kind, not per source, on
        purpose (PF1e sums same-kind ability damage into one pool that
        heals as a pool, not per source — see that model's docstring), so
        a breakdown would have to be reconstructed from active
        `CharacterEffect` rows whose handler targets that ability, which
        only exists once the `EFFECT_HANDLERS` entries above are written.
- [x] Frontend, done 2026-08-05: a real character (`isRealCharacter`) now
      renders `RealEffectsPanel` (`frontend/src/components/sheet/
      RealEffectsPanel.tsx`) instead of the old mock `EffectsPanel` — the
      two stay side by side rather than one replacing the other, since
      fixture characters ('1'/'2') have no DB row for the new endpoints to
      act on. New types (`ActiveEffect`/`ConditionCatalogEntry`/
      `ActivatableRef`) added alongside the untouched mock-era `Effect`/
      `EffectDef` rather than reusing them (incompatible shapes — no
      source_type/level/frequency/successes on the old ones). `sheet.py`
      gained `activeEffects` (this character's `CharacterEffect` rows
      resolved to a display name via whichever catalog `source_type`
      points at), `activatableSpells`/`activatableClassAbilities` (known
      spells/granted abilities flagged `is_persistent_effect` — empty for
      every character today since none are seeded with the flag yet, same
      "wiring ready, no content" state as `EFFECT_HANDLERS`). The activate
      popover browses/searches/filters the 79-row `/api/conditions`
      catalog and asks only for the numeric fields nothing else can supply
      (level/duration/incubation/frequency/successes), matching the
      backend's own "player types in what the data can't derive" design.
      One UI bug found and fixed along the way: picking a row swapped the
      popover's content before the click event finished bubbling to
      `document`, so the page's existing global "click outside closes an
      open `<details>`" listener saw a detached `event.target` and closed
      the popover; fixed with a local `stopPropagation` rather than
      touching that shared listener.
- [x] Activation popover → popup, done 2026-08-05: the inline
      `effect-activate-inline` block became a real centered
      `ActivateEffectModal` (`frontend/src/components/sheet/
      ActivateEffectModal.tsx`), reusing the `.modal-overlay`/`.modal-dialog`
      primitive `ItemDetailModal` already established rather than a second
      popup pattern. Dauer/Inkubation/Frequenz each got a value + unit
      (Runde/Minute/Stunde/Tag) pair (`frontend/src/lib/time.ts`'s shared
      `ROUNDS_PER_UNIT`/`roundsToUnitValue`, factored out of
      `CharacterSheetPage.tsx`'s local copy) instead of a rounds-only input,
      converted to rounds client-side before `POST .../effects` — the
      backend still only ever stores rounds. Opening the popup pre-fills
      Stufe from the character's level (spells/class abilities only —
      conditions/poisons/diseases have no level concept) and Dauer/
      Inkubation/Frequenz/Erfolge from the new `default_*` catalog fields
      above (still just a starting point, not locked — the player can
      always override before confirming).
- [x] **Class abilities as persistent effects — `activation_scope` column,
      full catalog classified (2026-08-07).** `is_persistent_effect` marks
      *which* class abilities are trackable at all, but said nothing about
      *who* can be the target — a real gap once Barbar's Kampfrausch (only
      the owning character can ever benefit) sat next to Barde's Bardic
      Performance songs, some of which target allies who never took a
      single level of Barde. New `BaseClassAbility.activation_scope`
      (`str | None`, plain-tag convention, migration `aad95723a953`):
      `"self"` (only the owner can be the target — stays gated by that
      character's own granted abilities, `sheet.py`'s existing
      `activatableClassAbilities`), `"external"` (the ability's own text
      excludes the owner as a target, e.g. Barde's Lied des Erfolgs: "kann
      diese Fähigkeit nicht auf sich selbst wirken" — offered to *every*
      character regardless of what they have granted, same as
      `conditionsCatalog`), `"both"` (owner names themselves as an eligible
      target alongside allies, e.g. Lied des Mutes/Lied der Größe/Lied des
      Heldenmuts). `None` whenever `is_persistent_effect` is `False`.
      `sheet.py` gained `_build_external_class_abilities` (all
      `external`/`both` rows, unfiltered by ownership) alongside the
      existing `_build_activatable_class_abilities` (now filtered to
      `self`/`both`, so an `external`-only ability doesn't wrongly appear in
      its own owner's activation list); both feed the sheet as
      `activatableClassAbilities`/new `externalClassAbilities`.
      `RealEffectsPanel.tsx`'s picker merges the two (deduping an ability
      that's `both` and already granted, so it doesn't show twice), tagged
      "Klassenfähigkeit" vs. "Klassenfähigkeit (von außen)".

      Classification covers every class with seeded `BaseClassAbility` rows
      (Druide/Mönch/Paladin have none yet, per `todos.md`) — 529 rows
      surveyed, 78 flagged, via one hand-done pass (Barbar/Entfesselter
      Barbar/Barde, 126 rows, 6 flagged: 2× Kampfrausch → `self`; Lied des
      Mutes/Lied der Größe/Lied des Heldenmuts → `both`; Lied des Erfolgs →
      `external`) plus four parallel research-agent passes over the rest
      (403 rows, 72 flagged — Mystiker 123→25, Kleriker 109→30, Hexenmeister
      66→8, Magier 32→5, Waldläufer 19→2, Schildkämpfer 6→2, Schurke 33→0,
      Kämpfer 7→0, Zwei-Waffen-Kämpfer 8→0), each grounded in the actual
      seeded (already PRD-correct) description text rather than guessed,
      then spot-checked by hand against the source JSON before applying
      (one agent-proposed flag, Schurke's Widerstandsfähigkeit, was
      overridden back to unflagged — it only triggers reactively at negative
      HP, not something the player pre-emptively turns on, so it fit the
      rubric's own "not a triggered reaction" exclusion despite having a
      tracked duration).

      **Correction (2026-08-08):** the Hexenmeister/Magier agent pass
      initially excluded two touch-buff abilities — Hexenmeister's
      Berührung des Schicksals (Schicksalhafte Blutlinie) and Magier's
      Glück des Wahrsagers (Schule der Erkenntniszauber) — as "resolves
      within the same round, nothing meaningful to show as active
      afterward," even though both explicitly grant "für eine Runde"
      (1 round). That reasoning didn't survive contact with how the
      Kleriker pass treated the *same* shape (touch a creature, explicit
      1-round bonus, X/day — Hauch des Guten/Kraftschub/etc., kept as
      `both` since the app already tracks equally short conditions like a
      1W4-round Verängstigt; an explicit duration is what the rubric asks
      for, not a minimum length). Reclassified both to `both` for
      consistency (neither excludes the caster as a target, same as the
      Kleriker precedent) — found by spot-checking a description the user
      flagged by hand rather than by re-running the agent. 78 rows flagged
      total now (was 76).

      Rubric applied throughout (is_persistent_effect=true only when *all*
      hold): the character chooses to turn it on (not passive/reactive/
      instantaneous); it has an explicit tracked duration; it isn't a
      sub-modifier of an *already*-tracked parent effect (the ~40 individual
      Barbar rage powers and Bardenauftritt's individual songs' shared
      resource-pool wrapper stayed unflagged for this reason, same precedent
      as the weapon-abilities Zornig/Kräftigend decision); its target is a
      PC (owner and/or allies), never an enemy/opponent condition (this app
      has no GM/monster view). Short (even single-round) touch-buff domain
      powers were kept when the source text states an explicit round count
      (Kleriker's Wort der Begeisterung/Hauch des Guten/etc.) rather than
      excluded as "too short to matter" — the app already tracks equally
      short conditions (e.g. a 1W4-round Verängstigt), so an explicit
      duration is what the rubric asks for, not a minimum length.
      Full backend suite green (225 tests, one new:
      `test_sheet_class_ability_activation_scope_filtering`, a live
      self/external/both filtering check).

      **Repeatable approach, for the next class this needs running against**
      (Druide/Mönch/Paladin once they get seeded `BaseClassAbility` rows, or
      any future class/archetype import): this is a data-classification
      pass, not a code change — nothing below touches the schema again, it
      only ever adds rows to `base_class_abilities.json`'s existing
      `is_persistent_effect`/`activation_scope` fields.
      1. Find the class's `BaseClass.id` in `base_classes.json`, filter
         `base_class_ability_grants.json` by `base_class_id` (include its
         archetypes' own ids too, e.g. Kämpfer's Zwei-Waffen-
         Kämpfer/Schildkämpfer — they grant their own rows separately from
         the root class), collect the distinct `ability_id`s, and read each
         one's full `description` in `base_class_abilities.json`. Never
         invent or guess content — only classify what the (already
         PRD-verified) text actually says.
      2. Apply the four-part rubric from the paragraph above: activated (not
         passive/reactive/instantaneous) · has an explicit tracked duration
         (a stated round/minute/hour count is enough, however short — not a
         judgment call about whether it "matters") · isn't a sub-modifier of
         an already-tracked parent effect (an umbrella resource-pool
         ability like Kampfrauschkraft/Bardenauftritt, or a bonus that only
         applies "while raging"/"while in a stance," stays unflagged; the
         *parent* effect carries it, resolved later by a handler keyed to
         the parent's own `source_id`) · targets a PC, not an
         enemy/opponent (this app has no GM/monster view).
      3. For `activation_scope`, read specifically for whether the ability's
         own text excludes the owner ("kann ... nicht auf sich selbst
         wirken" → `external`), explicitly includes the owner alongside
         allies ("sich selbst oder einen Verbündeten", "einschließlich er
         selbst" → `both`), or never mentions anyone but the owner (→
         `self`).
      4. For a class with few rows (roughly Barbar/Barde's ~40-130-row
         scale), do the read-and-classify by hand. For a much larger one
         (Mystiker/Kleriker's 100+ rows), splitting the work across a few
         parallel research agents — each given this same rubric, the worked
         examples above, and one class to survey — kept the read-through
         thorough without spending the whole conversation's context on raw
         description text; each agent reports back *only* the rows it would
         flag (id/name/scope/one-line justification quoting the specific
         source text), never the much larger unflagged set. Always spot-
         check the borderline calls against the raw JSON yourself before
         applying — one flag from this pass (Schurke's Widerstandsfähigkeit)
         didn't survive that check.
      5. Apply via a small script keyed by id (never hand-edit the JSON
         inline — 500+ rows makes that error-prone), asserting every id
         exists and none were already flagged (catches an id typo or a
         double-classification pass colliding) before writing. Re-run
         `python -m app.seed.class_ability_seed` to push it into the dev DB
         (idempotent upsert, safe to re-run), then the full backend suite.

      **Still open** (this pass only changed *composition* — which
      abilities count and who they can target — not *computation*): none of
      the 78 flagged rows have an `EFFECT_HANDLERS` entry yet
      (`rules/effects.py`'s registry stayed an empty dict, per slice 5's
      "Open — not wired yet" above) — activating any of them creates a real
      `CharacterEffect` row and shows a real countdown, but produces no
      stat-modifier output. The rage-power/Bardic-Performance-song "resolved
      by a handler on the parent effect" design mentioned throughout this
      pass (reading which sub-abilities a character has, the same way
      Zornig/Kräftigend was decided for weapon properties) hasn't been
      built either — writing the first one or two of those handlers would
      be the natural next step once slice 3's "Class-ability computation"
      item (which already waits on this slice) gets picked up. Druide/
      Mönch/Paladin's own class abilities aren't imported into the DB at
      all yet (per `todos.md`) — nothing to classify there until that
      happens, at which point the recipe above applies unchanged.

### 6. Possible actions / legality checks
- [ ] Scope narrowly first: e.g. "can this spell be prepared/cast right
      now," "does this feat's prerequisites check out" — as checks added to
      existing endpoints, not a new generic legality framework.
- [ ] Depends on slices 3 (feats/spells data) and 5 (effects) being at least
      thin-complete.

### 7. Level-up — thin (done 2026-08-04, pulled forward ahead of slices 5/6)
Pulled forward ahead of Effects/Actions per the "Beispielcharakter" gaps
above — no hard dependency on either (only slice 6 declares one on slice 5;
slice 7 only ever depended on slice 3, already done), and it completes the
create → play → level-up loop end to end.

- [x] `POST /api/characters/{id}/level-up`: adds one new `CharacterLevel`,
      reusing creation's own validation/budget functions (`resolve_root_class`,
      `_validate_options`, `_validate_feat_sub_choice`, `_skill_points_total`,
      `_feat_max`, `spontaneous_known_budget`/`arcane_prepared_budget`/
      `known_grades`, `is_valid_rolled_hit_points`) called once for the
      character's classes before this level and once after, diffing the two
      for this level's own delta rather than re-deriving PF1e's level-up math
      separately. Covers single-class leveling, multiclassing into a
      brand-new class (archetype + level-1 option-group picks, same shape as
      one `CharacterCreate.classes` row), feat slots (a regular odd-level
      slot and/or a class bonus slot, both the same `feats` list — the
      backend never distinguishes the two, only the frontend UI explains
      them separately), one rank per skill, one ability-score increase every
      4th level, and one new known/prepared spell.
- [x] New `CharacterLevel.ability_increase` column (nullable `String(2)`) —
      the one new schema piece, needed so a history log can say *which*
      level got its ability increase; the score itself still only lives on
      `Character.ability_score_*`.
- [x] `GET /api/characters/{id}/history` + `.../progression`'s `history`
      field, both backed by one shared `sheet.py` helper
      (`build_character_history`) reconstructed purely from `CharacterLevel`
      audit rows — no separate `history` table turned out to be needed after
      all, since every level-up fact already has a per-level home.
- [x] `LevelUpWizardPage` now posts to the real endpoint and re-fetches
      `.../progression` for its summary/history display, instead of writing
      to `AppStateContext` (`progressionOverrides`/`getProgressionOverride`/
      `setProgressionOverride` removed entirely, along with
      `lib/applyLevelUp.ts`). Added the missing HP-roll step
      (`HitPointsStep.tsx` — creation never needed one, it only ever creates
      level-1 characters, always auto-maxed) and the feat sub-choice dropdown
      in `LevelFeatStep.tsx` (ported from creation's `FeatsStep.tsx`,
      `LevelUpOptions` extended with `items`/`spellSchools`).
- [x] `backend/tests/test_level_up.py` (20 tests): odd/even-level feat
      gating, the fighter bonus feat slot, the 4th-level ability increase,
      skill-point delta, spontaneous/arcane-prepared spell budgets,
      multiclassing with archetype/option-group picks, and the progression/
      history endpoints reflecting a real level-up. Full backend suite green
      (211 tests). Manually driven end-to-end in the browser (Playwright)
      against the running dev servers.

  **Known gap, not fixed here:** `existing_level_options` (a class's
  recurring per-level picks, e.g. Waldläufer's 2nd favored enemy at level 5)
  validates against `base_class_option_groups`, same as creation's own
  option groups — for classes whose recurring picks were never seeded there
  at all (Waldläufer's `enemy`/`terrain`), a level-up submitting one will
  still 422. Pre-existing DB-completeness gap, not introduced by this slice;
  same category as the "Pick from a restricted list" open phases above.
  (The *other* half of this gap — classes that *do* have real seeded data
  but weren't being offered it, e.g. Barbar's Kampfrauschkraft — was a real
  bug, not just a gap, and is fixed; see that section's 2026-08-04 update.)

  **Bugs found via manual play-testing, fixed 2026-08-04:** two issues
  surfaced leveling up a Barbar in the running app (not caught by the tests
  above, which never happened to exercise either path):
  1. Kampfrauschkraft picks weren't offered at all — see the "Pick from a
     restricted list unification" section's update above (stale
     `class_level_options.json` fixture, wrong group key).
  2. `skill_ranks` only ever let a given skill gain +1 rank per level-up,
     even one with 0 prior ranks — checked against
     <http://prd.5footstep.de/Grundregelwerk/Fertigkeiten-erwerben>, whose
     only stated cap is "never more ranks in a skill than character level,"
     not "+1 per level-up." Changed `LevelUp.skill_ranks` from `list[UUID]`
     (implicitly "+1 each") to `dict[str, int]` (this level's own rank
     *delta* per skill, mirroring `CharacterCreate.skill_ranks`'s shape
     exactly) — a previously-untrained skill can now legally take several
     new ranks in one level-up, capped only by the level-up's skill-point
     budget and `existing_ranks + new_ranks <= new_total_level`.
     `LevelSkillsStep.tsx`'s one-shot toggle became a +/- stepper (mirrors
     creation's own `SkillsStep.tsx`); `LevelUpSummaryStep.tsx` shows the
     actual rank count instead of a hardcoded "+1 Rang". 2 new backend
     tests; live-verified in the browser (3 ranks into a fresh skill in one
     level-up).

  **More bugs found via manual play-testing, fixed 2026-08-04 (same
  session):** four more issues, all on the same Barbar:
  3. A regression from fix 1 above: `/api/class-level-options`'s `"max"`
     was set to the option group's own `max_choices` (10 for
     Kampfrauschkraft — a *lifetime* total across the whole career), not
     "picks allowed at this one occurrence" (always 1 for every recurring
     group found so far) — let the wizard offer selecting 10 rage powers in
     a single level-up. Fixed in the endpoint (`"max": 1`, hardcoded with an
     explanatory comment) *and* independently enforced server-side in the
     level-up endpoint itself (`len(choices) > 1` per group is rejected
     regardless of what the client sends).
  4. `BaseClassOptionChoice.min_level` was never checked (roadmap's own
     "Pick from a restricted list" phase 5) — a level-2 Barbar could pick
     "Innere Zähigkeit" (needs level 8). `_validate_options`
     (`routers/characters.py`) now takes the character's level *in that
     class* and rejects a choice whose `min_level` isn't met yet — wired
     through both level-up call sites and creation's (computing the
     per-class total level across every `ClassSelection` row for creation,
     the receiving class's own new level for level-up).
  5. The favored-class bonus (+1 HP or +1 skill rank on a level in the
     favored class — same source page as fix 2: "Charaktere, die eine Stufe
     in ihrer bevorzugten Klasse aufsteigen, erhalten die Möglichkeit, 1
     zusätzlichen Fertigkeitsrang oder 1 zusätzlichen Trefferpunkt zu
     bekommen") wasn't implemented at all. New `LevelUp.favored_class_bonus`
     (`"hp" | "skill" | None`), required exactly when the receiving class is
     the character's favored one (checked via `CharacterClass.is_favored`);
     "hp" adds 1 to the stored `CharacterLevel.hit_points`, "skill" adds 1
     to that level's skill-point budget. New `HitPointsStep.tsx` section
     (chip picker) asks for it when applicable; `CharacterProgression`
     gained `classes[].isFavored` to know when to ask. Race-specific favored
     class bonus options (Advanced Race Guide/APG) are a known follow-up —
     `hp`/`skill` should become two universal entries in the same
     "pick 1 of N legal options" mechanism already used for Kampfrauschkraft
     etc., not stay a hardcoded pair; see `todos.md`'s "Volksspezifische
     Optionen zur Bevorzugten Klasse" item for the planned shape.
  6. The level-up wizard's skill-point budget display
     (`skillPointsForThisLevel`, `levelUpCalculations.ts`) never included a
     race's flat skill-point-per-level bonus (Human's "Geschult") — a
     backend-only bug this was not: `_skill_points_total`
     (`routers/characters.py`) already included it correctly, so a Human
     Barbar's level-up would *accept* 5 skill picks server-side while the UI
     showed and enforced only 4, silently blocking the 5th pick through the
     UI. Added `raceGrantsSkillBonusPerLevel` (mirrors creation's
     `skillPointsTotal` exactly, including the alt-trait-trades-it-away
     check) — needed threading `CharacterProgression.altTraits` and
     `LevelUpOptions.races` through, both new.

  10 new backend tests across `test_level_up.py`; all four fixes
  live-verified in the browser (Playwright) against the running dev
  servers — the Kampfrauschkraft picker now shows "(0/1)" with the real 28
  choices, the favored-class chip picker renders and is required, and a
  Human Barbar's skill-point display now reads 6/6 (4 base + 1 Geschult + 1
  favored) instead of 4/4.
- [ ] Deliberately deferred further: a per-level-up "confirm and go back to
      the character sheet" navigation nicety, wealth/gold gained per level
      (depends on the still-open Wealth-by-Level item above), and any
      class-ability *computation* a new level might newly enable (deferred
      to slice 3's own "Class-ability computation" item, which already
      waits on slice 5).

### 8. Reference-data migration (later, not upfront)
- [ ] Move classes/feats/spells/items/effects from JSON fixtures into
      database tables + seed scripts, once the schemas from slices 1–7 have
      stabilized against real usage. Races are already handled in slice 2.

## Explicitly out of scope here

Already tracked/deferred elsewhere in `todos.md`: localization content
(DE/EN), auth/login flow, GM view, full-text compendium search.
