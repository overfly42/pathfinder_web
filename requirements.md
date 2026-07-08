# Pathfinder 1st Edition - Webanwendung für Charakterverwaltung

## Projektübersicht
Eine Webanwendung zur Verwaltung von Pathfinder 1st Edition Charakteren mit Fokus auf Charakterpflege, Levelaufstieg, Spielverlauf-Dokumentation und In-Game-Unterstützung durch einen digitalen Charakterbogen.

---

## Funktionale Anforderungen

### 1. Charakterverwaltung

#### 1.1 Charaktererstellung
- **FR-1.1.1**: Spieler können neue Charaktere anlegen
- **FR-1.1.2**: Ein Benutzer kann mehrere Charaktere verwalten
  - Charakterliste mit Übersicht aller Charaktere
  - Schneller Wechsel zwischen Charakteren
  - Duplikation von Charakteren (optional)
- **FR-1.1.3**: Folgende Basisdaten erfassen:
  - Name, Spieler, Kampagne
  - Rasse (aus verwaltbarer Datenbank)
  - Erste Klasse (aus verwaltbarer Datenbank)
  - Gesinnung (LG, LN, LE, NG, N, NE, CG, CN, CE)
  - Weltanschauung / Hintergrund (optional)
- **FR-1.1.4**: Charakterbild
  - Upload eines Charakterbildes (PNG, JPG, WebP)
  - Anzeige in Charakterübersicht und Live-Sheet
  - Bildverwaltung (Änderung, Löschung)
- **FR-1.1.5**: Multiclassing Support
  - Ein Charakter kann mehrere Klassen haben
  - Gesamtstufe = Summe aller Klassen-Level
  - Verwaltung von Stufen pro Klasse
  - Beispiel: Charakter ist Level 5 Barbar + Level 3 Magier = Gesamtstufe 8

#### 1.2 Charakterblatt - Basis-Attribute
- **FR-1.2.1**: Speichern und anzeigen der 6 Fähigkeiten (Ability Scores):
  - Stärke (STR)
  - Geschicklichkeit (DEX)
  - Konstitution (KON)
  - Intelligenz (INT)
  - Weisheit (WIS)
  - Charisma (CHA)
- **FR-1.2.2**: Automatische Berechnung von Modifiern basierend auf Ability Scores
- **FR-1.2.3**: Berücksichtigung von Rassen-Boni auf Attributes

#### 1.3 Charakterblatt - Kampfwerte
- **FR-1.3.1**: Automatische Berechnung von:
  - Trefferpunkte (HP) = Summe aller Hit Dice aus allen Klassen + CON Modifier × Gesamtstufe
  - Rüstungsklasse (AC) basierend auf Ausrüstung und Dexterity Modifier
  - Initiative (Dex Modifier + ggf. Feats)
  - Angriffswürfe (Base Attack Bonus + STR/DEX Modifier)
  - Schadensbonus (STR/DEX Modifier + Waffe)
- **FR-1.3.2**: Speichern und Berechnung von:
  - Base Attack Bonus (BAB) = kumulativ aus allen Klassen-Level
  - Rettungswürfe (Fortitude, Reflex, Will) = kumulativ aus allen Klassen
  - Beispiel: Barbar d12 + Magier d6 Hit Dice

#### 1.4 Charakterblatt - Fertigkeiten
- **FR-1.4.1**: Verwaltung aller Pathfinder Fertigkeiten (Skill Ranks)
  - Zuordnung von Skill Points pro Level je Klasse
  - Automatische Berechnung von Skill Modifiern
  - Berücksichtigung von Attribut-Modifiern und Trainings-Boni
  - Klassenfähigkeiten (Class Skills) werden kumulativ aus allen Klassen berücksichtigt
- **FR-1.4.2**: Darstellung von Klassenfähigkeiten (Class Features)
  - Anzeige aller Class Features aus ALLEN Klassen
  - Sortiert nach Klasse und Level
  - Automatische Freischaltung basierend auf Klassen-Level
- **FR-1.4.3**: Speichern und Berechnung von Spellcasting-Fertigkeiten
  - Zauber pro Klasse und Klassen-Level
  - Kumulatives Spellcasting (z.B. Magier-Zauber + Priester-Zauber)

#### 1.5 Feats und Spezialfähigkeiten
- **FR-1.5.1**: Verwaltung von Feats (aus verwaltbarer Datenbank)
  - Speicherung erlernter Feats pro Gesamtstufe (nicht pro Klasse)
  - Feats verfügbar bei Gesamtstufe 3, 6, 9, 12, etc.
  - Überprüfung von Feat-Voraussetzungen (mit Berücksichtigung aller Klassen)
  - Automatische Berechnung von Feat-Effekten
- **FR-1.5.2**: Verwaltung von Klassenfähigkeiten (Class Abilities)
  - Automatische Freischaltung basierend auf Klasse und Klassen-Level
  - Speicherung von Fähigkeitsbeschreibungen und Effekten
  - Separate Verwaltung für jede Klasse
- **FR-1.5.3**: Verwaltung von Zauber (Spells) je nach Klasse (aus verwaltbarer Datenbank)
  - Verfügbare Zauber basierend auf Klasse und Klassen-Level
  - Zauber-Beschreibungen und Effekte
  - Kumulativ für Multiclassing (z.B. als Magier Level 3 + Priester Level 2)

#### 1.6 Ausrüstung und Gegenstände
- **FR-1.6.1**: Inventar verwalten
  - Waffen (Waffentyp, Boni, Schaden)
  - Rüstung (Rüstungstyp, AC-Boni, Malus)
  - Schilde, Accessoires, Verbrauchsgegenstände
- **FR-1.6.2**: Automatische Berechnung von AC basierend auf Ausrüstung
- **FR-1.6.3**: Gewicht und Tragfähigkeit (optional für Phase 1)

---

### 2. Regelwerk- und Datenbank-Verwaltung

#### 2.1 Verwaltbare Regelwerk-Datenbank
- **FR-2.1.1**: Admin-Interface zur Verwaltung von Pathfinder-Regeln
  - Klassen hinzufügen/bearbeiten/löschen
  - Rassen hinzufügen/bearbeiten/löschen
  - Feats hinzufügen/bearbeiten/löschen
  - Zauber hinzufügen/bearbeiten/löschen
  - Attribute und Effekte pro Regelwerk-Element

#### 2.2 Klassen-Management
- **FR-2.2.1**: Speichern von Klassen-Definitionen:
  - Klassenname, Hit Die (d6, d8, d10, d12)
  - Base Attack Bonus Progression
  - Rettungswurf Progression (Fortitude, Reflex, Will)
  - Fertigkeitspunkte pro Level (+ INT Modifier)
  - Klassenfähigkeiten mit Level-Zuordnung
  - Zauberklassen (falls zutreffend) und Zauber pro Level
- **FR-2.2.2**: Klassische Klassen als Initial-Data-Set:
  - Barbar
  - Magier
  - (weitere Klassen können später hinzugefügt werden)

#### 2.3 Rassen-Management
- **FR-2.3.1**: Speichern von Rassen-Definitionen:
  - Rassenname
  - Attribute-Modifikatoren (z.B. +2 STR, -2 CHA)
  - Größe und Bewegungsgeschwindigkeit
  - Sprachen und Fertigkeitsboni
  - Rassenspezifische Fähigkeiten
- **FR-2.3.2**: Basis-Rassen als Initial-Data-Set (können erweitert werden)

#### 2.4 Feats-Management
- **FR-2.4.1**: Speichern von Feat-Definitionen:
  - Feat-Name, Beschreibung
  - Voraussetzungen (Attribute, Feats, Level, Klasse, etc.)
  - Mechanische Effekte und Modifier
  - Typ (Combat, Metamagic, etc.)
- **FR-2.4.2**: Automatische Validierung von Feat-Voraussetzungen bei Auswahl

#### 2.5 Zauber-Management
- **FR-2.5.1**: Speichern von Zauber-Definitionen:
  - Zauber-Name, Level, Klassen
  - Beschreibung, Bestandteile, Wirkungsdauer
  - Effekte auf Charakterwerte
- **FR-2.5.2**: Automatische Zuordnung zu Charakteren basierend auf Klasse und Level

#### 2.6 Extensible Rule Engine
- **FR-2.6.1**: Dynamisches System für Boni/Mali-Berechnung
  - Regeln können new Effects registrieren (z.B. +2 STR, Vorteil auf Würfe)
  - Automatische Neuberechnung aller Werte bei Regeländerung
  - Keine Code-Änderungen nötig für neue Regeln

---

### 3. Charakterentwicklung

#### 3.1 Levelaufstieg
- **FR-3.1.1**: Spieler können einen Charakter um ein Level erhöhen
  - Bei Multiclassing: Spieler wählt, welche Klasse den Level bekommt
  - Beispiel: Charakter ist Barbar 5 / Magier 2 → nächster Level geht in Barbar 6 oder Magier 3
- **FR-3.1.2**: Automatische Berechnung bei Levelaufstieg (basierend auf gewählter Klasse aus Datenbank):
  - Neue Trefferpunkte (Hit Die je nach Klasse, mit Mindestens-1 pro Hit Würfel)
  - Base Attack Bonus Erhöhung (kumulativ)
  - Rettungswürfe Anpassung (kumulativ)
  - Neue Fertigkeitspunkte basierend auf INT Modifier und gewählter Klasse
  - Prüfung auf neue verfügbare Klassenfähigkeiten für die gewählte Klasse
- **FR-3.1.3**: Anzeige verfügbarer Feats bei passenden Gesamtstufen (3, 6, 9, 12, etc.)
  - Feats werden auf Basis der Gesamtstufe gewährt, nicht pro Klasse
- **FR-3.1.4**: Erinnerung an verfügbare Klassenfähigkeiten für den nächsten Level in der gewählten Klasse (aus Datenbank)

#### 3.2 Fähigkeitspunkte (Ability Score Improvements)
- **FR-3.2.1**: Speichern von Ability Score Erhöhungen bei Gesamtstufen 4, 8, 12, 16, 20
  - Basiert auf Gesamtstufe, nicht auf Klassen-Level
- **FR-3.2.2**: Automatische Neuberechnung aller abhängigen Werte

#### 3.3 Levelverlauf
- **FR-3.3.1**: Übersicht aller bisherigen Level Durchläufe
- **FR-3.3.2**: Optionale Notizen pro Level (Entwicklung, neue Fähigkeiten, etc.)

---

### 4. Spielverlauf & Dokumentation

#### 4.1 Kampagnen-Historie
- **FR-4.1.1**: Speichern von Abenteuern/Spielsessions
  - Datum, Ort, Kurzbeschreibung
  - Erlebte XP, erhaltene Gegenstände, wichtige Ereignisse
- **FR-4.1.2**: Chronologische Anzeige des Spielverlaufs
- **FR-4.1.3**: Notizen pro Session (optional)

#### 4.2 Charaktermotivation & Lore
- **FR-4.2.1**: Speichern von Charakterbackstory
- **FR-4.2.2**: Persönliche Ziele und Motivationen
- **FR-4.2.3**: Beziehungen zu NPCs und anderen Charakteren

#### 4.3 Besitztümer & Errungenschaften
- **FR-4.3.1**: Langfristige Gegenstände und Ressourcen
- **FR-4.3.2**: Abgeschlossene Quests/Achievements

---

### 5. In-Game Charakterbogen (Live Sheet)

#### 5.1 Schnelle Referenzen
- **FR-5.1.1**: Kompakte Übersicht für Tabletop-Sessions
  - Charakterbild
  - Aktuelle HP und AC
  - Initiative
  - Wichtigste Angriffswürfe und Schadensangaben
  - Top-Fertigkeiten
- **FR-5.1.2**: Mobile-optimiertes Layout für Tabletop-Nutzung
- **FR-5.1.3**: Große, gut lesbare Schriftgrößen

#### 5.2 Dynamische Bonusberechnung
- **FR-5.2.1**: Einfache Eingabe von aktuellen Boni/Mali
  - Temporäre Boni durch Zauber oder Effekte
  - Schadensboni, Rettungswurf-Modifikatoren, etc.
- **FR-5.2.2**: Automatische Neuberechnung aller Werte basierend auf Regeldatenbank
- **FR-5.2.3**: Rückgängigmachen von Änderungen

#### 5.3 Aktionsleiste
- **FR-5.3.1**: Schnelle Aktionen zum Würfeln:
  - W20 für verschiedene Angriffswürfe
  - Schadensmodifizierer anwenden
  - Rettungswürfe
- **FR-5.3.2**: Anzeige der Würfelergebnisse mit Boni/Mali
- **FR-5.3.3**: Würfelverlauf pro Session (optional)

---

## Nicht-Funktionale Anforderungen

### 5. Benutzerfreundlichkeit
- **NFR-5.1**: Intuitive Navigation durch Charakterdaten
- **NFR-5.2**: Klar strukturierte Seiten
- **NFR-5.3**: Kontextbezogene Hilfe und Tooltips für Pathfinder-Regeln
- **NFR-5.4**: Responsive Design für Desktop und Tablet

### 6. Datenverwaltung
- **NFR-6.1**: Persistente Speicherung von Charakterdaten
- **NFR-6.2**: Backup und Export-Funktion (CSV, PDF)
- **NFR-6.3**: Import von Charakterdaten (optional Phase 2)
- **NFR-6.4**: Versionskontrolle von Charakteränderungen

### 7. Sicherheit
- **NFR-7.1**: Authentifizierung für Benutzer
- **NFR-7.2**: Datenschutz (DSGVO-Konformität)
- **NFR-7.3**: Sichere Speicherung von Benutzerdaten

### 8. Performance
- **NFR-8.1**: Schnelle Seitenladung (< 3 Sekunden)
- **NFR-8.2**: Responsive Interaktionen (< 500ms für Recalculation)
- **NFR-8.3**: Offline-Funktionalität für Live-Sheets (optional)

### 9. Wartbarkeit
- **NFR-9.1**: Sauberer, dokumentierter Code
- **NFR-9.2**: Testabdeckung (Unit Tests, Integration Tests)
- **NFR-9.3**: Pathfinder-Regelwerk als Datenbank versioniert

### 10. Erweiterbarkeit
- **NFR-10.1**: Modular aufgebautes Regelwerk-System
  - Neue Klassen ohne Code-Änderung hinzufügbar
  - Neue Rassen ohne Code-Änderung hinzufügbar
  - Neue Feats ohne Code-Änderung hinzufügbar
  - Neue Zauber ohne Code-Änderung hinzufügbar
- **NFR-10.2**: Einfache Admin-UI für Regelwerk-Verwaltung
- **NFR-10.3**: Datensicherung der Regelwerk-Datenbank (Export/Import)

---

## Pathfinder-Regelwerk Abhängigkeiten

Diese Anwendung basiert auf **Pathfinder 1st Edition** Regeln:
- Core Rulebook Attribut- und Skilldefinitionen
- Klassen-spezifische Regeln (BAB-Progression, Hit Die, Class Features)
- Rassen-Boni und -Malus
- Feat-Listen und -Voraussetzungen
- Zauber nach Klasse
- Standard Kampf- und Rettungswurf-Regeln

Alle Regel-Berechnungen müssen diesem Regelwerk entsprechen.

---

## Phase-weise Implementierung

### Phase 1: MVP (Minimum Viable Product)
- Benutzerregistrierung und Authentifizierung
- Regelwerk-Admin-Interface (Klassen, Rassen, Feats, Zauber)
- Initial-Data-Set: Barbar + Magier, Basis-Rassen
- Charaktererstellung mit Bildupload
- Multi-Character Management
- Multiclassing Support (Charaktere können mehrere Klassen haben)
- Basis-Attribut-Verwaltung
- Automatische Berechnung von Kampfwerten
- Einfacher Levelaufstieg (mit Klasse-Auswahl bei Multiclassing)
- Grundlegendes Live-Sheet

### Phase 2: Erweiterte Features
- Feats-System mit Voraussetzungs-Validierung
- Ausrüstungsverwaltung
- Spielverlauf-Dokumentation
- Erweiterte Live-Sheet Funktionen
- Neue Klassen/Rassen hinzufügen (z.B. Schurke, Priester, etc.)

### Phase 3: Polish & Optimierung
- Export/Import
- Offline-Modus
- Erweiterte Statistiken
- Community Features (optional)

---

## Akzeptanzkriterien

- ✓ Charaktere können erstellt und geladen werden
- ✓ Ein Spieler kann mehrere Charaktere verwalten
- ✓ Charaktere können Bilder haben
- ✓ Multiclassing wird unterstützt (ein Charakter kann mehrere Klassen haben)
  - Gesamtstufe = Summe aller Klassen-Level
  - HP-Berechnung: Summe aller Hit Dice
  - BAB und Rettungswürfe: kumulativ
  - Class Features: aus allen Klassen
  - Feats: basierend auf Gesamtstufe
- ✓ Alle Berechnungen folgen Pathfinder 1st Edition Regeln (aus Datenbank)
- ✓ Neue Klassen/Rassen/Feats/Zauber können ohne Code-Änderung hinzugefügt werden
- ✓ Initial-Data-Set (Barbar + Magier) funktioniert
- ✓ Levelaufstieg funktioniert automatisch und korrekt
- ✓ Live-Sheet zeigt aktuelle, korrekte Werte
- ✓ Boni und Mali werden korrekt angerechnet
- ✓ Spielverlauf wird dokumentiert
- ✓ Admin-Interface zur Verwaltung des Regelwerks vorhanden
