import { describe, it, expect } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { ToastProvider, useToast } from "@/lib/toast";

function TestConsumer() {
  const { toast } = useToast();
  return <button onClick={() => toast("hello", "success")}>Notify</button>;
}

function ToastWrapper({ children }: { children: React.ReactNode }) {
  return <ToastProvider>{children}</ToastProvider>;
}

describe("ToastProvider", () => {
  it("throws useToast outside provider", () => {
    expect(() => render(<TestConsumer />)).toThrow("useToast must be used within ToastProvider");
  });

  it("renders toast button inside provider", () => {
    render(<TestConsumer />, { wrapper: ToastWrapper });
    expect(screen.getByText("Notify")).toBeInTheDocument();
  });

  it("displays toast message on click", async () => {
    render(<TestConsumer />, { wrapper: ToastWrapper });
    fireEvent.click(screen.getByText("Notify"));
    await waitFor(() => {
      expect(screen.getByText("hello")).toBeInTheDocument();
    });
  });

  it("renders toast in fixed container", async () => {
    render(<TestConsumer />, { wrapper: ToastWrapper });
    fireEvent.click(screen.getByText("Notify"));
    await waitFor(() => {
      const container = document.querySelector(".fixed.bottom-4");
      expect(container).toBeInTheDocument();
    });
  });
});
