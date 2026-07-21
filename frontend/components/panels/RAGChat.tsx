"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import type { RAGResponse } from "@/types";
import { useRAGStream } from "@/hooks/useKnowledge";
import { useToast } from "@/lib/toast";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  sources?: Array<{ knowledge_id: string; title: string }>;
  query?: string;
  status: "streaming" | "done" | "error";
}

export function RAGChat() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [selectedKind, setSelectedKind] = useState<string | null>(null);
  const { isStreaming, start: startStream, stop: stopStream } = useRAGStream();
  const { toast } = useToast();
  const scrollRef = useRef<HTMLDivElement>(null);
  const assistantMsgIdRef = useRef<string | null>(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, isStreaming]);

  const appendAssistantContent = useCallback(
    (content: string) => {
      if (!assistantMsgIdRef.current) return;
      setMessages((prev) =>
        prev.map((msg) =>
          msg.id === assistantMsgIdRef.current
            ? { ...msg, content: msg.content + content }
            : msg
        )
      );
    },
    []
  );

  const finalizeAssistantMessage = useCallback(
    (sources: Array<{ knowledge_id: string; title: string }>) => {
      if (!assistantMsgIdRef.current) return;
      setMessages((prev) =>
        prev.map((msg) =>
          msg.id === assistantMsgIdRef.current
            ? { ...msg, status: "done", sources }
            : msg
        )
      );
      assistantMsgIdRef.current = null;
    },
    []
  );

  const handleError = useCallback(
    (message: string) => {
      if (assistantMsgIdRef.current) {
        setMessages((prev) =>
          prev.map((msg) =>
            msg.id === assistantMsgIdRef.current
              ? { ...msg, status: "error" as const, content: msg.content || message }
              : msg
          )
        );
        assistantMsgIdRef.current = null;
      }
      toast(message, "error");
    },
    [toast]
  );

  const handleSend = () => {
    const question = input.trim();
    if (!question || isStreaming) return;

    const userMsg: Message = {
      id: `user-${Date.now()}`,
      role: "user",
      content: question,
      status: "done",
    };

    setMessages((prev) => [...prev, userMsg]);
    setInput("");

    const assistantMsgId = `assistant-${Date.now()}`;
    const assistantMsg: Message = {
      id: assistantMsgId,
      role: "assistant",
      content: "",
      status: "streaming",
      query: question,
    };
    setMessages((prev) => [...prev, assistantMsg]);
    assistantMsgIdRef.current = assistantMsgId;

    startStream(question, selectedKind, null, {
      onToken: appendAssistantContent,
      onDone: finalizeAssistantMessage,
      onError: handleError,
    });
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleStop = () => {
    stopStream();
    if (assistantMsgIdRef.current) {
      setMessages((prev) =>
        prev.map((msg) =>
          msg.id === assistantMsgIdRef.current
            ? { ...msg, status: msg.content.length > 0 ? "done" : "error" }
            : msg
        )
      );
      assistantMsgIdRef.current = null;
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
              <div className="max-w-[85%] rounded-2xl bg-slate-100 px-4 py-2.5 text-sm text-slate-900 dark:bg-slate-800 dark:text-slate-100 shadow-sm whitespace-pre-wrap">
                {msg.content || (
                  <span className="inline-block h-4 w-2 animate-pulse rounded bg-slate-400" />
                )}
                {msg.status === "streaming" && (
                  <span className="ml-0.5 inline-block h-4 w-2 animate-pulse rounded bg-slate-400" />
                )}
              </div>
              {msg.status === "error" && (
                <p className="max-w-[85%] text-xs text-red-600 dark:text-red-400">
                  Stream failed. Please try again.
                </p>
              )}
              {msg.sources && msg.sources.length > 0 && msg.status === "done" && (
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
      </div>

      {/* Input bar */}
      <div className="border-t border-slate-200 bg-slate-50 px-3 py-2.5 dark:border-slate-700 dark:bg-slate-900/50">
        <div className="flex items-center gap-2 mb-2">
          <span className="text-xs font-medium uppercase tracking-wider text-slate-500 dark:text-slate-400">
            Scope:
          </span>
          <button
            type="button"
            onClick={() => setSelectedKind(null)}
            className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium transition-colors duration-150 cursor-pointer ${
              selectedKind === null
                ? "bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-300"
                : "bg-slate-200 text-slate-600 hover:bg-slate-300 dark:bg-slate-700 dark:text-slate-300 dark:hover:bg-slate-600"
            }`}
          >
            All kinds
          </button>
        </div>
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
            disabled={isStreaming}
            className="flex-1"
          />
          {isStreaming ? (
            <Button type="button" variant="outline" onClick={handleStop}>
              Stop
            </Button>
          ) : (
            <Button type="submit" disabled={!input.trim()}>
              Send
            </Button>
          )}
        </form>
      </div>
    </div>
  );
}
