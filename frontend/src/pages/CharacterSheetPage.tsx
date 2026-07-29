import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { createId } from '../lib/id';
import { useAppState } from '../state/AppStateContext';
import { useCharacter } from '../hooks/useCharacter';
import { useEffectsCatalog } from '../hooks/useEffectsCatalog';
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
import { ItemDetailModal } from '../components/sheet/ItemDetailModal';
import type { Effect, EffectsView } from '../types/character';
import type { SearchEntry } from '../search/types';
import './CharacterSheetPage.css';

const ROUNDS_PER_UNIT: Record<TimeUnit, number> = {
  round: 1,
  minute: 10,
  hour: 600,
  /** A day is a large but finite round count (24h), not Infinity — timed effects should decrement
   *  and expire like any other unit, not get silently dropped (see handleAdvanceTime). */
  day: 600 * 24,
};

export function CharacterSheetPage() {
  const { currentCharacterId, nameOverrides } = useAppState();
  const { character: rawCharacter, setCharacter, loading, error } = useCharacter(currentCharacterId);
  const nameOverride = nameOverrides[currentCharacterId];
  const character = rawCharacter && nameOverride ? { ...rawCharacter, name: nameOverride } : rawCharacter;
  const { catalog: effectsCatalog, loading: catalogLoading, error: catalogError } = useEffectsCatalog();
  const [skillsTab, setSkillsTab] = useState('skills');
  const [inventoryTab, setInventoryTab] = useState('inventory');
  const [itemDetailId, setItemDetailId] = useState<string | null>(null);
  const [pendingReveal, setPendingReveal] = useState<string | null>(null);

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
        <AppHeader character={null} effects={null} onJump={() => {}} />
        <div className="main" style={{ justifyContent: 'center' }}>
          <Panel title="Kein Charakter">
            <p style={{ marginBottom: 16 }}>Diesem Nutzer sind noch keine Charaktere zugeordnet.</p>
            <Link className="btn-levelup" to="/create">+ Neuer Charakter</Link>
          </Panel>
        </div>
      </div>
    );
  }

  if (loading || catalogLoading) {
    return (
      <div className="app">
        <p style={{ color: '#e2d3ab', padding: 24 }}>Lade Charakter …</p>
      </div>
    );
  }

  if (error || catalogError || !character || !effectsCatalog) {
    return (
      <div className="app">
        <p style={{ color: '#e2d3ab', padding: 24 }}>Charakter konnte nicht geladen werden: {error ?? catalogError}</p>
      </div>
    );
  }

  // Real (database-backed) characters (roadmap slice 2+) only have the thin/computed shape so
  // far — no abilities/saves/gear/etc. — unlike the two rich mock fixtures. Rather than crash on
  // missing fields, show a placeholder until the sheet's full computed shape exists (roadmap
  // slice 3+).
  if (!('effectsActive' in character)) {
    return (
      <div className="app">
        <AppHeader character={null} effects={null} onJump={() => {}} />
        <div className="main" style={{ justifyContent: 'center' }}>
          <Panel title={character.name}>
            <p>Dieser Charakter wurde gespeichert, aber die vollständige Charakterbogen-Ansicht ist noch nicht verfügbar.</p>
          </Panel>
        </div>
      </div>
    );
  }

  const effectsView: EffectsView = {
    effectsActive: character.effectsActive,
    effectsAvailable: effectsCatalog.filter((def) => !character.effectsActive.some((active) => active.id === def.id)),
  };

  function handleJump(entry: SearchEntry) {
    if (entry.tabGroup === 'skills' && entry.tabKey) setSkillsTab(entry.tabKey);
    if (entry.tabGroup === 'inventory' && entry.tabKey) setInventoryTab(entry.tabKey);
    setPendingReveal(entry.id);
  }

  function handleApplyHp(signedAmount: number) {
    setCharacter((prev) => {
      if (!prev) return prev;
      const current = Math.min(prev.hp.max, Math.max(0, prev.hp.current + signedAmount));
      return { ...prev, hp: { ...prev.hp, current } };
    });
  }

  function handleAddGear(name: string, qty: number) {
    setCharacter((prev) => (prev ? { ...prev, gear: [...prev.gear, { id: createId(), name, qty }] } : prev));
  }

  function handleSaveGear(id: string, name: string, qty: number) {
    setCharacter((prev) =>
      prev ? { ...prev, gear: prev.gear.map((item) => (item.id === id ? { ...item, name, qty } : item)) } : prev,
    );
  }

  function handleRemoveGear(id: string) {
    setCharacter((prev) => (prev ? { ...prev, gear: prev.gear.filter((item) => item.id !== id) } : prev));
  }

  function handleSlotChange(key: string, value: string) {
    setCharacter((prev) =>
      prev
        ? { ...prev, equipmentSlots: prev.equipmentSlots.map((slot) => (slot.key === key ? { ...slot, selected: value } : slot)) }
        : prev,
    );
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

  function handleSaveItemDetail(id: string, enhancement: string, properties: string[]) {
    setCharacter((prev) =>
      prev ? { ...prev, gear: prev.gear.map((item) => (item.id === id ? { ...item, enhancement, properties } : item)) } : prev,
    );
  }

  return (
    <div className="app">
      <AppHeader character={character} effects={effectsView} onJump={handleJump} />

      <div className="main">
        <Panel title="Charakter" hint={`Stufe ${character.level} · ${character.className}`}>
          <CharacterHeader character={character} />
          <VitalsBar character={character} onApplyHp={handleApplyHp} />

          <div className="section-label">Attribute</div>
          <AbilityScores abilities={character.abilities} />

          <SavesAndCombat saves={character.saves} combat={character.combat} />

          <SheetTabs
            character={character}
            activeTab={skillsTab}
            onTabChange={setSkillsTab}
            onToggleSpellCast={handleToggleSpellCast}
          />

          <InventoryTabs
            character={character}
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
          <ActionsPanel actions={character.actions} roundLabel={character.roundLabel} />
          <EffectsPanel
            effectsActive={effectsView.effectsActive}
            effectsAvailable={effectsView.effectsAvailable}
            onAdvanceTime={handleAdvanceTime}
            onShortRest={handleShortRest}
            onActivateEffect={handleActivateEffect}
            onRemoveEffect={handleRemoveActiveEffect}
            onAddCustomEffect={handleAddCustomEffect}
          />
        </div>
      </div>

      <ItemDetailModal
        item={character.gear.find((item) => item.id === itemDetailId) ?? null}
        onClose={() => setItemDetailId(null)}
        onSave={handleSaveItemDetail}
      />
    </div>
  );
}
