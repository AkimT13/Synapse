const METRICS: Array<{ label: string; value: string; tone?: "cyan" | "violet" }> = [
  { label: "Search", value: "Cross-modal", tone: "violet" },
  { label: "Citations", value: "Inline" },
  { label: "Formats", value: "PDF · DOCX · MD · HTML · PY" },
  { label: "Direction", value: "Code ↔ Knowledge", tone: "cyan" },
  { label: "Retrieval", value: "Semantic" },
  { label: "Results", value: "Relevance-scored" },
  { label: "Vector DB", value: "Actian VectorAI", tone: "violet" },
  { label: "Ingestion", value: "One-click" },
  { label: "Navigation", value: "Deep-linked", tone: "cyan" },
  { label: "Answers", value: "Grounded" },
];

function MetricSet({ ariaHidden = false }: { ariaHidden?: boolean }) {
  return (
    <div
      aria-hidden={ariaHidden || undefined}
      className="flex items-center gap-16 px-8 shrink-0"
    >
      {METRICS.map((m, i) => (
        <div key={`${m.label}-${i}`} className="flex items-baseline gap-3 whitespace-nowrap">
          <span className="font-mono text-[10px] uppercase tracking-[0.2em] text-neutral-500">
            {m.label}
          </span>
          <span
            className={`font-mono text-sm ${
              m.tone === "cyan"
                ? "text-cyan-fg"
                : m.tone === "violet"
                ? "text-violet-fg"
                : "text-white"
            }`}
          >
            {m.value}
          </span>
        </div>
      ))}
    </div>
  );
}

export function MetricsTicker() {
  return (
    <section
      aria-label="Technical specs"
      className="relative border-y border-line bg-black/40 py-5 overflow-hidden"
      style={{
        WebkitMaskImage:
          "linear-gradient(90deg, transparent, #000 10%, #000 90%, transparent)",
        maskImage:
          "linear-gradient(90deg, transparent, #000 10%, #000 90%, transparent)",
      }}
    >
      <div className="flex w-max animate-marquee gap-16">
        <MetricSet />
        <MetricSet ariaHidden />
      </div>
    </section>
  );
}
