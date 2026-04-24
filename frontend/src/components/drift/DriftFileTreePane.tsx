"use client";

import { Beaker, Search } from "lucide-react";

import { FileTree } from "@/components/workspace/FileTree";
import type { TreeNode } from "@/lib/api";

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

export function DriftFileTreePane({
  root,
  activePath,
  onSelect,
}: DriftFileTreePaneProps) {
  const fileCount = countFiles(root);

  return (
    <section className="pane">
      <div className="pane-head">
        <div className="flex flex-col gap-1">
          <span className="pane-title">Review queue</span>
          <span className="pane-sub">Choose a file to assess for scientific drift</span>
        </div>
        <span className="pane-sub">{fileCount}</span>
      </div>
      <div className="search-box">
        <Search size={12} />
        <input placeholder="Locate a code file" aria-label="Locate a code file" />
      </div>
      <div className="drift-queue-note">
        <Beaker size={14} />
        <span>Focus on code that implements domain rules, thresholds, or protocols.</span>
      </div>
      <div className="pane-body">
        <FileTree
          root={root}
          activePath={activePath}
          onSelect={onSelect}
          fileIcon="code"
        />
      </div>
    </section>
  );
}
