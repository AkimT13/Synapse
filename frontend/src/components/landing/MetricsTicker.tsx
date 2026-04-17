const METRICS: Array<{ label: string; value: string; tone?: "cyan" | "violet" }> = [
  { label: "Embedding", value: "text-embedding-3-large" },
  { label: "Dimension", value: "3072", tone: "cyan" },
  { label: "Chunk Size", value: "512 tokens" },
  { label: "Distance", value: "cosine" },
  { label: "Vector DB", value: "Actian VectorAI", tone: "violet" },
  { label: "Formats", value: "PDF · DOCX · MD · HTML · PY" },
  { label: "Providers", value: "OpenAI · Ollama" },
  { label: "Stages", value: "4", tone: "cyan" },
  { label: "Modalities", value: "Code ↔ Knowledge", tone: "violet" },
  { label: "IDs", value: "SHA-256" },
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
