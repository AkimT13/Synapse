import { execFile } from "node:child_process";
import { promisify } from "node:util";
import path from "node:path";

import type {
  CliFailure,
  DoctorPayload,
  DriftPayload,
  QueryPayload,
  ReviewPayload,
  ReindexPayload,
  IngestPayload,
  ServicesStatusPayload,
} from "./types/models";

const execFileAsync = promisify(execFile);

export interface ExecResult {
  stdout: string;
  stderr: string;
}

export interface ExecFileLike {
  (file: string, args: string[], options: { cwd: string }): Promise<ExecResult>;
}

export interface CliRunnerOptions {
  binary?: string;
  exec?: ExecFileLike;
}

export class SynapseCliRunner {
  private readonly binary: string;
  private readonly exec: ExecFileLike;

  constructor(options: CliRunnerOptions = {}) {
    this.binary = options.binary ?? "synapse";
    this.exec = options.exec ?? defaultExecFile;
  }

  async reviewFile(workspaceRoot: string, filePath: string): Promise<ReviewPayload> {
    return this.runJson(
      ["review", "--file", ensureAbsolute(filePath, workspaceRoot), "--json"],
      workspaceRoot,
    );
  }

  async driftCheckFile(workspaceRoot: string, filePath: string): Promise<DriftPayload> {
    return this.runJson(
      ["drift-check", "--file", ensureAbsolute(filePath, workspaceRoot), "--json"],
      workspaceRoot,
    );
  }

  async queryCode(workspaceRoot: string, text: string): Promise<QueryPayload> {
    return this.runJson(["query", "code", text, "--json"], workspaceRoot);
  }

  async queryFree(workspaceRoot: string, text: string): Promise<QueryPayload> {
    return this.runJson(["query", "free", text, "--json"], workspaceRoot);
  }

  async doctor(workspaceRoot: string): Promise<DoctorPayload> {
    return this.runJson(["doctor", "--json"], workspaceRoot);
  }

  async servicesStatus(workspaceRoot: string): Promise<ServicesStatusPayload> {
    return this.runJson(["services", "status", "--json"], workspaceRoot);
  }

  async ingestWorkspace(workspaceRoot: string): Promise<IngestPayload> {
    return this.runJson(["ingest", "--json"], workspaceRoot);
  }

  async reindexWorkspace(workspaceRoot: string): Promise<ReindexPayload> {
    return this.runJson(["reindex", "--json"], workspaceRoot);
  }

  async openServiceLogs(workspaceRoot: string): Promise<string> {
    const result = await this.runRaw(["services", "logs"], workspaceRoot);
    return [result.stdout.trim(), result.stderr.trim()].filter(Boolean).join("\n");
  }

  async runJson<T>(args: string[], workspaceRoot: string): Promise<T> {
    const result = await this.runRaw(args, workspaceRoot);
    const raw = result.stdout.trim();
    if (!raw) {
      throw createCliFailure({
        code: "EMPTY_STDOUT",
        message: "Synapse returned no JSON output.",
        stdout: result.stdout,
        stderr: result.stderr,
        command: [this.binary, ...withRepoRoot(args, workspaceRoot)],
      });
    }

    try {
      return JSON.parse(raw) as T;
    } catch (error) {
      throw createCliFailure({
        code: "INVALID_JSON",
        message: "Synapse returned invalid JSON.",
        stdout: result.stdout,
        stderr: result.stderr,
        command: [this.binary, ...withRepoRoot(args, workspaceRoot)],
        cause: error,
      });
    }
  }

  async runRaw(args: string[], workspaceRoot: string): Promise<ExecResult> {
    const command = withRepoRoot(args, workspaceRoot);
    try {
      return await this.exec(this.binary, command, { cwd: workspaceRoot });
    } catch (error) {
      throw normalizeExecError(error, this.binary, command);
    }
  }
}

export function ensureAbsolute(filePath: string, baseDir?: string): string {
  if (path.isAbsolute(filePath)) {
    return filePath;
  }
  return path.resolve(baseDir ?? process.cwd(), filePath);
}

export function withRepoRoot(args: string[], workspaceRoot: string): string[] {
  return [...args, "--repo-root", workspaceRoot];
}

export async function defaultExecFile(
  file: string,
  args: string[],
  options: { cwd: string },
): Promise<ExecResult> {
  const result = await execFileAsync(file, args, {
    cwd: options.cwd,
    encoding: "utf-8",
    maxBuffer: 8 * 1024 * 1024,
  });
  return {
    stdout: result.stdout,
    stderr: result.stderr,
  };
}

export function createCliFailure(options: {
  code: string;
  message: string;
  exitCode?: number;
  stdout?: string;
  stderr?: string;
  command?: string[];
  suggestedFixes?: string[];
  cause?: unknown;
}): CliFailure {
  const error = new Error(options.message) as CliFailure;
  error.code = options.code;
  error.exitCode = options.exitCode;
  error.stdout = options.stdout;
  error.stderr = options.stderr;
  error.command = options.command;
  error.suggestedFixes = options.suggestedFixes;
  if (options.cause) {
    (error as Error & { cause?: unknown }).cause = options.cause;
  }
  return error;
}

export function normalizeExecError(
  error: unknown,
  binary: string,
  command: string[],
): CliFailure {
  const candidate = error as NodeJS.ErrnoException & {
    code?: string;
    stdout?: string;
    stderr?: string;
  };

  if (candidate?.code === "ENOENT") {
    return createCliFailure({
      code: "BINARY_MISSING",
      message: `Could not find \`${binary}\` on PATH.`,
      command: [binary, ...command],
      suggestedFixes: [
        "Install the Synapse CLI so the `synapse` command is available on PATH.",
        "Run `synapse doctor` in the workspace terminal after installation.",
      ],
    });
  }

  const exitCode = typeof (candidate as unknown as { code?: unknown }).code === "number"
    ? (candidate as unknown as { code: number }).code
    : undefined;
  const stderr = typeof candidate?.stderr === "string" ? candidate.stderr : "";
  const stdout = typeof candidate?.stdout === "string" ? candidate.stdout : "";
  const detail = stderr.trim() || stdout.trim() || String(error);
  return createCliFailure({
    code: "COMMAND_FAILED",
    message: detail,
    exitCode,
    stdout,
    stderr,
    command: [binary, ...command],
    suggestedFixes: inferSuggestedFixes(detail),
  });
}

export function inferSuggestedFixes(detail: string): string[] {
  const fixes: string[] = [];
  if (detail.includes("No .synapse/config.yaml found")) {
    fixes.push("Run `synapse init` in the workspace root.");
  }
  if (detail.includes("not reachable on localhost:50051") || detail.includes("Actian")) {
    fixes.push("Run `synapse services up` and then `synapse doctor`.");
  }
  if (detail.includes("Code file not found")) {
    fixes.push("Open a file that belongs to the current workspace.");
  }
  if (detail.includes("No Python functions found")) {
    fixes.push("Review and drift check currently expect a Python file with functions.");
  }
  return fixes;
}
