import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { DashboardPanel } from "@/components/panels/DashboardPanel";

describe("DashboardPanel", () => {
  it("renders stat card counts", () => {
    render(
      <DashboardPanel
        articles={[]}
        knowledgeItems={[]}
        tasks={[]}
        agentRuns={[]}
      />
    );
    expect(screen.getByText("Articles")).toBeInTheDocument();
    const headings = screen.getAllByRole("heading");
    expect(headings.some((h) => h.textContent === "Active Tasks")).toBe(true);
    expect(headings.some((h) => h.textContent === "Agent Runs")).toBe(true);
  });

  it("displays correct article count", () => {
    render(
      <DashboardPanel
        articles={[{ id: "1", title: "A" } as any]}
        knowledgeItems={[]}
        tasks={[]}
        agentRuns={[]}
      />
    );
    expect(screen.getByText("1")).toBeInTheDocument();
  });

  it("shows empty state for no articles", () => {
    render(
      <DashboardPanel
        articles={[]}
        knowledgeItems={[]}
        tasks={[]}
        agentRuns={[]}
      />
    );
    expect(screen.getByText("No articles ingested yet.")).toBeInTheDocument();
  });

  it("shows empty state for no knowledge items", () => {
    render(
      <DashboardPanel
        articles={[]}
        knowledgeItems={[]}
        tasks={[]}
        agentRuns={[]}
      />
    );
    expect(screen.getByText("No knowledge extracted yet.")).toBeInTheDocument();
  });

  it("counts active tasks correctly", () => {
    const tasks = [
      { id: "1", title: "T1", status: "done" } as any,
      { id: "2", title: "T2", status: "in_progress" } as any,
      { id: "3", title: "T3", status: "blocked" } as any,
    ];
    render(
      <DashboardPanel
        articles={[]}
        knowledgeItems={[]}
        tasks={tasks}
        agentRuns={[]}
      />
    );
    expect(screen.getByText("2")).toBeInTheDocument();
  });

  it("renders recent articles with status badges", () => {
    const articles = [
      { id: "1", title: "Article One", source: "rss", status: "analyzed" } as any,
    ];
    render(
      <DashboardPanel
        articles={articles}
        knowledgeItems={[]}
        tasks={[]}
        agentRuns={[]}
      />
    );
    expect(screen.getByText("Article One")).toBeInTheDocument();
    expect(screen.getByText("rss")).toBeInTheDocument();
    expect(screen.getByText("analyzed")).toBeInTheDocument();
  });

  it("renders recent agent runs with status badges", () => {
    const runs = [
      { id: "1", agent_id: "daily-intel", status: "completed" } as any,
    ];
    render(
      <DashboardPanel
        articles={[]}
        knowledgeItems={[]}
        tasks={[]}
        agentRuns={runs}
      />
    );
    expect(screen.getByText("daily-intel")).toBeInTheDocument();
    expect(screen.getByText("completed")).toBeInTheDocument();
  });
});
