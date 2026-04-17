"use client";

import Link from "next/link";

import type { SourceRef } from "@/lib/api";
import { cn } from "@/lib/cn";

interface ResultCardProps {
  result: SourceRef;
  // Where clicking the card navigates. If omitted the card is static.
  href?: string;
}

export function ResultCard({ result, href }: ResultCardProps) {
  const content = (
    <>
      <div className="result-meta">
        <span className="source truncate">{result.source_file}</span>
        <Score value={result.score} />
      </div>
      <div className="result-title">{result.title}</div>
      <div className="result-excerpt">{result.excerpt}</div>
    </>
  );

  if (!href) {
    return <div className="result-card">{content}</div>;
  }
  return (
    <Link href={href} className="result-card block">
      {content}
    </Link>
  );
}

export function Score({ value }: { value: number }) {
  // Match the mockup's three-tier colour ramp. Scores are cosine
  // similarities which in practice land in roughly [0, 1].
  const tier = value >= 0.6 ? "high" : value >= 0.35 ? "mid" : "low";
  return (
    <span className={cn("score", tier === "mid" && "mid", tier === "low" && "low")}>
      {(value * 100).toFixed(1)}%
    </span>
  );
}
