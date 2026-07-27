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

**Referenzdaten** — alle ✅ implementiert (Mock/Fixture, `backend/app/main.py`):
- [x] `GET /api/races`, `GET /api/classes`, `GET /api/feats`, `GET /api/traits`, `GET /api/skills`, `GET /api/abilities`, `GET /api/spells-by-class`, `GET /api/point-buy-costs`, `GET /api/items`, `GET /api/effects`, `GET /api/class-level-options`
- [x] `GET /api/characters/{character_id}`, `GET /api/characters/{character_id}/progression`

**Nutzerverwaltung** — alle ❌ nicht implementiert:
- [ ] `POST /api/users`
- [ ] `GET /api/users`
- [ ] `PATCH /api/users/{user_id}`

**Charakterverwaltung** — alle ❌ nicht implementiert:
- [ ] `GET /api/users/{user_id}/characters`
- [ ] `POST /api/characters`
- [ ] `PATCH /api/characters/{character_id}`
- [ ] `DELETE /api/characters/{character_id}`
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

Ergänzung zu „UI-Mocks — Offene Punkte" oben: dort ging es um die drei statischen HTML-Mocks, die folgenden Punkte sind im aktuellen React-Scaffold (`frontend/src/`) bestätigt. `frontend/src/api/client.ts` hat aktuell nur `apiGet` — es existiert keinerlei Schreib-Infrastruktur, jede der folgenden Interaktionen ändert bislang nur lokalen React-State und geht beim Neuladen verloren.

- [ ] **Nutzer-Picker im Header ist reiner Platzhalter**: `AppHeader.tsx` zeigt nur ein statisches Label „Anna", keine Optionsliste, kein Handler.
- [ ] **„+ Neuer Nutzer"-Button ohne Funktion**: `AppHeader.tsx`, `onClick` fehlt.
- [ ] **Charakter-Picker im Header ist reiner Platzhalter**: `AppHeader.tsx`, ebenfalls ohne Optionsliste/Handler; bestätigt auch im React-Code, nicht nur im alten HTML-Mock.
- [ ] **Keine Charakterliste/-verwaltung**: keine Komponente/Seite zum Auswählen, Umbenennen oder Löschen von Charakteren existiert; Sheet und Level-up-Assistent verwenden aktuell hart codiert Charakter-ID „1".
- [ ] **Zustände/Zauber im Effekte-Panel nicht aktivierbar**: `EffectsPanel.tsx` — die „Verfügbare Zustände & Zauber"-Siegel haben keinen `onClick`-Handler, obwohl der CSS-Hover-Style dafür vorbereitet wirkt.
- [ ] **Kein vorzeitiges Entfernen eines aktiven Effekts**: nur automatischer Ablauf über Zeitfortschritt möglich, kein manueller „Entfernen"/Dispel-Button.
- [ ] **Kein Freitext-Zustand/Effekt mit frei wählbarer Dauer**: weiterhin kein UI dafür (siehe auch Punkt oben unter „UI-Mocks").
- [ ] **Kurze Rast vs. Tageswechsel weiterhin nicht unterschieden**: `CharacterSheetPage.tsx: handleAdvanceTime` behandelt „+1 Tag" als kompletten Reset aller aktiven Effekte, kein eigener Kurzrast-Pfad.
- [ ] **Tagesbasierte Folgeeffekte (Gift/Krankheit) weiterhin nicht modelliert**.
- [ ] **Zauberbuch/bekannte Zauber nicht als laufende Inventarliste im Sheet editierbar**: Hinzufügen/Entfernen ist weiterhin nur ein einmaliger Picker bei Erstellung/Stufenaufstieg, nicht im laufenden Charakterbogen (Requirement 2.2).
- [ ] **Item-Detail-Modal nicht an Item-ID gebunden (Bug)**: `ItemDetailModal.tsx` hält Verstärkungsbonus und Eigenschaften in lokalem State, der bei jedem Öffnen zurückgesetzt wird und nicht dem tatsächlichen Gegenstand zugeordnet ist — mehr als nur „nicht persistiert".
- [ ] **Ausrüstungs-Slots nicht ans Inventar gekoppelt**: Auswahlmöglichkeiten je Slot sind statische Fixture-Daten statt aus `character.gear` abgeleitet; AC wird nicht automatisch aus ausgerüsteten Gegenständen + GES-Modifikator neu berechnet (Requirement 2.3).
- [ ] **Kein UI für Charakterhintergrund**: Backstory, Ziele/Motivationen, NPC-Beziehungen (Requirement 2.4) — weder im Sheet noch in den Assistenten vorhanden, keine Komponenten existieren.
- [ ] **Regelhilfe/Kompendium weiterhin nicht vorhanden**: `GlobalSearch.tsx` durchsucht nur Daten des aktuell geladenen Charakters, keine durchsuchbare Regel-Datenbank.
- [ ] **Mehrere Archetypen pro Klasse weiterhin nur Einzel-Dropdown**: `ClassStep.tsx`/`ClassChoiceStep.tsx` ohne Mehrfachauswahl/Konfliktprüfung — bestätigt auch im React-Code.
- [ ] **Krieger-Bonustalent auf geraden Stufen weiterhin nicht abgebildet** (bestätigt auch im React-Code, `LevelFeatStep.tsx`).
- [ ] **Assistenten enden nur mit Mock-Bestätigungstext statt echtem Speichervorgang**: `SummaryStep.tsx` bzw. `LevelUpSummaryStep.tsx` zeigen nur „... wurde (im Mock) erstellt/übernommen" an, kein API-Call.
- [ ] **Kein Auto-Save/Draft-Save während der Assistenten** (weder Erstellung noch Stufenaufstieg).
- [ ] **Stufenaufstiegs-Historie fehlt im Datenmodell**: `CharacterProgression`-Typ (`types/characterProgression.ts`) hat kein Verlaufsfeld, obwohl Requirement 2 eine nachvollziehbare Historie verlangt.
