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
- [ ] Active-effects table with duration tracking.
- [ ] Activate/deactivate/custom-effect/advance-time/rest endpoints.
- [ ] Reuse the modifier design from slice 4 rather than inventing a second
      one.

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
  (still only in the `class_level_options.json` fixture), a level-up
  submitting one will 422. Pre-existing DB-completeness gap, not introduced
  by this slice; same category as the "Pick from a restricted list" open
  phases above.
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
