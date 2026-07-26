import type { PreparableSpellGrade } from '../../types/character';

interface SpellbookProps {
  grades: PreparableSpellGrade[];
  onTogglePrepare: (grade: number, spellKey: string) => void;
}

export function Spellbook({ grades, onTogglePrepare }: SpellbookProps) {
  return (
    <>
      <div className="spell-hint">
        Waldläuferzauber · göttlich, vorbereitend aus der vollen Klassenliste (kein Zauberbuch nötig). Auswahl gilt bis
        zur nächsten Vorbereitung (z. B. nach Rast).
      </div>
      {grades.map((grade) => {
        const preparedCount = grade.spells.filter((s) => s.prepared).length;
        return (
          <div className="spell-tab-block" key={grade.grade}>
            <div className={`spell-table-row${grade.locked ? ' locked' : ''}`}>
              <span className="grade">Grad {grade.grade}</span>
              {grade.locked ? (
                <>
                  <div className="stat"><span className="stat-label">Pro Tag</span><span className="stat-val">—</span></div>
                  <div className="stat"><span className="stat-label">Verfügbar ab</span><span className="stat-val">Stufe {grade.availableAtLevel}</span></div>
                  <div className="stat" />
                </>
              ) : (
                <>
                  <div className="stat"><span className="stat-label">Pro Tag</span><span className="stat-val">{grade.perDay}</span></div>
                  <div className="stat"><span className="stat-label">Vorbereitet</span><span className="stat-val">{preparedCount} / {grade.maxPrepared}</span></div>
                  <div className="stat" />
                </>
              )}
            </div>
            {!grade.locked && (
              <div className="chip-row spellprep">
                {grade.spells.map((spell) => (
                  <button
                    key={spell.key}
                    type="button"
                    className={`chip${spell.prepared ? ' active' : ''}`}
                    onClick={() => onTogglePrepare(grade.grade, spell.key)}
                  >
                    {spell.name}
                  </button>
                ))}
              </div>
            )}
          </div>
        );
      })}
    </>
  );
}
