import React from 'react';
import { AlertTriangle, RefreshCw } from 'lucide-react';

interface ErrorStateProps {
  title?: string;
  message: string;
  onRetry?: () => void;
  details?: string;
}

export const ErrorState: React.FC<ErrorStateProps> = ({
  title = 'Service Communication Failure',
  message,
  onRetry,
  details,
}) => {
  return (
    <div className="rounded-xl border border-rose-900/50 bg-rose-950/20 p-6 text-slate-200">
      <div className="flex items-start gap-4">
        <div className="p-2.5 rounded-lg bg-rose-900/30 text-rose-400 border border-rose-800/50">
          <AlertTriangle className="w-5 h-5" />
        </div>
        <div className="flex-1 min-w-0">
          <h3 className="text-base font-semibold text-rose-300">{title}</h3>
          <p className="mt-1 text-sm text-slate-300 leading-relaxed">{message}</p>
          {details && (
            <div className="mt-3 p-3 rounded-lg bg-slate-950/80 border border-rose-950 text-xs font-mono text-rose-300 overflow-x-auto">
              {details}
            </div>
          )}
          {onRetry && (
            <div className="mt-4">
              <button
                onClick={onRetry}
                className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-lg bg-rose-900/40 hover:bg-rose-900/60 border border-rose-700/50 text-xs font-medium text-rose-200 transition-colors shadow-sm cursor-pointer"
              >
                <RefreshCw className="w-3.5 h-3.5" />
                <span>Retry Connection</span>
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
