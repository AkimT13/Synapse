"use client";

import { Highlight, type Token, themes } from "prism-react-renderer";
import { File as FileIcon, Copy, MoreHorizontal, List } from "lucide-react";
import { useMemo, useEffect, useCallback } from "react";

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

// Try to extract a function / class name near the start of the selected text.
function detectAnchor(text: string): string | null {
  const m =
    text.match(/\bdef\s+([A-Za-z_][A-Za-z0-9_]*)/) ??
    text.match(/\bclass\s+([A-Za-z_][A-Za-z0-9_]*)/) ??
    text.match(/\bfunction\s+([A-Za-z_][A-Za-z0-9_]*)/);
  return m ? m[1] : null;
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

  const computeRange = useCallback(
    (start: number, end: number): CodeSelection | null => {
      if (!filePath) return null;
      const a = Math.min(start, end);
      const b = Math.max(start, end);
      const slice = lines.slice(a - 1, b).join("\n");
      return {
        file: filePath,
        text: slice,
        startLine: a,
        endLine: b,
      };
    },
    [filePath, lines],
  );

  const onRowClick = useCallback(
    (lineNumber: number, event: React.MouseEvent) => {
      if (event.ctrlKey || event.metaKey) {
        // clear
        setSelection(null);
        return;
      }
      if (event.shiftKey && selection && filePath) {
        const range = computeRange(selection.startLine, lineNumber);
        if (range) setSelection(range);
        return;
      }
      // click = set a single-line selection & anchor for future shift-click
      const range = computeRange(lineNumber, lineNumber);
      if (range) setSelection(range);
    },
    [computeRange, filePath, selection, setSelection],
  );

  // Keyboard shortcut: Cmd/Ctrl+Enter while a selection exists.
  useEffect(() => {
    if (!selection) return;
    const handler = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "Enter") {
        e.preventDefault();
        onFindRelated();
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [selection, onFindRelated]);

  const selectedBytes = selection ? new TextEncoder().encode(selection.text).length : 0;
  const selectedLines = selection ? selection.endLine - selection.startLine + 1 : 0;
  const anchorName = selection ? detectAnchor(selection.text) : null;

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
        <div style={{ display: "flex", alignItems: "center", gap: 12, minWidth: 0 }}>
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
        <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
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

      <div className="code-surface" id="codeSurface" style={{ position: "relative" }}>
        {selection && filePath === selection.file ? (
          <button
            type="button"
            className="sel-action"
            style={{
              top: Math.max(12, (selection.startLine - 1) * 21 - 44),
              left: 72,
            }}
            onClick={onFindRelated}
            disabled={retrievalLoading}
          >
            <span className="arrow">↳</span>
            {retrievalLoading ? (
              <span>Searching…</span>
            ) : (
              <>
                Find related knowledge
                {anchorName ? (
                  <>
                    {" for "}
                    <span className="kbd">{anchorName}</span>
                  </>
                ) : null}
              </>
            )}
            <span className="kbd">⌘ ↵</span>
          </button>
        ) : null}

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
                    onClick={(e) => onRowClick(lineNumber, e)}
                    style={{ cursor: "pointer" }}
                  >
                    <span className="ln">{lineNumber}</span>
                    <span className="cn">
                      {line.length === 0 ? (
                        "\u00a0"
                      ) : (
                        line.map((token, key) => {
                          const cls = tokenClass(token.types);
                          return (
                            <span key={key} className={cls}>
                              {token.content}
                            </span>
                          );
                        })
                      )}
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
              SEL {selectedLines} {selectedLines === 1 ? "line" : "lines"}, {selectedBytes} bytes
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
