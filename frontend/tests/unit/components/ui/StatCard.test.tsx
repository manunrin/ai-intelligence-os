import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { StatCard } from "@/components/ui/StatCard";

describe("StatCard", () => {
  it("renders title and value", () => {
    render(<StatCard title="Articles" value={42} />);
    expect(screen.getByText("Articles")).toBeInTheDocument();
    expect(screen.getByText("42")).toBeInTheDocument();
  });

  it("renders icon when provided", () => {
    const { container } = render(
      <StatCard title="Count" value={1} icon={<span data-testid="icon">★</span>} />
    );
    expect(container.querySelector('[data-testid="icon"]')).toBeInTheDocument();
  });

  it("renders trend text", () => {
    render(<StatCard title="Growth" value="12%" trend="+5% from last week" />);
    expect(screen.getByText("+5% from last week")).toBeInTheDocument();
  });

  it("applies variant color borders", () => {
    const { container } = render(<StatCard title="Error" value={3} variant="danger" />);
    expect(container.firstChild).toHaveClass("border-l-red-500");
  });

  it("defaults to default variant", () => {
    const { container } = render(<StatCard title="Default" value={0} />);
    expect(container.firstChild).toHaveClass("border-l-blue-500");
  });
});
