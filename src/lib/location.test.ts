import { describe, expect, it } from "vitest";
import { storeNow } from "@/lib/location";

describe("storeNow", () => {
  it("reads as Riyadh time (UTC+3)", () => {
    const now = storeNow(new Date(Date.UTC(2026, 10, 7, 12, 30)));
    expect(now.getHours()).toBe(15);
    expect(now.getMinutes()).toBe(30);
  });

  it("moves to the next day when Riyadh has passed midnight but UTC hasn't", () => {
    const now = storeNow(new Date(Date.UTC(2026, 10, 7, 22, 0)));
    expect(now.getDate()).toBe(8);
    expect(now.getHours()).toBe(1);
  });

  it("reads midnight as hour 0, not 24", () => {
    const now = storeNow(new Date(Date.UTC(2026, 10, 7, 21, 0)));
    expect(now.getHours()).toBe(0);
  });
});
