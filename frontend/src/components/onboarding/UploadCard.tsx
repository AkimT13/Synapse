"use client";

import { useCallback, useMemo, useRef, useState } from "react";
import clsx from "clsx";
import {
  Check,
  FileText,
  FolderOpen,
  Loader2,
  Upload,
} from "lucide-react";
import type { JobState } from "./types";

type Variant = "code" | "knowledge";

interface SourceOption {
  label: string;
  disabled?: boolean;
}

interface UploadCardProps {
  variant: Variant;
  kicker: string;
  title: string;
  description: string;
  sources: SourceOption[];
  activeSourceIndex: number;
  onSourceChange: (index: number) => void;
  state: JobState;
  onFiles: (files: File[]) => void;
  accept?: string;
  // Primary picker mode. When true, the click CTA opens a folder
  // dialog (webkitdirectory); when false, a normal file dialog.
  folder?: boolean;
  multiple?: boolean;
  idleTitle: string;
  idleMeta: string;
  ctaLabel: string;
  // When set, a secondary picker button with this label appears next
  // to the primary CTA — in the opposite mode to ``folder``. Used by
  // the knowledge card to let users pick either individual files or a
  // whole directory tree.
  secondaryCtaLabel?: string;
  statLabels: [string, string];
}

// Two stat boxes: file count + stored chunk count. The intermediate
// "functions / sections" column was removed because it was only
// populated immediately after a fresh ingest — when an already-uploaded
// corpus rehydrated from disk, both slots collapsed to em-dashes and
// offered no signal.
function deriveStats(state: JobState): [number | null, number | null] {
  if (state.kind === "done") {
    const r = state.result;
    return [r.files_processed, r.chunks_stored];
  }
  if (state.kind === "already-uploaded") {
    return [state.fileCount, state.chunkCount];
  }
  return [0, 0];
}

export function UploadCard({
  variant,
  kicker,
  title,
  description,
  sources,
  activeSourceIndex,
  onSourceChange,
  state,
  onFiles,
  accept,
  folder,
  multiple,
  idleTitle,
  idleMeta,
  ctaLabel,
  secondaryCtaLabel,
  statLabels,
}: UploadCardProps) {
  const inputId = `${variant}-input`;
  const secondaryInputId = `${variant}-input-alt`;
  const [isDragging, setIsDragging] = useState(false);
  const inputRef = useRef<HTMLInputElement | null>(null);
  const secondaryInputRef = useRef<HTMLInputElement | null>(null);

  const stats = useMemo(() => deriveStats(state), [state]);

  const handleFileList = useCallback(
    (list: FileList | null) => {
      if (!list || list.length === 0) return;
      onFiles(Array.from(list));
    },
    [onFiles],
  );

  const onDragOver = useCallback((e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(true);
  }, []);

  const onDragLeave = useCallback((e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
  }, []);

  const onDrop = useCallback(
    (e: React.DragEvent<HTMLDivElement>) => {
      e.preventDefault();
      e.stopPropagation();
      setIsDragging(false);
      if (state.kind !== "idle" && state.kind !== "error") return;
      handleFileList(e.dataTransfer.files);
    },
    [handleFileList, state.kind],
  );

  const dotColor =
    variant === "code" ? "bg-violet" : "bg-cyan";
  const glow =
    variant === "code"
      ? "radial-gradient(ellipse 340px 160px at 50% -10%, rgba(139,92,246,0.22), transparent 70%)"
      : "radial-gradient(ellipse 340px 160px at 50% -10%, rgba(6,182,212,0.22), transparent 70%)";

  const isBusy = state.kind === "uploading" || state.kind === "running";
  const isDone = state.kind === "done" || state.kind === "already-uploaded";

  return (
    <section
      className="relative overflow-hidden rounded-[22px] border border-line bg-white/[0.02] p-7"
    >
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0 opacity-70"
        style={{ background: glow }}
      />
      <div className="relative z-10">
        {/* Kicker */}
        <div className="flex items-center gap-2.5 font-mono text-[10px] uppercase tracking-[0.22em] text-[#737373]">
          <span className={clsx("h-1.5 w-1.5 rounded-full", dotColor)} />
          {kicker}
        </div>

        {/* Title + desc */}
        <h2 className="mt-3 font-serif text-[32px] leading-[1.08] tracking-[-0.025em] text-white">
          {title}
        </h2>
        <p className="mt-1.5 text-sm leading-[1.55] text-[#a3a3a3]">
          {description}
        </p>

        {/* Source switch */}
        <div
          role="tablist"
          aria-label="Source method"
          className="mt-5 mb-3 flex w-fit gap-1 rounded-[10px] border border-line bg-black/40 p-1"
        >
          {sources.map((s, i) => {
            const on = i === activeSourceIndex;
            return (
              <button
                key={s.label}
                type="button"
                disabled={s.disabled}
                onClick={() => !s.disabled && onSourceChange(i)}
                className={clsx(
                  "rounded-[7px] border-0 px-3 py-1.5 text-xs transition-colors",
                  on
                    ? "bg-white/[0.06] text-white"
                    : "bg-transparent text-[#a3a3a3] hover:text-white",
                  s.disabled && "cursor-not-allowed opacity-50",
                )}
              >
                {s.label}
                {s.disabled ? (
                  <span className="ml-1.5 text-[9px] tracking-wider text-[#525252]">
                    soon
                  </span>
                ) : null}
              </button>
            );
          })}
        </div>

        {/* Primary hidden input — matches ``folder`` mode. */}
        <input
          ref={inputRef}
          id={inputId}
          type="file"
          // @ts-expect-error webkitdirectory isn't in the React HTMLInputElement typing
          webkitdirectory={folder ? "" : undefined}
          directory={folder ? "" : undefined}
          multiple={multiple ?? true}
          accept={accept}
          className="hidden"
          onChange={(e) => {
            handleFileList(e.target.files);
            // reset so the user can pick the same files again if they error out
            e.target.value = "";
          }}
        />

        {/* Secondary hidden input — opposite mode to the primary. An
            <input> cannot be both a file- and folder-picker at once, so
            we mount two and switch via the label htmlFor. */}
        {secondaryCtaLabel ? (
          <input
            ref={secondaryInputRef}
            id={secondaryInputId}
            type="file"
            // @ts-expect-error webkitdirectory isn't in the React HTMLInputElement typing
            webkitdirectory={folder ? undefined : ""}
            directory={folder ? undefined : ""}
            multiple={multiple ?? true}
            accept={folder ? accept : undefined}
            className="hidden"
            onChange={(e) => {
              handleFileList(e.target.files);
              e.target.value = "";
            }}
          />
        ) : null}

        {/* Dropzone */}
        <div
          onDragOver={onDragOver}
          onDragLeave={onDragLeave}
          onDrop={onDrop}
          className={clsx(
            "relative mt-2.5 rounded-[14px] border border-dashed border-white/[0.15] bg-black/25 px-5 py-7 text-center transition-colors",
            isDragging && "border-white/30 bg-white/[0.03]",
            isDone &&
              "border-solid border-emerald/35 bg-emerald/[0.05]",
          )}
          style={
            isDone
              ? { borderColor: "rgba(16,185,129,0.35)", background: "rgba(16,185,129,0.05)" }
              : undefined
          }
        >
          {state.kind === "idle" || state.kind === "error" ? (
            <>
              <div className="mx-auto mb-2.5 inline-flex h-10 w-10 items-center justify-center rounded-xl bg-white/[0.04] text-[#d4d4d4]">
                {folder ? <FolderOpen size={20} strokeWidth={1.8} /> : <Upload size={20} strokeWidth={1.8} />}
              </div>
              <div className="text-sm font-medium text-white">
                {idleTitle}
              </div>
              <div className="mt-1 text-xs text-[#737373]">{idleMeta}</div>
              <div className="mt-4 flex flex-wrap items-center justify-center gap-2">
                <label
                  htmlFor={inputId}
                  className="btn btn-ghost cursor-pointer"
                >
                  {ctaLabel}
                </label>
                {secondaryCtaLabel ? (
                  <label
                    htmlFor={secondaryInputId}
                    className="btn btn-ghost cursor-pointer"
                  >
                    {secondaryCtaLabel}
                  </label>
                ) : null}
                {state.kind === "error" ? (
                  <span className="text-xs text-[#fca5a5]">
                    {state.message}
                  </span>
                ) : null}
              </div>
            </>
          ) : null}

          {state.kind === "uploading" ? (
            <>
              <div
                className="mx-auto mb-2.5 inline-flex h-10 w-10 items-center justify-center rounded-xl bg-white/[0.04] text-[#d4d4d4]"
                style={{
                  background: "rgba(139,92,246,0.12)",
                  color: "#c4b5fd",
                }}
              >
                <Loader2 size={20} strokeWidth={1.8} className="animate-spin" />
              </div>
              <div className="text-sm font-medium text-white">
                Uploading {state.fileCount} file{state.fileCount === 1 ? "" : "s"}...
              </div>
              <div className="mt-1 text-xs text-[#737373]">
                Hang on while we stream them to the ingestion service.
              </div>
            </>
          ) : null}

          {state.kind === "running" ? (
            <div className="text-left">
              <div className="mb-3 flex items-center gap-2.5">
                <span
                  className="inline-flex h-10 w-10 items-center justify-center rounded-xl"
                  style={{
                    background:
                      variant === "code"
                        ? "rgba(139,92,246,0.12)"
                        : "rgba(6,182,212,0.12)",
                    color: variant === "code" ? "#c4b5fd" : "#67e8f9",
                  }}
                >
                  <Loader2 size={20} strokeWidth={1.8} className="animate-spin" />
                </span>
                <div>
                  <div className="text-sm font-medium text-white">
                    Ingesting...
                  </div>
                  <div className="text-[11px] font-mono tracking-wider text-[#737373]">
                    job {state.jobId.slice(0, 8)}
                  </div>
                </div>
              </div>
              <div className="max-h-40 space-y-1 overflow-auto rounded-[10px] border border-line bg-black/30 p-3 font-mono text-[11px] leading-relaxed text-[#a3a3a3]">
                {state.messages.length === 0 ? (
                  <div className="text-[#525252]">Waiting for the first event...</div>
                ) : (
                  state.messages.slice(-20).map((m, i) => (
                    <div key={i} className="animate-rise">
                      <span className="text-[#525252]">{">"}</span> {m}
                    </div>
                  ))
                )}
              </div>
            </div>
          ) : null}

          {isDone ? (
            <>
              <div
                className="mx-auto mb-2.5 inline-flex h-10 w-10 items-center justify-center rounded-xl"
                style={{
                  background: "rgba(16,185,129,0.12)",
                  color: "#6ee7b7",
                }}
              >
                <Check size={20} strokeWidth={1.8} />
              </div>
              <div className="text-sm font-medium text-white">
                {state.kind === "already-uploaded"
                  ? `${idleTitle.replace(/^[a-z]/, (c) => c.toUpperCase())} already uploaded`
                  : `${idleTitle.replace(/^[a-z]/, (c) => c.toUpperCase())} ingested`}
              </div>
              <div className="mt-1 text-xs text-[#737373]">
                {state.kind === "done"
                  ? `${state.result.files_processed} files processed · ${state.result.chunks_stored} chunks stored${
                      state.result.errors.length > 0
                        ? ` · ${state.result.errors.length} errors`
                        : ""
                    }`
                  : state.kind === "already-uploaded"
                    ? `${state.fileCount} files on disk${
                        state.chunkCount !== null
                          ? ` · ${state.chunkCount.toLocaleString()} chunks indexed`
                          : ""
                      } · ready to query`
                    : ""}
              </div>
              <div className="mt-4 flex flex-wrap items-center justify-center gap-2">
                <label
                  htmlFor={inputId}
                  className="btn btn-ghost cursor-pointer"
                >
                  Replace
                </label>
                {secondaryCtaLabel ? (
                  <label
                    htmlFor={secondaryInputId}
                    className="btn btn-ghost cursor-pointer"
                  >
                    {secondaryCtaLabel}
                  </label>
                ) : null}
              </div>
            </>
          ) : null}
        </div>

        {/* Recent log preview (only when running and there are messages, or done) */}
        {isDone && state.kind === "done" && state.messages.length > 0 ? (
          <div className="mt-4 flex flex-col gap-2">
            <div className="grid grid-cols-[24px_1fr_auto_auto] items-center gap-3 rounded-[10px] border border-line bg-white/[0.02] px-3 py-2.5 text-[13px]">
              <span className="text-[#737373]">
                <FileText size={16} strokeWidth={1.8} />
              </span>
              <span className="truncate text-[#e5e5e5]">
                {state.messages[state.messages.length - 1]}
              </span>
              <span className="font-mono text-[11px] text-[#737373]">
                {state.result.files_processed} files
              </span>
              <span className="font-mono text-[10px] uppercase tracking-[0.18em] text-emerald-fg">
                {variant === "code" ? "parsed" : "chunked"}
              </span>
            </div>
          </div>
        ) : null}

        {/* Stats strip */}
        <div className="mt-4 grid grid-cols-2 gap-3">
          {statLabels.map((label, i) => (
            <div
              key={label}
              className="rounded-xl border border-line bg-white/[0.015] px-3.5 py-3"
            >
              <div className="font-mono text-[10px] uppercase tracking-[0.2em] text-[#737373]">
                {label}
              </div>
              <div className="mt-1 font-mono text-base text-white">
                {isBusy || stats[i] === null ? (
                  <span className="text-[#525252]">—</span>
                ) : (
                  stats[i]!.toLocaleString()
                )}
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
