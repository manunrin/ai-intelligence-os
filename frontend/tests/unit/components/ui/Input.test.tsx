import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { Input } from "@/components/ui/Input";

describe("Input", () => {
  it("renders label when provided", () => {
    render(<Input label="Username" />);
    expect(screen.getByText("Username")).toBeInTheDocument();
  });

  it("renders without label", () => {
    const { container } = render(<Input />);
    expect(container.querySelector("label")).toBeNull();
  });

  it("shows error message", () => {
    render(<Input error="Required field" />);
    expect(screen.getByText("Required field")).toBeInTheDocument();
  });

  it("does not show error when not provided", () => {
    const { container } = render(<Input />);
    expect(container.querySelector(".text-red-600")).toBeNull();
  });

  it("passes value prop", () => {
    const { container } = render(<Input value="test-value" />);
    const input = container.querySelector("input")!;
    expect(input.value).toBe("test-value");
  });

  it("applies custom className", () => {
    const { container } = render(<Input className="custom-input" />);
    const input = container.querySelector("input")!;
    expect(input.className).toContain("custom-input");
  });

  it("applies error border style", () => {
    const { container } = render(<Input error="Oops" />);
    const input = container.querySelector("input")!;
    expect(input.className).toContain("!border-red-500");
  });
});
