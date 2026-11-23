import React, { useState, useEffect, useCallback } from 'react';
import {
  Plug,
  CheckCircle2,
  XCircle,
  RefreshCw,
  Mail,
  Calendar,
  HardDrive,
  GitBranch,
  FileText,
  Table,
  Presentation,
  CheckSquare,
  Users,
  Search,
  ExternalLink,
  AlertTriangle,
  KeyRound,
  X,
  Sparkles,
} from 'lucide-react';
import { automationService } from '../services/automationService';
import type { IntegrationStatus, IntegrationStatusType } from '../types/automations';

export const IntegrationsView: React.FC = () => {
  const [integrations, setIntegrations] = useState<IntegrationStatus[]>([]);
  const [categories, setCategories] = useState<{ id: string; label: string }[]>([]);
  const [selectedCategory, setSelectedCategory] = useState<string>('all');
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [actionNotice, setActionNotice] = useState<{ type: 'success' | 'error' | 'info'; message: string } | null>(null);
  const [activeActionId, setActiveActionId] = useState<string | null>(null);
  const [detailModalService, setDetailModalService] = useState<IntegrationStatus | null>(null);
  const [configModalService, setConfigModalService] = useState<IntegrationStatus | null>(null);
  const [sendTestModalOpen, setSendTestModalOpen] = useState<boolean>(false);
  const [testEmailRecipient, setTestEmailRecipient] = useState<string>('');
  const [testEmailSubject, setTestEmailSubject] = useState<string>('');
  const [testEmailBody, setTestEmailBody] = useState<string>('');
  const [testEmailPreview, setTestEmailPreview] = useState<any | null>(null);
  const [testEmailResult, setTestEmailResult] = useState<any | null>(null);
  const [isSendingEmail, setIsSendingEmail] = useState<boolean>(false);

  const handlePreviewEmail = async () => {
    if (!testEmailRecipient.trim()) return;
    setIsSendingEmail(true);
    setTestEmailResult(null);
    try {
      const res = await automationService.sendTestEmail({
        recipient_email: testEmailRecipient.trim(),
        confirm: false,
        subject: testEmailSubject.trim() || undefined,
        body_text: testEmailBody.trim() || undefined,
      });
      setTestEmailPreview(res);
    } catch (err: any) {
      setTestEmailResult({ error: err?.message || 'Failed to preview test email.' });
    } finally {
      setIsSendingEmail(false);
    }
  };

  const handleConfirmSendEmail = async () => {
    if (!testEmailRecipient.trim()) return;
    setIsSendingEmail(true);
    try {
      const res = await automationService.sendTestEmail({
        recipient_email: testEmailRecipient.trim(),
        confirm: true,
        subject: testEmailSubject.trim() || undefined,
        body_text: testEmailBody.trim() || undefined,
      });
      setTestEmailResult(res);
      setTestEmailPreview(null);
      setActionNotice({
        type: 'success',
        message: `Verified test email sent to ${testEmailRecipient}! Message ID: ${res.message_id}`,
      });
    } catch (err: any) {
      setTestEmailResult({ error: err?.message || 'Failed to send test email.' });
    } finally {
      setIsSendingEmail(false);
    }
  };

  const fetchIntegrations = useCallback(async () => {
    setIsLoading(true);
    try {
      const [intData, catData] = await Promise.all([
        automationService.listIntegrations(selectedCategory, searchQuery),
        automationService.listCategories().catch(() => [
          { id: 'all', label: 'All Services' },
          { id: 'google', label: 'Google Workspace' },
          { id: 'developer', label: 'Developer Tools' },
          { id: 'communication', label: 'Communication' },
          { id: 'productivity', label: 'Productivity' },
          { id: 'storage', label: 'Storage' },
          { id: 'design', label: 'Design & Media' },
        ]),
      ]);
      setIntegrations(intData);
      setCategories(catData);
    } catch (err: any) {
      setActionNotice({ type: 'error', message: err?.message || 'Failed to load integrations.' });
    } finally {
      setIsLoading(false);
    }
  }, [selectedCategory, searchQuery]);

  useEffect(() => {
    fetchIntegrations();
  }, [fetchIntegrations]);

  // Listen for OAuth postMessage callback from auth popup
  useEffect(() => {
    const handleOAuthMessage = (event: MessageEvent) => {
      if (event.data?.type === 'OAUTH_SUCCESS') {
        setActionNotice({
          type: 'success',
          message: `Connected ${event.data.provider || 'service'} successfully! Account: ${event.data.email || 'Verified'}.`,
        });
        fetchIntegrations();
      }
    };
    window.addEventListener('message', handleOAuthMessage);
    return () => window.removeEventListener('message', handleOAuthMessage);
  }, [fetchIntegrations]);

  const handleConnect = async (service: IntegrationStatus) => {
    const sId = service.service_id || service.provider_id || '';
    if (!service.is_configured) {
      setConfigModalService(service);
      return;
    }

    setActiveActionId(sId);
    try {
      const authData = await automationService.getAuthUrl(sId);
      if (authData.authorization_url) {
        // Open official provider OAuth consent window
        const authWindow = window.open(
          authData.authorization_url,
          'oauth_popup',
          'width=600,height=700,status=no,toolbar=no,menubar=no'
        );
        if (!authWindow) {
          // If popup blocked, open in regular tab
          window.open(authData.authorization_url, '_blank');
        }
        setActionNotice({
          type: 'info',
          message: `Opened official ${service.service_name} authorization consent screen in new window. Complete sign-in to connect.`,
        });
      }
    } catch (err: any) {
      setActionNotice({ type: 'error', message: err?.message || 'Connection initiation failed.' });
    } finally {
      setActiveActionId(null);
    }
  };

  const handleTest = async (service: IntegrationStatus) => {
    const sId = service.service_id || service.provider_id || '';
    setActiveActionId(sId);
    try {
      const res = await automationService.testIntegration(sId);
      if (res.connected) {
        setActionNotice({
          type: 'success',
          message: `✓ ${service.service_name} API verified live and responding normally.`,
        });
      } else {
        setActionNotice({
          type: 'error',
          message: `API check failed for ${service.service_name}: ${res.error || 'Unknown error'}`,
        });
      }
      fetchIntegrations();
    } catch (err: any) {
      setActionNotice({ type: 'error', message: err?.message || 'Test failed.' });
    } finally {
      setActiveActionId(null);
    }
  };

  const handleDisconnect = async (service: IntegrationStatus) => {
    const sId = service.service_id || service.provider_id || '';
    if (!confirm(`Are you sure you want to disconnect ${service.service_name}? All encrypted tokens will be permanently erased.`)) {
      return;
    }
    setActiveActionId(sId);
    try {
      await automationService.disconnectIntegration(sId);
      setActionNotice({ type: 'success', message: `Disconnected ${service.service_name} and erased encrypted credentials.` });
      fetchIntegrations();
    } catch (err: any) {
      setActionNotice({ type: 'error', message: err?.message || 'Failed to disconnect.' });
    } finally {
      setActiveActionId(null);
    }
  };

  const renderServiceIcon = (iconName: string) => {
    const iconClass = 'w-5 h-5';
    switch (iconName) {
      case 'mail':
        return <Mail className={`${iconClass} text-rose-400`} />;
      case 'hard-drive':
        return <HardDrive className={`${iconClass} text-amber-400`} />;
      case 'calendar':
        return <Calendar className={`${iconClass} text-blue-400`} />;
      case 'file-text':
        return <FileText className={`${iconClass} text-indigo-400`} />;
      case 'table':
        return <Table className={`${iconClass} text-emerald-400`} />;
      case 'presentation':
        return <Presentation className={`${iconClass} text-amber-500`} />;
      case 'check-square':
        return <CheckSquare className={`${iconClass} text-teal-400`} />;
      case 'users':
        return <Users className={`${iconClass} text-cyan-400`} />;
      case 'git-branch':
        return <GitBranch className={`${iconClass} text-violet-400`} />;
      default:
        return <Plug className={`${iconClass} text-slate-400`} />;
    }
  };

  const getStatusBadge = (status: IntegrationStatusType, isConfigured: boolean) => {
    if (!isConfigured) {
      return (
        <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-amber-950/60 text-amber-300 border border-amber-800/60">
          <AlertTriangle className="w-3 h-3 text-amber-400" />
          Configuration Required
        </span>
      );
    }
    switch (status) {
      case 'connected':
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-emerald-950/60 text-emerald-300 border border-emerald-800/60">
            <CheckCircle2 className="w-3 h-3 text-emerald-400" />
            Connected & Verified
          </span>
        );
      case 'connected_with_limited_scopes':
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-yellow-950/60 text-yellow-300 border border-yellow-800/60">
            <AlertTriangle className="w-3 h-3 text-yellow-400" />
            Limited Scopes
          </span>
        );
      case 'token_expired':
      case 'reauthorization_required':
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-rose-950/60 text-rose-300 border border-rose-800/60">
            <XCircle className="w-3 h-3 text-rose-400" />
            Reauthorization Required
          </span>
        );
      case 'connection_error':
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-rose-950/60 text-rose-300 border border-rose-800/60">
            <XCircle className="w-3 h-3 text-rose-400" />
            Connection Error
          </span>
        );
      case 'planned':
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-slate-800 text-slate-300 border border-slate-700">
            <Sparkles className="w-3 h-3 text-indigo-400" />
            Planned
          </span>
        );
      case 'disconnected':
      case 'not_connected':
      default:
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-slate-800/80 text-slate-400 border border-slate-700">
            <span className="w-1.5 h-1.5 rounded-full bg-slate-500" />
            Not Connected
          </span>
        );
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-bold tracking-tight text-white">External Integrations</h1>
            <span className="px-2 py-0.5 rounded text-xs font-semibold bg-emerald-950 text-emerald-300 border border-emerald-800">
              Live APIs
            </span>
          </div>
          <p className="text-slate-400 text-sm mt-1">
            Connect individual Google Workspace services, developer tools, and communication APIs with encrypted OAuth tokens.
          </p>
        </div>

        <button
          onClick={fetchIntegrations}
          disabled={isLoading}
          className="p-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white border border-slate-700 transition-colors cursor-pointer self-start sm:self-auto"
          title="Refresh connections"
        >
          <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />
        </button>
      </div>

      {/* Action Notice Alert */}
      {actionNotice && (
        <div
          className={`p-3.5 rounded-lg text-sm flex items-center justify-between border ${
            actionNotice.type === 'success'
              ? 'bg-emerald-950/40 text-emerald-200 border-emerald-800/60'
              : actionNotice.type === 'info'
              ? 'bg-blue-950/40 text-blue-200 border-blue-800/60'
              : 'bg-rose-950/40 text-rose-200 border-rose-800/60'
          }`}
        >
          <span>{actionNotice.message}</span>
          <button onClick={() => setActionNotice(null)} className="text-slate-400 hover:text-white cursor-pointer ml-4">
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

      {/* Security & Zero-Mock Guarantee Banner */}
      <div className="p-4 rounded-xl bg-slate-900 border border-slate-800 flex items-start gap-3">
        <KeyRound className="w-5 h-5 text-emerald-400 shrink-0 mt-0.5" />
        <div className="text-xs text-slate-300 space-y-1">
          <p className="font-semibold text-white flex items-center gap-2">
            <span>Real OAuth Authorization & Fernet Symmetric Encryption</span>
            <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-emerald-950/80 text-emerald-300 border border-emerald-800/60">
              Zero Mock Guarantee
            </span>
          </p>
          <p>
            Each service authenticates via official OAuth 2.0 authorization code flows.
            Tokens are stored encrypted at rest via AES-256 (Fernet) keys derived from your SECRET_KEY.
            Services are marked connected only after real provider API health checks succeed.
          </p>
        </div>
      </div>

      {/* Search & Category Filter */}
      <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3">
        {/* Category Pills */}
        <div className="flex items-center gap-1.5 overflow-x-auto pb-1 sm:pb-0 scrollbar-none">
          {categories.map((cat) => (
            <button
              key={cat.id}
              onClick={() => setSelectedCategory(cat.id)}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium whitespace-nowrap transition-colors cursor-pointer ${
                selectedCategory === cat.id
                  ? 'bg-indigo-600 text-white shadow-sm'
                  : 'bg-slate-800/80 hover:bg-slate-800 text-slate-300 border border-slate-700/60'
              }`}
            >
              {cat.label}
            </button>
          ))}
        </div>

        {/* Search Input */}
        <div className="relative min-w-[220px]">
          <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            placeholder="Search integrations & tools..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-9 pr-3 py-1.5 rounded-lg bg-slate-900 border border-slate-700/80 text-slate-200 placeholder-slate-500 text-xs focus:outline-none focus:border-indigo-500 transition-colors"
          />
        </div>
      </div>

      {/* Services Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
        {integrations.map((item) => {
          const sId = item.service_id || item.provider_id || '';
          const isConnected = item.status === 'connected';
          const isBusy = activeActionId === sId;
          const isPlanned = item.status === 'planned';

          return (
            <div
              key={sId}
              className={`flex flex-col justify-between rounded-xl bg-slate-900 border transition-all ${
                isConnected
                  ? 'border-emerald-800/60 shadow-sm shadow-emerald-950/20'
                  : 'border-slate-800 hover:border-slate-700'
              }`}
            >
              {/* Card Header & Content */}
              <div className="p-5 space-y-4">
                <div className="flex items-start justify-between gap-3">
                  <div className="flex items-center gap-3">
                    <div className="p-2.5 rounded-lg bg-slate-800/90 border border-slate-700/60">
                      {renderServiceIcon(item.icon_name)}
                    </div>
                    <div>
                      <h3 className="font-semibold text-white text-base leading-tight">{item.service_name}</h3>
                      <p className="text-xs text-slate-400 capitalize mt-0.5">{item.category}</p>
                    </div>
                  </div>
                  {getStatusBadge(item.status, item.is_configured)}
                </div>

                <p className="text-xs text-slate-400 line-clamp-2 leading-relaxed">
                  {item.description}
                </p>

                {/* Account Identity when connected */}
                {isConnected && item.account_identity && (
                  <div className="px-3 py-2 rounded-lg bg-slate-950/60 border border-slate-800 text-xs flex items-center justify-between">
                    <span className="text-slate-400">Account:</span>
                    <span className="font-medium text-emerald-400 truncate ml-2 max-w-[180px]">
                      {item.account_identity}
                    </span>
                  </div>
                )}

                {/* Error Banner when in error or expired state */}
                {item.last_error && !isPlanned && (
                  <div className="px-3 py-2 rounded-lg bg-rose-950/40 border border-rose-900/60 text-xs text-rose-300">
                    <p className="font-medium text-rose-200">Attention Required</p>
                    <p className="mt-0.5 line-clamp-2 text-[11px] text-rose-300/80">{item.last_error}</p>
                  </div>
                )}

                {/* Capabilities Preview */}
                <div className="space-y-1.5 pt-1">
                  <p className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">Capabilities</p>
                  <ul className="space-y-1">
                    {item.capabilities.slice(0, 3).map((cap, i) => (
                      <li key={i} className="text-xs text-slate-300 flex items-center gap-2">
                        <CheckCircle2 className="w-3 h-3 text-emerald-500 shrink-0" />
                        <span className="truncate">{cap}</span>
                      </li>
                    ))}
                    {item.capabilities.length > 3 && (
                      <li className="text-[11px] text-indigo-400">
                        +{item.capabilities.length - 3} more tools supported
                      </li>
                    )}
                  </ul>
                </div>
              </div>

              {/* Card Footer Actions */}
              <div className="p-4 pt-3 border-t border-slate-800/80 bg-slate-900/40 rounded-b-xl flex items-center justify-between gap-2">
                <button
                  onClick={() => setDetailModalService(item)}
                  className="text-xs text-slate-400 hover:text-slate-200 font-medium cursor-pointer transition-colors"
                >
                  Details
                </button>

                <div className="flex items-center gap-2">
                  {isPlanned ? (
                    <span className="text-xs text-slate-500 italic">Upcoming</span>
                  ) : !item.is_configured ? (
                    <button
                      onClick={() => setConfigModalService(item)}
                      className="px-3 py-1.5 rounded-lg text-xs font-semibold bg-amber-500/10 hover:bg-amber-500/20 text-amber-300 border border-amber-500/30 transition-colors cursor-pointer flex items-center gap-1.5"
                    >
                      <AlertTriangle className="w-3 h-3" />
                      Configure
                    </button>
                  ) : isConnected ? (
                    <>
                      {sId === 'google_gmail' && (
                        <button
                          onClick={() => {
                            setSendTestModalOpen(true);
                            setTestEmailRecipient(item.account_identity || '');
                            setTestEmailResult(null);
                            setTestEmailPreview(null);
                          }}
                          className="px-2.5 py-1.5 rounded-lg text-xs font-semibold bg-indigo-600/20 hover:bg-indigo-600/30 text-indigo-300 border border-indigo-500/30 transition-colors cursor-pointer flex items-center gap-1"
                          title="Send verified test email via official Gmail API"
                        >
                          <Mail className="w-3 h-3" />
                          Send Test
                        </button>
                      )}
                      <button
                        onClick={() => handleTest(item)}
                        disabled={isBusy}
                        className="px-2.5 py-1.5 rounded-lg text-xs font-medium bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 transition-colors cursor-pointer flex items-center gap-1"
                        title="Run real API health probe"
                      >
                        <RefreshCw className={`w-3 h-3 ${isBusy ? 'animate-spin' : ''}`} />
                        Test
                      </button>
                      <button
                        onClick={() => handleDisconnect(item)}
                        disabled={isBusy}
                        className="px-2.5 py-1.5 rounded-lg text-xs font-medium bg-rose-950/30 hover:bg-rose-900/50 text-rose-300 border border-rose-800/50 transition-colors cursor-pointer"
                      >
                        Disconnect
                      </button>
                    </>
                  ) : (
                    <button
                      onClick={() => handleConnect(item)}
                      disabled={isBusy}
                      className="px-3.5 py-1.5 rounded-lg text-xs font-semibold bg-indigo-600 hover:bg-indigo-500 text-white shadow-sm transition-colors cursor-pointer flex items-center gap-1.5"
                    >
                      {isBusy ? <RefreshCw className="w-3 h-3 animate-spin" /> : <ExternalLink className="w-3 h-3" />}
                      Connect
                    </button>
                  )}
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Configuration Instructions Modal */}
      {configModalService && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-lg w-full p-6 shadow-2xl space-y-4">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <div className="flex items-center gap-2">
                <AlertTriangle className="w-5 h-5 text-amber-400" />
                <h3 className="font-semibold text-white text-base">
                  Configure {configModalService.service_name} Credentials
                </h3>
              </div>
              <button onClick={() => setConfigModalService(null)} className="text-slate-400 hover:text-white cursor-pointer">
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="space-y-3 text-xs text-slate-300 leading-relaxed">
              <p>
                To connect <strong className="text-white">{configModalService.service_name}</strong>, you must register an OAuth application in the provider's developer console and add the credentials to your backend environment.
              </p>

              {configModalService.provider_family === 'google' ? (
                <div className="p-3.5 rounded-xl bg-slate-950 border border-slate-800 space-y-2 font-mono text-[11px]">
                  <p className="text-amber-400 font-sans font-semibold">Google Cloud Setup Checklist:</p>
                  <ol className="list-decimal pl-4 space-y-1 text-slate-300 font-sans">
                    <li>Create a project in <strong>Google Cloud Console</strong>.</li>
                    <li>Enable Gmail, Google Drive, Google Calendar, and Docs APIs.</li>
                    <li>Configure OAuth Consent Screen (add test user if in Testing mode).</li>
                    <li>Create an <strong>OAuth 2.0 Web Application</strong> credential.</li>
                    <li>Set Authorized redirect URI to: <code className="text-indigo-300">http://localhost:8000/api/v1/integrations/google/callback</code></li>
                    <li>Add the following keys to <code className="text-emerald-400">backend/.env</code>:</li>
                  </ol>
                  <div className="p-2 rounded bg-slate-900 border border-slate-800 text-slate-200">
                    GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com<br />
                    GOOGLE_CLIENT_SECRET=GOCSPX-your-client-secret
                  </div>
                </div>
              ) : (
                <div className="p-3.5 rounded-xl bg-slate-950 border border-slate-800 space-y-2 font-mono text-[11px]">
                  <p className="text-amber-400 font-sans font-semibold">GitHub OAuth Setup Checklist:</p>
                  <ol className="list-decimal pl-4 space-y-1 text-slate-300 font-sans">
                    <li>Go to GitHub Settings &gt; Developer settings &gt; OAuth Apps.</li>
                    <li>Register a new OAuth Application.</li>
                    <li>Set Authorization callback URL to: <code className="text-indigo-300">http://localhost:8000/api/v1/integrations/github/callback</code></li>
                    <li>Add the keys to <code className="text-emerald-400">backend/.env</code>:</li>
                  </ol>
                  <div className="p-2 rounded bg-slate-900 border border-slate-800 text-slate-200">
                    GITHUB_CLIENT_ID=your-github-client-id<br />
                    GITHUB_CLIENT_SECRET=your-github-client-secret
                  </div>
                </div>
              )}

              <p className="text-slate-400">
                Detailed step-by-step guides are available in <code className="text-indigo-300">docs/integrations/GOOGLE_SETUP.md</code>.
              </p>
            </div>

            <div className="pt-2 flex justify-end">
              <button
                onClick={() => setConfigModalService(null)}
                className="px-4 py-2 rounded-lg text-xs font-semibold bg-slate-800 hover:bg-slate-700 text-white transition-colors cursor-pointer"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Service Detail Modal */}
      {detailModalService && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-lg w-full p-6 shadow-2xl space-y-4">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-lg bg-slate-800">
                  {renderServiceIcon(detailModalService.icon_name)}
                </div>
                <div>
                  <h3 className="font-semibold text-white text-base">{detailModalService.service_name}</h3>
                  <p className="text-xs text-slate-400 capitalize">{detailModalService.category} Integration</p>
                </div>
              </div>
              <button onClick={() => setDetailModalService(null)} className="text-slate-400 hover:text-white cursor-pointer">
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="space-y-4 text-xs text-slate-300">
              <div className="p-3 rounded-lg bg-slate-950 border border-slate-800 space-y-1">
                <p className="text-slate-400">Status:</p>
                <div className="flex items-center justify-between">
                  {getStatusBadge(detailModalService.status, detailModalService.is_configured)}
                  {detailModalService.account_identity && (
                    <span className="text-emerald-400 font-medium">{detailModalService.account_identity}</span>
                  )}
                </div>
              </div>

              <div>
                <p className="font-semibold text-slate-200 uppercase tracking-wider text-[11px] mb-1.5">
                  Supported Agent Tools
                </p>
                <div className="grid grid-cols-1 gap-1.5">
                  {detailModalService.capabilities.map((cap, i) => (
                    <div key={i} className="flex items-center gap-2 p-2 rounded bg-slate-800/40 border border-slate-800">
                      <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
                      <span>{cap}</span>
                    </div>
                  ))}
                </div>
              </div>

              {detailModalService.required_scopes.length > 0 && (
                <div>
                  <p className="font-semibold text-slate-200 uppercase tracking-wider text-[11px] mb-1.5">
                    OAuth Scopes Required
                  </p>
                  <div className="p-2.5 rounded-lg bg-slate-950 border border-slate-800 font-mono text-[10px] space-y-1 text-slate-400 overflow-x-auto">
                    {detailModalService.required_scopes.map((s, idx) => (
                      <p key={idx} className="truncate">{s}</p>
                    ))}
                  </div>
                </div>
              )}
            </div>

            <div className="pt-2 flex justify-end">
              <button
                onClick={() => setDetailModalService(null)}
                className="px-4 py-2 rounded-lg text-xs font-semibold bg-slate-800 hover:bg-slate-700 text-white transition-colors cursor-pointer"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Send Test Email Modal */}
      {sendTestModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-lg w-full p-6 shadow-2xl space-y-4">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <div className="flex items-center gap-2">
                <Mail className="w-5 h-5 text-indigo-400" />
                <h3 className="font-semibold text-white text-base">Send Verified Test Email</h3>
              </div>
              <button
                onClick={() => {
                  setSendTestModalOpen(false);
                  setTestEmailPreview(null);
                  setTestEmailResult(null);
                }}
                className="text-slate-400 hover:text-white cursor-pointer"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <p className="text-xs text-slate-300">
              Execute a real, end-to-end outbound email test using your authenticated Gmail connection and official Google REST API.
            </p>

            <div className="space-y-3 text-xs">
              <div>
                <label className="block text-slate-400 mb-1 font-medium">Recipient Email Address *</label>
                <input
                  type="email"
                  placeholder="e.g. your-email@gmail.com"
                  value={testEmailRecipient}
                  onChange={(e) => setTestEmailRecipient(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg bg-slate-950 border border-slate-800 text-slate-200 text-xs focus:outline-none focus:border-indigo-500 font-mono"
                />
              </div>

              <div>
                <label className="block text-slate-400 mb-1 font-medium">Subject (Optional)</label>
                <input
                  type="text"
                  placeholder="Personal AI Assistant — Verified Integration Test Email"
                  value={testEmailSubject}
                  onChange={(e) => setTestEmailSubject(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg bg-slate-950 border border-slate-800 text-slate-200 text-xs focus:outline-none focus:border-indigo-500"
                />
              </div>

              <div>
                <label className="block text-slate-400 mb-1 font-medium">Message Body (Optional)</label>
                <textarea
                  rows={3}
                  placeholder="Enter custom email body text or leave blank for default verification template..."
                  value={testEmailBody}
                  onChange={(e) => setTestEmailBody(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg bg-slate-950 border border-slate-800 text-slate-200 text-xs focus:outline-none focus:border-indigo-500"
                />
              </div>

              {testEmailPreview && (
                <div className="p-3 rounded-lg bg-indigo-950/40 border border-indigo-800/80 space-y-2 text-[11px]">
                  <div className="font-semibold text-indigo-300 flex items-center gap-1.5">
                    <Sparkles className="w-3.5 h-3.5" />
                    Draft Ready for Explicit Confirmation
                  </div>
                  <div className="text-slate-300 space-y-1">
                    <p><strong className="text-slate-400">To:</strong> {testEmailPreview.recipient}</p>
                    <p><strong className="text-slate-400">Subject:</strong> {testEmailPreview.subject}</p>
                    <pre className="p-2 rounded bg-slate-950/80 text-slate-300 font-mono whitespace-pre-wrap max-h-24 overflow-y-auto">
                      {testEmailPreview.body_preview}
                    </pre>
                  </div>
                </div>
              )}

              {testEmailResult && (
                <div
                  className={`p-3 rounded-lg text-[11px] border ${
                    testEmailResult.error
                      ? 'bg-rose-950/40 border-rose-800 text-rose-300'
                      : 'bg-emerald-950/40 border-emerald-800 text-emerald-300'
                  }`}
                >
                  {testEmailResult.error ? (
                    <div>{testEmailResult.error}</div>
                  ) : (
                    <div className="space-y-1">
                      <p className="font-bold flex items-center gap-1">
                        <CheckCircle2 className="w-3.5 h-3.5" /> {testEmailResult.message}
                      </p>
                      <p className="font-mono text-[10px] text-emerald-400">Message ID: {testEmailResult.message_id}</p>
                    </div>
                  )}
                </div>
              )}
            </div>

            <div className="pt-2 flex items-center justify-end gap-2 border-t border-slate-800">
              <button
                type="button"
                onClick={() => {
                  setSendTestModalOpen(false);
                  setTestEmailPreview(null);
                  setTestEmailResult(null);
                }}
                className="px-3 py-1.5 rounded-lg text-xs text-slate-400 hover:text-white transition-colors cursor-pointer"
              >
                Cancel
              </button>
              {!testEmailPreview ? (
                <button
                  type="button"
                  onClick={handlePreviewEmail}
                  disabled={!testEmailRecipient.trim() || isSendingEmail}
                  className="px-4 py-2 rounded-lg text-xs font-semibold bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white cursor-pointer transition-colors shadow-sm flex items-center gap-1.5"
                >
                  {isSendingEmail ? <RefreshCw className="w-3 h-3 animate-spin" /> : <Mail className="w-3.5 h-3.5" />}
                  Preview Draft
                </button>
              ) : (
                <button
                  type="button"
                  onClick={handleConfirmSendEmail}
                  disabled={isSendingEmail}
                  className="px-4 py-2 rounded-lg text-xs font-semibold bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white cursor-pointer transition-colors shadow-sm flex items-center gap-1.5"
                >
                  {isSendingEmail ? <RefreshCw className="w-3 h-3 animate-spin" /> : <CheckCircle2 className="w-3.5 h-3.5" />}
                  Confirm & Send Real Email
                </button>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
