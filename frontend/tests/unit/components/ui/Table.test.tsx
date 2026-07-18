import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { DataTable } from "@/components/ui/Table";

describe("DataTable", () => {
  it("renders column headers", () => {
    render(
      <DataTable
        columns={[{ key: "name", label: "Name" }, { key: "age", label: "Age" }]}
        data={[]}
      />
    );
    expect(screen.getByText("Name")).toBeInTheDocument();
    expect(screen.getByText("Age")).toBeInTheDocument();
  });

  it("renders empty state when no data", () => {
    render(
      <DataTable
        columns={[{ key: "id", label: "ID" }]}
        data={[]}
      />
    );
    expect(screen.getByText("No data available")).toBeInTheDocument();
  });

  it("renders rows with data", () => {
    render(
      <DataTable
        columns={[{ key: "title", label: "Title" }]}
        data={[{ id: "1", title: "First" }, { id: "2", title: "Second" }]}
      />
    );
    expect(screen.getByText("First")).toBeInTheDocument();
    expect(screen.getByText("Second")).toBeInTheDocument();
  });

  it("uses custom renderCell", () => {
    render(
      <DataTable
        columns={[{ key: "status", label: "Status" }]}
        data={[{ id: "1", status: "active" }]}
        renderCell={(key, value) => (key === "status" ? `🟢 ${value}` : String(value))}
      />
    );
    expect(screen.getByText("🟢 active")).toBeInTheDocument();
  });

  it("renders default cell as string", () => {
    render(
      <DataTable
        columns={[{ key: "name", label: "Name" }]}
        data={[{ id: "1", name: "Alice" }]}
      />
    );
    expect(screen.getByText("Alice")).toBeInTheDocument();
  });

  it("handles null cell values", () => {
    render(
      <DataTable
        columns={[{ key: "x", label: "X" }]}
        data={[{ id: "1", x: null }]}
      />
    );
    // null renders as empty string — check the table row has exactly one td
    const tds = document.querySelectorAll("tbody td");
    expect(tds.length).toBe(1);
    expect(tds[0].textContent).toBe("");
  });
});
