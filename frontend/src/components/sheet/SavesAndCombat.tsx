import type { StatEntry } from '../../types/character';

function StatGrid({ entries }: { entries: StatEntry[] }) {
  return (
    <div className="saves">
      {entries.map((entry) => (
        <div className="save" key={entry.key}>
          <span className="name">{entry.label}</span>
          <span className="val">{entry.value}</span>
        </div>
      ))}
    </div>
  );
}

export function SavesAndCombat({ saves, combat }: { saves: StatEntry[]; combat: StatEntry[] }) {
  return (
    <>
      <div className="section-label">Rettungswürfe</div>
      <StatGrid entries={saves} />

      <div className="section-label">Kampfwerte</div>
      <StatGrid entries={combat} />
    </>
  );
}
