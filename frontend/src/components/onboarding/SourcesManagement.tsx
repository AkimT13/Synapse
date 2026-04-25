"use client";

import { Loader2, RefreshCw, Search } from "lucide-react";
import { useRouter } from "next/navigation";
import { useMemo, useState } from "react";

import { FileTree } from "@/components/workspace/FileTree";
import type { TreeNode } from "@/lib/api";
import type { JobState } from "./types";

export interface SourcesManagementProps {
  codeTree: TreeNode | null;
  codeTreeLoading: boolean;
  knowledgeTree: TreeNode | null;
  knowledgeTreeLoading: boolean;
  stats: {
    codeFiles: number;
    codeChunks: number | null;
    knowledgeFiles: number;
    knowledgeChunks: number | null;
  };
  onReplaceCode: () => void;
  onReplaceKnowledge: () => void;
  codeState: JobState;
  knowledgeState: JobState;
}

export function SourcesManagement({
  codeTree,
  codeTreeLoading,
  knowledgeTree,
  knowledgeTreeLoading,
  stats,
  onReplaceCode,
  onReplaceKnowledge,
  codeState,
  knowledgeState,
}: SourcesManagementProps) {
  return (
    <div className="sources-cols">
      <SourcesPane
        title="Code sources"
        tree={codeTree}
        treeLoading={codeTreeLoading}
        fileCount={stats.codeFiles}
        chunkCount={stats.codeChunks}
        onReplace={onReplaceCode}
        state={codeState}
        fileIcon="code"
        navigatePrefix="/code"
      />
      <SourcesPane
        title="Knowledge docs"
        tree={knowledgeTree}
        treeLoading={knowledgeTreeLoading}
        fileCount={stats.knowledgeFiles}
        chunkCount={stats.knowledgeChunks}
        onReplace={onReplaceKnowledge}
        state={knowledgeState}
        fileIcon="doc"
        navigatePrefix="/knowledge"
      />
    </div>
  );
}

/* ------------------------------------------------------------------ */

interface SourcesPaneProps {
  title: string;
  tree: TreeNode | null;
  treeLoading: boolean;
  fileCount: number;
  chunkCount: number | null;
  onReplace: () => void;
  state: JobState;
  fileIcon: "code" | "doc";
  navigatePrefix: string;
}

function SourcesPane({
  title,
  tree,
  treeLoading,
  fileCount,
  chunkCount,
  onReplace,
  state,
  fileIcon,
  navigatePrefix,
}: SourcesPaneProps) {
  const router = useRouter();
  const [filter, setFilter] = useState("");

  const filteredTree = useMemo(() => {
    if (!tree || !filter) return tree;
    return filterTree(tree, filter.toLowerCase());
  }, [tree, filter]);

  const isRunning = state.kind === "uploading" || state.kind === "running";

  return (
    <div className="pane">
      {/* Header */}
      <div className="pane-head">
        <div className="flex items-center gap-3">
          <span className="pane-title">{title}</span>
          <span className="text-[11px] text-[#525252] font-mono">
            {fileCount} file{fileCount !== 1 ? "s" : ""}
          </span>
        </div>
        <button
          type="button"
          onClick={onReplace}
          disabled={isRunning}
          className="btn btn-ghost text-[11px] disabled:opacity-40 disabled:cursor-not-allowed"
        >
          <RefreshCw size={11} />
          Replace
        </button>
      </div>

      {/* Search */}
      <div className="search-box">
        <Search size={13} />
        <input
          placeholder="Filter files…"
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
        />
      </div>

      {/* Body */}
      <div className="pane-body">
        {isRunning ? (
          <InlineProgress state={state} />
        ) : treeLoading ? (
          <div className="flex items-center justify-center py-12 text-[#525252]">
            <Loader2 size={16} className="animate-spin" />
          </div>
        ) : filteredTree ? (
          <FileTree
            root={filteredTree}
            activePath={null}
            onSelect={(path) =>
              router.push(`${navigatePrefix}?file=${encodeURIComponent(path)}`)
            }
            fileIcon={fileIcon}
          />
        ) : (
          <div className="empty">No files.</div>
        )}
      </div>

      {/* Footer stats */}
      <div className="sources-pane-stats">
        <span>
          Files on disk<strong>{fileCount}</strong>
        </span>
        <span>
          Chunks indexed
          <strong>{chunkCount !== null ? chunkCount.toLocaleString() : "—"}</strong>
        </span>
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */

function InlineProgress({ state }: { state: JobState }) {
  if (state.kind === "uploading") {
    return (
      <div className="flex flex-col items-center justify-center gap-2 py-12">
        <Loader2 size={20} className="animate-spin text-[#c4b5fd]" />
        <span className="text-xs text-[#a3a3a3]">
          Uploading {state.fileCount} file{state.fileCount === 1 ? "" : "s"}…
        </span>
      </div>
    );
  }
  if (state.kind === "running") {
    return (
      <div className="p-4">
        <div className="mb-3 flex items-center gap-2.5">
          <Loader2 size={16} className="animate-spin text-[#c4b5fd]" />
          <span className="text-xs font-medium text-white">Ingesting…</span>
          <span className="font-mono text-[10px] text-[#525252]">
            {state.jobId.slice(0, 8)}
          </span>
        </div>
        <div className="max-h-52 space-y-1 overflow-auto rounded-[10px] border border-line bg-black/30 p-3 font-mono text-[11px] leading-relaxed text-[#a3a3a3]">
          {state.messages.length === 0 ? (
            <div className="text-[#525252]">Waiting for the first event…</div>
          ) : (
            state.messages.slice(-20).map((m, i) => (
              <div key={i} className="animate-rise">
                <span className="text-[#525252]">{">"}</span> {m}
              </div>
            ))
          )}
        </div>
      </div>
    );
  }
  return null;
}

/* ------------------------------------------------------------------ */

/** Recursively filter a tree to only include nodes matching the query. */
function filterTree(node: TreeNode, query: string): TreeNode | null {
  if (node.type === "file") {
    return node.name.toLowerCase().includes(query) ? node : null;
  }
  const filtered = node.children
    .map((child) => filterTree(child, query))
    .filter((c): c is TreeNode => c !== null);
  if (filtered.length === 0) return null;
  return { ...node, children: filtered };
}
