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
      <div className="search-box flex items-center gap-2 mx-3 my-2.5 px-2.5 py-2 border border-white/5 bg-black/30 rounded-lg text-white/40 text-xs">
        <Search size={12} />
        <input
          placeholder="Find in docs"
          className="flex-1 bg-transparent border-0 outline-none text-white/90 text-xs placeholder:text-white/30"
        />
      </div>
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
