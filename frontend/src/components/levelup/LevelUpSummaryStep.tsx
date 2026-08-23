import type { CharacterProgression } from '../../types/characterProgression';
import type { LevelUpDraft } from '../../types/levelUpDraft';
import type { LevelUpOptions } from '../../types/levelUpOptions';
import {
  abilityIncreaseGrantedThisLevel,
  classBonusFeatGrantedThisLevel,
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
      const archetypeLabel = c.archetypes.length ? c.archetypes.join(', ') : 'Keiner';
      classLine = `${c.className} (${archetypeLabel}): Stufe ${c.level} → ${info.level}`;
      for (const g of options.classLevelOptions[info.className] ?? []) {
        if (!g.levels.includes(info.level)) continue;
        const chosen = draft.existingLevelOptionSelections[g.key] ?? [];
        if (chosen.length) optLines.push(`${g.label}: ${chosen.join(', ')}`);
      }
    }
  } else {
    const archetypeLabel = target.archetypes.length ? target.archetypes.join(', ') : 'Keiner';
    classLine = `${target.className} (neu, ${archetypeLabel}): Stufe 1`;
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

  const bonusFeatGranted = classBonusFeatGrantedThisLevel(className, info?.level ?? null, options.classes);
  const sumBonusFeat = bonusFeatGranted ? draft.newBonusFeat || '— noch nicht gewählt —' : null;

  const skillLines = options.skills.filter((s) => (draft.skillIncreases[s.id] || 0) > 0);
  const specializationLines = draft.skillSpecializationIncreases.filter((e) => e.newRanks > 0);
  const skillById = new Map(options.skills.map((s) => [s.id, s]));
  const specializationNameById = new Map(options.skillSpecializations.map((s) => [s.id, s.name]));

  const isFavored =
    target.mode === 'existing' && (progression.classes.find((c) => c.id === target.classId)?.isFavored ?? false);
  const sumFavoredBonus = isFavored
    ? draft.favoredClassBonus === 'hp'
      ? '+1 Trefferpunkt'
      : draft.favoredClassBonus === 'skill'
        ? '+1 Fertigkeitsrang'
        : (draft.favoredClassBonus ?? '— noch nicht gewählt —')
    : null;
  // Only the race+class-specific alternates need their rules text spelled
  // out here — "hp"/"skill" are already self-explanatory via sumFavoredBonus
  // above, and have no entry in favoredClassBonusDescriptions anyway.
  const sumFavoredBonusDescription =
    draft.favoredClassBonus && draft.favoredClassBonus !== 'hp' && draft.favoredClassBonus !== 'skill'
      ? progression.favoredClassBonusDescriptions?.[draft.favoredClassBonus]
      : undefined;

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

        {bonusFeatGranted && (
          <div className="summary-block">
            <div className="sb-title">Bonus-Kampftalent ({className})</div>
            <div className="sb-line"><span>{sumBonusFeat}</span></div>
          </div>
        )}

        {isFavored && (
          <div className="summary-block">
            <div className="sb-title">Bevorzugte Klasse</div>
            <div className="sb-line"><span>{sumFavoredBonus}</span></div>
            {sumFavoredBonusDescription && <div className="desc">{sumFavoredBonusDescription}</div>}
          </div>
        )}

        <div className="summary-block summary-full">
          <div className="sb-title">Neue Fertigkeitsränge</div>
          {skillLines.length === 0 && specializationLines.length === 0 ? (
            <div className="sb-line"><span>Keine neuen Ränge vergeben.</span></div>
          ) : (
            <>
              {skillLines.map((s) => (
                <div className="sb-line" key={s.id}>
                  <span>{s.name}</span>
                  <span className="val">+{draft.skillIncreases[s.id]} Rang{draft.skillIncreases[s.id] > 1 ? 'e' : ''}</span>
                </div>
              ))}
              {specializationLines.map((entry) => {
                const skill = skillById.get(entry.skillId);
                if (!skill) return null;
                const label = entry.specializationId
                  ? specializationNameById.get(entry.specializationId) ?? '?'
                  : entry.customSpecialization || '…';
                return (
                  <div className="sb-line" key={entry.localId}>
                    <span>{skill.name} ({label})</span>
                    <span className="val">+{entry.newRanks} Rang{entry.newRanks > 1 ? 'e' : ''}</span>
                  </div>
                );
              })}
            </>
          )}
        </div>

        <div className="summary-block summary-full">
          <div className="sb-title">Neue Zauber</div>
          <div className="sb-line"><span>{sumSpell}</span></div>
        </div>
      </div>

      {progression.history.length > 0 && (
        <div className="summary-block summary-full" style={{ marginTop: 16 }}>
          <div className="sb-title">Bisherige Historie</div>
          {progression.history.map((entry) => (
            <div className="sb-line" key={entry.id}><span>{entry.description}</span><span className="val">{entry.date}</span></div>
          ))}
        </div>
      )}

      <div className="info-note" style={{ marginTop: 16 }}>
        Dieser Stufenaufstieg wird zusammen mit dem vorherigen Stand in der Charakterhistorie festgehalten.
      </div>
      {showConfirmBanner && (
        <div className="confirm-banner">✦ Stufenaufstieg wurde übernommen und in der Historie vermerkt.</div>
      )}
    </>
  );
}
