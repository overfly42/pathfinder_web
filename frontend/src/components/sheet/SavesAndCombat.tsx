import type { StatEntry, WeaponAttack } from '../../types/character';

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

export function SavesAndCombat({
  saves,
  combat,
  weaponAttacks,
}: {
  saves: StatEntry[];
  combat: StatEntry[];
  weaponAttacks: WeaponAttack[];
}) {
  return (
    <>
      <div className="section-label">Rettungswürfe</div>
      <StatGrid entries={saves} />

      <div className="section-label">Kampfwerte</div>
      <StatGrid entries={combat} />

      {weaponAttacks.length > 0 && (
        <>
          <div className="section-label">Waffen</div>
          <div className="saves">
            {weaponAttacks.map((weapon) => (
              <div className="save" key={weapon.key}>
                <span className="name">
                  {weapon.name} ({weapon.hand})
                  {weapon.note && (
                    <span className="skill-note" title={weapon.note} aria-label={weapon.note}>
                      ⓘ
                    </span>
                  )}
                </span>
                <span className="val">
                  Angriff {weapon.attackBonus} · Schaden {weapon.damage}
                </span>
              </div>
            ))}
          </div>
        </>
      )}
    </>
  );
}
