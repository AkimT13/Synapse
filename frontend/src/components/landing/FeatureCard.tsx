import type { ReactNode } from "react";

type Tone = "violet" | "cyan" | "emerald";

const TONE_STYLES: Record<Tone, { bg: string; stroke: string }> = {
  violet: { bg: "rgba(139, 92, 246, 0.12)", stroke: "#c4b5fd" },
  cyan: { bg: "rgba(6, 182, 212, 0.12)", stroke: "#67e8f9" },
  emerald: { bg: "rgba(16, 185, 129, 0.12)", stroke: "#6ee7b7" },
};

export function FeatureCard({
  tone,
  icon,
  title,
  body,
  footer,
}: {
  tone: Tone;
  icon: ReactNode;
  title: string;
  body: string;
  footer: string;
}) {
  const style = TONE_STYLES[tone];
  return (
    <article
      className="group relative rounded-3xl border border-white/5 bg-white/[0.02] p-10 transition-all duration-500 ease-snap hover:-translate-y-3 hover:border-violet/40 hover:bg-white/[0.035] hover:shadow-[0_0_40px_-10px_rgba(139,92,246,0.35)]"
    >
      <div
        className="inline-flex h-12 w-12 items-center justify-center rounded-xl transition-transform duration-500 ease-snap group-hover:-rotate-[4deg] group-hover:scale-110"
        style={{ backgroundColor: style.bg, color: style.stroke }}
      >
        {icon}
      </div>
      <h3 className="mt-6 font-serif text-2xl tracking-tight text-white">{title}</h3>
      <p className="mt-3 text-[15px] leading-relaxed text-neutral-400">{body}</p>
      <div className="mt-6 flex items-center gap-2 border-t border-white/5 pt-6 font-mono text-[11px] uppercase tracking-[0.2em] text-neutral-500">
        <span>{footer}</span>
      </div>
    </article>
  );
}
