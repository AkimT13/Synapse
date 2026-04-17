"use client";

import { Code2, FileText, Send, Sparkles } from "lucide-react";
import { useEffect, useRef } from "react";

import { useChat } from "@/lib/stores";
import { cn } from "@/lib/cn";

interface ComposerProps {
  value: string;
  onChange: (value: string) => void;
  onSubmit: () => void;
  disabled?: boolean;
}

export function Composer({ value, onChange, onSubmit, disabled }: ComposerProps) {
  const { scope, setScope } = useChat();
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Auto-grow the textarea as the user types, up to its CSS max-height.
  useEffect(() => {
    const ta = textareaRef.current;
    if (!ta) return;
    ta.style.height = "auto";
    ta.style.height = `${Math.min(ta.scrollHeight, 220)}px`;
  }, [value]);

  const canSubmit = !disabled && value.trim().length > 0;

  return (
    <div className="composer-dock">
      <div className="composer">
        <textarea
          ref={textareaRef}
          value={value}
          placeholder="Ask about your code, your docs, or the link between them…"
          onChange={(event) => onChange(event.target.value)}
          onKeyDown={(event) => {
            // Cmd/Ctrl + Enter submits; plain Enter inserts newline.
            if (event.key === "Enter" && (event.metaKey || event.ctrlKey)) {
              event.preventDefault();
              if (canSubmit) onSubmit();
            }
          }}
        />
        <div className="composer-row">
          <button
            type="button"
            className={cn("chip", scope === "all" && "active")}
            onClick={() => setScope("all")}
          >
            <Sparkles size={12} />
            Code + Knowledge
          </button>
          <button
            type="button"
            className={cn("chip", scope === "code" && "active")}
            onClick={() => setScope("code")}
          >
            <Code2 size={12} />
            Code only
          </button>
          <button
            type="button"
            className={cn("chip", scope === "knowledge" && "active")}
            onClick={() => setScope("knowledge")}
          >
            <FileText size={12} />
            Docs only
          </button>
          <span style={{ flex: 1 }} />
          <span className="composer-hint">Cmd + Enter to send</span>
          <button
            type="button"
            className="send-btn"
            onClick={onSubmit}
            disabled={!canSubmit}
            aria-label="Send"
          >
            <Send size={16} />
          </button>
        </div>
      </div>
    </div>
  );
}
