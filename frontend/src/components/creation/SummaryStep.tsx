import type { CreationDraft } from '../../types/creationDraft';
import type { CreationOptions } from '../../types/creationOptions';
import {
  abilityMod,
  classDef,
  formatMod,
  formatPrice,
  genderLabel,
  gearTotalValue,
  selectedRace,
  skillBonus,
  totalAbility,
  totalLevel,
} from '../../lib/creationCalculations';

type SubmitState = 'idle' | 'submitting' | 'success' | 'error';

interface SummaryStepProps {
  draft: CreationDraft;
  options: CreationOptions;
  submitState: SubmitState;
  submitErrorMessage: string;
}

export function SummaryStep({ draft, options, submitState, submitErrorMessage }: SummaryStepProps) {
  const race = selectedRace(draft, options);
  const level = totalLevel(draft);
  const gearValue = gearTotalValue(draft.gear);

  const skillLines = options.skills.filter((s) => (draft.skillRanks[s.id] || 0) > 0);
  const featNameById = new Map(options.feats.map((f) => [f.id, f.name]));

  const optionLines: { label: string; value: string }[] = [];
  for (const row of draft.classRows) {
    const cls = classDef(options, row.className);
    for (const group of cls?.optionGroups ?? []) {
      const chosen = row.options[group.key] ?? [];
      if (chosen.length) {
        optionLines.push({ label: `${row.className} — ${group.label.replace(/\s*\(.*\)/, '')}`, value: chosen.join(', ') });
      }
    }
  }

  const spellLines = Object.entries(draft.spellSelections).filter(([, spells]) => spells.length > 0);

  return (
    <>
      <div className="summary-grid">
        <div className="summary-block">
          <div className="sb-title">Grunddaten</div>
          <div className="sb-line"><span>Name</span><span className="val">{draft.name.trim() || '—'}</span></div>
          <div className="sb-line"><span>Geschlecht</span><span className="val">{genderLabel(draft.gender)}</span></div>
          <div className="sb-line"><span>Rasse</span><span className="val">{race ? race.name : '—'}</span></div>
          <div className="sb-line">
            <span>Rassenbonus-Attribut</span>
            <span className="val">
              {race && race.flex
                ? draft.flexAbility
                  ? options.abilities.find((a) => a.key === draft.flexAbility)?.name ?? draft.flexAbility
                  : '— noch nicht gewählt —'
                : race
                  ? '– (feste Werte)'
                  : '—'}
            </span>
          </div>
          <div className="sb-line"><span>Alt. Volksmerkmale</span><span className="val">{draft.altTraits.length ? draft.altTraits.join(', ') : 'Keine'}</span></div>
          <div className="sb-line"><span>Charakterstufe</span><span className="val">{level}</span></div>
        </div>

        <div className="summary-block">
          <div className="sb-title">Klassen</div>
          {draft.classRows.length === 0 ? (
            <div className="sb-line"><span>—</span></div>
          ) : (
            draft.classRows.map((row) => (
              <div className="sb-line" key={row.id}>
                <span>{row.className}{row.archetypes.length ? ` (${row.archetypes.join(', ')})` : ''}</span>
                <span className="val">Stufe {row.level}</span>
              </div>
            ))
          )}
        </div>

        <div className="summary-block">
          <div className="sb-title">Attribute</div>
          {options.abilities.map((a) => {
            const total = totalAbility(draft, options, a.key);
            return (
              <div className="sb-line" key={a.key}>
                <span>{a.name}</span>
                <span className="val">{total} ({formatMod(abilityMod(total))})</span>
              </div>
            );
          })}
        </div>

        <div className="summary-block">
          <div className="sb-title">Ausrüstung</div>
          <div className="sb-line"><span>Startgold</span><span className="val">{draft.gold} GM</span></div>
          <div className="sb-line"><span>Gegenstände</span><span className="val">{draft.gear.length}</span></div>
          <div className="sb-line"><span>Inventarwert</span><span className="val">{formatPrice(gearValue)}</span></div>
        </div>

        <div className="summary-block summary-full">
          <div className="sb-title">Fertigkeiten</div>
          {skillLines.length === 0 ? (
            <div className="sb-line"><span>Keine Fertigkeitsränge vergeben.</span></div>
          ) : (
            skillLines.map((s) => {
              const ranks = draft.skillRanks[s.id] || 0;
              const bonus = skillBonus(draft, options, s.id, s.ability);
              return (
                <div className="sb-line" key={s.id}>
                  <span>{s.name} ({ranks} Rang)</span>
                  <span className="val">{formatMod(bonus)}</span>
                </div>
              );
            })
          )}
        </div>

        <div className="summary-block summary-full">
          <div className="sb-title">Talente</div>
          <div className="summary-chips">
            {draft.feats.length === 0 ? (
              <span className="selected-empty">Keine Talente gewählt.</span>
            ) : (
              draft.feats.map((id) => <span className="chip active" key={id}>{featNameById.get(id) ?? id}</span>)
            )}
          </div>
        </div>

        <div className="summary-block summary-full">
          <div className="sb-title">Wesenszüge</div>
          <div className="summary-chips">
            {draft.traits.length === 0 ? (
              <span className="selected-empty">Keine Wesenszüge gewählt.</span>
            ) : (
              draft.traits.map((t) => <span className="chip active" key={t}>{t}</span>)
            )}
          </div>
        </div>

        <div className="summary-block summary-full">
          <div className="sb-title">Klassenoptionen</div>
          {optionLines.length === 0 ? (
            <div className="sb-line"><span>Keine Zusatzoptionen.</span></div>
          ) : (
            optionLines.map((line, i) => (
              <div className="sb-line" key={i}><span>{line.label}</span><span className="val">{line.value}</span></div>
            ))
          )}
        </div>

        <div className="summary-block summary-full">
          <div className="sb-title">Zauber</div>
          {spellLines.length === 0 ? (
            <div className="sb-line"><span>Keine Zauber ausgewählt.</span></div>
          ) : (
            spellLines.map(([className, spells]) => (
              <div className="sb-line" key={className}><span>{className}</span><span className="val">{spells.join(', ')}</span></div>
            ))
          )}
        </div>
      </div>

      {submitState === 'success' && (
        <div className="confirm-banner">✦ Charakter wurde erstellt und gespeichert.</div>
      )}
      {submitState === 'error' && (
        <div className="confirm-banner confirm-banner-error">{submitErrorMessage}</div>
      )}
    </>
  );
}
