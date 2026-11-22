import type { ReactNode } from 'react';
import { Inbox } from 'lucide-react';

interface EmptyStateProps {
  title: string;
  description: string;
  icon?: ReactNode;
  action?: ReactNode;
}

export const EmptyState: React.FC<EmptyStateProps> = ({
  title,
  description,
  icon,
  action,
}) => {
  return (
    <div className="flex flex-col items-center justify-center p-10 text-center rounded-xl border border-dashed border-slate-800 bg-slate-900/30">
      <div className="p-3 rounded-xl bg-slate-800/60 text-slate-400 mb-3 border border-slate-700/50">
        {icon || <Inbox className="w-6 h-6" />}
      </div>
      <h4 className="text-sm font-semibold text-slate-200">{title}</h4>
      <p className="mt-1 text-xs text-slate-400 max-w-sm leading-relaxed">{description}</p>
      {action && <div className="mt-4">{action}</div>}
    </div>
  );
};
