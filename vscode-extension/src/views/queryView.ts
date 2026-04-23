import type { SynapseStateStore } from "../state/store";
import { BaseTreeDataProvider, SynapseTreeItem } from "./tree";

export class QueryTreeDataProvider extends BaseTreeDataProvider {
  constructor(private readonly store: SynapseStateStore) {
    super();
    this.store.subscribe(() => this.refresh());
  }

  async getChildren(): Promise<SynapseTreeItem[]> {
    const query = this.store.getSnapshot().query;
    if (!query) {
      return [
        new SynapseTreeItem("No query results", {
          description: "Run Query Selection or Query Free Text",
        }),
      ];
    }

    const items: SynapseTreeItem[] = [
      new SynapseTreeItem(query.mode, {
        description: query.query,
        tooltip: query.query,
      }),
    ];

    if (query.answer) {
      items.push(
        new SynapseTreeItem("Answer", {
          description: query.answer,
          tooltip: query.answer,
        }),
      );
    }

    if (query.explanation) {
      items.push(
        new SynapseTreeItem("Explanation", {
          description: query.explanation,
          tooltip: query.explanation,
        }),
      );
    }

    for (const result of query.results) {
      items.push(
        new SynapseTreeItem(result.source_file, {
          description: `${result.kind} | ${result.score.toFixed(2)}`,
          tooltip: result.embed_text,
        }),
      );
    }

    return items;
  }
}
