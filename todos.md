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
      verbleibenden `backend/app/fixtures/*.json`. Begonnen, eine Rasse/
      Klasse nach der anderen (nicht als Bulk-Ersetzung), gegen
      `prd.5footstep.de` (deutsches PF1e-SRD) als Quelle:
  - [x] **Mensch** (Quelle: <http://prd.5footstep.de/AusbauregelnIIIVoelker/Grundvoelker/Menschen>):
        `base_race_abilities.json`/`race_ability_grants.json`/
        `race_ability_replacements.json` korrigiert — die drei echten
        Standard-Volksmerkmale (freier +2-Attributsbonus, Bonustalent,
        „Geschult", vormals fälschlich „Vielseitig" benannt) bestätigt;
        zwei erfundene Alternativmerkmale („Bemerkenswerte Fertigkeit",
        „Fokussierter Geist" — keine passten zu echten PF1e-Inhalten)
        entfernt. **Nachtrag (2026-07-31):** Die Aussage „Mensch hat aktuell
        keine Alternativmerkmale" war falsch — die Quelle listet unter
        „Alternative Volksmerkmale" tatsächlich 15 echte Einträge, die beim
        ersten Durchgang übersehen wurden. Nachträglich ergänzt: Bergkind,
        Blick für Begabungen, Doppelte Begabung, Elendskind, Findelkind,
        Glattzüngig, Heldenhaft, Konzentriertes Lernen, Landkind, Meereskind,
        Mischling, Naturkind, Sommerkind, Stadtkind, Winterkind — inklusive
        korrekter Ersetzt-Beziehungen („Doppelte Begabung" ersetzt sogar drei
        Merkmale gleichzeitig: den freien +2-Attributsbonus, Bonustalent
        *und* Geschult). Dabei einen
        echten Bug behoben: „Geschult" (+1 Fertigkeitsrang pro Stufe) war
        zwar als Datensatz vorhanden, wurde aber nirgends berechnet — jetzt
        in `backend/app/rules/skill_points.py` (`race_grants_bonus_skill_point_per_level`,
        gleiches Muster wie `rules/feat_slots.py`s `race_grants_bonus_feat`)
        sowie im Frontend-Gegenstück (`creationCalculations.ts`s
        `skillPointsTotal`) verdrahtet. Im selben Zug strukturell für alle
        7 Rassen korrigiert (nicht nur Mensch): Bewegungsrate war eine reine
        `BaseRace.speed`-Spalte (jetzt entfernt, Migration `005957a8da7f`)
        und Größe (Mittelgroß/Klein) war gar nicht modelliert — beides sind
        jetzt echte Volksmerkmal-Grants (`rules/speed.py`), inklusive der
        zwei tatsächlich kleinen Völker (Halbling, Gnom), die zuvor
        stillschweigend als mittelgroß behandelt wurden.
  - [x] **Halbling** (Quelle: <http://prd.5footstep.de/AusbauregelnIIIVoelker/Grundvoelker/Halblinge>):
        Standard-Volksmerkmale korrigiert — „Flink" (falscher Name/Wert:
        +4 auf Akrobatik nur bei Balanceakten) war eigentlich „Wendig" (+2
        auf Akrobatik *und* Klettern); „Glücklich" war eigentlich
        „Halblingsglück" (gleicher Wert, falscher Name/Bonustyp). Zwei
        fehlende echte Standardmerkmale ergänzt: „Geschärfte Sinne" (+2
        Wahrnehmung) und „Waffenvertrautheit (Halblinge)". Zwei erfundene
        Alternativmerkmale („Unauffällig", „Geschickter Wanderer" — keines
        passte zu echten PF1e-Inhalten) entfernt und durch **alle 13 echten
        Alternativmerkmale** ersetzt (Arglistig, Einschmeichelnd, Flinker
        Schleuderer, Grenzreiter, Mehrsprachigkeit, Praktisch begabt,
        Schnell wie ein Schatten, Schnell zu Fuß, Tiefschlag, Vielseitiges
        Glück, Wanderslust, Wuselig, Zaghaft), inklusive korrekter
        Ersetzt-Beziehungen (mehrere ersetzen zwei Merkmale gleichzeitig,
        z. B. „Schnell zu Fuß" ersetzt sowohl Verminderte Bewegungsrate als
        auch Wendig). Rein kompositionell (Auswahl-Optionen), keine neue
        Berechnung — siehe die zwei offenen Lücken unten.
  - [x] **Halb-Ork** (Quelle: <http://prd.5footstep.de/AusbauregelnIIIVoelker/Grundvoelker/HalbOrks>):
        Zwei fehlende echte Standardmerkmale ergänzt: „Einschüchternd" (+2
        Einschüchtern) und „Waffenvertrautheit (Halb-Orks)" (Krummschwert,
        Zweihändige Axt, orkische Waffen als Kriegswaffen). Die vorhandene
        Fähigkeit „Kampfrausch" war inhaltlich bereits die richtige
        Standardfähigkeit, aber falsch benannt/zu knapp beschrieben — in
        „Orkische Wildheit" umbenannt und die Beschreibung an den Wortlaut
        der Quelle angeglichen. Zwei erfundene Alternativmerkmale
        („Einschüchternde Erscheinung", „Wildnisschritt" — keines passte zu
        echten PF1e-Inhalten) entfernt und durch **alle 14 echten
        Alternativmerkmale** ersetzt (Bestiensinne, Geschult [teilt sich die
        Katalogzeile mit Mensch], Gesteigerte Dunkelsicht, Geübter Kletterer,
        Heilige Tätowierung, Herr der Bestien, Höhlenkundiger, Kettenkrieger,
        Kind der Großstadt, Lumpensammler, Reißzähne, Schamanenschüler,
        Waldwanderer, Zerstörer), inklusive korrekter Ersetzt-Beziehungen.
        Rein kompositionell, keine neue Berechnung.
  - [x] **Elf** (Quelle: <http://prd.5footstep.de/AusbauregelnIIIVoelker/Grundvoelker/Elfen>):
        Vier Standardmerkmale waren falsch benannt/unvollständig — „Niedrigsichtig"
        war eigentlich „Dämmersicht"; „Widerstandsfähiger Geist" und
        „Zauberkundig" waren ein falsch benannter, aufgespaltener Ersatz für
        die zwei echten Merkmale „Elfische Immunität" und „Elfenmagie"
        (Elfenmagie fehlte dabei der SR-Überwindungs-Bonus, „Zauberkundig"
        nutzte zudem die falsche Fertigkeit); „Elfische Waffenvertrautheit"
        fehlten Kurzbogen/Kompositkurzbogen. Zwei erfundene Alternativmerkmale
        („Eisenkultur", „Küstenbewohner") entfernt und durch **alle 13 echten
        Alternativmerkmale** ersetzt (Abgesandter, Arkane Konzentration,
        Dunkelsicht, Elementarresistenz, Ewiger Groll, Leichtfüßig,
        Lichtbringer, Naturverbundenheit, Schleichender Jäger,
        Stadtverbundenheit, Traumdeuter, Wasserverbundenheit, Wüstenläufer),
        inklusive korrekter Ersetzt-Beziehungen (drei ersetzen zwei Merkmale
        gleichzeitig). Elfs alternative „Dunkelsicht" ist bewusst eine eigene
        Katalogzeile statt der mit Halb-Ork geteilten: sie trägt zusätzlich
        Lichtempfindlichkeit, ein echter mechanischer Unterschied. Rein
        kompositionell, keine neue Berechnung. Beim Korrigieren einen echten
        Bug gefunden und behoben: die neue Katalogzeile für „-2 auf
        Konstitution" nutzte zunächst eine frisch generierte UUID statt der
        in `rules/race_abilities.py`s `HANDLERS`-Registry fest verdrahteten
        `ABILITY_KO_MINUS2`-ID — dadurch griff Elfs KO-Malus in keiner
        Berechnung (u. a. TP), bis die ID korrigiert wurde; ein Hinweis
        darauf, wie leicht eine neue Zeile für ein bereits über `HANDLERS`
        berechnetes Attribut die falsche ID bekommt, wenn sie nicht bewusst
        mit der bestehenden Zeile abgeglichen wird.
  - [x] **Zwerg, Gnom, Halbelf entfernt (2026-07-31):** Diese drei Rassen
        wurden nie gegen `prd.5footstep.de` geprüft (reines LLM-geratenes
        Platzhaltermaterial). Auf expliziten Wunsch komplett aus
        `base_races.json`/`base_race_abilities.json`/`race_ability_grants.json`/
        `race_ability_replacements.json` entfernt statt weiter als ungeprüfter
        Platzhalter mitgeführt — mit Elf/Mensch/Halbling/Halb-Ork geteilte
        Katalogzeilen (z. B. Dunkelsicht, die Attribut-±2-Katalogeinträge)
        blieben erhalten. Aktuell sind nur noch **vier** Rassen spielbar:
        Mensch, Halbling, Halb-Ork, Elf. Sollten Zwerg/Gnom/Halbelf später
        wieder gebraucht werden, müssen sie neu und einzeln gegen die echte
        Quelle aufgebaut werden (nicht aus der Git-Historie zurückgeholt, da
        die alten Daten selbst ungeprüft/teilweise erfunden waren).
  - [x] **Kämpfer** (Quelle: <http://prd.5footstep.de/Grundregelwerk/Klassen/Kaempfer>):
        Der Klassenname war falsch — hieß `Krieger` statt `Kämpfer` — und wurde
        überall korrigiert: `base_classes.json`/`classes.json`/
        `character_2.json`/`progression_2.json`, Backend-Kommentare/Tests,
        sowie im Frontend `levelUpCalculations.ts`s
        `fighterBonusFeatGrantedThisLevel`, die hart `className === 'Krieger'`
        verglich — nach der Umbenennung hätte das den Kämpfer-Bonustalent-Slot
        beim Stufenaufstieg still und leise nicht mehr ausgelöst. Im selben
        Zug wurde diese Funktion (jetzt `classBonusFeatGrantedThisLevel`)
        generalisiert: statt eines hart codierten Klassennamens fragt sie
        `ClassDef.bonusFeatLevels` ab (echte, vom Backend gelieferte Daten),
        funktioniert damit für jede Klasse mit Bonustalent-Daten, und
        vergleicht jetzt die eigene Stufe der Klasse statt der
        Charaktergesamtstufe (behebt nebenbei einen Mehrklassen-Bug). Hit
        Dice/GAB/Rettungswürfe/Fertigkeitspunkte waren bereits korrekt.
        Klassenfertigkeiten waren nur zur Hälfte korrekt (5 von 10 laut
        Quelle) — ergänzt: Beruf, Mit Tieren umgehen, Überlebenskunst,
        Wissen (Baukunst), Wissen (Gewölbekunde); die letzten beiden gab es
        noch gar nicht im gemeinsamen `base_skills.json`-Katalog und wurden
        dort neu angelegt. Die restlichen Klassenmerkmale der Quelle
        (Umgang mit Waffen und Rüstungen, Tapferkeit, Rüstungstraining,
        Waffentraining inkl. Waffengruppen, Rüstungsmeisterschaft,
        Waffenmeisterschaft) gab es im Datenmodell noch gar nicht (nur für
        Bonustalent gab es bereits Daten) — als reine Katalogzeilen
        (`BaseClassAbility`/`BaseClassAbilityGrant`) ergänzt, analog zu einer
        unberechneten Rassenfähigkeit wie Dunkelsicht: keine
        Berechnungslogik (kein Handler-Register für Klassenfähigkeiten wie
        `rules/race_abilities.py`s `HANDLERS` existiert noch), und aktuell
        auch kein Endpunkt, der generische Klassenfähigkeiten wie
        `/api/races` exponiert — die Daten sind also vorhanden, aber vom
        Frontend noch nicht erreichbar. Archetypen (`Waffenmeister`,
        `Söldnerkommandant`) noch nicht gegen eine Quelle geprüft.
  - [x] **Kämpfer-Archetyp Zwei-Waffen-Kämpfer** (Quelle:
        <http://prd.5footstep.de/Expertenregeln/Klassen/Grundklassen/Kaempfer/ZweiWaffenKaempfer>):
        Als neue `BaseClass`-Zeile (`arch_class_of` = Kämpfer) ergänzt, plus
        alle 8 eigenen Klassenmerkmale (Defensiver Wirbel, Zwillingsklingen,
        Doppelangriff, Verbesserte Balance, Doppelte Gelegenheit, Perfekte
        Balance, Geschickter Doppelangriff, Tödliche Verteidigung) als
        `BaseClassAbility`/`BaseClassAbilityGrant`-Zeilen, mit
        `base_class_id` auf die Archetyp-Zeile statt die Kämpfer-Wurzel (bis
        jetzt hatte kein Archetyp eigene Grants). Dafür neu eingeführt:
        `BaseClassAbilityReplacement` (Migration `c09f87a2a76f`) — pro Zeile
        ersetzt eine Archetyp-Fähigkeit einen konkreten
        `BaseClassAbilityGrant` der Wurzelklasse (grant-genau, nicht
        fähigkeits-genau wie `RaceAbilityReplacement`, weil ein
        Kämpfer-Archetyp oft nur einzelne Stufen eines wiederkehrenden
        Merkmals ersetzt, z. B. nur Rüstungstraining 1+2, nicht 3+4).
        `sheet.py`s `_build_class_features` wertet das jetzt aus: ersetzte
        Grants der Wurzelklasse fallen weg, sobald der Charakter den
        Archetyp gewählt hat. Auch in `classes.json` und beiden
        `pathfinder-*-mock.html`-Dateien als Archetyp-Option ergänzt.
        `Waffenmeister`/`Söldnerkommandant` bleiben weiterhin ungeprüfte
        Platzhalter ohne eigene Merkmale.
  - [x] **Waldläufer** (Quelle: <http://prd.5footstep.de/Grundregelwerk/Klassen/Waldlaeufer>):
        Trefferwürfel/GAB/Rettungswürfe/Fertigkeitspunkte/Zauberattribut
        (WE)/Zaubertradition (divine) waren bereits korrekt. Klassenfertigkeiten
        korrigiert: `Fluchtkunst` war fälschlich als Klassenfertigkeit
        hinterlegt (nicht Teil der Quellliste, Zeile in `base_class_skills.json`
        entfernt) und es fehlten Beruf, Einschüchtern, Wissen (Geographie),
        Wissen (Gewölbekunde), Zauberkunde (ergänzt; Wissen (Geographie) gab
        es noch gar nicht im `base_skills.json`-Katalog und wurde dort neu
        angelegt — analog zu Wissen (Baukunst)/(Gewölbekunde) bei Kämpfer).
        Alle 17 Klassenmerkmale der Quelle (Umgang mit Waffen und Rüstungen,
        Erzfeind, Spuren lesen, Tierempathie, Kampfstiltalent, Ausdauer,
        Bevorzugtes Gelände, Bund des Jägers, Unterholz durchqueren, Schneller
        Verfolger, Entrinnen, Beute, Tarnung, Verbessertes Entrinnen,
        Meisterliches Verstecken, Verbesserte Beute, Meisterjäger) als reine
        Katalogzeilen (`BaseClassAbility`/`BaseClassAbilityGrant`) ergänzt,
        gleiche Tiefe wie bei Kämpfer (keine Berechnungslogik). Kampfstiltalent
        bewusst *nicht* in `feat_slots.py`s `BONUS_FEAT_SLOT_ABILITY_IDS`
        aufgenommen — im Gegensatz zu Kämpfers Bonustalent ist die Auswahl
        auf eine kampfstilabhängige Talentliste beschränkt, kein freier Slot.
        Die bereits vorhandenen `BaseClassOptionChoice`-Listen für die
        Options-Gruppen `enemy` (Erzfeind) und `terrain` (Bevorzugtes Gelände)
        waren stark unvollständig (8 von 32 bzw. 7 von 11 Einträgen, teils mit
        abweichenden Bezeichnungen wie „Sumpf" statt „Feuchtgebiete") — auf
        die vollständigen Quelllisten gebracht (Zeilen mit gleicher `id`
        umbenannt, fehlende ergänzt). `max_choices: 1` an beiden Gruppen
        unverändert gelassen (weitere Erzfeind-/Geländewahlen bei
        Stufenaufstieg sind ein separates, noch nicht gebautes Feature).
  - [x] **Magier** (Quelle: <http://prd.5footstep.de/Grundregelwerk/Klassen/Magier>):
        Trefferwürfel (W6)/GAB (halb)/Rettungswürfe (nur Willen gut)/
        Fertigkeitspunkte (2 + IN)/Zauberattribut (IN)/Zaubertradition
        (arcane-prepared) waren bereits korrekt. Klassenfertigkeiten waren
        falsch: „Gegenstände magisch nutzen" (UMD) ist laut Quelle **keine**
        Magier-Klassenfertigkeit und wurde entfernt; es fehlten Beruf,
        Fliegen, Handwerk, Schätzen sowie „Wissen (alle)" — die Quelle listet
        explizit alle Wissen-Unterfertigkeiten, nicht nur Wissen (Arkanes),
        ergänzt wurden daher auch Wissen (Natur/Religion/lokal/Baukunst/
        Gewölbekunde/Geographie). „Fliegen" und „Schätzen" gab es noch gar
        nicht im gemeinsamen `base_skills.json`-Katalog und wurden dort neu
        angelegt (analog zu Wissen (Baukunst) bei Kämpfer). Außerdem einen
        falschen Fertigkeitsnamen korrigiert: der Katalogeintrag hieß
        „Linguistik", die Quelle nennt die Fertigkeit „Sprachenkunde" —
        umbenannt (nur der Anzeigename, nicht die ID/der interne Key), betrifft
        damit auch die anderen Klassen, die dieselbe Katalogzeile nutzen
        (Barde, Kleriker, Orakel, Schurke), aber nur als Namenskorrektur ohne
        weitere Datenänderung an deren Klassenfertigkeiten-Listen.
        Die bereits vorhandene Spezialschule-Options-Gruppe (`school`) hatte
        zwei falsche Schulnamen — „Weissagung" (Quelle: „Erkenntniszauber")
        und „Bannmagie" (Quelle: „Bannzauber") — korrigiert, die übrigen
        sechs Schulen (Beschwörung/Hervorrufung/Illusion/Nekromantie/
        Verwandlung/Verzauberung) sowie „Universalist" (Allgemeine Schule)
        waren bereits richtig. Alle Klassenmerkmale der Quelle, die nicht an
        eine einzelne Schulwahl gebunden sind, als reine Katalogzeilen
        (`BaseClassAbility`/`BaseClassAbilityGrant`) ergänzt — gleiche Tiefe
        wie bei Kämpfer/Waldläufer, keine Berechnungslogik: Umgang mit Waffen
        und Rüstungen, Arkane Schule, Arkane Verbindung, Zaubertricks und
        Schriftrolle anfertigen (alle Stufe 1), sowie Bonustalent (Stufen 5/
        10/15/20, geteilte Katalogzeile analog zu Kämpfers Bonus-Kampftalent).
        Bonustalent bewusst *nicht* in `feat_slots.py`s
        `BONUS_FEAT_SLOT_ABILITY_IDS` aufgenommen — die Auswahl ist auf
        metamagische/Gegenstandserschaffungs-/Zaubermeisterschaft-Talente
        beschränkt, kein freier Slot (gleiche Begründung wie bei Waldläufers
        Kampfstiltalent). Für „Arkane Verbindung" (Vertrauter oder Fokus) eine
        neue Options-Gruppe (`arcane_bond`) samt der zwei Wahlmöglichkeiten
        angelegt, analog zur bestehenden `school`-Gruppe. Dabei fiel auf, dass
        die `school`-Options-Gruppe zusätzlich zu den zwei Namensfehlern eine
        ganze Schule **fehlte**: „Beschwörung" war überhaupt nicht als Wahl
        vorhanden (nur 7 der 8 echten Schulen + Universalist) — als achte
        Wahlmöglichkeit ergänzt.
        Alle 26 schulspezifischen Fähigkeiten (8 Schulen × 3 + Universalist ×
        2: Bannzauber/Beschwörung/Erkenntniszauber/Hervorrufung/Illusion/
        Nekromantie/Verwandlung/Verzauberung je „Stufe 1, Stufe 1, Stufe 6
        oder 8", Universalist „Stufe 1, Stufe 8") als `BaseClassAbility`/
        `BaseClassAbilityGrant`-Zeilen ergänzt, jede Grant-Zeile mit
        `option_choice_id` auf die jeweilige Schulwahl verdrahtet — damit
        landen beim Charakterbogen (`sheet.py`s `_build_class_features`, das
        `option_choice_id`-Filtern existierte bereits für Kleriker-Domänen)
        nur die Fähigkeiten der tatsächlich gewählten Schule in
        `classFeatures`, stufenkorrekt gegated. Manuell End-to-End geprüft
        (Hervorrufung-Magier Stufe 8 bekommt genau Starke Zauber/
        Energiegeschoss/Elementarwand, Universalist genau Hand des
        Lehrlings/Metamagische Meisterschaft). Gleiche Tiefe wie überall
        sonst: die Zahlenwerte selbst (Skalierung mit halber Magierstufe,
        Einsatzhäufigkeit „3 + IN-Modifikator" usw.) sind nicht berechnet,
        nur die Fähigkeit samt Beschreibungstext ist vorhanden — jetzt als
        eigener Punkt in `roadmap.md` (Slice 3, „Class-ability computation")
        festgehalten, nicht nur hier erwähnt. Da die
        `option_choice_id`-Grants jetzt eine reale FK auf
        `base_class_option_choices` haben, mussten `test_classes.py` und
        `test_feat_slots.py` (die `seed_class_abilities` bisher ohne
        vorheriges `seed_class_options` aufriefen — bis dahin hatte kein
        Grant `option_choice_id` gesetzt, daher unbemerkt) um den fehlenden
        Seed-Aufruf ergänzt werden.
        `test_character_sheet.py`s
        `test_character_sheet_for_character_without_extras_has_empty_lists`
        nutzte bisher Magier als Beispiel für „keine Klassenmerkmale" — auf
        Barbar umgestellt (einzige verbliebene Klasse ganz ohne
        `BaseClassAbilityGrant`-Daten). **Weiterhin nicht** modelliert: der
        Vertrauten-Regelblock (Tabelle „Besondere Fähigkeiten des
        Vertrauten") und Beschwörer/Kriegsmagier (Magiers zwei Archetypen)
        wurden nicht gegen die Quelle geprüft. Die drei
        `pathfinder-*-mock.html`-Dateien wurden **nicht** synchronisiert
        (gleiches Vorgehen wie beim noch unsynchronisierten Kämpfer→Krieger-
        Rename in den Mocks) — deren `SPELLS_BY_CLASS['Magier']` fehlen
        zusätzlich weiterhin die drei Zaubertricks (Licht, Kleiner Trick,
        Widerstand).
  - [x] **Hexenmeister** (Quelle: <http://prd.5footstep.de/Grundregelwerk/Klassen/Hexenmeister>):
        Trefferwürfel (W6)/GAB (halb)/Rettungswürfe (nur Willen gut)/
        Fertigkeitspunkte (2 + IN)/Zauberattribut (CH)/Zaubertradition (arcane,
        `spellType: spontaneous`) waren bereits korrekt; `base_class_spells*
        .json` hatte bereits echte Zeilen für Stufe 1–6 der „Bekannter
        Zauber"-Tabelle, aber mit einer Lücke (Stufe 6 fehlte Grad 3 = 1) und
        endete dort — auf die volle Tabelle bis Stufe 20 ergänzt (Lücke
        mitkorrigiert). Klassenfertigkeiten waren falsch: „Diplomatie" ist
        laut Quelle **keine** Hexenmeister-Klassenfertigkeit und wurde
        entfernt; es fehlten Beruf, Fliegen, Handwerk und Schätzen (gleiche
        vier wie bei der Magier-Korrektur, wiederverwendet). Die bereits
        vorhandene `bloodline`-Options-Gruppe hatte nur 6 der 10 echten
        Blutlinien, mit Kurz-/Fantasienamen statt der Quellennamen
        („Arkanum"→„Arkane Blutlinie", „Drache"→„Drachenblutlinie",
        „Unheilig"→„Teuflische Blutlinie", „Elementar"→„Elementare
        Blutlinie", „Fey"→„Feenblutlinie", „Abyssisch"→„Dämonische
        Blutlinie"); umbenannt und um die vier fehlenden ergänzt (Abnormale
        Blutlinie, Blutlinie des Grabes, Himmlische Blutlinie, Schicksalhafte
        Blutlinie). Alle Klassenmerkmale, die nicht an eine Blutlinie
        gebunden sind, als reine Katalogzeilen ergänzt (gleiche Tiefe wie bei
        Kämpfer/Waldläufer/Magier, keine Berechnungslogik): Umgang mit Waffen
        und Rüstungen, Blutlinie (Übersicht), Zaubertricks und
        Materialkomponentenlos zaubern (alle Stufe 1), sowie Zauber des
        Blutes (Stufen 3/5/7/9/11/13/15/17/19) und Talent des Blutes (Stufen
        7/13/19) — beides geteilte Katalogzeilen analog zu Kämpfers
        Bonus-Kampftalent, beide bewusst *nicht* in `feat_slots.py`s
        `BONUS_FEAT_SLOT_ABILITY_IDS`, da die Zauber-/Talentwahl auf die
        gewählte Blutlinie beschränkt ist statt ein freier Slot zu sein
        (gleiche Begründung wie Magiers Bonustalent). Für jede der 10
        Blutlinien Geheimnis des Blutes (Stufe 1, ungated bis auf
        `option_choice_id`) plus die 5 nummerierten Macht-des-Blutes-
        Fähigkeiten (Stufen 1/3/9/15/20) als `BaseClassAbility`/
        `BaseClassAbilityGrant`-Zeilen ergänzt, jede Grant-Zeile mit
        `option_choice_id` auf die jeweilige Blutlinienwahl verdrahtet — 66
        neue Katalogzeilen, 76 neue Grants insgesamt. Manuell End-to-End
        geprüft (Drachenblutlinie liefert genau Geheimnis des Blutes/Klauen/
        Drachenresistenz/Odemwaffe/Schwingen/Macht des Drachen, stufenkorrekt
        gegated; `class_bonus_feat_slot_count` bleibt bei 0 für Hexenmeister,
        da weder Zauber des Blutes noch Talent des Blutes als Slot getaggt
        sind). Gleiche Tiefe wie überall sonst: die Zahlenwerte selbst sind
        nicht berechnet, nur Fähigkeit samt Beschreibungstext. **Weiterhin
        nicht** modelliert (kein Schema dafür vorhanden): die pro Blutlinie
        zusätzliche Klassenfertigkeit (z. B. Wissen (Gewölbekunde) für die
        Abnormale Blutlinie) und die pro Blutlinie eigene
        Bonuszauber-/Bonustalente-Liste (welcher konkrete Zauber/welches
        konkrete Talent bei Zauber des Blutes/Talent des Blutes zur Auswahl
        steht) — beides bräuchte entweder ein neues Schema (choice-gated
        Klassenfertigkeit) oder eine FK von Grant auf `base_spells`/
        `base_feats` (choice- und levelgated gleichzeitig), beides über den
        Rahmen dieser Korrektur hinaus. Die Drachenblutlinie-Tabelle
        (Drachentyp → Energietyp/Odem-Form) und die Elementare-Blutlinie-
        Tabelle (Element → Energietyp/Bewegungsart) sind nur als Kurzhinweis
        in der ersten Macht-des-Blutes-Fähigkeit erwähnt, nicht als eigene
        Datenstruktur. Die drei `pathfinder-*-mock.html`-Dateien wurden
        **nicht** synchronisiert (gleiches Vorgehen wie bei Magier); die
        `archetypes`-Liste in `classes.json` (`["Keiner", "Fluchbringer",
        "Blutlinie: Drache"]`) wurde ebenfalls nicht geprüft — sie vermischt
        mutmaßlich echte Archetypen mit einer Blutlinienwahl und gehört auf
        die separate Archetypen-Quellenseite, nicht auf die hier bearbeitete
        Basisklassenseite.
  - [x] **Schurke** (Quelle: <http://prd.5footstep.de/Grundregelwerk/Klassen/Schurke>):
        Trefferwürfel (W8)/GAB (3/4)/Rettungswürfe (nur Reflex gut)/
        Fertigkeitspunkte (8 + IN)/kein Zauberwirker (`spellType: none`)
        waren bereits korrekt. Klassenfertigkeiten waren falsch: „Mit Tieren
        umgehen" ist laut Quelle **keine** Schurken-Klassenfertigkeit und
        wurde entfernt; es fehlten Beruf, Schätzen, Schwimmen und Wissen
        (Gewölbekunde) (ergänzt, alle vier gab es bereits im gemeinsamen
        `base_skills.json`-Katalog). Alle 10 Klassenmerkmale der Quelle als
        `BaseClassAbility`/`BaseClassAbilityGrant`-Zeilen ergänzt, gleiche
        Tiefe wie bei Kämpfer/Waldläufer/Magier/Hexenmeister (keine
        Berechnungslogik, nur Fähigkeit samt Beschreibungstext, aber
        stufenkorrekt gegated und mit der Quelltabelle abgeglichen): Umgang
        mit Waffen und Rüstungen (Stufe 1), Hinterhältiger Angriff (10× auf
        jeder ungeraden Stufe 1–19, wächst um 1W6), Fallen finden (Stufe 1),
        Entrinnen (Stufe 2), Trick (10× auf jeder geraden Stufe 2–20),
        Fallengespür (6× auf Stufe 3/6/9/12/15/18), Reflexbewegung (Stufe 4),
        Verbesserte Reflexbewegung (Stufe 8), Verbesserte Tricks (Stufe 10)
        und Meisterhafter Angriff (Stufe 20) — 33 Grants insgesamt.
        **Weiterhin nicht** modelliert: der eigentliche Trick-Katalog (die
        Quelle listet 15 einfache Tricks wie Blutende Wunde, Höhere/Niedere
        Magie, Kampfkniff, Schurkenfinesse, Waffentraining, Widerstands­
        fähigkeit sowie 8 Verbesserte Tricks wie Ausweichrolle, Bannschlag,
        Fertigkeitsmeisterschaft, Verbessertes Entrinnen) — „Trick"/„Verbesserte
        Tricks" sind nur als Auswahl-Slot hinterlegt, analog zu Kämpfers
        Bonustalent, Waldläufers Kampfstiltalent und Magiers Bonustalent, bei
        denen aus demselben Grund (freie Wahl aus einer eingeschränkten
        Liste statt eines festen Ergebnisses pro Stufe) ebenfalls kein
        Katalog der Wahlmöglichkeiten hinterlegt ist. Anders als bei
        Hexenmeisters Blutlinien (feste, choice-gated Fähigkeitsfolge pro
        Blutlinie) lässt sich das hier nicht ohne ein neues Schema für
        wiederholte freie Talentwahl lösen — größerer Scope als diese
        Korrektur. Die zwei Archetypen (`Meucheldieb`, `Klingentänzer`) in
        `classes.json` wurden nicht gegen eine Quelle geprüft. Die drei
        `pathfinder-*-mock.html`-Dateien wurden **nicht** synchronisiert
        (gleiches Vorgehen wie bei Magier/Hexenmeister).
  - [x] **Nachtrag 2026-08-01: Schurke-Trick-Katalog sowie Kämpfer-/Magier-/
        Hexenmeister-Talentpools nachgeholt.** Der oben als „weiterhin nicht
        modelliert" markierte Trick-Katalog (siehe auch `roadmap.md`s „Pick
        from a restricted list"-Plan) ist jetzt vollständig hinterlegt: alle
        23 Tricks (15 Basis-/8 Verbesserte Tricks) als eigene
        `BaseClassOptionGroup`/`Choice`-Paare (`trick`/`trick_advanced`,
        analog zu Domänen/Blutlinie/Schule, nicht als separates
        Pool-Schema — siehe `roadmap.md` für die Designentscheidung) plus
        `BaseClassAbility`/`Grant`-Zeilen für den Beschreibungstext.
        Kampfkniff/Schurkenfinesse/Waffentraining-Trick sind zusätzlich über
        die neue `BaseClassAbilityFeatOption`-Tabelle an die
        Talent-Kataloge gekoppelt (Kampfkniff: beliebiges Kampftalent;
        Schurkenfinesse/Waffentraining: fest Waffenfinesse/Waffenfokus),
        Höhere/Niedere Magie über `BaseClassAbilitySpellOption` an
        Magier/Hexenmeisters Zaubertrick-/Grad-1-Listen. Gleichzeitig auch
        Kämpfers Bonus-Kampftalent (bisher ungefiltert wählbar trotz
        „nur Kampftalente"-Regel) und Magiers Bonustalent
        (Metamagie/Gegenstandserschaffung/Zaubermeisterschaft) auf dieselbe
        Art verdrahtet. Hexenmeisters Talent des Blutes ebenfalls: die
        ursprüngliche Annahme, dass dafür ~80 neue Talente fehlen, war
        veraltet (Stand vor `build_feats_seed.py`s Erweiterung auf 325
        Talente) — alle 80 Referenzen aus dem bereits vorhandenen
        `hexenmeister_bloodline_bonus_feats.json`-Import lösen sich
        namensbasiert gegen den aktuellen Katalog auf, ohne dass ein
        einziges Talent neu angelegt werden musste. **Weiterhin offen:**
        Waldläufers Kampfstiltalent (keine vorbereitete Quelle wie bei
        Hexenmeister — die stilspezifischen Talentlisten stehen nur als
        Fließtext auf der Waldläufer-Klassenseite, noch nicht abgerufen;
        außerdem fehlt Waldläufer noch eine `combat_style`-Options-Gruppe,
        bisher nur `enemy`/`terrain`); Hexenmeisters tatsächliche
        (deterministische) Zauber-des-Blutes-Zauber pro Blutlinie/Stufe
        (neue Tabelle `BaseClassSpellGrant` existiert, aber ungefüllt —
        die konkrete Zauberzuordnung wurde in keinem bisherigen Import
        erfasst); sowie jegliche Durchsetzung dieser Pools bei
        Charaktererstellung/Stufenaufstieg (die Daten sind vorhanden, aber
        noch von keinem Endpunkt ausgewertet — siehe `roadmap.md` Phasen
        5–6). End-to-end verifiziert, dass ein gewählter Trick ohne jede
        Änderung an `sheet.py` in `classFeatures` auftaucht (genau wie eine
        Domänen-/Blutlinien-/Schulwahl) — bestätigt die Designentscheidung,
        Trick über die bestehende Options-Gruppen-Maschinerie zu
        modellieren statt über ein neues Pool-Schema.
  - [x] **Nachtrag 2026-08-01 (Fortsetzung): Waldläufer-Kampfstiltalent und
        Hexenmeisters echte Zauber des Blutes nachgeholt.** Beide oben als
        offen markierten Lücken sind jetzt geschlossen. Waldläufer
        (Quelle: <http://prd.5footstep.de/Grundregelwerk/Klassen/Waldlaeufer>):
        die Klassenseite listet die vollständige Talentliste beider
        Kampfstile im Fließtext (Bogenschießen: Fernschuss/Kernschuss/
        Präzisionsschuss/Schnelles Schießen, +2 ab Stufe 6, +2 ab Stufe 10;
        Kampf mit zwei Waffen: Doppelschnitt/Kampf mit zwei Waffen/Schnelle
        Waffenbereitschaft/Verbesserter Schildstoß, +2 ab Stufe 6, +2 ab
        Stufe 10) — alle 16 Talente existierten bereits im Katalog, keine
        einzige Neuanlage nötig. Neue `combat_style`-Options-Gruppe
        (`max_choices: 1`) ergänzt, die 16 Talente über
        `BaseClassAbilityFeatOption` an Kampfstiltalent gekoppelt (gated auf
        die jeweilige Stilwahl). **Nicht** modelliert: welche der 8 Talente
        pro Stil ab welcher Stufe wählbar sind (nur 4 vor Stufe 6) — es wird
        die volle Endliste je Stil hinterlegt, gleiche „noch nicht
        durchgesetzt"-Tiefe wie überall sonst hier.

        Hexenmeisters Zauber des Blutes (gleiche Quelle wie Talent des
        Blutes) stammt aus den zehn „Bonuszauber:"-Zeilen je Blutlinie
        (fester Zauber auf Stufe 3/5/7/9/11/13/15/17/19, keine echte Wahl —
        anders als Talent des Blutes daher `BaseClassSpellGrant` statt
        `BaseClassAbilitySpellOption`; Stichprobe Drachenblutlinie gegen die
        echte PF1e-SRD-Progression verifiziert). Von den 81 referenzierten
        Zaubern (80 eindeutige Namen plus Elementarhorde, die im ersten
        Durchgang übersehen und vor dem Seeden nachgetragen wurde) fehlten
        78 im 23-Zauber-Katalog — aufgelöst über den PRD-Bulk-Zauberindex
        (`/cache/prd_datatable__zauber.txt`, gleiches Vorgehen wie
        `import_feats_from_prd.py` für Talente), der Name/Schule/
        Kurzbeschreibung direkt lieferte, keine manuelle Texterstellung
        nötig. Ein Datenfehler in der Quelle gefunden und korrigiert:
        „Zauber zurückwerfen"s Beschreibung fehlt im Index das führende „R"
        („eflektiert…" statt „Reflektiert…"). 72 der 79 neuen Zauber haben
        zusätzlich eine reguläre `BaseClassSpell`-Zeile für Hexenmeister
        erhalten (Grad aus dem Index); die restlichen 7 sind laut Index
        nicht auf der Hexenmeister/Magier-Liste und daher bewusst listenfrei
        (z. B. Himmlische Blutlinie: „Segnen" ist ein Kleriker-Zauber — passt
        zu den echten Regeln für die Himmlische Blutlinie) — nur der
        `BaseClassSpellGrant` existiert für diese. `spell_seed.py` seedet
        die neue Tabelle jetzt mit; Vorbedingung `class_option_seed.py`
        ergänzt (mehrere Bestandstests in `test_characters.py`/`test_spells.py`
        riefen `seed_spells` bisher ohne vorheriges `seed_class_options` auf
        — bis dahin hatte `base_class_spells.json` keine Blutlinien-Gate,
        daher unbemerkt — um den fehlenden Seed-Aufruf ergänzt).
  - [x] **Nachtrag 2026-08-01 (Fortsetzung 2): Waldläufer-Erzfeind/
        Bevorzugtes-Gelände auf wiederholte Wahl umgestellt, Bund des
        Jägers als echte Wahl modelliert, ein Datenfehler aus dem vorigen
        Durchgang korrigiert.** Beim Durchsuchen der bereits importierten
        Klassen nach weiteren „Pick from a restricted list"-Lücken (siehe
        `roadmap.md`) fiel auf: der eigentliche `BaseClassAbilityGrant`-Plan
        für Erzfeind (Stufe 1/5/10/15/20) und Bevorzugtes Gelände (Stufe
        3/8/13/18) war bereits von Anfang an korrekt hinterlegt — nur die
        zugehörigen `BaseClassOptionGroup`-Zeilen (`enemy`/`terrain`) hatten
        noch `max_choices: 1` aus der Zeit, bevor wiederholte Wahlen
        unterstützt wurden. Reine Zahlenkorrektur auf 5/4, keine neuen
        Zeilen nötig (die 32 Feinde/11 Gelände existierten schon vollständig).
        Bund des Jägers (Stufe 4, bisher nur Fließtext mit beiden Zweigen
        in einer Fähigkeitszeile) bekam eine neue `hunter_bond`-Options-Gruppe
        (`max_choices: 1`, Wahlmöglichkeiten „Bund mit Gefährten"/
        „Tiergefährte") und wurde nach demselben Muster wie Hexenmeisters
        Blutlinien-Fähigkeiten aufgeteilt: eine gekürzte, ungegatete
        Übersichtsfähigkeit (immer sichtbar) plus zwei neue
        `option_choice_id`-gegatete Fähigkeitszeilen mit dem jeweiligen
        Zweigtext. Die Tiergefährte-Zweigbeschreibung nennt weiterhin nur
        die feste Tierliste als Fließtext (Dachs, Hund, Kamel, Pferd, Pony,
        kleine Raubkatze, Giftschlange, Würgeschlange, Schreckensratte,
        Vogel, Wolf, Hai) — welches konkrete Tier gewählt wurde, bleibt
        bewusst außerhalb des Scopes (Tiergefährten-Katalog existiert
        nirgends im Schema, eigener, größerer Posten).

        **Dabei gefundener Bug (aus dem vorigen Durchgang, jetzt behoben):**
        die neu angelegte `combat_style`-Options-Gruppe für Waldläufers
        Kampfstiltalent hatte fälschlich Mönchs `base_class_id`
        (`4ed3adcc-…`) statt Waldläufers (`91ab69e8-…`) — eine
        Verwechslung beim Ausfüllen der Konstante im Erzeugungsskript, vom
        ursprünglichen Test nicht bemerkt, da dieser nur nach dem `key`
        filterte statt zusätzlich `base_class_id` zu prüfen. Behoben, und
        der Test um eine `base_class_id`-Prüfung ergänzt (gleiche Ergänzung
        vorsorglich auch bei `enemy`/`hunter_bond`), damit ein ähnlicher
        Fehler künftig auffällt.
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
        | Orakel | 3 |
        | Kleriker | 3 |
        | Barde | 1 |
        | Barbar, Druide, Mönch, Paladin | 0 |

        Zusätzlich schon teilweise real hinterlegt (unabhängig von der
        Testnutzung): Zauber-Tabellen (`base_class_spells*.json`) für Magier/
        Barde/Orakel; Options-Gruppen (Domänen/Mysterien/Bindungen) für
        Druide/Kleriker/Orakel/Waldläufer.

        **Vorschlag für die Reihenfolge:** Kämpfer, Waldläufer, Magier,
        Hexenmeister und Schurke sind erledigt (siehe oben) und decken
        zusammen bereits ~95 % der Testerwähnungen sowie die wichtigsten
        mechanischen Achsen ab (volles GAB mit Bonustalenten, volles GAB als
        Teilzeit-Zauberwirker divine-spontan, halbes GAB arkan-vorbereitet,
        halbes GAB arkan-spontan, 3/4 GAB fertigkeitsbasiert ohne Zauber).
        Als Nächstes Kleriker (einzige vorbereitete Divine-Klasse mit
        Domänen), um die Abdeckung abzurunden, ohne eine bereits abgedeckte
        Mechanik zu duplizieren. Barbar/Druide/Mönch/Paladin haben aktuell
        keine Testabdeckung und sind — analog zu Zwerg/Gnom/Halbelf bei den
        Rassen — gute Kandidaten, um sie beim nächsten Aufräumdurchgang als
        ungeprüftes Platzhaltermaterial zu entfernen, statt sie einzeln zu
        verifizieren.
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
