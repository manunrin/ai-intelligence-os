import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { Textarea } from "@/components/ui/Textarea";

describe("Textarea", () => {
  it("renders label", () => {
    render(<Textarea label="Description" />);
    expect(screen.getByText("Description")).toBeInTheDocument();
  });

  it("shows error message", () => {
    render(<Textarea error="Too short" />);
    expect(screen.getByText("Too short")).toBeInTheDocument();
  });

  it("passes value prop", () => {
    const { container } = render(<Textarea value="long text here" />);
    const textarea = container.querySelector("textarea")!;
    expect(textarea.value).toBe("long text here");
  });

  it("applies custom className", () => {
    const { container } = render(<Textarea className="full-width" />);
    const textarea = container.querySelector("textarea")!;
    expect(textarea.className).toContain("full-width");
  });
});
