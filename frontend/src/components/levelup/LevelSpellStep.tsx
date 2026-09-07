import type { Dispatch, SetStateAction } from 'react';
import type { CharacterProgression } from '../../types/characterProgression';
import type { LevelUpDraft } from '../../types/levelUpDraft';
import type { LevelUpOptions } from '../../types/levelUpOptions';
import {
  abilityMod,
  arcanePreparedBudget,
  bonusCapGrade,
  bonusKnownSpellSlot,
  effectiveCastingAbility,
  spellGradeBudgetAtLevel,
  spontaneousBonusOverflowUsed,
} from '../../lib/creationCalculations';
import {
  effectiveAbilityTotal,
  getReceivingClassAndLevel,
  getReceivingClassName,
  receivingArchetypeNames,
} from '../../lib/levelUpCalculations';

interface LevelSpellStepProps {
  progression: CharacterProgression;
  options: LevelUpOptions;
  draft: LevelUpDraft;
  setDraft: Dispatch<SetStateAction<LevelUpDraft>>;
}

export function LevelSpellStep({ progression, options, draft, setDraft }: LevelSpellStepProps) {
  const className = getReceivingClassName(progression, draft.target);
  const classDef = className ? options.classes.find((c) => c.name === className) : undefined;
  const type = classDef?.spellType ?? 'none';

  if (!classDef || (type !== 'arcane-prepared' && type !== 'spontaneous')) {
    const note =
      type === 'divine-prepared'
        ? 'Diese Klasse bereitet Zauber frei aus der vollen Klassen-Zauberliste vor — hier ist keine Auswahl nötig.'
        : 'Diese Klasse hat keine Zauberfähigkeit.';
    return <div className="selected-empty">{note}</div>;
  }

  const receiving = getReceivingClassAndLevel(progression, draft.target);
  const newLevel = receiving?.level ?? 1;
  // Grade cap straight from the class table at the level this level-up
  // reaches (cumulative, not a delta — same shape creation's SpellsStep
  // already reads) — `null` values (arcane-prepared) just mark a grade as
  // accessible, the real cap there is `arcanePreparedBudget` below.
  const gradeBudget = spellGradeBudgetAtLevel(classDef, newLevel);
  const alreadyKnownNames = new Set((className && progression.spellsKnown[className]) || []);
  const classSpells = (className && options.spellsByClass[className]) || [];
  // This one level-up's own favored-class-bonus pick (not a career total,
  // see rules/spells.py's bonus_known_spell_slot) grants Mystiker/Hexe one
  // extra known-spell slot, usable on any grade at or below capGrade.
  const bonusAvailable = className && bonusKnownSpellSlot(className, draft.favoredClassBonus) ? 1 : 0;
  const capGrade = bonusCapGrade(gradeBudget);

  function toggle(name: string, canAdd: (selected: string[]) => boolean) {
    setDraft((prev) => {
      const selected = prev.newSpells;
      let next: string[];
      if (selected.includes(name)) next = selected.filter((n) => n !== name);
      else if (canAdd(selected)) next = [...selected, name];
      else next = selected;
      return { ...prev, newSpells: next };
    });
  }

  if (type === 'arcane-prepared') {
    const castingAbility = effectiveCastingAbility(classDef, receivingArchetypeNames(progression, draft.target));
    const mod = castingAbility
      ? abilityMod(effectiveAbilityTotal(progression, castingAbility, draft.abilityIncrease))
      : 0;
    // `arcanePreparedBudget` is cumulative (total spellbook picks by this
    // level) — this level-up's own remaining share is that total minus
    // what's already known, not the raw class-table value itself. A
    // favored-class-bonus pick (Hexe's "Zusätzlicher Hexenvertraut-Zauber")
    // adds exactly one more slot on top, but only usable on a spell at or
    // below capGrade — see rules/spells.py's arcane_prepared_overflows_budget.
    const alreadyKnownNonGrade0 = classSpells.filter((s) => s.grade !== 0 && alreadyKnownNames.has(s.name)).length;
    const normalRemaining = Math.max(0, arcanePreparedBudget(newLevel, mod) - alreadyKnownNonGrade0);
    const remainingBudget = normalRemaining + bonusAvailable;
    const selectable = classSpells.filter(
      (s) => s.grade !== 0 && String(s.grade) in gradeBudget && !alreadyKnownNames.has(s.name),
    );
    const picked = draft.newSpells.length;

    return (
      <div className="summary-block">
        <div className="sb-title">{className} — Zauberbuch (arkan, vorbereitend) — neue Zauber diese Stufe</div>
        <div className="pick-counter" style={{ marginBottom: 10 }}>
          Ausgewählt: <b>{picked}</b> / <b>{remainingBudget}</b>
        </div>
        {bonusAvailable > 0 && (
          <div className="pick-counter" style={{ marginBottom: 10 }}>
            + Bevorzugte-Klasse-Bonus: 1 zusätzlicher Zauber, Grad ≤ {capGrade}
          </div>
        )}
        <div className="chip-row">
          {selectable.map((spell) => {
            const active = draft.newSpells.includes(spell.name);
            // The next pick past normalRemaining is the bonus-covered one —
            // only legal at or below capGrade.
            const wouldUseBonus = !active && picked >= normalRemaining;
            const disabled = !active && (picked >= remainingBudget || (wouldUseBonus && spell.grade > capGrade));
            return (
              <button
                key={spell.id}
                type="button"
                className={`chip${active ? ' active' : ''}${disabled ? ' disabled' : ''}`}
                onClick={disabled ? undefined : () => toggle(spell.name, (sel) => sel.length < remainingBudget)}
              >
                Grad {spell.grade}: {spell.name}
              </button>
            );
          })}
        </div>
      </div>
    );
  }

  // spontaneous: separate cap per grade, this level-up's own remaining
  // share of each grade's cumulative class-table cap, plus a shared
  // bonus-spell pool (favored-class-bonus pick) any grade at or below
  // capGrade can draw on — see rules/spells.py's spontaneous_grade_overflow.
  const grades = Object.keys(gradeBudget).map(Number).sort((a, b) => a - b);
  const alreadyKnownByGrade: Record<number, number> = {};
  const pickedByGrade: Record<number, number> = {};
  for (const grade of grades) {
    alreadyKnownByGrade[grade] = classSpells.filter((s) => s.grade === grade && alreadyKnownNames.has(s.name)).length;
    const gradeSpellNames = new Set(classSpells.filter((s) => s.grade === grade).map((s) => s.name));
    pickedByGrade[grade] = draft.newSpells.filter((name) => gradeSpellNames.has(name)).length;
  }
  const bonusUsed = spontaneousBonusOverflowUsed(gradeBudget, alreadyKnownByGrade, pickedByGrade, capGrade);
  const bonusRemaining = Math.max(0, bonusAvailable - bonusUsed);

  return (
    <div className="summary-block">
      <div className="sb-title">{className} — Bekannte Zauber (spontan) — neue Zauber diese Stufe</div>
      {bonusAvailable > 0 && (
        <div className="pick-counter" style={{ marginBottom: 10 }}>
          + Bevorzugte-Klasse-Bonus: {bonusRemaining > 0 ? '1 zusätzlicher Zauber verfügbar' : 'bereits verwendet'}, Grad ≤ {capGrade}
        </div>
      )}
      {grades.map((grade) => {
        const alreadyAtGrade = alreadyKnownByGrade[grade];
        const normalRemaining = Math.max(0, (gradeBudget[String(grade)] ?? 0) - alreadyAtGrade);
        const overflowHere = grade <= capGrade ? Math.max(0, pickedByGrade[grade] - normalRemaining) : 0;
        const remainingCap = normalRemaining + (grade <= capGrade ? overflowHere + bonusRemaining : 0);
        const gradeSpells = classSpells.filter((s) => s.grade === grade && !alreadyKnownNames.has(s.name));
        const gradeSelected = draft.newSpells.filter((name) => gradeSpells.some((s) => s.name === name));
        return (
          <div key={grade} style={{ marginBottom: 10 }}>
            <div className="pick-counter" style={{ marginBottom: 6 }}>
              Grad {grade}: <b>{gradeSelected.length}</b> / <b>{remainingCap}</b>
            </div>
            <div className="chip-row">
              {gradeSpells.map((spell) => {
                const active = draft.newSpells.includes(spell.name);
                const disabled = !active && gradeSelected.length >= remainingCap;
                return (
                  <button
                    key={spell.id}
                    type="button"
                    className={`chip${active ? ' active' : ''}${disabled ? ' disabled' : ''}`}
                    onClick={
                      disabled
                        ? undefined
                        : () =>
                            toggle(
                              spell.name,
                              (sel) => sel.filter((name) => gradeSpells.some((s) => s.name === name)).length < remainingCap,
                            )
                    }
                  >
                    {spell.name}
                  </button>
                );
              })}
            </div>
          </div>
        );
      })}
    </div>
  );
}
