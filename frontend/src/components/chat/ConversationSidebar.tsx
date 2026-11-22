import React, { useState } from 'react';
import type { ConversationSummary } from '../../types/chat';
import { Plus, MessageSquare, Trash2, Edit2, Check, X } from 'lucide-react';

interface ConversationSidebarProps {
  conversations: ConversationSummary[];
  activeId: string | null;
  onSelect: (id: string) => void;
  onNew: () => void;
  onRename: (id: string, newTitle: string) => void;
  onDelete: (id: string) => void;
  isOpen: boolean;
  onClose: () => void;
}

export const ConversationSidebar: React.FC<ConversationSidebarProps> = ({
  conversations,
  activeId,
  onSelect,
  onNew,
  onRename,
  onDelete,
  isOpen,
  onClose,
}) => {
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editTitle, setEditTitle] = useState('');

  const startRename = (c: ConversationSummary, e: React.MouseEvent) => {
    e.stopPropagation();
    setEditingId(c.id);
    setEditTitle(c.title);
  };

  const saveRename = (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (editTitle.trim()) {
      onRename(id, editTitle.trim());
    }
    setEditingId(null);
  };

  const cancelRename = (e: React.MouseEvent) => {
    e.stopPropagation();
    setEditingId(null);
  };

  const handleDelete = (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (window.confirm('Delete this conversation thread?')) {
      onDelete(id);
    }
  };

  return (
    <>
      {isOpen && (
        <div
          onClick={onClose}
          className="fixed inset-0 bg-slate-950/80 backdrop-blur-sm z-30 lg:hidden"
        />
      )}

      <div
        className={`w-72 bg-slate-950 border-r border-slate-800 flex flex-col h-full shrink-0 transition-transform duration-200 z-30 ${
          isOpen ? 'fixed inset-y-0 left-0 lg:static' : 'hidden lg:flex'
        }`}
      >
        {/* New Chat Button */}
        <div className="p-3 border-b border-slate-800/80">
          <button
            onClick={() => {
              onNew();
              onClose();
            }}
            className="w-full flex items-center justify-center gap-2 py-2 px-3 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold shadow-sm transition-colors cursor-pointer"
          >
            <Plus className="w-4 h-4" />
            <span>New Conversation</span>
          </button>
        </div>

        {/* Conversations List */}
        <div className="flex-1 overflow-y-auto p-2 space-y-1">
          {conversations.length === 0 ? (
            <div className="p-6 text-center text-xs text-slate-500">
              No conversations yet. Start a new chat!
            </div>
          ) : (
            conversations.map((c) => {
              const isActive = c.id === activeId;
              const isEditing = c.id === editingId;

              return (
                <div
                  key={c.id}
                  onClick={() => {
                    onSelect(c.id);
                    onClose();
                  }}
                  className={`group relative flex items-center justify-between p-2.5 rounded-lg text-xs transition-colors cursor-pointer ${
                    isActive
                      ? 'bg-indigo-600/15 text-indigo-300 border border-indigo-500/30'
                      : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900 border border-transparent'
                  }`}
                >
                  <div className="flex items-center gap-2.5 min-w-0 flex-1">
                    <MessageSquare
                      className={`w-4 h-4 shrink-0 ${
                        isActive ? 'text-indigo-400' : 'text-slate-500 group-hover:text-slate-300'
                      }`}
                    />

                    {isEditing ? (
                      <input
                        type="text"
                        value={editTitle}
                        onChange={(e) => setEditTitle(e.target.value)}
                        onClick={(e) => e.stopPropagation()}
                        className="bg-slate-900 border border-indigo-500 text-slate-100 rounded px-1.5 py-0.5 text-xs w-full outline-none"
                        autoFocus
                      />
                    ) : (
                      <div className="truncate flex-1">
                        <div className="truncate font-medium">{c.title}</div>
                        {c.last_message_preview && (
                          <div className="truncate text-[10px] text-slate-500 mt-0.5">
                            {c.last_message_preview}
                          </div>
                        )}
                      </div>
                    )}
                  </div>

                  {/* Actions */}
                  <div className="flex items-center gap-1 shrink-0 ml-1">
                    {isEditing ? (
                      <>
                        <button
                          onClick={(e) => saveRename(c.id, e)}
                          className="p-1 hover:text-emerald-400 text-slate-400"
                        >
                          <Check className="w-3.5 h-3.5" />
                        </button>
                        <button
                          onClick={cancelRename}
                          className="p-1 hover:text-rose-400 text-slate-400"
                        >
                          <X className="w-3.5 h-3.5" />
                        </button>
                      </>
                    ) : (
                      <div className="hidden group-hover:flex items-center gap-0.5">
                        <button
                          onClick={(e) => startRename(c, e)}
                          className="p-1 hover:text-slate-200 text-slate-500"
                          title="Rename"
                        >
                          <Edit2 className="w-3 h-3" />
                        </button>
                        <button
                          onClick={(e) => handleDelete(c.id, e)}
                          className="p-1 hover:text-rose-400 text-slate-500"
                          title="Delete"
                        >
                          <Trash2 className="w-3 h-3" />
                        </button>
                      </div>
                    )}
                  </div>
                </div>
              );
            })
          )}
        </div>
      </div>
    </>
  );
};
