"use client";

import { File, FileText, FolderClosed, FolderOpen } from "lucide-react";
import { useMemo, useState } from "react";

import type { TreeNode } from "@/lib/api";
import { cn } from "@/lib/cn";

interface FileTreeProps {
  root: TreeNode;
  activePath: string | null;
  onSelect: (path: string) => void;
  // Icon used for leaf files. Code gets <File/>, knowledge gets <FileText/>.
  fileIcon?: "code" | "doc";
}

export function FileTree({ root, activePath, onSelect, fileIcon = "code" }: FileTreeProps) {
  if (!root.children || root.children.length === 0) {
    return <div className="empty">No files yet.</div>;
  }
  return (
    <div className="tree">
      {root.children.map((child) => (
        <TreeNodeView
          key={child.path}
          node={child}
          depth={0}
          activePath={activePath}
          onSelect={onSelect}
          fileIcon={fileIcon}
        />
      ))}
    </div>
  );
}

interface TreeNodeViewProps {
  node: TreeNode;
  depth: number;
  activePath: string | null;
  onSelect: (path: string) => void;
  fileIcon: "code" | "doc";
}

function TreeNodeView({ node, depth, activePath, onSelect, fileIcon }: TreeNodeViewProps) {
  const initiallyOpen = useMemo(
    () => activePath?.startsWith(`${node.path}/`) ?? false,
    [activePath, node.path],
  );
  const [open, setOpen] = useState(initiallyOpen || depth < 1);

  const padding = { paddingLeft: 10 + depth * 14 };

  if (node.type === "dir") {
    return (
      <>
        <button
          type="button"
          className="tree-item"
          style={padding}
          onClick={() => setOpen((value) => !value)}
        >
          <span className={cn("tree-chevron", open && "open")} />
          <span className="ico">
            {open ? <FolderOpen size={14} /> : <FolderClosed size={14} />}
          </span>
          <span className="truncate">{node.name}</span>
        </button>
        {open &&
          node.children.map((child) => (
            <TreeNodeView
              key={child.path}
              node={child}
              depth={depth + 1}
              activePath={activePath}
              onSelect={onSelect}
              fileIcon={fileIcon}
            />
          ))}
      </>
    );
  }

  const isActive = node.path === activePath;
  return (
    <button
      type="button"
      className={cn("tree-item", isActive && "active")}
      style={padding}
      onClick={() => onSelect(node.path)}
    >
      <span className="ico w-[10px]" />
      <span className="ico">
        {fileIcon === "doc" ? <FileText size={14} /> : <File size={14} />}
      </span>
      <span className="truncate">{node.name}</span>
    </button>
  );
}
