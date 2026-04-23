export interface SourceResult {
  source_file: string;
  chunk_type: string;
  kind: string;
  score: number;
  embed_text: string;
}

export interface DriftFinding {
  issue_type: string;
  summary: string;
}

export interface DriftCheckEntry {
  label: string;
  source_file: string;
  line_range: { start: number; end: number } | null;
  status: string;
  summary: string;
  violations: string[];
  confidence: string;
  used_fallback: boolean;
  findings: DriftFinding[];
  supporting_sources: SourceResult[];
}

export interface ReviewContextEntry {
  label: string;
  query_text: string;
  has_conflict: boolean;
  used_fallback: boolean;
  sources: SourceResult[];
}

export interface ReviewPayload {
  workspace: string;
  target: string;
  drift_status: string;
  drift: DriftCheckEntry[];
  context: ReviewContextEntry[];
}

export interface DriftPayload {
  workspace: string;
  target: string;
  status: string;
  checks: DriftCheckEntry[];
}

export interface QueryPayload {
  mode: string;
  query: string;
  answer?: string;
  explanation?: string;
  has_conflict?: boolean;
  used_fallback?: boolean;
  is_implemented?: boolean;
  results: SourceResult[];
}

export interface DoctorCheck {
  name: string;
  ok: boolean;
  detail: string;
  fix?: string;
}

export interface DoctorPayload {
  workspace: {
    name: string;
    repo_root: string;
    config_path: string;
    runtime_compose_path: string;
  };
  ok: boolean;
  checks: DoctorCheck[];
  suggested_fixes: string[];
}

export interface ServicesStatusPayload {
  workspace: string;
  action: string;
  compose_file: string;
  compose_command: string[];
  ok: boolean;
  stdout: string;
  stderr: string;
  running?: boolean;
}

export interface IngestSummary {
  kind: string;
  path: string;
  files_processed: number;
  chunks_parsed: number;
  chunks_normalized: number;
  chunks_embedded: number;
  chunks_stored: number;
  errors: string[];
}

export interface IngestPayload {
  workspace: string;
  target: string;
  summaries: IngestSummary[];
  progress: string[];
}

export interface ReindexPayload {
  workspace: string;
  target: string;
  reset: {
    workspace: string;
    collection: string;
    deleted: boolean;
  };
  ingest: IngestPayload;
}

export interface CliFailure extends Error {
  code: string;
  exitCode?: number;
  stderr?: string;
  stdout?: string;
  command?: string[];
  suggestedFixes?: string[];
}
