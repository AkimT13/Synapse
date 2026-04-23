const test = require("node:test");
const assert = require("node:assert/strict");

const {
  SynapseCliRunner,
  createCliFailure,
  inferSuggestedFixes,
  normalizeExecError,
  withRepoRoot,
} = require("../out/cli.js");

test("withRepoRoot appends workspace root", () => {
  assert.deepEqual(withRepoRoot(["doctor", "--json"], "/repo"), [
    "doctor",
    "--json",
    "--repo-root",
    "/repo",
  ]);
});

test("reviewFile uses an absolute file path and workspace cwd", async () => {
  const seen = {};
  const runner = new SynapseCliRunner({
    exec: async (file, args, options) => {
      seen.file = file;
      seen.args = args;
      seen.cwd = options.cwd;
      return {
        stdout: JSON.stringify({ workspace: "demo", target: "/repo/file.py", drift_status: "aligned", drift: [], context: [] }),
        stderr: "",
      };
    },
  });

  const payload = await runner.reviewFile("/repo", "file.py");
  assert.equal(seen.file, "synapse");
  assert.equal(seen.cwd, "/repo");
  assert.deepEqual(seen.args, [
    "review",
    "--file",
    "/repo/file.py",
    "--json",
    "--repo-root",
    "/repo",
  ]);
  assert.equal(payload.target, "/repo/file.py");
});

test("queryCode parses JSON payloads", async () => {
  const runner = new SynapseCliRunner({
    exec: async () => ({
      stdout: JSON.stringify({ mode: "code", query: "Behavior", has_conflict: true, results: [] }),
      stderr: "",
    }),
  });

  const payload = await runner.queryCode("/repo", "Behavior");
  assert.equal(payload.mode, "code");
  assert.equal(payload.has_conflict, true);
});

test("invalid JSON produces a structured failure", async () => {
  const runner = new SynapseCliRunner({
    exec: async () => ({
      stdout: "not-json",
      stderr: "",
    }),
  });

  await assert.rejects(
    () => runner.doctor("/repo"),
    (error) => error.code === "INVALID_JSON",
  );
});

test("ENOENT becomes a missing-binary failure", () => {
  const error = Object.assign(new Error("missing"), { code: "ENOENT" });
  const failure = normalizeExecError(error, "synapse", ["doctor", "--json"]);
  assert.equal(failure.code, "BINARY_MISSING");
  assert.match(failure.message, /Could not find `synapse`/);
});

test("stderr-derived failures include setup guidance", () => {
  const failure = createCliFailure({
    code: "COMMAND_FAILED",
    message: "No .synapse/config.yaml found",
    stderr: "No .synapse/config.yaml found",
    suggestedFixes: inferSuggestedFixes("No .synapse/config.yaml found"),
  });
  assert.deepEqual(failure.suggestedFixes, ["Run `synapse init` in the workspace root."]);
});
