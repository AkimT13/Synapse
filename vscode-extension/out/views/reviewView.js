"use strict";
var __createBinding = (this && this.__createBinding) || (Object.create ? (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    var desc = Object.getOwnPropertyDescriptor(m, k);
    if (!desc || ("get" in desc ? !m.__esModule : desc.writable || desc.configurable)) {
      desc = { enumerable: true, get: function() { return m[k]; } };
    }
    Object.defineProperty(o, k2, desc);
}) : (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    o[k2] = m[k];
}));
var __setModuleDefault = (this && this.__setModuleDefault) || (Object.create ? (function(o, v) {
    Object.defineProperty(o, "default", { enumerable: true, value: v });
}) : function(o, v) {
    o["default"] = v;
});
var __importStar = (this && this.__importStar) || (function () {
    var ownKeys = function(o) {
        ownKeys = Object.getOwnPropertyNames || function (o) {
            var ar = [];
            for (var k in o) if (Object.prototype.hasOwnProperty.call(o, k)) ar[ar.length] = k;
            return ar;
        };
        return ownKeys(o);
    };
    return function (mod) {
        if (mod && mod.__esModule) return mod;
        var result = {};
        if (mod != null) for (var k = ownKeys(mod), i = 0; i < k.length; i++) if (k[i] !== "default") __createBinding(result, mod, k[i]);
        __setModuleDefault(result, mod);
        return result;
    };
})();
Object.defineProperty(exports, "__esModule", { value: true });
exports.ReviewTreeDataProvider = void 0;
const vscode = __importStar(require("vscode"));
const path = __importStar(require("node:path"));
const tree_1 = require("./tree");
class ReviewTreeDataProvider extends tree_1.BaseTreeDataProvider {
    store;
    constructor(store) {
        super();
        this.store = store;
        this.store.subscribe(() => this.refresh());
    }
    async getRootChildren() {
        const state = this.store.getSnapshot();
        const review = state.review;
        const drift = state.drift;
        if (!review && !drift) {
            return [
                new tree_1.SynapseTreeItem("Review a file", {
                    description: "No results yet",
                    tooltip: [
                        "Use `Synapse: Review Current File` for the full review.",
                        "Use `Synapse: Drift Check Current File` for violations only.",
                    ].join("\n"),
                    iconPath: new vscode.ThemeIcon("search"),
                    collapsibleState: vscode.TreeItemCollapsibleState.Expanded,
                    children: [
                        new tree_1.SynapseTreeItem("Recommended", {
                            description: "Run Review Current File",
                            tooltip: "This gives drift findings plus supporting context.",
                            iconPath: new vscode.ThemeIcon("play"),
                        }),
                    ],
                }),
            ];
        }
        if (review) {
            return buildReviewTree(review);
        }
        return buildDriftTree(drift);
    }
}
exports.ReviewTreeDataProvider = ReviewTreeDataProvider;
function buildReviewTree(review) {
    const driftCount = review.drift.length;
    const contextCount = review.context.length;
    return [
        new tree_1.SynapseTreeItem(path.basename(review.target), {
            description: titleCase(review.drift_status),
            tooltip: `${review.target}\nWorkspace: ${review.workspace}`,
            iconPath: statusIcon(review.drift_status),
            collapsibleState: vscode.TreeItemCollapsibleState.Expanded,
            children: [
                new tree_1.SynapseTreeItem("File", {
                    description: review.target,
                    tooltip: review.target,
                    iconPath: new vscode.ThemeIcon("file"),
                }),
                new tree_1.SynapseTreeItem("Workspace", {
                    description: review.workspace,
                    tooltip: review.workspace,
                    iconPath: new vscode.ThemeIcon("folder"),
                }),
            ],
        }),
        new tree_1.SynapseTreeItem("Drift findings", {
            description: `${driftCount} check${driftCount === 1 ? "" : "s"}`,
            tooltip: driftCount === 0 ? "No drift entries were returned." : undefined,
            iconPath: new vscode.ThemeIcon("warning"),
            collapsibleState: vscode.TreeItemCollapsibleState.Expanded,
            children: driftCount === 0
                ? [
                    new tree_1.SynapseTreeItem("No drift findings", {
                        description: "The review returned no check entries",
                        iconPath: new vscode.ThemeIcon("pass"),
                    }),
                ]
                : review.drift.map(createDriftEntryItem),
        }),
        new tree_1.SynapseTreeItem("Context", {
            description: `${contextCount} retrieval set${contextCount === 1 ? "" : "s"}`,
            tooltip: contextCount === 0 ? "No additional retrieval context was returned." : undefined,
            iconPath: new vscode.ThemeIcon("book"),
            collapsibleState: vscode.TreeItemCollapsibleState.Collapsed,
            children: contextCount === 0
                ? [
                    new tree_1.SynapseTreeItem("No supporting context", {
                        description: "Review completed without extra retrieved context",
                        iconPath: new vscode.ThemeIcon("circle-slash"),
                    }),
                ]
                : review.context.map(createContextItem),
        }),
    ];
}
function buildDriftTree(drift) {
    const checks = drift.checks.length;
    return [
        new tree_1.SynapseTreeItem(path.basename(drift.target), {
            description: titleCase(drift.status),
            tooltip: `${drift.target}\nWorkspace: ${drift.workspace}`,
            iconPath: statusIcon(drift.status),
            collapsibleState: vscode.TreeItemCollapsibleState.Expanded,
            children: [
                new tree_1.SynapseTreeItem("File", {
                    description: drift.target,
                    tooltip: drift.target,
                    iconPath: new vscode.ThemeIcon("file"),
                }),
                new tree_1.SynapseTreeItem("Workspace", {
                    description: drift.workspace,
                    tooltip: drift.workspace,
                    iconPath: new vscode.ThemeIcon("folder"),
                }),
            ],
        }),
        new tree_1.SynapseTreeItem("Checks", {
            description: `${checks} result${checks === 1 ? "" : "s"}`,
            iconPath: new vscode.ThemeIcon("checklist"),
            collapsibleState: vscode.TreeItemCollapsibleState.Expanded,
            children: checks === 0
                ? [
                    new tree_1.SynapseTreeItem("No drift results", {
                        description: "The drift check returned no check entries",
                        iconPath: new vscode.ThemeIcon("pass"),
                    }),
                ]
                : drift.checks.map(createDriftEntryItem),
        }),
    ];
}
function createDriftEntryItem(entry) {
    const details = [
        new tree_1.SynapseTreeItem("Summary", {
            description: summarize(entry.summary),
            tooltip: entry.summary,
            iconPath: new vscode.ThemeIcon("note"),
        }),
    ];
    if (entry.line_range) {
        details.push(new tree_1.SynapseTreeItem("Lines", {
            description: `${entry.line_range.start}-${entry.line_range.end}`,
            tooltip: `${entry.source_file}:${entry.line_range.start}-${entry.line_range.end}`,
            iconPath: new vscode.ThemeIcon("list-ordered"),
        }));
    }
    if (entry.findings.length > 0) {
        details.push(new tree_1.SynapseTreeItem("Findings", {
            description: `${entry.findings.length}`,
            iconPath: new vscode.ThemeIcon("comment-discussion"),
            collapsibleState: vscode.TreeItemCollapsibleState.Collapsed,
            children: entry.findings.map((finding) => new tree_1.SynapseTreeItem(finding.issue_type, {
                description: summarize(finding.summary, 50),
                tooltip: finding.summary,
                iconPath: new vscode.ThemeIcon("warning"),
            })),
        }));
    }
    if (entry.violations.length > 0) {
        details.push(new tree_1.SynapseTreeItem("Violations", {
            description: `${entry.violations.length}`,
            iconPath: new vscode.ThemeIcon("error"),
            collapsibleState: vscode.TreeItemCollapsibleState.Collapsed,
            children: entry.violations.map((violation) => new tree_1.SynapseTreeItem(violation, {
                tooltip: violation,
                iconPath: new vscode.ThemeIcon("circle-large-outline"),
            })),
        }));
    }
    details.push(createSourcesItem(entry.supporting_sources));
    return new tree_1.SynapseTreeItem(entry.label, {
        description: `${titleCase(entry.status)} • ${entry.confidence}`,
        tooltip: entry.source_file,
        iconPath: statusIcon(entry.status),
        collapsibleState: vscode.TreeItemCollapsibleState.Collapsed,
        children: details,
    });
}
function createContextItem(entry) {
    const flags = [
        entry.has_conflict ? "conflict" : undefined,
        entry.used_fallback ? "fallback" : undefined,
    ].filter(Boolean);
    return new tree_1.SynapseTreeItem(entry.label, {
        description: flags.length > 0 ? flags.join(" • ") : "supporting context",
        tooltip: entry.query_text,
        iconPath: new vscode.ThemeIcon(entry.has_conflict ? "warning" : "references"),
        collapsibleState: vscode.TreeItemCollapsibleState.Collapsed,
        children: [
            new tree_1.SynapseTreeItem("Query", {
                description: summarize(entry.query_text, 70),
                tooltip: entry.query_text,
                iconPath: new vscode.ThemeIcon("search"),
            }),
            createSourcesItem(entry.sources),
        ],
    });
}
function createSourcesItem(sources) {
    if (sources.length === 0) {
        return new tree_1.SynapseTreeItem("Sources", {
            description: "None returned",
            iconPath: new vscode.ThemeIcon("circle-slash"),
        });
    }
    return new tree_1.SynapseTreeItem("Sources", {
        description: `${sources.length} match${sources.length === 1 ? "" : "es"}`,
        iconPath: new vscode.ThemeIcon("library"),
        collapsibleState: vscode.TreeItemCollapsibleState.Collapsed,
        children: sources.slice(0, 5).map((source) => new tree_1.SynapseTreeItem(path.basename(source.source_file), {
            description: `${source.kind} • ${source.score.toFixed(2)}`,
            tooltip: `${source.source_file}\n\n${source.embed_text}`,
            iconPath: new vscode.ThemeIcon("file-code"),
            collapsibleState: vscode.TreeItemCollapsibleState.Collapsed,
            children: [
                new tree_1.SynapseTreeItem("Chunk", {
                    description: source.chunk_type,
                    tooltip: source.chunk_type,
                    iconPath: new vscode.ThemeIcon("symbol-string"),
                }),
                new tree_1.SynapseTreeItem("Excerpt", {
                    description: summarize(source.embed_text, 70),
                    tooltip: source.embed_text,
                    iconPath: new vscode.ThemeIcon("note"),
                }),
            ],
        })),
    });
}
function summarize(value, max = 80) {
    return value.length <= max ? value : `${value.slice(0, max - 1)}…`;
}
function titleCase(value) {
    return value
        .split(/[_\s-]+/)
        .filter(Boolean)
        .map((part) => part[0].toUpperCase() + part.slice(1))
        .join(" ");
}
function statusIcon(status) {
    const normalized = status.toLowerCase();
    if (normalized.includes("align") || normalized.includes("ok") || normalized.includes("pass")) {
        return new vscode.ThemeIcon("pass");
    }
    if (normalized.includes("warn") || normalized.includes("review")) {
        return new vscode.ThemeIcon("warning");
    }
    return new vscode.ThemeIcon("error");
}
//# sourceMappingURL=reviewView.js.map