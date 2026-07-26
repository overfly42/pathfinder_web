import { useEffect, useState } from 'react';
import { useCharacter } from '../hooks/useCharacter';
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
import type { Effect } from '../types/character';
import type { SearchEntry } from '../search/types';
import './CharacterSheetPage.css';

const ROUNDS_PER_UNIT: Record<TimeUnit, number> = {
  round: 1,
  minute: 10,
  hour: 600,
  day: Infinity,
};

function createId() {
  return typeof crypto !== 'undefined' && crypto.randomUUID ? crypto.randomUUID() : `id-${Date.now()}-${Math.random()}`;
}

export function CharacterSheetPage() {
  const { character, setCharacter, loading, error } = useCharacter('1');
  const [skillsTab, setSkillsTab] = useState('skills');
  const [inventoryTab, setInventoryTab] = useState('inventory');
  const [itemDetailName, setItemDetailName] = useState<string | null>(null);
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
      if (event.key === 'Escape') setItemDetailName(null);
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

  if (loading) {
    return (
      <div className="app">
        <p style={{ color: '#e2d3ab', padding: 24 }}>Lade Charakter …</p>
      </div>
    );
  }

  if (error || !character) {
    return (
      <div className="app">
        <p style={{ color: '#e2d3ab', padding: 24 }}>Charakter konnte nicht geladen werden: {error}</p>
      </div>
    );
  }

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
      const newlyExpired: Effect[] = [];

      for (const effect of prev.effectsActive) {
        if (unit === 'day') {
          newlyExpired.push({ ...effect, active: false, durationRounds: null, durationLabel: 'Aktivieren' });
          continue;
        }
        if (effect.durationRounds == null) {
          stillActive.push(effect);
          continue;
        }
        const remaining = effect.durationRounds - roundsElapsed;
        if (remaining <= 0) {
          newlyExpired.push({ ...effect, active: false, durationRounds: null, durationLabel: 'Aktivieren' });
        } else {
          stillActive.push({ ...effect, durationRounds: remaining, durationLabel: `${remaining} ${remaining === 1 ? 'Runde' : 'Runden'}` });
        }
      }

      return { ...prev, effectsActive: stillActive, effectsAvailable: [...prev.effectsAvailable, ...newlyExpired] };
    });
  }

  return (
    <div className="app">
      <AppHeader character={character} onJump={handleJump} />

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
            onOpenItemDetail={setItemDetailName}
            onSlotChange={handleSlotChange}
            onTogglePrepare={handleTogglePrepare}
          />
        </Panel>

        <div className="right-col">
          <ActionsPanel actions={character.actions} roundLabel={character.roundLabel} />
          <EffectsPanel
            effectsActive={character.effectsActive}
            effectsAvailable={character.effectsAvailable}
            onAdvanceTime={handleAdvanceTime}
          />
        </div>
      </div>

      <ItemDetailModal itemName={itemDetailName} onClose={() => setItemDetailName(null)} />
    </div>
  );
}
