export interface IngestionDoneResult {
  files_processed: number;
  chunks_parsed: number;
  chunks_normalized: number;
  chunks_embedded: number;
  chunks_stored: number;
  errors: string[];
}

export type JobState =
  | { kind: "idle" }
  // Set on mount when the backend reports files already on disk from
  // a previous session. Visually identical to "done" but with a
  // "replace" affordance rather than fresh numbers.
  | { kind: "already-uploaded"; fileCount: number }
  | { kind: "uploading"; fileCount: number }
  | { kind: "running"; jobId: string; messages: string[] }
  | { kind: "done"; result: IngestionDoneResult; messages: string[] }
  | { kind: "error"; message: string };
