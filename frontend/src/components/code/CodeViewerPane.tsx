"use client";

import { File as FileIcon, Copy, MoreHorizontal, List } from "lucide-react";
import { Highlight, type Token, themes } from "prism-react-renderer";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { HeaderAction } from "@/components/workspace/HeaderAction";
import { cn } from "@/lib/cn";
import type { CodeSelection } from "@/lib/stores";

interface CodeViewerPaneProps {
  filePath: string | null;
  source: string;
  loading: boolean;
  selection: CodeSelection | null;
  setSelection: (selection: CodeSelection | null) => void;
  onFindRelated: () => void;
  retrievalLoading: boolean;
}

// Map prism token types to the existing .kw/.cls/.str/.com/.fn/.pun/.num/.dec classes.
function tokenClass(types: string[]): string {
  if (types.includes("comment")) return "com";
  if (types.includes("string")) return "str";
  if (types.includes("number")) return "num";
  if (types.includes("keyword")) return "kw";
  if (types.includes("builtin")) return "cls";
  if (types.includes("class-name")) return "cls";
  if (types.includes("function")) return "fn";
  if (types.includes("decorator")) return "dec";
  if (types.includes("punctuation")) return "pun";
  if (types.includes("operator")) return "pun";
  return "";
}

function languageFromPath(path: string | null): string {
  if (!path) return "python";
  const ext = path.split(".").pop()?.toLowerCase() ?? "";
  switch (ext) {
    case "py":
      return "python";
    case "ts":
    case "tsx":
      return "tsx";
    case "js":
    case "jsx":
      return "jsx";
    case "java":
      return "java";
    case "c":
    case "h":
      return "c";
    case "cpp":
    case "hpp":
    case "cc":
      return "cpp";
    case "rs":
      return "rust";
    case "go":
      return "go";
    case "rb":
      return "ruby";
    default:
      return "python";
  }
}

function breadcrumbSegments(path: string | null): { parts: string[]; leaf: string } {
  if (!path) return { parts: [], leaf: "" };
  const pieces = path.split("/");
  const leaf = pieces.pop() ?? "";
  return { parts: pieces, leaf };
}

// Extract a function / class / def name near the start of the selection so
// the header action can show it as a concrete target.
function detectAnchor(text: string): string | null {
  const match =
    text.match(/\bdef\s+([A-Za-z_][A-Za-z0-9_]*)/) ??
    text.match(/\bclass\s+([A-Za-z_][A-Za-z0-9_]*)/) ??
    text.match(/\bfunction\s+([A-Za-z_][A-Za-z0-9_]*)/);
  return match ? match[1] : null;
}

// Walk from an event's target up to the nearest .code-row and extract
// its data-line attribute. Returns null if the event didn't land on a
// known row (whitespace, sidebar, etc).
function lineFromEvent(event: MouseEvent | React.MouseEvent): number | null {
  const target = event.target as Element | null;
  const row = target?.closest?.<HTMLElement>(".code-row[data-line]");
  if (!row) return null;
  const parsed = parseInt(row.dataset.line ?? "", 10);
  return Number.isNaN(parsed) ? null : parsed;
}

export function CodeViewerPane({
  filePath,
  source,
  loading,
  selection,
  setSelection,
  onFindRelated,
  retrievalLoading,
}: CodeViewerPaneProps) {
  const lines = useMemo(() => source.split("\n"), [source]);
  const language = languageFromPath(filePath);
  const { parts, leaf } = breadcrumbSegments(filePath);

  // Drag state lives in a ref because only mouseup commits a re-render
  // via setSelection; tracking drag in state would churn needlessly.
  const anchorRef = useRef<number | null>(null);
  const [dragging, setDragging] = useState(false);

  const computeRange = useCallback(
    (start: number, end: number): CodeSelection | null => {
      if (!filePath) return null;
      const low = Math.min(start, end);
      const high = Math.max(start, end);
      const slice = lines.slice(low - 1, high).join("\n");
      return {
        file: filePath,
        text: slice,
        startLine: low,
        endLine: high,
      };
    },
    [filePath, lines],
  );

  // Click / drag selection. Shift-click extends from the existing start,
  // otherwise a fresh drag pins the anchor on mousedown and the head
  // tracks the row under the cursor until mouseup.
  const onRowMouseDown = useCallback(
    (event: React.MouseEvent) => {
      if (event.button !== 0) return;
      const line = lineFromEvent(event);
      if (line === null || !filePath) return;
      event.preventDefault();

      if (event.shiftKey && selection) {
        const range = computeRange(selection.startLine, line);
        if (range) setSelection(range);
        return;
      }

      anchorRef.current = line;
      setDragging(true);
      const range = computeRange(line, line);
      if (range) setSelection(range);
    },
    [computeRange, filePath, selection, setSelection],
  );

  // Window-level move/up so leaving the surface mid-drag doesn't strand
  // the state — the user can drag into the sidebar and back, release
  // anywhere, and the selection always resolves cleanly.
  useEffect(() => {
    if (!dragging) return;

    const onMove = (event: MouseEvent) => {
      const anchor = anchorRef.current;
      if (anchor === null) return;
      const line = lineFromEvent(event);
      if (line === null) return;
      const range = computeRange(anchor, line);
      if (range) setSelection(range);
    };

    const onUp = () => {
      setDragging(false);
      anchorRef.current = null;
    };

    window.addEventListener("mousemove", onMove);
    window.addEventListener("mouseup", onUp);
    return () => {
      window.removeEventListener("mousemove", onMove);
      window.removeEventListener("mouseup", onUp);
    };
  }, [dragging, computeRange, setSelection]);

  // Keyboard: ⌘↵ fires retrieval, Escape clears the selection.
  useEffect(() => {
    const handler = (event: KeyboardEvent) => {
      if ((event.metaKey || event.ctrlKey) && event.key === "Enter") {
        if (selection && !retrievalLoading) {
          event.preventDefault();
          onFindRelated();
        }
        return;
      }
      if (event.key === "Escape" && selection) {
        event.preventDefault();
        setSelection(null);
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [onFindRelated, retrievalLoading, selection, setSelection]);

  const selectedBytes = selection
    ? new TextEncoder().encode(selection.text).length
    : 0;
  const selectedLines = selection
    ? selection.endLine - selection.startLine + 1
    : 0;
  const anchorName = selection ? detectAnchor(selection.text) : null;
  const headerTarget =
    anchorName ??
    (selection ? `LN ${selection.startLine}–${selection.endLine}` : null);

  if (loading && !source) {
    return (
      <section className="pane code-stage">
        <div className="pane-head">
          <span className="pane-title">Code</span>
        </div>
        <div className="empty">Loading…</div>
      </section>
    );
  }

  if (!filePath) {
    return (
      <section className="pane code-stage">
        <div className="pane-head">
          <span className="pane-title">Code</span>
        </div>
        <div className="empty">Select a file from the tree to view.</div>
      </section>
    );
  }

  return (
    <section className="pane code-stage">
      <div className="pane-head">
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: 12,
            minWidth: 0,
          }}
        >
          <div className="code-tab">
            <FileIcon size={12} />
            <span className="truncate">{leaf}</span>
          </div>
          <div className="breadcrumb min-w-0">
            {parts.map((part, i) => (
              <span key={i} className="flex items-center gap-2 min-w-0">
                <span className="truncate">{part}</span>
                <span className="sep">/</span>
              </span>
            ))}
            <span className="leaf truncate">{leaf}</span>
          </div>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <HeaderAction
            label="Find related knowledge"
            target={headerTarget}
            onActivate={onFindRelated}
            disabled={!selection}
            busy={retrievalLoading}
          />
          <span className="badge v">{language.toUpperCase()}</span>
          <button className="tool" aria-label="Symbols" type="button">
            <List size={14} />
          </button>
          <button
            className="tool"
            aria-label="Copy"
            type="button"
            onClick={() => {
              if (typeof navigator !== "undefined" && navigator.clipboard) {
                navigator.clipboard.writeText(source).catch(() => {});
              }
            }}
          >
            <Copy size={14} />
          </button>
          <button className="tool" aria-label="More" type="button">
            <MoreHorizontal size={14} />
          </button>
        </div>
      </div>

      <div
        className="code-surface"
        id="codeSurface"
        onMouseDown={onRowMouseDown}
      >
        <Highlight code={source} language={language} theme={themes.nightOwl}>
          {({ tokens }) => (
            <>
              {tokens.map((line: Token[], i: number) => {
                const lineNumber = i + 1;
                const isSelected =
                  selection !== null &&
                  lineNumber >= selection.startLine &&
                  lineNumber <= selection.endLine;
                return (
                  <div
                    key={i}
                    className={cn("code-row", isSelected && "selected")}
                    data-line={lineNumber}
                  >
                    <span className="ln">{lineNumber}</span>
                    <span className="cn">
                      {line.length === 0
                        ? "\u00a0"
                        : line.map((token, key) => {
                            const cls = tokenClass(token.types);
                            return (
                              <span key={key} className={cls}>
                                {token.content}
                              </span>
                            );
                          })}
                    </span>
                  </div>
                );
              })}
            </>
          )}
        </Highlight>
      </div>

      <div className="meta-strip">
        {selection ? (
          <>
            <span>
              LN {selection.startLine}–{selection.endLine}
            </span>
            <span style={{ color: "#404040" }}>·</span>
            <span>
              SEL {selectedLines} {selectedLines === 1 ? "line" : "lines"},{" "}
              {selectedBytes} bytes
            </span>
            <span style={{ color: "#404040" }}>·</span>
            <span>FILE</span>
            <span style={{ color: "#d4d4d4" }}>{filePath}</span>
          </>
        ) : (
          <>
            <span>NO SELECTION</span>
            <span style={{ color: "#404040" }}>·</span>
            <span>FILE</span>
            <span style={{ color: "#d4d4d4" }}>{filePath}</span>
            <span style={{ color: "#404040" }}>·</span>
            <span>{lines.length} LINES</span>
          </>
        )}
      </div>
    </section>
  );
}
