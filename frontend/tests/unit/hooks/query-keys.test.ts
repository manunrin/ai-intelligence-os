import { describe, it, expect } from "vitest";
import { articleKeys } from "@/hooks/useArticles";
import { taskKeys } from "@/hooks/useTasks";
import { knowledgeKeys } from "@/hooks/useKnowledge";
import { reportKeys } from "@/hooks/useReports";
import { agentRunKeys } from "@/hooks/useAgentRuns";

describe("query keys — articles", () => {
  it("has all and lists keys", () => {
    expect(articleKeys.all).toEqual(["articles"]);
    expect(articleKeys.lists()).toEqual(["articles", "list"]);
  });

  it("has details key factory", () => {
    // details() returns base detail key; no param factory (unlike agentRunKeys)
    expect(articleKeys.details()).toEqual(["articles", "detail"]);
  });
});

describe("query keys — tasks", () => {
  it("has all and lists keys", () => {
    expect(taskKeys.all).toEqual(["tasks"]);
    expect(taskKeys.lists()).toEqual(["tasks", "list"]);
  });
});

describe("query keys — knowledge", () => {
  it("has all and lists keys", () => {
    expect(knowledgeKeys.all).toEqual(["knowledge"]);
    expect(knowledgeKeys.lists()).toEqual(["knowledge", "list"]);
  });
});

describe("query keys — reports", () => {
  it("has all and lists keys", () => {
    expect(reportKeys.all).toEqual(["reports"]);
    expect(reportKeys.lists()).toEqual(["reports", "list"]);
  });
});

describe("query keys — agentRuns", () => {
  it("has all, lists, and details keys", () => {
    expect(agentRunKeys.all).toEqual(["agentRuns"]);
    expect(agentRunKeys.lists()).toEqual(["agentRuns", "list"]);
    expect(agentRunKeys.details("r1")).toEqual(["agentRuns", "detail", "r1"]);
  });
});
