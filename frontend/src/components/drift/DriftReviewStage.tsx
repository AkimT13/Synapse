"use client";

import { AlertTriangle, CheckCircle2, FileWarning, Microscope } from "lucide-react";

import { cn } from "@/lib/cn";
import type {
  FileReviewResponse,
  ReviewCheck,
  ReviewFinding,
  ReviewStatus,
} from "@/lib/api";

interface DriftReviewStageProps {
  filePath: string | null;
  review: FileReviewResponse | null;
  loading: boolean;
  error: string | null;
}

const STATUS_COPY: Record<
  ReviewStatus,
  { label: string; scientist: string; tone: string }
> = {
  aligned: {
    label: "Aligned",
    scientist: "Current code behavior appears consistent with the indexed constraint set.",
    tone: "calm",
  },
  warning: {
    label: "Warning",
    scientist: "The evidence is incomplete or ambiguous enough that this file needs review.",
    tone: "caution",
  },
  conflict: {
    label: "Conflict",
    scientist: "The code appears to diverge from the indexed scientific or protocol constraints.",
    tone: "alert",
  },
  unknown: {
    label: "Unknown",
    scientist: "Synapse could not form a reliable review from the indexed evidence yet.",
    tone: "neutral",
  },
};

export function DriftReviewStage({
  filePath,
  review,
  loading,
  error,
}: DriftReviewStageProps) {
  const reviewStatus = review?.drift_status ?? "unknown";
  const conflictCount = review?.drift.filter((check) => check.status === "conflict").length ?? 0;
  const warningCount = review?.drift.filter((check) => check.status === "warning").length ?? 0;

  return (
    <section className="pane drift-stage">
      <div className="pane-head drift-stage-head">
        <div className="flex min-w-0 flex-col gap-1">
          <span className="pane-title">Drift review</span>
          <span className="pane-sub">
            Compare extracted code behavior against indexed scientific constraints.
          </span>
        </div>
        <StatusBadge status={reviewStatus} large />
      </div>

      <div className="pane-body">
        {!filePath ? (
          <div className="empty">Choose a file from the review queue to begin.</div>
        ) : loading ? (
          <div className="empty">Reviewing code against indexed constraints…</div>
        ) : error ? (
          <ReviewErrorState error={error} />
        ) : !review ? (
          <div className="empty">No review results are available for this file yet.</div>
        ) : (
          <div className="drift-stage-scroll">
            <section className={cn("drift-hero", `is-${STATUS_COPY[reviewStatus].tone}`)}>
              <div className="drift-hero-copy">
                <div className="drift-hero-kicker">
                  <Microscope size={14} />
                  Scientist briefing
                </div>
                <h2>{STATUS_COPY[reviewStatus].label} review state</h2>
                <p>{STATUS_COPY[reviewStatus].scientist}</p>
              </div>
              <div className="drift-hero-metrics">
                <Metric label="Checks" value={review.drift.length} />
                <Metric label="Conflicts" value={conflictCount} tone="alert" />
                <Metric label="Warnings" value={warningCount} tone="caution" />
              </div>
            </section>

            <section className="drift-panel">
              <div className="drift-panel-head">
                <span>Review target</span>
                <span>{review.workspace}</span>
              </div>
              <div className="drift-target-path">{review.target}</div>
            </section>

            <section className="drift-section">
              <div className="drift-section-head">
                <h3>Assessment breakdown</h3>
                <p>
                  Each check isolates one function or behavior and compares what the code appears
                  to do against the indexed domain evidence.
                </p>
              </div>

              {review.drift.length === 0 ? (
                <div className="drift-panel drift-panel-empty">
                  No file-level checks were returned for this review.
                </div>
              ) : (
                review.drift.map((check, index) => (
                  <DriftCheckCard
                    key={`${check.label}-${check.line_range?.start ?? index}`}
                    check={check}
                  />
                ))
              )}
            </section>
          </div>
        )}
      </div>
    </section>
  );
}

function ReviewErrorState({ error }: { error: string }) {
  const lower = error.toLowerCase();
  const missingEndpoint =
    lower.includes("404") ||
    lower.includes("not found") ||
    lower.includes("cannot post /api/review/file");

  return (
    <div className="drift-error-card">
      <FileWarning size={18} />
      <div className="drift-error-copy">
        <strong>{missingEndpoint ? "Review API not available yet" : "Review failed"}</strong>
        <p>
          {missingEndpoint
            ? "The GUI is ready for file review, but the backend endpoint is not serving review payloads yet."
            : error}
        </p>
        <span>
          Expected contract: overall file status, per-check findings, and supporting evidence.
        </span>
      </div>
    </div>
  );
}

function DriftCheckCard({ check }: { check: ReviewCheck }) {
  return (
    <article className="drift-check-card">
      <div className="drift-check-head">
        <div className="min-w-0">
          <div className="drift-check-label">{check.label}</div>
          <div className="drift-check-meta">
            {check.line_range
              ? `Lines ${check.line_range.start}-${check.line_range.end}`
              : "Line range unavailable"}
          </div>
        </div>
        <div className="drift-check-badges">
          <StatusBadge status={check.status} />
          <ConfidenceBadge value={check.confidence} />
        </div>
      </div>

      <p className="drift-check-summary">{check.summary}</p>

      {check.findings.length > 0 ? (
        <div className="drift-findings">
          {check.findings.map((finding, index) => (
            <FindingCard key={`${finding.issue_type}-${index}`} finding={finding} />
          ))}
        </div>
      ) : (
        <div className="drift-alignment-note">
          {check.status === "aligned"
            ? "No structured mismatch was extracted for this behavior."
            : "No structured finding was extracted, but the language review still flags this behavior for attention."}
        </div>
      )}
    </article>
  );
}

function FindingCard({ finding }: { finding: ReviewFinding }) {
  return (
    <div className="drift-finding-card">
      <div className="drift-finding-head">
        <span className="drift-finding-type">{finding.issue_type.replaceAll("_", " ")}</span>
        <span className={cn("drift-severity", `is-${finding.severity}`)}>{finding.severity}</span>
      </div>
      <p className="drift-finding-summary">{finding.summary}</p>
      <div className="drift-compare-grid">
        <CompareBlock label="Constraint expects" value={finding.expected} />
        <CompareBlock label="Code appears to do" value={finding.observed} />
      </div>
      <div className="drift-compare-foot">{finding.comparison}</div>
    </div>
  );
}

function CompareBlock({ label, value }: { label: string; value: string }) {
  return (
    <div className="drift-compare-block">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function Metric({
  label,
  value,
  tone = "neutral",
}: {
  label: string;
  value: number;
  tone?: "neutral" | "alert" | "caution";
}) {
  return (
    <div className={cn("drift-metric", `is-${tone}`)}>
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function StatusBadge({
  status,
  large = false,
}: {
  status: ReviewStatus;
  large?: boolean;
}) {
  const Icon =
    status === "aligned" ? CheckCircle2 : status === "conflict" ? AlertTriangle : Microscope;
  return (
    <span className={cn("drift-status-badge", `is-${status}`, large && "is-large")}>
      <Icon size={large ? 15 : 13} />
      {STATUS_COPY[status].label}
    </span>
  );
}

function ConfidenceBadge({ value }: { value: string }) {
  return <span className={cn("drift-confidence-badge", `is-${value}`)}>{value} confidence</span>;
}
