"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense, useCallback, useEffect, useState } from "react";

import { DriftDashboard } from "@/components/drift/DriftDashboard";
import { DriftEvidencePane } from "@/components/drift/DriftEvidencePane";
import { DriftFileTreePane } from "@/components/drift/DriftFileTreePane";
import { DriftReviewStage } from "@/components/drift/DriftReviewStage";
import { useScanQueue } from "@/hooks/useScanQueue";
import {
  corpora,
  review,
  type FileReviewResponse,
  type TreeNode,
} from "@/lib/api";
import { useDriftStore } from "@/lib/drift-store";

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
  const queryClient = useQueryClient();

  const view = useDriftStore((s) => s.view);
  const setView = useDriftStore((s) => s.setView);
  const results = useDriftStore((s) => s.results);

  // Drive the scan queue
  useScanQueue();

  const treeQuery = useQuery({
    queryKey: ["code-tree"],
    queryFn: () => corpora.codeTree(),
  });

  useEffect(() => {
    if (requestedFile && requestedFile !== activePath) {
      setActivePath(requestedFile);
      setView("detail");
      return;
    }
  }, [requestedFile, activePath, setView]);

  const reviewQuery = useQuery<FileReviewResponse>({
    queryKey: ["drift-review", activePath],
    queryFn: () => review.file({ path: activePath as string }),
    enabled: Boolean(activePath) && view === "detail",
    retry: false,
    staleTime: 5 * 60 * 1000,
  });

  // When selecting a file from the dashboard, seed React Query cache from Zustand
  const handleSelectFile = useCallback(
    (path: string) => {
      const cached = results.get(path);
      if (cached) {
        queryClient.setQueryData(["drift-review", path], cached.response);
      }
      setActivePath(path);
      setView("detail");
    },
    [results, queryClient, setView],
  );

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

  if (view === "dashboard") {
    return <DriftDashboard root={treeRoot} onSelectFile={handleSelectFile} />;
  }

  const error =
    reviewQuery.error instanceof Error ? reviewQuery.error.message : null;

  return (
    <div className="drift-cols">
      <DriftFileTreePane
        root={treeRoot}
        activePath={activePath}
        onSelect={handleSelectFile}
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
