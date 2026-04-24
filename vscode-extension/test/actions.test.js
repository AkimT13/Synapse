const test = require("node:test");
const assert = require("node:assert/strict");

const { SynapseStateStore } = require("../out/state/store.js");
const {
  createDoctorHandler,
  createQuerySelectionHandler,
  createReviewCurrentFileHandler,
  getAbsoluteFilePath,
} = require("../out/commands/actions.js");

function makeContext(overrides = {}) {
  const calls = { errors: [] };
  const store = new SynapseStateStore();
  const context = {
    cli: {
      reviewFile: async (_workspaceRoot, filePath) => {
        calls.reviewPath = filePath;
        return {
          workspace: "demo",
          target: filePath,
          drift_status: "aligned",
          drift: [],
          context: [],
        };
      },
      driftCheckFile: async () => {
        throw new Error("unused");
      },
      queryCode: async (_workspaceRoot, text) => {
        calls.queryText = text;
        return {
          mode: "code",
          query: text,
          has_conflict: false,
          results: [],
        };
      },
      queryFree: async () => {
        throw new Error("unused");
      },
      doctor: async () => ({
        workspace: {
          name: "demo",
          repo_root: "/repo",
          config_path: "/repo/.synapse/config.yaml",
          runtime_compose_path: "/repo/.synapse/runtime/docker-compose.yml",
        },
        ok: true,
        checks: [],
        suggested_fixes: [],
      }),
      servicesStatus: async () => ({
        workspace: "demo",
        action: "status",
        compose_file: "/repo/.synapse/runtime/docker-compose.yml",
        compose_command: ["docker", "compose"],
        ok: true,
        stdout: "",
        stderr: "",
        running: true,
      }),
      ingestWorkspace: async () => {
        throw new Error("unused");
      },
      reindexWorkspace: async () => {
        throw new Error("unused");
      },
      openServiceLogs: async () => "",
    },
    store,
    window: {
      showErrorMessage: async (message) => {
        calls.errors.push(message);
        return undefined;
      },
      showInformationMessage: async () => undefined,
      showInputBox: async () => undefined,
    },
    commands: {
      executeCommand: async (command) => {
        calls.command = command;
        return undefined;
      },
    },
    output: {
      appendLine: () => undefined,
      show: () => undefined,
    },
    getActiveEditor: () => ({
      document: {
        uri: { fsPath: "/repo/example.py" },
        getText: () => "selected code",
      },
      selection: { isEmpty: false },
    }),
    getWorkspaceFolder: () => ({ uri: { fsPath: "/repo" }, name: "repo" }),
    refreshStatus: async () => undefined,
    ...overrides,
  };
  return { context, calls, store };
}

test("getAbsoluteFilePath returns an absolute path", () => {
  assert.equal(getAbsoluteFilePath("/tmp/a.py"), "/tmp/a.py");
  assert.match(getAbsoluteFilePath("relative.py"), /relative\.py$/);
});

test("review command uses the active file and focuses the Synapse view", async () => {
  const { context, calls } = makeContext();
  await createReviewCurrentFileHandler(context)();
  assert.equal(calls.reviewPath, "/repo/example.py");
  assert.equal(calls.command, "workbench.view.extension.synapse");
});

test("query selection uses only the selected text", async () => {
  const { context, calls, store } = makeContext({
    getActiveEditor: () => ({
      document: {
        uri: { fsPath: "/repo/example.py" },
        getText: () => "threshold = -4 * sigma",
      },
      selection: { isEmpty: false },
    }),
  });
  await createQuerySelectionHandler(context)();
  assert.equal(calls.queryText, "threshold = -4 * sigma");
  assert.equal(store.getSnapshot().query.query, "threshold = -4 * sigma");
});

test("query selection rejects an empty selection", async () => {
  const { context, calls } = makeContext({
    getActiveEditor: () => ({
      document: {
        uri: { fsPath: "/repo/example.py" },
        getText: () => "",
      },
      selection: { isEmpty: true },
    }),
  });
  await createQuerySelectionHandler(context)();
  assert.deepEqual(calls.errors, ["Select code before running Synapse query."]);
});

test("doctor falls back to the workspace when no editor is active", async () => {
  const { context, calls } = makeContext({
    getActiveEditor: () => undefined,
    refreshStatus: async (workspaceRoot) => {
      calls.refreshed = workspaceRoot;
    },
  });
  await createDoctorHandler(context)();
  assert.equal(calls.refreshed, "/repo");
  assert.equal(calls.command, "workbench.view.extension.synapse");
});
