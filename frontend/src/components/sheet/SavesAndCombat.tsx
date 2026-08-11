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
          <StatGrid
            entries={weaponAttacks.map((weapon) => ({
              key: weapon.key,
              label: `${weapon.name} (${weapon.hand})`,
              value: `Angriff ${weapon.attackBonus} · Schaden ${weapon.damage}`,
            }))}
          />
        </>
      )}
    </>
  );
}
