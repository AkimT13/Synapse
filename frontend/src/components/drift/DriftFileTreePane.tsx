"use client";

import { ArrowLeft, Beaker, Search, X } from "lucide-react";
import { useMemo } from "react";

import { FileTree } from "@/components/workspace/FileTree";
import type { TreeNode } from "@/lib/api";
import { useDriftStore } from "@/lib/drift-store";

interface DriftFileTreePaneProps {
  root: TreeNode;
  activePath: string | null;
  onSelect: (path: string) => void;
}

function countFiles(node: TreeNode): number {
  if (node.type === "file") return 1;
  let total = 0;
  for (const child of node.children ?? []) total += countFiles(child);
  return total;
}

function filterTree(node: TreeNode, query: string): TreeNode | null {
  if (node.type === "file") {
    return node.path.toLowerCase().includes(query) ? node : null;
  }
  const filtered = (node.children ?? [])
    .map((child) => filterTree(child, query))
    .filter(Boolean) as TreeNode[];
  if (filtered.length === 0) return null;
  return { ...node, children: filtered };
}

export function DriftFileTreePane({
  root,
  activePath,
  onSelect,
}: DriftFileTreePaneProps) {
  const searchQuery = useDriftStore((s) => s.searchQuery);
  const setSearchQuery = useDriftStore((s) => s.setSearchQuery);
  const view = useDriftStore((s) => s.view);
  const setView = useDriftStore((s) => s.setView);

  const displayRoot = useMemo(() => {
    if (!searchQuery.trim()) return root;
    return filterTree(root, searchQuery.trim().toLowerCase()) ?? {
      name: root.name,
      path: root.path,
      type: "dir" as const,
      children: [],
    };
  }, [root, searchQuery]);

  const fileCount = countFiles(displayRoot);

  return (
    <section className="pane">
      <div className="pane-head">
        <div className="flex flex-col gap-1">
          {view === "detail" && (
            <button
              type="button"
              className="drift-back-btn"
              onClick={() => setView("dashboard")}
            >
              <ArrowLeft size={13} />
              Back to overview
            </button>
          )}
          <span className="pane-title">Review queue</span>
          <span className="pane-sub">Choose a file to assess for scientific drift</span>
        </div>
        <span className="pane-sub">{fileCount}</span>
      </div>
      <div className="search-box">
        <Search size={12} />
        <input
          placeholder="Locate a code file"
          aria-label="Locate a code file"
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
        />
        {searchQuery && (
          <button
            type="button"
            className="drift-search-clear"
            onClick={() => setSearchQuery("")}
            aria-label="Clear search"
          >
            <X size={12} />
          </button>
        )}
      </div>
      <div className="drift-queue-note">
        <Beaker size={14} />
        <span>Focus on code that implements domain rules, thresholds, or protocols.</span>
      </div>
      <div className="pane-body">
        <FileTree
          root={displayRoot}
          activePath={activePath}
          onSelect={onSelect}
          fileIcon="code"
        />
      </div>
    </section>
  );
}
