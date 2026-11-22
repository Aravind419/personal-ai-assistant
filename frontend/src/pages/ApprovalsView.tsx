import React, { useState, useEffect, useCallback } from 'react';
import {
  ShieldAlert,
  ShieldCheck,
  CheckCircle2,
  XCircle,
  Clock,
  Ban,
  Search,
  RefreshCw,
  AlertTriangle,
  FileCode,
  Terminal,
  Info,
} from 'lucide-react';

import { toolService } from '../services/toolService';
import type { Approval, ApprovalStatus } from '../types/tool';

export const ApprovalsView: React.FC = () => {
  const [approvals, setApprovals] = useState<Approval[]>([]);
  const [activeTab, setActiveTab] = useState<string>('all');
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Modals & Inspection
  const [selectedApproval, setSelectedApproval] = useState<Approval | null>(null);
  const [actionModal, setActionModal] = useState<{
    type: 'approve' | 'reject';
    approval: Approval;
  } | null>(null);
  const [rejectReason, setRejectReason] = useState<string>('');
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [executionResult, setExecutionResult] = useState<any | null>(null);

  const fetchApprovals = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const statusParam = activeTab === 'all' ? undefined : activeTab;
      const data = await toolService.getApprovals({ status: statusParam });
      setApprovals(data);
    } catch (err: any) {
      setError(err?.message || 'Failed to fetch approval requests.');
    } finally {
      setIsLoading(false);
    }
  }, [activeTab]);

  useEffect(() => {
    fetchApprovals();
  }, [fetchApprovals]);

  const handleApproveConfirm = async () => {
    if (!actionModal) return;
    setIsSubmitting(true);
    try {
      const isCritical = actionModal.approval.permission_level === 'critical';
      const res = await toolService.approveAction(actionModal.approval.id, true, undefined, isCritical);
      setExecutionResult(res.execution || null);
      await fetchApprovals();
      if (!res.execution) {
        setActionModal(null);
      }
    } catch (err: any) {
      setError(err?.message || 'Failed to approve action.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleRejectConfirm = async () => {
    if (!actionModal) return;
    setIsSubmitting(true);
    try {
      await toolService.rejectAction(actionModal.approval.id, rejectReason || undefined);
      setActionModal(null);
      setRejectReason('');
      await fetchApprovals();
    } catch (err: any) {
      setError(err?.message || 'Failed to reject action.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const filteredApprovals = approvals.filter((app) => {
    if (!searchQuery.trim()) return true;
    const q = searchQuery.toLowerCase();
    return (
      app.tool_name.toLowerCase().includes(q) ||
      app.action.toLowerCase().includes(q) ||
      (app.target_resource && app.target_resource.toLowerCase().includes(q)) ||
      app.reason.toLowerCase().includes(q)
    );
  });

  const pendingCount = approvals.filter((a) => a.status === 'pending').length;
  const approvedCount = approvals.filter((a) => a.status === 'approved').length;
  const rejectedCount = approvals.filter((a) => a.status === 'rejected').length;
  const expiredCount = approvals.filter((a) => a.status === 'expired').length;

  const getRiskBadge = (level: string) => {
    switch (level.toLowerCase()) {
      case 'critical':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-semibold bg-rose-500/20 text-rose-300 border border-rose-500/30">
            <ShieldAlert className="w-3.5 h-3.5 text-rose-400" />
            Critical (Level 3)
          </span>
        );
      case 'sensitive':
      case 'medium':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-semibold bg-amber-500/20 text-amber-300 border border-amber-500/30">
            <AlertTriangle className="w-3.5 h-3.5 text-amber-400" />
            Sensitive (Level 2)
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-semibold bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
            <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
            Safe (Level 1)
          </span>
        );
    }
  };

  const getStatusBadge = (status: ApprovalStatus) => {
    switch (status) {
      case 'pending':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-semibold bg-amber-500/10 text-amber-400 border border-amber-500/30 animate-pulse">
            <Clock className="w-3 h-3" />
            Awaiting Approval
          </span>
        );
      case 'approved':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">
            <CheckCircle2 className="w-3 h-3" />
            Approved
          </span>
        );
      case 'rejected':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-semibold bg-rose-500/10 text-rose-400 border border-rose-500/30">
            <XCircle className="w-3 h-3" />
            Rejected
          </span>
        );
      case 'expired':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-semibold bg-slate-800 text-slate-400 border border-slate-700">
            <Clock className="w-3 h-3" />
            Expired
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-semibold bg-slate-800 text-slate-400 border border-slate-700">
            <Ban className="w-3 h-3" />
            Cancelled
          </span>
        );
    }
  };

  return (
    <div className="space-y-6 pb-12">
      {/* Page Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-800 pb-5">
        <div>
          <h1 className="text-2xl font-bold text-slate-100 flex items-center gap-2">
            <ShieldAlert className="w-6 h-6 text-amber-400" />
            Human-in-the-Loop Approvals
          </h1>
          <p className="text-sm text-slate-400 mt-1">
            Authoritative confirmation gateway for sensitive and critical assistant operations.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => fetchApprovals()}
            className="px-3 py-1.5 rounded-lg text-sm bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 flex items-center gap-1.5 transition-colors cursor-pointer"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin' : ''}`} />
            Refresh
          </button>
        </div>
      </div>

      {/* Metrics Banner */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800">
          <div className="text-xs font-medium text-slate-400">Pending Review</div>
          <div className="text-2xl font-bold text-amber-400 mt-1 flex items-center gap-2">
            {pendingCount}
            {pendingCount > 0 && <span className="w-2.5 h-2.5 rounded-full bg-amber-400 animate-ping" />}
          </div>
        </div>
        <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800">
          <div className="text-xs font-medium text-slate-400">Approved</div>
          <div className="text-2xl font-bold text-emerald-400 mt-1">{approvedCount}</div>
        </div>
        <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800">
          <div className="text-xs font-medium text-slate-400">Rejected</div>
          <div className="text-2xl font-bold text-rose-400 mt-1">{rejectedCount}</div>
        </div>
        <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800">
          <div className="text-xs font-medium text-slate-400">Expired / Cancelled</div>
          <div className="text-2xl font-bold text-slate-300 mt-1">{expiredCount}</div>
        </div>
      </div>

      {/* Filter Tabs & Search */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="flex items-center gap-1 p-1 bg-slate-900 border border-slate-800 rounded-lg overflow-x-auto">
          {[
            { id: 'all', label: 'All Requests' },
            { id: 'pending', label: `Pending (${pendingCount})` },
            { id: 'approved', label: 'Approved' },
            { id: 'rejected', label: 'Rejected' },
            { id: 'expired', label: 'Expired' },
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`px-3 py-1.5 rounded-md text-xs font-medium transition-colors whitespace-nowrap cursor-pointer ${
                activeTab === tab.id
                  ? 'bg-indigo-600 text-white shadow-sm'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        <div className="relative w-full md:w-72">
          <Search className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
          <input
            type="text"
            placeholder="Search by tool, resource, or action..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-9 pr-3 py-1.5 text-xs bg-slate-900 border border-slate-800 rounded-lg text-slate-200 placeholder-slate-500 focus:outline-none focus:border-indigo-500"
          />
        </div>
      </div>

      {/* Error Alert */}
      {error && (
        <div className="p-4 rounded-lg bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs flex items-center justify-between">
          <span>{error}</span>
          <button onClick={() => setError(null)} className="text-rose-400 hover:underline">
            Dismiss
          </button>
        </div>
      )}

      {/* Approvals List */}
      <div className="space-y-3">
        {isLoading ? (
          <div className="p-8 text-center text-sm text-slate-500 bg-slate-900/40 rounded-xl border border-slate-800">
            Loading approval requests...
          </div>
        ) : filteredApprovals.length === 0 ? (
          <div className="p-10 text-center bg-slate-900/30 rounded-xl border border-slate-800 space-y-2">
            <CheckCircle2 className="w-8 h-8 text-slate-600 mx-auto" />
            <div className="text-sm font-medium text-slate-300">No approval requests found</div>
            <p className="text-xs text-slate-500">
              {activeTab === 'pending'
                ? 'All actions have been reviewed or executed.'
                : 'No actions match the selected filter.'}
            </p>
          </div>
        ) : (
          filteredApprovals.map((app) => (
            <div
              key={app.id}
              className={`p-4 rounded-xl border transition-all ${
                app.status === 'pending'
                  ? 'bg-slate-900/90 border-amber-500/40 shadow-sm shadow-amber-500/5'
                  : 'bg-slate-900/50 border-slate-800 hover:border-slate-700'
              }`}
            >
              <div className="flex flex-col md:flex-row md:items-start justify-between gap-3">
                <div className="space-y-1.5 flex-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="text-sm font-semibold text-slate-100 flex items-center gap-1.5">
                      <Terminal className="w-4 h-4 text-indigo-400" />
                      {app.tool_name}
                    </span>
                    {getRiskBadge(app.permission_level)}
                    {getStatusBadge(app.status)}
                  </div>

                  <p className="text-xs text-slate-300 font-medium">{app.reason}</p>

                  {app.target_resource && (
                    <div className="text-xs text-slate-400 flex items-center gap-1.5">
                      <span className="text-slate-500">Target Resource:</span>
                      <code className="px-1.5 py-0.5 rounded bg-slate-800 font-mono text-slate-200">
                        {app.target_resource}
                      </code>
                    </div>
                  )}

                  {app.expected_consequences && (
                    <p className="text-xs text-amber-300/80 italic">
                      Expected Consequences: {app.expected_consequences}
                    </p>
                  )}

                  <div className="flex items-center gap-4 text-[11px] text-slate-500 pt-1">
                    <span>Requested: {new Date(app.created_at).toLocaleString()}</span>
                    <span>Expires: {new Date(app.expires_at).toLocaleString()}</span>
                    {app.decided_at && (
                      <span className="text-slate-400">
                        Decided: {new Date(app.decided_at).toLocaleString()} by {app.decided_by || 'user'}
                      </span>
                    )}
                  </div>
                </div>

                {/* Action Buttons */}
                <div className="flex items-center gap-2 shrink-0">
                  <button
                    onClick={() => setSelectedApproval(app)}
                    className="px-2.5 py-1.5 rounded-lg text-xs bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 flex items-center gap-1 cursor-pointer transition-colors"
                  >
                    <Info className="w-3.5 h-3.5" />
                    Details
                  </button>

                  {app.status === 'pending' && (
                    <>
                      <button
                        onClick={() => {
                          setExecutionResult(null);
                          setActionModal({ type: 'reject', approval: app });
                        }}
                        className="px-3 py-1.5 rounded-lg text-xs bg-rose-600/20 hover:bg-rose-600/30 text-rose-300 border border-rose-500/30 flex items-center gap-1 cursor-pointer transition-colors"
                      >
                        <XCircle className="w-3.5 h-3.5 text-rose-400" />
                        Reject
                      </button>
                      <button
                        onClick={() => {
                          setExecutionResult(null);
                          setActionModal({ type: 'approve', approval: app });
                        }}
                        className="px-3 py-1.5 rounded-lg text-xs font-semibold bg-emerald-600 hover:bg-emerald-500 text-white shadow-sm flex items-center gap-1 cursor-pointer transition-colors"
                      >
                        <CheckCircle2 className="w-3.5 h-3.5" />
                        Approve & Execute
                      </button>
                    </>
                  )}
                </div>
              </div>
            </div>
          ))
        )}
      </div>

      {/* Details Modal */}
      {selectedApproval && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm">
          <div className="w-full max-w-2xl bg-slate-900 border border-slate-800 rounded-xl shadow-2xl p-6 space-y-4 max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <h3 className="text-base font-bold text-slate-100 flex items-center gap-2">
                <FileCode className="w-5 h-5 text-indigo-400" />
                Approval Details: {selectedApproval.tool_name}
              </h3>
              <button
                onClick={() => setSelectedApproval(null)}
                className="text-slate-400 hover:text-slate-200 text-sm cursor-pointer"
              >
                ✕
              </button>
            </div>

            <div className="space-y-3 text-xs">
              <div className="grid grid-cols-2 gap-3">
                <div className="p-2.5 rounded-lg bg-slate-950 border border-slate-800">
                  <span className="text-slate-500 block">Approval ID</span>
                  <span className="font-mono text-slate-300">{selectedApproval.id}</span>
                </div>
                <div className="p-2.5 rounded-lg bg-slate-950 border border-slate-800">
                  <span className="text-slate-500 block">Arguments SHA-256 Hash</span>
                  <span className="font-mono text-slate-300 truncate block">
                    {selectedApproval.arguments_hash}
                  </span>
                </div>
              </div>

              <div>
                <span className="text-slate-400 font-semibold block mb-1">Exact Requested Arguments</span>
                <pre className="p-3 rounded-lg bg-slate-950 border border-slate-800 font-mono text-[11px] text-indigo-300 overflow-x-auto">
                  {JSON.stringify(selectedApproval.arguments, null, 2)}
                </pre>
              </div>

              {selectedApproval.decision_reason && (
                <div className="p-3 rounded-lg bg-slate-950 border border-slate-800">
                  <span className="text-slate-400 font-semibold block mb-0.5">Decision Note</span>
                  <p className="text-slate-300">{selectedApproval.decision_reason}</p>
                </div>
              )}
            </div>

            <div className="flex justify-end pt-3 border-t border-slate-800">
              <button
                onClick={() => setSelectedApproval(null)}
                className="px-4 py-2 rounded-lg text-xs bg-slate-800 hover:bg-slate-700 text-slate-200 cursor-pointer"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Confirmation Modal (Approve or Reject) */}
      {actionModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm">
          <div className="w-full max-w-lg bg-slate-900 border border-slate-800 rounded-xl shadow-2xl p-6 space-y-4">
            <div className="flex items-center gap-3">
              {actionModal.type === 'approve' ? (
                <div className="w-10 h-10 rounded-lg bg-emerald-500/20 text-emerald-400 flex items-center justify-center">
                  <CheckCircle2 className="w-6 h-6" />
                </div>
              ) : (
                <div className="w-10 h-10 rounded-lg bg-rose-500/20 text-rose-400 flex items-center justify-center">
                  <XCircle className="w-6 h-6" />
                </div>
              )}
              <div>
                <h3 className="text-base font-bold text-slate-100">
                  {actionModal.type === 'approve' ? 'Confirm Action Approval' : 'Reject Action Request'}
                </h3>
                <p className="text-xs text-slate-400">
                  Tool: <code className="text-indigo-300 font-mono">{actionModal.approval.tool_name}</code>
                </p>
              </div>
            </div>

            {actionModal.approval.permission_level === 'critical' && actionModal.type === 'approve' && (
              <div className="p-3 rounded-lg bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs flex items-start gap-2">
                <AlertTriangle className="w-4 h-4 text-rose-400 shrink-0 mt-0.5" />
                <div>
                  <strong className="block font-semibold">CRITICAL LEVEL 3 ACTION</strong>
                  This action involves destructive modifications or sensitive operations that cannot be undone.
                </div>
              </div>
            )}

            <div className="p-3 rounded-lg bg-slate-950 border border-slate-800 text-xs space-y-1.5">
              <div className="text-slate-400">
                Reason: <span className="text-slate-200">{actionModal.approval.reason}</span>
              </div>
              {actionModal.approval.target_resource && (
                <div className="text-slate-400">
                  Target: <span className="text-indigo-300 font-mono">{actionModal.approval.target_resource}</span>
                </div>
              )}
            </div>

            {actionModal.type === 'reject' && (
              <div className="space-y-1">
                <label className="text-xs font-medium text-slate-300">Rejection Reason (Optional)</label>
                <input
                  type="text"
                  placeholder="e.g. Unintended operation or incorrect arguments"
                  value={rejectReason}
                  onChange={(e) => setRejectReason(e.target.value)}
                  className="w-full px-3 py-2 text-xs bg-slate-950 border border-slate-800 rounded-lg text-slate-200 focus:outline-none focus:border-rose-500"
                />
              </div>
            )}

            {executionResult && (
              <div className="p-3 rounded-lg bg-emerald-500/10 border border-emerald-500/30 text-xs space-y-1">
                <div className="font-semibold text-emerald-400 flex items-center gap-1.5">
                  <CheckCircle2 className="w-4 h-4" />
                  Execution Completed Successfully!
                </div>
                <pre className="text-[11px] font-mono text-emerald-200 bg-slate-950 p-2 rounded max-h-32 overflow-y-auto">
                  {JSON.stringify(executionResult.result, null, 2)}
                </pre>
              </div>
            )}

            <div className="flex justify-end gap-2 pt-2 border-t border-slate-800">
              <button
                onClick={() => setActionModal(null)}
                disabled={isSubmitting}
                className="px-3 py-1.5 rounded-lg text-xs bg-slate-800 hover:bg-slate-700 text-slate-300 cursor-pointer"
              >
                {executionResult ? 'Close' : 'Cancel'}
              </button>

              {!executionResult && actionModal.type === 'approve' && (
                <button
                  onClick={handleApproveConfirm}
                  disabled={isSubmitting}
                  className="px-4 py-1.5 rounded-lg text-xs font-semibold bg-emerald-600 hover:bg-emerald-500 text-white cursor-pointer flex items-center gap-1"
                >
                  {isSubmitting ? 'Executing...' : 'Confirm & Execute'}
                </button>
              )}

              {!executionResult && actionModal.type === 'reject' && (
                <button
                  onClick={handleRejectConfirm}
                  disabled={isSubmitting}
                  className="px-4 py-1.5 rounded-lg text-xs font-semibold bg-rose-600 hover:bg-rose-500 text-white cursor-pointer"
                >
                  {isSubmitting ? 'Rejecting...' : 'Confirm Rejection'}
                </button>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
