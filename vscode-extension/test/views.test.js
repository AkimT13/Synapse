const test = require("node:test");
const assert = require("node:assert/strict");
const Module = require("node:module");

const originalLoad = Module._load;

class MockEventEmitter {
  constructor() {
    this.event = () => ({ dispose() {} });
  }

  fire() {}

  dispose() {}
}

class MockTreeItem {
  constructor(label, collapsibleState = 0) {
    this.label = label;
    this.collapsibleState = collapsibleState;
  }
}

class MockThemeIcon {
  constructor(id) {
    this.id = id;
  }
}

Module._load = function patchedLoad(request, parent, isMain) {
  if (request === "vscode") {
    return {
      EventEmitter: MockEventEmitter,
      TreeItem: MockTreeItem,
      ThemeIcon: MockThemeIcon,
      TreeItemCollapsibleState: {
        None: 0,
        Collapsed: 1,
        Expanded: 2,
      },
    };
  }
  return originalLoad.call(this, request, parent, isMain);
};

const { SynapseStateStore } = require("../out/state/store.js");
const { StatusTreeDataProvider } = require("../out/views/statusView.js");
const { ReviewTreeDataProvider } = require("../out/views/reviewView.js");
const { QueryTreeDataProvider } = require("../out/views/queryView.js");

test.after(() => {
  Module._load = originalLoad;
});

test("status view shows workspace, doctor summary, and expanded guidance", async () => {
  const store = new SynapseStateStore();
  store.update({
    workspaceRoot: "/repo",
    doctor: {
      workspace: {
        name: "demo",
        repo_root: "/repo",
        config_path: "/repo/.synapse/config.yaml",
        runtime_compose_path: "/repo/.synapse/runtime/docker-compose.yml",
      },
      ok: false,
      checks: [
        {
          name: "Config file",
          ok: false,
          detail: "Missing config",
          fix: "Run `synapse init`",
        },
      ],
      suggested_fixes: ["Run `synapse init`"],
    },
    services: {
      workspace: "demo",
      action: "status",
      compose_file: "/repo/.synapse/runtime/docker-compose.yml",
      compose_command: ["docker", "compose"],
      ok: false,
      stdout: "",
      stderr: "service unavailable",
      running: false,
    },
    lastError: "No .synapse/config.yaml found",
  });

  const provider = new StatusTreeDataProvider(store);
  const roots = await provider.getChildren();

  assert.deepEqual(roots.map((item) => item.label), [
    "Workspace",
    "Doctor",
    "Services",
    "Last error",
  ]);
  assert.equal(roots[1].children[2].label, "Config file");
  assert.equal(roots[1].children[3].label, "Suggested fixes");
  assert.equal(roots[3].children[0].description, "Run `synapse init`");
});

test("review view groups review output into file, findings, and context sections", async () => {
  const store = new SynapseStateStore();
  store.update({
    review: {
      workspace: "/repo",
      target: "/repo/example.py",
      drift_status: "aligned",
      drift: [
        {
          label: "Threshold check",
          source_file: "/repo/example.py",
          line_range: { start: 10, end: 12 },
          status: "warning",
          summary: "Threshold may drift from the documented sigma range.",
          violations: ["sigma range mismatch"],
          confidence: "high",
          used_fallback: false,
          findings: [{ issue_type: "domain", summary: "Documented limit is tighter." }],
          supporting_sources: [
            {
              source_file: "/repo/docs/spec.md",
              chunk_type: "knowledge",
              kind: "constraint",
              score: 0.91,
              embed_text: "Threshold should stay within the documented sigma band.",
            },
          ],
        },
      ],
      context: [
        {
          label: "Constraint coverage",
          query_text: "threshold sigma limits",
          has_conflict: true,
          used_fallback: false,
          sources: [
            {
              source_file: "/repo/docs/spec.md",
              chunk_type: "knowledge",
              kind: "constraint",
              score: 0.88,
              embed_text: "Domain limits describe expected threshold behavior.",
            },
          ],
        },
      ],
    },
  });

  const provider = new ReviewTreeDataProvider(store);
  const roots = await provider.getChildren();

  assert.deepEqual(roots.map((item) => item.label), [
    "example.py",
    "Drift findings",
    "Context",
  ]);
  assert.equal(roots[1].children[0].label, "Threshold check");
  assert.equal(roots[1].children[0].children[2].label, "Findings");
  assert.equal(roots[2].children[0].children[1].label, "Sources");
});

test("query view shows flags, narratives, and grouped sources", async () => {
  const store = new SynapseStateStore();
  store.update({
    query: {
      mode: "free_text",
      query: "What does the threshold mean?",
      answer: "It represents the domain cutoff.",
      explanation: "The retrieved material links it to the sigma constraint.",
      has_conflict: false,
      used_fallback: true,
      is_implemented: true,
      results: [
        {
          source_file: "/repo/docs/spec.md",
          chunk_type: "knowledge",
          kind: "constraint",
          score: 0.93,
          embed_text: "Threshold acts as the cutoff for the validated range.",
        },
      ],
    },
  });

  const provider = new QueryTreeDataProvider(store);
  const roots = await provider.getChildren();

  assert.deepEqual(roots.map((item) => item.label), [
    "Free Text",
    "Answer",
    "Explanation",
    "Flags",
    "Results",
  ]);
  assert.equal(roots[3].children[2].label, "Fallback");
  assert.equal(roots[4].children[0].label, "spec.md");
  assert.equal(roots[4].children[0].children[1].label, "Excerpt");
});
