import type { Character, DescribedEntry } from '../../types/character';
import { TabBar, TabPanel, type TabDef } from '../primitives/Tabs';

const TABS: TabDef[] = [
  { key: 'skills', label: 'Fertigkeiten' },
  { key: 'feats', label: 'Talente' },
  { key: 'traits', label: 'Wesenszüge' },
  { key: 'classfeatures', label: 'Klassenfähigkeiten' },
  { key: 'raceabilities', label: 'Rasseneigenschaften' },
  { key: 'spells', label: 'Zauber' },
];

function DescribedList({ entries, idPrefix }: { entries: DescribedEntry[]; idPrefix: string }) {
  return (
    <>
      {entries.map((entry) => (
        <div className="trait-item" id={`${idPrefix}-${entry.key}`} key={entry.key}>
          <div className="name">{entry.name}</div>
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
  onToggleSpellCast: (grade: number, spellKey: string) => void;
}

export function SheetTabs({ character, activeTab, onTabChange, onToggleSpellCast }: SheetTabsProps) {
  return (
    <>
      <div className="section-label">Fertigkeiten &amp; Fähigkeiten</div>
      <div className="tabset">
        <TabBar tabs={TABS} active={activeTab} onChange={onTabChange} />

        <TabPanel active={activeTab} tabKey="skills">
          {character.skills.map((skill) => (
            <div className="skill-row" id={`skill-${skill.key}`} key={skill.key}>
              <span>{skill.label}</span>
              <span className="val">{skill.value}</span>
            </div>
          ))}
        </TabPanel>

        <TabPanel active={activeTab} tabKey="feats">
          <DescribedList entries={character.feats} idPrefix="feat" />
        </TabPanel>

        <TabPanel active={activeTab} tabKey="traits">
          <DescribedList entries={character.traits} idPrefix="trait" />
        </TabPanel>

        <TabPanel active={activeTab} tabKey="classfeatures">
          <DescribedList entries={character.classFeatures} idPrefix="classfeature" />
        </TabPanel>

        <TabPanel active={activeTab} tabKey="raceabilities">
          <DescribedList entries={character.raceAbilities} idPrefix="raceability" />
        </TabPanel>

        <TabPanel active={activeTab} tabKey="spells">
          <div className="spell-hint">
            Vorbereitete Zauber des Tages · zum Wirken anklicken. Auswahl der Vorbereitung erfolgt im Zauberbuch (Ausrüstung).
          </div>
          {character.spellsKnown.map((grade) => (
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
                    <div className="stat"><span className="stat-label">Vorbereitet</span><span className="stat-val">{grade.prepared}</span></div>
                    <div className="stat"><span className="stat-label">Frei</span><span className="stat-val">{grade.spells.filter((s) => !s.used).length}</span></div>
                    <div className="stat"><span className="stat-label">Gewirkt</span><span className="stat-val">{grade.spells.filter((s) => s.used).length}</span></div>
                  </>
                )}
              </div>
              {!grade.locked && (
                <div className="chip-row spellprep">
                  {grade.spells.map((spell) => (
                    <button
                      key={spell.key}
                      type="button"
                      className={`chip${spell.used ? ' used' : ''}`}
                      onClick={() => onToggleSpellCast(grade.grade, spell.key)}
                    >
                      {spell.name}
                    </button>
                  ))}
                </div>
              )}
            </div>
          ))}
        </TabPanel>
      </div>
    </>
  );
}
