export type NavTabId =
  | 'overview'
  | 'chat'
  | 'tasks'
  | 'memory'
  | 'skills'
  | 'tools'
  | 'integrations'
  | 'automations'
  | 'approvals'
  | 'activity_logs'
  | 'settings';

export interface NavItemConfig {
  id: NavTabId;
  label: string;
  iconName: string;
  description: string;
  phasePlanned: string;
  isImplementedInPhase0: boolean;
}
