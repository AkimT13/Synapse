import * as path from "node:path";
import * as vscode from "vscode";

import type { QueryPayload, SourceResult } from "../types/models";
import type { SynapseStateStore } from "../state/store";
import { BaseTreeDataProvider, SynapseTreeItem } from "./tree";

export class QueryTreeDataProvider extends BaseTreeDataProvider {
  constructor(private readonly store: SynapseStateStore) {
    super();
    this.store.subscribe(() => this.refresh());
  }

  protected async getRootChildren(): Promise<SynapseTreeItem[]> {
    const query = this.store.getSnapshot().query;
    if (!query) {
      return [
        new SynapseTreeItem("Query with Synapse", {
          description: "No results yet",
          tooltip: [
            "Use `Synapse: Query Selection` to inspect highlighted code.",
            "Use `Synapse: Query Free Text` for domain questions with citations.",
          ].join("\n"),
          iconPath: new vscode.ThemeIcon("comment-discussion"),
          collapsibleState: vscode.TreeItemCollapsibleState.Expanded,
          children: [
            new SynapseTreeItem("Recommended", {
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

function buildQueryTree(query: QueryPayload): SynapseTreeItem[] {
  const resultCount = query.results.length;
  const items: SynapseTreeItem[] = [
    new SynapseTreeItem(titleCase(query.mode), {
      description: `${resultCount} result${resultCount === 1 ? "" : "s"}`,
      tooltip: query.query,
      iconPath: new vscode.ThemeIcon("search"),
      collapsibleState: vscode.TreeItemCollapsibleState.Expanded,
      children: [
        new SynapseTreeItem("Query", {
          description: summarize(query.query, 80),
          tooltip: query.query,
          iconPath: new vscode.ThemeIcon("comment"),
        }),
      ],
    }),
  ];

  if (query.answer) {
    items.push(
      new SynapseTreeItem("Answer", {
        description: summarize(query.answer),
        tooltip: query.answer,
        iconPath: new vscode.ThemeIcon("sparkle"),
      }),
    );
  }

  if (query.explanation) {
    items.push(
      new SynapseTreeItem("Explanation", {
        description: summarize(query.explanation),
        tooltip: query.explanation,
        iconPath: new vscode.ThemeIcon("note"),
      }),
    );
  }

  if (
    query.has_conflict !== undefined
    || query.is_implemented !== undefined
    || query.used_fallback !== undefined
  ) {
    const facts: SynapseTreeItem[] = [];
    if (query.has_conflict !== undefined) {
      facts.push(
        new SynapseTreeItem("Conflict", {
          description: query.has_conflict ? "Yes" : "No",
          iconPath: new vscode.ThemeIcon(query.has_conflict ? "warning" : "pass"),
        }),
      );
    }
    if (query.is_implemented !== undefined) {
      facts.push(
        new SynapseTreeItem("Implemented", {
          description: query.is_implemented ? "Yes" : "No",
          iconPath: new vscode.ThemeIcon(query.is_implemented ? "pass" : "circle-slash"),
        }),
      );
    }
    if (query.used_fallback !== undefined) {
      facts.push(
        new SynapseTreeItem("Fallback", {
          description: query.used_fallback ? "Used" : "Not used",
          iconPath: new vscode.ThemeIcon("history"),
        }),
      );
    }
    items.push(
      new SynapseTreeItem("Flags", {
        description: `${facts.length}`,
        iconPath: new vscode.ThemeIcon("symbol-boolean"),
        collapsibleState: vscode.TreeItemCollapsibleState.Collapsed,
        children: facts,
      }),
    );
  }

  items.push(createResultsItem(query.results));
  return items;
}

function createResultsItem(results: SourceResult[]): SynapseTreeItem {
  if (results.length === 0) {
    return new SynapseTreeItem("Results", {
      description: "No citations returned",
      iconPath: new vscode.ThemeIcon("circle-slash"),
    });
  }

  return new SynapseTreeItem("Results", {
    description: `${results.length} cited match${results.length === 1 ? "" : "es"}`,
    iconPath: new vscode.ThemeIcon("references"),
    collapsibleState: vscode.TreeItemCollapsibleState.Expanded,
    children: results.slice(0, 6).map((result) =>
      new SynapseTreeItem(path.basename(result.source_file), {
        description: `${result.kind} • ${result.score.toFixed(2)}`,
        tooltip: `${result.source_file}\n\n${result.embed_text}`,
        iconPath: new vscode.ThemeIcon(result.chunk_type === "code" ? "file-code" : "book"),
        collapsibleState: vscode.TreeItemCollapsibleState.Collapsed,
        children: [
          new SynapseTreeItem("Kind", {
            description: result.chunk_type,
            tooltip: result.chunk_type,
            iconPath: new vscode.ThemeIcon("symbol-string"),
          }),
          new SynapseTreeItem("Excerpt", {
            description: summarize(result.embed_text),
            tooltip: result.embed_text,
            iconPath: new vscode.ThemeIcon("note"),
          }),
        ],
      }),
    ),
  });
}

function summarize(value: string, max = 90): string {
  return value.length <= max ? value : `${value.slice(0, max - 1)}…`;
}

function titleCase(value: string): string {
  return value
    .split(/[_\s-]+/)
    .filter(Boolean)
    .map((part) => part[0].toUpperCase() + part.slice(1))
    .join(" ");
}
