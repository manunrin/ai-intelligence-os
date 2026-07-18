import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { Button } from "@/components/ui/Button";

describe("Button", () => {
  it("renders children", () => {
    render(<Button>Click me</Button>);
    expect(screen.getByText("Click me")).toBeInTheDocument();
  });

  it("applies default variant classes", () => {
    const { container } = render(<Button>Default</Button>);
    const button = container.querySelector("button")!;
    expect(button.className).toContain("bg-blue-600");
    expect(button.className).toContain("text-white");
  });

  it("applies outline variant classes", () => {
    const { container } = render(<Button variant="outline">Outline</Button>);
    const button = container.querySelector("button")!;
    expect(button.className).toContain("border");
    expect(button.className).not.toContain("bg-blue-600");
  });

  it("applies destructive variant classes", () => {
    const { container } = render(<Button variant="destructive">Delete</Button>);
    const button = container.querySelector("button")!;
    expect(button.className).toContain("bg-red-600");
  });

  it("applies size classes", () => {
    const { container } = render(<Button size="sm">Small</Button>);
    const button = container.querySelector("button")!;
    expect(button.className).toContain("text-sm px-3 py-1.5");
  });

  it("passes through disabled state", () => {
    const { container } = render(<Button disabled>Disabled</Button>);
    const button = container.querySelector("button")!;
    expect(button.disabled).toBe(true);
    expect(button.className).toContain("disabled:opacity-50");
  });

  it("merges custom className", () => {
    const { container } = render(<Button className="custom-class">Custom</Button>);
    const button = container.querySelector("button")!;
    expect(button.className).toContain("custom-class");
  });
});
