import "@testing-library/jest-dom/vitest";

// Mock next/navigation — pages/hooks use useRouter, usePathname, etc.
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn(), prefetch: vi.fn() }),
  usePathname: () => "/",
  useSearchParams: () => ({ get: vi.fn() }),
}));

// Mock fetch globally — api.ts calls fetch directly
let _origFetch: typeof fetch | undefined;

beforeEach(() => {
  _origFetch = globalThis.fetch;
  (globalThis.fetch as any) = vi.fn();
});

afterEach(() => {
  const fn = globalThis.fetch as any;
  if (fn && typeof fn.mockRestore === "function") {
    fn.mockRestore();
  }
  if (_origFetch !== undefined) {
    (globalThis.fetch as any) = _origFetch;
  }
});
