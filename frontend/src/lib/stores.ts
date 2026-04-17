/**
 * Client-side stores. Intentionally minimal — persistent data lives on
 * the server (Actian, SQLite, filesystem); these stores only hold UI
 * state that needs to survive navigation: active selection, active
 * conversation, and last-known ingest status.
 */
"use client";

import { create } from "zustand";

import type { ConversationHeader } from "@/lib/api";

// ----- code selection ------------------------------------------------------

export interface CodeSelection {
  file: string;
  text: string;
  // Inclusive line numbers of the selection, 1-based.
  startLine: number;
  endLine: number;
}

interface CodeSelectionState {
  selection: CodeSelection | null;
  setSelection: (selection: CodeSelection | null) => void;
}

export const useCodeSelection = create<CodeSelectionState>((set) => ({
  selection: null,
  setSelection: (selection) => set({ selection }),
}));

// ----- knowledge selection -------------------------------------------------

export interface KnowledgeSelection {
  file: string;
  text: string;
}

interface KnowledgeSelectionState {
  selection: KnowledgeSelection | null;
  setSelection: (selection: KnowledgeSelection | null) => void;
}

export const useKnowledgeSelection = create<KnowledgeSelectionState>((set) => ({
  selection: null,
  setSelection: (selection) => set({ selection }),
}));

// ----- chat ---------------------------------------------------------------

type ChatScope = "all" | "code" | "knowledge";

interface ChatState {
  activeConversation: ConversationHeader | null;
  scope: ChatScope;
  setActive: (conversation: ConversationHeader | null) => void;
  setScope: (scope: ChatScope) => void;
}

export const useChat = create<ChatState>((set) => ({
  activeConversation: null,
  scope: "all",
  setActive: (conversation) => set({ activeConversation: conversation }),
  setScope: (scope) => set({ scope }),
}));
