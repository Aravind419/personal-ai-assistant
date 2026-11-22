import React, { useState, useEffect, useCallback } from 'react';
import {
  Wrench,
  Server,
  History,
  Play,
  RefreshCw,
  Plus,
  Trash2,
  Code2,
  Layers,
  Search,
} from 'lucide-react';
import { toolService } from '../services/toolService';
import type {
  ToolDefinition,
  ToolExecutionSummary,
  McpServer,
  ToolsHealth,
} from '../types/tool';


export const ToolsView: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'tools' | 'history' | 'mcp'>('tools');
  const [tools, setTools] = useState<ToolDefinition[]>([]);
  const [executions, setExecutions] = useState<ToolExecutionSummary[]>([]);
  const [mcpServers, setMcpServers] = useState<McpServer[]>([]);
  const [health, setHealth] = useState<ToolsHealth | null>(null);
  const [categoryFilter, setCategoryFilter] = useState<string>('all');
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Modals & Test Run
  const [selectedToolSchema, setSelectedToolSchema] = useState<ToolDefinition | null>(null);
  const [testToolModal, setTestToolModal] = useState<ToolDefinition | null>(null);
  const [testArgs, setTestArgs] = useState<string>('{}');
  const [testResult, setTestResult] = useState<any | null>(null);
  const [isExecutingTest, setIsExecutingTest] = useState<boolean>(false);

  // Add MCP Server Modal
  const [isAddMcpModalOpen, setIsAddMcpModalOpen] = useState<boolean>(false);
  const [newMcpName, setNewMcpName] = useState<string>('');
  const [newMcpType, setNewMcpType] = useState<string>('stdio');
  const [newMcpCommand, setNewMcpCommand] = useState<string>('');
  const [newMcpUrl, setNewMcpUrl] = useState<string>('');

  const fetchData = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const [toolsData, healthData, mcpData] = await Promise.all([
        toolService.getTools(),
        toolService.getToolsHealth(),
        toolService.getMcpServers(),
      ]);
      setTools(toolsData);
      setHealth(healthData);
      setMcpServers(mcpData);

      if (activeTab === 'history') {
        const hist = await toolService.getExecutionHistory({ limit: 50 });
        setExecutions(hist);
      }
    } catch (err: any) {
      setError(err?.message || 'Failed to load tools data.');
    } finally {
      setIsLoading(false);
    }
  }, [activeTab]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const handleTestRun = async () => {
    if (!testToolModal) return;
    setIsExecutingTest(true);
    setTestResult(null);
    try {
      let parsedArgs = {};
      if (testArgs.trim()) {
        parsedArgs = JSON.parse(testArgs);
      }
      const res = await toolService.executeTool(testToolModal.id, parsedArgs);
      setTestResult(res);
      // Refresh history if active
      if (activeTab === 'history') {
        const hist = await toolService.getExecutionHistory({ limit: 50 });
        setExecutions(hist);
      }
    } catch (err: any) {
      setTestResult({ success: false, error: err?.message || 'Execution error' });
    } finally {
      setIsExecutingTest(false);
    }
  };

  const handleCreateMcp = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newMcpName.trim()) return;
    try {
      await toolService.createMcpServer({
        name: newMcpName.trim(),
        server_type: newMcpType,
        command: newMcpCommand.trim() || undefined,
        url: newMcpUrl.trim() || undefined,
      });
      setIsAddMcpModalOpen(false);
      setNewMcpName('');
      setNewMcpCommand('');
      setNewMcpUrl('');
      await fetchData();
    } catch (err: any) {
      setError(err?.message || 'Failed to add MCP server.');
    }
  };

  const handleDiscoverMcp = async (serverId: string) => {
    try {
      await toolService.discoverMcpTools(serverId);
      await fetchData();
    } catch (err: any) {
      setError(err?.message || 'Failed to discover tools for server.');
    }
  };

  const handleDeleteMcp = async (serverId: string) => {
    if (!confirm('Are you sure you want to delete this MCP server?')) return;
    try {
      await toolService.deleteMcpServer(serverId);
      await fetchData();
    } catch (err: any) {
      setError(err?.message || 'Failed to delete MCP server.');
    }
  };

  const filteredTools = tools.filter((t) => {
    if (categoryFilter !== 'all' && t.category !== categoryFilter) return false;
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      return t.name.toLowerCase().includes(q) || t.description.toLowerCase().includes(q);
    }
    return true;
  });

  return (
    <div className="space-y-6 pb-12">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-800 pb-5">
        <div>
          <h1 className="text-2xl font-bold text-slate-100 flex items-center gap-2">
            <Wrench className="w-6 h-6 text-indigo-400" />
            Tool Execution Hub & Registry
          </h1>
          <p className="text-sm text-slate-400 mt-1">
            Centralized registry for native tools, external MCP servers, and execution telemetry.
          </p>
        </div>
        <button
          onClick={() => fetchData()}
          className="px-3 py-1.5 rounded-lg text-sm bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 flex items-center gap-1.5 transition-colors self-start cursor-pointer"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin' : ''}`} />
          Refresh
        </button>
      </div>

      {/* Health Overview Cards */}
      {health && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800">
            <div className="text-xs font-medium text-slate-400">Total Registered Tools</div>
            <div className="text-2xl font-bold text-slate-100 mt-1">{health.total_tools_count}</div>
          </div>
          <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800">
            <div className="text-xs font-medium text-slate-400">Enabled Tools</div>
            <div className="text-2xl font-bold text-emerald-400 mt-1">{health.enabled_tools_count}</div>
          </div>
          <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800">
            <div className="text-xs font-medium text-slate-400">Configured MCP Servers</div>
            <div className="text-2xl font-bold text-indigo-400 mt-1">{health.mcp_servers_count}</div>
          </div>
          <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800">
            <div className="text-xs font-medium text-slate-400">Connected MCP Servers</div>
            <div className="text-2xl font-bold text-emerald-400 mt-1">{health.connected_mcp_servers}</div>
          </div>
        </div>
      )}

      {/* Main Tabs */}
      <div className="flex border-b border-slate-800 gap-6">
        <button
          onClick={() => setActiveTab('tools')}
          className={`pb-3 text-sm font-semibold flex items-center gap-2 border-b-2 transition-colors cursor-pointer ${
            activeTab === 'tools'
              ? 'border-indigo-500 text-indigo-400'
              : 'border-transparent text-slate-400 hover:text-slate-200'
          }`}
        >
          <Layers className="w-4 h-4" />
          Registered Tools ({tools.length})
        </button>
        <button
          onClick={() => setActiveTab('history')}
          className={`pb-3 text-sm font-semibold flex items-center gap-2 border-b-2 transition-colors cursor-pointer ${
            activeTab === 'history'
              ? 'border-indigo-500 text-indigo-400'
              : 'border-transparent text-slate-400 hover:text-slate-200'
          }`}
        >
          <History className="w-4 h-4" />
          Execution History
        </button>
        <button
          onClick={() => setActiveTab('mcp')}
          className={`pb-3 text-sm font-semibold flex items-center gap-2 border-b-2 transition-colors cursor-pointer ${
            activeTab === 'mcp'
              ? 'border-indigo-500 text-indigo-400'
              : 'border-transparent text-slate-400 hover:text-slate-200'
          }`}
        >
          <Server className="w-4 h-4" />
          MCP Servers ({mcpServers.length})
        </button>
      </div>

      {error && (
        <div className="p-4 rounded-lg bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs">
          {error}
        </div>
      )}

      {/* TAB 1: Registered Tools */}
      {activeTab === 'tools' && (
        <div className="space-y-4">
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div className="flex items-center gap-1.5 p-1 bg-slate-900 border border-slate-800 rounded-lg overflow-x-auto text-xs">
              {['all', 'system', 'math', 'text', 'file', 'developer', 'mcp'].map((cat) => (
                <button
                  key={cat}
                  onClick={() => setCategoryFilter(cat)}
                  className={`px-3 py-1 rounded-md capitalize cursor-pointer transition-colors ${
                    categoryFilter === cat
                      ? 'bg-indigo-600 text-white'
                      : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800'
                  }`}
                >
                  {cat}
                </button>
              ))}
            </div>

            <div className="relative w-full md:w-64">
              <Search className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
              <input
                type="text"
                placeholder="Search tools..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full pl-9 pr-3 py-1.5 text-xs bg-slate-900 border border-slate-800 rounded-lg text-slate-200 placeholder-slate-500 focus:outline-none focus:border-indigo-500"
              />
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {filteredTools.map((tool) => (
              <div
                key={tool.id}
                className="p-5 rounded-xl bg-slate-900/60 border border-slate-800 hover:border-slate-700 transition-all flex flex-col justify-between space-y-4"
              >
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-mono font-bold text-indigo-400 bg-indigo-500/10 border border-indigo-500/20 px-2 py-0.5 rounded">
                      {tool.name}
                    </span>
                    <span
                      className={`text-[10px] font-semibold px-2 py-0.5 rounded uppercase ${
                        tool.permission_level === 'critical'
                          ? 'bg-rose-500/20 text-rose-300 border border-rose-500/30'
                          : tool.permission_level === 'sensitive'
                          ? 'bg-amber-500/20 text-amber-300 border border-amber-500/30'
                          : 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30'
                      }`}
                    >
                      {tool.permission_level}
                    </span>
                  </div>

                  <p className="text-xs text-slate-300 leading-relaxed">{tool.description}</p>
                </div>

                <div className="space-y-3 pt-2 border-t border-slate-800/80">
                  <div className="flex items-center justify-between text-[11px] text-slate-400">
                    <span className="capitalize">Env: {tool.execution_environment}</span>
                    <span>Timeout: {tool.timeout_seconds}s</span>
                  </div>

                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => setSelectedToolSchema(tool)}
                      className="flex-1 py-1.5 rounded-lg text-xs bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 flex items-center justify-center gap-1 cursor-pointer transition-colors"
                    >
                      <Code2 className="w-3.5 h-3.5" />
                      Schema
                    </button>
                    <button
                      onClick={() => {
                        setTestToolModal(tool);
                        setTestArgs('{}');
                        setTestResult(null);
                      }}
                      className="px-3 py-1.5 rounded-lg text-xs bg-indigo-600 hover:bg-indigo-500 text-white flex items-center justify-center gap-1 cursor-pointer transition-colors"
                    >
                      <Play className="w-3 h-3" />
                      Test
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* TAB 2: Execution History */}
      {activeTab === 'history' && (
        <div className="space-y-3">
          {executions.length === 0 ? (
            <div className="p-8 text-center text-sm text-slate-500 bg-slate-900/40 rounded-xl border border-slate-800">
              No executions recorded yet. Run tools or send messages to view history.
            </div>
          ) : (
            executions.map((exec) => (
              <div
                key={exec.id}
                className="p-4 rounded-xl bg-slate-900/50 border border-slate-800 flex flex-col md:flex-row md:items-center justify-between gap-3 text-xs"
              >
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <span className="font-semibold text-slate-100 font-mono text-sm">{exec.tool_name}</span>
                    <span
                      className={`px-2 py-0.5 rounded text-[10px] font-semibold uppercase ${
                        exec.status === 'succeeded'
                          ? 'bg-emerald-500/20 text-emerald-300'
                          : exec.status === 'awaiting_approval'
                          ? 'bg-amber-500/20 text-amber-300 animate-pulse'
                          : 'bg-rose-500/20 text-rose-300'
                      }`}
                    >
                      {exec.status}
                    </span>
                    {exec.duration_ms !== null && exec.duration_ms !== undefined && (
                      <span className="text-slate-500">{exec.duration_ms} ms</span>
                    )}
                  </div>

                  <div className="text-slate-400">
                    Args:{' '}
                    <code className="text-indigo-300 font-mono">
                      {JSON.stringify(exec.requested_arguments)}
                    </code>
                  </div>

                  {exec.result_summary && (
                    <div className="text-slate-300 truncate max-w-2xl">
                      Result: <span className="font-mono text-emerald-300">{exec.result_summary}</span>
                    </div>
                  )}

                  {exec.error_details && (
                    <div className="text-rose-400 font-mono">{exec.error_details}</div>
                  )}
                </div>

                <div className="text-right text-slate-500 text-[11px] shrink-0">
                  <div>{new Date(exec.started_at).toLocaleString()}</div>
                  <div className="capitalize">{exec.execution_environment}</div>
                </div>
              </div>
            ))
          )}
        </div>
      )}

      {/* TAB 3: MCP Servers */}
      {activeTab === 'mcp' && (
        <div className="space-y-4">
          <div className="flex justify-between items-center">
            <p className="text-xs text-slate-400">
              Configure Model Context Protocol (MCP) servers to dynamically discover and execute external tools.
            </p>
            <button
              onClick={() => setIsAddMcpModalOpen(true)}
              className="px-3 py-1.5 rounded-lg text-xs font-semibold bg-indigo-600 hover:bg-indigo-500 text-white flex items-center gap-1.5 cursor-pointer shadow-sm transition-colors"
            >
              <Plus className="w-3.5 h-3.5" />
              Add MCP Server
            </button>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {mcpServers.map((server) => (
              <div
                key={server.id}
                className="p-5 rounded-xl bg-slate-900/60 border border-slate-800 space-y-3"
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Server className="w-4 h-4 text-indigo-400" />
                    <span className="font-bold text-slate-100 text-sm">{server.name}</span>
                  </div>
                  <span
                    className={`text-[10px] font-semibold px-2 py-0.5 rounded uppercase ${
                      server.status === 'connected'
                        ? 'bg-emerald-500/20 text-emerald-300'
                        : server.status === 'error'
                        ? 'bg-rose-500/20 text-rose-300'
                        : 'bg-slate-800 text-slate-400'
                    }`}
                  >
                    {server.status}
                  </span>
                </div>

                <div className="text-xs text-slate-400 space-y-1">
                  <div>
                    Type: <span className="text-slate-200 capitalize">{server.server_type}</span>
                  </div>
                  {server.command && (
                    <div>
                      Command: <code className="text-indigo-300 font-mono">{server.command}</code>
                    </div>
                  )}
                  {server.url && (
                    <div>
                      URL: <code className="text-indigo-300 font-mono">{server.url}</code>
                    </div>
                  )}
                  <div>
                    Discovered Tools: <strong className="text-slate-200">{server.discovered_tools_count}</strong>
                  </div>
                  {server.last_error && (
                    <div className="text-rose-400 text-[11px] font-mono">{server.last_error}</div>
                  )}
                </div>

                <div className="flex items-center gap-2 pt-2 border-t border-slate-800">
                  <button
                    onClick={() => handleDiscoverMcp(server.id)}
                    className="flex-1 py-1.5 rounded-lg text-xs bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 flex items-center justify-center gap-1 cursor-pointer transition-colors"
                  >
                    <RefreshCw className="w-3 h-3" />
                    Discover Tools
                  </button>
                  <button
                    onClick={() => handleDeleteMcp(server.id)}
                    className="p-1.5 rounded-lg text-xs bg-rose-500/10 hover:bg-rose-500/20 text-rose-400 border border-rose-500/30 cursor-pointer transition-colors"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Schema Modal */}
      {selectedToolSchema && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm">
          <div className="w-full max-w-xl bg-slate-900 border border-slate-800 rounded-xl shadow-2xl p-6 space-y-4">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <h3 className="text-base font-bold text-slate-100 flex items-center gap-2">
                <Code2 className="w-5 h-5 text-indigo-400" />
                Parameters Schema: {selectedToolSchema.name}
              </h3>
              <button
                onClick={() => setSelectedToolSchema(null)}
                className="text-slate-400 hover:text-slate-200 cursor-pointer"
              >
                ✕
              </button>
            </div>
            <pre className="p-4 rounded-lg bg-slate-950 border border-slate-800 font-mono text-xs text-indigo-300 overflow-x-auto max-h-96">
              {JSON.stringify(selectedToolSchema.parameters_schema, null, 2)}
            </pre>
            <div className="flex justify-end">
              <button
                onClick={() => setSelectedToolSchema(null)}
                className="px-4 py-2 rounded-lg text-xs bg-slate-800 hover:bg-slate-700 text-slate-200 cursor-pointer"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Test Tool Modal */}
      {testToolModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm">
          <div className="w-full max-w-lg bg-slate-900 border border-slate-800 rounded-xl shadow-2xl p-6 space-y-4">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <h3 className="text-base font-bold text-slate-100 flex items-center gap-2">
                <Play className="w-4 h-4 text-emerald-400" />
                Execute Tool: {testToolModal.name}
              </h3>
              <button
                onClick={() => setTestToolModal(null)}
                className="text-slate-400 hover:text-slate-200 cursor-pointer"
              >
                ✕
              </button>
            </div>

            <div className="space-y-2">
              <label className="text-xs font-medium text-slate-300">Arguments (JSON format)</label>
              <textarea
                rows={4}
                value={testArgs}
                onChange={(e) => setTestArgs(e.target.value)}
                className="w-full p-3 text-xs font-mono bg-slate-950 border border-slate-800 rounded-lg text-indigo-300 focus:outline-none focus:border-indigo-500"
              />
            </div>

            {testResult && (
              <div
                className={`p-3 rounded-lg border text-xs space-y-1 font-mono ${
                  testResult.success
                    ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-300'
                    : 'bg-rose-500/10 border-rose-500/30 text-rose-300'
                }`}
              >
                <div className="font-bold">{testResult.success ? 'Success' : 'Failed'}</div>
                <pre className="text-[11px] max-h-40 overflow-y-auto">
                  {JSON.stringify(testResult.result || testResult.error, null, 2)}
                </pre>
              </div>
            )}

            <div className="flex justify-end gap-2 pt-2 border-t border-slate-800">
              <button
                onClick={() => setTestToolModal(null)}
                className="px-3 py-1.5 rounded-lg text-xs bg-slate-800 hover:bg-slate-700 text-slate-300 cursor-pointer"
              >
                Close
              </button>
              <button
                onClick={handleTestRun}
                disabled={isExecutingTest}
                className="px-4 py-1.5 rounded-lg text-xs font-semibold bg-indigo-600 hover:bg-indigo-500 text-white cursor-pointer"
              >
                {isExecutingTest ? 'Running...' : 'Run Tool'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Add MCP Server Modal */}
      {isAddMcpModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm">
          <form
            onSubmit={handleCreateMcp}
            className="w-full max-w-md bg-slate-900 border border-slate-800 rounded-xl shadow-2xl p-6 space-y-4"
          >
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <h3 className="text-base font-bold text-slate-100 flex items-center gap-2">
                <Server className="w-4 h-4 text-indigo-400" />
                Add Model Context Protocol (MCP) Server
              </h3>
              <button
                type="button"
                onClick={() => setIsAddMcpModalOpen(false)}
                className="text-slate-400 hover:text-slate-200 cursor-pointer"
              >
                ✕
              </button>
            </div>

            <div className="space-y-3 text-xs">
              <div>
                <label className="block text-slate-300 font-medium mb-1">Server Name</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. filesystem, github, fetch"
                  value={newMcpName}
                  onChange={(e) => setNewMcpName(e.target.value)}
                  className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-slate-200 focus:outline-none focus:border-indigo-500"
                />
              </div>

              <div>
                <label className="block text-slate-300 font-medium mb-1">Server Type</label>
                <select
                  value={newMcpType}
                  onChange={(e) => setNewMcpType(e.target.value)}
                  className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-slate-200 focus:outline-none focus:border-indigo-500"
                >
                  <option value="stdio">stdio (Local Subprocess Command)</option>
                  <option value="http">http (Remote JSON-RPC Endpoint)</option>
                </select>
              </div>

              {newMcpType === 'stdio' ? (
                <div>
                  <label className="block text-slate-300 font-medium mb-1">Command / Binary</label>
                  <input
                    type="text"
                    placeholder="e.g. npx, uvx, python"
                    value={newMcpCommand}
                    onChange={(e) => setNewMcpCommand(e.target.value)}
                    className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-slate-200 focus:outline-none focus:border-indigo-500"
                  />
                </div>
              ) : (
                <div>
                  <label className="block text-slate-300 font-medium mb-1">Server URL</label>
                  <input
                    type="url"
                    placeholder="http://localhost:8080/mcp"
                    value={newMcpUrl}
                    onChange={(e) => setNewMcpUrl(e.target.value)}
                    className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-slate-200 focus:outline-none focus:border-indigo-500"
                  />
                </div>
              )}
            </div>

            <div className="flex justify-end gap-2 pt-2 border-t border-slate-800">
              <button
                type="button"
                onClick={() => setIsAddMcpModalOpen(false)}
                className="px-3 py-1.5 rounded-lg text-xs bg-slate-800 hover:bg-slate-700 text-slate-300 cursor-pointer"
              >
                Cancel
              </button>
              <button
                type="submit"
                className="px-4 py-1.5 rounded-lg text-xs font-semibold bg-indigo-600 hover:bg-indigo-500 text-white cursor-pointer"
              >
                Save Server
              </button>
            </div>
          </form>
        </div>
      )}
    </div>
  );
};
