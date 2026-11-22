import React, { useState, useEffect, useCallback } from 'react';
import {
  Brain,
  Search,
  Plus,
  Trash2,
  Archive,
  ArchiveRestore,
  Edit2,
  RefreshCw,
  Sparkles,
  Calendar,
  Tag,
  CheckCircle2,
  X,
} from 'lucide-react';
import { memoryService } from '../services/memoryService';
import type { MemoryItem, MemoryStats, MemoryCreatePayload, MemoryUpdatePayload } from '../types/memory';
import { LoadingState } from '../components/common/LoadingState';
import { ErrorState } from '../components/common/ErrorState';
import { EmptyState } from '../components/common/EmptyState';

const CATEGORIES = [
  { id: 'all', label: 'All Categories' },
  { id: 'relationships', label: 'Relationships' },
  { id: 'personal_facts', label: 'Personal Facts' },
  { id: 'education', label: 'Education' },
  { id: 'career_goals', label: 'Career Goals' },
  { id: 'technical_skills', label: 'Technical Skills' },
  { id: 'preferences', label: 'Preferences' },
  { id: 'projects', label: 'Projects' },
  { id: 'important_events', label: 'Important Events' },
  { id: 'decisions', label: 'Decisions' },
  { id: 'ongoing_activities', label: 'Ongoing Activities' },
  { id: 'communication_preferences', label: 'Communication Preferences' },
  { id: 'profile', label: 'Profile' },
  { id: 'technical_knowledge', label: 'Technical Knowledge' },
  { id: 'goals', label: 'Goals' },
  { id: 'episodic', label: 'Episodic' },
  { id: 'procedural', label: 'Procedural' },
  { id: 'general', label: 'General' },
];

const CATEGORY_COLORS: Record<string, string> = {
  relationships: 'bg-rose-900/30 text-rose-300 border-rose-700/50',
  personal_facts: 'bg-emerald-900/30 text-emerald-300 border-emerald-700/50',
  education: 'bg-teal-900/30 text-teal-300 border-teal-700/50',
  career_goals: 'bg-orange-900/30 text-orange-300 border-orange-700/50',
  technical_skills: 'bg-sky-900/30 text-sky-300 border-sky-700/50',
  preferences: 'bg-blue-900/30 text-blue-300 border-blue-700/50',
  projects: 'bg-emerald-900/30 text-emerald-300 border-emerald-700/50',
  important_events: 'bg-amber-900/30 text-amber-300 border-amber-700/50',
  decisions: 'bg-violet-900/30 text-violet-300 border-violet-700/50',
  ongoing_activities: 'bg-lime-900/30 text-lime-300 border-lime-700/50',
  communication_preferences: 'bg-fuchsia-900/30 text-fuchsia-300 border-fuchsia-700/50',
  profile: 'bg-purple-900/30 text-purple-300 border-purple-700/50',
  technical_knowledge: 'bg-cyan-900/30 text-cyan-300 border-cyan-700/50',
  goals: 'bg-amber-900/30 text-amber-300 border-amber-700/50',
  episodic: 'bg-pink-900/30 text-pink-300 border-pink-700/50',
  procedural: 'bg-indigo-900/30 text-indigo-300 border-indigo-700/50',
  general: 'bg-neutral-800 text-neutral-300 border-neutral-700',
};

export const MemoryView: React.FC = () => {
  const [memories, setMemories] = useState<MemoryItem[]>([]);
  const [stats, setStats] = useState<MemoryStats | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCategory, setSelectedCategory] = useState('all');
  const [showArchived, setShowArchived] = useState(false);

  // Modal states
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingMemory, setEditingMemory] = useState<MemoryItem | null>(null);
  const [formContent, setFormContent] = useState('');
  const [formCategory, setFormCategory] = useState('preferences');
  const [formImportance, setFormImportance] = useState(0.8);
  const [formConfidence, setFormConfidence] = useState(0.9);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [actionSuccess, setActionSuccess] = useState<string | null>(null);

  const fetchMemoriesAndStats = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const [memRes, statsRes] = await Promise.all([
        memoryService.listMemories({
          category: selectedCategory === 'all' ? undefined : selectedCategory,
          search: searchQuery.trim() || undefined,
          is_archived: showArchived,
        }),
        memoryService.getStats(),
      ]);
      setMemories(memRes.items);
      setStats(statsRes);
    } catch (err: any) {
      setError(err?.message || 'Failed to load semantic memory data.');
    } finally {
      setIsLoading(false);
    }
  }, [selectedCategory, searchQuery, showArchived]);

  useEffect(() => {
    fetchMemoriesAndStats();
  }, [fetchMemoriesAndStats]);

  const handleOpenCreateModal = () => {
    setEditingMemory(null);
    setFormContent('');
    setFormCategory('preferences');
    setFormImportance(0.8);
    setFormConfidence(0.9);
    setIsModalOpen(true);
  };

  const handleOpenEditModal = (mem: MemoryItem) => {
    setEditingMemory(mem);
    setFormContent(mem.content);
    setFormCategory(mem.category);
    setFormImportance(mem.importance);
    setFormConfidence(mem.confidence);
    setIsModalOpen(true);
  };

  const handleSaveMemory = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!formContent.trim()) return;

    setIsSubmitting(true);
    try {
      if (editingMemory) {
        const updatePayload: MemoryUpdatePayload = {
          content: formContent.trim(),
          category: formCategory,
          importance: formImportance,
          confidence: formConfidence,
        };
        await memoryService.updateMemory(editingMemory.id, updatePayload);
        setActionSuccess('Memory updated successfully.');
      } else {
        const createPayload: MemoryCreatePayload = {
          content: formContent.trim(),
          category: formCategory,
          importance: formImportance,
          confidence: formConfidence,
        };
        await memoryService.createMemory(createPayload);
        setActionSuccess('New semantic memory saved with vector embedding.');
      }
      setIsModalOpen(false);
      fetchMemoriesAndStats();
      setTimeout(() => setActionSuccess(null), 4000);
    } catch (err: any) {
      alert(err?.message || 'Failed to save memory.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleDeleteMemory = async (id: string) => {
    if (!window.confirm('Permanently delete this memory? Its vector embedding will also be removed.')) {
      return;
    }
    try {
      await memoryService.deleteMemory(id);
      setActionSuccess('Memory and vector embedding permanently deleted.');
      fetchMemoriesAndStats();
      setTimeout(() => setActionSuccess(null), 4000);
    } catch (err: any) {
      alert(err?.message || 'Failed to delete memory.');
    }
  };

  const handleToggleArchive = async (mem: MemoryItem) => {
    try {
      await memoryService.toggleArchive(mem.id, !mem.is_archived);
      setActionSuccess(mem.is_archived ? 'Memory restored to active knowledge.' : 'Memory archived.');
      fetchMemoriesAndStats();
      setTimeout(() => setActionSuccess(null), 4000);
    } catch (err: any) {
      alert(err?.message || 'Failed to toggle archive state.');
    }
  };

  return (
    <div className="flex-1 flex flex-col h-full bg-neutral-950 text-neutral-100 overflow-y-auto">
      {/* Header */}
      <div className="p-6 border-b border-neutral-800 bg-neutral-900/50 backdrop-blur-sm sticky top-0 z-10 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2.5">
            <div className="p-2 bg-purple-500/10 border border-purple-500/20 rounded-lg text-purple-400">
              <Brain className="w-5 h-5" />
            </div>
            <h1 className="text-xl font-semibold tracking-tight">Semantic Memory Store</h1>
            <span className="text-xs px-2.5 py-0.5 rounded-full font-medium bg-purple-900/40 text-purple-300 border border-purple-700/50">
              pgvector 384-dim
            </span>
          </div>
          <p className="text-xs text-neutral-400 mt-1">
            Permanent user knowledge, extracted facts, and vector embeddings retrieved automatically during conversations.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => fetchMemoriesAndStats()}
            className="p-2 text-neutral-400 hover:text-neutral-200 hover:bg-neutral-800 rounded-lg border border-neutral-700 transition"
            title="Refresh"
          >
            <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />
          </button>
          <button
            onClick={handleOpenCreateModal}
            className="flex items-center gap-1.5 px-3.5 py-2 bg-purple-600 hover:bg-purple-500 text-white rounded-lg text-xs font-medium transition shadow-sm"
          >
            <Plus className="w-4 h-4" />
            Add Memory
          </button>
        </div>
      </div>

      <div className="p-6 max-w-7xl w-full mx-auto space-y-6">
        {/* Success Alert Banner */}
        {actionSuccess && (
          <div className="flex items-center gap-2 p-3 bg-emerald-950/60 border border-emerald-800 text-emerald-300 rounded-lg text-xs">
            <CheckCircle2 className="w-4 h-4 shrink-0 text-emerald-400" />
            <span>{actionSuccess}</span>
          </div>
        )}

        {/* Overview Stats Cards */}
        {stats && (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <div className="bg-neutral-900 border border-neutral-800 rounded-xl p-4">
              <div className="text-neutral-400 text-xs font-medium">Active Memories</div>
              <div className="text-2xl font-bold mt-1 text-white">{stats.total_active}</div>
              <div className="text-[11px] text-neutral-500 mt-1 flex items-center gap-1">
                <Sparkles className="w-3 h-3 text-purple-400" />
                Indexed in PostgreSQL pgvector
              </div>
            </div>

            <div className="bg-neutral-900 border border-neutral-800 rounded-xl p-4">
              <div className="text-neutral-400 text-xs font-medium">Archived Memories</div>
              <div className="text-2xl font-bold mt-1 text-neutral-300">{stats.total_archived}</div>
              <div className="text-[11px] text-neutral-500 mt-1">Excluded from auto-retrieval</div>
            </div>

            <div className="bg-neutral-900 border border-neutral-800 rounded-xl p-4 sm:col-span-2">
              <div className="text-neutral-400 text-xs font-medium mb-2">Category Distribution</div>
              <div className="flex flex-wrap gap-1.5">
                {Object.entries(stats.category_distribution).length === 0 ? (
                  <span className="text-xs text-neutral-500">No categories indexed yet</span>
                ) : (
                  Object.entries(stats.category_distribution).map(([cat, count]) => (
                    <span
                      key={cat}
                      className={`text-xs px-2.5 py-1 rounded-md border font-medium flex items-center gap-1.5 ${
                        CATEGORY_COLORS[cat] || CATEGORY_COLORS.general
                      }`}
                    >
                      <Tag className="w-3 h-3" />
                      {cat.replace('_', ' ')}
                      <span className="bg-black/30 px-1.5 py-0.2 rounded-full text-[10px]">{count}</span>
                    </span>
                  ))
                )}
              </div>
            </div>
          </div>
        )}

        {/* Filter & Search Bar */}
        <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3 bg-neutral-900/60 p-3 rounded-xl border border-neutral-800">
          <div className="relative flex-1">
            <Search className="w-4 h-4 text-neutral-400 absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search memories by content or semantic keywords..."
              className="w-full bg-neutral-950 border border-neutral-800 rounded-lg pl-9 pr-3 py-1.5 text-xs text-neutral-200 placeholder-neutral-500 focus:outline-none focus:border-purple-500 transition"
            />
          </div>

          <div className="flex items-center gap-2 overflow-x-auto pb-1 sm:pb-0">
            <select
              value={selectedCategory}
              onChange={(e) => setSelectedCategory(e.target.value)}
              className="bg-neutral-950 border border-neutral-800 text-neutral-300 text-xs rounded-lg px-2.5 py-1.5 focus:outline-none focus:border-purple-500"
            >
              {CATEGORIES.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.label}
                </option>
              ))}
            </select>

            <button
              onClick={() => setShowArchived(!showArchived)}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium border transition ${
                showArchived
                  ? 'bg-amber-900/30 text-amber-300 border-amber-700/60'
                  : 'bg-neutral-950 text-neutral-400 border-neutral-800 hover:text-neutral-200'
              }`}
            >
              <Archive className="w-3.5 h-3.5" />
              {showArchived ? 'Viewing Archived' : 'Active Only'}
            </button>
          </div>
        </div>

        {/* Memories Content List */}
        {isLoading ? (
          <LoadingState message="Loading semantic memories..." />
        ) : error ? (
          <ErrorState message={error} onRetry={fetchMemoriesAndStats} />
        ) : memories.length === 0 ? (
          <EmptyState
            title={showArchived ? 'No archived memories' : 'No memories found'}
            description={
              showArchived
                ? 'Archived memories will appear here.'
                : 'Start chatting with the assistant or click "Add Memory" to store facts, preferences, and knowledge.'
            }
          />
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {memories.map((mem) => {
              const colorClass = CATEGORY_COLORS[mem.category] || CATEGORY_COLORS.general;
              const formattedDate = new Date(mem.created_at).toLocaleDateString(undefined, {
                month: 'short',
                day: 'numeric',
                year: 'numeric',
              });

              return (
                <div
                  key={mem.id}
                  className="bg-neutral-900 border border-neutral-800 rounded-xl p-4 flex flex-col justify-between hover:border-neutral-700 transition space-y-3 group"
                >
                  <div>
                    <div className="flex flex-wrap items-center justify-between gap-2 mb-2">
                      <div className="flex flex-wrap items-center gap-1.5">
                        <span className={`text-[11px] px-2 py-0.5 rounded-md border font-medium ${colorClass}`}>
                          {mem.category.replace('_', ' ')}
                        </span>
                        {mem.subcategory && (
                          <span className="text-[10px] px-1.5 py-0.5 rounded bg-neutral-800 text-neutral-300 border border-neutral-700/60 font-mono">
                            {mem.subcategory.replace('_', ' ')}
                          </span>
                        )}
                        {mem.temporal_scope && (
                          <span className={`text-[10px] px-1.5 py-0.5 rounded font-mono ${
                            mem.temporal_scope === 'current'
                              ? 'bg-emerald-950/60 text-emerald-300 border border-emerald-800/60'
                              : mem.temporal_scope === 'previous'
                              ? 'bg-amber-950/60 text-amber-300 border border-amber-800/60'
                              : 'bg-neutral-800/60 text-neutral-400 border border-neutral-700/40'
                          }`}>
                            {mem.temporal_scope}
                          </span>
                        )}
                        {mem.is_current === false && (
                          <span className="text-[10px] px-1.5 py-0.5 rounded bg-neutral-800 text-neutral-400 border border-neutral-700/40">
                            historical
                          </span>
                        )}
                      </div>

                      <div className="flex items-center gap-2 text-[11px] text-neutral-400">
                        <span title="Importance score">Importance: {Math.round(mem.importance * 100)}%</span>
                        <span>•</span>
                        <span title="Confidence score">Confidence: {Math.round(mem.confidence * 100)}%</span>
                      </div>
                    </div>

                    <p className="text-sm text-neutral-200 leading-relaxed font-normal">{mem.content}</p>

                    {mem.original_statement && (
                      <p className="text-[11px] text-neutral-400 mt-1 italic font-mono bg-neutral-950/50 px-2 py-1 rounded border border-neutral-800/50">
                        "{mem.original_statement}"
                      </p>
                    )}
                  </div>

                  <div className="pt-3 border-t border-neutral-800/60 flex items-center justify-between text-xs text-neutral-500">
                    <div className="flex items-center gap-1.5 text-[11px]">
                      <Calendar className="w-3.5 h-3.5 text-neutral-500" />
                      <span>{formattedDate}</span>
                      {mem.source_conversation_id && (
                        <span className="text-purple-400 bg-purple-950/40 px-1.5 py-0.2 rounded border border-purple-800/40 text-[10px]">
                          auto-extracted
                        </span>
                      )}
                    </div>

                    <div className="flex items-center gap-1 opacity-90 group-hover:opacity-100 transition">
                      <button
                        onClick={() => handleOpenEditModal(mem)}
                        className="p-1.5 text-neutral-400 hover:text-neutral-200 hover:bg-neutral-800 rounded transition"
                        title="Edit Memory"
                      >
                        <Edit2 className="w-3.5 h-3.5" />
                      </button>
                      <button
                        onClick={() => handleToggleArchive(mem)}
                        className="p-1.5 text-neutral-400 hover:text-amber-300 hover:bg-neutral-800 rounded transition"
                        title={mem.is_archived ? 'Restore' : 'Archive'}
                      >
                        {mem.is_archived ? (
                          <ArchiveRestore className="w-3.5 h-3.5" />
                        ) : (
                          <Archive className="w-3.5 h-3.5" />
                        )}
                      </button>
                      <button
                        onClick={() => handleDeleteMemory(mem.id)}
                        className="p-1.5 text-neutral-400 hover:text-rose-400 hover:bg-neutral-800 rounded transition"
                        title="Delete Memory"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Add / Edit Modal */}
      {isModalOpen && (
        <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-neutral-900 border border-neutral-800 rounded-xl max-w-lg w-full p-6 shadow-2xl relative">
            <button
              onClick={() => setIsModalOpen(false)}
              className="absolute top-4 right-4 text-neutral-400 hover:text-neutral-200"
            >
              <X className="w-4 h-4" />
            </button>

            <h2 className="text-base font-semibold text-neutral-100 mb-1">
              {editingMemory ? 'Edit Semantic Memory' : 'Add New Semantic Memory'}
            </h2>
            <p className="text-xs text-neutral-400 mb-4">
              Stored facts are permanently saved in PostgreSQL with a 384-dimensional vector embedding.
            </p>

            <form onSubmit={handleSaveMemory} className="space-y-4">
              <div>
                <label className="block text-xs font-medium text-neutral-300 mb-1">Memory Content</label>
                <textarea
                  value={formContent}
                  onChange={(e) => setFormContent(e.target.value)}
                  placeholder="e.g. User prefers Python 3.13 with strict type hints and async FastAPI backend architecture."
                  rows={4}
                  required
                  className="w-full bg-neutral-950 border border-neutral-800 rounded-lg p-2.5 text-xs text-neutral-200 placeholder-neutral-500 focus:outline-none focus:border-purple-500"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-neutral-300 mb-1">Category</label>
                <select
                  value={formCategory}
                  onChange={(e) => setFormCategory(e.target.value)}
                  className="w-full bg-neutral-950 border border-neutral-800 rounded-lg p-2 text-xs text-neutral-200 focus:outline-none focus:border-purple-500"
                >
                  {CATEGORIES.filter((c) => c.id !== 'all').map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.label}
                    </option>
                  ))}
                </select>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <div className="flex justify-between text-xs text-neutral-300 mb-1">
                    <span>Importance</span>
                    <span className="text-purple-400 font-mono">{Math.round(formImportance * 100)}%</span>
                  </div>
                  <input
                    type="range"
                    min="0.1"
                    max="1.0"
                    step="0.05"
                    value={formImportance}
                    onChange={(e) => setFormImportance(parseFloat(e.target.value))}
                    className="w-full accent-purple-500"
                  />
                </div>

                <div>
                  <div className="flex justify-between text-xs text-neutral-300 mb-1">
                    <span>Confidence</span>
                    <span className="text-purple-400 font-mono">{Math.round(formConfidence * 100)}%</span>
                  </div>
                  <input
                    type="range"
                    min="0.5"
                    max="1.0"
                    step="0.05"
                    value={formConfidence}
                    onChange={(e) => setFormConfidence(parseFloat(e.target.value))}
                    className="w-full accent-purple-500"
                  />
                </div>
              </div>

              <div className="pt-2 flex justify-end gap-2">
                <button
                  type="button"
                  onClick={() => setIsModalOpen(false)}
                  className="px-3.5 py-1.5 bg-neutral-800 hover:bg-neutral-700 text-neutral-300 rounded-lg text-xs font-medium transition"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isSubmitting || !formContent.trim()}
                  className="px-4 py-1.5 bg-purple-600 hover:bg-purple-500 disabled:opacity-50 text-white rounded-lg text-xs font-medium transition"
                >
                  {isSubmitting ? 'Saving...' : editingMemory ? 'Save Changes' : 'Create Memory'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
