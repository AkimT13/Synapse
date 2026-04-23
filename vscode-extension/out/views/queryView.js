"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.QueryTreeDataProvider = void 0;
const tree_1 = require("./tree");
class QueryTreeDataProvider extends tree_1.BaseTreeDataProvider {
    store;
    constructor(store) {
        super();
        this.store = store;
        this.store.subscribe(() => this.refresh());
    }
    async getChildren() {
        const query = this.store.getSnapshot().query;
        if (!query) {
            return [
                new tree_1.SynapseTreeItem("No query results", {
                    description: "Run Query Selection or Query Free Text",
                }),
            ];
        }
        const items = [
            new tree_1.SynapseTreeItem(query.mode, {
                description: query.query,
                tooltip: query.query,
            }),
        ];
        if (query.answer) {
            items.push(new tree_1.SynapseTreeItem("Answer", {
                description: query.answer,
                tooltip: query.answer,
            }));
        }
        if (query.explanation) {
            items.push(new tree_1.SynapseTreeItem("Explanation", {
                description: query.explanation,
                tooltip: query.explanation,
            }));
        }
        for (const result of query.results) {
            items.push(new tree_1.SynapseTreeItem(result.source_file, {
                description: `${result.kind} | ${result.score.toFixed(2)}`,
                tooltip: result.embed_text,
            }));
        }
        return items;
    }
}
exports.QueryTreeDataProvider = QueryTreeDataProvider;
//# sourceMappingURL=queryView.js.map