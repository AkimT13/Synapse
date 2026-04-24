"use client";

import { create } from "zustand";

import type { FileReviewResponse, ReviewStatus } from "@/lib/api";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface CachedResult {
  response: FileReviewResponse;
  status: ReviewStatus;
  scannedAt: number;
}

export interface CachedError {
  error: string;
  scannedAt: number;
}

interface DriftState {
  // View mode
  view: "dashboard" | "detail";
  setView: (view: "dashboard" | "detail") => void;

  // File tree search
  searchQuery: string;
  setSearchQuery: (query: string) => void;

  // Results cache
  results: Map<string, CachedResult>;
  errors: Map<string, CachedError>;
  cacheResult: (path: string, response: FileReviewResponse) => void;
  cacheError: (path: string, error: string) => void;
  clearCache: () => void;

  // Scan queue
  queue: string[];
  currentScan: string | null;
  completedCount: number;
  totalQueued: number;
  queueStatus: "idle" | "scanning";
  enqueueFiles: (paths: string[]) => void;
  dequeueNext: () => string | null;
  markCurrentComplete: () => void;
  markCurrentError: () => void;
  cancelQueue: () => void;
}

// ---------------------------------------------------------------------------
// Store
// ---------------------------------------------------------------------------

export const useDriftStore = create<DriftState>((set, get) => ({
  view: "dashboard",
  setView: (view) => set({ view }),

  searchQuery: "",
  setSearchQuery: (searchQuery) => set({ searchQuery }),

  results: new Map(),
  errors: new Map(),

  cacheResult: (path, response) =>
    set((state) => {
      const next = new Map(state.results);
      next.set(path, {
        response,
        status: response.drift_status,
        scannedAt: Date.now(),
      });
      return { results: next };
    }),

  cacheError: (path, error) =>
    set((state) => {
      const next = new Map(state.errors);
      next.set(path, { error, scannedAt: Date.now() });
      return { errors: next };
    }),

  clearCache: () => set({ results: new Map(), errors: new Map() }),

  queue: [],
  currentScan: null,
  completedCount: 0,
  totalQueued: 0,
  queueStatus: "idle",

  enqueueFiles: (paths) => {
    const { results, errors } = get();
    // Skip files that already have a cached result or error
    const fresh = paths.filter((p) => !results.has(p) && !errors.has(p));
    if (fresh.length === 0) return;
    set({
      queue: fresh,
      completedCount: 0,
      totalQueued: fresh.length,
      queueStatus: "scanning",
      currentScan: null,
    });
  },

  dequeueNext: () => {
    const { queue } = get();
    if (queue.length === 0) {
      set({ queueStatus: "idle", currentScan: null });
      return null;
    }
    const [next, ...rest] = queue;
    set({ queue: rest, currentScan: next });
    return next;
  },

  markCurrentComplete: () =>
    set((state) => ({
      completedCount: state.completedCount + 1,
      currentScan: null,
    })),

  markCurrentError: () =>
    set((state) => ({
      completedCount: state.completedCount + 1,
      currentScan: null,
    })),

  cancelQueue: () =>
    set({ queue: [], currentScan: null, queueStatus: "idle" }),
}));
