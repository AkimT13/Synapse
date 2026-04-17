"use client";

import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import type { ReactNode } from "react";

import type { ChatMessage, SourceRef } from "@/lib/api";
import { cn } from "@/lib/cn";

import { CitationBadge } from "./CitationBadge";

interface MessageBubbleProps {
  message: ChatMessage;
  focused?: boolean;
  loading?: boolean;
  onFocus?: () => void;
  onCitationClick?: (n: number) => void;
}

// Split assistant content on [N] markers, interleaving markdown-rendered
// prose with clickable citation chips. Markdown is only applied to the
// non-citation slices so we never lose a [N] across a code fence.
function renderAssistantContent(
  content: string,
  sources: SourceRef[],
  onCitationClick?: (n: number) => void,
): ReactNode[] {
  const parts = content.split(/(\[\d+\])/g);
  return parts
    .map((part, index) => {
      if (!part) return null;
      const match = part.match(/^\[(\d+)\]$/);
      if (match) {
        const n = parseInt(match[1], 10);
        const source = sources.find((s) => s.index === n);
        return (
          <CitationBadge
            key={`cite-${index}`}
            n={n}
            source={source}
            onActivate={onCitationClick}
          />
        );
      }
      return (
        <ReactMarkdown
          key={`md-${index}`}
          remarkPlugins={[remarkGfm]}
          components={{
            // Unwrap the outer <p> from ReactMarkdown when we render a
            // fragment mid-line; otherwise citations break the paragraph.
            p: ({ children }) => <>{children}</>,
          }}
        >
          {part}
        </ReactMarkdown>
      );
    })
    .filter(Boolean) as ReactNode[];
}

export function MessageBubble({
  message,
  focused,
  loading,
  onFocus,
  onCitationClick,
}: MessageBubbleProps) {
  if (message.role === "user") {
    return <div className="msg-user">{message.content}</div>;
  }

  const sourceCount = message.sources?.length ?? 0;

  return (
    <div
      className={cn("msg-asst", focused && "focused")}
      onClick={onFocus}
      role="button"
      tabIndex={0}
      onKeyDown={(event) => {
        if (event.key === "Enter" || event.key === " ") {
          onFocus?.();
        }
      }}
    >
      <div className="asst-head">
        <span className="chip-dot" />
        <span>Synapse</span>
        {!loading && sourceCount > 0 && (
          <span className="gen-time">{sourceCount} source{sourceCount === 1 ? "" : "s"}</span>
        )}
      </div>
      <div className="asst-body">
        {loading ? (
          <div className="asst-loading" aria-label="Thinking">
            <span />
            <span />
            <span />
          </div>
        ) : (
          renderAssistantContent(
            message.content,
            message.sources ?? [],
            onCitationClick,
          )
        )}
      </div>
    </div>
  );
}
