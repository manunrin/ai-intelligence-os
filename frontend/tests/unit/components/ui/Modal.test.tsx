import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { Modal } from "@/components/ui/Modal";

describe("Modal", () => {
  it("is hidden when open is false", () => {
    const { container } = render(
      <Modal open={false} onClose={() => {}} title="Hidden">
        Content
      </Modal>
    );
    expect(container.firstChild).toBeNull();
  });

  it("renders when open", () => {
    render(
      <Modal open title="Title">
        Body
      </Modal>
    );
    expect(screen.getByText("Title")).toBeInTheDocument();
    expect(screen.getByText("Body")).toBeInTheDocument();
  });

  it("closes on Escape key", () => {
    const onClose = vi.fn();
    render(
      <Modal open onClose={onClose} title="Test">
        Content
      </Modal>
    );
    fireEvent.keyDown(document, { key: "Escape" });
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it("closes on overlay click", () => {
    const onClose = vi.fn();
    const { container } = render(
      <Modal open onClose={onClose} title="Test">
        Content
      </Modal>
    );
    const overlay = container.querySelector("div.fixed");
    if (overlay) fireEvent.click(overlay);
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it("renders footer", () => {
    render(
      <Modal open onClose={() => {}} title="Test" footer={<button>Save</button>}>
        Body
      </Modal>
    );
    expect(screen.getByText("Save")).toBeInTheDocument();
  });

  it("hides footer when not provided", () => {
    const { container } = render(
      <Modal open onClose={() => {}} title="Test">
        Body
      </Modal>
    );
    const footerEl = container.querySelector(".border-t");
    expect(footerEl).toBeNull();
  });
});
