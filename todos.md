# Todos / Offene Punkte

Zentrale Liste offener Punkte für das Projekt — sowohl grundsätzliche
Architektur-/Anforderungsentscheidungen als auch konkrete Lücken in den
bestehenden UI-Mocks. Ersetzt `offene_punkte_ui_mocks.md` (Inhalt unten
übernommen).

## Architektur- & Anforderungs-Checkliste

Aus der Checkliste in `requirements_v2.md` (§8), Stand dort noch offen:

- [ ] **Datenmodelle**: Teilweise definiert (siehe `readme.md`: Charakter, Charakterstufen, Klassen, Skills, Attribute, Rassen, Feats). Es fehlen noch Archetypen, Ausrüstung, Wesenszüge, aktive Effekte/Zustände, Session-Logik und Verlaufshistorie.
- [ ] **Anwendungslogik für Fähigkeiten, Effekte und Zustände**: Noch nicht festgelegt.
- [ ] **Authentifizierung/Benutzerverwaltung**: Für das MVP bewusst ausgeklammert (siehe `requirements_v2.md` §7, local-only). Offen ist noch, *wie* das Design eine spätere Ergänzung ermöglichen soll.
- [ ] **Technische Architektur**: `readme.md` benennt bereits einen Zielstack (React, FastAPI, PostgreSQL mit Vector-Extension, Docker/Podman) — das widerspricht dem "Noch nicht"-Status in der `requirements_v2.md`-Checkliste. Sollte abgeglichen/bestätigt werden, damit beide Dokumente konsistent sind.
- [ ] **Lokalisierungs-/Übersetzungsansatz**: Noch nicht definiert (nur Anforderung: Deutsch Standard, Englisch zusätzlich).
- [ ] **Qualitätskriterien** (Sicherheit, Zuverlässigkeit, Performance): Noch nicht festgelegt.

## Beispielcharakter — Vollständigkeitslücken

Beim Versuch, einen konkreten Level-12-Mensch/Barbar (Talente, Kampfrausch-
kräfte, benannte Magie-Ausrüstung, frei eingegebene Attributswerte, zwei
permanente aktive Effekte) über die App zu erstellen, wurden mehrere echte
Lücken gefunden, die keiner bestehenden Slice-Zeile zugeordnet waren.
Vollständige Analyse, jede Zeile mit Verweis auf die zuständige Slice bzw.
den zuständigen Code, in `roadmap.md`s Abschnitt „Beispielcharakter
(Referenz-Charakter für Vollständigkeitsprüfung)" — hier nur die
Kurzfassung als Einstiegspunkt:

- [x] Talent-Sub-Wahl-Schema (welche Waffe/Fertigkeit ein Talent betrifft,
      z. B. Waffenfokus → Langschwert) — done, see `roadmap.md`.
- [x] Waffenkatalog ohne Kampfwerte — Schema-Felder (Schaden/kritischer
      Bereich/Reichweite/Waffentyp) ergänzt und Katalog von 16 auf 205
      Waffen-Zeilen (plus 3→45 Werkzeuge) aus `prd.5footstep.de` erweitert,
      siehe `roadmap.md`. Die eigentliche Angriffsbonus-/Schadensberechnung,
      die diese Felder liest, bleibt offen (neuer Punkt unten).
- [ ] Item→Skill-Check-Bonus nicht verdrahtet (z. B. Diebeswerkzeug sollte
      einen Bonus auf Mechanismus ausschalten geben statt nur den
      Improvisations-Malus zu vermeiden) — `CharacterGear` ist bisher nur an
      die AC-Berechnung angebunden, keine Verbindung zu Fertigkeitswürfen
      existiert. `roadmap.md`.
- [ ] Magische Verzauberung/Material als Berechnung statt Freitext —
      `roadmap.md`.
- [ ] Wondrous-Item-Katalog mit echter Attributsboni-Wirkung — `roadmap.md`.
- [ ] Freie Attributseingabe / höheres Punktekauf-Budget (aktuell fest auf
      `{10, 15, 20, 25}` Punkte begrenzt) — `roadmap.md`.
- [ ] Startgold/Vermögen nach Stufe (Wealth by Level) — `roadmap.md`.
- [ ] Aktive Effekte für permanente Boni außerhalb von Ausrüstung — deckt
      sich mit roadmap Slice 5 (Effects/Conditions/Time), komplett offen.
- [x] Barbar — vollständig gegen `prd.5footstep.de` importiert (Kampfrausch,
      Kampfrauschkräfte, Klassenschale, Klassenfertigkeiten-Fix), siehe
      `todos_history.md`.

## Referenzdaten-Inhalte sind Platzhalter, keine geprüften Regeln

Die konkreten Inhalte der Referenzdaten — Fertigkeitsnamen (`base_skills.json`),
Rasseneigenschaften/-namen (`base_races.json`, `base_race_abilities.json`),
Klasseneigenschaften (`classes.json`, `base_classes.json`) usw. — sind aktuell
von einem LLM plausibel geraten, nicht aus dem tatsächlichen Pathfinder-1e-
Regelwerk extrahiert. Namen, Attributszuordnungen, Klassenfertigkeiten und
Rassenboni können daher im Detail falsch sein. Für die aktuelle Phase reicht
das aus, um das Datenmodell und alle Use Cases (Erstellung, Validierung,
Persistenz) durchzuspielen — das ist bewusst kein Blocker für die laufende
Slice-Arbeit.

- [ ] **Vor dem produktiven Einsatz**: sämtliche Seed-/Fixture-Inhalte gegen
      das echte Regelwerk prüfen und einzeln (nicht als Bulk-Ersetzung)
      korrigieren, sobald der jeweilige Datenbereich (Rassen, Klassen,
      Fertigkeiten, später Talente/Zauber/Gegenstände) strukturell
      abgeschlossen ist — betrifft `backend/app/fixtures/seed/*.json` und die
      verbleibenden `backend/app/fixtures/*.json`. Begonnen, eine Rasse/
      Klasse nach der anderen (nicht als Bulk-Ersetzung), gegen
      `prd.5footstep.de` (deutsches PF1e-SRD) als Quelle:
  Alle bisher gegen die Quelle geprüften und korrigierten Rassen/Klassen
  (Mensch, Halbling, Halb-Ork, Elf; Kämpfer inkl. Zwei-Waffen-Kämpfer/
  Schildkämpfer, Waldläufer, Magier, Hexenmeister, Schurke, Mystiker,
  Kleriker, Barde, Entfesselter Barbar, Barbar; diverse Nachträge zu
  Options-Gruppen/Talentpools) sind archiviert in `todos_history.md`. Noch
  offen:
  - [ ] **Restliche Klassen offen.** Testnutzung als Priorisierungssignal
        (wie oft eine Klasse namentlich in `backend/tests/*.py` vorkommt,
        Stand 2026-07-31):

        | Klasse | Testerwähnungen |
        |---|---|
        | Kämpfer | 28 (bereits korrigiert, siehe oben) |
        | Waldläufer | 18 (bereits korrigiert, siehe oben) |
        | Magier | 18 (bereits korrigiert, siehe oben) |
        | Hexenmeister | 8 (bereits korrigiert, siehe oben) |
        | Schurke | 5 (bereits korrigiert, siehe oben) |
        | Mystiker (vormals Orakel) | 3 (bereits korrigiert, siehe oben) |
        | Kleriker | 3 (bereits korrigiert, siehe oben) |
        | Barde | 1 (bereits korrigiert, siehe oben) |
        | Barbar | 0, aber seit 2026-08-03 vollständig korrigiert (siehe oben) |
        | Druide, Mönch, Paladin | 0 |

        Zusätzlich schon teilweise real hinterlegt (unabhängig von der
        Testnutzung): Zauber-Tabellen (`base_class_spells*.json`) für Magier/
        Barde/Mystiker; Options-Gruppen (Domänen/Bindungen) für
        Druide/Waldläufer.

        **Vorschlag für die Reihenfolge:** Kämpfer, Waldläufer, Magier,
        Hexenmeister, Schurke, Mystiker und Kleriker sind erledigt (siehe
        oben) und decken zusammen bereits ~98 % der Testerwähnungen sowie
        die wichtigsten mechanischen Achsen ab (volles GAB mit Bonustalenten,
        volles GAB als Teilzeit-Zauberwirker divine-spontan, halbes GAB
        arkan-vorbereitet, halbes GAB arkan-spontan, 3/4 GAB
        fertigkeitsbasiert ohne Zauber, 3/4 GAB divine-vorbereitet mit
        Domänen). Barde/Druide/Mönch/Paladin haben aktuell keine oder kaum
        Testabdeckung und sind — analog zu Zwerg/Gnom/Halbelf bei den
        Rassen — gute Kandidaten, um sie beim nächsten Aufräumdurchgang als
        ungeprüftes Platzhaltermaterial zu entfernen, statt sie einzeln zu
        verifizieren. Barbar ist davon ausgenommen und inzwischen vollständig
        korrigiert (siehe `todos_history.md`) — ein Löschen hätte jetzt echte,
        sourced Daten verworfen statt geratenes Platzhaltermaterial.

  - [ ] **Bekannte Berechnungslücken, entdeckt bei der Halbling-Korrektur**
        (nicht Halbling-spezifisch, betrifft potenziell jede Rasse):
    - Volksboni auf Rettungswürfe (z. B. Halblingsglück +1 auf alle RW,
          Furchtlos +2 gegen Furcht) und auf Fertigkeitswürfe (z. B. Wendig,
          Geschärfte Sinne) fließen nirgends in `Character.saves` bzw. die
          Fertigkeitsberechnung in `sheet.py`s `_build_skills` ein — anders
          als Menschs „Geschult" (Slice: Mensch-Korrektur) wurde das hier
          nicht mitgebaut, weil `Character.saves` aktuell eine reine
          Modell-Property ohne DB-Zugriff ist; das bräuchte einen eigenen
          Architekturschritt (ähnlich der Modifier-Stacking-Lösung aus
          Slice 4), keinen Nebeneffekt einer Rassen-Korrektur.
    - Gewählte Alternativmerkmale, die eine andere Rassen-Berechnung
          überschreiben sollten (z. B. „Schnell zu Fuß" müsste die
          Bewegungsrate auf 9 m ändern), wirken sich aktuell nicht aus:
          `rules/speed.py`s `race_speed()` liest nur die
          nicht-alternativen Grants, nicht `CharacterRacialChoice` (die
          gewählten `alt_traits`). Composition (welches Merkmal gewählt
          wurde) ist korrekt gespeichert, die Auswirkung auf die
          Berechnung fehlt noch.

## UI-Mocks — Offene Punkte

Abgleich der bestehenden Mocks (`pathfinder-mock.html` — Charakterbogen,
`pathfinder-character-creation-mock.html` — Charaktererstellung,
`pathfinder-levelup-mock.html` — Stufenaufstieg) gegen `requirements_v2.md`.

### MVP-relevant

- [x] **Rast-/Zeitmechanik (Grundmechanik)**: `pathfinder-mock.html` hat jetzt eine Zeit-Button-Gruppe im Effekte-Panel (+1 Runde / +1 Minute / +1 Stunde / +1 Tag), die Rundenzahlen auf den Effekte-Seals herunterzählt und abgelaufene Effekte in die „Verfügbar"-Liste zurückschiebt; „+1 Tag" schließt eine Rast ein und löscht alle aktiven Effekte/Zaubervorbereitungen. Offene Teil-Punkte dazu:
  - [ ] **Kurze Rast vs. Tageswechsel nicht unterschieden**: „+1 Tag" behandelt Rast und Tageswechsel aktuell als ein und dasselbe. Falls später eine kurze Rast (ohne vollen Tagesfortschritt, z. B. Zauber-Vorbereitung erneuern ohne Kalender weiterzuschalten) benötigt wird, braucht es einen eigenen Button/eigene Logik.
  - [ ] **Tagesbasierte Effekte (Gift-/Krankheitsfolgeschaden) nicht modelliert**: Die aktuelle Logik kennt nur Rundenzähler und einen kompletten Reset bei „+1 Tag". Effekte, die täglich neu ausgewertet werden müssen (z. B. Gift mit Folgeschaden nach 24h, Krankheitsverlauf), werden nicht simuliert.
  - [ ] Nur im Charakterbogen-Mock umgesetzt, keine Session-/Datenpersistenz (rein clientseitiger DOM-Zustand, kein Speichern).
- [ ] **Zustand/Effekt frei hinzufügen**: Die „Verfügbaren Zustände" im Charakterbogen sind eine feste, vordefinierte Liste zum Aktivieren. Es fehlt eine Möglichkeit, einen neuen Zustand/Effekt mit frei wählbarer Dauer manuell einzutragen (z. B. ein vom Spielleiter verhängtes Gift mit 5 Runden Dauer).
- [ ] **Zauberbuch als laufende Inventarliste**: Laut Requirement 2.2 soll das Zauberbuch „wie das Inventar verwaltet" werden (Zauber hinzufügen/entfernen über die Zeit, z. B. nach Fund einer Schriftrolle). Aktuell existiert das nur als einmaliger Picker bei Erstellung/Stufenaufstieg — keine „Zauber zum Zauberbuch hinzufügen"-Aktion im laufenden Charakterbogen.
- [ ] **Charakterliste/-verwaltung**: Der Header-Picker für „Charakter" in `pathfinder-mock.html` ist nur ein Dropdown-Stub. Es fehlt eine echte Übersicht (Liste/Karten) aller eigenen Charaktere zum Auswählen, Umbenennen oder Löschen.
- [ ] **Nutzerverwaltung**: Der „+ Neuer Nutzer"-Button im Header ist ebenfalls nur ein Platzhalter ohne zugehörigen Mock.
- [ ] **Regelhilfe/Kompendium**: Requirement 2 verlangt „Regelhilfe mit Regeltexten zu Fähigkeiten". Die bestehende Suche im Charakterbogen durchsucht nur die Daten des aktuellen Charakters, nicht eine durchsuchbare Regel-Datenbank (Talente, Zauber, Klassenfähigkeiten mit vollem Text).
- [ ] **Mehrere Archetypen pro Klasse**: Requirement 2.1 erlaubt mehrere, sich nicht widersprechende Archetypen gleichzeitig auf einer Klasse. Die Wizards (Erstellung & Stufenaufstieg) haben aktuell nur ein Einzel-Dropdown pro Klasse, keinen Mehrfach-Picker mit Konfliktprüfung.

### Bekannte Detail-Lücken in den bestehenden Mocks

- [ ] **Kämpfer-Bonustalent**: Der Kämpfer bekommt zusätzlich zum normalen Talent auf ungeraden Stufen ein Bonus-Kampftalent auf jeder geraden Stufe. Das würde die Zähllogik im Talente-Schritt selbst ändern (nicht nur eine neue Auswahlgruppe) und ist im Stufenaufstiegs-Mock bewusst noch nicht umgesetzt.
- [ ] **Terminologie „Zauberbuch"**: Im Charakterbogen-Mock ist der Ausrüstungs-Tab für die Waldläufer-Zaubervorbereitung mit „Zauberbuch" beschriftet, obwohl der Waldläufer ein göttlicher, vorbereitender Zauberwirker ohne echtes Zauberbuch ist (nur arkane Vorbereiter wie der Magier führen laut Requirement 2.2 ein Zauberbuch).

### Später / Ausblick (laut Requirements bewusst nicht MVP)

- [ ] Klassen-/Archetypen-Referenztabelle („Archetypen werden in der Klassen-Tabelle verlinkt", Requirement 2.1)
- [ ] Spielleiter-Ansicht (Requirements Abschnitt 3: „spätere Erweiterung")
- [ ] Echte Mehrsprachigkeit DE/EN — aktuell nur ein Sprach-Dropdown ohne übersetzte Inhalte
- [ ] Auth-/Login-Flow (laut MVP-Abgrenzung, Requirements Abschnitt 7, bewusst ausgeklammert)

## Backend-Endpunkte — Status

Vollständige Beschreibung/Zweck je Endpunkt in `readme.md` (Abschnitt „API Endpoints"). Alle Pfad-IDs (`character_id`, `user_id`, `item_id`, `effect_id`, `spell_id`, `slot_id`, …) sind als UUID zu behandeln, analog zu den `uuid id`-Feldern im ER-Diagramm in `readme.md`. Der Sammelstatus hier dient als Fortschritts-Checkliste; `readme.md` bleibt die inhaltliche Doku.

Legende: ✅ implementiert (Mock/Fixture, GET-only) · ❌ nicht implementiert

**Referenzdaten** — alle ✅ implementiert (`GET /api/races` seit Slice 2, `GET /api/skills`/`GET /api/feats`/`GET /api/traits`/`GET /api/spells`/`GET /api/spells-by-class`/`GET /api/items` seit Slice 3 echte Datenbank, Rest Mock/Fixture in `backend/app/main.py`):
- [x] `GET /api/races`, `GET /api/skills`, `GET /api/feats`, `GET /api/traits`, `GET /api/spells`, `GET /api/spells-by-class`, `GET /api/items` (Datenbank), `GET /api/classes` (Fixture, überlagert mit Datenbank-Feldern — siehe `readme.md`), `GET /api/abilities`, `GET /api/point-buy-costs`, `GET /api/effects`, `GET /api/class-level-options` (Fixture)
- [x] `GET /api/characters/{character_id}`, `GET /api/characters/{character_id}/progression`

**Nutzerverwaltung** — alle ✅ implementiert (echte `users`-Tabelle, `backend/app/routers/users.py`):
- [x] `POST /api/users`
- [x] `GET /api/users`
- [x] `PATCH /api/users/{user_id}` (Backend + Tests vorhanden, noch kein Frontend-UI dafür)

**Charakterverwaltung** — Grundgerüst (roadmap Slice 2, minimale „thin"-Zeile) ✅, Rest ❌:
- [ ] `GET /api/users/{user_id}/characters`
- [x] `POST /api/characters`
- [x] `GET /api/characters/{character_id}` (zusammengeführt mit dem bestehenden Mock-Fixture-Endpunkt)
- [x] `PATCH /api/characters/{character_id}`
- [x] `DELETE /api/characters/{character_id}`
- [ ] `PUT /api/characters/{character_id}/draft` (optional, Auto-Save)

**Stufenaufstieg** — alle ❌ nicht implementiert:
- [ ] `POST /api/characters/{character_id}/level-up`
- [ ] `GET /api/characters/{character_id}/history`

**Vitalwerte/Kampf** — ❌ nicht implementiert:
- [ ] `PATCH /api/characters/{character_id}/hp`

**Zustände/Effekte/Zeit** — alle ❌ nicht implementiert:
- [ ] `POST /api/characters/{character_id}/effects/{effect_id}/activate`
- [ ] `DELETE /api/characters/{character_id}/effects/{active_effect_id}`
- [ ] `POST /api/characters/{character_id}/effects/custom`
- [ ] `POST /api/characters/{character_id}/advance-time`
- [ ] `POST /api/characters/{character_id}/rest`

**Zauber** — bekannte Zauber/Zauberbuch (Slice 3) ✅, Vorbereiten/Wirken pro Tag (Slice 6) ❌:
- [ ] `POST /api/characters/{character_id}/spells/{spell_id}/cast`
- [ ] `POST /api/characters/{character_id}/spells/{spell_id}/prepare`
- [ ] `DELETE /api/characters/{character_id}/spells/{spell_id}/prepare`
- [x] `POST /api/characters/{character_id}/spellbook` (nur arkan-vorbereitende Klassen, siehe `roadmap.md`)
- [x] `DELETE /api/characters/{character_id}/spellbook/{spell_id}`
- [x] `POST /api/characters` (`spell_ids`) — bekannte Zauber/Zauberbuch bei Erstellung, real gegen `BaseClassSpellsKnown` validiert
- [ ] Backend-Endpunkte oben sind fertig, aber **im Charakterbogen (`Spellbook.tsx`) noch nicht verdrahtet** — `POST`/`DELETE .../spellbook` werden von der Zauberbuch-Ansicht bislang nicht aufgerufen (Zauber hinzufügen/entfernen im Sheet bleibt reiner Session-State). Das ist inzwischen die Ausnahme, nicht mehr die Regel: `CharacterSheetPage.tsx` lädt für echte (Datenbank-)Charaktere längst den vollständigen berechneten Sheet-Zustand vom Backend (`GET /api/characters/{id}` → `build_character_sheet`, siehe `readme.md`) statt der Mock-Fixtures — Ausrüstung/Inventar (roadmap Slice 4, siehe oben) ist inzwischen ebenfalls echt angebunden. Der Stufenaufstiegs-Assistent (`LevelSpellStep.tsx`) wurde auf die neuen Grad-/Budget-Regeln umgestellt, bleibt aber wie der Rest von Stufenaufstieg rein session-lokal (kein echter Endpoint, siehe roadmap Slice 7).

**Ausrüstung/Inventar** — Startausrüstung bei Erstellung (Slice 3) ✅, laufende Inventarverwaltung (Slice 4) ✅ für Rüstung/Schild, restliche 12 Ausrüstungsplätze weiterhin nur kosmetisch:
- [x] `POST /api/characters` (`gear`) — Startausrüstung aus dem echten `base_items`-Katalog (Name/Kategorie/Preis), rein deskriptiv gespeichert (`CharacterGear`, direkt am Charakter statt pro Stufe wie Talente/Wesenszüge, da Ausrüstung jederzeit im Spiel dazukommt/verschwindet).
- [x] `POST /api/characters/{character_id}/gear`, `PATCH /api/characters/{character_id}/gear/{item_id}`, `DELETE /api/characters/{character_id}/gear/{item_id}`, `PUT /api/characters/{character_id}/slots/{slot_key}` — echt implementiert (`backend/app/routers/characters.py`), siehe `roadmap.md` Slice 4. `slot_key` ist aktuell auf `"ruestung"`/`"schild"` beschränkt — nur diese zwei haben echte mechanische Katalogdaten (`BaseItem.ac_bonus`/`max_dex_bonus`, echte PF1e-SRD-Werte für die 6 Rüstungs-/2 Schild-Einträge in `base_items.json`). Die Rüstungsklasse (`armorClass`) wird in `sheet.py` daraus real berechnet (inkl. Dex-Bonus-Deckelung durch schwere Rüstung), nicht mehr nur ein Platzhalter.
- [ ] Die übrigen 12 „Wondrous Item"-Plätze (Ring, Gürtel, Amulett, …) bleiben bewusst rein kosmetisch/nur im Frontend — dafür existieren noch keine echten Katalogeinträge (die Fixture-Charaktere zeigen dort nur handgetippte Flavor-Strings), und deren mechanische Werte jetzt zu erfinden wäre genau das in diesem Dokument oben beschriebene Rateinhalt-Problem, kein Schema-Lücke.

**Charakterhintergrund** — alle ❌ nicht implementiert:
- [ ] `GET /api/characters/{character_id}/background`
- [ ] `PUT /api/characters/{character_id}/background`

**Regelwerk/Referenz** — ❌ nicht implementiert:
- [ ] `GET /api/compendium/search?q=`

## React-Frontend — Fehlende UI-Elemente / Bugs (Stand aktueller Scaffold)

Ergänzung zu „UI-Mocks — Offene Punkte" oben: dort ging es um die drei statischen HTML-Mocks, die folgenden Punkte sind im aktuellen React-Scaffold (`frontend/src/`) bestätigt. `frontend/src/api/client.ts` hat weiterhin nur `apiGet` — es existiert keinerlei Schreib-Infrastruktur zum Backend. Ein erster Batch (unten mit [x]) wurde als reine Frontend-/Local-State-Lösung umgesetzt: ein neuer `AppStateContext` (`frontend/src/state/AppStateContext.tsx`) hält Nutzer-/Charakterliste, aktuelle Auswahl und Level-up-Overrides session-lokal (kein Backend-Write, geht beim Neuladen weiterhin verloren). Dafür gibt es jetzt einen zweiten Charakter-Fixture (`character_2.json`/`progression_2.json`, ein Kämpfer), damit der Charakter-Picker echt zwischen zwei vom Backend geladenen Charakteren wechselt.

- [x] **Nutzer-Picker im Header ist reiner Platzhalter**: `AppHeader.tsx` zeigt jetzt eine echte Dropdown-Liste (`useAppState().users`) mit Auswahl-Handler.
- [x] **„+ Neuer Nutzer"-Button ohne Funktion**: öffnet ein Inline-Formular, ruft `addUser()` im Context auf.
- [x] **Charakter-Picker im Header ist reiner Platzhalter**: echte Dropdown-Liste über `characterIds`, inkl. Umbenennen/Löschen pro Zeile.
- [x] **Keine Charakterliste/-verwaltung**: als Popover am Charakter-Picker gelöst (Auswählen/Umbenennen/Löschen), keine eigene Seite. Charaktere sind jetzt einem Nutzer zugeordnet (`characterOwners` im `AppStateContext`) — der Picker zeigt nur die Charaktere des aktuell gewählten Nutzers; ein neu angelegter Nutzer startet ohne Charaktere (Empty State „Kein Charakter" im Sheet statt eines geleakten fremden Charakters). Da der Erstellungs-Assistent weiterhin keinen Charakter in den Store schreibt (siehe unten), hat ein neuer Nutzer aktuell keinen Weg, in derselben Sitzung einen eigenen Charakter zu bekommen.
- [x] **Zustände/Zauber im Effekte-Panel nicht aktivierbar**: `AvailableSeal` hat jetzt `onClick` → `handleActivateEffect`.
- [x] **Kein vorzeitiges Entfernen eines aktiven Effekts**: „✕"-Button an jedem aktiven Siegel.
- [x] **Kein Freitext-Zustand/Effekt mit frei wählbarer Dauer**: „+ Eigener Zustand"-Formular im Effekte-Panel (Name + optionale Rundenzahl, leer = „bis Rast").
- [x] **Kurze Rast vs. Tageswechsel weiterhin nicht unterschieden**: eigener „Kurze Rast"-Button (löst nur „bis Rast"-Effekte auf + erneuert Zauberplätze, ohne Rundenzähler zu verändern); „+1 Tag" behandelt einen Tag jetzt als endliche Rundenzahl (24 h) statt alle Effekte pauschal zu löschen, und schließt zusätzlich eine Rast ein.
- [ ] **Tagesbasierte Folgeeffekte (Gift/Krankheit) weiterhin nicht modelliert** — bewusst zurückgestellt, eigene Simulationslogik nötig.
- [x] **Zauberbuch/bekannte Zauber nicht als laufende Inventarliste im Sheet editierbar**: „+ Zauber hinzufügen" / „✕" pro Zauber in `Spellbook.tsx`, analog zur Ausrüstungsliste. Bleibt reiner Session-State — die neuen echten Backend-Endpunkte (`POST`/`DELETE .../spellbook`, roadmap Slice 3) sind noch nicht angebunden, da `Spellbook.tsx`/`CharacterSheetPage.tsx` weiterhin komplett auf den beiden Mock-Charakter-Fixtures laufen, nicht auf einem echten Backend-Charakter.
- [x] **Item-Detail-Modal nicht an Item-ID gebunden (Bug)**: `ItemDetailModal` bekommt jetzt das echte `GearItem` (nicht nur den Namen), seedet seinen State pro Item-ID neu und schreibt Verstärkung/Eigenschaften über `onSave` zurück in `character.gear` (`GearItem` hat dafür neue optionale Felder `enhancement`/`properties`).
- [x] **Ausrüstungs-Slots nicht ans Inventar gekoppelt / AC nicht neu berechnet**: für Rüstung/Schild jetzt echt umgesetzt (roadmap Slice 4) — Anlegen/Ablegen ruft `PUT /api/characters/{id}/slots/{slot_key}` auf, `armorClass` wird serverseitig aus den ausgerüsteten Gegenständen berechnet (`backend/app/sheet.py`, `backend/app/rules/modifiers.py`), nicht im Frontend. Die übrigen 12 Ausrüstungsplätze (Ring, Gürtel, Amulett, …) bleiben weiterhin rein kosmetisch — keine echten Katalogeinträge dafür, siehe „Ausrüstung/Inventar" oben.
- [ ] **Kein UI für Charakterhintergrund**: weiterhin offen (neues Feature, kein Bugfix).
- [ ] **Regelhilfe/Kompendium weiterhin nicht vorhanden**: weiterhin offen (braucht echten Regeltext-Datenbestand, nicht nur UI-Verdrahtung).
- [x] **Mehrere Archetypen pro Klasse weiterhin nur Einzel-Dropdown**: `ClassRow`/`ClassProgressionEntry`/`LevelUpTarget` speichern jetzt `archetypes: string[]`; `ClassStep.tsx` und `ClassLevelStep.tsx` nutzen dafür einen Mehrfachauswahl-Chip-Picker (`OptionGroupPicker`) statt eines Einzel-Dropdowns. **Weiterhin offen**: keine Konfliktprüfung zwischen Archetypen — dafür fehlen noch Metadaten (welche Archetypen sich gegenseitig ausschließen); das ist eine eigene Datenmodell-Entscheidung.
- [x] **Kämpfer-Bonustalent auf geraden Stufen weiterhin nicht abgebildet**: `fighterBonusFeatGrantedThisLevel()` in `levelUpCalculations.ts` + zweiter Auswahl-Slot in `LevelFeatStep.tsx`/`LevelUpSummaryStep.tsx`. Filtert jetzt tatsächlich auf `type === 'combat'` statt die volle Talenteliste anzubieten, seit `BaseFeat` (Roadmap Slice 3) eine echte `type`-Spalte hat.
- [~] **Assistenten enden nur mit Mock-Bestätigungstext statt echtem Speichervorgang**: Der **Stufenaufstiegs**-Assistent schreibt sein Ergebnis jetzt wirklich in den (session-lokalen) `AppStateContext` zurück (inkl. Historieneintrag) statt nur einen Banner zu zeigen. Der **Charaktererstellungs**-Assistent ruft jetzt `POST /api/characters` echt auf (Slice 2, minimale Felder: Name/Nutzer/Rasse/Klasse) statt nur einen Mock-Banner zu zeigen — bewusst weiterhin **nicht** vollständig: einen Draft in einen vollständigen `Character` (mit berechneten Rettungswürfen/Kampfwerten/AC) zu verwandeln hieße, genau die Berechnungen im Frontend nachzubauen, die eigentlich das Backend übernehmen soll (kommt mit Slice 3). Der neu erstellte Charakter erscheint noch nicht im Charakter-Picker im Header (dafür fehlt `GET /api/users/{user_id}/characters`).
- [ ] **Kein Auto-Save/Draft-Save während der Assistenten**: weiterhin offen.
- [x] **Stufenaufstiegs-Historie fehlt im Datenmodell**: `CharacterProgression.history: HistoryEntry[]` ergänzt; der Level-up-Assistent hängt bei jedem Abschluss einen Eintrag an und zeigt die bisherige Historie in der Zusammenfassung an. Bleibt reines Session-State (kein Backend-Write) und wirkt sich nicht auf die separate `Character`-Sheet-Ansicht aus (siehe unten).
- [ ] **Backend-Schreibzugriff weiterhin komplett offen**: alles oben bleibt lokaler React-State; `apiGet`-only-Client und die „Backend-Endpunkte — Status"-Liste oben sind unverändert. Zusätzliche bekannte Einschränkung: Charakterbogen (`/api/characters/{id}`) und Progression (`/api/characters/{id}/progression`) sind laut Backend-Kommentar weiterhin „zwei Mock-Ansichten desselben Charakters" — ein im Level-up-Assistenten übernommener Stufenaufstieg aktualisiert die Progression, nicht die im Charakterbogen angezeigten Werte.
