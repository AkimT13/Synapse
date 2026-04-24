import * as vscode from "vscode";
import * as path from "node:path";
import type {
  DriftCheckEntry,
  DriftPayload,
  ReviewContextEntry,
  ReviewPayload,
  SourceResult,
} from "../types/models";
import type { SynapseStateStore } from "../state/store";

const VIEW_TYPE = "synapse.reviewPanel";

export class ReviewWebviewPanel {
  private panel: vscode.WebviewPanel | undefined;
  private readonly store: SynapseStateStore;
  private unsubscribe: (() => void) | undefined;

  constructor(store: SynapseStateStore) {
    this.store = store;
  }

  reveal(): void {
    const state = this.store.getSnapshot();
    if (this.panel) {
      this.panel.webview.html = this.buildHtml(state.review, state.drift);
      this.panel.reveal(vscode.ViewColumn.Beside, true);
      return;
    }

    this.panel = vscode.window.createWebviewPanel(
      VIEW_TYPE,
      "Synapse Review",
      { viewColumn: vscode.ViewColumn.Beside, preserveFocus: true },
      { enableScripts: true, retainContextWhenHidden: true },
    );

    this.panel.webview.html = this.buildHtml(state.review, state.drift);

    this.panel.webview.onDidReceiveMessage((msg: unknown) => {
      const message = msg as { command: string; path?: string; line?: number };
      if (message.command === "openFile" && message.path) {
        const uri = vscode.Uri.file(message.path);
        const line = Math.max((message.line ?? 1) - 1, 0);
        vscode.window.showTextDocument(uri, {
          selection: new vscode.Range(line, 0, line, 0),
          preview: true,
        });
      }
    });

    this.unsubscribe = this.store.subscribe(() => {
      if (!this.panel) return;
      const s = this.store.getSnapshot();
      this.panel.webview.html = this.buildHtml(s.review, s.drift);
    });

    this.panel.onDidDispose(() => {
      this.panel = undefined;
      this.unsubscribe?.();
      this.unsubscribe = undefined;
    });
  }

  restorePanel(panel: vscode.WebviewPanel): void {
    this.panel = panel;
    const state = this.store.getSnapshot();
    panel.webview.html = this.buildHtml(state.review, state.drift);

    panel.webview.onDidReceiveMessage((msg: unknown) => {
      const message = msg as { command: string; path?: string; line?: number };
      if (message.command === "openFile" && message.path) {
        const uri = vscode.Uri.file(message.path);
        const line = Math.max((message.line ?? 1) - 1, 0);
        vscode.window.showTextDocument(uri, {
          selection: new vscode.Range(line, 0, line, 0),
          preview: true,
        });
      }
    });

    this.unsubscribe = this.store.subscribe(() => {
      if (!this.panel) return;
      const s = this.store.getSnapshot();
      this.panel.webview.html = this.buildHtml(s.review, s.drift);
    });

    panel.onDidDispose(() => {
      this.panel = undefined;
      this.unsubscribe?.();
      this.unsubscribe = undefined;
    });
  }

  static get viewType(): string {
    return VIEW_TYPE;
  }

  private buildHtml(review?: ReviewPayload, drift?: DriftPayload): string {
    if (!review && !drift) {
      return wrapPage("Synapse Review", `<p class="empty">Run a review or drift check to see results here.</p>`);
    }

    if (review) {
      return wrapPage(`Synapse Review — ${path.basename(review.target)}`, renderReview(review));
    }

    return wrapPage(`Synapse Drift — ${path.basename(drift!.target)}`, renderDrift(drift!));
  }
}

// --- HTML renderers ---

function renderReview(r: ReviewPayload): string {
  const parts: string[] = [];

  parts.push(renderHeader(r.target, r.drift_status, r.workspace));

  parts.push(`<h2>Drift Findings <span class="badge">${r.drift.length}</span></h2>`);
  if (r.drift.length === 0) {
    parts.push(`<p class="empty">No drift findings.</p>`);
  } else {
    for (const entry of r.drift) {
      parts.push(renderDriftEntry(entry));
    }
  }

  parts.push(`<h2>Context <span class="badge">${r.context.length}</span></h2>`);
  if (r.context.length === 0) {
    parts.push(`<p class="empty">No supporting context was returned.</p>`);
  } else {
    for (const ctx of r.context) {
      parts.push(renderContextEntry(ctx));
    }
  }

  return parts.join("\n");
}

function renderDrift(d: DriftPayload): string {
  const parts: string[] = [];

  parts.push(renderHeader(d.target, d.status, d.workspace));

  parts.push(`<h2>Checks <span class="badge">${d.checks.length}</span></h2>`);
  if (d.checks.length === 0) {
    parts.push(`<p class="empty">No drift results.</p>`);
  } else {
    for (const entry of d.checks) {
      parts.push(renderDriftEntry(entry));
    }
  }

  return parts.join("\n");
}

function renderHeader(target: string, status: string, workspace: string): string {
  return `
    <div class="header-card">
      <div class="header-top">
        <span class="file-name">${esc(path.basename(target))}</span>
        <span class="status-badge ${statusClass(status)}">${esc(titleCase(status))}</span>
      </div>
      <div class="header-meta">
        <span class="meta-label">Path:</span> <span class="meta-value">${esc(target)}</span>
      </div>
      <div class="header-meta">
        <span class="meta-label">Workspace:</span> <span class="meta-value">${esc(workspace)}</span>
      </div>
    </div>`;
}

function renderDriftEntry(entry: DriftCheckEntry): string {
  const lineLink = entry.line_range
    ? `<a class="file-link" href="#" data-path="${escAttr(entry.source_file)}" data-line="${entry.line_range.start}">Lines ${entry.line_range.start}–${entry.line_range.end}</a>`
    : "";

  const findingsHtml =
    entry.findings.length > 0
      ? `<div class="subsection">
          <strong>Findings</strong>
          <table class="findings-table">
            <thead><tr><th>Type</th><th>Summary</th></tr></thead>
            <tbody>${entry.findings.map((f) => `<tr><td class="finding-type">${esc(f.issue_type)}</td><td>${esc(f.summary)}</td></tr>`).join("")}</tbody>
          </table>
        </div>`
      : "";

  const violationsHtml =
    entry.violations.length > 0
      ? `<div class="subsection">
          <strong>Violations</strong>
          <ul class="violations">${entry.violations.map((v) => `<li>${esc(v)}</li>`).join("")}</ul>
        </div>`
      : "";

  const sourcesHtml = renderSources(entry.supporting_sources);

  return `
    <div class="card">
      <div class="card-header">
        <span class="status-icon ${statusClass(entry.status)}">${statusEmoji(entry.status)}</span>
        <span class="card-label">${esc(entry.label)}</span>
        <span class="confidence-badge">${esc(entry.confidence)}</span>
      </div>
      <p class="summary">${esc(entry.summary)}</p>
      ${lineLink ? `<div class="line-info">${lineLink}</div>` : ""}
      ${findingsHtml}
      ${violationsHtml}
      ${sourcesHtml}
    </div>`;
}

function renderContextEntry(ctx: ReviewContextEntry): string {
  const flags: string[] = [];
  if (ctx.has_conflict) flags.push("conflict");
  if (ctx.used_fallback) flags.push("fallback");

  return `
    <details class="card context-card">
      <summary class="card-header">
        <span class="card-label">${esc(ctx.label)}</span>
        ${flags.map((f) => `<span class="flag-badge ${f}">${esc(f)}</span>`).join("")}
      </summary>
      <div class="card-body">
        <div class="subsection">
          <strong>Query</strong>
          <p class="query-text">${esc(ctx.query_text)}</p>
        </div>
        ${renderSources(ctx.sources)}
      </div>
    </details>`;
}

function renderSources(sources: SourceResult[]): string {
  if (sources.length === 0) {
    return `<div class="subsection"><strong>Sources</strong> <span class="muted">None</span></div>`;
  }

  const rows = sources
    .slice(0, 10)
    .map(
      (s) => `
    <details class="source-detail">
      <summary>
        <a class="file-link" href="#" data-path="${escAttr(s.source_file)}" data-line="1">${esc(path.basename(s.source_file))}</a>
        <span class="source-meta">${esc(s.kind)} &middot; ${s.score.toFixed(2)} &middot; ${esc(s.chunk_type)}</span>
      </summary>
      <pre class="source-excerpt">${esc(s.embed_text)}</pre>
    </details>`,
    )
    .join("\n");

  return `<div class="subsection"><strong>Supporting Sources</strong> <span class="badge">${sources.length}</span>${rows}</div>`;
}

// --- Helpers ---

function esc(text: string): string {
  return text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function escAttr(text: string): string {
  return text.replace(/&/g, "&amp;").replace(/"/g, "&quot;").replace(/'/g, "&#39;");
}

function titleCase(value: string): string {
  return value
    .split(/[_\s-]+/)
    .filter(Boolean)
    .map((part) => part[0].toUpperCase() + part.slice(1))
    .join(" ");
}

function statusClass(status: string): string {
  const n = status.toLowerCase();
  if (n.includes("align") || n.includes("ok") || n.includes("pass")) return "status-ok";
  if (n.includes("warn") || n.includes("review")) return "status-warn";
  return "status-error";
}

function statusEmoji(status: string): string {
  const cls = statusClass(status);
  if (cls === "status-ok") return "&#x2714;";
  if (cls === "status-warn") return "&#x26A0;";
  return "&#x2716;";
}

function wrapPage(title: string, body: string): string {
  return `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>${esc(title)}</title>
  <style>
    body {
      font-family: var(--vscode-font-family, sans-serif);
      font-size: var(--vscode-font-size, 13px);
      color: var(--vscode-foreground);
      background: var(--vscode-editor-background);
      padding: 16px 24px;
      margin: 0;
      line-height: 1.5;
    }
    h2 {
      margin: 24px 0 8px;
      font-size: 1.15em;
      border-bottom: 1px solid var(--vscode-panel-border, #444);
      padding-bottom: 4px;
    }
    .badge {
      font-size: 0.85em;
      background: var(--vscode-badge-background);
      color: var(--vscode-badge-foreground);
      padding: 1px 7px;
      border-radius: 10px;
      margin-left: 6px;
      vertical-align: middle;
    }
    .empty {
      color: var(--vscode-disabledForeground, #888);
      font-style: italic;
    }

    /* Header card */
    .header-card {
      background: var(--vscode-editorWidget-background, var(--vscode-sideBar-background));
      border: 1px solid var(--vscode-panel-border, #444);
      border-radius: 6px;
      padding: 14px 18px;
      margin-bottom: 8px;
    }
    .header-top {
      display: flex;
      align-items: center;
      gap: 12px;
      margin-bottom: 8px;
    }
    .file-name {
      font-size: 1.3em;
      font-weight: 600;
    }
    .status-badge {
      padding: 2px 10px;
      border-radius: 12px;
      font-size: 0.85em;
      font-weight: 600;
    }
    .status-badge.status-ok { background: #2ea04370; color: #73d07d; }
    .status-badge.status-warn { background: #d29e2270; color: #e8c766; }
    .status-badge.status-error { background: #f8514970; color: #ff8a8a; }
    .header-meta {
      font-size: 0.9em;
      color: var(--vscode-descriptionForeground, #aaa);
    }
    .meta-label { font-weight: 600; }

    /* Drift/finding cards */
    .card {
      background: var(--vscode-editorWidget-background, var(--vscode-sideBar-background));
      border: 1px solid var(--vscode-panel-border, #444);
      border-radius: 6px;
      padding: 12px 16px;
      margin-bottom: 10px;
    }
    .card-header {
      display: flex;
      align-items: center;
      gap: 8px;
      flex-wrap: wrap;
    }
    .status-icon {
      font-size: 1.1em;
    }
    .status-icon.status-ok { color: #73d07d; }
    .status-icon.status-warn { color: #e8c766; }
    .status-icon.status-error { color: #ff8a8a; }
    .card-label {
      font-weight: 600;
      font-size: 1.05em;
    }
    .confidence-badge {
      font-size: 0.8em;
      background: var(--vscode-badge-background);
      color: var(--vscode-badge-foreground);
      padding: 1px 7px;
      border-radius: 10px;
      margin-left: auto;
    }
    .summary {
      margin: 6px 0;
    }
    .line-info {
      margin: 4px 0 8px;
    }

    /* Findings table */
    .findings-table {
      width: 100%;
      border-collapse: collapse;
      margin-top: 6px;
    }
    .findings-table th, .findings-table td {
      text-align: left;
      padding: 4px 8px;
      border-bottom: 1px solid var(--vscode-panel-border, #333);
    }
    .findings-table th {
      font-weight: 600;
      font-size: 0.9em;
      color: var(--vscode-descriptionForeground, #aaa);
    }
    .finding-type {
      white-space: nowrap;
      font-weight: 500;
      color: var(--vscode-editorWarning-foreground, #e8c766);
    }

    /* Violations */
    .violations {
      margin: 4px 0 0 16px;
      padding: 0;
    }
    .violations li {
      color: var(--vscode-editorError-foreground, #ff8a8a);
      margin-bottom: 2px;
    }

    /* Subsections */
    .subsection {
      margin-top: 10px;
    }
    .muted {
      color: var(--vscode-disabledForeground, #888);
    }

    /* Sources */
    .source-detail {
      margin: 4px 0 4px 8px;
    }
    .source-detail summary {
      cursor: pointer;
      padding: 3px 0;
    }
    .source-meta {
      font-size: 0.85em;
      color: var(--vscode-descriptionForeground, #aaa);
      margin-left: 8px;
    }
    .source-excerpt {
      background: var(--vscode-textCodeBlock-background, #1e1e1e);
      padding: 8px 12px;
      border-radius: 4px;
      font-family: var(--vscode-editor-font-family, monospace);
      font-size: var(--vscode-editor-font-size, 12px);
      white-space: pre-wrap;
      word-break: break-word;
      margin: 4px 0 8px 0;
      max-height: 300px;
      overflow-y: auto;
    }

    /* Links */
    .file-link {
      color: var(--vscode-textLink-foreground);
      text-decoration: none;
      cursor: pointer;
    }
    .file-link:hover {
      text-decoration: underline;
    }

    /* Context cards */
    .context-card summary {
      cursor: pointer;
      list-style: revert;
    }
    .card-body {
      margin-top: 8px;
    }
    .query-text {
      font-style: italic;
      color: var(--vscode-descriptionForeground, #aaa);
    }

    /* Flag badges */
    .flag-badge {
      font-size: 0.78em;
      padding: 1px 6px;
      border-radius: 8px;
      margin-left: 4px;
    }
    .flag-badge.conflict { background: #f8514970; color: #ff8a8a; }
    .flag-badge.fallback { background: #d29e2270; color: #e8c766; }
  </style>
</head>
<body>
  ${body}
  <script>
    (function() {
      const vscode = acquireVsCodeApi();
      document.addEventListener('click', function(e) {
        const link = e.target.closest('.file-link');
        if (link) {
          e.preventDefault();
          vscode.postMessage({
            command: 'openFile',
            path: link.dataset.path,
            line: parseInt(link.dataset.line, 10) || 1
          });
        }
      });
    })();
  </script>
</body>
</html>`;
}
