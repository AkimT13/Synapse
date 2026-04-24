const test = require("node:test");
const assert = require("node:assert/strict");

const manifest = require("../package.json");

test("manifest exposes the Synapse demo commands with categories", () => {
  const commands = manifest.contributes.commands;
  const ids = commands.map((command) => command.command);

  assert.deepEqual(ids, [
    "synapse.reviewCurrentFile",
    "synapse.driftCheckCurrentFile",
    "synapse.querySelection",
    "synapse.queryFreeText",
    "synapse.ingestWorkspace",
    "synapse.reindexWorkspace",
    "synapse.openServiceLogs",
    "synapse.doctor",
  ]);

  for (const command of commands) {
    assert.equal(command.category, "Synapse");
    assert.ok(command.shortTitle);
  }
});

test("manifest exposes demo-focused welcome content and view actions", () => {
  const welcomeViews = manifest.contributes.viewsWelcome.map((entry) => entry.view);
  assert.deepEqual(welcomeViews, [
    "synapse.statusView",
    "synapse.statusView",
    "synapse.reviewView",
    "synapse.queryView",
  ]);

  const viewTitleCommands = manifest.contributes.menus["view/title"].map((entry) => entry.command);
  assert.deepEqual(viewTitleCommands, [
    "synapse.doctor",
    "synapse.ingestWorkspace",
    "synapse.reindexWorkspace",
    "synapse.openServiceLogs",
    "synapse.reviewCurrentFile",
    "synapse.driftCheckCurrentFile",
    "synapse.querySelection",
    "synapse.queryFreeText",
  ]);
});
