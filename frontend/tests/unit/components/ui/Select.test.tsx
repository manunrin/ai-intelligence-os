import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { Select } from "@/components/ui/Select";

describe("Select", () => {
  it("renders label", () => {
    render(<Select label="Category" options={[{ value: "a" }]} />);
    expect(screen.getByText("Category")).toBeInTheDocument();
  });

  it("renders options", () => {
    const options = [
      { value: "en", label: "English" },
      { value: "zh", label: "Chinese" },
    ];
    render(<Select options={options} />);
    expect(screen.getByText("English")).toBeInTheDocument();
    expect(screen.getByText("Chinese")).toBeInTheDocument();
  });

  it("falls back to value as label", () => {
    render(<Select options={[{ value: "raw" }]} />);
    expect(screen.getByText("raw")).toBeInTheDocument();
  });

  it("shows error message", () => {
    render(<Select options={[]} error="Invalid selection" />);
    expect(screen.getByText("Invalid selection")).toBeInTheDocument();
  });

  it("applies custom className", () => {
    const { container } = render(<Select options={[]} className="wide-select" />);
    const select = container.querySelector("select")!;
    expect(select.className).toContain("wide-select");
  });
});
