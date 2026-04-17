"use client";

import { Plus, Trash2 } from "lucide-react";

import type { ConversationHeader } from "@/lib/api";
import { cn } from "@/lib/cn";

interface ConversationListPaneProps {
  conversations: ConversationHeader[];
  activeId: string | null;
  onSelect: (conversation: ConversationHeader) => void;
  onCreate: () => void;
  onDelete: (conversation: ConversationHeader) => void;
  creating?: boolean;
}

// Format "updated_at" as a short, lower-case relative hint. We favour
// terse output because the pane is narrow.
function relativeLabel(iso: string): string {
  const then = new Date(iso).getTime();
  if (Number.isNaN(then)) return "";
  const now = Date.now();
  const diffMs = now - then;
  const minute = 60_000;
  const hour = 60 * minute;
  const day = 24 * hour;
  if (diffMs < 2 * minute) return "just now";
  if (diffMs < hour) return `${Math.floor(diffMs / minute)} min ago`;
  if (diffMs < day) return "today";
  if (diffMs < 2 * day) return "yesterday";
  if (diffMs < 7 * day) return `${Math.floor(diffMs / day)} days ago`;
  return new Date(iso).toLocaleDateString();
}

export function ConversationListPane({
  conversations,
  activeId,
  onSelect,
  onCreate,
  onDelete,
  creating,
}: ConversationListPaneProps) {
  return (
    <section className="pane">
      <div className="pane-head">
        <span className="pane-title">Conversations</span>
        <button
          type="button"
          className="tool"
          aria-label="New conversation"
          onClick={onCreate}
          disabled={creating}
        >
          <Plus size={14} />
        </button>
      </div>
      <div className="pane-body" style={{ padding: 8 }}>
        {conversations.length === 0 ? (
          <div className="empty" style={{ padding: 16, fontSize: 12 }}>
            No conversations yet.
          </div>
        ) : (
          conversations.map((conversation) => (
            <button
              key={conversation.id}
              type="button"
              className={cn(
                "convo-item",
                conversation.id === activeId && "active",
              )}
              onClick={() => onSelect(conversation)}
            >
              <div className="convo-title">{conversation.title || "Untitled"}</div>
              <div className="convo-meta">{relativeLabel(conversation.updated_at)}</div>
              <button
                type="button"
                aria-label="Delete conversation"
                className="convo-delete"
                onClick={(event) => {
                  event.stopPropagation();
                  onDelete(conversation);
                }}
              >
                <Trash2 size={12} />
              </button>
            </button>
          ))
        )}
      </div>
    </section>
  );
}
