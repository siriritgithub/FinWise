import { useState, useRef, useEffect } from "react";
import { useMutation } from "@tanstack/react-query";
import { Send, Bot, User, Sparkles } from "lucide-react";
import api from "../lib/api";
import type { ChatResponse } from "../types";

interface Message {
  role: "user" | "assistant";
  text: string;
}

export function Chat() {
  const [messages, setMessages] = useState<Message[]>([
    {
      role: "assistant",
      text: "Hi! I'm FinWise AI. Ask me naturally about your money, planning, forecasts, goals, budgets — or general finance questions. I'll use your verified FinWise data whenever the question needs it.",
    },
  ]);
  const [input, setInput] = useState("");
  const bottomRef = useRef<HTMLDivElement>(null);

  const mutation = useMutation({
    mutationFn: (payload: { message: string; history: { role: "user" | "assistant"; content: string }[] }) =>
      api.post<ChatResponse>("/chat", payload).then((r) => r.data),
    onSuccess: (data) => {
      setMessages((prev) => [...prev, { role: "assistant", text: data.answer_text }]);
    },
    onError: (error: any) => {
      const detail = error?.response?.data?.detail || "I couldn't reach the AI service. Make sure the FinWise backend and Ollama are running.";
      setMessages((prev) => [...prev, { role: "assistant", text: detail }]);
    },
  });

  const send = () => {
    const text = input.trim();
    if (!text || mutation.isPending) return;
    const history = messages.slice(-12).map((m) => ({ role: m.role, content: m.text }));
    setMessages((prev) => [...prev, { role: "user", text }]);
    mutation.mutate({ message: text, history });
    setInput("");
  };

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, mutation.isPending]);

  return (
    <div className="flex flex-col h-[calc(100vh-6rem)] min-h-[520px]">
      <div className="flex items-center gap-3 mb-4">
        <div className="icon-box"><Sparkles size={18} /></div>
        <div>
          <h1 className="text-2xl font-bold text-white">AI Finance Assistant</h1>
        </div>
      </div>

      <div className="dark-card flex-1 min-h-0 overflow-y-auto mb-4 space-y-5 p-5 lg:p-6">
        {messages.map((m, i) => (
          <div key={`${m.role}-${i}`} className={`flex gap-3 ${m.role === "user" ? "justify-end" : "justify-start"}`}>
            {m.role === "assistant" && (
              <div className="w-9 h-9 rounded-full bg-blue-500/10 border border-blue-400/15 flex items-center justify-center flex-shrink-0 mt-0.5">
                <Bot size={17} className="text-cyan-300" />
              </div>
            )}
            <div className={m.role === "user"
              ? "max-w-[78%] lg:max-w-2xl rounded-2xl rounded-br-md px-4 py-3 text-sm whitespace-pre-wrap bg-gradient-to-r from-blue-600 to-blue-500 text-white shadow-lg shadow-blue-950/20"
              : "max-w-[82%] lg:max-w-2xl rounded-2xl rounded-bl-md px-4 py-3.5 text-sm leading-6 whitespace-pre-wrap bg-[#172338] text-slate-100 border border-white/10 shadow-lg shadow-black/10"
            }>
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
              <span className="inline-flex items-center gap-2"><span className="h-2 w-2 rounded-full bg-cyan-400 animate-pulse" /> FinWise AI is thinking...</span>
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      <div className="flex gap-3">
        <input
          className="dark-input flex-1 h-12"
          placeholder="Ask about your finances..."
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && send()}
          disabled={mutation.isPending}
        />
        <button onClick={send} disabled={mutation.isPending || !input.trim()} className="dark-primary h-12 w-12 p-0 rounded-xl">
          <Send size={18} />
        </button>
      </div>
    </div>
  );
}
