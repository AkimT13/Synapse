/**
 * Typed HTTP client for the Synapse backend.
 *
 * Every function here mirrors a FastAPI endpoint. Shapes are kept in
 * sync manually — the backend schemas are in api/schemas.py. A
 * mismatch is a contract bug; don't paper over it here.
 */

// The backend runs on a sibling port during development. In production
// both live behind the same reverse proxy so a relative URL works.
export const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE ?? "http://127.0.0.1:8000";

// ---------------------------------------------------------------------------
// Shared types (mirror backend/api/schemas.py)
// ---------------------------------------------------------------------------

export type ChunkType = "code" | "knowledge";

export interface SourceRef {
  index: number;
  chunk_type: ChunkType;
  source_file: string;
  title: string;
  excerpt: string;
  score: number;
  kind?: string | null;
}

export interface RetrievalResponse {
  results: SourceRef[];
  explanation?: string | null;
  answer?: string | null;
  has_conflict?: boolean | null;
  is_implemented?: boolean | null;
  used_fallback?: boolean | null;
}

export interface WorkspaceStats {
  code_files: number;
  knowledge_files: number;
  total_code_chunks?: number | null;
  total_knowledge_chunks?: number | null;
}

export interface TreeNode {
  name: string;
  path: string;
  type: "file" | "dir";
  children: TreeNode[];
}

export interface IngestionAck {
  job_id: string;
  files_saved: number;
}

export interface ConversationHeader {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
}

export interface ChatMessage {
  id: string;
  conversation_id: string;
  role: "user" | "assistant";
  content: string;
  sources: SourceRef[];
  created_at: string;
}

export interface ConversationDetail extends ConversationHeader {
  messages: ChatMessage[];
}

// ---------------------------------------------------------------------------
// Low-level helpers
// ---------------------------------------------------------------------------

class ApiError extends Error {
  constructor(
    public readonly status: number,
    message: string,
  ) {
    super(message);
  }
}

async function request<T>(
  path: string,
  init: RequestInit = {},
): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init.headers ?? {}),
    },
  });
  if (!response.ok) {
    const text = await response.text().catch(() => "");
    throw new ApiError(
      response.status,
      text || `${response.status} ${response.statusText}`,
    );
  }
  if (response.status === 204) {
    return undefined as unknown as T;
  }
  return (await response.json()) as T;
}

// ---------------------------------------------------------------------------
// Endpoints
// ---------------------------------------------------------------------------

// -- workspace --
export const workspace = {
  stats: () => request<WorkspaceStats>("/api/workspace/stats"),
  reset: () =>
    request<{ cleared: boolean }>("/api/workspace/reset", { method: "POST" }),
};

// -- corpora --
export const corpora = {
  codeTree: () => request<TreeNode>("/api/corpora/code/tree"),
  knowledgeTree: () => request<TreeNode>("/api/corpora/knowledge/tree"),
  codeFileUrl: (path: string) =>
    `${API_BASE}/api/corpora/code/files/${encodePath(path)}`,
  knowledgeFileUrl: (path: string) =>
    `${API_BASE}/api/corpora/knowledge/files/${encodePath(path)}`,
  async codeFile(path: string): Promise<string> {
    const response = await fetch(this.codeFileUrl(path));
    if (!response.ok) throw new ApiError(response.status, response.statusText);
    return response.text();
  },
  async knowledgeFile(path: string): Promise<string> {
    const response = await fetch(this.knowledgeFileUrl(path));
    if (!response.ok) throw new ApiError(response.status, response.statusText);
    return response.text();
  },
};

function encodePath(path: string): string {
  return path.split("/").map(encodeURIComponent).join("/");
}

// -- ingestion --
// Multipart uploads can't use the JSON helper above.
export async function ingestCode(files: File[]): Promise<IngestionAck> {
  return uploadFiles("/api/ingest/code", files);
}

export async function ingestKnowledge(files: File[]): Promise<IngestionAck> {
  return uploadFiles("/api/ingest/knowledge", files);
}

async function uploadFiles(path: string, files: File[]): Promise<IngestionAck> {
  const body = new FormData();
  for (const file of files) {
    body.append("files", file, fileRelativePath(file));
  }
  const response = await fetch(`${API_BASE}${path}`, { method: "POST", body });
  if (!response.ok) {
    const text = await response.text().catch(() => "");
    throw new ApiError(response.status, text || response.statusText);
  }
  return (await response.json()) as IngestionAck;
}

// webkitdirectory decorates File with `webkitRelativePath`; fall back to
// the plain name for plain-multi-file uploads.
function fileRelativePath(file: File): string {
  const relpath = (file as File & { webkitRelativePath?: string })
    .webkitRelativePath;
  return relpath && relpath.length > 0 ? relpath : file.name;
}

export function ingestJobStreamUrl(jobId: string): string {
  return `${API_BASE}/api/ingest/jobs/${encodeURIComponent(jobId)}/stream`;
}

// -- retrieval --
export const retrieval = {
  codeToKnowledge: (body: {
    text: string;
    k?: number;
    domain?: string;
    constraints_only?: boolean;
  }) =>
    request<RetrievalResponse>("/api/retrieve/code-to-knowledge", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  knowledgeToCode: (body: { text: string; k?: number; language?: string }) =>
    request<RetrievalResponse>("/api/retrieve/knowledge-to-code", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  free: (body: { question: string; k?: number }) =>
    request<RetrievalResponse>("/api/retrieve/free", {
      method: "POST",
      body: JSON.stringify(body),
    }),
};

// -- chat --
export const chat = {
  list: () => request<ConversationHeader[]>("/api/chat/conversations"),
  create: (title?: string) =>
    request<ConversationHeader>("/api/chat/conversations", {
      method: "POST",
      body: JSON.stringify({ title }),
    }),
  get: (id: string) =>
    request<ConversationDetail>(
      `/api/chat/conversations/${encodeURIComponent(id)}`,
    ),
  remove: (id: string) =>
    request<{ ok: boolean }>(
      `/api/chat/conversations/${encodeURIComponent(id)}`,
      { method: "DELETE" },
    ),
  postMessage: (
    id: string,
    body: { content: string; scope?: "all" | "code" | "knowledge"; k?: number },
  ) =>
    request<{ user_message: ChatMessage; assistant_message: ChatMessage }>(
      `/api/chat/conversations/${encodeURIComponent(id)}/messages`,
      { method: "POST", body: JSON.stringify(body) },
    ),
};

export { ApiError };
