"use client";

import { RefreshCw } from "lucide-react";
import { useRef } from "react";

import { CitedText } from "@/components/workspace/CitedText";
import { ResultCard } from "@/components/workspace/ResultCard";
import type { RetrievalResponse } from "@/lib/api";
import { cn } from "@/lib/cn";

interface RelatedCodePaneProps {
  selectionText: string | null;
  loading: boolean;
  error: string | null;
  response: RetrievalResponse | null;
  onRefresh: () => void;
}

function truncateChip(text: string, max = 48): string {
  if (text.length <= max) return text;
  return text.slice(0, max).trimEnd() + "…";
}

export function RelatedCodePane({
  selectionText,
  loading,
  error,
  response,
  onRefresh,
}: RelatedCodePaneProps) {
  const bodyRef = useRef<HTMLDivElement | null>(null);
  return (
    <section className="pane">
      <div className="pane-head">
        <div className="flex flex-col gap-1.5 min-w-0">
          <span className="pane-title">Related code</span>
          {selectionText ? (
            <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-md bg-cyan-500/10 text-cyan-300 font-mono text-[10px] tracking-[0.12em] max-w-[280px] truncate">
              selection · {truncateChip(selectionText)}
            </span>
          ) : (
            <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-md bg-white/[0.04] text-white/40 font-mono text-[10px] tracking-[0.12em]">
              no selection
            </span>
          )}
        </div>
        <button
          type="button"
          aria-label="Refresh"
          onClick={onRefresh}
          disabled={!selectionText || loading}
          className="w-[30px] h-[30px] inline-flex items-center justify-center rounded-lg text-white/40 border border-transparent hover:text-white hover:bg-white/[0.04] hover:border-white/10 transition disabled:opacity-40 disabled:cursor-not-allowed"
        >
          <RefreshCw size={14} className={cn(loading && "animate-spin")} />
        </button>
      </div>

      <div className="pane-body" ref={bodyRef}>
        {!selectionText ? (
          <div className="empty">
            Select a passage to find code that implements it
          </div>
        ) : loading ? (
          <div className="empty">Searching related code…</div>
        ) : error ? (
          <div className="empty text-red-300/80">{error}</div>
        ) : response ? (
          <>
            {(response.explanation || response.is_implemented !== null) && (
              <div className="mx-[14px] my-2.5 rounded-xl border border-white/10 bg-white/[0.02] p-4">
                {response.is_implemented !== null &&
                  response.is_implemented !== undefined && (
                    <div className="mb-2">
                      <span
                        className={cn(
                          "inline-flex items-center gap-1 rounded-full border px-2.5 py-0.5 text-[10px] tracking-[0.18em] uppercase font-mono",
                          response.is_implemented
                            ? "border-emerald-500/40 text-emerald-300 bg-emerald-500/10"
                            : "border-violet-500/40 text-violet-300 bg-violet-500/10",
                        )}
                      >
                        {response.is_implemented ? "implemented" : "not implemented"}
                      </span>
                    </div>
                  )}
                {response.explanation && (
                  <div className="text-[13px] leading-relaxed text-white/75">
                    <CitedText
                      text={response.explanation}
                      containerRef={bodyRef}
                    />
                  </div>
                )}
              </div>
            )}

            {response.results.length === 0 ? (
              <div className="empty">No related code found.</div>
            ) : (
              response.results.map((ref, idx) => (
                <ResultCard
                  key={`${ref.source_file}-${ref.index}-${idx}`}
                  result={ref}
                  citationIndex={ref.index}
                  href={`/code?file=${encodeURIComponent(ref.source_file)}`}
                />
              ))
            )}
          </>
        ) : null}
      </div>
    </section>
  );
}
