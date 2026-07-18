import { describe, it, expect } from "vitest";
import { unwrap, unwrapSingle, ApiError } from "@/lib/api";

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
