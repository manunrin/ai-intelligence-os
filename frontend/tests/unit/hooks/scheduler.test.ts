import { describe, it, expect } from "vitest";
import { formatCronExpression, isValidCron } from "@/lib/cron-helpers";

describe("formatCronExpression", () => {
  it("formats common patterns", () => {
    expect(formatCronExpression("0 8 * * *")).toBe("Every day at 8:00 AM");
    expect(formatCronExpression("0 */2 * * *")).toBe("Every 2 hours");
    expect(formatCronExpression("0 9 * * 1-5")).toBe("Weekdays at 9:00 AM");
    expect(formatCronExpression("* * * * *")).toBe("Every minute");
    expect(formatCronExpression("0 * * * *")).toBe("Every hour");
  });

  it("shows raw expression for unmapped patterns", () => {
    expect(formatCronExpression("30 14 * * 1,3,5")).toBe("30 14 * * 1,3,5");
  });
});

describe("isValidCron", () => {
  it("returns true for valid five-field expressions", () => {
    expect(isValidCron("0 8 * * *")).toBe(true);
    expect(isValidCron("*/5 * * * *")).toBe(true);
    expect(isValidCron("0 9 * * 1-5")).toBe(true);
  });

  it("returns false for invalid expressions", () => {
    expect(isValidCron("invalid")).toBe(false);
    expect(isValidCron("* * *")).toBe(false);
    expect(isValidCron("")).toBe(false);
  });
});
