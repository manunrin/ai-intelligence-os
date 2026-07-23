import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { unwrap, unwrapSingle, ApiError } from "@/lib/api";

// Mock document.cookie
let _cookie = "";
Object.defineProperty(document, "cookie", {
  get: () => _cookie,
  set: (val) => { _cookie = val; },
  configurable: true,
});

describe("ApiError", () => {
  it("has correct name and code", () => {
    const err = new ApiError("BAD_REQUEST", "something failed");
    expect(err.name).toBe("ApiError");
    expect(err.code).toBe("BAD_REQUEST");
    expect(err.message).toBe("something failed");
  });

  it("stores optional details", () => {
    const details = [{ field: "email", message: "invalid" }];
    const err = new ApiError("VALIDATION_ERROR", "bad input", details);
    expect(err.details).toEqual(details);
  });
});

describe("unwrap", () => {
  it("extracts data array from envelope", async () => {
    const raw = { success: true, data: [{ id: "1" }, { id: "2" }] };
    const result = await unwrap(raw);
    expect(result).toEqual([{ id: "1" }, { id: "2" }]);
  });

  it("returns empty array for null", async () => {
    expect(await unwrap(null)).toEqual([]);
  });

  it("returns empty array for non-array without data key", async () => {
    const result = await unwrap({ foo: "bar" });
    expect(result).toEqual([]);
  });

  it("falls back to treating raw value as array", async () => {
    const result = await unwrap([{ id: "1" }]);
    expect(result).toEqual([{ id: "1" }]);
  });
});

describe("unwrapSingle", () => {
  it("extracts data object from envelope", async () => {
    const raw = { success: true, data: { id: "42" } };
    const result = await unwrapSingle(raw);
    expect(result).toEqual({ id: "42" });
  });

  it("returns null-like for null input", async () => {
    const result = await unwrapSingle(null);
    expect(result).toBeNull();
  });

  it("returns raw value when no data key", async () => {
    const raw = { id: "1", name: "test" };
    const result = await unwrapSingle(raw);
    expect(result).toEqual(raw);
  });
});

describe("API interceptor — silent token refresh", () => {
  beforeEach(() => {
    _cookie = "";
  });

  it("401 on normal request triggers refresh then retries with new token", async () => {
    const mockFetch = vi.fn();
    (globalThis.fetch as any) = mockFetch;

    // Call 1: original request → 401
    // Call 2: refresh → success
    // Call 3: retry of original → success
    mockFetch
      .mockResolvedValueOnce({
        ok: false,
        status: 401,
        json: async () => ({ code: "UNAUTHORIZED", message: "Token expired" }),
      })
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({ success: true, data: { access_token: "new-token" }, error: null }),
      })
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({ success: true, data: { id: "1" }, error: null }),
      });

    const { api } = await import("@/lib/api");
    const result = await api.get("/api/v1/knowledge/search");
    expect(result).toEqual({ success: true, data: { id: "1" }, error: null });
    expect(mockFetch).toHaveBeenCalledTimes(3);
  });

  it("401 on /api/v1/auth/login does NOT trigger refresh", async () => {
    const mockFetch = vi.fn();
    (globalThis.fetch as any) = mockFetch;

    mockFetch.mockResolvedValueOnce({
      ok: false,
      status: 401,
      json: async () => ({ code: "UNAUTHORIZED", message: "Invalid credentials" }),
    });

    const { api } = await import("@/lib/api");
    try {
      await api.get("/api/v1/auth/login");
    } catch {
      // Expected to throw
    }
    expect(mockFetch).toHaveBeenCalledTimes(1);
  });

  it("concurrent 401s → only one refresh initiated", async () => {
    const mockFetch = vi.fn();
    (globalThis.fetch as any) = mockFetch;

    let resolveRefresh: (v: Response) => void;
    const refreshPromise = new Promise<Response>((resolve) => {
      resolveRefresh = resolve as never;
    });

    // Both requests get 401 first, then refresh succeeds, then both retries succeed
    mockFetch
      .mockResolvedValueOnce({
        ok: false,
        status: 401,
        json: async () => ({ code: "UNAUTHORIZED", message: "Token expired" }),
      })
      .mockResolvedValueOnce({
        ok: false,
        status: 401,
        json: async () => ({ code: "UNAUTHORIZED", message: "Token expired" }),
      })
      .mockReturnValueOnce(refreshPromise as never);

    const { api } = await import("@/lib/api");
    const p1 = api.get("/api/v1/knowledge/search").catch(() => {});
    const p2 = api.get("/api/v1/knowledge/items").catch(() => {});

    // Wait for both 401s to arrive and refresh to start
    await new Promise((r) => setTimeout(r, 50));

    // Two 401s + one refresh = 3 fetches total
    expect(mockFetch).toHaveBeenCalledTimes(3);

    resolveRefresh!({
      ok: true,
      status: 200,
      json: async () => ({ success: true, data: { access_token: "new-token" }, error: null }),
    } as never);

    // Both retry requests succeed
    mockFetch
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({ success: true, data: { id: "1" }, error: null }),
      })
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({ success: true, data: { id: "2" }, error: null }),
      });

    await Promise.all([p1, p2]);
    expect(mockFetch).toHaveBeenCalledTimes(5);
  });

  it("request already retried → 401 again → throws session expired", async () => {
    const mockFetch = vi.fn();
    (globalThis.fetch as any) = mockFetch;

    mockFetch
      .mockResolvedValueOnce({
        ok: false,
        status: 401,
        json: async () => ({ code: "UNAUTHORIZED", message: "Token expired" }),
      })
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({ success: true, data: { access_token: "new-token" }, error: null }),
      })
      .mockResolvedValueOnce({
        ok: false,
        status: 401,
        json: async () => ({ code: "UNAUTHORIZED", message: "Still unauthorized" }),
      });

    const { api } = await import("@/lib/api");
    try {
      await api.get("/api/v1/knowledge/search");
    } catch (err) {
      expect((err as ApiError).code).toBe("UNAUTHORIZED");
      expect((err as ApiError).message).toContain("Session expired");
    }
  });
});
