"use client";

import { Search } from "lucide-react";

import { FileTree } from "@/components/workspace/FileTree";
import type { TreeNode } from "@/lib/api";

interface DocTreePaneProps {
  tree: TreeNode | null;
  activePath: string | null;
  onSelect: (path: string) => void;
  count: number;
}

export function DocTreePane({
  tree,
  activePath,
  onSelect,
  count,
}: DocTreePaneProps) {
  return (
    <section className="pane">
      <div className="pane-head">
        <span className="pane-title">Documents</span>
        <span className="pane-sub">{count}</span>
      </div>
      <label className="search-box">
        <Search size={12} />
        <input placeholder="Find in docs" />
      </label>
      <div className="pane-body">
        {tree && tree.children && tree.children.length > 0 ? (
          <FileTree
            root={tree}
            activePath={activePath}
            onSelect={onSelect}
            fileIcon="doc"
          />
        ) : (
          <div className="px-4 py-8 text-center text-[13px] text-white/50">
            No knowledge documents yet.
            <div className="mt-3">
              <a
                href="/onboarding"
                className="text-cyan-300 hover:underline text-sm"
              >
                Upload documents →
              </a>
            </div>
          </div>
        )}
      </div>
    </section>
  );
}
