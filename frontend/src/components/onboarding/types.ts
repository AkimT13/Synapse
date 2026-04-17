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
  | { kind: "uploading"; fileCount: number }
  | { kind: "running"; jobId: string; messages: string[] }
  | { kind: "done"; result: IngestionDoneResult; messages: string[] }
  | { kind: "error"; message: string };
