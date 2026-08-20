import { useEffect, useState, type Dispatch, type SetStateAction } from 'react';
import { Link, useParams } from 'react-router-dom';
import { apiGet, apiPost } from '../api/client';
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

type SubmitState = 'idle' | 'submitting' | 'success' | 'error';

export function LevelUpWizardPage() {
  const { characterId = '1' } = useParams();
  const { progression: fetchedProgression, loading: progressionLoading, error: progressionError } =
    useCharacterProgression(characterId);
  const { options, loading: optionsLoading, error: optionsError } = useLevelUpOptions(characterId);
  const [draft, setDraft] = useState<LevelUpDraft | null>(null);
  const [stepIndex, setStepIndex] = useState(0);
  const [submitState, setSubmitState] = useState<SubmitState>('idle');
  const [submitErrorMessage, setSubmitErrorMessage] = useState('');
  // Re-fetched after a successful POST .../level-up so the summary step shows
  // the real, server-computed level/history instead of the pre-submit draft.
  const [confirmedProgression, setConfirmedProgression] = useState<CharacterProgression | null>(null);
  const progression = confirmedProgression ?? fetchedProgression;

  useEffect(() => {
    if (progression && !draft) {
      setDraft({
        target: { mode: 'existing', classId: progression.classes[0].id },
        hitPoints: null,
        favoredClassBonus: null,
        existingLevelOptionSelections: {},
        abilityIncrease: null,
        skillIncreases: {},
        newFeat: null,
        newBonusFeat: null,
        featSubChoices: {},
        newSpell: null,
      });
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
  const opts = options;
  const currentDraft = draft;

  const setLevelUpDraft: Dispatch<SetStateAction<LevelUpDraft>> = (value) => {
    setDraft((prev) => {
      if (!prev) return prev;
      return typeof value === 'function' ? (value as (p: LevelUpDraft) => LevelUpDraft)(prev) : value;
    });
  };

  function goToStep(n: number) {
    if (n < 0 || n > STEPS.length - 1) return;
    setStepIndex(n);
  }

  async function nextStep() {
    if (stepIndex === STEPS.length - 1) {
      if (submitState === 'success' || submitState === 'submitting') return;
      if (currentDraft.hitPoints === null) {
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
    switch (STEPS[stepIndex].key) {
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
            <span className="subtitle">Stufenaufstieg</span>
          </div>
        </div>
        <div className="spacer" />
        <Link className="btn-outline" to="/">← Zurück zum Charakterbogen</Link>
      </header>

      <div className="wizard-wrap">
        <div className="wizard">
          <CharContextBanner progression={prog} />

          <Stepper steps={STEPS} activeIndex={stepIndex} onSelect={goToStep} />

          <Panel title={STEPS[stepIndex].label} hint={`Schritt ${stepIndex + 1} von ${STEPS.length}`}>
            {renderStep()}
          </Panel>

          {submitState === 'error' && <p className="warning-note">{submitErrorMessage}</p>}

          <div className="wizard-nav">
            <button type="button" className="btn-nav prev" disabled={stepIndex === 0} onClick={() => goToStep(stepIndex - 1)}>
              ← Zurück
            </button>
            <button
              type="button"
              className="btn-nav next"
              onClick={nextStep}
              disabled={stepIndex === STEPS.length - 1 && submitState === 'submitting'}
            >
              {stepIndex === STEPS.length - 1
                ? submitState === 'submitting'
                  ? 'Speichert …'
                  : 'Stufenaufstieg übernehmen ✦'
                : 'Weiter →'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
