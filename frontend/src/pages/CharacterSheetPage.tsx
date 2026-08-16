import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { createId } from '../lib/id';
import { apiDelete, apiPatch, apiPost, apiPut } from '../api/client';
import { useAppState } from '../state/AppStateContext';
import { useCharacter } from '../hooks/useCharacter';
import { useEffectsCatalog } from '../hooks/useEffectsCatalog';
import { useConditionsCatalog } from '../hooks/useConditionsCatalog';
import { useItemsCatalog } from '../hooks/useItemsCatalog';
import { Panel } from '../components/primitives/Panel';
import { AppHeader } from '../components/sheet/AppHeader';
import { CharacterHeader } from '../components/sheet/CharacterHeader';
import { VitalsBar } from '../components/sheet/VitalsBar';
import { AbilityScores } from '../components/sheet/AbilityScores';
import { SavesAndCombat } from '../components/sheet/SavesAndCombat';
import { SheetTabs } from '../components/sheet/SheetTabs';
import { InventoryTabs } from '../components/sheet/InventoryTabs';
import { ActionsPanel } from '../components/sheet/ActionsPanel';
import { EffectsPanel, type TimeUnit } from '../components/sheet/EffectsPanel';
import { RealEffectsPanel, type ActivateEffectInput } from '../components/sheet/RealEffectsPanel';
import { ActivateEffectModal, type AvailableEntry } from '../components/sheet/ActivateEffectModal';
import { ItemDetailModal } from '../components/sheet/ItemDetailModal';
import type { ActionOption, ConditionType, Effect, EffectsView } from '../types/character';
import type { SearchEntry } from '../search/types';
import { ROUNDS_PER_UNIT } from '../lib/time';
import './CharacterSheetPage.css';

// The two mock sheet fixtures (`backend/app/main.py`'s CHARACTER_FIXTURES) have no
// backing database row — gear/slot mutations for them stay local-only (nothing to write to).
const FIXTURE_CHARACTER_IDS = new Set(['1', '2']);

// Aktionen-panel card tag by source type, for the activation modal opened via `handleActionClick`
// below — 'gear' never reaches this map (handled separately, no modal). Mirrors the tag each
// `sourceType` gets when picked from the Effekte panel's own picker (`RealEffectsPanel.tsx`).
const ACTIVATABLE_ACTION_TAGS: Record<NonNullable<ActionOption['sourceType']>, string> = {
  spell: 'Zauber',
  class_ability: 'Klassenfähigkeit',
  feat: 'Talent',
  gear: '',
};

export function CharacterSheetPage() {
  const { currentCharacterId, nameOverrides } = useAppState();
  const { character: rawCharacter, setCharacter, loading, error, refetch } = useCharacter(currentCharacterId);
  const nameOverride = nameOverrides[currentCharacterId];
  const character = rawCharacter && nameOverride ? { ...rawCharacter, name: nameOverride } : rawCharacter;
  const { catalog: effectsCatalog, loading: catalogLoading, error: catalogError } = useEffectsCatalog();
  const { catalog: conditionsCatalog, loading: conditionsLoading, error: conditionsError } = useConditionsCatalog();
  const { catalog: itemsCatalog, loading: itemsLoading, error: itemsError } = useItemsCatalog();
  const [skillsTab, setSkillsTab] = useState('skills');
  const [inventoryTab, setInventoryTab] = useState('inventory');
  const [itemDetailId, setItemDetailId] = useState<string | null>(null);
  const [pendingReveal, setPendingReveal] = useState<string | null>(null);
  const [gearError, setGearError] = useState<string | null>(null);
  const [hpError, setHpError] = useState<string | null>(null);
  const [effectError, setEffectError] = useState<string | null>(null);
  // Lifted out of RealEffectsPanel (same reason skillsTab/inventoryTab are lifted here): a
  // global-search jump to a catalog entry that the panel's own filter is currently hiding
  // needs to reset that filter first, same as jumping to a skill needs to switch tabs first.
  const [effectsSearch, setEffectsSearch] = useState('');
  const [effectsTypeFilter, setEffectsTypeFilter] = useState<ConditionType | ''>('');
  // Lifted out of RealEffectsPanel so ActionsPanel can trigger the same modal for a spell/class
  // ability action card, not just the Effekte panel's own picker.
  const [picked, setPicked] = useState<AvailableEntry | null>(null);
  const isRealCharacter = !FIXTURE_CHARACTER_IDS.has(currentCharacterId);

  // Closes any open gear popover when clicking outside it (mirrors the mock's global click listener).
  useEffect(() => {
    function handleDocClick(event: MouseEvent) {
      document.querySelectorAll<HTMLDetailsElement>('.gear-edit[open], .gear-add[open]').forEach((details) => {
        if (!details.contains(event.target as Node)) details.removeAttribute('open');
      });
    }
    document.addEventListener('click', handleDocClick);
    return () => document.removeEventListener('click', handleDocClick);
  }, []);

  useEffect(() => {
    function handleKeydown(event: KeyboardEvent) {
      if (event.key === 'Escape') setItemDetailId(null);
    }
    document.addEventListener('keydown', handleKeydown);
    return () => document.removeEventListener('keydown', handleKeydown);
  }, []);

  useEffect(() => {
    if (!pendingReveal) return;
    const id = pendingReveal;
    const frame = requestAnimationFrame(() => {
      const el = document.getElementById(id);
      if (!el) return;
      el.scrollIntoView({ behavior: 'smooth', block: 'center' });
      el.classList.remove('search-hit');
      void el.offsetWidth;
      el.classList.add('search-hit');
      setTimeout(() => el.classList.remove('search-hit'), 1600);
    });
    setPendingReveal(null);
    return () => cancelAnimationFrame(frame);
  }, [pendingReveal]);

  if (!currentCharacterId) {
    return (
      <div className="app">
        <AppHeader character={null} effects={null} conditionsCatalog={null} onJump={() => {}} />
        <div className="main" style={{ justifyContent: 'center' }}>
          <Panel title="Kein Charakter">
            <p style={{ marginBottom: 16 }}>Diesem Nutzer sind noch keine Charaktere zugeordnet.</p>
            <Link className="btn-levelup" to="/create">+ Neuer Charakter</Link>
          </Panel>
        </div>
      </div>
    );
  }

  if (loading || catalogLoading || conditionsLoading || itemsLoading) {
    return (
      <div className="app">
        <p style={{ color: '#e2d3ab', padding: 24 }}>Lade Charakter …</p>
      </div>
    );
  }

  if (error || catalogError || conditionsError || itemsError || !character || !effectsCatalog || !conditionsCatalog || !itemsCatalog) {
    return (
      <div className="app">
        <p style={{ color: '#e2d3ab', padding: 24 }}>
          Charakter konnte nicht geladen werden: {error ?? catalogError ?? conditionsError ?? itemsError}
        </p>
      </div>
    );
  }

  // Only meaningful for fixture characters — a real character's `effectsActive` is always `[]`
  // (see sheet.py), so this would otherwise list every mock catalog def as "available" and make
  // it falsely searchable/jumpable for a page that never renders those seals (RealEffectsPanel
  // renders instead of EffectsPanel there).
  const effectsView: EffectsView = isRealCharacter
    ? { effectsActive: [], effectsAvailable: [] }
    : {
        effectsActive: character.effectsActive,
        effectsAvailable: effectsCatalog.filter((def) => !character.effectsActive.some((active) => active.id === def.id)),
      };

  function handleJump(entry: SearchEntry) {
    if (entry.tabGroup === 'skills' && entry.tabKey) setSkillsTab(entry.tabKey);
    if (entry.tabGroup === 'inventory' && entry.tabKey) setInventoryTab(entry.tabKey);
    // A condition-catalog/activatable-spell/-ability hit lives inside RealEffectsPanel's own
    // search+type filter — reset it first so the target seal is actually in the DOM to scroll to,
    // same reasoning as switching skills/inventory tabs above.
    if (entry.id.startsWith('condition-catalog-') || entry.id.startsWith('activatable-')) {
      setEffectsSearch('');
      setEffectsTypeFilter('');
    }
    setPendingReveal(entry.id);
  }

  async function handleApplyHp(signedAmount: number) {
    if (!isRealCharacter) {
      setCharacter((prev) => {
        if (!prev) return prev;
        // Mirrors the backend's clamp (routers/characters.py's adjust_hp):
        // healing past hp.max is wasted, and damage bottoms out at -KO score
        // (PF1e RAW death threshold), not 0. Damage drains temporary HP
        // first, only spilling into current HP once that pool is empty;
        // healing never refills temporary HP.
        const conScore = prev.abilities.find((ability) => ability.key === 'KO')?.score ?? 0;
        let temporary = prev.hp.temporary;
        let amount = signedAmount;
        if (amount < 0) {
          const absorbed = Math.min(temporary, -amount);
          temporary -= absorbed;
          amount += absorbed;
        }
        const current = Math.max(-conScore, Math.min(prev.hp.max, prev.hp.current + amount));
        return { ...prev, hp: { ...prev.hp, current, temporary } };
      });
      return;
    }
    setHpError(null);
    try {
      await apiPatch(`/api/characters/${currentCharacterId}/hp`, { delta: signedAmount });
      refetch();
    } catch {
      setHpError('Trefferpunkte konnten nicht aktualisiert werden.');
    }
  }

  async function handleSetTempHp(amount: number) {
    if (!isRealCharacter) {
      setCharacter((prev) => (prev ? { ...prev, hp: { ...prev.hp, temporary: amount } } : prev));
      return;
    }
    setHpError(null);
    try {
      await apiPatch(`/api/characters/${currentCharacterId}/hp`, { temporary_hit_points: amount });
      refetch();
    } catch {
      setHpError('Temporäre Trefferpunkte konnten nicht aktualisiert werden.');
    }
  }

  async function handleAddGear(itemId: string, qty: number) {
    if (!isRealCharacter) {
      const item = itemsCatalog?.find((i) => i.id === itemId);
      if (!item) return;
      setCharacter((prev) => (prev ? { ...prev, gear: [...prev.gear, { id: createId(), name: item.name, qty }] } : prev));
      return;
    }
    setGearError(null);
    try {
      await apiPost(`/api/characters/${currentCharacterId}/gear`, { item_id: itemId, quantity: qty });
      refetch();
    } catch {
      setGearError('Gegenstand konnte nicht hinzugefügt werden.');
    }
  }

  async function handleSaveGear(id: string, qty: number) {
    if (!isRealCharacter) {
      setCharacter((prev) =>
        prev ? { ...prev, gear: prev.gear.map((item) => (item.id === id ? { ...item, qty } : item)) } : prev,
      );
      return;
    }
    setGearError(null);
    try {
      await apiPatch(`/api/characters/${currentCharacterId}/gear/${id}`, { quantity: qty });
      refetch();
    } catch {
      setGearError('Gegenstand konnte nicht gespeichert werden.');
    }
  }

  async function handleRemoveGear(id: string) {
    if (!isRealCharacter) {
      setCharacter((prev) => (prev ? { ...prev, gear: prev.gear.filter((item) => item.id !== id) } : prev));
      return;
    }
    setGearError(null);
    try {
      await apiDelete(`/api/characters/${currentCharacterId}/gear/${id}`);
      refetch();
    } catch {
      setGearError('Gegenstand konnte nicht entfernt werden.');
    }
  }

  async function handleSlotChange(key: string, value: string) {
    if (!isRealCharacter) {
      setCharacter((prev) =>
        prev
          ? { ...prev, equipmentSlots: prev.equipmentSlots.map((slot) => (slot.key === key ? { ...slot, selected: value } : slot)) }
          : prev,
      );
      return;
    }
    setGearError(null);
    try {
      await apiPut(`/api/characters/${currentCharacterId}/slots/${key}`, { item_id: value || null });
      refetch();
    } catch {
      setGearError('Ausrüstungsplatz konnte nicht geändert werden.');
    }
  }

  function handleToggleSpellCast(grade: number, spellKey: string) {
    setCharacter((prev) => {
      if (!prev) return prev;
      const spellsKnown = prev.spellsKnown.map((g) =>
        g.grade !== grade
          ? g
          : { ...g, spells: g.spells.map((s) => (s.key === spellKey ? { ...s, used: !s.used } : s)) },
      );
      return { ...prev, spellsKnown };
    });
  }

  function handleTogglePrepare(grade: number, spellKey: string) {
    setCharacter((prev) => {
      if (!prev) return prev;
      const spellbook = prev.spellbook.map((g) => {
        if (g.grade !== grade) return g;
        const activeCount = g.spells.filter((s) => s.prepared).length;
        const target = g.spells.find((s) => s.key === spellKey);
        if (!target || (!target.prepared && activeCount >= (g.maxPrepared ?? Infinity))) return g;
        return { ...g, spells: g.spells.map((s) => (s.key === spellKey ? { ...s, prepared: !s.prepared } : s)) };
      });
      return { ...prev, spellbook };
    });
  }

  function handleAdvanceTime(unit: TimeUnit) {
    setCharacter((prev) => {
      if (!prev) return prev;
      const roundsElapsed = ROUNDS_PER_UNIT[unit];
      const stillActive: Effect[] = [];

      for (const effect of prev.effectsActive) {
        if (effect.durationRounds == null) {
          // "Bis Rast" effects only clear on an actual rest — a full day tick implies one,
          // shorter ticks don't.
          if (unit === 'day') continue;
          stillActive.push(effect);
          continue;
        }
        const remaining = effect.durationRounds - roundsElapsed;
        if (remaining <= 0) continue;
        stillActive.push({ ...effect, durationRounds: remaining, durationLabel: `${remaining} ${remaining === 1 ? 'Runde' : 'Runden'}` });
      }

      const spellsKnown =
        unit === 'day'
          ? prev.spellsKnown.map((g) => ({ ...g, spells: g.spells.map((s) => ({ ...s, used: false })) }))
          : prev.spellsKnown;

      return { ...prev, effectsActive: stillActive, spellsKnown };
    });
  }

  /** Kurze Rast: renews spell slots and clears "bis Rast" effects without advancing any round
   *  counters, unlike "+1 Tag" which also ticks timed effects down (Requirement: rest vs. day-tick
   *  need to be distinguishable — see todos.md). */
  function handleShortRest() {
    setCharacter((prev) => {
      if (!prev) return prev;
      const effectsActive = prev.effectsActive.filter((effect) => effect.durationRounds !== null);
      const spellsKnown = prev.spellsKnown.map((g) => ({ ...g, spells: g.spells.map((s) => ({ ...s, used: false })) }));
      return { ...prev, effectsActive, spellsKnown };
    });
  }

  function handleActivateEffect(defId: string) {
    const def = effectsCatalog?.find((d) => d.id === defId);
    if (!def) return;
    setCharacter((prev) => {
      if (!prev) return prev;
      const effect: Effect = {
        id: createId(),
        icon: def.icon,
        amount: def.amount,
        name: def.name,
        detail: def.detail,
        variant: 'buff',
        active: true,
        durationRounds: null,
        durationLabel: 'bis Rast',
      };
      return { ...prev, effectsActive: [...prev.effectsActive, effect] };
    });
  }

  function handleRemoveActiveEffect(effectId: string) {
    setCharacter((prev) => (prev ? { ...prev, effectsActive: prev.effectsActive.filter((e) => e.id !== effectId) } : prev));
  }

  function handleAddCustomEffect(name: string, rounds: number | null) {
    setCharacter((prev) => {
      if (!prev) return prev;
      const effect: Effect = {
        id: createId(),
        icon: '✦',
        amount: '',
        name,
        detail: 'Eigener Zustand',
        variant: 'neutral',
        active: true,
        durationRounds: rounds,
        durationLabel: rounds != null ? `${rounds} ${rounds === 1 ? 'Runde' : 'Runden'}` : 'bis Rast',
      };
      return { ...prev, effectsActive: [...prev.effectsActive, effect] };
    });
  }

  function handleAddSpellToBook(grade: number, name: string) {
    setCharacter((prev) => {
      if (!prev) return prev;
      const spellbook = prev.spellbook.map((g) =>
        g.grade !== grade ? g : { ...g, spells: [...g.spells, { key: createId(), name, prepared: false }] },
      );
      return { ...prev, spellbook };
    });
  }

  function handleRemoveSpellFromBook(grade: number, spellKey: string) {
    setCharacter((prev) => {
      if (!prev) return prev;
      const spellbook = prev.spellbook.map((g) =>
        g.grade !== grade ? g : { ...g, spells: g.spells.filter((s) => s.key !== spellKey) },
      );
      return { ...prev, spellbook };
    });
  }

  async function handleActivateRealEffect(input: ActivateEffectInput) {
    setEffectError(null);
    try {
      await apiPost(`/api/characters/${currentCharacterId}/effects`, {
        source_type: input.sourceType,
        source_id: input.sourceId,
        level: input.level,
        incubation_remaining: input.incubationRemaining,
        duration_remaining: input.durationRemaining,
        frequency_rounds: input.frequencyRounds,
        successes_required: input.successesRequired,
      });
      refetch();
    } catch {
      setEffectError('Effekt konnte nicht aktiviert werden.');
    }
  }

  function handleActivateAndClose(input: ActivateEffectInput) {
    handleActivateRealEffect(input);
    setPicked(null);
  }

  // Aktionen-panel cards route to one of two existing flows: spell/class-ability/feat entries open
  // the same activation modal the Effekte panel's own picker uses; gear entries have no player-
  // supplied values to ask for, so they fire straight through to the use/toggle endpoint (backend
  // `sheet.py`'s `_build_actions` already decided which of the two per entry via `gearActionKind`).
  function handleActionClick(action: ActionOption) {
    if (!action.sourceType || !action.sourceId) return; // mock/fixture card, never wired
    if (action.sourceType === 'gear') {
      handleGearAction(action.sourceId, action.gearActionKind ?? 'use');
      return;
    }
    setPicked({
      domId: `action-${action.id}`,
      sourceType: action.sourceType,
      sourceId: action.sourceId,
      name: action.name,
      description: action.description,
      icon: action.icon,
      tag: ACTIVATABLE_ACTION_TAGS[action.sourceType],
      defaultDurationRounds: action.defaultDurationRounds,
    });
  }

  async function handleGearAction(itemId: string, kind: 'use' | 'toggle') {
    if (!isRealCharacter) return;
    setEffectError(null);
    try {
      await apiPatch(`/api/characters/${currentCharacterId}/gear/${itemId}/${kind}`);
      refetch();
    } catch {
      setEffectError('Aktion konnte nicht ausgeführt werden.');
    }
  }

  async function handleRemoveRealEffect(effectId: string) {
    setEffectError(null);
    try {
      await apiDelete(`/api/characters/${currentCharacterId}/effects/${effectId}`);
      refetch();
    } catch {
      setEffectError('Effekt konnte nicht entfernt werden.');
    }
  }

  async function handleSaveResult(effectId: string, success: boolean) {
    setEffectError(null);
    try {
      await apiPost(`/api/characters/${currentCharacterId}/effects/${effectId}/save-result`, { success });
      refetch();
    } catch {
      setEffectError('Rettungswurf-Ergebnis konnte nicht gespeichert werden.');
    }
  }

  async function handleAdvanceRealTime(unit: TimeUnit) {
    setEffectError(null);
    try {
      await apiPost(`/api/characters/${currentCharacterId}/advance-time`, { unit });
      refetch();
    } catch {
      setEffectError('Zeit konnte nicht vorangeschritten werden.');
    }
  }

  async function handleSaveItemDetail(id: string, enhancement: string, properties: string[]) {
    if (!isRealCharacter) {
      setCharacter((prev) =>
        prev ? { ...prev, gear: prev.gear.map((item) => (item.id === id ? { ...item, enhancement, properties } : item)) } : prev,
      );
      return;
    }
    setGearError(null);
    try {
      await apiPatch(`/api/characters/${currentCharacterId}/gear/${id}`, {
        enhancement: parseInt(enhancement, 10) || 0,
        properties,
      });
      refetch();
    } catch {
      setGearError('Gegenstand konnte nicht gespeichert werden.');
    }
  }

  return (
    <div className="app">
      <AppHeader character={character} effects={effectsView} conditionsCatalog={conditionsCatalog} onJump={handleJump} />

      <div className="main">
        <Panel title="Charakter" hint={`Stufe ${character.level} · ${character.className}`}>
          <CharacterHeader character={character} />
          <VitalsBar character={character} onApplyHp={handleApplyHp} onSetTempHp={handleSetTempHp} />
          {hpError && <p style={{ color: '#e29a9a' }}>{hpError}</p>}

          <div className="section-label">Attribute</div>
          <AbilityScores abilities={character.abilities} />

          <SavesAndCombat saves={character.saves} combat={character.combat} weaponAttacks={character.weaponAttacks} />

          <SheetTabs
            character={character}
            activeTab={skillsTab}
            onTabChange={setSkillsTab}
            onToggleSpellCast={handleToggleSpellCast}
          />

          {gearError && <p style={{ color: '#e29a9a' }}>{gearError}</p>}
          <InventoryTabs
            character={character}
            itemsCatalog={itemsCatalog}
            activeTab={inventoryTab}
            onTabChange={setInventoryTab}
            onAddGear={handleAddGear}
            onSaveGear={handleSaveGear}
            onRemoveGear={handleRemoveGear}
            onOpenItemDetail={setItemDetailId}
            onSlotChange={handleSlotChange}
            onTogglePrepare={handleTogglePrepare}
            onAddSpellToBook={handleAddSpellToBook}
            onRemoveSpellFromBook={handleRemoveSpellFromBook}
          />
        </Panel>

        <div className="right-col">
          <ActionsPanel actions={character.actions} roundLabel={character.roundLabel} onActionClick={handleActionClick} />
          {effectError && <p style={{ color: '#e29a9a' }}>{effectError}</p>}
          {isRealCharacter ? (
            <RealEffectsPanel
              activeEffects={character.activeEffects}
              conditionsCatalog={conditionsCatalog}
              activatableSpells={character.activatableSpells}
              activatableClassAbilities={character.activatableClassAbilities}
              activatableFeats={character.activatableFeats}
              externalClassAbilities={character.externalClassAbilities}
              search={effectsSearch}
              onSearchChange={setEffectsSearch}
              typeFilter={effectsTypeFilter}
              onTypeFilterChange={setEffectsTypeFilter}
              onAdvanceTime={handleAdvanceRealTime}
              onPick={setPicked}
              onRemove={handleRemoveRealEffect}
              onSaveResult={handleSaveResult}
            />
          ) : (
            <EffectsPanel
              effectsActive={effectsView.effectsActive}
              effectsAvailable={effectsView.effectsAvailable}
              onAdvanceTime={handleAdvanceTime}
              onShortRest={handleShortRest}
              onActivateEffect={handleActivateEffect}
              onRemoveEffect={handleRemoveActiveEffect}
              onAddCustomEffect={handleAddCustomEffect}
            />
          )}
        </div>
      </div>

      <ItemDetailModal
        item={character.gear.find((item) => item.id === itemDetailId) ?? null}
        onClose={() => setItemDetailId(null)}
        onSave={handleSaveItemDetail}
      />

      <ActivateEffectModal
        entry={picked}
        characterLevel={character.level}
        onCancel={() => setPicked(null)}
        onActivate={handleActivateAndClose}
      />
    </div>
  );
}
