export type TabGroup = 'skills' | 'inventory';

export interface SearchEntry {
  id: string;
  label: string;
  value: string;
  category: string;
  tabGroup?: TabGroup;
  tabKey?: string;
}
