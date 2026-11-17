import { describe, expect, it } from "vitest";
import { summariseProviderModes } from "@/lib/provider-modes";

const modes = (payment: string, notification: string, odoo: string) => ({
  payment_provider_mode: payment,
  notification_provider_mode: notification,
  odoo_order_push_mode: odoo,
});

describe("summariseProviderModes", () => {
  it("staging: payments and notifications simulated, Odoo push live", () => {
    const s = summariseProviderModes(modes("stub", "stub", "live"));
    expect(s.anySimulated).toBe(true);
    expect(s.simulated).toEqual(["payments", "notifications"]);
    expect(s.active).toEqual([{ label: "Odoo order push", mode: "live" }]);
    expect(s.message).toBe(
      "Test mode: Payments and notifications are simulated — no real charges or emails/SMS. " +
        "Odoo order push is live — orders are sent to the connected Odoo.",
    );
    // The old banner claimed the Odoo push was a stub too.
    expect(s.message).not.toMatch(/ERP orders/);
  });

  it("local development: everything simulated", () => {
    const s = summariseProviderModes(modes("stub", "stub", "stub"));
    expect(s.message).toBe(
      "Test mode: Payments, Odoo order push and notifications are simulated — " +
        "no real charges, ERP orders or emails/SMS.",
    );
    expect(s.active).toEqual([]);
  });

  it("a single simulated provider uses the right verb", () => {
    expect(summariseProviderModes(modes("live", "live", "stub")).message).toMatch(
      /^Test mode: Odoo order push is simulated — no real ERP orders\. Payments are live/,
    );
  });

  it("nothing simulated: no notice", () => {
    const s = summariseProviderModes(modes("live", "live", "live"));
    expect(s.anySimulated).toBe(false);
    expect(s.simulated).toEqual([]);
  });

  it("an unrecognised mode is reported by name, not guessed", () => {
    expect(summariseProviderModes(modes("stub", "stub", "sandbox")).message).toContain(
      "Odoo order push mode: sandbox.",
    );
  });
});
