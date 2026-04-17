"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { ArrowRight, GitBranch, Layers, Network } from "lucide-react";

import { CodeWindow } from "@/components/landing/CodeWindow";
import { FeatureCard } from "@/components/landing/FeatureCard";
import { MetricsTicker } from "@/components/landing/MetricsTicker";
import { workspace } from "@/lib/api";

/* Landing page — ported from mockups/index.html into React + Tailwind.
   Interactive bits: IntersectionObserver reveal-on-scroll + copy button. */

export default function Home() {
  // If the backend already has corpora on disk, the nav pill's primary
  // CTA should go straight to the workspace. Otherwise it should point
  // at onboarding so a first-time visitor can upload. We default to the
  // onboarding link until stats resolve — it's the safe choice if the
  // check fails.
  const [workspaceHref, setWorkspaceHref] = useState<"/onboarding" | "/code">(
    "/onboarding",
  );

  useEffect(() => {
    let cancelled = false;
    workspace
      .stats()
      .then((stats) => {
        if (cancelled) return;
        if (stats.code_files > 0 || stats.knowledge_files > 0) {
          setWorkspaceHref("/code");
        }
      })
      .catch(() => {
        // Backend unreachable — leave as /onboarding.
      });
    return () => {
      cancelled = true;
    };
  }, []);

  // Reveal-on-scroll: any element with data-reveal slides up when visible.
  useEffect(() => {
    if (typeof window === "undefined") return;
    const els = Array.from(document.querySelectorAll<HTMLElement>("[data-reveal]"));
    if (!("IntersectionObserver" in window) || els.length === 0) {
      els.forEach((el) => el.setAttribute("data-reveal-visible", "true"));
      return;
    }
    const io = new IntersectionObserver(
      (entries, observer) => {
        for (const entry of entries) {
          if (entry.isIntersecting) {
            (entry.target as HTMLElement).setAttribute("data-reveal-visible", "true");
            observer.unobserve(entry.target);
          }
        }
      },
      { threshold: 0.12, rootMargin: "0px 0px -40px 0px" }
    );
    els.forEach((el) => io.observe(el));
    return () => io.disconnect();
  }, []);

  return (
    <main className="relative min-h-screen overflow-x-hidden bg-ink text-white">
      <style jsx global>{`
        [data-reveal] {
          opacity: 0;
          transform: translateY(30px);
          transition: opacity 0.9s cubic-bezier(0.23, 1, 0.32, 1),
            transform 0.9s cubic-bezier(0.23, 1, 0.32, 1);
        }
        [data-reveal][data-reveal-visible="true"] {
          opacity: 1;
          transform: translateY(0);
        }
        .shimmer-text {
          background: linear-gradient(
            90deg,
            #a78bfa 0%,
            #ffffff 40%,
            #ffffff 60%,
            #22d3ee 100%
          );
          background-size: 200% 100%;
          -webkit-background-clip: text;
          background-clip: text;
          -webkit-text-fill-color: transparent;
          color: transparent;
          animation: shimmer 6s linear infinite;
        }
        @keyframes shimmer {
          from {
            background-position: 200% 0;
          }
          to {
            background-position: -200% 0;
          }
        }
        .glass-pill {
          background: rgba(10, 10, 10, 0.7);
          backdrop-filter: blur(16px);
          -webkit-backdrop-filter: blur(16px);
          border: 1px solid rgba(255, 255, 255, 0.1);
        }
      `}</style>

      {/* ============== NAV PILL ============== */}
      <nav className="glass-pill fixed left-1/2 top-6 z-50 w-[95%] max-w-2xl -translate-x-1/2 rounded-full">
        <div className="flex items-center justify-between py-2 pl-4 pr-2">
          <Link href="#top" className="flex items-center gap-2">
            <span
              className="inline-block h-3.5 w-3.5 rounded-full"
              style={{
                background:
                  "conic-gradient(from 180deg, #8b5cf6, #06b6d4, #8b5cf6)",
                boxShadow: "0 0 12px -2px rgba(139,92,246,0.6)",
              }}
            />
            <span className="font-serif text-xl leading-none tracking-[-0.035em]">
              Synapse
            </span>
          </Link>
          <div className="hidden items-center gap-6 sm:flex">
            <a
              href="#features"
              className="text-[11px] uppercase tracking-[0.2em] text-neutral-400 transition-colors hover:text-white"
            >
              Features
            </a>
            <a
              href="#integration"
              className="text-[11px] uppercase tracking-[0.2em] text-neutral-400 transition-colors hover:text-white"
            >
              Integration
            </a>
          </div>
          <Link
            href={workspaceHref}
            className="rounded-full bg-white px-4 py-2 text-xs font-medium text-black transition-colors hover:bg-neutral-200"
          >
            Workspace →
          </Link>
        </div>
      </nav>

      {/* ============== HERO ============== */}
      <header
        id="top"
        className="relative isolate overflow-hidden px-6 pb-28 pt-28 sm:pb-36 sm:pt-32"
      >
        {/* Radial gradient backdrop */}
        <div
          aria-hidden
          className="absolute inset-0 -z-10"
          style={{
            background: `radial-gradient(ellipse 900px 500px at 50% -5%, rgba(139,92,246,0.40), transparent 60%),
                         radial-gradient(ellipse 700px 400px at 0% 30%, rgba(6,182,212,0.10), transparent 60%)`,
          }}
        />

        {/* Ambient orbs */}
        <div
          aria-hidden
          className="orb orb-violet"
          style={{
            width: 420,
            height: 420,
            top: -120,
            left: "50%",
            transform: "translateX(-50%)",
          }}
        />
        <div
          aria-hidden
          className="orb orb-cyan"
          style={{ width: 320, height: 320, top: 180, left: -80 }}
        />

        <div className="relative mx-auto max-w-5xl text-center">
          {/* Kicker */}
          <div
            className="glass-pill inline-flex animate-rise items-center gap-2 rounded-full px-3 py-1.5"
            style={{ animationDelay: "0.15s" }}
          >
            <span className="h-1.5 w-1.5 rounded-full bg-violet" />
            <span className="text-[10px] uppercase tracking-[0.2em] text-neutral-300">
              Code and documentation · built on Actian VectorAI
            </span>
          </div>

          {/* Heading */}
          <h1
            className="mt-8 animate-rise font-serif text-6xl leading-[0.95] tracking-[-0.035em] text-white sm:text-7xl md:text-8xl lg:text-[8.5rem]"
            style={{ animationDelay: "0.35s" }}
          >
            Your code. Your docs.
            <br />
            <span className="shimmer-text italic">One search.</span>
          </h1>

          {/* Subtitle */}
          <p
            className="mx-auto mt-8 max-w-2xl animate-rise text-lg leading-relaxed text-neutral-400"
            style={{ animationDelay: "0.55s" }}
          >
            Ask a question about your code and find the documentation behind it.
            Ask a question about your documentation and find the code that
            implements it. One place to search everything your team knows.
          </p>

          {/* CTAs */}
          <div
            className="mt-12 flex animate-rise flex-col items-center justify-center gap-6 sm:flex-row"
            style={{ animationDelay: "0.75s" }}
          >
            <Link href="/onboarding" className="shiny-border">
              <span className="shiny-inner">
                Launch the demo
                <ArrowRight size={14} />
              </span>
            </Link>
            <a
              href="#features"
              className="group inline-flex items-center gap-2 text-sm text-neutral-400 transition-colors hover:text-white"
            >
              See how it works
              <span className="transition-transform group-hover:translate-x-1">
                →
              </span>
            </a>
          </div>
        </div>
      </header>

      {/* ============== METRICS TICKER ============== */}
      <MetricsTicker />

      {/* ============== FEATURES ============== */}
      <section id="features" className="relative px-6 py-28 sm:py-36">
        <div
          aria-hidden
          className="orb orb-violet"
          style={{ width: 360, height: 360, top: 200, right: -120 }}
        />

        <div className="relative mx-auto max-w-6xl">
          <div className="max-w-3xl" data-reveal>
            <p className="font-mono text-[11px] uppercase tracking-[0.2em] text-neutral-500">
              01 / What it does
            </p>
            <h2 className="mt-4 font-serif text-4xl leading-[0.95] tracking-[-0.035em] text-white sm:text-5xl md:text-6xl">
              Two inputs. One{" "}
              <span className="italic text-neutral-400">search</span>.
            </h2>
            <p className="mt-6 max-w-2xl text-lg leading-relaxed text-neutral-400">
              Code and documentation speak different languages. Synapse brings
              them together, so a single question finds the right answer —
              wherever it&apos;s written.
            </p>
          </div>

          <div className="mt-16 grid gap-6 md:grid-cols-3">
            <div data-reveal>
              <FeatureCard
                tone="violet"
                icon={<GitBranch size={22} strokeWidth={1.8} />}
                title="Drop in everything"
                body="Point Synapse at your repository and your documentation. Both get indexed in minutes — no conversions, no manual mapping."
                footer="code · documentation"
              />
            </div>
            <div data-reveal style={{ transitionDelay: "80ms" }}>
              <FeatureCard
                tone="cyan"
                icon={<Layers size={22} strokeWidth={1.8} />}
                title="Shared understanding"
                body="Code and prose live in the same semantic space, so related ideas sit next to each other — whether they show up in a function or a spec."
                footer="semantic search"
              />
            </div>
            <div data-reveal style={{ transitionDelay: "160ms" }}>
              <FeatureCard
                tone="emerald"
                icon={<Network size={22} strokeWidth={1.8} />}
                title="Search in any direction"
                body="Highlight a function to find the spec behind it. Highlight a paragraph to find the code that implements it. Or just ask a question and get an answer with citations."
                footer="built on actian vectorai"
              />
            </div>
          </div>
        </div>
      </section>

      {/* ============== INTEGRATION ============== */}
      <section id="integration" className="relative px-6 py-28 sm:py-36">
        <div
          aria-hidden
          className="orb orb-cyan"
          style={{ width: 380, height: 380, bottom: -80, left: -60 }}
        />

        <div className="relative mx-auto grid max-w-6xl items-center gap-16 lg:grid-cols-[1fr_1.2fr]">
          <div data-reveal>
            <p className="font-mono text-[11px] uppercase tracking-[0.2em] text-neutral-500">
              02 / Plug it in
            </p>
            <h2 className="mt-4 font-serif text-4xl leading-[0.95] tracking-[-0.035em] text-white sm:text-5xl md:text-6xl">
              Works with <span className="italic">what you have</span>.
            </h2>
            <p className="mt-6 text-lg leading-relaxed text-neutral-400">
              Connect your codebase and your documentation, and Synapse handles
              the rest. No new formats to learn, no workflow to redesign.
            </p>
            <ul className="mt-8 space-y-3 text-neutral-400">
              <li className="flex gap-3">
                <span className="mt-0.5 text-violet">—</span>
                Re-run anytime as your project evolves.
              </li>
              <li className="flex gap-3">
                <span className="mt-0.5 text-cyan">—</span>
                Scales cleanly from a single repo to the whole organization.
              </li>
              <li className="flex gap-3">
                <span className="mt-0.5 text-emerald">—</span>
                Transparent progress, clear results.
              </li>
            </ul>
          </div>

          <div data-reveal style={{ transitionDelay: "120ms" }}>
            <CodeWindow />
          </div>
        </div>
      </section>

      {/* ============== FOOTER ============== */}
      <footer className="relative mt-12 border-t border-line bg-[#050505] px-6 pb-8 pt-20">
        <div className="mx-auto max-w-6xl">
          <div className="grid gap-12 md:grid-cols-4">
            <div className="md:col-span-2">
              <div className="flex items-center gap-2">
                <span
                  className="inline-block h-3.5 w-3.5 rounded-full"
                  style={{
                    background:
                      "conic-gradient(from 180deg, #8b5cf6, #06b6d4, #8b5cf6)",
                  }}
                />
                <span className="font-serif text-4xl tracking-[-0.035em] text-white">
                  Synapse
                </span>
              </div>
              <p className="mt-4 max-w-sm text-[15px] leading-relaxed text-neutral-400">
                One place to search everything your team knows. Built for work
                where the spec matters as much as the code.
              </p>
            </div>

            <div>
              <h4 className="text-[10px] uppercase tracking-[0.2em] text-neutral-500">
                Explore
              </h4>
              <ul className="mt-5 space-y-3 text-sm text-neutral-300">
                <li>
                  <a href="#features" className="transition-colors hover:text-white">
                    Features
                  </a>
                </li>
                <li>
                  <a
                    href="#integration"
                    className="transition-colors hover:text-white"
                  >
                    Integration
                  </a>
                </li>
                <li>
                  <a href="#top" className="transition-colors hover:text-white">
                    Back to top
                  </a>
                </li>
              </ul>
            </div>

            <div>
              <h4 className="text-[10px] uppercase tracking-[0.2em] text-neutral-500">
                Project
              </h4>
              <ul className="mt-5 space-y-3 text-sm text-neutral-300">
                <li>
                  <a href="#" className="transition-colors hover:text-white">
                    GitHub repository
                  </a>
                </li>
                <li>
                  <span className="text-neutral-400">
                    Built at Actian VectorAI Hackathon &apos;26
                  </span>
                </li>
                <li>
                  <span className="text-neutral-400">
                    by Akim Tarasov &amp; Aneesh Kumar
                  </span>
                </li>
              </ul>
            </div>
          </div>

          <div className="mt-16 flex flex-col items-start justify-between gap-3 border-t border-line pt-6 sm:flex-row sm:items-center">
            <p className="font-mono text-[11px] tracking-wide text-neutral-500">
              © 2026 Synapse · Hackathon build
            </p>
            <div className="flex items-center gap-2 text-[11px] uppercase tracking-[0.2em] text-neutral-400">
              <span className="status-dot" aria-hidden />
              Demo live
            </div>
          </div>
        </div>
      </footer>
    </main>
  );
}
