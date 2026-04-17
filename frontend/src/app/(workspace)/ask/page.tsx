"use client";

import {
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { ChatStagePane } from "@/components/chat/ChatStagePane";
import { ConversationListPane } from "@/components/chat/ConversationListPane";
import {
  SourcesPane,
  type SourcesPaneHandle,
} from "@/components/chat/SourcesPane";
import {
  chat,
  workspace,
  type ChatMessage,
  type ConversationDetail,
  type ConversationHeader,
} from "@/lib/api";
import { useChat } from "@/lib/stores";

// A stable placeholder ID for the optimistic assistant loading bubble.
const PENDING_ID = "__pending_assistant__";

export default function AskPage() {
  const queryClient = useQueryClient();
  const { activeConversation, scope, setActive } = useChat();
  const sourcesRef = useRef<SourcesPaneHandle>(null);

  const [draft, setDraft] = useState("");
  // Which assistant message the sources panel reflects. Defaults to the
  // most recent assistant turn; the user can click a previous bubble to
  // pin it to that turn instead.
  const [focusedAssistantId, setFocusedAssistantId] = useState<string | null>(null);
  const [pendingAssistant, setPendingAssistant] = useState<ChatMessage | null>(null);

  // --- conversation list ---------------------------------------------------
  const conversationsQuery = useQuery({
    queryKey: ["chat", "list"],
    queryFn: chat.list,
  });

  const conversations = useMemo(
    () => conversationsQuery.data ?? [],
    [conversationsQuery.data],
  );

  // Default-select the newest conversation on first load if nothing is
  // active yet. This keeps the sources panel from looking empty forever.
  useEffect(() => {
    if (!activeConversation && conversations.length > 0) {
      setActive(conversations[0]);
    }
  }, [conversations, activeConversation, setActive]);

  // --- active conversation detail -----------------------------------------
  const detailQuery = useQuery({
    queryKey: ["chat", "detail", activeConversation?.id],
    queryFn: () => chat.get(activeConversation!.id),
    enabled: !!activeConversation,
  });

  const messages: ChatMessage[] = useMemo(
    () => detailQuery.data?.messages ?? [],
    [detailQuery.data],
  );

  // Track the latest assistant automatically unless the user has pinned
  // a different one (by clicking an older bubble or citation).
  useEffect(() => {
    const lastAssistant = [...messages].reverse().find((m) => m.role === "assistant");
    if (lastAssistant) {
      setFocusedAssistantId((current) =>
        messages.some((m) => m.id === current) ? current : lastAssistant.id,
      );
    } else {
      setFocusedAssistantId(null);
    }
  }, [messages]);

  // --- workspace stats (for sources footer) -------------------------------
  const statsQuery = useQuery({
    queryKey: ["workspace", "stats"],
    queryFn: workspace.stats,
  });

  // --- mutations -----------------------------------------------------------
  const createMutation = useMutation({
    mutationFn: (title?: string) => chat.create(title),
    onSuccess: (created) => {
      queryClient.setQueryData<ConversationHeader[]>(
        ["chat", "list"],
        (prev) => [created, ...(prev ?? [])],
      );
      setActive(created);
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => chat.remove(id),
    onSuccess: (_, id) => {
      queryClient.setQueryData<ConversationHeader[]>(
        ["chat", "list"],
        (prev) => (prev ?? []).filter((c) => c.id !== id),
      );
      queryClient.removeQueries({ queryKey: ["chat", "detail", id] });
      if (activeConversation?.id === id) {
        setActive(null);
      }
    },
  });

  const postMutation = useMutation({
    mutationFn: async (params: { conversationId: string; content: string }) =>
      chat.postMessage(params.conversationId, {
        content: params.content,
        scope,
      }),
  });

  // --- submit flow ---------------------------------------------------------
  const handleSubmit = useCallback(async () => {
    const text = draft.trim();
    if (!text || postMutation.isPending) return;

    // Ensure we have a conversation to post into.
    let conversation = activeConversation;
    if (!conversation) {
      try {
        conversation = await createMutation.mutateAsync(
          text.slice(0, 60) || undefined,
        );
      } catch {
        return;
      }
    }

    // Append the user's message optimistically into the detail cache, and
    // show a loading placeholder bubble for the assistant response.
    const timestamp = new Date().toISOString();
    const optimisticUser: ChatMessage = {
      id: `__optimistic_${Date.now()}`,
      conversation_id: conversation.id,
      role: "user",
      content: text,
      sources: [],
      created_at: timestamp,
    };
    const pending: ChatMessage = {
      id: PENDING_ID,
      conversation_id: conversation.id,
      role: "assistant",
      content: "",
      sources: [],
      created_at: timestamp,
    };

    queryClient.setQueryData<ConversationDetail | undefined>(
      ["chat", "detail", conversation.id],
      (prev) =>
        prev
          ? { ...prev, messages: [...prev.messages, optimisticUser] }
          : prev,
    );
    setPendingAssistant(pending);
    setDraft("");

    try {
      const response = await postMutation.mutateAsync({
        conversationId: conversation.id,
        content: text,
      });

      queryClient.setQueryData<ConversationDetail | undefined>(
        ["chat", "detail", conversation.id],
        (prev) => {
          if (!prev) return prev;
          // Swap our optimistic user bubble for the server's canonical
          // one, then append the assistant reply.
          const withoutOptimistic = prev.messages.filter(
            (m) => m.id !== optimisticUser.id,
          );
          return {
            ...prev,
            updated_at: new Date().toISOString(),
            messages: [
              ...withoutOptimistic,
              response.user_message,
              response.assistant_message,
            ],
          };
        },
      );
      // Bump this conversation to the top of the sidebar list.
      queryClient.setQueryData<ConversationHeader[]>(
        ["chat", "list"],
        (prev) => {
          if (!prev) return prev;
          const updated = prev.find((c) => c.id === conversation!.id);
          if (!updated) return prev;
          const rest = prev.filter((c) => c.id !== conversation!.id);
          return [
            { ...updated, updated_at: new Date().toISOString() },
            ...rest,
          ];
        },
      );
      setFocusedAssistantId(response.assistant_message.id);
    } catch {
      // Roll back the optimistic user bubble on failure.
      queryClient.setQueryData<ConversationDetail | undefined>(
        ["chat", "detail", conversation.id],
        (prev) =>
          prev
            ? {
                ...prev,
                messages: prev.messages.filter((m) => m.id !== optimisticUser.id),
              }
            : prev,
      );
    } finally {
      setPendingAssistant(null);
    }
  }, [
    activeConversation,
    createMutation,
    draft,
    postMutation,
    queryClient,
  ]);

  // --- derived: sources for the focused assistant turn --------------------
  // Only surface the sources the assistant actually cited in its prose.
  // The LLM is prompted to emit [N] markers where N indexes the retrieved
  // results; anything retrieved but not referenced stays hidden so the
  // panel count matches the badges in the text.
  const focusedSources = useMemo(() => {
    const focused = messages.find(
      (m) => m.role === "assistant" && m.id === focusedAssistantId,
    );
    if (!focused) return [];
    const citedIndices = new Set(
      Array.from(focused.content.matchAll(/\[(\d+)\]/g)).map((match) =>
        parseInt(match[1], 10),
      ),
    );
    if (citedIndices.size === 0) return [];
    return focused.sources.filter((source) => citedIndices.has(source.index));
  }, [messages, focusedAssistantId]);

  // --- handlers ------------------------------------------------------------
  const handleCreate = useCallback(() => {
    if (createMutation.isPending) return;
    createMutation.mutate(undefined);
  }, [createMutation]);

  const handleDelete = useCallback(
    (conversation: ConversationHeader) => {
      deleteMutation.mutate(conversation.id);
    },
    [deleteMutation],
  );

  const handleSelect = useCallback(
    (conversation: ConversationHeader) => setActive(conversation),
    [setActive],
  );

  const handleFocusAssistant = useCallback((message: ChatMessage) => {
    setFocusedAssistantId(message.id);
  }, []);

  const handleCitationClick = useCallback(
    (message: ChatMessage, n: number) => {
      setFocusedAssistantId(message.id);
      // Wait a tick so the sources panel has re-rendered with this
      // message's sources before we try to flash the target card.
      window.setTimeout(() => sourcesRef.current?.flash(n), 0);
    },
    [],
  );

  const emptyState = (
    <div className="ask-empty">
      <h3>Ask your first question</h3>
      <p>
        Questions can span your ingested code and your reference docs.
        Try &quot;where is the pitch command clamped?&quot;
      </p>
    </div>
  );

  return (
    <div className="ask-cols">
      <ConversationListPane
        conversations={conversations}
        activeId={activeConversation?.id ?? null}
        onSelect={handleSelect}
        onCreate={handleCreate}
        onDelete={handleDelete}
        creating={createMutation.isPending}
      />
      <ChatStagePane
        messages={messages}
        focusedAssistantId={focusedAssistantId}
        pendingAssistant={pendingAssistant}
        draft={draft}
        onDraftChange={setDraft}
        onSubmit={handleSubmit}
        onFocusAssistant={handleFocusAssistant}
        onCitationClick={handleCitationClick}
        sending={postMutation.isPending}
        emptyState={emptyState}
      />
      <SourcesPane
        ref={sourcesRef}
        sources={focusedSources}
        stats={statsQuery.data}
      />
    </div>
  );
}
