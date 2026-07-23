import { describe, it, expect, vi, beforeEach } from "vitest";
import { getAccessToken, setAccessToken, clearAccessToken, isAuthEndpoint, refreshAccessToken } from "@/lib/token-manager";

// Mock document.cookie
let _cookie = "";
Object.defineProperty(document, "cookie", {
  get: () => _cookie,
  set: (val) => { _cookie = val; },
  configurable: true,
});

describe("token-manager — get/set/clear", () => {
  beforeEach(() => {
    _cookie = "";
  });

  it("setAccessToken stores token and sets cookie", () => {
    setAccessToken("test-token-123");
    expect(getAccessToken()).toBe("test-token-123");
    expect(document.cookie).toContain("aio_auth_token=test-token-123");
  });

  it("getAccessToken returns null when no token stored", () => {
    clearAccessToken();
    expect(getAccessToken()).toBeNull();
  });

  it("clearAccessToken clears memory and cookie", () => {
    setAccessToken("abc");
    clearAccessToken();
    expect(getAccessToken()).toBeNull();
    expect(document.cookie).toContain("aio_auth_token=");
  });
});

describe("isAuthEndpoint", () => {
  it("returns true for /api/v1/auth/login", () => {
    expect(isAuthEndpoint("/api/v1/auth/login")).toBe(true);
  });

  it("returns true for /api/v1/auth/register", () => {
    expect(isAuthEndpoint("/api/v1/auth/register")).toBe(true);
  });

  it("returns true for /api/v1/auth/refresh", () => {
    expect(isAuthEndpoint("/api/v1/auth/refresh")).toBe(true);
  });

  it("returns true for /api/v1/auth/logout", () => {
    expect(isAuthEndpoint("/api/v1/auth/logout")).toBe(true);
  });

  it("returns false for non-auth endpoints", () => {
    expect(isAuthEndpoint("/api/v1/knowledge/search")).toBe(false);
    expect(isAuthEndpoint("/api/v1/agents/runs")).toBe(false);
  });
});

describe("refreshAccessToken", () => {
  it("success: returns new token string", async () => {
    const mockFetch = vi.fn();
    (globalThis.fetch as any) = mockFetch;

    mockFetch.mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: async () => ({ success: true, data: { access_token: "new-token" }, error: null }),
    });

    const result = await refreshAccessToken();
    expect(result).toBe("new-token");
    expect(mockFetch).toHaveBeenCalledTimes(1);
    expect(mockFetch).toHaveBeenCalledWith("/api/v1/auth/refresh", { method: "POST" });
  });

  it("failure 401: rejects with error message", async () => {
    const mockFetch = vi.fn();
    (globalThis.fetch as any) = mockFetch;

    mockFetch.mockResolvedValueOnce({
      ok: false,
      status: 401,
      json: async () => ({}),
    });

    await expect(refreshAccessToken()).rejects.toThrow(/invalid or expired/i);
  });

  it("concurrent calls share same Promise", async () => {
    const mockFetch = vi.fn();
    (globalThis.fetch as any) = mockFetch;

    let resolveFirst: (v: Response) => void;
    const promise = new Promise<Response>((resolve) => {
      resolveFirst = resolve as never;
    });

    mockFetch.mockReturnValueOnce(promise as never);

    const p1 = refreshAccessToken();
    const p2 = refreshAccessToken();

    expect(mockFetch).toHaveBeenCalledTimes(1);

    resolveFirst!({
      ok: true,
      status: 200,
      json: async () => ({ success: true, data: { access_token: "resolved-token" }, error: null }),
    } as never);

    const [r1, r2] = await Promise.all([p1, p2]);
    expect(r1).toBe(r2);
    expect(r1).toBe("resolved-token");
  });

  it("only one fetch even with 5 concurrent callers", async () => {
    const mockFetch = vi.fn();
    (globalThis.fetch as any) = mockFetch;

    let resolveFirst: (v: Response) => void;
    const promise = new Promise<Response>((resolve) => {
      resolveFirst = resolve as never;
    });

    mockFetch.mockReturnValueOnce(promise as never);

    const promises = Array.from({ length: 5 }, () => refreshAccessToken());

    expect(mockFetch).toHaveBeenCalledTimes(1);

    resolveFirst!({
      ok: true,
      status: 200,
      json: async () => ({ success: true, data: { access_token: "single-token" }, error: null }),
    } as never);

    const results = await Promise.all(promises);
    expect(results.every((r) => r === "single-token")).toBe(true);
  });
});
