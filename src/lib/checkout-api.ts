/**
 * Typed client for the order-creation API (/api/v1/orders).
 *
 * Mirrors catalogue-api.ts's shape: this is the one place that knows the backend's
 * wire shape (snake_case Pydantic models). The backend recomputes every price from
 * PostgreSQL — this client never sends a unit price, tax, or total, only what the
 * customer wants to buy and where it's going.
 */
import type { CartItem, Address, Order, OrderStatus } from "@/lib/store";

const API_BASE_URL =
  (import.meta.env.VITE_API_BASE_URL as string | undefined) ?? "http://localhost:8000";

export class CheckoutApiError extends Error {
  status?: number;
  code?: string;
  constructor(message: string, status?: number, code?: string) {
    super(message);
    this.name = "CheckoutApiError";
    this.status = status;
    this.code = code;
  }
}

export type OrderItemAttributeOut = {
  code: string;
  name_en: string;
  value_label_en: string;
};

export type OrderItemOut = {
  id: string;
  sku: string;
  name_en: string;
  attributes: OrderItemAttributeOut[];
  inscription: string | null;
  quantity: number;
  unit_price: string;
  line_total: string;
};

export type OrderStatusEventOut = {
  status: string;
  occurred_at: string;
};

export type OrderOut = {
  id: string;
  order_number: string;
  status: string;
  currency: string;
  subtotal_amount: string;
  discount_amount: string;
  promo_code: string | null;
  tax_amount: string;
  delivery_fee_amount: string;
  total_amount: string;
  is_gift: boolean;
  recipient_name: string;
  recipient_phone: string;
  delivery_area: string | null;
  delivery_address: string | null;
  delivery_address_extra: string | null;
  delivery_date: string | null;
  delivery_time: string | null;
  tracking_token: string;
  payment_method: string | null;
  items: OrderItemOut[];
  status_history: OrderStatusEventOut[];
  created_at: string;
};

export async function createOrder(input: {
  cart: CartItem[];
  promoCode: string | null;
  customerName: string;
  customerEmail?: string;
  customerPhone: string;
  address: Address | null;
}): Promise<OrderOut> {
  const payload = {
    items: input.cart.map((item) => ({
      product_slug: item.productId,
      quantity: item.qty,
      attributes: item.attributes ?? {},
      inscription: item.inscription ?? null,
    })),
    promo_code: input.promoCode,
    customer: {
      name: input.customerName,
      email: input.customerEmail ?? null,
      phone: input.customerPhone,
    },
    delivery: {
      is_gift: input.address?.isGift ?? false,
      identity_secret: input.address?.identitySecret ?? false,
      recipient_name: input.address?.name ?? input.customerName,
      recipient_phone: input.address?.phone ?? input.customerPhone,
      area: input.address?.area ?? null,
      address: input.address?.address ?? null,
      address_extra: input.address?.extra ?? null,
      delivery_date: input.address?.deliveryDate ?? null,
      delivery_time: input.address?.deliveryTime ?? null,
    },
  };

  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}/api/v1/orders`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
  } catch {
    throw new CheckoutApiError(
      "Could not reach the order service. Check your connection and try again.",
    );
  }

  const body = await response.json().catch(() => null);
  if (!response.ok) {
    const message = body?.error?.message ?? `Order request failed (${response.status}).`;
    throw new CheckoutApiError(message, response.status, body?.error?.code);
  }
  return body as OrderOut;
}

export async function payOrder(orderId: string, methodLabel: string): Promise<OrderOut> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}/api/v1/orders/${orderId}/pay`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ method_label: methodLabel }),
    });
  } catch {
    throw new CheckoutApiError(
      "Could not reach the payment service. Check your connection and try again.",
    );
  }

  const body = await response.json().catch(() => null);
  if (!response.ok) {
    const message = body?.error?.message ?? `Payment request failed (${response.status}).`;
    throw new CheckoutApiError(message, response.status, body?.error?.code);
  }
  return body as OrderOut;
}

export async function fetchOrder(orderId: string): Promise<OrderOut> {
  const response = await fetch(`${API_BASE_URL}/api/v1/orders/${orderId}`);
  const body = await response.json().catch(() => null);
  if (!response.ok) {
    const message = body?.error?.message ?? `Order lookup failed (${response.status}).`;
    throw new CheckoutApiError(message, response.status, body?.error?.code);
  }
  return body as OrderOut;
}

export async function fetchOrderByTrackingToken(trackingToken: string): Promise<OrderOut> {
  const response = await fetch(
    `${API_BASE_URL}/api/v1/orders/by-tracking-token/${encodeURIComponent(trackingToken)}`,
  );
  const body = await response.json().catch(() => null);
  if (!response.ok) {
    const message = body?.error?.message ?? `Order lookup failed (${response.status}).`;
    throw new CheckoutApiError(message, response.status, body?.error?.code);
  }
  return body as OrderOut;
}

// The backend's 5-status model (pending_payment/paid/processing/delivered/cancelled)
// collapses onto the Storefront's existing 3-stage display (Processing/Paid/
// Delivered — src/lib/store.ts) rather than the other way around, since redesigning
// OrderStatusTimeline's visual model is out of scope here. "processing" isn't set by
// anything yet (no fulfilment system exists this sprint) — it maps alongside "paid"
// so the mapping is total and won't silently mis-render if that ever changes.
function mapOrderStatus(status: string): OrderStatus {
  switch (status) {
    case "paid":
    case "processing":
      return "Paid";
    case "delivered":
      return "Delivered";
    case "pending_payment":
    case "cancelled":
    default:
      return "Processing";
  }
}

/** Maps an authoritative backend order onto the Storefront's existing local `Order`
 * shape, so the already-built confirmation/tracking UI (success.tsx, track.$id.tsx,
 * OrderStatusTimeline) can render it completely unchanged. Fields the backend doesn't
 * track yet (loyalty points earned, assigned courier) are simply omitted — both are
 * already-optional fields those pages render conditionally.
 */
export function toLocalOrder(order: OrderOut): Order {
  return {
    id: order.order_number,
    items: order.items.map((item) => ({
      productId: item.sku,
      name: item.name_en,
      qty: item.quantity,
      unitPrice: Number(item.unit_price),
      attributes:
        item.attributes.length > 0
          ? Object.fromEntries(item.attributes.map((a) => [a.code, a.value_label_en]))
          : undefined,
      inscription: item.inscription ?? undefined,
    })),
    subtotal: Number(order.subtotal_amount),
    discount: Number(order.discount_amount),
    tax: Number(order.tax_amount),
    deliveryFee: Number(order.delivery_fee_amount),
    total: Number(order.total_amount),
    address: {
      id: order.id,
      name: order.recipient_name,
      phone: order.recipient_phone,
      area: order.delivery_area ?? "",
      address: order.delivery_address ?? "",
      extra: order.delivery_address_extra ?? undefined,
      isGift: order.is_gift,
      deliveryDate: order.delivery_date ?? undefined,
      deliveryTime: order.delivery_time ?? undefined,
    },
    method: order.payment_method ?? "—",
    createdAt: Date.parse(order.created_at),
    status: mapOrderStatus(order.status),
    statusHistory: order.status_history.map((event) => ({
      status: mapOrderStatus(event.status),
      at: Date.parse(event.occurred_at),
    })),
    trackingToken: order.tracking_token,
  };
}
