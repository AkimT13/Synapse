"use client";

import { AlertTriangle, CheckCircle2, FlaskConical, Scan, X } from "lucide-react";
import { useMemo } from "react";

import type { TreeNode } from "@/lib/api";
import { cn } from "@/lib/cn";
import { useDriftStore } from "@/lib/drift-store";
import { StatusBadge } from "./StatusBadge";

interface DriftDashboardProps {
  root: TreeNode;
  onSelectFile: (path: string) => void;
}

function collectFiles(node: TreeNode): string[] {
  if (node.type === "file") return [node.path];
  const paths: string[] = [];
  for (const child of node.children ?? []) paths.push(...collectFiles(child));
  return paths;
}

function timeAgo(ts: number): string {
  const delta = Math.floor((Date.now() - ts) / 1000);
  if (delta < 60) return "just now";
  if (delta < 3600) return `${Math.floor(delta / 60)}m ago`;
  return `${Math.floor(delta / 3600)}h ago`;
}

export function DriftDashboard({ root, onSelectFile }: DriftDashboardProps) {
  const results = useDriftStore((s) => s.results);
  const errors = useDriftStore((s) => s.errors);
  const queueStatus = useDriftStore((s) => s.queueStatus);
  const currentScan = useDriftStore((s) => s.currentScan);
  const completedCount = useDriftStore((s) => s.completedCount);
  const totalQueued = useDriftStore((s) => s.totalQueued);
  const enqueueFiles = useDriftStore((s) => s.enqueueFiles);
  const cancelQueue = useDriftStore((s) => s.cancelQueue);

  const allFiles = useMemo(() => collectFiles(root), [root]);

  const aligned = useMemo(
    () => Array.from(results.values()).filter((r) => r.status === "aligned").length,
    [results],
  );
  const needAttention = useMemo(
    () =>
      Array.from(results.values()).filter(
        (r) => r.status === "warning" || r.status === "conflict",
      ).length + errors.size,
    [results, errors],
  );

  // Donut chart data
  const scanned = results.size;
  const total = Math.max(allFiles.length, 1);
  const alignedPct = (aligned / total) * 100;
  const attentionPct = (needAttention / total) * 100;
  const circumference = 2 * Math.PI * 40;

  const handleScanAll = () => {
    enqueueFiles(allFiles);
  };

  const progressPct = totalQueued > 0 ? (completedCount / totalQueued) * 100 : 0;

  return (
    <div className="drift-dashboard">
      {/* Summary Section */}
      <section className="drift-dashboard-summary">
        <div className="drift-summary-ring">
          <svg viewBox="0 0 100 100" className="drift-ring-svg">
            {/* Background ring */}
            <circle
              cx="50" cy="50" r="40"
              fill="none"
              stroke="rgba(255,255,255,0.06)"
              strokeWidth="8"
            />
            {/* Aligned arc */}
            {alignedPct > 0 && (
              <circle
                cx="50" cy="50" r="40"
                fill="none"
                stroke="rgba(16,185,129,0.8)"
                strokeWidth="8"
                strokeDasharray={`${(alignedPct / 100) * circumference} ${circumference}`}
                strokeDashoffset="0"
                strokeLinecap="round"
                transform="rotate(-90 50 50)"
              />
            )}
            {/* Attention arc */}
            {attentionPct > 0 && (
              <circle
                cx="50" cy="50" r="40"
                fill="none"
                stroke="rgba(248,113,113,0.8)"
                strokeWidth="8"
                strokeDasharray={`${(attentionPct / 100) * circumference} ${circumference}`}
                strokeDashoffset={`${-(alignedPct / 100) * circumference}`}
                strokeLinecap="round"
                transform="rotate(-90 50 50)"
              />
            )}
          </svg>
          <div className="drift-ring-center">
            <strong>{scanned}</strong>
            <span>scanned</span>
          </div>
        </div>

        <div className="drift-summary-cards">
          <div className="drift-summary-card">
            <FlaskConical size={16} className="text-violet-fg" />
            <div>
              <strong>{allFiles.length}</strong>
              <span>Files in codebase</span>
            </div>
          </div>
          <div className="drift-summary-card is-aligned">
            <CheckCircle2 size={16} />
            <div>
              <strong>{aligned}</strong>
              <span>Aligned</span>
            </div>
          </div>
          <div className="drift-summary-card is-attention">
            <AlertTriangle size={16} />
            <div>
              <strong>{needAttention}</strong>
              <span>Need attention</span>
            </div>
          </div>
        </div>
      </section>

      {/* Scan Controls */}
      <section className="drift-scan-bar">
        {queueStatus === "idle" ? (
          <button
            type="button"
            className="btn btn-accent"
            onClick={handleScanAll}
            disabled={allFiles.length === 0}
          >
            <Scan size={14} />
            Scan all files
          </button>
        ) : (
          <>
            <div className="drift-scan-progress-wrap">
              <span className="drift-scan-label">
                Scanning {completedCount + 1} of {totalQueued}…
              </span>
              <div className="drift-progress-bar">
                <div
                  className="drift-progress-fill"
                  style={{ width: `${progressPct}%` }}
                />
              </div>
            </div>
            <button
              type="button"
              className="btn btn-ghost"
              onClick={cancelQueue}
            >
              <X size={14} />
              Cancel
            </button>
          </>
        )}
      </section>

      {/* File Status List */}
      <section className="drift-file-list">
        {allFiles.length === 0 ? (
          <div className="empty">No files scanned yet.</div>
        ) : (
          allFiles.map((path) => {
            const cached = results.get(path);
            const errored = errors.get(path);
            const isScanning = currentScan === path;

            return (
              <button
                key={path}
                type="button"
                className={cn("drift-file-row", isScanning && "is-scanning")}
                onClick={() => onSelectFile(path)}
              >
                <span className="drift-file-row-path">{path}</span>
                <span className="drift-file-row-status">
                  {isScanning ? (
                    <span className="drift-scanning-pill">Scanning…</span>
                  ) : cached ? (
                    <>
                      <StatusBadge status={cached.status} />
                      <span className="drift-file-row-time">{timeAgo(cached.scannedAt)}</span>
                    </>
                  ) : errored ? (
                    <span className="drift-error-pill">Error</span>
                  ) : (
                    <span className="drift-unscanned-pill">Not scanned</span>
                  )}
                </span>
              </button>
            );
          })
        )}
      </section>
    </div>
  );
}
