"use client";

import "highlight.js/styles/github-dark.css";

import { useSearchParams } from "next/navigation";
import { Suspense, useEffect, useMemo, useState } from "react";

import { DocTreePane } from "@/components/knowledge/DocTreePane";
import { DocViewerPane } from "@/components/knowledge/DocViewerPane";
import { RelatedCodePane } from "@/components/knowledge/RelatedCodePane";
import {
  corpora,
  retrieval,
  type RetrievalResponse,
  type TreeNode,
} from "@/lib/api";
import { useKnowledgeSelection } from "@/lib/stores";

function countFiles(node: TreeNode | null): number {
  if (!node) return 0;
  if (node.type === "file") return 1;
  let n = 0;
  for (const child of node.children ?? []) n += countFiles(child);
  return n;
}

function firstFile(node: TreeNode | null): string | null {
  if (!node) return null;
  if (node.type === "file") return node.path;
  for (const child of node.children ?? []) {
    const found = firstFile(child);
    if (found) return found;
  }
  return null;
}

export default function KnowledgePage() {
  return (
    <Suspense fallback={<div className="empty">Loading documents…</div>}>
      <KnowledgePageInner />
    </Suspense>
  );
}

function KnowledgePageInner() {
  const [tree, setTree] = useState<TreeNode | null>(null);
  const [treeError, setTreeError] = useState<string | null>(null);

  const [activePath, setActivePath] = useState<string | null>(null);
  const [content, setContent] = useState<string | null>(null);
  const [docLoading, setDocLoading] = useState(false);
  const [docError, setDocError] = useState<string | null>(null);

  const { selection, setSelection } = useKnowledgeSelection();
  const searchParams = useSearchParams();
  const requestedFile = searchParams.get("file");

  const [retrievalResp, setRetrievalResp] =
    useState<RetrievalResponse | null>(null);
  const [retrievalLoading, setRetrievalLoading] = useState(false);
  const [retrievalError, setRetrievalError] = useState<string | null>(null);

  // Load knowledge tree once on mount. Deep-links (?file=…) win over the
  // first-file fallback so citations can jump to a specific document.
  useEffect(() => {
    let cancelled = false;
    corpora
      .knowledgeTree()
      .then((t) => {
        if (cancelled) return;
        setTree(t);
        setActivePath((current) => current ?? requestedFile ?? firstFile(t));
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        setTreeError(
          err instanceof Error ? err.message : "Failed to load documents",
        );
      });
    return () => {
      cancelled = true;
    };
  }, [requestedFile]);

  // If the user navigates to a different ?file= while already on the page,
  // swap the viewer to that doc.
  useEffect(() => {
    if (requestedFile && requestedFile !== activePath) {
      setActivePath(requestedFile);
    }
  }, [requestedFile, activePath]);

  // Fetch the active document's contents whenever `activePath` changes.
  useEffect(() => {
    if (!activePath) {
      setContent(null);
      return;
    }
    let cancelled = false;
    setDocLoading(true);
    setDocError(null);
    corpora
      .knowledgeFile(activePath)
      .then((text) => {
        if (cancelled) return;
        setContent(text);
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        setDocError(
          err instanceof Error ? err.message : "Failed to load document",
        );
        setContent(null);
      })
      .finally(() => {
        if (!cancelled) setDocLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [activePath]);

  // Kick off a retrieval query for the given passage.
  async function runRetrieval(text: string) {
    if (!text.trim()) return;
    setRetrievalLoading(true);
    setRetrievalError(null);
    setRetrievalResp(null);
    try {
      const resp = await retrieval.knowledgeToCode({ text });
      setRetrievalResp(resp);
    } catch (err) {
      setRetrievalError(
        err instanceof Error ? err.message : "Retrieval failed",
      );
    } finally {
      setRetrievalLoading(false);
    }
  }

  function onSelectPassage(text: string) {
    if (!activePath) return;
    setSelection({ file: activePath, text });
    runRetrieval(text);
  }

  function onRefresh() {
    if (selection?.text) {
      runRetrieval(selection.text);
    }
  }

  // Clear selection when switching documents so the chip doesn't lie.
  useEffect(() => {
    if (selection && selection.file !== activePath) {
      setSelection(null);
      setRetrievalResp(null);
      setRetrievalError(null);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activePath]);

  const fileCount = useMemo(() => countFiles(tree), [tree]);

  return (
    <div
      className="grid h-full min-h-0"
      style={{ gridTemplateColumns: "264px 1fr 380px" }}
    >
      <DocTreePane
        tree={tree}
        activePath={activePath}
        onSelect={(p) => setActivePath(p)}
        count={fileCount}
      />

      <DocViewerPane
        path={activePath}
        content={treeError ? null : content}
        loading={docLoading}
        error={treeError ?? docError}
        onSelectPassage={onSelectPassage}
        retrievalLoading={retrievalLoading}
      />

      <RelatedCodePane
        selectionText={selection?.text ?? null}
        loading={retrievalLoading}
        error={retrievalError}
        response={retrievalResp}
        onRefresh={onRefresh}
      />
    </div>
  );
}
