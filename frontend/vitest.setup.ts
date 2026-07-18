import "@testing-library/jest-dom/vitest";

// Mock next/navigation — pages/hooks use useRouter, usePathname, etc.
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn(), prefetch: vi.fn() }),
  usePathname: () => "/",
  useSearchParams: () => ({ get: vi.fn() }),
}));

// Mock fetch globally — api.ts calls fetch directly
const _fetch = globalThis.fetch;
beforeEach(() => {
  (globalThis.fetch as ReturnType<typeof vi.fn>) = vi.fn();
});
afterEach(() => {
  (globalThis.fetch as ReturnType<typeof vi.fn>).mockRestore();
});
