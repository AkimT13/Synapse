"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.SynapseStateStore = void 0;
class SynapseStateStore {
    state = {};
    listeners = new Set();
    getSnapshot() {
        return this.state;
    }
    subscribe(listener) {
        this.listeners.add(listener);
        return () => this.listeners.delete(listener);
    }
    update(patch) {
        this.state = { ...this.state, ...patch };
        for (const listener of this.listeners) {
            listener(this.state);
        }
    }
    clearError() {
        if (!this.state.lastError) {
            return;
        }
        const { lastError: _lastError, ...next } = this.state;
        this.state = next;
        for (const listener of this.listeners) {
            listener(this.state);
        }
    }
}
exports.SynapseStateStore = SynapseStateStore;
//# sourceMappingURL=store.js.map