import type { ReactNode } from 'react';

export interface TabDef {
  key: string;
  label: string;
}

interface TabBarProps {
  tabs: TabDef[];
  active: string;
  onChange: (key: string) => void;
}

export function TabBar({ tabs, active, onChange }: TabBarProps) {
  return (
    <div className="tab-bar">
      {tabs.map((tab) => (
        <button
          key={tab.key}
          type="button"
          className={`tab-btn${active === tab.key ? ' active' : ''}`}
          onClick={() => onChange(tab.key)}
        >
          {tab.label}
        </button>
      ))}
    </div>
  );
}

interface TabPanelProps {
  active: string;
  tabKey: string;
  children: ReactNode;
}

export function TabPanel({ active, tabKey, children }: TabPanelProps) {
  return <div className={`tab-panel${active === tabKey ? ' active' : ''}`}>{children}</div>;
}
