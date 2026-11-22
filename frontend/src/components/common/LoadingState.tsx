import React from 'react';
import { Loader2 } from 'lucide-react';

interface LoadingStateProps {
  message?: string;
  subMessage?: string;
}

export const LoadingState: React.FC<LoadingStateProps> = ({
  message = 'Loading system diagnostics...',
  subMessage = 'Querying backend API and verifying PostgreSQL connectivity',
}) => {
  return (
    <div className="flex flex-col items-center justify-center py-16 px-4 text-center">
      <div className="relative mb-4">
        <div className="w-12 h-12 rounded-full border-2 border-indigo-500/20 animate-ping absolute inset-0" />
        <div className="w-12 h-12 rounded-xl bg-indigo-950/60 border border-indigo-500/30 flex items-center justify-center text-indigo-400">
          <Loader2 className="w-6 h-6 animate-spin" />
        </div>
      </div>
      <h3 className="text-sm font-semibold text-slate-200">{message}</h3>
      {subMessage && <p className="text-xs text-slate-400 mt-1 max-w-sm">{subMessage}</p>}
    </div>
  );
};
