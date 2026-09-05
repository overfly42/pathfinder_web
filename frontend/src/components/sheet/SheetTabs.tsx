import { formatBreakdown } from '../../lib/breakdown';
import type { Character, DescribedEntry, PreparedSpellRef } from '../../types/character';
import { InfoButton } from '../primitives/InfoButton';
import { TabBar, TabPanel, type TabDef } from '../primitives/Tabs';

const TABS: TabDef[] = [
  { key: 'skills', label: 'Fertigkeiten' },
  { key: 'feats', label: 'Talente' },
  { key: 'traits', label: 'Wesenszüge' },
  { key: 'classfeatures', label: 'Klassenfähigkeiten' },
  { key: 'raceabilities', label: 'Rasseneigenschaften' },
  { key: 'spells', label: 'Zauber' },
];

/** Marks an entry whose mechanical effect isn't computed anywhere on the sheet yet (no
 *  `HANDLERS` entry on the backend) — the player has to remember/apply it themselves at the
 *  table. Absent entirely once a handler exists, so it never claims "definitely flavor-only"
 *  for something that just hasn't been implemented yet. */
function NoHandlerBadge({ title }: { title: string }) {
  return (
    <span className="no-handler-badge" title={title}>
      Nur Text
    </span>
  );
}

/** Marks a `classFeatures` entry granted by the "Sekundärklasse" alternate rule
 *  (`entry.isSecondary`) rather than a real class level — see `DescribedEntry`'s
 *  own docstring. */
function SecondaryClassBadge() {
  return (
    <span
      className="secondary-class-badge"
      title="Merkmal der gewählten Sekundärklasse, nicht einer echten Klassenstufe."
    >
      Sekundärklasse
    </span>
  );
}

function DescribedList({ entries, idPrefix }: { entries: DescribedEntry[]; idPrefix: string }) {
  return (
    <>
      {entries.map((entry) => (
        <div className="trait-item" id={`${idPrefix}-${entry.key}`} key={entry.key}>
          <div className="name">
            {entry.name}
            {entry.isSecondary && <SecondaryClassBadge />}
            {!entry.hasHandler && (
              <NoHandlerBadge title="Wird noch nicht automatisch berechnet — Wirkung selbst am Tisch anwenden." />
            )}
          </div>
          <div className="desc">{entry.description}</div>
        </div>
      ))}
    </>
  );
}

interface SheetTabsProps {
  character: Character;
  activeTab: string;
  onTabChange: (tab: string) => void;
  onCastSpell: (grade: number, spell: PreparedSpellRef) => void;
  onRestoreSpell: (grade: number, spell: PreparedSpellRef) => void;
}

export function SheetTabs({ character, activeTab, onTabChange, onCastSpell, onRestoreSpell }: SheetTabsProps) {
  const hasPearls = character.spellsKnown.some((grade) => (grade.pearlsTotal ?? 0) > 0);
  return (
    <>
      <div className="section-label">Fertigkeiten &amp; Fähigkeiten</div>
      <div className="tabset">
        <TabBar tabs={TABS} active={activeTab} onChange={onTabChange} />

        <TabPanel active={activeTab} tabKey="skills">
          {character.skills.map((skill) => {
            const breakdownText = formatBreakdown(skill.breakdown);
            const infoContent =
              [skill.note, breakdownText].filter(Boolean).join('\n\n') ||
              'Keine weiteren Informationen verfügbar.';
            return (
              <div className="skill-row" id={`skill-${skill.key}`} key={skill.key}>
                <span>
                  {skill.label}
                  <InfoButton label={skill.label} content={infoContent} />
                </span>
                <span className="val">{skill.value}</span>
              </div>
            );
          })}
        </TabPanel>

        <TabPanel active={activeTab} tabKey="feats">
          <DescribedList entries={character.feats} idPrefix="feat" />
        </TabPanel>

        <TabPanel active={activeTab} tabKey="traits">
          <DescribedList entries={character.traits} idPrefix="trait" />
        </TabPanel>

        <TabPanel active={activeTab} tabKey="classfeatures">
          <DescribedList entries={character.classFeatures} idPrefix="classfeature" />
          {character.favoredClassBonuses && character.favoredClassBonuses.length > 0 && (
            <>
              <div className="section-label" style={{ marginTop: 14 }}>
                Bevorzugte Klasse
              </div>
              {character.favoredClassBonuses.map((entry) => (
                <div className="trait-item" id={`favoredclassbonus-${entry.key}`} key={entry.key}>
                  <div className="name">
                    {entry.name}
                    {' — '}
                    {entry.currentBonus !== null
                      ? `${entry.pickCount}× gewählt, aktueller Bonus: +${entry.currentBonus}`
                      : `${entry.pickCount}× gewählt`}
                    {!entry.hasHandler && (
                      <NoHandlerBadge title="Kein einzelner berechneter Bonus — Wirkung der Beschreibung entnehmen." />
                    )}
                  </div>
                  <div className="desc">{entry.description}</div>
                </div>
              ))}
            </>
          )}
        </TabPanel>

        <TabPanel active={activeTab} tabKey="raceabilities">
          <DescribedList entries={character.raceAbilities} idPrefix="raceability" />
        </TabPanel>

        <TabPanel active={activeTab} tabKey="spells">
          <div className="spell-hint">
            Vorbereitete Zauber des Tages · zum Wirken anklicken. Auswahl der Vorbereitung erfolgt im Zauberbuch (Ausrüstung).
            {hasPearls && (
              <>
                {' '}Bereits gewirkte Zauber mit verfügbarer Perle der Macht (hervorgehoben) erneut antippen, um sie
                zurückzurufen.
              </>
            )}
          </div>
          {character.spellsKnown.map((grade) => {
            const preparedTotal = grade.spells.reduce((sum, s) => sum + s.preparedCount, 0);
            const usedTotal = grade.spells.reduce((sum, s) => sum + s.usedCount, 0);
            const isSpontaneous = grade.slotsAvailable != null;
            return (
              <div className="spell-tab-block" key={grade.grade}>
                <div className={`spell-table-row${grade.locked ? ' locked' : ''}`}>
                  <span className="grade">Grad {grade.grade}</span>
                  {grade.locked ? (
                    <>
                      <div className="stat"><span className="stat-label">Vorbereitet</span><span className="stat-val">—</span></div>
                      <div className="stat"><span className="stat-label">Frei</span><span className="stat-val">—</span></div>
                      <div className="stat"><span className="stat-label">Verfügbar ab</span><span className="stat-val">Stufe {grade.availableAtLevel}</span></div>
                    </>
                  ) : isSpontaneous ? (
                    <>
                      <div className="stat"><span className="stat-label">Bekannt</span><span className="stat-val">{grade.spells.length}</span></div>
                      <div className="stat"><span className="stat-label">Zauberplätze frei</span><span className="stat-val">{grade.slotsAvailable}/{grade.perDay}</span></div>
                      <div className="stat"><span className="stat-label">Gewirkt heute</span><span className="stat-val">{(grade.perDay ?? 0) - (grade.slotsAvailable ?? 0)}</span></div>
                    </>
                  ) : (
                    <>
                      <div className="stat"><span className="stat-label">Vorbereitet</span><span className="stat-val">{preparedTotal}</span></div>
                      <div className="stat"><span className="stat-label">Frei</span><span className="stat-val">{preparedTotal - usedTotal}</span></div>
                      <div className="stat"><span className="stat-label">Gewirkt</span><span className="stat-val">{usedTotal}</span></div>
                    </>
                  )}
                </div>
                {!grade.locked && grade.pearlsTotal != null && (
                  <div className="pearl-counter">
                    ⚬ Perle der Macht: {grade.pearlsAvailable}/{grade.pearlsTotal} heute
                  </div>
                )}
                {!grade.locked && (
                  <div className="chip-row spellprep">
                    {grade.spells.map((spell) => {
                      const remaining = spell.preparedCount - spell.usedCount;
                      const canRestore = remaining <= 0 && (grade.pearlsAvailable ?? 0) > 0;
                      return (
                        <button
                          key={spell.key}
                          type="button"
                          disabled={remaining <= 0 && !canRestore}
                          className={`chip${remaining <= 0 ? ' used' : ''}${canRestore ? ' restorable' : ''}`}
                          title={canRestore ? 'Mit einer Perle der Macht erneut vorbereiten' : undefined}
                          onClick={() => {
                            if (remaining > 0) onCastSpell(grade.grade, spell);
                            else if (canRestore) onRestoreSpell(grade.grade, spell);
                          }}
                        >
                          {isSpontaneous ? spell.name : `${spell.name} (${remaining}/${spell.preparedCount})`}
                        </button>
                      );
                    })}
                  </div>
                )}
              </div>
            );
          })}
        </TabPanel>
      </div>
    </>
  );
}
