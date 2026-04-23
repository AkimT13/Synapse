import type {
  DoctorPayload,
  DriftPayload,
  QueryPayload,
  ReviewPayload,
  ServicesStatusPayload,
} from "../types/models";

export interface WorkspaceState {
  workspaceRoot?: string;
  review?: ReviewPayload;
  drift?: DriftPayload;
  query?: QueryPayload;
  doctor?: DoctorPayload;
  services?: ServicesStatusPayload;
  lastError?: string;
}

export type StateListener = (state: WorkspaceState) => void;

export class SynapseStateStore {
  private state: WorkspaceState = {};

  private readonly listeners = new Set<StateListener>();

  getSnapshot(): WorkspaceState {
    return this.state;
  }

  subscribe(listener: StateListener): () => void {
    this.listeners.add(listener);
    return () => this.listeners.delete(listener);
  }

  update(patch: Partial<WorkspaceState>): void {
    this.state = { ...this.state, ...patch };
    for (const listener of this.listeners) {
      listener(this.state);
    }
  }

  clearError(): void {
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
