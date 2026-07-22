export type Article = {
  id: string;
  title: string;
  summary: string | null;
  content: string | null;
  url: string | null;
  source: string;
  language: string;
  tags: string[];
  status: string;
  fetched_at: string;
  published_at: string | null;
  user_id: string | null;
} & Record<string, unknown>;

export type KnowledgeItem = {
  id: string;
  title: string;
  content: string;
  kind: string;
  article_id: string | null;
  tags: string[];
  created_at: string;
  user_id: string | null;
} & Record<string, unknown>;

export interface KnowledgeSearchResult {
  knowledge_id: string;
  title: string;
  content: string;
  kind: string;
  score: number | null;
  tags: string[];
  hybrid_score?: number | null;
  dense_score?: number | null;
  keyword_score?: number | null;
}

export interface RAGResponse {
  answer: string;
  sources: Array<{
    knowledge_id: string;
    title: string;
  }>;
  query: string;
}

export type AgentRun = {
  id: string;
  agent_id: string;
  workflow_id: string | null;
  status: string;
  stage: string;
  input_payload: Record<string, unknown>;
  output_payload: Record<string, unknown> | null;
  error_message: string | null;
  started_at: string;
  finished_at: string | null;
  duration_ms: number | null;
  user_id: string | null;
  retry_count?: number;
} & Record<string, unknown>;

export type Task = {
  id: string;
  title: string;
  description: string | null;
  priority: string;
  status: string;
  dependency: string[];
  created_at: string;
  user_id: string | null;
} & Record<string, unknown>;

export interface AgentInfo {
  name: string;
  version: string;
  description: string;
}

export type IntelligenceReport = {
  id: string;
  topic: string;
  created_at: string;
  user_id: string | null;
};
