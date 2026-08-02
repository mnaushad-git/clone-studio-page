import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
  CheckoutApiError,
  createOrder,
  payOrder,
  toLocalOrder,
  type OrderOut,
} from "@/lib/checkout-api";
import type { CartItem, Address } from "@/lib/store";

const cartItem: CartItem = {
  lineId: "swiss-frosting||",
  productId: "swiss-frosting",
  qty: 2,
  unitPrice: 12.5,
};

const address: Address = {
  id: "addr-1",
  name: "Sara M.",
  phone: "+966 500000000",
  area: "Al Olaya",
  address: "123 Test Street",
  isDefault: true,
};

function makeOrderOut(overrides: Partial<OrderOut> = {}): OrderOut {
  return {
    id: "order-1",
    order_number: "TB-ABC123",
    status: "pending_payment",
    currency: "SAR",
    subtotal_amount: "25.00",
    discount_amount: "0.00",
    promo_code: null,
    tax_amount: "1.19",
    delivery_fee_amount: "15.00",
    total_amount: "40.00",
    is_gift: false,
    recipient_name: "Sara M.",
    recipient_phone: "+966 500000000",
    delivery_area: "Al Olaya",
    delivery_address: "123 Test Street",
    delivery_address_extra: null,
    delivery_date: "Tomorrow",
    delivery_time: "10:00am - 12:00pm",
    tracking_token: "tk-tbabc123",
    payment_method: null,
    items: [],
    status_history: [],
    created_at: "2026-07-29T00:00:00Z",
    ...overrides,
  };
}

describe("createOrder", () => {
  const originalFetch = global.fetch;

  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn());
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    global.fetch = originalFetch;
  });

  it("sends product slugs/quantities, never a client-side price, and returns the created order", async () => {
    const order = makeOrderOut();
    vi.mocked(fetch).mockResolvedValueOnce(new Response(JSON.stringify(order), { status: 200 }));

    const result = await createOrder({
      cart: [cartItem],
      promoCode: "WELCOME10",
      customerName: "Sara M.",
      customerPhone: "+966 500000000",
      address,
    });

    expect(result).toEqual(order);
    const [, init] = vi.mocked(fetch).mock.calls[0];
    const body = JSON.parse(init?.body as string);
    expect(body.items).toEqual([
      {
        product_slug: "swiss-frosting",
        quantity: 2,
        attributes: {},
        inscription: null,
      },
    ]);
    expect(body).not.toHaveProperty("unit_price");
    expect(body).not.toHaveProperty("total");
    expect(body.promo_code).toBe("WELCOME10");
  });

  it("throws a CheckoutApiError with the backend's error code on a non-2xx response", async () => {
    const errorBody = {
      error: { code: "VALIDATION_ERROR", message: "Minimum order is 30.00 SAR." },
    };
    vi.mocked(fetch).mockResolvedValueOnce(
      new Response(JSON.stringify(errorBody), { status: 422 }),
    );

    await expect(
      createOrder({
        cart: [cartItem],
        promoCode: null,
        customerName: "Sara M.",
        customerPhone: "+966 500000000",
        address,
      }),
    ).rejects.toMatchObject({ name: "CheckoutApiError", status: 422, code: "VALIDATION_ERROR" });
  });

  it("throws a CheckoutApiError when the network request itself fails", async () => {
    vi.mocked(fetch).mockRejectedValueOnce(new TypeError("network down"));

    await expect(
      createOrder({
        cart: [cartItem],
        promoCode: null,
        customerName: "Sara M.",
        customerPhone: "+966 500000000",
        address,
      }),
    ).rejects.toBeInstanceOf(CheckoutApiError);
  });

  it("falls back to the customer name/phone when there is no address (gift/edge case)", async () => {
    const order = makeOrderOut();
    vi.mocked(fetch).mockResolvedValueOnce(new Response(JSON.stringify(order), { status: 200 }));

    await createOrder({
      cart: [cartItem],
      promoCode: null,
      customerName: "Guest Buyer",
      customerPhone: "+966 511111111",
      address: null,
    });

    const [, init] = vi.mocked(fetch).mock.calls[0];
    const body = JSON.parse(init?.body as string);
    expect(body.delivery.recipient_name).toBe("Guest Buyer");
    expect(body.delivery.recipient_phone).toBe("+966 511111111");
  });
});

describe("payOrder", () => {
  const originalFetch = global.fetch;

  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn());
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    global.fetch = originalFetch;
  });

  it("posts the method label to /orders/{id}/pay and returns the updated (paid) order", async () => {
    const order = makeOrderOut({ status: "paid" });
    vi.mocked(fetch).mockResolvedValueOnce(new Response(JSON.stringify(order), { status: 200 }));

    const result = await payOrder("order-1", "Apple Pay");

    expect(result.status).toBe("paid");
    const [url, init] = vi.mocked(fetch).mock.calls[0];
    expect(url).toContain("/orders/order-1/pay");
    expect(JSON.parse(init?.body as string)).toEqual({ method_label: "Apple Pay" });
  });

  it("throws a CheckoutApiError with the backend's code when payment is declined", async () => {
    const errorBody = { error: { code: "PAYMENT_DECLINED", message: "Payment was declined." } };
    vi.mocked(fetch).mockResolvedValueOnce(
      new Response(JSON.stringify(errorBody), { status: 402 }),
    );

    await expect(payOrder("order-1", "Credit Card")).rejects.toMatchObject({
      name: "CheckoutApiError",
      status: 402,
      code: "PAYMENT_DECLINED",
    });
  });

  it("throws a CheckoutApiError when the network request itself fails", async () => {
    vi.mocked(fetch).mockRejectedValueOnce(new TypeError("network down"));

    await expect(payOrder("order-1", "Cash")).rejects.toBeInstanceOf(CheckoutApiError);
  });
});

describe("toLocalOrder", () => {
  it("maps money strings to numbers and never re-derives them client-side", () => {
    const local = toLocalOrder(makeOrderOut());

    expect(local.subtotal).toBe(25.0);
    expect(local.tax).toBe(1.19);
    expect(local.deliveryFee).toBe(15.0);
    expect(local.total).toBe(40.0);
  });

  it("uses the backend order_number as the local order id (both are the TB-XXXXXX customer-facing code)", () => {
    const local = toLocalOrder(makeOrderOut({ order_number: "TB-ZZZ999" }));

    expect(local.id).toBe("TB-ZZZ999");
  });

  it("maps items preserving attributes/inscription", () => {
    const local = toLocalOrder(
      makeOrderOut({
        items: [
          {
            id: "item-1",
            sku: "TB-CHO-009",
            name_en: "Berry Truffle",
            attributes: [
              { code: "size", name_en: "Size", value_label_en: "Large" },
              { code: "flavor", name_en: "Flavor", value_label_en: "Dark" },
            ],
            inscription: "Happy Birthday",
            quantity: 2,
            unit_price: "7.99",
            line_total: "15.98",
          },
        ],
      }),
    );

    expect(local.items).toEqual([
      {
        productId: "TB-CHO-009",
        name: "Berry Truffle",
        qty: 2,
        unitPrice: 7.99,
        attributes: { size: "Large", flavor: "Dark" },
        inscription: "Happy Birthday",
      },
    ]);
  });

  it.each([
    ["pending_payment", "Processing"],
    ["paid", "Paid"],
    ["processing", "Paid"],
    ["delivered", "Delivered"],
    ["cancelled", "Processing"],
  ] as const)("maps backend status %s to local status %s", (backendStatus, localStatus) => {
    const local = toLocalOrder(makeOrderOut({ status: backendStatus }));

    expect(local.status).toBe(localStatus);
  });

  it("maps status_history entries through the same status mapping", () => {
    const local = toLocalOrder(
      makeOrderOut({
        status_history: [
          { status: "pending_payment", occurred_at: "2026-07-30T09:00:00Z" },
          { status: "paid", occurred_at: "2026-07-30T09:05:00Z" },
        ],
      }),
    );

    expect(local.statusHistory).toEqual([
      { status: "Processing", at: Date.parse("2026-07-30T09:00:00Z") },
      { status: "Paid", at: Date.parse("2026-07-30T09:05:00Z") },
    ]);
  });

  it("falls back to an em dash for method when no payment has been recorded yet", () => {
    const local = toLocalOrder(makeOrderOut({ payment_method: null }));

    expect(local.method).toBe("—");
  });

  it("carries the payment method through when present", () => {
    const local = toLocalOrder(makeOrderOut({ payment_method: "Apple Pay" }));

    expect(local.method).toBe("Apple Pay");
  });

  it("builds an address from the recipient/delivery fields", () => {
    const local = toLocalOrder(
      makeOrderOut({
        is_gift: true,
        recipient_name: "Layla H.",
        recipient_phone: "+966 522222222",
        delivery_area: "Al Malaz",
        delivery_address: "456 Another Street",
        delivery_address_extra: "Apt 3",
        delivery_date: "Today",
        delivery_time: "2:00pm - 4:00pm",
      }),
    );

    expect(local.address).toEqual({
      id: "order-1",
      name: "Layla H.",
      phone: "+966 522222222",
      area: "Al Malaz",
      address: "456 Another Street",
      extra: "Apt 3",
      isGift: true,
      deliveryDate: "Today",
      deliveryTime: "2:00pm - 4:00pm",
    });
  });

  it("carries the tracking token through unchanged", () => {
    const local = toLocalOrder(makeOrderOut({ tracking_token: "tk-tbzzz999" }));

    expect(local.trackingToken).toBe("tk-tbzzz999");
  });
});
