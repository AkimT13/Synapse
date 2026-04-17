"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import { ArrowRight, Check } from "lucide-react";
import {
  ingestCode,
  ingestJobStreamUrl,
  ingestKnowledge,
  workspace,
} from "@/lib/api";
import { UploadCard } from "@/components/onboarding/UploadCard";
import type { IngestionDoneResult, JobState } from "@/components/onboarding/types";

type Variant = "code" | "knowledge";

export default function OnboardingPage() {
  const [codeState, setCodeState] = useState<JobState>({ kind: "idle" });
  const [knowledgeState, setKnowledgeState] = useState<JobState>({
    kind: "idle",
  });
  const [codeSource, setCodeSource] = useState(0);
  const [knowledgeSource, setKnowledgeSource] = useState(0);

  // Hold live EventSource refs so we can clean them up on unmount or restart.
  const codeEsRef = useRef<EventSource | null>(null);
  const knowledgeEsRef = useRef<EventSource | null>(null);

  // Unmount cleanup — SSE connections must never leak. We capture the
  // refs into locals at cleanup time; the refs are mutable containers, not
  // rendered DOM, so reading .current on teardown is the correct behaviour.
  useEffect(() => {
    const codeRef = codeEsRef;
    const knowledgeRef = knowledgeEsRef;
    return () => {
      codeRef.current?.close();
      knowledgeRef.current?.close();
    };
  }, []);

  // On mount, detect whether a previous session already uploaded corpora.
  // If so, seed each side's state to "already-uploaded" so the card shows
  // a done look with a replace affordance rather than an empty dropzone.
  useEffect(() => {
    let cancelled = false;
    workspace
      .stats()
      .then((stats) => {
        if (cancelled) return;
        if (stats.code_files > 0) {
          setCodeState((current) =>
            current.kind === "idle"
              ? { kind: "already-uploaded", fileCount: stats.code_files }
              : current,
          );
        }
        if (stats.knowledge_files > 0) {
          setKnowledgeState((current) =>
            current.kind === "idle"
              ? {
                  kind: "already-uploaded",
                  fileCount: stats.knowledge_files,
                }
              : current,
          );
        }
      })
      .catch(() => {
        // Backend may be down; leave both sides in idle.
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const openStream = useCallback(
    (
      variant: Variant,
      jobId: string,
      setState: (s: JobState) => void,
    ) => {
      const ref = variant === "code" ? codeEsRef : knowledgeEsRef;
      // Close any previous stream from an earlier attempt on this side.
      ref.current?.close();

      const es = new EventSource(ingestJobStreamUrl(jobId));
      ref.current = es;

      let messages: string[] = [];
      setState({ kind: "running", jobId, messages: [] });

      es.addEventListener("progress", (e) => {
        try {
          const payload = JSON.parse((e as MessageEvent).data);
          messages = [...messages, payload.message as string];
          setState({ kind: "running", jobId, messages });
        } catch {
          // ignore malformed payloads
        }
      });

      es.addEventListener("done", (e) => {
        try {
          const result = JSON.parse(
            (e as MessageEvent).data,
          ) as IngestionDoneResult;
          setState({ kind: "done", result, messages });
        } catch {
          setState({
            kind: "error",
            message: "Malformed completion payload",
          });
        }
        es.close();
        ref.current = null;
      });

      es.addEventListener("error", (e) => {
        // SSE fires a generic 'error' on network blips too; treat a closed
        // connection as a terminal failure unless we already got `done`.
        try {
          const data = (e as MessageEvent).data;
          if (data) {
            const payload = JSON.parse(data);
            setState({
              kind: "error",
              message: payload.message ?? "Ingestion failed",
            });
          } else {
            setState({
              kind: "error",
              message: "Lost connection to ingestion stream",
            });
          }
        } catch {
          setState({
            kind: "error",
            message: "Lost connection to ingestion stream",
          });
        }
        es.close();
        ref.current = null;
      });
    },
    [],
  );

  const handleCodeFiles = useCallback(
    async (files: File[]) => {
      if (files.length === 0) return;
      setCodeState({ kind: "uploading", fileCount: files.length });
      try {
        const ack = await ingestCode(files);
        openStream("code", ack.job_id, setCodeState);
      } catch (err) {
        setCodeState({
          kind: "error",
          message: err instanceof Error ? err.message : "Upload failed",
        });
      }
    },
    [openStream],
  );

  const handleKnowledgeFiles = useCallback(
    async (files: File[]) => {
      if (files.length === 0) return;
      setKnowledgeState({ kind: "uploading", fileCount: files.length });
      try {
        const ack = await ingestKnowledge(files);
        openStream("knowledge", ack.job_id, setKnowledgeState);
      } catch (err) {
        setKnowledgeState({
          kind: "error",
          message: err instanceof Error ? err.message : "Upload failed",
        });
      }
    },
    [openStream],
  );

  // A side counts as "ready" when freshly ingested OR when the backend
  // already had a corpus on disk at page load. Either way the user has
  // something to open.
  const codeReady =
    codeState.kind === "done" || codeState.kind === "already-uploaded";
  const knowledgeReady =
    knowledgeState.kind === "done" ||
    knowledgeState.kind === "already-uploaded";
  const bothDone = codeReady && knowledgeReady;

  const totalChunks = useMemo(() => {
    const c = codeState.kind === "done" ? codeState.result.chunks_stored : 0;
    const k =
      knowledgeState.kind === "done"
        ? knowledgeState.result.chunks_stored
        : 0;
    return c + k;
  }, [codeState, knowledgeState]);

  return (
    <>
      {/* ===== Top bar ===== */}
      <header
        className="topbar"
        style={{ borderBottom: "1px solid var(--line)" }}
      >
        <Link className="brand" href="/">
          <span className="brand-dot" />
          <span className="brand-word">Synapse</span>
        </Link>

        <StepRail
          activeStep={bothDone ? 3 : 2}
        />

        <div className="flex items-center gap-3.5">
          <span className="status-pill">
            <span className="status-dot" />
            Live session
          </span>
          <span className="avatar">SY</span>
        </div>
      </header>

      {/* ===== Page ===== */}
      <main className="relative overflow-hidden px-7 pt-[72px] pb-[120px]" style={{ minHeight: "calc(100vh - 56px)" }}>
        <div
          aria-hidden
          className="orb orb-violet"
          style={{
            width: 520,
            height: 520,
            top: -160,
            right: -140,
          }}
        />
        <div
          aria-hidden
          className="orb orb-cyan"
          style={{
            width: 440,
            height: 440,
            bottom: -200,
            left: -160,
          }}
        />

        <div className="relative z-[2] mx-auto max-w-[1080px]">
          <p className="font-mono text-[11px] uppercase tracking-[0.2em] text-[#737373]">
            Project setup / new workspace
          </p>
          <h1 className="my-5 font-serif font-normal leading-[1.02] tracking-[-0.03em] text-white text-[clamp(40px,5.4vw,72px)]">
            Point Synapse at your{" "}
            <em className="italic text-violet-fg not-italic sm:italic">code</em>
            <br />
            and your{" "}
            <em className="italic text-violet-fg not-italic sm:italic">knowledge</em>.
          </h1>
          <p className="max-w-[640px] text-base leading-[1.6] text-[#a3a3a3]">
            Two sources, one collection. Connect a repository and drop your
            specifications, compliance docs, and internal wikis. Synapse
            normalizes everything to natural language before embedding, so a
            query doesn&apos;t have to know which modality it&apos;s looking for.
          </p>

          {/* Cards */}
          <div className="mt-14 grid gap-5 md:grid-cols-2">
            <UploadCard
              variant="code"
              kicker="Source code · step 1"
              title="Connect a repository"
              description="Python, TypeScript, Go, Rust. Parsed via AST — signatures, decorators, and docstrings preserved."
              sources={[
                { label: "Local folder" },
                { label: "GitHub URL", disabled: true },
                { label: "Sample repo", disabled: true },
              ]}
              activeSourceIndex={codeSource}
              onSourceChange={setCodeSource}
              state={codeState}
              onFiles={handleCodeFiles}
              folder
              multiple
              idleTitle="drop your repo here"
              idleMeta="or pick a folder — we preserve the tree via webkitdirectory"
              ctaLabel="Pick a folder"
              statLabels={["Files", "Functions", "Chunks"]}
            />

            <UploadCard
              variant="knowledge"
              kicker="Knowledge · step 2"
              title="Drop in your docs"
              description="PDF, DOCX, Markdown, HTML, and plain text. Parsed via docling's hybrid chunker with structure-aware splits."
              sources={[
                { label: "Drop files" },
                { label: "Paste URL", disabled: true },
                { label: "From Drive", disabled: true },
              ]}
              activeSourceIndex={knowledgeSource}
              onSourceChange={setKnowledgeSource}
              state={knowledgeState}
              onFiles={handleKnowledgeFiles}
              accept=".pdf,.docx,.md,.txt,.html"
              multiple
              idleTitle="drop files to ingest"
              idleMeta="PDF, DOCX, Markdown, HTML, TXT — structure detected automatically"
              ctaLabel="Pick files"
              statLabels={["Documents", "Sections", "Chunks"]}
            />
          </div>

          {/* Footer action bar */}
          <div className="mt-12 flex flex-col items-stretch justify-between gap-4 rounded-[18px] border border-line bg-white/[0.015] px-6 py-5 md:flex-row md:items-center">
            <div className="flex items-center gap-3.5 text-sm text-[#a3a3a3]">
              <span
                className="inline-flex h-[22px] w-[22px] items-center justify-center rounded-full"
                style={{
                  background: bothDone
                    ? "rgba(16,185,129,0.15)"
                    : "rgba(255,255,255,0.04)",
                  color: bothDone ? "#6ee7b7" : "#525252",
                }}
              >
                <Check size={12} strokeWidth={3} />
              </span>
              <span>
                {bothDone ? (
                  <>
                    <span className="text-white">
                      {totalChunks.toLocaleString()}
                    </span>{" "}
                    chunks embedded across one collection ·{" "}
                    <span className="text-white">ready</span>
                  </>
                ) : (
                  <>
                    Waiting for both sources to finish ingesting.
                  </>
                )}
              </span>
            </div>

            {bothDone ? (
              <Link
                href="/code"
                className="shiny-border"
                aria-label="Open workspace"
              >
                <span className="shiny-inner">
                  Open workspace
                  <ArrowRight size={14} strokeWidth={2} />
                </span>
              </Link>
            ) : (
              <button
                type="button"
                disabled
                aria-disabled="true"
                className="btn btn-ghost cursor-not-allowed opacity-45"
              >
                Open workspace
                <ArrowRight size={14} strokeWidth={2} />
              </button>
            )}
          </div>
        </div>
      </main>
    </>
  );
}

/* ---------- sub-components kept inline (small) ---------- */

function StepRail({ activeStep }: { activeStep: 1 | 2 | 3 }) {
  const steps: { idx: 1 | 2 | 3; label: string }[] = [
    { idx: 1, label: "Source" },
    { idx: 2, label: "Ingest" },
    { idx: 3, label: "Workspace" },
  ];
  return (
    <div className="hidden items-center gap-3.5 font-mono text-[11px] uppercase tracking-[0.22em] text-[#737373] md:inline-flex">
      {steps.map((s, i) => {
        const isDone = activeStep > s.idx;
        const isActive = activeStep === s.idx;
        return (
          <span key={s.idx} className="inline-flex items-center gap-3.5">
            <span className="inline-flex items-center gap-2">
              <span
                className="inline-flex h-[22px] w-[22px] items-center justify-center rounded-full border text-[10px]"
                style={{
                  borderColor: isDone
                    ? "rgba(16,185,129,0.5)"
                    : isActive
                    ? "rgba(139,92,246,0.5)"
                    : "var(--line-strong)",
                  background: isDone
                    ? "rgba(16,185,129,0.12)"
                    : isActive
                    ? "rgba(139,92,246,0.14)"
                    : "transparent",
                  color: isDone
                    ? "#6ee7b7"
                    : isActive
                    ? "#c4b5fd"
                    : "#737373",
                }}
              >
                {isDone ? <Check size={10} strokeWidth={3} /> : s.idx}
              </span>
              <span
                style={{
                  color: isActive ? "#fff" : isDone ? "#d4d4d4" : "#737373",
                }}
              >
                {s.label}
              </span>
            </span>
            {i < steps.length - 1 ? (
              <span
                aria-hidden
                className="inline-block h-px w-10"
                style={{ background: "var(--line)" }}
              />
            ) : null}
          </span>
        );
      })}
    </div>
  );
}
