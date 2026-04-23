import type { SynapseStateStore } from "../state/store";
import { BaseTreeDataProvider, SynapseTreeItem } from "./tree";

export class ReviewTreeDataProvider extends BaseTreeDataProvider {
  constructor(private readonly store: SynapseStateStore) {
    super();
    this.store.subscribe(() => this.refresh());
  }

  async getChildren(): Promise<SynapseTreeItem[]> {
    const state = this.store.getSnapshot();
    const review = state.review;
    const drift = state.drift;

    if (!review && !drift) {
      return [
        new SynapseTreeItem("No review results", {
          description: "Run Review Current File or Drift Check Current File",
        }),
      ];
    }

    if (review) {
      const items: SynapseTreeItem[] = [
        new SynapseTreeItem(review.target, {
          description: review.drift_status,
          tooltip: review.workspace,
        }),
      ];
      for (const entry of review.drift) {
        items.push(
          new SynapseTreeItem(entry.label, {
            description: `${entry.status} | ${entry.confidence}`,
            tooltip: entry.summary,
          }),
        );
        for (const source of entry.supporting_sources.slice(0, 3)) {
          items.push(
            new SynapseTreeItem(`  ${source.kind}`, {
              description: `${source.score.toFixed(2)} | ${source.source_file}`,
              tooltip: source.embed_text,
            }),
          );
        }
      }
      return items;
    }

    return [
      new SynapseTreeItem(drift!.target, {
        description: drift!.status,
        tooltip: drift!.workspace,
      }),
      ...drift!.checks.flatMap((entry) => {
        const sourceItems = entry.supporting_sources.slice(0, 3).map(
          (source) =>
            new SynapseTreeItem(`  ${source.kind}`, {
              description: `${source.score.toFixed(2)} | ${source.source_file}`,
              tooltip: source.embed_text,
            }),
        );
        return [
          new SynapseTreeItem(entry.label, {
            description: `${entry.status} | ${entry.confidence}`,
            tooltip: entry.summary,
          }),
          ...sourceItems,
        ];
      }),
    ];
  }
}
