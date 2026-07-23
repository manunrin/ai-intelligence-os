import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { SchedulerExecutionHistory } from "@/components/panels/SchedulerExecutionHistory";
import type { ExecutionHistoryItem } from "@/types";

const mockHistory: ExecutionHistoryItem[] = [
  {
    id: "run-1",
    status: "completed",
    stage: "complete",
    started_at: "2026-07-23T08:00:00Z",
    finished_at: "2026-07-23T08:05:30Z",
    duration_ms: 330000,
    error_message: null,
    retry_count: 0,
  },
  {
    id: "run-2",
    status: "failed",
    stage: "failed",
    started_at: "2026-07-23T09:00:00Z",
    finished_at: "2026-07-23T09:01:00Z",
    duration_ms: 60000,
    error_message: "LLM provider timeout",
    retry_count: 1,
  },
];

describe("SchedulerExecutionHistory", () => {
  it("renders empty state when history is empty", () => {
    const { container } = render(
      <SchedulerExecutionHistory history={[]} isLoading={false} />
    );
    expect(container).toHaveTextContent("No executions recorded");
  });

  it("renders loading state when loading", () => {
    const { container } = render(
      <SchedulerExecutionHistory history={[]} isLoading={true} />
    );
    expect(container).toHaveTextContent("Loading execution history");
  });

  it("renders history rows with status badges", () => {
    render(<SchedulerExecutionHistory history={mockHistory} isLoading={false} />);
    expect(screen.getByText("completed")).toBeInTheDocument();
    expect(screen.getByText("failed")).toBeInTheDocument();
  });

  it("formats duration correctly for minutes", () => {
    render(<SchedulerExecutionHistory history={mockHistory} isLoading={false} />);
    // 60000ms = 1m
    expect(screen.getByText("1m 0s")).toBeInTheDocument();
  });

  it("formats duration correctly for hours", () => {
    const longRun: ExecutionHistoryItem = {
      id: "long-run",
      status: "completed",
      stage: "complete",
      started_at: "2026-07-23T08:00:00Z",
      finished_at: "2026-07-23T09:05:30Z",
      duration_ms: 3930000,
      error_message: null,
    };
    render(<SchedulerExecutionHistory history={[longRun]} isLoading={false} />);
    // 3930000ms ≈ 1h 5m (component shows h and min only)
    expect(screen.getByText("1h 5m")).toBeInTheDocument();
  });

  it("displays error message when present", () => {
    render(<SchedulerExecutionHistory history={mockHistory} isLoading={false} />);
    expect(screen.getByText("LLM provider timeout")).toBeInTheDocument();
  });

  it("truncates long error messages", () => {
    const longError: ExecutionHistoryItem = {
      id: "error-run",
      status: "failed",
      stage: "failed",
      started_at: "2026-07-23T10:00:00Z",
      finished_at: "2026-07-23T10:00:01Z",
      duration_ms: 1000,
      error_message: "A very long error message that should be truncated in the UI to prevent layout overflow while still being accessible via the title attribute for full context",
    };
    const { container } = render(
      <SchedulerExecutionHistory history={[longError]} isLoading={false} />
    );
    const errorEl = container.querySelector("[title]");
    expect(errorEl).toHaveAttribute(
      "title",
      "A very long error message that should be truncated in the UI to prevent layout overflow while still being accessible via the title attribute for full context"
    );
  });
});
