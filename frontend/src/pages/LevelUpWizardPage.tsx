import { useEffect, useState, type Dispatch, type SetStateAction } from 'react';
import { Link, useParams } from 'react-router-dom';
import { apiGet, apiPost } from '../api/client';
import { createId } from '../lib/id';
import { useCharacterProgression } from '../hooks/useCharacterProgression';
import { useLevelUpOptions } from '../hooks/useLevelUpOptions';
import { levelUpRequestBody } from '../lib/levelUpSubmission';
import type { CharacterProgression } from '../types/characterProgression';
import type { LevelUpDraft } from '../types/levelUpDraft';
import { Panel } from '../components/primitives/Panel';
import { Stepper, type StepDef } from '../components/primitives/Stepper';
import { CharContextBanner } from '../components/levelup/CharContextBanner';
import { ClassLevelStep } from '../components/levelup/ClassLevelStep';
import { ClassChoiceStep } from '../components/levelup/ClassChoiceStep';
import { HitPointsStep } from '../components/levelup/HitPointsStep';
import { AbilityIncreaseStep } from '../components/levelup/AbilityIncreaseStep';
import { LevelSkillsStep } from '../components/levelup/LevelSkillsStep';
import { LevelFeatStep } from '../components/levelup/LevelFeatStep';
import { LevelSpellStep } from '../components/levelup/LevelSpellStep';
import { LevelUpSummaryStep } from '../components/levelup/LevelUpSummaryStep';
import './LevelUpWizardPage.css';

const STEPS: StepDef[] = [
  { key: 'classLevel', label: 'Klassenstufe' },
  { key: 'classChoice', label: 'Klassenwahl' },
  { key: 'hitPoints', label: 'Trefferpunkte' },
  { key: 'ability', label: 'Attribut' },
  { key: 'skills', label: 'Fertigkeiten' },
  { key: 'feat', label: 'Talente' },
  { key: 'spell', label: 'Zauber' },
  { key: 'summary', label: 'Zusammenfassung' },
];

// A companion's "level-up" fills in its lowest open HD (roadmap slice 10 step 3): no class
// choice, no spells; HP only while that HD has none yet.
const COMPANION_STEP_KEYS = new Set(['hitPoints', 'ability', 'skills', 'feat', 'summary']);

type SubmitState = 'idle' | 'submitting' | 'success' | 'error';

function emptyDraft(progression: CharacterProgression): LevelUpDraft {
  return {
    target: { mode: 'existing', classId: progression.classes[0].id },
    hitPoints: null,
    favoredClassBonus: null,
    existingLevelOptionSelections: {},
    abilityIncrease: null,
    skillIncreases: {},
    skillSpecializationIncreases: (progression.skillRankDetails ?? []).map((detail) => ({
      localId: createId(),
      skillId: detail.skillId,
      specializationId: detail.specializationId,
      customSpecialization: detail.customSpecialization,
      newRanks: 0,
    })),
    newFeat: null,
    newBonusFeat: null,
    featSubChoices: {},
    featSubChoices2: {},
    newSpells: [],
  };
}

export function LevelUpWizardPage() {
  const { characterId = '1' } = useParams();
  const { progression: fetchedProgression, loading: progressionLoading, error: progressionError } =
    useCharacterProgression(characterId);
  const [optionsReloadKey, setOptionsReloadKey] = useState(0);
  const { options, loading: optionsLoading, error: optionsError } = useLevelUpOptions(characterId, optionsReloadKey);
  const [draft, setDraft] = useState<LevelUpDraft | null>(null);
  const [stepIndex, setStepIndex] = useState(0);
  const [submitState, setSubmitState] = useState<SubmitState>('idle');
  const [submitErrorMessage, setSubmitErrorMessage] = useState('');
  // Re-fetched after a successful POST .../level-up so the summary step shows
  // the real, server-computed level/history instead of the pre-submit draft.
  const [confirmedProgression, setConfirmedProgression] = useState<CharacterProgression | null>(null);
  const progression = confirmedProgression ?? fetchedProgression;

  // Whether this HD asks for HP — fixed when the draft starts, so the step list doesn't shift
  // under the summary once the saved HD no longer reports its HP as open.
  const [askHitPoints, setAskHitPoints] = useState(true);
  useEffect(() => {
    if (progression && !draft) {
      setDraft(emptyDraft(progression));
      setAskHitPoints(!progression.companion || progression.companion.hitPointsOpen);
    }
  }, [progression, draft]);

  if (progressionLoading || optionsLoading || !draft) {
    return (
      <div className="app">
        <p style={{ color: '#e2d3ab', padding: 24 }}>Lade Stufenaufstieg …</p>
      </div>
    );
  }

  if (progressionError || optionsError || !progression || !options) {
    return (
      <div className="app">
        <p style={{ color: '#e2d3ab', padding: 24 }}>
          Charakter konnte nicht geladen werden: {progressionError || optionsError}
        </p>
      </div>
    );
  }

  const prog = progression;
  const companion = prog.companion;
  // The companion's pseudo class isn't on `/api/classes` — the progression carries it.
  const opts = companion ? { ...options, classes: [...options.classes, companion.classDef] } : options;
  const currentDraft = draft;
  const steps = companion
    ? STEPS.filter((s) => COMPANION_STEP_KEYS.has(s.key) && (s.key !== 'hitPoints' || askHitPoints))
    : STEPS;
  const sheetLink = '/';

  if (companion && companion.openHitDie === null && submitState !== 'success') {
    return (
      <div className="app">
        <p style={{ color: '#e2d3ab', padding: 24 }}>
          {prog.name} hat keine offenen Trefferwürfel. Neue TW kommen mit dem Stufenaufstieg des Meisters.{' '}
          <Link to={sheetLink}>Zurück zum Charakterbogen</Link>
        </p>
      </div>
    );
  }

  const setLevelUpDraft: Dispatch<SetStateAction<LevelUpDraft>> = (value) => {
    setDraft((prev) => {
      if (!prev) return prev;
      return typeof value === 'function' ? (value as (p: LevelUpDraft) => LevelUpDraft)(prev) : value;
    });
  };

  function goToStep(n: number) {
    if (n < 0 || n > steps.length - 1) return;
    setStepIndex(n);
  }

  /** After completing one open HD, start on the next one. */
  async function continueWithNextHitDie() {
    const refreshed = await apiGet<CharacterProgression>(`/api/characters/${characterId}/progression`);
    setConfirmedProgression(refreshed);
    setDraft(emptyDraft(refreshed));
    setAskHitPoints(!refreshed.companion || refreshed.companion.hitPointsOpen);
    setOptionsReloadKey((key) => key + 1);
    setStepIndex(0);
    setSubmitState('idle');
  }

  async function nextStep() {
    if (stepIndex === steps.length - 1) {
      if (submitState === 'success' || submitState === 'submitting') return;
      if (currentDraft.hitPoints === null && askHitPoints) {
        setSubmitState('error');
        setSubmitErrorMessage('Bitte im Schritt „Trefferpunkte" einen Wert eintragen.');
        return;
      }
      const target = currentDraft.target;
      const targetIsFavored =
        target.mode === 'existing' && (prog.classes.find((c) => c.id === target.classId)?.isFavored ?? false);
      if (targetIsFavored && currentDraft.favoredClassBonus === null) {
        setSubmitState('error');
        setSubmitErrorMessage('Bitte im Schritt „Trefferpunkte" den Bonus der bevorzugten Klasse wählen.');
        return;
      }
      setSubmitState('submitting');
      try {
        await apiPost(`/api/characters/${characterId}/level-up`, levelUpRequestBody(prog, opts, currentDraft));
        const refreshed = await apiGet<CharacterProgression>(`/api/characters/${characterId}/progression`);
        setConfirmedProgression(refreshed);
        setSubmitState('success');
      } catch {
        setSubmitState('error');
        setSubmitErrorMessage('Stufenaufstieg konnte nicht gespeichert werden.');
      }
      return;
    }
    goToStep(stepIndex + 1);
  }

  function renderStep() {
    switch (steps[stepIndex].key) {
      case 'classLevel':
        return <ClassLevelStep progression={prog} options={opts} draft={currentDraft} setDraft={setLevelUpDraft} />;
      case 'classChoice':
        return <ClassChoiceStep progression={prog} options={opts} draft={currentDraft} setDraft={setLevelUpDraft} />;
      case 'hitPoints':
        return <HitPointsStep progression={prog} options={opts} draft={currentDraft} setDraft={setLevelUpDraft} />;
      case 'ability':
        return <AbilityIncreaseStep progression={prog} options={opts} draft={currentDraft} setDraft={setLevelUpDraft} />;
      case 'skills':
        return <LevelSkillsStep progression={prog} options={opts} draft={currentDraft} setDraft={setLevelUpDraft} />;
      case 'feat':
        return <LevelFeatStep progression={prog} options={opts} draft={currentDraft} setDraft={setLevelUpDraft} />;
      case 'spell':
        return <LevelSpellStep progression={prog} options={opts} draft={currentDraft} setDraft={setLevelUpDraft} />;
      case 'summary':
        return (
          <LevelUpSummaryStep
            progression={prog}
            options={opts}
            draft={currentDraft}
            showConfirmBanner={submitState === 'success'}
          />
        );
      default:
        return null;
    }
  }

  return (
    <div className="app">
      <header>
        <div className="brand">
          <div className="sigil">P</div>
          <div>
            <div className="title">GEFÄHRTENBUCH</div>
            <span className="subtitle">
              {companion ? `Gefährte: TW ${companion.openHitDie ?? prog.classes[0].level} ausfüllen` : 'Stufenaufstieg'}
            </span>
          </div>
        </div>
        <div className="spacer" />
        <Link className="btn-outline" to={sheetLink}>← Zurück zum Charakterbogen</Link>
      </header>

      <div className="wizard-wrap">
        <div className="wizard">
          <CharContextBanner progression={prog} />

          <Stepper steps={steps} activeIndex={stepIndex} onSelect={goToStep} />

          <Panel title={steps[stepIndex].label} hint={`Schritt ${stepIndex + 1} von ${steps.length}`}>
            {renderStep()}
          </Panel>

          {submitState === 'error' && <p className="warning-note">{submitErrorMessage}</p>}
          {companion && submitState === 'success' && companion.openHitDie !== null && (
            <p className="info-note">
              Noch {companion.openHitDice} offene{companion.openHitDice === 1 ? 'r' : ''} TW.{' '}
              <button type="button" className="companion-link" onClick={continueWithNextHitDie}>
                Nächsten TW ausfüllen →
              </button>
            </p>
          )}

          <div className="wizard-nav">
            <button type="button" className="btn-nav prev" disabled={stepIndex === 0} onClick={() => goToStep(stepIndex - 1)}>
              ← Zurück
            </button>
            <button
              type="button"
              className="btn-nav next"
              onClick={nextStep}
              disabled={stepIndex === steps.length - 1 && submitState === 'submitting'}
            >
              {stepIndex === steps.length - 1
                ? submitState === 'submitting'
                  ? 'Speichert …'
                  : companion
                    ? 'TW übernehmen ✦'
                    : 'Stufenaufstieg übernehmen ✦'
                : 'Weiter →'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
