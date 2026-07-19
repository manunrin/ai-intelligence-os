"use client";

import { useState } from "react";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { EmptyState } from "@/components/ui/EmptyState";
import { KnowledgePanel } from "@/components/panels/KnowledgePanel";
import { KnowledgeDetail } from "@/components/panels/KnowledgeDetail";
import { RAGChat } from "@/components/panels/RAGChat";
import type { KnowledgeItem, KnowledgeSearchResult } from "@/types";
import { useKnowledgeSearchMutation } from "@/hooks/useKnowledge";
import { useToast } from "@/lib/toast";

interface KnowledgePageProps {
  items: KnowledgeItem[];
  onNew: () => void;
  onEdit: (item: KnowledgeItem) => void;
  onDelete: (id: string) => void;
}

export function KnowledgePage({ items, onNew, onEdit, onDelete }: KnowledgePageProps) {
  const [selectedItem, setSelectedItem] = useState<KnowledgeItem | null>(null);
  const [filterKind, setFilterKind] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [isSearching, setIsSearching] = useState(false);
  const [searchResults, setSearchResults] = useState<KnowledgeSearchResult[]>([]);
  const [activeTab, setActiveTab] = useState<"knowledge" | "rag">("knowledge");
  const searchMutation = useKnowledgeSearchMutation();
  const { toast } = useToast();

  const kinds = [...new Set(items.map((i) => i.kind))];
  const filteredItems = filterKind ? items.filter((i) => i.kind === filterKind) : items;

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!searchQuery.trim()) return;

    setIsSearching(true);
    try {
      const response = await searchMutation.mutateAsync({
        query: searchQuery,
        limit: 10,
        kind_filter: filterKind,
      });

      if (Array.isArray(response)) {
        setSearchResults(response);
      } else {
        setSearchResults([]);
      }
    } catch (err) {
      toast(err instanceof Error ? err.message : "Search failed", "error");
      setSearchResults([]);
    } finally {
      setIsSearching(false);
    }
  };

  const handleClearSearch = () => {
    setSearchQuery("");
    setSearchResults([]);
    setIsSearching(false);
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-semibold tracking-tight text-slate-900 dark:text-slate-100">Knowledge Base</h2>
          <p className="text-sm text-slate-500 dark:text-slate-400 mt-0.5">
            {activeTab === "rag"
              ? "AI-powered answers from your knowledge"
              : `${isSearching ? searchResults.length : filteredItems.length} item${(isSearching ? searchResults.length : filteredItems.length) !== 1 ? 's' : ''}`}
            {!isSearching && activeTab === "knowledge" && filteredItems.length !== items.length && ` of ${items.length} total`}
          </p>
        </div>
        {activeTab === "knowledge" && (
          <Button onClick={onNew}>New Item</Button>
        )}
      </div>

      {/* Tab bar */}
      <div className="flex gap-1 rounded-lg bg-slate-100 p-1 dark:bg-slate-800 w-fit">
        <button
          type="button"
          onClick={() => setActiveTab("knowledge")}
          className={`rounded-md px-3 py-1.5 text-sm font-medium transition-colors duration-150 ${
            activeTab === "knowledge"
              ? "bg-white text-slate-900 shadow-sm dark:bg-slate-700 dark:text-slate-100"
              : "text-slate-600 hover:text-slate-900 dark:text-slate-400 dark:hover:text-slate-200"
          }`}
        >
          Browse
        </button>
        <button
          type="button"
          onClick={() => setActiveTab("rag")}
          className={`rounded-md px-3 py-1.5 text-sm font-medium transition-colors duration-150 ${
            activeTab === "rag"
              ? "bg-white text-slate-900 shadow-sm dark:bg-slate-700 dark:text-slate-100"
              : "text-slate-600 hover:text-slate-900 dark:text-slate-400 dark:hover:text-slate-200"
          }`}
        >
          Ask AI
        </button>
      </div>

      {/* Knowledge tab */}
      {activeTab === "knowledge" && (
        <>
          {/* Search bar */}
          <form onSubmit={handleSearch} className="flex gap-2">
            <Input
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search knowledge base..."
              className="flex-1"
            />
            <Button type="submit" disabled={isSearching || !searchQuery.trim()}>
              {isSearching ? "Searching..." : "Search"}
            </Button>
            {isSearching && (
              <Button type="button" variant="outline" onClick={handleClearSearch}>
                Clear
              </Button>
            )}
          </form>

          {/* Tag/kind filter bar */}
          {kinds.length > 0 && (
            <div className="flex flex-wrap items-center gap-1.5">
              <button
                type="button"
                onClick={() => setFilterKind(null)}
                className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium transition-colors duration-150 cursor-pointer ${
                  filterKind === null
                    ? "bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-300"
                    : "bg-slate-100 text-slate-600 hover:bg-slate-200 dark:bg-slate-800 dark:text-slate-400 dark:hover:bg-slate-700"
                }`}
              >
                All ({isSearching ? searchResults.length : items.length})
              </button>
              {kinds.map((kind) => (
                <button
                  key={kind}
                  type="button"
                  onClick={() => setFilterKind(filterKind === kind ? null : kind)}
                  className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium transition-colors duration-150 cursor-pointer ${
                    filterKind === kind
                      ? "bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-300"
                      : "bg-slate-100 text-slate-600 hover:bg-slate-200 dark:bg-slate-800 dark:text-slate-400 dark:hover:bg-slate-700"
                  }`}
                >
                  {kind} ({isSearching ? searchResults.filter(r => r.kind === kind).length : items.filter(i => i.kind === kind).length})
                </button>
              ))}
            </div>
          )}

          {/* Content grid */}
          {isSearching ? (
            searchResults.length > 0 ? (
              <KnowledgePanel
                items={searchResults.map((r) => ({
                  ...r,
                  id: r.knowledge_id,
                  article_id: null,
                  created_at: "",
                  user_id: null,
                })) as KnowledgeItem[]}
                onNew={onNew}
                onEdit={onEdit}
                onDelete={onDelete}
                showScores={true}
              />
            ) : (
              <EmptyState
                title="No results found"
                description="Try a different search query or clear the search to see all items."
              />
            )
          ) : (
            <KnowledgePanel
              items={filteredItems}
              onNew={onNew}
              onEdit={onEdit}
              onDelete={onDelete}
            />
          )}
        </>
      )}

      {/* RAG Chat tab */}
      {activeTab === "rag" && <RAGChat />}

      {/* Detail slide-over */}
      {selectedItem && (
        <KnowledgeDetail item={selectedItem} onClose={() => setSelectedItem(null)} />
      )}
    </div>
  );
}
