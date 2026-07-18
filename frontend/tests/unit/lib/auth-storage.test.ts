import { describe, it, expect } from "vitest";
import { getStoredToken, storeToken, clearToken, getStoredUser, storeUser, clearUser, clearAuth } from "@/lib/auth-storage";

describe("auth-storage", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it("stores and retrieves token", () => {
    storeToken("abc123");
    expect(getStoredToken()).toBe("abc123");
  });

  it("returns null when no token stored", () => {
    expect(getStoredToken()).toBeNull();
  });

  it("clears token", () => {
    storeToken("xyz");
    clearToken();
    expect(getStoredToken()).toBeNull();
  });

  it("stores and retrieves user object", () => {
    const user = { id: "1", username: "alice" };
    storeUser(user);
    expect(getStoredUser()).toEqual(user);
  });

  it("returns null when no user stored", () => {
    expect(getStoredUser()).toBeNull();
  });

  it("clears user", () => {
    storeUser({ id: "1" });
    clearUser();
    expect(getStoredUser()).toBeNull();
  });

  it("clears both token and user", () => {
    storeToken("t");
    storeUser({ id: "1" });
    clearAuth();
    expect(getStoredToken()).toBeNull();
    expect(getStoredUser()).toBeNull();
  });
});
