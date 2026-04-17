"use client";

import { forwardRef } from "react";

import type { SourceRef } from "@/lib/api";
import { cn } from "@/lib/cn";

interface CitationBadgeProps {
  n: number;
  source?: SourceRef;
  onActivate?: (n: number) => void;
}

// Pick the chip's accent colour from the source's chunk_type. Code chunks
// use the violet tone (default), knowledge chunks take the cyan variant.
function citeClass(source?: SourceRef): string {
  if (!source) return "";
  return source.chunk_type === "knowledge" ? "c" : "";
}

export const CitationBadge = forwardRef<HTMLButtonElement, CitationBadgeProps>(
  function CitationBadge({ n, source, onActivate }, ref) {
    return (
      <button
        ref={ref}
        type="button"
        className={cn("cite", citeClass(source))}
        onClick={(event) => {
          event.stopPropagation();
          onActivate?.(n);
        }}
        title={source ? `${source.title} — ${source.source_file}` : `Citation ${n}`}
      >
        {n}
      </button>
    );
  },
);
