import type { ReactNode } from 'react';
import type { NavTabId, NavItemConfig } from '../../types/navigation';
import {
  LayoutDashboard,
  MessageSquare,
  CheckSquare,
  Brain,
  Sparkles,
  Wrench,
  Plug,
  Zap,
  ShieldCheck,
  ScrollText,
  Settings,
  ChevronRight,
} from 'lucide-react';

export const NAVIGATION_ITEMS: NavItemConfig[] = [
  {
    id: 'overview',
    label: 'Overview',
    iconName: 'LayoutDashboard',
    description: 'System health, PostgreSQL status, and architecture metrics.',
    phasePlanned: 'Phase 0',
    isImplementedInPhase0: true,
  },
  {
    id: 'chat',
    label: 'Chat',
    iconName: 'MessageSquare',
    description: 'Direct conversational interface with streaming AI responses.',
    phasePlanned: 'Phase 1',
    isImplementedInPhase0: true,
  },
  {
    id: 'tasks',
    label: 'Tasks',
    iconName: 'CheckSquare',
    description: 'Task lifecycle management, backlog, and multi-step plans.',
    phasePlanned: 'Phase 2',
    isImplementedInPhase0: false,
  },
  {
    id: 'memory',
    label: 'Memory',
    iconName: 'Brain',
    description: 'Controlled persistent memory, user preferences, and pgvector knowledge store.',
    phasePlanned: 'Phase 2',
    isImplementedInPhase0: false,
  },
  {
    id: 'skills',
    label: 'Skills',
    iconName: 'Sparkles',
    description: 'Executable reusable agent skill catalog and custom capability definitions.',
    phasePlanned: 'Phase 3',
    isImplementedInPhase0: false,
  },
  {
    id: 'tools',
    label: 'Tools',
    iconName: 'Wrench',
    description: 'Native execution tools, MCP servers, and local environment bridges.',
    phasePlanned: 'Phase 3',
    isImplementedInPhase0: false,
  },
  {
    id: 'integrations',
    label: 'Integrations',
    iconName: 'Plug',
    description: 'External service accounts, OAuth providers, and cloud connectors.',
    phasePlanned: 'Phase 4',
    isImplementedInPhase0: false,
  },
  {
    id: 'automations',
    label: 'Automations',
    iconName: 'Zap',
    description: 'Background cron jobs, event-driven reactive pipelines, and proactive triggers.',
    phasePlanned: 'Phase 4',
    isImplementedInPhase0: false,
  },
  {
    id: 'approvals',
    label: 'Approvals',
    iconName: 'ShieldCheck',
    description: 'Human-in-the-loop permission gateway for sensitive actions and external writes.',
    phasePlanned: 'Phase 3',
    isImplementedInPhase0: false,
  },
  {
    id: 'activity_logs',
    label: 'Activity Logs',
    iconName: 'ScrollText',
    description: 'Structured audit trail of agent executions, tool calls, and system events.',
    phasePlanned: 'Phase 1',
    isImplementedInPhase0: false,
  },
  {
    id: 'settings',
    label: 'Settings',
    iconName: 'Settings',
    description: 'AI model provider credentials, base URLs, and runtime parameters.',
    phasePlanned: 'Phase 1',
    isImplementedInPhase0: true,
  },
];

const ICONS: Record<string, ReactNode> = {
  LayoutDashboard: <LayoutDashboard className="w-4 h-4" />,
  MessageSquare: <MessageSquare className="w-4 h-4" />,
  CheckSquare: <CheckSquare className="w-4 h-4" />,
  Brain: <Brain className="w-4 h-4" />,
  Sparkles: <Sparkles className="w-4 h-4" />,
  Wrench: <Wrench className="w-4 h-4" />,
  Plug: <Plug className="w-4 h-4" />,
  Zap: <Zap className="w-4 h-4" />,
  ShieldCheck: <ShieldCheck className="w-4 h-4" />,
  ScrollText: <ScrollText className="w-4 h-4" />,
  Settings: <Settings className="w-4 h-4" />,
};

interface SidebarProps {
  currentTab: NavTabId;
  onSelectTab: (tab: NavTabId) => void;
  isOpen: boolean;
  onClose: () => void;
}

export const Sidebar: React.FC<SidebarProps> = ({
  currentTab,
  onSelectTab,
  isOpen,
  onClose,
}) => {
  return (
    <>
      {/* Mobile backdrop */}
      {isOpen && (
        <div
          onClick={onClose}
          className="fixed inset-0 bg-slate-950/80 backdrop-blur-sm z-40 md:hidden"
        />
      )}

      {/* Sidebar container */}
      <aside
        className={`fixed md:sticky top-0 left-0 z-50 md:z-20 h-screen w-64 bg-slate-950 border-r border-slate-800 flex flex-col transition-transform duration-200 ease-in-out md:translate-x-0 ${
          isOpen ? 'translate-x-0' : '-translate-x-full'
        }`}
      >
        {/* Navigation list */}
        <div className="p-3 border-b border-slate-800/80">
          <div className="px-3 py-1.5 text-[11px] font-semibold tracking-wider uppercase text-slate-500">
            Navigation Menu
          </div>
        </div>

        <nav className="flex-1 overflow-y-auto p-3 space-y-1">
          {NAVIGATION_ITEMS.map((item) => {
            const isActive = currentTab === item.id;
            const icon = ICONS[item.iconName] || <LayoutDashboard className="w-4 h-4" />;

            return (
              <button
                key={item.id}
                onClick={() => {
                  onSelectTab(item.id);
                  onClose();
                }}
                className={`w-full flex items-center justify-between px-3 py-2.5 rounded-lg text-xs font-medium transition-all group cursor-pointer ${
                  isActive
                    ? 'bg-indigo-600/15 text-indigo-300 border border-indigo-500/30'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900 border border-transparent'
                }`}
              >
                <div className="flex items-center gap-3 min-w-0">
                  <div
                    className={`${
                      isActive ? 'text-indigo-400' : 'text-slate-500 group-hover:text-slate-300'
                    }`}
                  >
                    {icon}
                  </div>
                  <span className="truncate">{item.label}</span>
                </div>

                <div className="flex items-center gap-1.5">
                  {!item.isImplementedInPhase0 && (
                    <span className="text-[10px] px-1.5 py-0.2 rounded bg-slate-900 text-slate-500 border border-slate-800">
                      {item.phasePlanned}
                    </span>
                  )}
                  {isActive && <ChevronRight className="w-3.5 h-3.5 text-indigo-400" />}
                </div>
              </button>
            );
          })}
        </nav>

        {/* Footer info */}
        <div className="p-3 border-t border-slate-800/80 bg-slate-950/50">
          <div className="px-2 py-2 rounded-lg bg-slate-900/60 border border-slate-800 text-[11px] text-slate-400 space-y-1">
            <div className="flex items-center justify-between">
              <span className="text-slate-500">Mode:</span>
              <span className="text-slate-300 font-mono">Single-user</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-slate-500">Active Phase:</span>
              <span className="text-indigo-400 font-medium">Phase 1 Active</span>
            </div>
          </div>
        </div>
      </aside>
    </>
  );
};
