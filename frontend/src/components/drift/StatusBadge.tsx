"use client";

import { AlertTriangle, CheckCircle2, Microscope } from "lucide-react";

import { cn } from "@/lib/cn";
import type { ReviewStatus } from "@/lib/api";

export const STATUS_COPY: Record<
  ReviewStatus,
  { label: string; scientist: string; tone: string }
> = {
  aligned: {
    label: "Aligned",
    scientist:
      "Current code behavior appears consistent with the indexed constraint set.",
    tone: "calm",
  },
  warning: {
    label: "Warning",
    scientist:
      "The evidence is incomplete or ambiguous enough that this file needs review.",
    tone: "caution",
  },
  conflict: {
    label: "Conflict",
    scientist:
      "The code appears to diverge from the indexed scientific or protocol constraints.",
    tone: "alert",
  },
  unknown: {
    label: "Unknown",
    scientist:
      "Synapse could not form a reliable review from the indexed evidence yet.",
    tone: "neutral",
  },
};

export function StatusBadge({
  status,
  large = false,
}: {
  status: ReviewStatus;
  large?: boolean;
}) {
  const Icon =
    status === "aligned"
      ? CheckCircle2
      : status === "conflict"
        ? AlertTriangle
        : Microscope;
  return (
    <span
      className={cn(
        "drift-status-badge",
        `is-${status}`,
        large && "is-large",
      )}
    >
      <Icon size={large ? 15 : 13} />
      {STATUS_COPY[status].label}
    </span>
  );
}

export function ConfidenceBadge({ value }: { value: string }) {
  return (
    <span className={cn("drift-confidence-badge", `is-${value}`)}>
      {value} confidence
    </span>
  );
}
