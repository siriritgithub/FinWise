import { useState, useRef, useEffect } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Send, Bot, User, Sparkles, Wifi, WifiOff, Plus, Trash2, MessageSquare } from "lucide-react";
import api from "../lib/api";
import type { ChatResponse } from "../types";

interface Message {
  role: "user" | "assistant";
  text: string;
}

interface OllamaStatus {
  ollama_enabled: boolean;
  ollama_online: boolean;
  model: string;
}

interface Conversation {
  id: number;
  title: string | null;
  updated_at: string;
  last_message: string | null;
}

interface ConversationMessage {
  id: number;
  role: "user" | "assistant";
  content: string;
  created_at: string;
}

const MUTATION_QUERY_KEYS: Record<string, string[][]> = {
  transactions: [["transactions"], ["recentTransactions"], ["dashboardSummary"]],
  accounts: [["accounts"], ["dashboardSummary"], ["netWorth"]],
  budgets: [["budgets"], ["budgetSummary"], ["dashboardSummary"]],
  goals: [["goals"], ["dashboardSummary"]],
};

function cleanText(text: string): string {
  return text
    .replace(/\*\*(.+?)\*\*/gs, "$1")
    .replace(/\*(.+?)\*/g, "$1")
    .replace(/#{1,6}\s*/g, "")
    .replace(/```[\s\S]*?```/g, "")
    .replace(/`([^`]+)`/g, "$1")
    .replace(/\bINR\s*/g, "₹")
    .replace(/\bRs\.?\s*/g, "₹")
    .replace(/\n{3,}/g, "\n\n")
    .trim();
}

function timeAgo(dateStr: string): string {
  const normalized = /(?:Z|[+-]\d{2}:\d{2})$/.test(dateStr)
    ? dateStr
    : `${dateStr}Z`;

  const timestamp = new Date(normalized).getTime();
  if (Number.isNaN(timestamp)) return "";

  const diff = Math.max(0, Date.now() - timestamp);
  const mins = Math.floor(diff / 60000);

  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;

  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;

  return `${Math.floor(hrs / 24)}d ago`;
}

const WELCOME: Message = {
  role: "assistant",
  text: "Hi! I'm FinWise AI. Ask me naturally about your finances — balances, spending, goals, budgets, forecasts, or general finance questions. I'll use your verified FinWise data to answer.",
};

const SUGGESTIONS = [
  "What's my net worth?",
  "How's my emergency fund?",
  "Compare this month vs last month",
  "Show my monthly report",
  "What are my top spending categories?",
  "Recommend budgets for me",
  "What's my financial health score?",
  "Show my savings goals",
];

export function Chat() {
  const queryClient = useQueryClient();
  const [messages, setMessages] = useState<Message[]>([WELCOME]);
  const [input, setInput] = useState("");
  const [conversationId, setConversationId] = useState<number | null>(null);
  const [deletingId, setDeletingId] = useState<number | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);
  const hasInteracted = messages.length > 1;

  // ── Status ────────────────────────────────────────────────────────────────
  const { data: ollamaStatus } = useQuery<OllamaStatus>({
    queryKey: ["ollamaStatus"],
    queryFn: () => api.get<OllamaStatus>("/chat/status").then((r) => r.data),
    refetchInterval: 30_000,
    retry: false,
  });

  // ── Conversation list ─────────────────────────────────────────────────────
  const { data: conversations = [] } = useQuery<Conversation[]>({
    queryKey: ["conversations"],
    queryFn: () => api.get<Conversation[]>("/chat/conversations").then((r) => r.data),
    refetchInterval: 0,
    retry: false,
  });

  // ── Load a conversation ───────────────────────────────────────────────────
  const loadConversation = async (id: number) => {
    if (id === conversationId) return;
    try {
      const { data } = await api.get<ConversationMessage[]>(`/chat/conversations/${id}/messages`);
      setConversationId(id);
      if (data.length === 0) {
        setMessages([WELCOME]);
      } else {
        setMessages(data.map((m) => ({ role: m.role, text: cleanText(m.content) })));
      }
    } catch {
      // ignore
    }
  };

  // ── New chat ──────────────────────────────────────────────────────────────
  const startNewChat = () => {
    setConversationId(null);
    setMessages([WELCOME]);
    setInput("");
  };

  // ── Delete conversation ───────────────────────────────────────────────────
  const deleteConversation = async (id: number) => {
    if (!window.confirm("Delete this conversation?")) return;
    setDeletingId(id);
    try {
      await api.delete(`/chat/conversations/${id}`);
      queryClient.invalidateQueries({ queryKey: ["conversations"] });
      if (conversationId === id) startNewChat();
    } finally {
      setDeletingId(null);
    }
  };

  // ── Send message ──────────────────────────────────────────────────────────
  const mutation = useMutation({
    mutationFn: (payload: { message: string; conversation_id: number | null }) =>
      api.post<ChatResponse & { mutations?: string[]; conversation_id?: number }>(
        "/chat",
        payload
      ).then((r) => r.data),

    onSuccess: (data) => {
      const text = cleanText(data.answer_text || data.response || "");
      setMessages((prev) => [...prev, { role: "assistant", text }]);

      if (data.conversation_id && data.conversation_id !== conversationId) {
      setConversationId(data.conversation_id);
     }
     queryClient.invalidateQueries({ queryKey: ["conversations"] });

      const mutated: string[] = data.mutations || [];
      const keysToInvalidate = new Set<string>();
      mutated.forEach((m) => {
        (MUTATION_QUERY_KEYS[m] || []).forEach((k) => keysToInvalidate.add(k.join(".")));
      });
      keysToInvalidate.forEach((k) => {
        queryClient.invalidateQueries({ queryKey: k.split(".") });
      });
      if (mutated.length > 0) {
        queryClient.invalidateQueries({ queryKey: ["dashboardSummary"] });
        queryClient.invalidateQueries({ queryKey: ["healthScore"] });
        queryClient.invalidateQueries({ queryKey: ["forecast"] });
        queryClient.invalidateQueries({ queryKey: ["anomalies"] });
        queryClient.invalidateQueries({ queryKey: ["spendingTrends"] });
        queryClient.invalidateQueries({ queryKey: ["netWorth"] });
      }
    },

    onError: (error: unknown) => {
      const detail =
        (error as { response?: { data?: { detail?: string } } })?.response?.data?.detail ||
        "I couldn't reach the AI service. Make sure the FinWise backend is running.";
      setMessages((prev) => [...prev, { role: "assistant", text: detail }]);
    },
  });

  const send = () => {
    const text = input.trim();
    if (!text || mutation.isPending) return;
    setMessages((prev) => [...prev, { role: "user", text }]);
    mutation.mutate({ message: text, conversation_id: conversationId });
    setInput("");
  };

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, mutation.isPending]);

  const isOnline = ollamaStatus?.ollama_online ?? null;

  return (
    <div className="flex h-[calc(100vh-6rem)] min-h-[520px] gap-4">

      {/* ── Conversation sidebar ─────────────────────────────────────────── */}
      <div className="w-64 flex-shrink-0 flex flex-col gap-2">
        <button
          onClick={startNewChat}
          className="flex items-center gap-2 w-full px-3 py-2.5 rounded-xl border border-white/10 bg-white/5 hover:bg-white/10 text-sm text-white transition-colors"
        >
          <Plus size={15} />
          New Chat
        </button>

        <div className="dark-card flex-1 min-h-0 overflow-y-auto p-2 space-y-1">
          {conversations.length === 0 && (
            <p className="text-xs text-slate-500 px-2 py-3 text-center">No conversations yet</p>
          )}
          {conversations.map((c) => (
            <div
              key={c.id}
              onClick={() => loadConversation(c.id)}
              className={`group flex items-start gap-2 px-2.5 py-2 rounded-lg cursor-pointer transition-colors ${
                c.id === conversationId
                  ? "bg-blue-600/20 border border-blue-500/30"
                  : "hover:bg-white/5 border border-transparent"
              }`}
            >
              <MessageSquare size={13} className="text-slate-400 mt-0.5 flex-shrink-0" />
              <div className="flex-1 min-w-0">
                <p className="text-xs text-slate-200 truncate leading-snug">
                  {c.title || "New conversation"}
                </p>
                <p className="text-[10px] text-slate-500 mt-0.5">{timeAgo(c.updated_at)}</p>
              </div>
              <button
                onClick={(e) => { e.stopPropagation(); deleteConversation(c.id); }}
                disabled={deletingId === c.id}
                className="opacity-0 group-hover:opacity-100 p-0.5 rounded text-slate-500 hover:text-red-400 transition-all flex-shrink-0"
              >
                <Trash2 size={12} />
              </button>
            </div>
          ))}
        </div>
      </div>

      {/* ── Main chat area ───────────────────────────────────────────────── */}
      <div className="flex flex-col flex-1 min-w-0">
        {/* Header */}
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-3">
            <div className="icon-box">
              <Sparkles size={18} />
            </div>
            <h1 className="text-2xl font-bold text-white">AI Finance Assistant</h1>
          </div>

          <div className="flex items-center gap-2 text-xs px-3 py-1.5 rounded-full border border-white/10 bg-white/5">
            {isOnline === null ? (
              <span className="text-slate-400">Checking AI...</span>
            ) : isOnline ? (
              <>
                <Wifi size={13} className="text-emerald-400" />
                <span className="text-emerald-400">{ollamaStatus?.model ?? "AI"} connected</span>
              </>
            ) : (
              <>
                <WifiOff size={13} className="text-red-400" />
                <span className="text-red-400">AI offline</span>
              </>
            )}
          </div>
        </div>

        {/* Quick suggestions */}
        {!hasInteracted && (
          <div className="flex flex-wrap gap-2 mb-3">
            {SUGGESTIONS.map((s) => (
              <button
                key={s}
                onClick={() => setInput(s)}
                className="text-xs px-3 py-1.5 rounded-full border border-white/10 bg-white/5 text-slate-300 hover:bg-white/10 hover:text-white transition-colors"
              >
                {s}
              </button>
            ))}
          </div>
        )}

        {/* Messages */}
        <div className="dark-card flex-1 min-h-0 overflow-y-auto mb-4 space-y-5 p-5 lg:p-6">
          {messages.map((m, i) => (
            <div
              key={`${m.role}-${i}`}
              className={`flex gap-3 ${m.role === "user" ? "justify-end" : "justify-start"}`}
            >
              {m.role === "assistant" && (
                <div className="w-9 h-9 rounded-full bg-blue-500/10 border border-blue-400/15 flex items-center justify-center flex-shrink-0 mt-0.5">
                  <Bot size={17} className="text-cyan-300" />
                </div>
              )}
              <div
                className={
                  m.role === "user"
                    ? "max-w-[78%] lg:max-w-2xl rounded-2xl rounded-br-md px-4 py-3 text-sm whitespace-pre-wrap bg-gradient-to-r from-blue-600 to-blue-500 text-white shadow-lg shadow-blue-950/20"
                    : "max-w-[82%] lg:max-w-2xl rounded-2xl rounded-bl-md px-4 py-3.5 text-sm leading-6 whitespace-pre-wrap bg-[#172338] text-slate-100 border border-white/10 shadow-lg shadow-black/10"
                }
              >
                {m.text}
              </div>
              {m.role === "user" && (
                <div className="w-9 h-9 rounded-full bg-slate-700/70 border border-white/10 flex items-center justify-center flex-shrink-0 mt-0.5">
                  <User size={17} className="text-slate-300" />
                </div>
              )}
            </div>
          ))}

          {mutation.isPending && (
            <div className="flex gap-3">
              <div className="w-9 h-9 rounded-full bg-blue-500/10 border border-blue-400/15 flex items-center justify-center">
                <Bot size={17} className="text-cyan-300" />
              </div>
              <div className="bg-[#172338] border border-white/10 rounded-2xl rounded-bl-md px-4 py-3 text-sm text-slate-400">
                <span className="inline-flex items-center gap-2">
                  <span className="h-2 w-2 rounded-full bg-cyan-400 animate-pulse" />
                  FinWise AI is thinking...
                </span>
              </div>
            </div>
          )}
          <div ref={bottomRef} />
        </div>

        {/* Input */}
        <div className="flex gap-3">
          <input
            className="dark-input flex-1 h-12"
            placeholder="Ask about your finances..."
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && send()}
            disabled={mutation.isPending}
          />
          <button
            onClick={send}
            disabled={mutation.isPending || !input.trim()}
            className="dark-primary h-12 w-12 p-0 rounded-xl"
          >
            <Send size={18} />
          </button>
        </div>
      </div>
    </div>
  );
}
