export interface Article {
  id: string;
  title: string;
  summary: string;
  content: string;
  url: string;
  source: string;
  language: string;
  tags: string[];
  status: "raw" | "analyzed" | "translated" | "error";
  fetched_at: string;
  published_at?: string;
} & Record<string, unknown>;

export interface KnowledgeItem {
  id: string;
  title: string;
  content: string;
  kind: "article" | "research" | "analysis" | "translation";
  article_id: string | null;
  tags: string[];
  created_at: string;
} & Record<string, unknown>;

export interface AgentRun {
  id: string;
  agent_id: string;
  workflow_id: string | null;
  status: "pending" | "running" | "completed" | "failed";
  input_payload: Record<string, unknown>;
  output_payload: Record<string, unknown> | null;
  error_message: string | null;
  started_at: string;
  finished_at: string | null;
} & Record<string, unknown>;

export interface Task {
  id: string;
  title: string;
  description: string;
  priority: "low" | "medium" | "high" | "urgent";
  status: "todo" | "in_progress" | "done" | "blocked";
  dependency: string[];
  created_at: string;
} & Record<string, unknown>;

export interface AgentInfo {
  name: string;
  version: string;
  description: string;
}

export interface IntelligenceReport {
  id: string;
  topic: string;
  research_result: Record<string, unknown> | null;
  analysis_result: Record<string, unknown> | null;
  translation_result: Record<string, unknown> | null;
  knowledge_items: KnowledgeItem[];
  tasks: Task[];
  created_at: string;
}
