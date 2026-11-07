import { describe, expect, it } from "vitest";
import { toLocalOrder, type OrderOut } from "@/lib/checkout-api";
import { odooSyncLabel } from "@/lib/admin-api";
import { formatStableDate } from "@/lib/format-date";

function orderOut(overrides: Partial<OrderOut> = {}): OrderOut {
  return {
    id: "00000000-0000-0000-0000-000000000001",
    order_number: "DEMO-ABC123",
    is_demo: true,
    status: "paid",
    currency: "SAR",
    subtotal_amount: "100.00",
    discount_amount: "0.00",
    promo_code: null,
    tax_amount: "4.76",
    delivery_fee_amount: "15.00",
    total_amount: "115.00",
    is_gift: false,
    recipient_name: "Test",
    recipient_phone: "+966500000000",
    delivery_area: null,
    delivery_address: null,
    delivery_address_extra: null,
    delivery_date: null,
    delivery_time: null,
    tracking_token: "tk-test",
    payment_method: "Demo payment",
    items: [],
    status_history: [],
    created_at: "2026-11-07T00:00:00Z",
    ...overrides,
  } as OrderOut;
}

describe("demo order labelling", () => {
  it("carries the backend's is_demo flag onto the local order", () => {
    expect(toLocalOrder(orderOut()).isDemo).toBe(true);
    expect(toLocalOrder(orderOut({ is_demo: false })).isDemo).toBe(false);
  });
});

describe("odooSyncLabel", () => {
  it("never lets a simulated sync read as a delivered one", () => {
    expect(odooSyncLabel("simulated")).toBe("simulated (not in Odoo)");
    expect(odooSyncLabel("synced")).toBe("synced");
  });
});

describe("formatStableDate", () => {
  const timestamp = Date.UTC(2026, 9, 1);

  it("is the same text whatever the visitor's locale or time zone", () => {
    expect(formatStableDate(timestamp, "en")).toBe("10/1/2026");
  });

  it("uses the UTC date, not the local one, right at midnight", () => {
    expect(formatStableDate(Date.UTC(2026, 9, 1, 23, 59), "en")).toBe("10/1/2026");
  });

  it("formats Arabic in the Arabic locale", () => {
    expect(formatStableDate(timestamp, "ar")).not.toBe("10/1/2026");
  });
});
