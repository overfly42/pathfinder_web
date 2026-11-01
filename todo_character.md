# Offene Punkte: Knaar Petz, Parzival Petz und Horus

Stand: 2026-11-01, geprüft an den Charakterbögen der laufenden App (Dev-DB).

- **Knaar Petz**: Halb-Ork, Jäger 7 (Göttlicher Jäger), NG, Domäne: Unterdomäne der Erforschung (Reisen), Sekundärklasse Magier (Elementarmagieschule der Luft)
- **Parzival Petz**: Tiergefährte von Knaar, Grizzlybär (Hausregel), Elementargefährte: Luft (Hausregel), effektive Stufe 7
- **Horus**: Vertrauter von Knaar, Falke, effektive Stufe 7

**Art** sagt, was eine Umsetzung bringen würde:

- **Spielwerte**: ändert Zahlen auf dem Bogen (Bewegungsrate, Initiative, Fertigkeiten, Zauberliste, …), wird derzeit nicht berechnet.
- **Hinweis**: kein fester Wert, aber eine Erinnerung am passenden Wert wäre hilfreich (situative Boni, Resistenzen, Sinne).
- **Nur Beschreibung**: reine Regel- oder Erzählwirkung, der Beschreibungstext auf dem Bogen genügt.

## Knaar Petz

| Element | Quelle | Was fehlt | Art | Anmerkung |
| --- | --- | --- | --- | --- |
| Domänenzauber | Domäne (Göttlicher Jäger) | Die Domänenzauber werden nicht in die bekannten Zauber eingetragen: Grad 1 Rascher Rückzug (ersetzt Lange Schritte durch die Unterdomäne), Grad 2 Gegenstand aufspüren; ab Stufe 9 Grad 3 Fliegen. | Spielwerte | Im Importskript bewusst als Text belassen (`scripts/import_jaeger_archetypes.py`); der Archetyp nennt aber die Grade (Grad 1 ab 3., Grad 2 ab 6., …). |
| Bewegungsrate +3 m | Verliehene Fähigkeiten (Domäne der Reisen) | Bogen zeigt 9 m statt 12 m. | Spielwerte | Wirkt sich auch auf den Sprungbonus bei Akrobatik aus. |
| Luftüberlegenheit | Schulfähigkeit (Sekundärklasse Magier), Elementarmagieschule der Luft | Fehlt ganz: +3 Verbesserungsbonus auf Fliegen (+2, +1 je 5 Stufen), Federfall nach Belieben. | Spielwerte | Ab Stufe 7 bekommt der Charakter über die Sekundärklasse die Schulfähigkeiten der 1. Stufe; keine davon steht auf dem Bogen. |
| Blendender Blitz | Schulfähigkeit (Sekundärklasse Magier), Elementarmagieschule der Luft | Fehlt ganz: Elektrizitätsschaden im 1,5-m-Umkreis, Anwendungen pro Tag. | Spielwerte | Als aktivierbare Fähigkeit mit Tageszähler wie andere Schulkräfte. |
| Reaktionsschnell | Wesenszug | +2 Wesenszugbonus auf Initiative fehlt (Bogen zeigt +1). | Spielwerte | |
| Bestiensinne | Alternatives Volksmerkmal (Halb-Ork) | +2 auf Wahrnehmung fehlt. | Spielwerte | |
| Geübter Kletterer | Alternatives Volksmerkmal (Halb-Ork) | +1 auf Akrobatik und Klettern fehlt. | Spielwerte | |
| Wissen (Gewölbekunde) | Klassenfertigkeiten (Göttlicher Jäger) | Bleibt Klassenfertigkeit, obwohl der Archetyp sie gegen Wissen (Religion) tauscht. | Spielwerte | Derzeit ohne Auswirkung, solange Knaar keine Ränge darin hat. |
| Waffenvertrautheit (Halb-Orks) | Volksmerkmal | Umgang mit Krummschwert, Zweihändiger Axt und orkischen Waffen (als Kriegswaffen) wird nicht berechnet. | Spielwerte | Bei Knaar ohne Auswirkung: Als Jäger beherrscht er Kriegswaffen ohnehin; relevant nur bei orkischen exotischen Waffen. |
| Orkblut | Volksmerkmal | Zählt nicht als Mensch und Ork bei Voraussetzungen (Talente, Wesenszüge, Gegenstände). | Spielwerte | Wirkt nur auf die Auswahl, nicht auf Zahlen. |
| Genauer Schlag | Talent (Gemeinschaftstalent) | +1W6 Präzisionsschaden, wenn ein Verbündeter mit demselben Talent denselben Gegner flankiert. | Hinweis | Parzival hat das Talent auch: ein Hinweis am Angriff („+1W6 beim Flankieren mit Parzival“) wäre sinnvoll. |
| Ausmanövrieren | Talent (über Genaues Ausmanövrieren) | +4 statt +2 Angriffsbonus beim Flankieren. | Hinweis | Am Angriff als situativer Bonus. |
| Dunkelsicht | Volksmerkmal | 18 m, keine eigene Sinnes-Anzeige auf dem Bogen. | Hinweis | Gilt genauso für Dämmersicht und Geruchssinn bei Parzival und Horus (gemeinsame „Sinne“-Zeile). |
| Röntgenblick | Unterdomäne der Erforschung (ersetzt Flinkfuß) | Wie Hellsehen durch Oberflächen. | Nur Beschreibung | Ohne Tageslimit; Wirkungsdauer steht im Text. |
| Tierseele | Talent | Tierzauber dürfen auch Knaar betreffen. | Nur Beschreibung | |
| Böse, chaotische, gute und rechtschaffene Zauber | Klassenmerkmal Jäger | Zauber gegen die Gesinnung der Gottheit sind verboten. | Nur Beschreibung | Bräuchte ein Gottheiten-Modell (gleicher offener Punkt wie beim Kleriker). |
| Naturausbildung | Klassenmerkmal Jäger | Jägerstufe zählt als Druiden-/Waldläuferstufe für Talente und Optionen, die den Tiergefährten betreffen. | Nur Beschreibung | Würde erst bei entsprechenden Voraussetzungen relevant. |
| Verbesserte Empathische Verbindung | Klassenmerkmal Jäger | Durch die Augen des Gefährten sehen. | Nur Beschreibung | |
| Unterholz durchqueren | Klassenmerkmal Jäger | Ungehindert durch natürliches Unterholz. | Nur Beschreibung | Steht bei Parzival bereits als Hinweis. |

## Parzival Petz (Tiergefährte)

| Element | Quelle | Was fehlt | Art | Anmerkung |
| --- | --- | --- | --- | --- |
| Celestische Schablone | Außerweltlicher Gefährte (Knaar ist NG) | Steht nur als Hinweistext. Nach der Schablone (Monsterhandbuch) bei 6 TW: Dunkelsicht 18 m, Resistenz gegen Elektrizität, Kälte und Säure 10, SR 5/Böses, ZR = HG + 5, Böses niederstrecken 1/Tag. | Hinweis | Sinne und ZR hätten Platz auf dem Bogen; Resistenzen und SR gibt es dort bisher nicht als Werte. Zahlen vor der Umsetzung gegen das PRD prüfen. |
| Ergreifen | Besonderer Angriff der Tierart | Am Klauenangriff vermerkt, aber der +4-Bonus auf KMB für Ringkämpfe fehlt. | Hinweis | Am KMB als situativer Bonus. |
| Genauer Schlag | Talent | Wie bei Knaar: +1W6 beim gemeinsamen Flankieren. | Hinweis | |
| Dämmersicht, Geruchssinn | Tierart | Keine Sinnes-Anzeige. | Hinweis | Siehe Dunkelsicht bei Knaar. |
| Elementare Unterart (Luft) | Elementargefährte (Hausregel) | Unterart wird nur genannt. | Nur Beschreibung | |
| Zauber teilen | Tiergefährte | Zauber auf sich selbst auch auf den Gefährten wirken. | Nur Beschreibung | |

## Horus (Vertrauter)

| Element | Quelle | Was fehlt | Art | Anmerkung |
| --- | --- | --- | --- | --- |
| Verbessertes Entrinnen | Vertrauter | Keine Kennzeichnung am Reflexwurf. | Hinweis | Gilt genauso für Entrinnen bei Tiergefährten. |
| Dämmersicht | Tierart | Keine Sinnes-Anzeige. | Hinweis | |
| Zauber teilen | Vertrauter | | Nur Beschreibung | |
| Empathische Verbindung | Vertrauter | | Nur Beschreibung | |
| Berührungszauber übermitteln | Vertrauter | | Nur Beschreibung | |
| Mit Meister sprechen | Vertrauter | | Nur Beschreibung | |
| Mit Tieren seiner Art sprechen | Vertrauter | | Nur Beschreibung | |

## Ausrüstung: Besondere Materialien

Quelle: [Ausrüstungskompendium, Besondere Materialien](https://prd.5footstep.de/Ausr%C3%BCstungskompendium/Waffen-und-R%C3%BCstungen/Besondere-Materialien). In der App gibt es dafür keinen Katalog: Ein Material lässt sich bei einem Ausrüstungsgegenstand nur als Freitext in den Eigenschaften eintragen und wird nicht berechnet. Betrifft Knaars Krummschwert und Lamellar-Rüstung (Leder) sowie jede künftige Ausrüstung der drei.

| Element | Quelle | Was fehlt | Art | Anmerkung |
| --- | --- | --- | --- | --- |
| Materialkatalog und Auswahl | Besondere Materialien | Material pro Waffe/Rüstung wählbar machen, mit Preisaufschlag nach Gegenstandsart (leichte/mittelschwere/schwere Rüstung, Waffe, Munition) und „gilt als Meisterarbeit“ (Mithral, Feuer-/Eisgeschmiedeter Stahl, Schwarzholz, Drachenhaut). | Spielwerte | Grundlage für alle folgenden Zeilen; nicht jedes Material passt zu jedem Gegenstand (z. B. Aalhaut nur Leder-, Fell- oder beschlagene Lederrüstung, Kaltes Eisen nur mit Metallteilen). |
| Mithral (Rüstung) | Besondere Materialien | Eine Rüstungskategorie leichter (Bewegungsrate, Umgang), höherer max. GE-Bonus, geringerer Rüstungsmalus und Zauberpatzer, halbes Gewicht. | Spielwerte | Würde z. B. die Bewegungsrate bei mittelschwerer Rüstung und Knaars Rüstungsmalus auf Akrobatik, Klettern, Fliegen usw. ändern. |
| Aalhaut, Schwarzblattstoff (Rüstung) | Besondere Materialien | Rüstungsmalus und max. GE-Bonus verbessert bzw. halbes Gewicht; Aalhaut zusätzlich Schutz gegen Elektrizität. | Spielwerte | Beide sind für Lederrüstungen gedacht. Ob Knaars Lamellar-Rüstung (Leder) dazuzählt, im PRD-Text prüfen. |
| Adamant, Elysische Bronze (Rüstung) | Besondere Materialien | Schadensreduzierung 1/–, 2/– oder 3/– je nach Rüstungskategorie; Elysische Bronze nur gegen natürliche Waffen magischer Bestien und monströser Humanoider. | Hinweis | Der Bogen hat keinen SR-Wert; als Hinweis an der RK. |
| Feuer-/Eisgeschmiedeter Stahl, Engelhaut, Lebendstahl (Rüstung) | Besondere Materialien | Energieresistenz bzw. Auren- und Gesinnungseffekte bzw. Beschädigung angreifender Metallwaffen. | Hinweis | Situativ, Resistenzen haben noch kein eigenes Feld. |
| Adamant, Kaltes Eisen, Alchemistensilber, Elysische Bronze (Waffe) | Besondere Materialien | Überwinden der passenden Schadensreduzierung (bzw. Härte bei Adamant). | Hinweis | Am Angriff anzeigen („überwindet SR/Kaltes Eisen“); dieselbe Anzeige bräuchte Parzival, falls er später die Größere elementare Manifestation (Erde) hätte. |
| Alchemistensilber (Waffe) | Besondere Materialien | −1 auf Schadenswürfe mit Hieb- und Stichwaffen (mind. 1 Schaden). | Spielwerte | Würde Knaars Krummschwert-Schaden ändern. |
| Blutkristall, Feuer-/Eisgeschmiedeter Stahl, Trauerwurz, Viridium (Waffe) | Besondere Materialien | Zusatzschaden gegen blutende Ziele, Energieschaden nach Aufladung, Lebenskraftspeicher, Krankheit bei Treffer. | Hinweis | Situative Effekte am Angriff. |
| Schwarzholz, Grünholz, Peitschenholz, Greifenmähne | Besondere Materialien | Gewicht, Selbstheilung des Gegenstands, Sondereigenschaften von Holzwaffen bzw. Kleidung. | Nur Beschreibung | Gewicht wird erst mit einer Traglast-Berechnung relevant (eigener offener Punkt in `todos.md`). |
| Primitive Materialien (Bronze, Gold, Knochen, Obsidian, Stein) | Besondere Materialien | Abzüge bzw. Zerbrechlichkeit für Waffen und Rüstungen aus diesen Materialien. | Nur Beschreibung | Nur in Kampagnen ohne Stahl relevant. |

## Ausrüstung: Ausrüstungsplätze für Tiere

Parzival und Horus haben auf ihrem Bogen dieselben 17 Ausrüstungsplätze wie ein humanoider Charakter, darunter Ringe, Hände, Hauptwaffe, Nebenhand und Schild. Tiere haben aber einen eingeschränkten Satz. Die deutsche PRD regelt das nicht; die Beschreibung der Ausrüstungsplätze im Ausrüstungskompendium (Wundersame Gegenstände) geht nur von Humanoiden aus. Die Regel für nichthumanoide Kreaturen steht im englischen *Ultimate Equipment*. Vor der Umsetzung muss entschieden werden, ob sie als Hausregel übernommen wird (dann in `requirements_v2.md` unter „Hausregeln“ eintragen).

| Element | Quelle | Was fehlt | Art | Anmerkung |
| --- | --- | --- | --- | --- |
| Eigener Platzsatz für Tiere | Ultimate Equipment (nicht im PRD) | Gefährten und Vertraute zeigen alle humanoiden Plätze. Nur die für Tiere erlaubten Plätze anzeigen und belegbar machen. | Spielwerte | Welche Plätze genau erlaubt sind (z. B. Hals, Kopf, Stirnband, Augen, Schultern, Brust, Gürtel, Füße/Hufeisen, Handgelenke/Vorderbeine), anhand der Quelle festlegen. Dabei gilt: Ein Gegenstand wirkt nur in einem belegbaren Platz, sonst dürfte er nicht in die Werte eingehen. |
| Keine Waffen-, Schild-, Hand- und Ringplätze | Ultimate Equipment (nicht im PRD) | Hauptwaffe, Nebenhand, Schild, Hände und beide Ringplätze sind bei Tieren belegbar, obwohl sie keine Waffen führen und keine Hände haben. | Spielwerte | Ihre Angriffe sind die natürlichen Angriffe der Tierart, die der Bogen bereits berechnet. |
| Unterschied Vierbeiner / Vogel | Ultimate Equipment (nicht im PRD) | Ein Vogel wie Horus hat einen anderen Körperbau als ein Vierbeiner wie Parzival (Flügel statt Vorderbeine). | Spielwerte | Prüfen, ob die Quelle nach Körperbau unterscheidet. Die Gefährten-Tierarten bräuchten dann eine Angabe zum Körperbau. |
| Rüstung für Tiere (Rossharnisch) | Ausrüstungskompendium, Rüstungen („Rüstungen für ungewöhnliche Kreaturen“) | Der Rüstungsplatz bleibt. Für nichthumanoide Kreaturen gelten aber eigene Preis- und Gewichtsfaktoren je Größe (z. B. Mittelgroß Kosten ×2); ob die App sie anwendet, ist ungeprüft. | Spielwerte | Halber Rüstungsbonus für sehr kleine Träger und das Verlangsamen durch Rossharnisch sind bereits umgesetzt. |

## Bereits umgesetzt (zur Einordnung)

Diese Elemente sind auf dem Bogen als „Nur Text“ markiert, werden aber an anderer Stelle berechnet:

- **Tiergefährte (Jäger), Vertrauter (Magier)**: Anspruch auf Gefährte bzw. Vertrauten (Gefährten-Abschnitt).
- **Umgang mit Waffen und Rüstungen, Umgang mit Rüstungen (leichte)**: Waffen- und Rüstungskompetenz bei Angriffen und Rüstungsmalus.
- **Zauber, Stoßgebete**: Zauberliste und Zauberplätze.
- **Halb-Ork (Jäger)**: +1 TP je Wahl für Parzival (7 Wahlen = +7 TP).
- **Tieraspekt (Tiergefährte)**: wird auf Parzivals Bogen berechnet (Stier).
- **Genaues Ausmanövrieren**: Ausmanövrieren als Talent bei Knaar, Hinweis bei Parzival.
- **Gesinnung (Göttlicher Jäger)**: wird bei der Gesinnungswahl geprüft.
- **Bonus für den Meister (Falke)**: +3 Wahrnehmung bei Tageslicht als Hinweis an Knaars Wahrnehmung.
