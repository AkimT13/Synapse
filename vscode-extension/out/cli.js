"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.SynapseCliRunner = void 0;
exports.ensureAbsolute = ensureAbsolute;
exports.withRepoRoot = withRepoRoot;
exports.defaultExecFile = defaultExecFile;
exports.createCliFailure = createCliFailure;
exports.normalizeExecError = normalizeExecError;
exports.inferSuggestedFixes = inferSuggestedFixes;
const node_child_process_1 = require("node:child_process");
const node_util_1 = require("node:util");
const node_path_1 = __importDefault(require("node:path"));
const execFileAsync = (0, node_util_1.promisify)(node_child_process_1.execFile);
class SynapseCliRunner {
    binary;
    exec;
    constructor(options = {}) {
        this.binary = options.binary ?? "synapse";
        this.exec = options.exec ?? defaultExecFile;
    }
    async reviewFile(workspaceRoot, filePath) {
        return this.runJson(["review", "--file", ensureAbsolute(filePath, workspaceRoot), "--json"], workspaceRoot);
    }
    async driftCheckFile(workspaceRoot, filePath) {
        return this.runJson(["drift-check", "--file", ensureAbsolute(filePath, workspaceRoot), "--json"], workspaceRoot);
    }
    async queryCode(workspaceRoot, text) {
        return this.runJson(["query", "code", text, "--json"], workspaceRoot);
    }
    async queryFree(workspaceRoot, text) {
        return this.runJson(["query", "free", text, "--json"], workspaceRoot);
    }
    async doctor(workspaceRoot) {
        return this.runJson(["doctor", "--json"], workspaceRoot);
    }
    async servicesStatus(workspaceRoot) {
        return this.runJson(["services", "status", "--json"], workspaceRoot);
    }
    async ingestWorkspace(workspaceRoot) {
        return this.runJson(["ingest", "--json"], workspaceRoot);
    }
    async reindexWorkspace(workspaceRoot) {
        return this.runJson(["reindex", "--json"], workspaceRoot);
    }
    async openServiceLogs(workspaceRoot) {
        const result = await this.runRaw(["services", "logs"], workspaceRoot);
        return [result.stdout.trim(), result.stderr.trim()].filter(Boolean).join("\n");
    }
    async runJson(args, workspaceRoot) {
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
            return JSON.parse(raw);
        }
        catch (error) {
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
    async runRaw(args, workspaceRoot) {
        const command = withRepoRoot(args, workspaceRoot);
        try {
            return await this.exec(this.binary, command, { cwd: workspaceRoot });
        }
        catch (error) {
            throw normalizeExecError(error, this.binary, command);
        }
    }
}
exports.SynapseCliRunner = SynapseCliRunner;
function ensureAbsolute(filePath, baseDir) {
    if (node_path_1.default.isAbsolute(filePath)) {
        return filePath;
    }
    return node_path_1.default.resolve(baseDir ?? process.cwd(), filePath);
}
function withRepoRoot(args, workspaceRoot) {
    return [...args, "--repo-root", workspaceRoot];
}
async function defaultExecFile(file, args, options) {
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
function createCliFailure(options) {
    const error = new Error(options.message);
    error.code = options.code;
    error.exitCode = options.exitCode;
    error.stdout = options.stdout;
    error.stderr = options.stderr;
    error.command = options.command;
    error.suggestedFixes = options.suggestedFixes;
    if (options.cause) {
        error.cause = options.cause;
    }
    return error;
}
function normalizeExecError(error, binary, command) {
    const candidate = error;
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
    const exitCode = typeof candidate.code === "number"
        ? candidate.code
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
function inferSuggestedFixes(detail) {
    const fixes = [];
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
//# sourceMappingURL=cli.js.map