import React from 'react';

interface StatusBadgeProps {
  status: 'healthy' | 'degraded' | 'connected' | 'disconnected' | 'active' | 'disabled' | 'error' | string;
  label?: string;
  size?: 'sm' | 'md';
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({ status, label, size = 'md' }) => {
  const norm = status.toLowerCase();

  let colorClasses = 'bg-slate-800 text-slate-300 border-slate-700';
  let dotColor = 'bg-slate-400';

  if (norm === 'healthy' || norm === 'connected' || norm === 'active') {
    colorClasses = 'bg-emerald-950/70 text-emerald-300 border-emerald-800/60';
    dotColor = 'bg-emerald-400 shadow-emerald-500/50 shadow-sm animate-pulse';
  } else if (norm === 'degraded' || norm === 'warning') {
    colorClasses = 'bg-amber-950/70 text-amber-300 border-amber-800/60';
    dotColor = 'bg-amber-400';
  } else if (norm === 'disconnected' || norm === 'error' || norm === 'failed') {
    colorClasses = 'bg-rose-950/70 text-rose-300 border-rose-800/60';
    dotColor = 'bg-rose-400';
  } else if (norm.includes('disabled') || norm === 'pending') {
    colorClasses = 'bg-slate-900 text-slate-400 border-slate-800';
    dotColor = 'bg-slate-500';
  }

  const paddingClasses = size === 'sm' ? 'px-2 py-0.5 text-xs' : 'px-2.5 py-1 text-xs font-medium';

  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full border ${paddingClasses} ${colorClasses} tracking-wide transition-colors`}
    >
      <span className={`w-1.5 h-1.5 rounded-full ${dotColor}`} />
      <span>{label || status}</span>
    </span>
  );
};
