"use client";

import { RefreshCw } from "lucide-react";

import { ResultCard } from "@/components/workspace/ResultCard";
import type { RetrievalResponse } from "@/lib/api";
import type { CodeSelection } from "@/lib/stores";

interface RelatedKnowledgePaneProps {
  selection: CodeSelection | null;
  response: RetrievalResponse | null;
  loading: boolean;
  onRefresh: () => void;
  selectionLabel: string | null;
}

function encodePath(path: string): string {
  return path.split("/").map(encodeURIComponent).join("/");
}

export function RelatedKnowledgePane({
  selection,
  response,
  loading,
  onRefresh,
  selectionLabel,
}: RelatedKnowledgePaneProps) {
  return (
    <section className="pane">
      <div className="pane-head">
        <div style={{ display: "flex", flexDirection: "column", gap: 6, minWidth: 0 }}>
          <span className="pane-title">Related knowledge</span>
          {selectionLabel ? (
            <span className="pane-selection-chip truncate">
              selection · {selectionLabel}
            </span>
          ) : (
            <span className="pane-sub">No selection</span>
          )}
        </div>
        <button
          type="button"
          className="tool"
          aria-label="Refresh"
          onClick={onRefresh}
          disabled={loading || !selection}
        >
          <RefreshCw size={14} />
        </button>
      </div>

      <div className="pane-body">
        {loading ? (
          <div className="empty">
            <span className="animate-pulse">Searching…</span>
          </div>
        ) : !response ? (
          <div className="empty">Select code to find related domain knowledge</div>
        ) : response.results.length === 0 ? (
          <div className="empty">No related knowledge found for this selection.</div>
        ) : (
          <div>
            {response.used_fallback ? (
              <div
                style={{
                  margin: "10px 14px 0",
                  padding: "8px 12px",
                  borderRadius: 10,
                  border: "1px solid rgba(6, 182, 212, 0.25)",
                  background: "rgba(6, 182, 212, 0.06)",
                  color: "#67e8f9",
                  fontSize: 11,
                  letterSpacing: "0.12em",
                  textTransform: "uppercase",
                }}
              >
                Showing broader context
              </div>
            ) : null}

            {response.explanation ? (
              <div
                style={{
                  margin: "10px 14px 0",
                  padding: "12px 14px",
                  borderRadius: 12,
                  border: "1px solid rgba(139, 92, 246, 0.2)",
                  background: "rgba(139, 92, 246, 0.06)",
                  color: "#e5e5e5",
                  fontSize: 13,
                  lineHeight: 1.55,
                }}
              >
                {response.explanation}
              </div>
            ) : null}

            {response.results.map((result) => (
              <ResultCard
                key={`${result.chunk_type}-${result.source_file}-${result.index}`}
                result={result}
                href={`/knowledge/${encodePath(result.source_file)}`}
              />
            ))}
          </div>
        )}
      </div>
    </section>
  );
}
