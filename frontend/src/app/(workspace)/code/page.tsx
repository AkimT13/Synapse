"use client";

import { useMutation, useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import { CodeViewerPane } from "@/components/code/CodeViewerPane";
import { FileTreePane } from "@/components/code/FileTreePane";
import { RelatedKnowledgePane } from "@/components/code/RelatedKnowledgePane";
import { corpora, retrieval, type RetrievalResponse, type TreeNode } from "@/lib/api";
import { useCodeSelection } from "@/lib/stores";

// Walk a tree until we find the first file; used for the initial
// auto-selection so the viewer isn't empty on mount.
function firstFile(node: TreeNode): string | null {
  if (node.type === "file") return node.path;
  for (const child of node.children ?? []) {
    const found = firstFile(child);
    if (found) return found;
  }
  return null;
}

function detectAnchor(text: string): string | null {
  const m =
    text.match(/\bdef\s+([A-Za-z_][A-Za-z0-9_]*)/) ??
    text.match(/\bclass\s+([A-Za-z_][A-Za-z0-9_]*)/) ??
    text.match(/\bfunction\s+([A-Za-z_][A-Za-z0-9_]*)/);
  return m ? m[1] : null;
}

export default function CodePage() {
  const { selection, setSelection } = useCodeSelection();
  const [activePath, setActivePath] = useState<string | null>(null);
  const [response, setResponse] = useState<RetrievalResponse | null>(null);

  const treeQuery = useQuery({
    queryKey: ["code-tree"],
    queryFn: () => corpora.codeTree(),
  });

  // Default to the first file in the tree once it loads.
  useEffect(() => {
    if (treeQuery.data && !activePath) {
      const initial = firstFile(treeQuery.data);
      if (initial) setActivePath(initial);
    }
  }, [treeQuery.data, activePath]);

  const fileQuery = useQuery({
    queryKey: ["code-file", activePath],
    queryFn: () => corpora.codeFile(activePath as string),
    enabled: Boolean(activePath),
  });

  // Drop the old selection when switching files — it wouldn't make
  // sense against different source.
  useEffect(() => {
    if (selection && activePath && selection.file !== activePath) {
      setSelection(null);
      setResponse(null);
    }
  }, [activePath, selection, setSelection]);

  const retrievalMutation = useMutation({
    mutationFn: (text: string) => retrieval.codeToKnowledge({ text }),
    onSuccess: (data) => setResponse(data),
  });

  const onFindRelated = () => {
    if (!selection) return;
    retrievalMutation.mutate(selection.text);
  };

  const selectionLabel = useMemo(() => {
    if (!selection) return null;
    return detectAnchor(selection.text) ?? `LN ${selection.startLine}–${selection.endLine}`;
  }, [selection]);

  // Empty state: the tree is literally empty. Direct the user back to onboarding.
  if (treeQuery.isSuccess && (!treeQuery.data.children || treeQuery.data.children.length === 0)) {
    return (
      <div className="empty">
        <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
          <span>No code has been ingested yet.</span>
          <Link
            href="/onboarding"
            className="btn btn-ghost"
            style={{ alignSelf: "center" }}
          >
            Go to onboarding
          </Link>
        </div>
      </div>
    );
  }

  if (treeQuery.isLoading) {
    return <div className="empty">Loading workspace…</div>;
  }

  if (treeQuery.isError) {
    return (
      <div className="empty">
        Failed to load code tree. Is the backend running?
      </div>
    );
  }

  const treeRoot =
    treeQuery.data ?? ({ name: "root", path: "", type: "dir", children: [] } as TreeNode);

  return (
    <>
      <style jsx>{`
        .code-cols {
          display: grid;
          grid-template-columns: 264px 1fr 380px;
          height: 100%;
          min-height: 0;
        }
        @media (max-width: 1100px) {
          .code-cols {
            grid-template-columns: 220px 1fr 340px;
          }
        }
      `}</style>
      <div className="code-cols">
        <FileTreePane
          root={treeRoot}
          activePath={activePath}
          onSelect={(path) => {
            setActivePath(path);
            setResponse(null);
          }}
        />
        <CodeViewerPane
          filePath={activePath}
          source={fileQuery.data ?? ""}
          loading={fileQuery.isLoading}
          selection={selection && selection.file === activePath ? selection : null}
          setSelection={setSelection}
          onFindRelated={onFindRelated}
          retrievalLoading={retrievalMutation.isPending}
        />
        <RelatedKnowledgePane
          selection={selection}
          response={response}
          loading={retrievalMutation.isPending}
          onRefresh={onFindRelated}
          selectionLabel={selectionLabel}
        />
      </div>
    </>
  );
}
