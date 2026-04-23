"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.ReviewTreeDataProvider = void 0;
const tree_1 = require("./tree");
class ReviewTreeDataProvider extends tree_1.BaseTreeDataProvider {
    store;
    constructor(store) {
        super();
        this.store = store;
        this.store.subscribe(() => this.refresh());
    }
    async getChildren() {
        const state = this.store.getSnapshot();
        const review = state.review;
        const drift = state.drift;
        if (!review && !drift) {
            return [
                new tree_1.SynapseTreeItem("No review results", {
                    description: "Run Review Current File or Drift Check Current File",
                }),
            ];
        }
        if (review) {
            const items = [
                new tree_1.SynapseTreeItem(review.target, {
                    description: review.drift_status,
                    tooltip: review.workspace,
                }),
            ];
            for (const entry of review.drift) {
                items.push(new tree_1.SynapseTreeItem(entry.label, {
                    description: `${entry.status} | ${entry.confidence}`,
                    tooltip: entry.summary,
                }));
                for (const source of entry.supporting_sources.slice(0, 3)) {
                    items.push(new tree_1.SynapseTreeItem(`  ${source.kind}`, {
                        description: `${source.score.toFixed(2)} | ${source.source_file}`,
                        tooltip: source.embed_text,
                    }));
                }
            }
            return items;
        }
        return [
            new tree_1.SynapseTreeItem(drift.target, {
                description: drift.status,
                tooltip: drift.workspace,
            }),
            ...drift.checks.flatMap((entry) => {
                const sourceItems = entry.supporting_sources.slice(0, 3).map((source) => new tree_1.SynapseTreeItem(`  ${source.kind}`, {
                    description: `${source.score.toFixed(2)} | ${source.source_file}`,
                    tooltip: source.embed_text,
                }));
                return [
                    new tree_1.SynapseTreeItem(entry.label, {
                        description: `${entry.status} | ${entry.confidence}`,
                        tooltip: entry.summary,
                    }),
                    ...sourceItems,
                ];
            }),
        ];
    }
}
exports.ReviewTreeDataProvider = ReviewTreeDataProvider;
//# sourceMappingURL=reviewView.js.map