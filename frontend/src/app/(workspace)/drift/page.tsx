"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";

import { DriftEvidencePane } from "@/components/drift/DriftEvidencePane";
import { DriftFileTreePane } from "@/components/drift/DriftFileTreePane";
import { DriftReviewStage } from "@/components/drift/DriftReviewStage";
import {
  corpora,
  review,
  type FileReviewResponse,
  type TreeNode,
} from "@/lib/api";

function firstFile(node: TreeNode): string | null {
  if (node.type === "file") return node.path;
  for (const child of node.children ?? []) {
    const found = firstFile(child);
    if (found) return found;
  }
  return null;
}

export default function DriftPage() {
  return (
    <Suspense fallback={<div className="empty">Loading drift review…</div>}>
      <DriftPageInner />
    </Suspense>
  );
}

function DriftPageInner() {
  const searchParams = useSearchParams();
  const requestedFile = searchParams.get("file");
  const [activePath, setActivePath] = useState<string | null>(null);

  const treeQuery = useQuery({
    queryKey: ["code-tree"],
    queryFn: () => corpora.codeTree(),
  });

  useEffect(() => {
    if (requestedFile && requestedFile !== activePath) {
      setActivePath(requestedFile);
      return;
    }
    if (!requestedFile && treeQuery.data && !activePath) {
      const initial = firstFile(treeQuery.data);
      if (initial) setActivePath(initial);
    }
  }, [requestedFile, treeQuery.data, activePath]);

  const reviewQuery = useQuery<FileReviewResponse>({
    queryKey: ["drift-review", activePath],
    queryFn: () => review.file({ path: activePath as string }),
    enabled: Boolean(activePath),
    retry: false,
  });

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
    return <div className="empty">Failed to load code tree. Is the backend running?</div>;
  }

  const treeRoot =
    treeQuery.data ?? ({ name: "root", path: "", type: "dir", children: [] } as TreeNode);
  const error =
    reviewQuery.error instanceof Error ? reviewQuery.error.message : null;

  return (
    <div className="drift-cols">
      <DriftFileTreePane
        root={treeRoot}
        activePath={activePath}
        onSelect={setActivePath}
      />
      <DriftReviewStage
        filePath={activePath}
        review={reviewQuery.data ?? null}
        loading={reviewQuery.isPending}
        error={error}
      />
      <DriftEvidencePane
        review={reviewQuery.data ?? null}
        loading={reviewQuery.isPending}
        error={error}
      />
    </div>
  );
}
