"use client";

import { useEffect, useRef } from "react";

import type { ChatMessage } from "@/lib/api";

import { Composer } from "./Composer";
import { MessageBubble } from "./MessageBubble";

interface ChatStagePaneProps {
  messages: ChatMessage[];
  focusedAssistantId: string | null;
  pendingAssistant?: ChatMessage | null;
  draft: string;
  onDraftChange: (value: string) => void;
  onSubmit: () => void;
  onFocusAssistant: (message: ChatMessage) => void;
  onCitationClick: (message: ChatMessage, n: number) => void;
  sending?: boolean;
  emptyState?: React.ReactNode;
}

export function ChatStagePane({
  messages,
  focusedAssistantId,
  pendingAssistant,
  draft,
  onDraftChange,
  onSubmit,
  onFocusAssistant,
  onCitationClick,
  sending,
  emptyState,
}: ChatStagePaneProps) {
  const scrollRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to the bottom whenever the message list changes or the
  // assistant placeholder toggles on/off.
  useEffect(() => {
    const el = scrollRef.current;
    if (!el) return;
    el.scrollTop = el.scrollHeight;
  }, [messages.length, pendingAssistant?.id, sending]);

  const hasAnything = messages.length > 0 || !!pendingAssistant;

  return (
    <section className="pane chat-stage">
      <div className="chat-scroll" ref={scrollRef}>
        {!hasAnything && emptyState ? (
          emptyState
        ) : (
          <div className="chat-column">
            {messages.map((message) => (
              <MessageBubble
                key={message.id}
                message={message}
                focused={message.role === "assistant" && message.id === focusedAssistantId}
                onFocus={
                  message.role === "assistant"
                    ? () => onFocusAssistant(message)
                    : undefined
                }
                onCitationClick={
                  message.role === "assistant"
                    ? (n) => onCitationClick(message, n)
                    : undefined
                }
              />
            ))}
            {pendingAssistant && (
              <MessageBubble
                key={pendingAssistant.id}
                message={pendingAssistant}
                loading
              />
            )}
          </div>
        )}
      </div>
      <Composer
        value={draft}
        onChange={onDraftChange}
        onSubmit={onSubmit}
        disabled={sending}
      />
    </section>
  );
}
