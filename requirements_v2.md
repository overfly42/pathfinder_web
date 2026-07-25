# Anforderungen für eine Pathfinder-Webanwendung

## 1. Ziel der Anwendung
- Digitale Verwaltung von Pathfinder-Charakteren für Spieler.
- Unterstützung bei der Charakterentwicklung über mehrere Stufen hinweg.

## 2. Kernfunktionen
- Charaktere anlegen, bearbeiten und verwalten.
- Stufenaufstieg mit Historie und nachvollziehbarer Entwicklung.
- Spielmodus zur Verwaltung von Zuständen, Effekten und Zaubern.
- Mehrere Spieler gleichzeitig und unabhängig voneinander auf die Anwendung zugreifen lassen, ohne direkte Interaktion über die Anwendung.
- Zustände, Zauber und ähnliche Effekte über eine Session hinweg speichern und zeit- oder ereignisbasiert wieder aufheben können, zum Beispiel nach Schlafdauer oder anderem Ablauf.
- Regelhilfe mit entsprechenden Regeltexten zu Fähigkeiten bereitstellen.

### 2.1 Charaktererstellung und Stufenaufstieg
- Ein Charakter kann eine oder mehrere Klassenstufen haben, wobei die Summe der Klassenstufen der Charakterstufe entspricht.
- Ein Charakter kann mehrere Archetypen einer Klasse haben, sofern diese sich nicht widersprechen.
- Archetypen werden in der Klassen-Tabelle verlinkt.
- Ein Charakter hat eine Rasse.
- Ein Charakter hat Talente.
- Ein Charakter hat Ausrüstung.
- Ausrüstung kann festen Ausrüstungsplätzen zugeordnet werden (z. B. Kopf, Stirnband, Gürtel, Ring links/rechts). Auswählbar sind dabei nur Gegenstände, die sich im Inventar des Charakters befinden.
- Ein Charakter hat Wesenszüge.

### 2.2 Zauberwirken
- Ein Charakter hat je nach Klasse eine von drei Zauberwirker-Arten: keine Zauberfähigkeit, vorbereitendes Zauberwirken oder spontanes Zauberwirken (jeweils arkan oder göttlich).
- Für zauberkundige Charaktere werden pro Zaubergrad geführt: die Anzahl bekannter Zauber, die Anzahl täglich verfügbarer Zauberplätze und die aktuell vorbereiteten bzw. nutzbaren Zauber.
- Vorbereitendes Zauberwirken (z. B. Waldläufer, Kleriker, Druide, Magier): Täglich wird eine Auswahl an Zaubern vorbereitet, die anschließend beim Wirken verbraucht wird.
  - Göttliche vorbereitende Zauberwirker wählen ihre Vorbereitung frei aus der vollständigen Klassen-Zauberliste, ohne eine feste bekannte Liste.
  - Arkane vorbereitende Zauberwirker (z. B. Magier) führen ein Zauberbuch mit einer begrenzten, individuell erlernten Auswahl an Zaubern, aus der jeweils vorbereitet wird. Das Zauberbuch wird wie das Inventar verwaltet (Zauber hinzufügen/entfernen).
- Spontanes Zauberwirken (z. B. Hexenmeister, Barde, Orakel): Es existiert eine kurze, feste Liste bekannter Zauber, die ohne tägliche Vorbereitung direkt gegen die verfügbaren Zauberplätze gewirkt werden. Die bekannte Liste wird ebenfalls wie eine Inventarliste verwaltet und ändert sich in der Regel nur bei Stufenaufstieg.
- Für vorbereitete bzw. bekannte Zauber muss zwischen drei Zuständen unterschieden werden: nicht vorbereitet, vorbereitet (bzw. bekannt und verfügbar) sowie gewirkt/verbraucht für den aktuellen Tag.
- Verbrauchte bzw. vorbereitete Zauber werden zeit- oder ereignisbasiert zurückgesetzt (z. B. nach einer Rast), analog zu anderen Zuständen und Effekten (siehe Abschnitt 2).

## 3. Nutzergruppen
- Spielerinnen und Spieler.
- Spielleiterinnen und Spielleiter als spätere Erweiterung.

## 4. Bedienungsanforderungen
- Klare und einfache Bedienung.
- Schneller Zugriff auf wichtige Charakterinformationen.
- Gute Lesbarkeit von Regeln und Fähigkeiten.

## 5. Technische Rahmenbedingungen
- Webbasierte Anwendung.
- Mehrbenutzerfähigkeit mit gemeinsamer Datenbasis.
- Persistente Speicherung von Charakterdaten.
- Sicherer Zugriff auf die eigenen Daten.
- Die Anwendung soll multilingual angelegt werden.
- Standardsprache soll Deutsch sein.
- Alle Inhalte sollen zusätzlich auch auf Englisch verfügbar sein.
- Die Daten sollen in einer PostgreSQL-Datenbank gespeichert werden.
- Die Programmiersprache soll Python sein.
- Programmcode und Kommentare im Programm sollen auf Englisch geschrieben sein.

## 6. Funktionale Anforderungen
- Die Anwendung muss Charaktere erstellen, bearbeiten und löschen können.
- Die Anwendung muss die Charakterstufe aus den vorhandenen Klassenstufen ableiten können.
- Die Anwendung muss die Zuordnung von Klassen, Archetypen, Rassen, Talenten, Ausrüstung und Wesenszügen pro Charakter unterstützen.
- Die Anwendung muss eine Historie für Stufenaufstiege und Änderungen an Charakterdaten führen.
- Die Anwendung muss Zustände, Effekte und Zauber an einem Charakter speichern und deren Ablauf verwalten können.
- Die Anwendung muss Zustände, Effekte und Zauber zeitbasiert oder ereignisbasiert automatisch aufheben können.
- Die Anwendung muss je nach Zauberwirker-Art (keine, vorbereitend, spontan; arkan oder göttlich) bekannte Zauber, tägliche Zauberplätze und vorbereitete Zauber pro Zaubergrad verwalten können.
- Die Anwendung muss für Zauber die drei Zustände nicht vorbereitet, vorbereitet/bekannt und gewirkt/verbraucht unterscheiden und beim Wirken sowie bei Rücksetzung (z. B. nach Rast) aktualisieren können.
- Die Anwendung muss für arkane vorbereitende Zauberwirker ein Zauberbuch mit einer editierbaren, individuell erlernten Zauberliste unterstützen; göttliche vorbereitende Zauberwirker müssen stattdessen aus der vollständigen Klassen-Zauberliste vorbereiten können.
- Die Anwendung muss mehreren Nutzern gleichzeitig und unabhängig voneinander Zugriff auf ihre eigenen Charaktere ermöglichen.
- Die Anwendung muss Regeltexte und Fähigkeitsbeschreibungen für die Regelhilfe bereitstellen.
- Die Anwendung muss Nutzerinformationen und Charakterdaten sicher speichern und abrufen können.
- Daten und Datenbeziehungen, zum Beispiel die Zuordnung von Fähigkeiten zu Klassen, müssen in der Datenbank gespeichert werden.
- Die genaue Funktionalität von Fähigkeiten und deren Wirkungslogik muss im Programm umgesetzt werden.

## 7. MVP-Abgrenzung
- Die erste Version soll als MVP klar abgegrenzt werden.
- Im MVP sollen Charakterdaten eingegeben und dargestellt werden können.
- Im MVP gibt es noch keine vollständige Datenbasis; unvollständig modellierte Fähigkeiten müssen später erweitert und nachgeladen werden können.
- Im MVP richtet sich die Anwendung nur an Spieler.
- Da die Anwendung nur für lokale Nutzung gedacht ist und keine personenbezogenen Daten speichert, kann auf eine Authentifizierung verzichtet werden.
- Das Design sollte jedoch so angelegt werden, dass eine spätere Authentifizierung problemlos ergänzt werden kann.

## 8. Checkliste vor Projektstart

| Frage | Antwort | Status |
| --- | --- | --- |
| Wer sind die Nutzer im MVP? | Nur Spieler. Im MVP können Charaktere erstellt und Stufen hinzugefügt werden. Weitere Rollen sind nicht vorgesehen. | Erledigt |
| Sind wichtige Datenmodelle und deren Beziehungen definiert? | Teilweise. Das README enthält erste Entitäten wie Charakter, Charakterstufen, Klassen, Skills, Attribute, Rassen und Feats. Für den MVP fehlen aber noch Archetypen, Ausrüstung, Wesenszüge, aktive Effekte und Zustände, Session-Logik und Verlaufshistorie. | Offen |
| Ist die Anwendungslogik für Fähigkeiten, Effekte und Zustände festgelegt? | Noch nicht. | Offen |
| Ist die Entscheidung zu Authentifizierung, Benutzerverwaltung und Zugriffskontrolle getroffen? | Noch nicht. | Offen |
| Ist die technische Architektur für Backend, Frontend und Datenbank festgelegt? | Noch nicht. | Offen |
| Ist der Lokalisierungs- und Übersetzungsansatz definiert? | Noch nicht. | Offen |
| Sind Qualitätskriterien wie Sicherheit, Zuverlässigkeit und Performance festgelegt? | Noch nicht. | Offen |

## 9. Ausblick
- Die Anforderungen werden im nächsten Schritt in detailierte Qualitätsanforderungen unterteilt.
