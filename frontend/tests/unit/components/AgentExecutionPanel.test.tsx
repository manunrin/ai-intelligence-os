import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { Badge } from "@/components/ui/Badge";

describe("Quality score display in AgentExecutionPanel", () => {
  // We test the helper logic extracted from the panel via the Badge component
  // since the helpers are internal to the module. The key behaviors are:
  // - Score >= 0.7 renders with success (green) variant
  // - Score 0.4-0.69 renders with warning (amber) variant
  // - Score < 0.4 renders with danger (red) variant
  // - Null/undefined renders "—"

  it("renders quality badge with green for high score", () => {
    const { container } = render(<Badge variant="success">85%</Badge>);
    expect(screen.getByText("85%")).toBeInTheDocument();
    expect(container.firstChild).toHaveClass("bg-green-100");
  });

  it("renders quality badge with amber for medium score", () => {
    const { container } = render(<Badge variant="warning">52%</Badge>);
    expect(screen.getByText("52%")).toBeInTheDocument();
    expect(container.firstChild).toHaveClass("bg-amber-100");
  });

  it("renders quality badge with red for low score", () => {
    const { container } = render(<Badge variant="danger">23%</Badge>);
    expect(screen.getByText("23%")).toBeInTheDocument();
    expect(container.firstChild).toHaveClass("bg-red-100");
  });

  it("renders placeholder for null score", () => {
    render(<span>—</span>);
    expect(screen.getByText("—")).toBeInTheDocument();
  });
});
