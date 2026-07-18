import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { Card } from "@/components/ui/Card";

describe("Card", () => {
  it("renders children", () => {
    render(<Card>Content</Card>);
    expect(screen.getByText("Content")).toBeInTheDocument();
  });

  it("renders title", () => {
    render(<Card title="Title Text">Body</Card>);
    expect(screen.getByText("Title Text")).toBeInTheDocument();
  });

  it("renders subtitle", () => {
    render(<Card subtitle="Subtitle text">Body</Card>);
    expect(screen.getByText("Subtitle text")).toBeInTheDocument();
  });

  it("renders footer", () => {
    render(
      <Card footer={<span>Footer</span>}>Body</Card>
    );
    expect(screen.getByText("Footer")).toBeInTheDocument();
  });

  it("does not render header section when no title or subtitle", () => {
    const { container } = render(<Card>No Header</Card>);
    const header = container.querySelector("div.border-b");
    expect(header).toBeNull();
  });

  it("merges custom className", () => {
    const { container } = render(<Card className="custom-card">Body</Card>);
    expect(container.firstChild).toHaveClass("custom-card");
  });
});
