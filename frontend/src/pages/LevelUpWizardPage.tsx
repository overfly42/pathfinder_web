import { useEffect, useState, type Dispatch, type SetStateAction } from 'react';
import { Link, useParams } from 'react-router-dom';
import { useAppState } from '../state/AppStateContext';
import { useCharacterProgression } from '../hooks/useCharacterProgression';
import { useLevelUpOptions } from '../hooks/useLevelUpOptions';
import { applyLevelUp } from '../lib/applyLevelUp';
import type { LevelUpDraft } from '../types/levelUpDraft';
import { Panel } from '../components/primitives/Panel';
import { Stepper, type StepDef } from '../components/primitives/Stepper';
import { CharContextBanner } from '../components/levelup/CharContextBanner';
import { ClassLevelStep } from '../components/levelup/ClassLevelStep';
import { ClassChoiceStep } from '../components/levelup/ClassChoiceStep';
import { AbilityIncreaseStep } from '../components/levelup/AbilityIncreaseStep';
import { LevelSkillsStep } from '../components/levelup/LevelSkillsStep';
import { LevelFeatStep } from '../components/levelup/LevelFeatStep';
import { LevelSpellStep } from '../components/levelup/LevelSpellStep';
import { LevelUpSummaryStep } from '../components/levelup/LevelUpSummaryStep';
import './LevelUpWizardPage.css';

const STEPS: StepDef[] = [
  { key: 'classLevel', label: 'Klassenstufe' },
  { key: 'classChoice', label: 'Klassenwahl' },
  { key: 'ability', label: 'Attribut' },
  { key: 'skills', label: 'Fertigkeiten' },
  { key: 'feat', label: 'Talente' },
  { key: 'spell', label: 'Zauber' },
  { key: 'summary', label: 'Zusammenfassung' },
];

export function LevelUpWizardPage() {
  const { characterId = '1' } = useParams();
  const { getProgressionOverride, setProgressionOverride } = useAppState();
  const { progression: fetchedProgression, loading: progressionLoading, error: progressionError } =
    useCharacterProgression(characterId);
  // A prior confirm in this session (or a fresh level-up on top of an already-leveled-up
  // character) takes precedence over the freshly fetched fixture baseline.
  const progression = getProgressionOverride(characterId) ?? fetchedProgression;
  const { options, loading: optionsLoading, error: optionsError } = useLevelUpOptions();
  const [draft, setDraft] = useState<LevelUpDraft | null>(null);
  const [stepIndex, setStepIndex] = useState(0);
  const [showConfirmBanner, setShowConfirmBanner] = useState(false);

  useEffect(() => {
    if (progression && !draft) {
      setDraft({
        target: { mode: 'existing', classId: progression.classes[0].id },
        existingLevelOptionSelections: {},
        abilityIncrease: null,
        skillIncreases: {},
        newFeat: null,
        newBonusFeat: null,
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

  function nextStep() {
    if (stepIndex === STEPS.length - 1) {
      if (!showConfirmBanner) setProgressionOverride(characterId, applyLevelUp(prog, currentDraft));
      setShowConfirmBanner(true);
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
      case 'ability':
        return <AbilityIncreaseStep progression={prog} options={opts} draft={currentDraft} setDraft={setLevelUpDraft} />;
      case 'skills':
        return <LevelSkillsStep progression={prog} options={opts} draft={currentDraft} setDraft={setLevelUpDraft} />;
      case 'feat':
        return <LevelFeatStep progression={prog} options={opts} draft={currentDraft} setDraft={setLevelUpDraft} />;
      case 'spell':
        return <LevelSpellStep progression={prog} options={opts} draft={currentDraft} setDraft={setLevelUpDraft} />;
      case 'summary':
        return <LevelUpSummaryStep progression={prog} options={opts} draft={currentDraft} showConfirmBanner={showConfirmBanner} />;
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

          <div className="wizard-nav">
            <button type="button" className="btn-nav prev" disabled={stepIndex === 0} onClick={() => goToStep(stepIndex - 1)}>
              ← Zurück
            </button>
            <button type="button" className="btn-nav next" onClick={nextStep}>
              {stepIndex === STEPS.length - 1 ? 'Stufenaufstieg übernehmen ✦' : 'Weiter →'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
