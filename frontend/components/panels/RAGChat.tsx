"use client";

import { useState, useRef, useEffect } from "react";
import type { RAGResponse } from "@/types";
import { useRAGQuery } from "@/hooks/useKnowledge";
import { useToast } from "@/lib/toast";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  sources?: Array<{ knowledge_id: string; title: string }>;
  query?: string;
}

export function RAGChat() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [isTyping, setIsTyping] = useState(false);
  const { mutateAsync, isPending } = useRAGQuery();
  const { toast } = useToast();
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, isTyping]);

  const handleSend = async () => {
    const question = input.trim();
    if (!question || isPending) return;

    const userMsg: Message = {
      id: `user-${Date.now()}`,
      role: "user",
      content: question,
    };

    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setIsTyping(true);

    try {
      const response: RAGResponse = await mutateAsync({ query: question });

      const assistantMsg: Message = {
        id: `assistant-${Date.now()}`,
        role: "assistant",
        content: response.answer,
        sources: response.sources.length > 0 ? response.sources : undefined,
      };

      setMessages((prev) => [...prev, assistantMsg]);
    } catch (err) {
      toast(err instanceof Error ? err.message : "RAG query failed", "error");
    } finally {
      setIsTyping(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="flex flex-col h-[560px] rounded-xl border border-slate-200 bg-white dark:border-slate-700 dark:bg-slate-900 overflow-hidden">
      {/* Messages area */}
      <div ref={scrollRef} className="flex-1 overflow-y-auto px-4 py-4 space-y-4">
        {messages.length === 0 && (
          <div className="flex h-full items-center justify-center text-center">
            <div>
              <p className="text-sm font-medium text-slate-700 dark:text-slate-300">
                Ask about your knowledge base
              </p>
              <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
                Get AI-powered answers with source citations
              </p>
            </div>
          </div>
        )}

        {messages.map((msg) =>
          msg.role === "user" ? (
            <div key={msg.id} className="flex justify-end">
              <div className="max-w-[80%] rounded-2xl bg-blue-600 px-4 py-2.5 text-sm text-white shadow-sm">
                {msg.content}
              </div>
            </div>
          ) : (
            <div key={msg.id} className="space-y-2">
              <div className="max-w-[85%] rounded-2xl bg-slate-100 px-4 py-2.5 text-sm text-slate-900 dark:bg-slate-800 dark:text-slate-100 shadow-sm">
                {msg.content}
              </div>
              {msg.sources && msg.sources.length > 0 && (
                <div className="max-w-[85%]">
                  <p className="mb-1.5 text-xs font-medium uppercase tracking-wider text-slate-500 dark:text-slate-400">
                    Sources
                  </p>
                  <div className="flex flex-wrap gap-1.5">
                    {msg.sources.map((src, i) => (
                      <span
                        key={i}
                        className="inline-flex items-center gap-1 rounded-md border border-slate-200 bg-slate-50 px-2 py-1 text-xs text-slate-600 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-300"
                      >
                        <span className="font-medium text-slate-400 dark:text-slate-500">#{i + 1}</span>
                        {src.title}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )
        )}

        {isTyping && (
          <div className="flex items-center gap-1.5 px-4 py-3">
            <span className="h-2 w-2 animate-bounce rounded-full bg-slate-400 [--animation-delay:0ms]" />
            <span className="h-2 w-2 animate-bounce rounded-full bg-slate-400 [--animation-delay:150ms]" />
            <span className="h-2 w-2 animate-bounce rounded-full bg-slate-400 [--animation-delay:300ms]" />
          </div>
        )}
      </div>

      {/* Input bar */}
      <div className="border-t border-slate-200 bg-slate-50 px-3 py-2.5 dark:border-slate-700 dark:bg-slate-900/50">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            handleSend();
          }}
          className="flex items-center gap-2"
        >
          <Input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask a question..."
            disabled={isPending}
            className="flex-1"
          />
          <Button type="submit" disabled={isPending || !input.trim()}>
            Send
          </Button>
        </form>
      </div>
    </div>
  );
}
