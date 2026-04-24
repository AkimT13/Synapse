"use client";

import { useEffect, useRef } from "react";

import { review } from "@/lib/api";
import { useDriftStore } from "@/lib/drift-store";

/**
 * Drives sequential file scanning from the drift store queue.
 * Pops one file at a time, calls the review API, and caches the result.
 * Cleans up via AbortController on unmount.
 */
export function useScanQueue() {
  const abortRef = useRef<AbortController | null>(null);

  const queueStatus = useDriftStore((s) => s.queueStatus);
  const currentScan = useDriftStore((s) => s.currentScan);
  const queueLength = useDriftStore((s) => s.queue.length);

  useEffect(() => {
    if (queueStatus !== "scanning") return;
    if (currentScan !== null) return;
    if (queueLength === 0) {
      // Queue drained — mark idle
      useDriftStore.getState().cancelQueue();
      return;
    }

    const path = useDriftStore.getState().dequeueNext();
    if (!path) return;

    const controller = new AbortController();
    abortRef.current = controller;

    let cancelled = false;

    review
      .file({ path })
      .then((response) => {
        if (cancelled) return;
        useDriftStore.getState().cacheResult(path, response);
        useDriftStore.getState().markCurrentComplete();
      })
      .catch((err) => {
        if (cancelled) return;
        const message =
          err instanceof Error ? err.message : "Unknown error";
        useDriftStore.getState().cacheError(path, message);
        useDriftStore.getState().markCurrentError();
      });

    return () => {
      cancelled = true;
      controller.abort();
    };
  }, [queueStatus, currentScan, queueLength]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      abortRef.current?.abort();
    };
  }, []);
}
