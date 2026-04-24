"use client";

import { BookMarked, Sparkles } from "lucide-react";

import type { FileReviewResponse, ReviewEvidenceSource } from "@/lib/api";
import { cn } from "@/lib/cn";

interface DriftEvidencePaneProps {
  review: FileReviewResponse | null;
  loading: boolean;
  error: string | null;
}

export function DriftEvidencePane({
  review,
  loading,
  error,
}: DriftEvidencePaneProps) {
  return (
    <section className="pane">
      <div className="pane-head">
        <div className="flex min-w-0 flex-col gap-1">
          <span className="pane-title">Evidence</span>
          <span className="pane-sub">Why Synapse believes this review state</span>
        </div>
      </div>

      <div className="pane-body">
        {loading ? (
          <div className="drift-evidence-scroll">
            <EvidenceSkeleton />
            <EvidenceSkeleton />
            <EvidenceSkeleton />
          </div>
        ) : error ? (
          <div className="empty">Evidence will appear here once a review payload is available.</div>
        ) : !review ? (
          <div className="empty">Select a file to inspect evidence and supporting constraints.</div>
        ) : (
          <div className="drift-evidence-scroll">
            <div className="drift-evidence-note">
              <Sparkles size={14} />
              <span>
                Review evidence is grouped by check so scientists can inspect the code claim and the
                supporting domain text together.
              </span>
            </div>

            {review.context.map((entry, index) => (
              <section
                key={`${entry.label}-${index}`}
                className="drift-evidence-group"
              >
                <div className="drift-evidence-head">
                  <div>
                    <h3>{entry.label}</h3>
                    <p>{entry.query_text}</p>
                  </div>
                  <span
                    className={cn(
                      "drift-inline-pill",
                      entry.has_conflict ? "is-conflict" : "is-aligned",
                    )}
                  >
                    {entry.has_conflict ? "Conflict signaled" : "No conflict signaled"}
                  </span>
                </div>

                {entry.sources.length === 0 ? (
                  <div className="drift-panel drift-panel-empty">
                    No supporting sources were returned for this check.
                  </div>
                ) : (
                  entry.sources.map((source, sourceIndex) => (
                    <EvidenceCard
                      key={`${source.source_file}-${sourceIndex}`}
                      source={source}
                    />
                  ))
                )}
              </section>
            ))}
          </div>
        )}
      </div>
    </section>
  );
}

function EvidenceSkeleton() {
  return (
    <div className="drift-evidence-card" style={{ opacity: 0.5 }}>
      <div className="drift-evidence-card-head">
        <div className="skel-line skel-sm" />
        <div className="skel-line skel-sm" style={{ width: 48 }} />
      </div>
      <div className="skel-line skel-md" style={{ marginTop: 10 }} />
      <div className="skel-line skel-full" style={{ marginTop: 8 }} />
      <div className="skel-line skel-lg" style={{ marginTop: 4 }} />
    </div>
  );
}

function EvidenceCard({ source }: { source: ReviewEvidenceSource }) {
  return (
    <article className="drift-evidence-card">
      <div className="drift-evidence-card-head">
        <div className="drift-evidence-kind">
          <BookMarked size={14} />
          <span>{source.kind ?? source.chunk_type}</span>
        </div>
        <span className="score">{(source.score * 100).toFixed(1)}%</span>
      </div>
      <div className="drift-evidence-file">{source.source_file}</div>
      <p className="drift-evidence-text">{source.embed_text}</p>
    </article>
  );
}
