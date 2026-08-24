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

function DescribedList({ entries, idPrefix }: { entries: DescribedEntry[]; idPrefix: string }) {
  return (
    <>
      {entries.map((entry) => (
        <div className="trait-item" id={`${idPrefix}-${entry.key}`} key={entry.key}>
          <div className="name">
            {entry.name}
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
}

export function SheetTabs({ character, activeTab, onTabChange, onCastSpell }: SheetTabsProps) {
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
          </div>
          {character.spellsKnown.map((grade) => {
            const preparedTotal = grade.spells.reduce((sum, s) => sum + s.preparedCount, 0);
            const usedTotal = grade.spells.reduce((sum, s) => sum + s.usedCount, 0);
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
                  ) : (
                    <>
                      <div className="stat"><span className="stat-label">Vorbereitet</span><span className="stat-val">{preparedTotal}</span></div>
                      <div className="stat"><span className="stat-label">Frei</span><span className="stat-val">{preparedTotal - usedTotal}</span></div>
                      <div className="stat"><span className="stat-label">Gewirkt</span><span className="stat-val">{usedTotal}</span></div>
                    </>
                  )}
                </div>
                {!grade.locked && (
                  <div className="chip-row spellprep">
                    {grade.spells.map((spell) => {
                      const remaining = spell.preparedCount - spell.usedCount;
                      return (
                        <button
                          key={spell.key}
                          type="button"
                          disabled={remaining <= 0}
                          className={`chip${remaining <= 0 ? ' used' : ''}`}
                          onClick={() => onCastSpell(grade.grade, spell)}
                        >
                          {spell.name} ({remaining}/{spell.preparedCount})
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
