"use client";

import { useEffect, useRef, useState } from "react";

import { DocumentRenderer } from "./DocumentRenderer";

interface DocViewerPaneProps {
  path: string | null;
  content: string | null;
  loading: boolean;
  error: string | null;
  onSelectPassage: (text: string) => void;
}

interface FloatingPos {
  top: number;
  left: number;
}

export function DocViewerPane({
  path,
  content,
  loading,
  error,
  onSelectPassage,
}: DocViewerPaneProps) {
  const surfaceRef = useRef<HTMLDivElement | null>(null);
  const [selectedText, setSelectedText] = useState<string>("");
  const [pos, setPos] = useState<FloatingPos | null>(null);

  useEffect(() => {
    function onSelectionChange() {
      const sel = window.getSelection();
      if (!sel || sel.rangeCount === 0 || sel.isCollapsed) {
        setSelectedText("");
        setPos(null);
        return;
      }
      const range = sel.getRangeAt(0);
      const surface = surfaceRef.current;
      if (!surface) return;
      // Only fire when the selection is fully inside the doc surface.
      if (!surface.contains(range.commonAncestorContainer)) {
        setSelectedText("");
        setPos(null);
        return;
      }
      const text = sel.toString().trim();
      if (!text) {
        setSelectedText("");
        setPos(null);
        return;
      }
      const rect = range.getBoundingClientRect();
      const surfaceRect = surface.getBoundingClientRect();
      setSelectedText(text);
      setPos({
        // Position relative to the scrollable surface.
        top: rect.top - surfaceRect.top + surface.scrollTop - 42,
        left: Math.max(
          8,
          rect.left - surfaceRect.left + surface.scrollLeft,
        ),
      });
    }

    document.addEventListener("selectionchange", onSelectionChange);
    return () => {
      document.removeEventListener("selectionchange", onSelectionChange);
    };
  }, [path]);

  const fileName = path ? path.split("/").pop() ?? path : null;

  return (
    <section className="pane">
      <div className="pane-head">
        <div className="flex items-center gap-3 min-w-0">
          {fileName ? (
            <>
              <div className="inline-flex items-center gap-2 rounded-md border border-white/10 bg-white/[0.02] px-2.5 py-1 text-[12px] text-white/90 max-w-[360px]">
                <span className="truncate">{fileName}</span>
              </div>
              {path && path.includes("/") && (
                <span className="font-mono text-[11px] text-white/40 truncate">
                  {path.substring(0, path.lastIndexOf("/"))}
                </span>
              )}
            </>
          ) : (
            <span className="pane-title">Document</span>
          )}
        </div>
      </div>

      <div
        ref={surfaceRef}
        className="relative flex-1 overflow-auto min-h-0 px-12 py-10"
        style={{
          background:
            "radial-gradient(ellipse 700px 240px at 50% -10%, rgba(6, 182, 212, 0.08), transparent 70%), #050505",
        }}
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
          <>
            <DocumentRenderer path={path} content={content} />

            {selectedText && pos && (
              <button
                type="button"
                className="sel-action"
                style={{ top: pos.top, left: pos.left }}
                onMouseDown={(e) => {
                  // Prevent losing the selection when the button is clicked.
                  e.preventDefault();
                }}
                onClick={() => {
                  onSelectPassage(selectedText);
                }}
              >
                <span className="arrow">↳</span>
                Find related code for this paragraph
                <span className="kbd">⌘ ↵</span>
              </button>
            )}
          </>
        ) : null}
      </div>
    </section>
  );
}
