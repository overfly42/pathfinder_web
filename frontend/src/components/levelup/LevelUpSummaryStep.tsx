import type { CharacterProgression } from '../../types/characterProgression';
import type { LevelUpDraft } from '../../types/levelUpDraft';
import type { LevelUpOptions } from '../../types/levelUpOptions';
import {
  abilityIncreaseGrantedThisLevel,
  featGrantedThisLevel,
  getNewLevel,
  getOldTotalLevel,
  getReceivingClassAndLevel,
  getReceivingClassName,
} from '../../lib/levelUpCalculations';

interface LevelUpSummaryStepProps {
  progression: CharacterProgression;
  options: LevelUpOptions;
  draft: LevelUpDraft;
  showConfirmBanner: boolean;
}

export function LevelUpSummaryStep({ progression, options, draft, showConfirmBanner }: LevelUpSummaryStepProps) {
  const oldLevel = getOldTotalLevel(progression);
  const newLevel = getNewLevel(progression);
  const info = getReceivingClassAndLevel(progression, draft.target);
  const className = getReceivingClassName(progression, draft.target);
  const target = draft.target;

  let classLine = '—';
  const optLines: string[] = [];

  if (target.mode === 'existing') {
    const c = progression.classes.find((x) => x.id === target.classId);
    if (c && info) {
      classLine = `${c.className} (${c.archetype}): Stufe ${c.level} → ${info.level}`;
      for (const g of options.classLevelOptions[info.className] ?? []) {
        if (!g.levels.includes(info.level)) continue;
        const chosen = draft.existingLevelOptionSelections[g.key] ?? [];
        if (chosen.length) optLines.push(`${g.label}: ${chosen.join(', ')}`);
      }
    }
  } else {
    classLine = `${target.className} (neu, ${target.archetype}): Stufe 1`;
    for (const [key, values] of Object.entries(target.options)) {
      if (values.length) optLines.push(`${key}: ${values.join(', ')}`);
    }
  }
  const classLineFull = classLine + (optLines.length ? ` — ${optLines.join(' · ')}` : '');

  const abilityIncreaseGranted = abilityIncreaseGrantedThisLevel(newLevel);
  const sumAbility = abilityIncreaseGranted
    ? draft.abilityIncrease
      ? (() => {
          const name = options.abilities.find((a) => a.key === draft.abilityIncrease)?.name ?? draft.abilityIncrease;
          const cur = progression.abilityScores[draft.abilityIncrease];
          return `${name} ${cur} → ${cur + 1}`;
        })()
      : '— noch nicht gewählt —'
    : 'Keine (nicht Stufe 4/8/12/16/20).';

  const featGranted = featGrantedThisLevel(newLevel);
  const sumFeat = featGranted ? draft.newFeat || '— noch nicht gewählt —' : 'Keins auf dieser Stufe.';

  const skillLines = options.skills.filter((s) => draft.skillIncreases[s.key]);

  const classDef = className ? options.classes.find((c) => c.name === className) : undefined;
  const spellType = classDef?.spellType ?? 'none';
  const sumSpell =
    spellType === 'arcane-prepared' || spellType === 'spontaneous'
      ? draft.newSpell || '— noch nicht gewählt —'
      : 'Keine Änderung nötig.';

  return (
    <>
      <div className="summary-grid">
        <div className="summary-block summary-full">
          <div className="sb-title">Klassenstufe</div>
          <div className="sb-line"><span>{classLineFull}</span><span className="val">{oldLevel} → {newLevel}</span></div>
        </div>

        <div className="summary-block">
          <div className="sb-title">Attributssteigerung</div>
          <div className="sb-line"><span>{sumAbility}</span></div>
        </div>

        <div className="summary-block">
          <div className="sb-title">Neues Talent</div>
          <div className="sb-line"><span>{sumFeat}</span></div>
        </div>

        <div className="summary-block summary-full">
          <div className="sb-title">Neue Fertigkeitsränge</div>
          {skillLines.length === 0 ? (
            <div className="sb-line"><span>Keine neuen Ränge vergeben.</span></div>
          ) : (
            skillLines.map((s) => (
              <div className="sb-line" key={s.key}><span>{s.name}</span><span className="val">+1 Rang</span></div>
            ))
          )}
        </div>

        <div className="summary-block summary-full">
          <div className="sb-title">Neue Zauber</div>
          <div className="sb-line"><span>{sumSpell}</span></div>
        </div>
      </div>

      <div className="info-note" style={{ marginTop: 16 }}>
        Dieser Stufenaufstieg wird zusammen mit dem vorherigen Stand in der Charakterhistorie festgehalten.
      </div>
      {showConfirmBanner && (
        <div className="confirm-banner">✦ Stufenaufstieg wurde (im Mock) übernommen und in der Historie vermerkt.</div>
      )}
    </>
  );
}
