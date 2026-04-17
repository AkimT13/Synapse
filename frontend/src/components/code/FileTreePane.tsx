"use client";

import { Search } from "lucide-react";

import { FileTree } from "@/components/workspace/FileTree";
import type { TreeNode } from "@/lib/api";

interface FileTreePaneProps {
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

export function FileTreePane({ root, activePath, onSelect }: FileTreePaneProps) {
  const fileCount = countFiles(root);
  return (
    <section className="pane">
      <div className="pane-head">
        <span className="pane-title">Files</span>
        <span className="pane-sub">{fileCount}</span>
      </div>
      <div className="search-box">
        <Search size={12} />
        <input placeholder="Find in files" />
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
