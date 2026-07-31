import type { Character } from '../../types/character';
import type { ItemCatalogEntry } from '../../types/creationOptions';
import { TabBar, TabPanel, type TabDef } from '../primitives/Tabs';
import { GearList } from './GearList';
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
  activeTab: string;
  onTabChange: (tab: string) => void;
  onAddGear: (itemId: string, qty: number) => void;
  onSaveGear: (id: string, qty: number) => void;
  onRemoveGear: (id: string) => void;
  onOpenItemDetail: (id: string) => void;
  onSlotChange: (key: string, value: string) => void;
  onTogglePrepare: (grade: number, spellKey: string) => void;
  onAddSpellToBook: (grade: number, name: string) => void;
  onRemoveSpellFromBook: (grade: number, spellKey: string) => void;
}

export function InventoryTabs({
  character,
  itemsCatalog,
  activeTab,
  onTabChange,
  onAddGear,
  onSaveGear,
  onRemoveGear,
  onOpenItemDetail,
  onSlotChange,
  onTogglePrepare,
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
        </TabPanel>

        <TabPanel active={activeTab} tabKey="slots">
          <EquipmentSlots slots={character.equipmentSlots} onChange={onSlotChange} />
        </TabPanel>

        <TabPanel active={activeTab} tabKey="spellbook">
          <Spellbook
            grades={character.spellbook}
            onTogglePrepare={onTogglePrepare}
            onAddSpell={onAddSpellToBook}
            onRemoveSpell={onRemoveSpellFromBook}
          />
        </TabPanel>
      </div>
    </>
  );
}
