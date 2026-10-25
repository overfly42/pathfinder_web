import { Fragment, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { useAppState } from '../state/AppStateContext';
import { useCharacter } from '../hooks/useCharacter';
import { formatBreakdown } from '../lib/breakdown';
import { formatSpellComponents } from '../lib/spellComponents';
import { gearLine } from '../lib/gearSummary';
import { exportCharacterPdf } from '../lib/exportCharacterPdf';
import { alignmentLabel } from '../lib/alignment';
import { companionLevelName, formatCompanionBreakdown } from '../lib/companionLevels';
import type { Character, DescribedEntry, StatEntry } from '../types/character';
import './CharacterPrintPage.css';

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="print-section">
      <h2>{title}</h2>
      {children}
    </section>
  );
}

function StatBoxes({ entries }: { entries: StatEntry[] }) {
  return (
    <div className="print-stats">
      {entries.map((entry) => (
        <div className="print-stat" key={entry.key}>
          <span className="label">{entry.label}</span>
          <span className="value">{entry.value}</span>
        </div>
      ))}
    </div>
  );
}

function Described({ entries }: { entries: DescribedEntry[] }) {
  if (entries.length === 0) return <p className="print-empty">—</p>;
  return (
    <>
      {entries.map((entry) => (
        <div className="print-entry" key={entry.key}>
          <strong>{entry.name}</strong>
          {entry.isSecondary && ' (Sekundärklasse)'}
          {entry.summary && <> [{entry.summary}]</>}
          {entry.description && <> — {entry.description}</>}
        </div>
      ))}
    </>
  );
}

function PrintableSheet({ character }: { character: Character }) {
  const { language } = useAppState();
  const hp = character.hp;
  const movement = [
    `Land ${character.speed}`,
    character.climbSpeed && `Klettern ${character.climbSpeed}`,
    character.swimSpeed && `Schwimmen ${character.swimSpeed}`,
    character.burrowSpeed && `Graben ${character.burrowSpeed}`,
    character.flySpeed && `Fliegen ${character.flySpeed}${character.flyManeuverability ? ` (${character.flyManeuverability})` : ''}`,
  ].filter(Boolean);
  // Spellbook entries (full text, independent of today's preparation) are the spell list; casters
  // without a spellbook (divine/spontaneous) fall back to their known spells.
  const bookGrades = character.spellbook.filter((g) => !g.locked && g.spells.length > 0);
  const usesSpellbook = bookGrades.length > 0;
  const spellGrades = usesSpellbook ? bookGrades : character.spellsKnown.filter((g) => !g.locked && g.spells.length > 0);

  return (
    <div className="print-sheet">
      <header className="print-header">
        <h1>{character.name}</h1>
        <p>
          {character.race} · {character.className}
          {character.archetype ? ` (${character.archetype})` : ''} · Stufe {character.level}
          {character.alignment ? ` · ${alignmentLabel(character.alignment)}` : ''}
        </p>
      </header>

      <div className="print-vitals">
        <div><span className="label">TP</span><span className="value">{hp.current}/{hp.max}{hp.temporary > 0 ? ` (+${hp.temporary} temp.)` : ''}</span></div>
        <div><span className="label">RK</span><span className="value">{character.armorClass}</span></div>
        <div><span className="label">Auf dem falschen Fuß</span><span className="value">{character.armorClassFlatFooted}</span></div>
        <div><span className="label">Initiative</span><span className="value">{character.initiative}</span></div>
        <div className="wide"><span className="label">Bewegung</span><span className="value">{movement.join(' · ')}</span></div>
      </div>
      {character.armorClassBreakdown && character.armorClassBreakdown.length > 0 && (
        <p className="print-note">RK: {formatBreakdown(character.armorClassBreakdown)?.replace(/\n/g, ', ')}</p>
      )}

      {character.armorClassFlatFootedBreakdown && character.armorClassFlatFootedBreakdown.length > 0 && (
        <p className="print-note">Auf dem falschen Fuß: {formatBreakdown(character.armorClassFlatFootedBreakdown)?.replace(/\n/g, ', ')}</p>
      )}

      <Section title="Attribute">
        <div className="print-abilities">
          {character.abilities.map((a) => (
            <div className="print-ability" key={a.key}>
              <span className="label">{a.label}</span>
              <span className="value">{a.score}</span>
              <span className="mod">{a.mod}</span>
              {a.damage > 0 && <span className="dmg">-{a.damage} Schaden</span>}
              {a.breakdown && a.breakdown.length > 0 && (
                <span className="bd">{formatBreakdown(a.breakdown)?.replace(/\n/g, ', ')}</span>
              )}
            </div>
          ))}
        </div>
      </Section>

      <div className="print-cols-2">
        <Section title="Rettungswürfe"><StatBoxes entries={character.saves} /></Section>
        <Section title="Kampfwerte"><StatBoxes entries={character.combat} /></Section>
      </div>

      {character.weaponAttacks.length > 0 && (
        <Section title="Waffen">
          <table className="print-table">
            <thead><tr><th>Waffe</th><th>Hand</th><th>Angriff</th><th>Schaden</th></tr></thead>
            <tbody>
              {character.weaponAttacks.map((w) => (
                <tr key={w.key}><td>{w.name}</td><td>{w.hand}</td><td>{w.attackBonus}</td><td>{w.damage}</td></tr>
              ))}
            </tbody>
          </table>
        </Section>
      )}

      <Section title="Fertigkeiten">
        <table className="print-table">
          <thead><tr><th>Fertigkeit</th><th>Wert</th><th>Zusammensetzung / Hinweis</th></tr></thead>
          <tbody>
            {character.skills.map((s) => (
              <tr key={s.key}>
                <td>{s.label}</td>
                <td>{s.value}</td>
                <td>{[formatBreakdown(s.breakdown)?.replace(/\n/g, ', '), s.note].filter(Boolean).join(' · ')}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </Section>

      <Section title="Talente"><Described entries={character.feats} /></Section>
      <Section title="Wesenszüge"><Described entries={character.traits} /></Section>
      <Section title="Klassenfähigkeiten">
        <Described entries={character.classFeatures} />
        {character.companionLevels?.map((entry) => (
          <div className="print-entry" key={entry.track}>
            <strong>{entry.label}</strong> — {companionLevelName(entry.track)}{' '}
            {entry.level}: {formatCompanionBreakdown(entry)}
          </div>
        ))}
        {character.favoredClassBonuses && character.favoredClassBonuses.length > 0 && (
          <>
            <h3>Bevorzugte Klasse</h3>
            {character.favoredClassBonuses.map((b) => (
              <div className="print-entry" key={b.key}>
                <strong>{b.name}</strong> — {b.pickCount}× gewählt
                {b.currentBonus !== null ? `, aktueller Bonus: +${b.currentBonus}` : ''}
                {b.description && <> — {b.description}</>}
              </div>
            ))}
          </>
        )}
      </Section>
      <Section title="Rasseneigenschaften"><Described entries={character.raceAbilities} /></Section>
      {character.companion?.trickLimits && (
        <Section title="Tricks">
          <p className="print-entry">
            Bonustricks {character.companion.trickLimits.bonus.used}/{character.companion.trickLimits.bonus.max} ·
            Abgerichtet {character.companion.trickLimits.trained.used}/
            {character.companion.trickLimits.trained.max ?? 'unbegrenzt'}
            {character.companion.trickPurpose && <> · Aufgabe: {character.companion.trickPurpose.name}</>}
          </p>
          {character.companion.tricks.map((t) => (
            <div className="print-entry" key={t.id}>
              <strong>{t.name}</strong> (SG {t.dc}, {t.source === 'bonus' ? 'Bonus' : 'abgerichtet'}
              {t.purposeName ? `, ${t.purposeName}` : ''}) — {t.description}
            </div>
          ))}
        </Section>
      )}

      {(spellGrades.length > 0 || character.activatableSpells.length > 0) && (
        <Section title={usesSpellbook ? 'Zauberbuch' : 'Zauber'}>
          {character.activatableSpells.length > 0 && (
            <p className="print-entry"><strong>Jederzeit wirkbar:</strong> {character.activatableSpells.map((s) => s.name).join(', ')}</p>
          )}
          {spellGrades.map((grade) => (
            <div className="print-spell-grade" key={`${grade.baseClassId ?? ''}-${grade.grade}`}>
              <h3>
                Grad {grade.grade}
                {grade.dc != null && ` · SG ${grade.dc}`}
                {grade.perDay != null && ` · ${grade.perDay} pro Tag`}
              </h3>
              <table className="print-table print-spell-table">
                <colgroup>
                  {[15, 12, 9, 12, 11, 15, 13, 7, 6].map((w, i) => <col key={i} style={{ width: `${w}%` }} />)}
                </colgroup>
                <thead>
                  <tr>
                    <th>Zauber</th><th>Schule</th><th>Zeit</th><th>Komponenten</th>
                    <th>Reichweite</th><th>Ziel/Gebiet</th><th>Dauer</th><th>RW</th><th>ZR</th>
                  </tr>
                </thead>
                <tbody>
                  {grade.spells.map((s) => (
                    <Fragment key={s.key}>
                      <tr className="spell-main">
                        <td>{s.name}</td>
                        <td>{s.school ?? '—'}</td>
                        <td>{s.castingTime ?? '—'}</td>
                        <td>{formatSpellComponents(s.components, language)}</td>
                        <td>{s.range ?? '—'}</td>
                        <td>{s.target ?? '—'}</td>
                        <td>{s.duration ?? '—'}</td>
                        <td>{s.savingThrow ?? '—'}</td>
                        <td>{s.spellResistance ?? '—'}</td>
                      </tr>
                      {s.description && <tr className="spell-desc"><td colSpan={9}>{s.description}</td></tr>}
                    </Fragment>
                  ))}
                </tbody>
              </table>
            </div>
          ))}
        </Section>
      )}

      <Section title="Ausrüstung">
        {character.equipmentSlots.length > 0 && (
          <>
            <h3>Ausrüstungsplätze</h3>
            <table className="print-table">
              <thead><tr><th>Platz</th><th>Angelegt</th></tr></thead>
              <tbody>
                {character.equipmentSlots.map((slot) => (
                  <tr key={slot.key}>
                    <td>{slot.label}</td>
                    <td>{slot.options.find((o) => o.value === slot.selected)?.label ?? (slot.selected || '—')}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            <h3>Inventar</h3>
          </>
        )}
        {character.gear.length === 0 ? (
          <p className="print-empty">—</p>
        ) : (
          <table className="print-table">
            <thead><tr><th>Anz.</th><th>Gegenstand</th><th>Details</th></tr></thead>
            <tbody>
              {character.gear.map((item) => (
                <tr key={item.id}><td>{item.qty}</td><td>{item.name}</td><td>{gearLine(item)}</td></tr>
              ))}
            </tbody>
          </table>
        )}
        {character.wands && character.wands.length > 0 && (
          <>
            <h3>Zauberstäbe</h3>
            <table className="print-table">
              <thead><tr><th>Zauber</th><th>Grad</th><th>ZS</th><th>Ladungen</th></tr></thead>
              <tbody>
                {character.wands.map((w) => (
                  <tr key={w.id}><td>{w.spellName}</td><td>{w.spellGrade}</td><td>{w.casterLevel}</td><td>{w.chargesRemaining}/{w.maxCharges}</td></tr>
                ))}
              </tbody>
            </table>
          </>
        )}
      </Section>

    </div>
  );
}

export function CharacterPrintPage() {
  const { currentCharacterId, currentUserId, language } = useAppState();
  const { character, loading, error } = useCharacter(currentCharacterId);

  useEffect(() => {
    if (character) document.title = `${character.name} — Charakterbogen`;
  }, [character]);

  return (
    <div className="print-page">
      <div className="print-toolbar">
        <Link to={`/?${currentUserId ? `user=${currentUserId}&` : ''}character=${currentCharacterId}`}>← Zurück</Link>
        <span>
          <button type="button" onClick={() => character && exportCharacterPdf(character, language)} disabled={!character}>
            Als PDF speichern
          </button>{' '}
          <button type="button" onClick={() => window.print()} disabled={!character}>Drucken</button>
        </span>
      </div>
      {loading && <p>Lade Charakter …</p>}
      {!loading && (error || !character) && <p>Charakter konnte nicht geladen werden{error ? `: ${error}` : '.'}</p>}
      {character && <PrintableSheet character={character} />}
    </div>
  );
}
