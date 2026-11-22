import type { NavItemConfig } from '../../types/navigation';
import { Layers, ShieldAlert, GitBranch } from 'lucide-react';

interface PlaceholderViewProps {
  item: NavItemConfig;
}

export const PlaceholderView: React.FC<PlaceholderViewProps> = ({ item }) => {
  return (
    <div className="space-y-6 max-w-4xl">
      {/* Title section */}
      <div className="border-b border-slate-800 pb-5">
        <div className="flex items-center gap-3">
          <h2 className="text-2xl font-bold tracking-tight text-white">{item.label}</h2>
          <span className="px-2.5 py-0.5 rounded-full text-xs font-medium bg-amber-950/80 text-amber-300 border border-amber-800/60">
            {item.phasePlanned} Placeholder
          </span>
        </div>
        <p className="mt-1 text-sm text-slate-400">{item.description}</p>
      </div>

      {/* Scope banner */}
      <div className="p-4 rounded-xl border border-slate-800 bg-slate-900/60 flex items-start gap-3">
        <ShieldAlert className="w-5 h-5 text-amber-400 shrink-0 mt-0.5" />
        <div className="text-xs text-slate-300 space-y-1">
          <p className="font-semibold text-slate-200">Phase 0 Architectural Scope Limitation</p>
          <p className="leading-relaxed">
            This module is reserved for <span className="text-amber-300 font-medium">{item.phasePlanned}</span>. Per
            project principles, no mock executions or fake AI responses are implemented in Phase 0.
            The navigation placeholder establishes the information architecture and UI layout.
          </p>
        </div>
      </div>

      {/* Specification Card */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="p-5 rounded-xl border border-slate-800/80 bg-slate-900/40 space-y-3">
          <div className="flex items-center gap-2 text-indigo-400 font-medium text-sm">
            <Layers className="w-4 h-4" />
            <span>Target Responsibilities</span>
          </div>
          <p className="text-xs text-slate-400 leading-relaxed">
            When implemented in {item.phasePlanned}, this interface will connect to dedicated backend
            services and orchestration workflows.
          </p>
          <div className="pt-2 border-t border-slate-800 text-xs text-slate-500">
            Status: <span className="text-slate-400 font-mono">Not Initialized</span>
          </div>
        </div>

        <div className="p-5 rounded-xl border border-slate-800/80 bg-slate-900/40 space-y-3">
          <div className="flex items-center gap-2 text-emerald-400 font-medium text-sm">
            <GitBranch className="w-4 h-4" />
            <span>Architectural Prerequisite</span>
          </div>
          <p className="text-xs text-slate-400 leading-relaxed">
            Requires completion and verification of the Phase 0 foundational layer (FastAPI, PostgreSQL schema,
            and configuration).
          </p>
          <div className="pt-2 border-t border-slate-800 text-xs text-slate-500">
            Prerequisite: <span className="text-emerald-400 font-mono">Phase 0 Foundation (Active)</span>
          </div>
        </div>
      </div>
    </div>
  );
};
