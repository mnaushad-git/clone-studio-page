import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
  AdminApiError,
  login,
  logout,
  fetchMe,
  updateOrderStatus,
  fetchDeliveryOptions,
  type AdminUserOut,
} from "@/lib/admin-api";

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

const admin: AdminUserOut = {
  id: "admin-1",
  email: "owner@terrificbites.sa",
  full_name: "Store Owner",
  role: "SUPER_ADMIN",
  is_active: true,
  last_login_at: null,
};

describe("admin-api fetch layer", () => {
  const originalFetch = global.fetch;

  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn());
    document.cookie = "admin_csrf=; expires=Thu, 01 Jan 1970 00:00:00 GMT";
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    global.fetch = originalFetch;
  });

  it("login sends credentials and the email/password body, and returns the admin profile", async () => {
    vi.mocked(fetch).mockResolvedValueOnce(jsonResponse(admin));

    const result = await login("owner@terrificbites.sa", "hunter2");

    expect(result).toEqual(admin);
    const [url, init] = vi.mocked(fetch).mock.calls[0];
    expect(url).toContain("/api/v1/admin/auth/login");
    expect(init?.credentials).toBe("include");
    expect(JSON.parse(init?.body as string)).toEqual({
      email: "owner@terrificbites.sa",
      password: "hunter2",
    });
  });

  it("never includes a password field in any other request body", async () => {
    vi.mocked(fetch).mockResolvedValueOnce(jsonResponse({ ok: true }));

    await logout();

    const [, init] = vi.mocked(fetch).mock.calls[0];
    if (init?.body) {
      expect(JSON.parse(init.body as string)).not.toHaveProperty("password");
    } else {
      expect(init?.body).toBeUndefined();
    }
  });

  it("throws an AdminApiError with the backend's error code on a non-2xx response", async () => {
    vi.mocked(fetch).mockResolvedValueOnce(
      jsonResponse({ error: { code: "UNAUTHORIZED", message: "Invalid email or password." } }, 401),
    );

    await expect(login("x@example.com", "wrong")).rejects.toMatchObject({
      name: "AdminApiError",
      status: 401,
      code: "UNAUTHORIZED",
    });
  });

  it("throws an AdminApiError when the network request itself fails", async () => {
    vi.mocked(fetch).mockRejectedValueOnce(new TypeError("network down"));

    await expect(fetchMe()).rejects.toBeInstanceOf(AdminApiError);
  });

  it("echoes the admin_csrf cookie as X-CSRF-Token on a mutating request", async () => {
    document.cookie = "admin_csrf=test-csrf-token";
    vi.mocked(fetch).mockResolvedValueOnce(
      jsonResponse({
        id: "o1",
        order_number: "TB-1",
        status: "processing",
        payment_status: "paid",
        currency: "SAR",
        subtotal_amount: "10.00",
        discount_amount: "0.00",
        promo_code: null,
        discount_type: null,
        discount_value: null,
        tax_amount: "0.00",
        delivery_fee_amount: "0.00",
        total_amount: "10.00",
        cancellation_reason: null,
        refund_status: null,
        tracking_token: "tk-1",
        created_at: "2026-07-30T00:00:00Z",
        updated_at: "2026-07-30T00:00:00Z",
        customer: { name: "A", email: null, phone: "+9665" },
        delivery: {
          recipient_name: "A",
          recipient_phone: "+9665",
          area: null,
          address: null,
          address_extra: null,
          delivery_date: null,
          delivery_time: null,
          is_gift: false,
          identity_secret: false,
        },
        items: [],
        payments: [],
        odoo: {
          sync_status: "not_synced",
          sale_order_id: null,
          last_synced_at: null,
          outbox_events: [],
        },
        notifications: [],
        notification_outbox_events: [],
        status_history: [],
        audit_events: [],
      }),
    );

    await updateOrderStatus("o1", "processing");

    const [, init] = vi.mocked(fetch).mock.calls[0];
    const headers = new Headers(init?.headers);
    expect(headers.get("X-CSRF-Token")).toBe("test-csrf-token");
  });

  it("on a 401, attempts a silent refresh once and retries the original request", async () => {
    vi.mocked(fetch)
      .mockResolvedValueOnce(
        jsonResponse({ error: { code: "UNAUTHORIZED", message: "expired" } }, 401),
      )
      .mockResolvedValueOnce(jsonResponse(admin)) // refresh succeeds
      .mockResolvedValueOnce(jsonResponse(admin)); // retried /me succeeds

    const result = await fetchMe();

    expect(result).toEqual(admin);
    expect(vi.mocked(fetch)).toHaveBeenCalledTimes(3);
    expect(vi.mocked(fetch).mock.calls[1][0]).toContain("/api/v1/admin/auth/refresh");
  });

  it("propagates the 401 if the silent refresh itself fails", async () => {
    vi.mocked(fetch)
      .mockResolvedValueOnce(
        jsonResponse({ error: { code: "UNAUTHORIZED", message: "expired" } }, 401),
      )
      .mockResolvedValueOnce(jsonResponse({ error: { code: "UNAUTHORIZED" } }, 401)); // refresh fails

    await expect(fetchMe()).rejects.toMatchObject({ status: 401 });
    expect(vi.mocked(fetch)).toHaveBeenCalledTimes(2);
  });

  it("fetchDeliveryOptions is public — no credentials/CSRF required to succeed", async () => {
    vi.mocked(fetch).mockResolvedValueOnce(
      jsonResponse({
        delivery_enabled: true,
        flat_delivery_fee: "15.00",
        free_delivery_threshold: "0.00",
        minimum_order_amount: "30.00",
        same_day_delivery_enabled: false,
        same_day_cutoff_time: null,
        available_days: [0, 1, 2, 3, 4, 5, 6],
        slots: [],
      }),
    );

    const result = await fetchDeliveryOptions();

    expect(result.flat_delivery_fee).toBe("15.00");
    const [url] = vi.mocked(fetch).mock.calls[0];
    expect(url).toContain("/api/v1/checkout/delivery-options");
  });
});
