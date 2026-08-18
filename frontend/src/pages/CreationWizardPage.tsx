import { useState } from 'react';
import { Link } from 'react-router-dom';
import { apiPost } from '../api/client';
import { featSelectionsForSubmission, selectedRace, spellIdsForSubmission } from '../lib/creationCalculations';
import { useCreationOptions } from '../hooks/useCreationOptions';
import { useAppState } from '../state/AppStateContext';
import { createInitialDraft } from '../lib/initialDraft';
import { Panel } from '../components/primitives/Panel';
import { Stepper, type StepDef } from '../components/primitives/Stepper';
import { BasicsStep } from '../components/creation/BasicsStep';
import { ClassStep } from '../components/creation/ClassStep';
import { AbilitiesStep } from '../components/creation/AbilitiesStep';
import { SkillsStep } from '../components/creation/SkillsStep';
import { FeatsStep } from '../components/creation/FeatsStep';
import { TraitsStep } from '../components/creation/TraitsStep';
import { SpellsStep } from '../components/creation/SpellsStep';
import { EquipmentStep } from '../components/creation/EquipmentStep';
import { SummaryStep } from '../components/creation/SummaryStep';
import './CreationWizardPage.css';

const STEPS: StepDef[] = [
  { key: 'basics', label: 'Grunddaten' },
  { key: 'class', label: 'Klasse' },
  { key: 'abilities', label: 'Attribute' },
  { key: 'skills', label: 'Fertigkeiten' },
  { key: 'feats', label: 'Talente' },
  { key: 'traits', label: 'Wesenszüge' },
  { key: 'spells', label: 'Zauber' },
  { key: 'equipment', label: 'Ausrüstung' },
  { key: 'summary', label: 'Zusammenfassung' },
];

type SubmitState = 'idle' | 'submitting' | 'success' | 'error';

export function CreationWizardPage() {
  const { options, loading, error } = useCreationOptions();
  const { currentUserId } = useAppState();
  const [draft, setDraft] = useState(createInitialDraft);
  const [stepIndex, setStepIndex] = useState(0);
  const [submitState, setSubmitState] = useState<SubmitState>('idle');
  const [submitErrorMessage, setSubmitErrorMessage] = useState('');

  if (loading) {
    return (
      <div className="app">
        <p style={{ color: '#e2d3ab', padding: 24 }}>Lade Charaktererstellung …</p>
      </div>
    );
  }

  if (error || !options) {
    return (
      <div className="app">
        <p style={{ color: '#e2d3ab', padding: 24 }}>Referenzdaten konnten nicht geladen werden: {error}</p>
      </div>
    );
  }

  const opts = options;

  function goToStep(n: number) {
    if (n < 0 || n > STEPS.length - 1) return;
    setStepIndex(n);
  }

  async function nextStep() {
    if (stepIndex === STEPS.length - 1) {
      if (!currentUserId) {
        setSubmitState('error');
        setSubmitErrorMessage('Bitte zuerst oben im Header einen Nutzer auswählen.');
        return;
      }
      if (!draft.raceId) {
        setSubmitState('error');
        setSubmitErrorMessage('Bitte im Schritt „Grunddaten" eine Rasse auswählen.');
        return;
      }
      const hasClass = draft.classRows.length > 0 && draft.classRows.every((row) => row.className);
      if (!draft.name.trim() || !hasClass) {
        setSubmitState('error');
        setSubmitErrorMessage('Bitte Name und Klasse ausfüllen.');
        return;
      }
      const race = selectedRace(draft, opts);
      if (race?.flex && !draft.flexAbility) {
        setSubmitState('error');
        setSubmitErrorMessage('Bitte im Schritt „Attribute" ein Attribut für den freien Rassenbonus wählen.');
        return;
      }
      const featById = new Map(opts.feats.map((f) => [f.id, f]));
      const missingFeatSubChoice = draft.feats.some((id) => {
        const feat = featById.get(id);
        return feat?.subChoiceType && !draft.featSubChoices[id];
      });
      if (missingFeatSubChoice) {
        setSubmitState('error');
        setSubmitErrorMessage('Bitte im Schritt „Talente" für jedes markierte Talent eine Wahl treffen (Waffe/Fertigkeit/Schule).');
        return;
      }
      if (!draft.favoredClassBonus) {
        setSubmitState('error');
        setSubmitErrorMessage('Bitte im Schritt „Klasse" den Bonus der bevorzugten Klasse für die 1. Stufe wählen.');
        return;
      }

      setSubmitState('submitting');
      try {
        await apiPost('/api/characters', {
          name: draft.name.trim(),
          user_id: currentUserId,
          race_id: draft.raceId,
          classes: draft.classRows.map((row) => ({
            class_name: row.className,
            level: row.level,
            archetypes: row.archetypes,
            options: row.options,
          })),
          favored_class_bonus: { '1': draft.favoredClassBonus },
          ability_scores: draft.abilityScores,
          point_budget: draft.pointBudget,
          flex_ability: draft.flexAbility,
          alt_traits: draft.altTraits,
          skill_ranks: draft.skillRanks,
          feats: featSelectionsForSubmission(draft, opts),
          trait_ids: draft.traits,
          spell_ids: spellIdsForSubmission(draft, opts),
          gear: draft.gear.map((item) => ({ item_id: item.itemId, quantity: item.qty })),
        });
        setSubmitState('success');
      } catch {
        setSubmitState('error');
        setSubmitErrorMessage('Charakter konnte nicht gespeichert werden.');
      }
      return;
    }
    goToStep(stepIndex + 1);
  }

  function renderStep() {
    switch (STEPS[stepIndex].key) {
      case 'basics':
        return <BasicsStep draft={draft} options={opts} setDraft={setDraft} />;
      case 'class':
        return <ClassStep draft={draft} options={opts} setDraft={setDraft} />;
      case 'abilities':
        return <AbilitiesStep draft={draft} options={opts} setDraft={setDraft} />;
      case 'skills':
        return <SkillsStep draft={draft} options={opts} setDraft={setDraft} />;
      case 'feats':
        return <FeatsStep draft={draft} options={opts} setDraft={setDraft} />;
      case 'traits':
        return <TraitsStep draft={draft} options={opts} setDraft={setDraft} />;
      case 'spells':
        return <SpellsStep draft={draft} options={opts} setDraft={setDraft} />;
      case 'equipment':
        return <EquipmentStep draft={draft} options={opts} setDraft={setDraft} />;
      case 'summary':
        return (
          <SummaryStep
            draft={draft}
            options={opts}
            submitState={submitState}
            submitErrorMessage={submitErrorMessage}
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
            <span className="subtitle">Neuen Charakter erschaffen</span>
          </div>
        </div>
        <div className="spacer" />
        <Link className="btn-outline" to="/">← Zurück zum Charakterbogen</Link>
      </header>

      <div className="wizard-wrap">
        <div className="wizard">
          <Stepper steps={STEPS} activeIndex={stepIndex} onSelect={goToStep} />

          <Panel title={STEPS[stepIndex].label} hint={`Schritt ${stepIndex + 1} von ${STEPS.length}`}>
            {renderStep()}
          </Panel>

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
                  : 'Charakter erstellen ✦'
                : 'Weiter →'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
