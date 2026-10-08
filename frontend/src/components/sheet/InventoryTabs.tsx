import type { Character } from '../../types/character';
import type { ItemCatalogEntry, SpellDef } from '../../types/creationOptions';
import { TabBar, TabPanel, type TabDef } from '../primitives/Tabs';
import { GearList } from './GearList';
import { WandList } from './WandList';
import { EquipmentSlots } from './EquipmentSlots';
import { Spellbook } from './Spellbook';

const TABS: TabDef[] = [
  { key: 'inventory', label: 'Inventar' },
  { key: 'slots', label: 'Ausrüstungsplätze' },
  { key: 'spellbook', label: 'Zauberbuch' },
];

interface InventoryTabsProps {
  character: Character;
  itemsCatalog: ItemCatalogEntry[];
  spellsByClass: Record<string, SpellDef[]> | null;
  activeTab: string;
  onTabChange: (tab: string) => void;
  onAddGear: (itemId: string, qty: number) => void;
  onSaveGear: (id: string, qty: number) => void;
  onRemoveGear: (id: string) => void;
  onOpenItemDetail: (id: string) => void;
  wandSpellCatalog: SpellDef[];
  onAddWand: (spellId: string) => void;
  onUseWand: (id: string) => void;
  onRemoveWand: (id: string) => void;
  onSlotChange: (key: string, value: string) => void;
  onPrepareSpell: (grade: number, spellKey: string, baseClassId: string) => void;
  onUnprepareSpell: (grade: number, spellKey: string, baseClassId: string) => void;
  onAddSpellToBook: (grade: number, baseClassId: string, spellId: string, name: string) => void;
  onRemoveSpellFromBook: (grade: number, spellKey: string) => void;
}

export function InventoryTabs({
  character,
  itemsCatalog,
  spellsByClass,
  activeTab,
  onTabChange,
  onAddGear,
  onSaveGear,
  onRemoveGear,
  onOpenItemDetail,
  wandSpellCatalog,
  onAddWand,
  onUseWand,
  onRemoveWand,
  onSlotChange,
  onPrepareSpell,
  onUnprepareSpell,
  onAddSpellToBook,
  onRemoveSpellFromBook,
}: InventoryTabsProps) {
  return (
    <>
      <div className="section-label">Ausrüstung</div>
      <div className="tabset">
        <TabBar tabs={TABS} active={activeTab} onChange={onTabChange} />

        <TabPanel active={activeTab} tabKey="inventory">
          <GearList
            gear={character.gear}
            catalog={itemsCatalog}
            onAdd={onAddGear}
            onSave={onSaveGear}
            onRemove={onRemoveGear}
            onOpenDetail={onOpenItemDetail}
          />
          {character.wands && (
            <WandList
              wands={character.wands}
              spellCatalog={wandSpellCatalog}
              onAdd={onAddWand}
              onUse={onUseWand}
              onRemove={onRemoveWand}
            />
          )}
        </TabPanel>

        <TabPanel active={activeTab} tabKey="slots">
          <EquipmentSlots slots={character.equipmentSlots} onChange={onSlotChange} />
        </TabPanel>

        <TabPanel active={activeTab} tabKey="spellbook">
          <Spellbook
            grades={character.spellbook}
            classes={character.classes}
            spellsByClass={spellsByClass}
            onPrepareSpell={onPrepareSpell}
            onUnprepareSpell={onUnprepareSpell}
            onAddSpell={onAddSpellToBook}
            onRemoveSpell={onRemoveSpellFromBook}
          />
        </TabPanel>
      </div>
    </>
  );
}
