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
exports.QueryTreeDataProvider = void 0;
const path = __importStar(require("node:path"));
const vscode = __importStar(require("vscode"));
const tree_1 = require("./tree");
class QueryTreeDataProvider extends tree_1.BaseTreeDataProvider {
    store;
    constructor(store) {
        super();
        this.store = store;
        this.store.subscribe(() => this.refresh());
    }
    async getRootChildren() {
        const query = this.store.getSnapshot().query;
        if (!query) {
            return [
                new tree_1.SynapseTreeItem("Query with Synapse", {
                    description: "No results yet",
                    tooltip: [
                        "Use `Synapse: Query Selection` to inspect highlighted code.",
                        "Use `Synapse: Query Free Text` for domain questions with citations.",
                    ].join("\n"),
                    iconPath: new vscode.ThemeIcon("comment-discussion"),
                    collapsibleState: vscode.TreeItemCollapsibleState.Expanded,
                    children: [
                        new tree_1.SynapseTreeItem("Recommended", {
                            description: "Run Query Selection or Query Free Text",
                            tooltip: "The query panel fills after a successful query.",
                            iconPath: new vscode.ThemeIcon("play"),
                        }),
                    ],
                }),
            ];
        }
        return buildQueryTree(query);
    }
}
exports.QueryTreeDataProvider = QueryTreeDataProvider;
function buildQueryTree(query) {
    const resultCount = query.results.length;
    const items = [
        new tree_1.SynapseTreeItem(titleCase(query.mode), {
            description: `${resultCount} result${resultCount === 1 ? "" : "s"}`,
            tooltip: query.query,
            iconPath: new vscode.ThemeIcon("search"),
            collapsibleState: vscode.TreeItemCollapsibleState.Expanded,
            children: [
                new tree_1.SynapseTreeItem("Query", {
                    description: summarize(query.query, 80),
                    tooltip: query.query,
                    iconPath: new vscode.ThemeIcon("comment"),
                }),
            ],
        }),
    ];
    if (query.answer) {
        items.push(new tree_1.SynapseTreeItem("Answer", {
            description: summarize(query.answer),
            tooltip: query.answer,
            iconPath: new vscode.ThemeIcon("sparkle"),
        }));
    }
    if (query.explanation) {
        items.push(new tree_1.SynapseTreeItem("Explanation", {
            description: summarize(query.explanation),
            tooltip: query.explanation,
            iconPath: new vscode.ThemeIcon("note"),
        }));
    }
    if (query.has_conflict !== undefined
        || query.is_implemented !== undefined
        || query.used_fallback !== undefined) {
        const facts = [];
        if (query.has_conflict !== undefined) {
            facts.push(new tree_1.SynapseTreeItem("Conflict", {
                description: query.has_conflict ? "Yes" : "No",
                iconPath: new vscode.ThemeIcon(query.has_conflict ? "warning" : "pass"),
            }));
        }
        if (query.is_implemented !== undefined) {
            facts.push(new tree_1.SynapseTreeItem("Implemented", {
                description: query.is_implemented ? "Yes" : "No",
                iconPath: new vscode.ThemeIcon(query.is_implemented ? "pass" : "circle-slash"),
            }));
        }
        if (query.used_fallback !== undefined) {
            facts.push(new tree_1.SynapseTreeItem("Fallback", {
                description: query.used_fallback ? "Used" : "Not used",
                iconPath: new vscode.ThemeIcon("history"),
            }));
        }
        items.push(new tree_1.SynapseTreeItem("Flags", {
            description: `${facts.length}`,
            iconPath: new vscode.ThemeIcon("symbol-boolean"),
            collapsibleState: vscode.TreeItemCollapsibleState.Collapsed,
            children: facts,
        }));
    }
    items.push(createResultsItem(query.results));
    return items;
}
function createResultsItem(results) {
    if (results.length === 0) {
        return new tree_1.SynapseTreeItem("Results", {
            description: "No citations returned",
            iconPath: new vscode.ThemeIcon("circle-slash"),
        });
    }
    return new tree_1.SynapseTreeItem("Results", {
        description: `${results.length} cited match${results.length === 1 ? "" : "es"}`,
        iconPath: new vscode.ThemeIcon("references"),
        collapsibleState: vscode.TreeItemCollapsibleState.Expanded,
        children: results.slice(0, 6).map((result) => new tree_1.SynapseTreeItem(path.basename(result.source_file), {
            description: `${result.kind} • ${result.score.toFixed(2)}`,
            tooltip: `${result.source_file}\n\n${result.embed_text}`,
            iconPath: new vscode.ThemeIcon(result.chunk_type === "code" ? "file-code" : "book"),
            collapsibleState: vscode.TreeItemCollapsibleState.Collapsed,
            children: [
                new tree_1.SynapseTreeItem("Kind", {
                    description: result.chunk_type,
                    tooltip: result.chunk_type,
                    iconPath: new vscode.ThemeIcon("symbol-string"),
                }),
                new tree_1.SynapseTreeItem("Excerpt", {
                    description: summarize(result.embed_text),
                    tooltip: result.embed_text,
                    iconPath: new vscode.ThemeIcon("note"),
                }),
            ],
        })),
    });
}
function summarize(value, max = 90) {
    return value.length <= max ? value : `${value.slice(0, max - 1)}…`;
}
function titleCase(value) {
    return value
        .split(/[_\s-]+/)
        .filter(Boolean)
        .map((part) => part[0].toUpperCase() + part.slice(1))
        .join(" ");
}
//# sourceMappingURL=queryView.js.map