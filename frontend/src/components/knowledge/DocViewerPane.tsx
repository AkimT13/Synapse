"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import { HeaderAction } from "@/components/workspace/HeaderAction";

import { DocumentRenderer } from "./DocumentRenderer";

interface DocViewerPaneProps {
  path: string | null;
  content: string | null;
  loading: boolean;
  error: string | null;
  onSelectPassage: (text: string) => void;
  retrievalLoading: boolean;
}

/**
 * Knowledge document viewer. Native text selection runs as usual on
 * the prose; we capture the selection on `mouseup` only (not on every
 * `selectionchange` fire, which was the source of the previous flicker).
 *
 * The retrieval trigger lives in the pane header, matching the code
 * pane's placement — consistent UX, no positioning math, no re-renders
 * during the drag.
 */
export function DocViewerPane({
  path,
  content,
  loading,
  error,
  onSelectPassage,
  retrievalLoading,
}: DocViewerPaneProps) {
  const surfaceRef = useRef<HTMLDivElement | null>(null);
  const [captured, setCaptured] = useState<string>("");

  // Capture the final selection when the user releases. We deliberately
  // avoid clearing on mousedown — each setState triggers a React render,
  // and a render during an active drag can force ReactMarkdown to rebuild
  // DOM nodes, which the browser interprets as the selected range being
  // destroyed. So: no mid-drag state churn, one read on mouseup.
  const onSurfaceMouseUp = useCallback(() => {
    const surface = surfaceRef.current;
    if (!surface) return;
    const selection = window.getSelection();
    if (!selection || selection.rangeCount === 0 || selection.isCollapsed) {
      // Plain click with no drag — drop any stale capture.
      setCaptured((prev) => (prev ? "" : prev));
      return;
    }
    const range = selection.getRangeAt(0);
    if (!surface.contains(range.commonAncestorContainer)) {
      setCaptured((prev) => (prev ? "" : prev));
      return;
    }
    const text = selection.toString().trim();
    if (!text) {
      setCaptured((prev) => (prev ? "" : prev));
      return;
    }
    setCaptured(text);
  }, []);

  // Whenever the active document changes, drop any captured text — it's
  // no longer meaningful against a different file.
  useEffect(() => {
    setCaptured("");
  }, [path]);

  // Keyboard: ⌘↵ fires retrieval if we have a capture, Escape clears.
  useEffect(() => {
    const handler = (event: KeyboardEvent) => {
      if ((event.metaKey || event.ctrlKey) && event.key === "Enter") {
        if (captured && !retrievalLoading) {
          event.preventDefault();
          onSelectPassage(captured);
        }
        return;
      }
      if (event.key === "Escape" && captured) {
        event.preventDefault();
        setCaptured("");
        window.getSelection()?.removeAllRanges();
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [captured, onSelectPassage, retrievalLoading]);

  const fileName = path ? path.split("/").pop() ?? path : null;
  const headerTarget = captured
    ? truncateForChip(captured)
    : null;

  return (
    <section className="pane">
      <div className="pane-head">
        <div className="flex items-center gap-3 min-w-0">
          {fileName ? (
            <>
              <div className="code-tab">
                <span className="truncate">{fileName}</span>
              </div>
              {path && path.includes("/") && (
                <span className="breadcrumb font-mono text-[11px] text-white/40 truncate">
                  {path.substring(0, path.lastIndexOf("/"))}
                </span>
              )}
            </>
          ) : (
            <span className="pane-title">Document</span>
          )}
        </div>
        <HeaderAction
          label="Find related code"
          target={headerTarget}
          onActivate={() => captured && onSelectPassage(captured)}
          disabled={!captured}
          busy={retrievalLoading}
        />
      </div>

      <div
        ref={surfaceRef}
        className="doc-surface relative flex-1 overflow-auto min-h-0 px-12 py-10"
        style={{
          background:
            "radial-gradient(ellipse 700px 240px at 50% -10%, rgba(6, 182, 212, 0.08), transparent 70%), #050505",
        }}
        onMouseUp={onSurfaceMouseUp}
      >
        {!path ? (
          <div className="empty h-full">
            Select a document from the left to preview it here.
          </div>
        ) : loading ? (
          <div className="empty h-full">Loading document…</div>
        ) : error ? (
          <div className="empty h-full text-red-300/80">{error}</div>
        ) : content !== null ? (
          <DocumentRenderer path={path} content={content} />
        ) : null}
      </div>
    </section>
  );
}

function truncateForChip(text: string, max = 32): string {
  const cleaned = text.replace(/\s+/g, " ").trim();
  if (cleaned.length <= max) return cleaned;
  return cleaned.slice(0, max).trimEnd() + "…";
}
