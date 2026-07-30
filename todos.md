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
      verbleibenden `backend/app/fixtures/*.json`.

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

- [ ] **Krieger-Bonustalent**: Der Krieger bekommt zusätzlich zum normalen Talent auf ungeraden Stufen ein Bonus-Kampftalent auf jeder geraden Stufe. Das würde die Zähllogik im Talente-Schritt selbst ändern (nicht nur eine neue Auswahlgruppe) und ist im Stufenaufstiegs-Mock bewusst noch nicht umgesetzt.
- [ ] **Terminologie „Zauberbuch"**: Im Charakterbogen-Mock ist der Ausrüstungs-Tab für die Waldläufer-Zaubervorbereitung mit „Zauberbuch" beschriftet, obwohl der Waldläufer ein göttlicher, vorbereitender Zauberwirker ohne echtes Zauberbuch ist (nur arkane Vorbereiter wie der Magier führen laut Requirement 2.2 ein Zauberbuch).

### Später / Ausblick (laut Requirements bewusst nicht MVP)

- [ ] Klassen-/Archetypen-Referenztabelle („Archetypen werden in der Klassen-Tabelle verlinkt", Requirement 2.1)
- [ ] Spielleiter-Ansicht (Requirements Abschnitt 3: „spätere Erweiterung")
- [ ] Echte Mehrsprachigkeit DE/EN — aktuell nur ein Sprach-Dropdown ohne übersetzte Inhalte
- [ ] Auth-/Login-Flow (laut MVP-Abgrenzung, Requirements Abschnitt 7, bewusst ausgeklammert)

## Backend-Endpunkte — Status

Vollständige Beschreibung/Zweck je Endpunkt in `readme.md` (Abschnitt „API Endpoints"). Alle Pfad-IDs (`character_id`, `user_id`, `item_id`, `effect_id`, `spell_id`, `slot_id`, …) sind als UUID zu behandeln, analog zu den `uuid id`-Feldern im ER-Diagramm in `readme.md`. Der Sammelstatus hier dient als Fortschritts-Checkliste; `readme.md` bleibt die inhaltliche Doku.

Legende: ✅ implementiert (Mock/Fixture, GET-only) · ❌ nicht implementiert

**Referenzdaten** — alle ✅ implementiert (`GET /api/races` seit Slice 2, `GET /api/skills`/`GET /api/feats` seit Slice 3 echte Datenbank, Rest Mock/Fixture in `backend/app/main.py`):
- [x] `GET /api/races`, `GET /api/skills`, `GET /api/feats` (Datenbank), `GET /api/classes`, `GET /api/traits`, `GET /api/abilities`, `GET /api/spells-by-class`, `GET /api/point-buy-costs`, `GET /api/items`, `GET /api/effects`, `GET /api/class-level-options` (Fixture)
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

**Zauber** — alle ❌ nicht implementiert:
- [ ] `POST /api/characters/{character_id}/spells/{spell_id}/cast`
- [ ] `POST /api/characters/{character_id}/spells/{spell_id}/prepare`
- [ ] `DELETE /api/characters/{character_id}/spells/{spell_id}/prepare`
- [ ] `POST /api/characters/{character_id}/spellbook`
- [ ] `DELETE /api/characters/{character_id}/spellbook/{spell_id}`

**Ausrüstung/Inventar** — alle ❌ nicht implementiert:
- [ ] `POST /api/characters/{character_id}/gear`
- [ ] `PATCH /api/characters/{character_id}/gear/{item_id}`
- [ ] `DELETE /api/characters/{character_id}/gear/{item_id}`
- [ ] `PUT /api/characters/{character_id}/slots/{slot_id}`

**Charakterhintergrund** — alle ❌ nicht implementiert:
- [ ] `GET /api/characters/{character_id}/background`
- [ ] `PUT /api/characters/{character_id}/background`

**Regelwerk/Referenz** — ❌ nicht implementiert:
- [ ] `GET /api/compendium/search?q=`

## React-Frontend — Fehlende UI-Elemente / Bugs (Stand aktueller Scaffold)

Ergänzung zu „UI-Mocks — Offene Punkte" oben: dort ging es um die drei statischen HTML-Mocks, die folgenden Punkte sind im aktuellen React-Scaffold (`frontend/src/`) bestätigt. `frontend/src/api/client.ts` hat weiterhin nur `apiGet` — es existiert keinerlei Schreib-Infrastruktur zum Backend. Ein erster Batch (unten mit [x]) wurde als reine Frontend-/Local-State-Lösung umgesetzt: ein neuer `AppStateContext` (`frontend/src/state/AppStateContext.tsx`) hält Nutzer-/Charakterliste, aktuelle Auswahl und Level-up-Overrides session-lokal (kein Backend-Write, geht beim Neuladen weiterhin verloren). Dafür gibt es jetzt einen zweiten Charakter-Fixture (`character_2.json`/`progression_2.json`, ein Krieger), damit der Charakter-Picker echt zwischen zwei vom Backend geladenen Charakteren wechselt.

- [x] **Nutzer-Picker im Header ist reiner Platzhalter**: `AppHeader.tsx` zeigt jetzt eine echte Dropdown-Liste (`useAppState().users`) mit Auswahl-Handler.
- [x] **„+ Neuer Nutzer"-Button ohne Funktion**: öffnet ein Inline-Formular, ruft `addUser()` im Context auf.
- [x] **Charakter-Picker im Header ist reiner Platzhalter**: echte Dropdown-Liste über `characterIds`, inkl. Umbenennen/Löschen pro Zeile.
- [x] **Keine Charakterliste/-verwaltung**: als Popover am Charakter-Picker gelöst (Auswählen/Umbenennen/Löschen), keine eigene Seite. Charaktere sind jetzt einem Nutzer zugeordnet (`characterOwners` im `AppStateContext`) — der Picker zeigt nur die Charaktere des aktuell gewählten Nutzers; ein neu angelegter Nutzer startet ohne Charaktere (Empty State „Kein Charakter" im Sheet statt eines geleakten fremden Charakters). Da der Erstellungs-Assistent weiterhin keinen Charakter in den Store schreibt (siehe unten), hat ein neuer Nutzer aktuell keinen Weg, in derselben Sitzung einen eigenen Charakter zu bekommen.
- [x] **Zustände/Zauber im Effekte-Panel nicht aktivierbar**: `AvailableSeal` hat jetzt `onClick` → `handleActivateEffect`.
- [x] **Kein vorzeitiges Entfernen eines aktiven Effekts**: „✕"-Button an jedem aktiven Siegel.
- [x] **Kein Freitext-Zustand/Effekt mit frei wählbarer Dauer**: „+ Eigener Zustand"-Formular im Effekte-Panel (Name + optionale Rundenzahl, leer = „bis Rast").
- [x] **Kurze Rast vs. Tageswechsel weiterhin nicht unterschieden**: eigener „Kurze Rast"-Button (löst nur „bis Rast"-Effekte auf + erneuert Zauberplätze, ohne Rundenzähler zu verändern); „+1 Tag" behandelt einen Tag jetzt als endliche Rundenzahl (24 h) statt alle Effekte pauschal zu löschen, und schließt zusätzlich eine Rast ein.
- [ ] **Tagesbasierte Folgeeffekte (Gift/Krankheit) weiterhin nicht modelliert** — bewusst zurückgestellt, eigene Simulationslogik nötig.
- [x] **Zauberbuch/bekannte Zauber nicht als laufende Inventarliste im Sheet editierbar**: „+ Zauber hinzufügen" / „✕" pro Zauber in `Spellbook.tsx`, analog zur Ausrüstungsliste.
- [x] **Item-Detail-Modal nicht an Item-ID gebunden (Bug)**: `ItemDetailModal` bekommt jetzt das echte `GearItem` (nicht nur den Namen), seedet seinen State pro Item-ID neu und schreibt Verstärkung/Eigenschaften über `onSave` zurück in `character.gear` (`GearItem` hat dafür neue optionale Felder `enhancement`/`properties`).
- [ ] **Ausrüstungs-Slots nicht ans Inventar gekoppelt / AC nicht neu berechnet**: bewusst zurückgestellt — AC soll laut Entscheidung künftig vom Backend berechnet werden, nicht im Frontend; erst nach diesem Architekturschritt sinnvoll umsetzbar.
- [ ] **Kein UI für Charakterhintergrund**: weiterhin offen (neues Feature, kein Bugfix).
- [ ] **Regelhilfe/Kompendium weiterhin nicht vorhanden**: weiterhin offen (braucht echten Regeltext-Datenbestand, nicht nur UI-Verdrahtung).
- [x] **Mehrere Archetypen pro Klasse weiterhin nur Einzel-Dropdown**: `ClassRow`/`ClassProgressionEntry`/`LevelUpTarget` speichern jetzt `archetypes: string[]`; `ClassStep.tsx` und `ClassLevelStep.tsx` nutzen dafür einen Mehrfachauswahl-Chip-Picker (`OptionGroupPicker`) statt eines Einzel-Dropdowns. **Weiterhin offen**: keine Konfliktprüfung zwischen Archetypen — dafür fehlen noch Metadaten (welche Archetypen sich gegenseitig ausschließen); das ist eine eigene Datenmodell-Entscheidung.
- [x] **Krieger-Bonustalent auf geraden Stufen weiterhin nicht abgebildet**: `fighterBonusFeatGrantedThisLevel()` in `levelUpCalculations.ts` + zweiter Auswahl-Slot in `LevelFeatStep.tsx`/`LevelUpSummaryStep.tsx`. Filtert jetzt tatsächlich auf `type === 'combat'` statt die volle Talenteliste anzubieten, seit `BaseFeat` (Roadmap Slice 3) eine echte `type`-Spalte hat.
- [~] **Assistenten enden nur mit Mock-Bestätigungstext statt echtem Speichervorgang**: Der **Stufenaufstiegs**-Assistent schreibt sein Ergebnis jetzt wirklich in den (session-lokalen) `AppStateContext` zurück (inkl. Historieneintrag) statt nur einen Banner zu zeigen. Der **Charaktererstellungs**-Assistent ruft jetzt `POST /api/characters` echt auf (Slice 2, minimale Felder: Name/Nutzer/Rasse/Klasse) statt nur einen Mock-Banner zu zeigen — bewusst weiterhin **nicht** vollständig: einen Draft in einen vollständigen `Character` (mit berechneten Rettungswürfen/Kampfwerten/AC) zu verwandeln hieße, genau die Berechnungen im Frontend nachzubauen, die eigentlich das Backend übernehmen soll (kommt mit Slice 3). Der neu erstellte Charakter erscheint noch nicht im Charakter-Picker im Header (dafür fehlt `GET /api/users/{user_id}/characters`).
- [ ] **Kein Auto-Save/Draft-Save während der Assistenten**: weiterhin offen.
- [x] **Stufenaufstiegs-Historie fehlt im Datenmodell**: `CharacterProgression.history: HistoryEntry[]` ergänzt; der Level-up-Assistent hängt bei jedem Abschluss einen Eintrag an und zeigt die bisherige Historie in der Zusammenfassung an. Bleibt reines Session-State (kein Backend-Write) und wirkt sich nicht auf die separate `Character`-Sheet-Ansicht aus (siehe unten).
- [ ] **Backend-Schreibzugriff weiterhin komplett offen**: alles oben bleibt lokaler React-State; `apiGet`-only-Client und die „Backend-Endpunkte — Status"-Liste oben sind unverändert. Zusätzliche bekannte Einschränkung: Charakterbogen (`/api/characters/{id}`) und Progression (`/api/characters/{id}/progression`) sind laut Backend-Kommentar weiterhin „zwei Mock-Ansichten desselben Charakters" — ein im Level-up-Assistenten übernommener Stufenaufstieg aktualisiert die Progression, nicht die im Charakterbogen angezeigten Werte.
