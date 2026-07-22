import { describe, it, expect } from "vitest";
import { parseSearchResponse } from "@/hooks/useKnowledge";

describe("parseSearchResponse", () => {
  it("returns empty array for null/undefined", () => {
    expect(parseSearchResponse(null)).toEqual([]);
    expect(parseSearchResponse(undefined)).toEqual([]);
  });

  it("returns empty array for non-object input", () => {
    expect(parseSearchResponse("string")).toEqual([]);
    expect(parseSearchResponse(42)).toEqual([]);
  });

  it("parses nested data.results", () => {
    const raw = {
      success: true,
      data: {
        results: [
          { knowledge_id: "1", title: "Test", content: "Content", kind: "note", score: 0.9, tags: ["tag1"] },
        ],
      },
    };
    const result = parseSearchResponse(raw);
    expect(result).toHaveLength(1);
    expect(result[0].knowledge_id).toBe("1");
    expect(result[0].title).toBe("Test");
  });

  it("handles missing results key", () => {
    const raw = {
      success: true,
      data: {},
    };
    expect(parseSearchResponse(raw)).toEqual([]);
  });

  it("handles non-object data", () => {
    const raw = {
      success: true,
      data: "not an object",
    };
    expect(parseSearchResponse(raw)).toEqual([]);
  });
});
