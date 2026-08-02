/**
 * Typed client for the Admin Portal API (/api/v1/admin/*), plus the public
 * checkout delivery-options endpoint the Storefront also reads from.
 *
 * Mirrors catalogue-api.ts/checkout-api.ts's conventions (wire DTOs in the backend's
 * exact snake_case shape, one apiFetch helper, a typed Error subclass) with one
 * addition neither of those needed: every admin request sends credentials (the
 * httpOnly session cookies) and every mutating request echoes the `admin_csrf`
 * cookie back as `X-CSRF-Token` (double-submit CSRF pattern — see
 * backend/app/core/security.py). On a 401 this client makes exactly one silent
 * attempt to refresh the session and replay the request before giving up, so a
 * near-expiry access token doesn't surface as a spurious error mid-session.
 */
import { useMutation, useQuery, useQueryClient, type UseQueryResult } from "@tanstack/react-query";

const API_BASE_URL =
  (import.meta.env.VITE_API_BASE_URL as string | undefined) ?? "http://localhost:8000";

export class AdminApiError extends Error {
  status?: number;
  code?: string;
  constructor(message: string, status?: number, code?: string) {
    super(message);
    this.name = "AdminApiError";
    this.status = status;
    this.code = code;
  }
}

// -- CSRF -----------------------------------------------------------------------------

function getCookie(name: string): string | null {
  const match = document.cookie.match(new RegExp(`(?:^|; )${name}=([^;]*)`));
  return match ? decodeURIComponent(match[1]) : null;
}

const MUTATING_METHODS = new Set(["POST", "PATCH", "PUT", "DELETE"]);

// -- fetch layer ------------------------------------------------------------------------

let refreshInFlight: Promise<boolean> | null = null;

async function attemptRefresh(): Promise<boolean> {
  if (!refreshInFlight) {
    refreshInFlight = fetch(`${API_BASE_URL}/api/v1/admin/auth/refresh`, {
      method: "POST",
      credentials: "include",
    })
      .then((r) => r.ok)
      .catch(() => false)
      .finally(() => {
        refreshInFlight = null;
      });
  }
  return refreshInFlight;
}

async function rawFetch(path: string, init: RequestInit): Promise<Response> {
  const method = (init.method ?? "GET").toUpperCase();
  const headers = new Headers(init.headers);
  if (init.body && !headers.has("Content-Type")) headers.set("Content-Type", "application/json");
  if (MUTATING_METHODS.has(method)) {
    const csrf = getCookie("admin_csrf");
    if (csrf) headers.set("X-CSRF-Token", csrf);
  }

  try {
    return await fetch(`${API_BASE_URL}${path}`, { ...init, headers, credentials: "include" });
  } catch {
    throw new AdminApiError(
      "Could not reach the admin service. Check your connection and try again.",
    );
  }
}

// Only login/refresh themselves must never trigger a refresh-and-retry (that would
// either retry a genuinely failed login as if it were an expired session, or recurse
// into refreshing-the-refresh-call) — every other admin endpoint, including /me,
// should transparently recover from an expired access token this way.
const NEVER_RETRY_PATHS = ["/api/v1/admin/auth/login", "/api/v1/admin/auth/refresh"];

async function apiFetch<T>(path: string, init: RequestInit = {}, _retried = false): Promise<T> {
  const response = await rawFetch(path, init);

  if (response.status === 401 && !_retried && !NEVER_RETRY_PATHS.includes(path)) {
    const refreshed = await attemptRefresh();
    if (refreshed) return apiFetch<T>(path, init, true);
  }

  if (response.status === 204) return undefined as T;

  const body = await response.json().catch(() => null);
  if (!response.ok) {
    const message = body?.error?.message ?? `Admin request failed (${response.status}).`;
    throw new AdminApiError(message, response.status, body?.error?.code);
  }
  return body as T;
}

function buildQuery(params?: Record<string, string | number | boolean | undefined | null>): string {
  if (!params) return "";
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== null && value !== "") search.set(key, String(value));
  }
  const qs = search.toString();
  return qs ? `?${qs}` : "";
}

// -- auth -----------------------------------------------------------------------------

export type AdminUserOut = {
  id: string;
  email: string;
  full_name: string;
  role: "SUPER_ADMIN" | "OPERATIONS_ADMIN" | "CATALOGUE_ADMIN" | "SUPPORT_ADMIN";
  is_active: boolean;
  last_login_at: string | null;
};

export function login(email: string, password: string): Promise<AdminUserOut> {
  return apiFetch<AdminUserOut>("/api/v1/admin/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
}

export function logout(): Promise<{ ok: boolean }> {
  return apiFetch<{ ok: boolean }>("/api/v1/admin/auth/logout", { method: "POST" });
}

export function fetchMe(): Promise<AdminUserOut> {
  return apiFetch<AdminUserOut>("/api/v1/admin/auth/me");
}

export function changePassword(
  currentPassword: string,
  newPassword: string,
): Promise<{ ok: boolean }> {
  return apiFetch<{ ok: boolean }>("/api/v1/admin/auth/change-password", {
    method: "POST",
    body: JSON.stringify({ current_password: currentPassword, new_password: newPassword }),
  });
}

export function useAdminMe(enabled = true): UseQueryResult<AdminUserOut, AdminApiError> {
  return useQuery({
    queryKey: ["admin", "me"],
    queryFn: fetchMe,
    enabled,
    retry: false,
  });
}

// -- dashboard --------------------------------------------------------------------------

export type DashboardSummaryOut = {
  orders_today: number;
  revenue_today: string;
  paid_orders_today: number;
  pending_payment_orders_today: number;
  awaiting_odoo_sync: number;
  failed_odoo_sync: number;
  failed_notifications: number;
  stuck_orders: number;
  orders_requiring_attention: number;
};

export type DashboardRecentOrderOut = {
  id: string;
  order_number: string;
  customer_name: string;
  customer_phone: string;
  total_amount: string;
  payment_status: string;
  status: string;
  odoo_sync_status: string;
  created_at: string;
};

export type DashboardAlertOut = { type: string; message: string; count: number };

export function fetchDashboardSummary(): Promise<DashboardSummaryOut> {
  return apiFetch<DashboardSummaryOut>("/api/v1/admin/dashboard/summary");
}
export function fetchDashboardRecentOrders(): Promise<DashboardRecentOrderOut[]> {
  return apiFetch<DashboardRecentOrderOut[]>("/api/v1/admin/dashboard/recent-orders");
}
export function fetchDashboardAlerts(): Promise<DashboardAlertOut[]> {
  return apiFetch<DashboardAlertOut[]>("/api/v1/admin/dashboard/operational-alerts");
}

export function useDashboardSummary(): UseQueryResult<DashboardSummaryOut, AdminApiError> {
  return useQuery({ queryKey: ["admin", "dashboard", "summary"], queryFn: fetchDashboardSummary });
}
export function useDashboardRecentOrders(): UseQueryResult<
  DashboardRecentOrderOut[],
  AdminApiError
> {
  return useQuery({
    queryKey: ["admin", "dashboard", "recent-orders"],
    queryFn: fetchDashboardRecentOrders,
  });
}
export function useDashboardAlerts(): UseQueryResult<DashboardAlertOut[], AdminApiError> {
  return useQuery({ queryKey: ["admin", "dashboard", "alerts"], queryFn: fetchDashboardAlerts });
}

// -- orders ---------------------------------------------------------------------------

export type AdminOrderListItemOut = {
  id: string;
  order_number: string;
  created_at: string;
  customer_name: string;
  customer_phone: string;
  delivery_date: string | null;
  delivery_time: string | null;
  item_count: number;
  items_summary: string[];
  subtotal_amount: string;
  delivery_fee_amount: string;
  discount_amount: string;
  total_amount: string;
  payment_status: string;
  status: string;
  odoo_sync_status: string;
  notification_status: string;
};

export type AdminOrderListOut = {
  items: AdminOrderListItemOut[];
  total: number;
  limit: number;
  offset: number;
};

export type AdminOrderFilters = {
  order_number?: string;
  customer_name?: string;
  customer_phone?: string;
  customer_email?: string;
  status?: string;
  payment_status?: string;
  odoo_sync_status?: string;
  notification_status?: string;
  delivery_date?: string;
  created_from?: string;
  created_to?: string;
  sort?: "newest" | "oldest" | "total_desc" | "total_asc" | "delivery_date";
  limit?: number;
  offset?: number;
};

export type AdminOrderItemAttributeOut = {
  code: string;
  name_en: string;
  value_label_en: string;
};

export type AdminOrderItemOut = {
  id: string;
  sku: string;
  name_en: string;
  attributes: AdminOrderItemAttributeOut[];
  inscription: string | null;
  quantity: number;
  unit_price: string;
  line_total: string;
};

export type AdminOrderPaymentOut = {
  id: string;
  attempt_number: number;
  provider: string;
  method_label: string;
  amount: string;
  currency: string;
  status: string;
  provider_reference: string | null;
  created_at: string;
  updated_at: string;
};

export type AdminOrderNotificationOut = {
  id: string;
  channel: string;
  template: string;
  recipient: string;
  provider: string;
  status: string;
  provider_reference: string | null;
  created_at: string;
};

export type AdminOrderOutboxEventOut = {
  id: string;
  event_type: string;
  status: string;
  attempts: number;
  last_error: string | null;
  processed_at: string | null;
  created_at: string;
};

export type AdminOrderStatusEventOut = { status: string; note: string | null; occurred_at: string };
export type AdminAuditEventBriefOut = {
  id: string;
  admin_email: string;
  action: string;
  reason: string | null;
  created_at: string;
};

export type AdminOrderDetailOut = {
  id: string;
  order_number: string;
  status: string;
  payment_status: string;
  currency: string;
  subtotal_amount: string;
  discount_amount: string;
  promo_code: string | null;
  discount_type: string | null;
  discount_value: string | null;
  tax_amount: string;
  delivery_fee_amount: string;
  total_amount: string;
  cancellation_reason: string | null;
  refund_status: string | null;
  tracking_token: string;
  created_at: string;
  updated_at: string;
  customer: { name: string; email: string | null; phone: string };
  delivery: {
    recipient_name: string;
    recipient_phone: string;
    area: string | null;
    address: string | null;
    address_extra: string | null;
    delivery_date: string | null;
    delivery_time: string | null;
    is_gift: boolean;
    identity_secret: boolean;
  };
  items: AdminOrderItemOut[];
  payments: AdminOrderPaymentOut[];
  odoo: {
    sync_status: string;
    sale_order_id: number | null;
    last_synced_at: string | null;
    outbox_events: AdminOrderOutboxEventOut[];
  };
  notifications: AdminOrderNotificationOut[];
  notification_outbox_events: AdminOrderOutboxEventOut[];
  status_history: AdminOrderStatusEventOut[];
  audit_events: AdminAuditEventBriefOut[];
};

export type AdminRetryResponseOut = {
  queued: boolean;
  worker_dispatched: boolean;
  message: string;
};

export function fetchAdminOrders(filters: AdminOrderFilters = {}): Promise<AdminOrderListOut> {
  return apiFetch<AdminOrderListOut>(`/api/v1/admin/orders${buildQuery(filters)}`);
}
export function fetchAdminOrder(orderId: string): Promise<AdminOrderDetailOut> {
  return apiFetch<AdminOrderDetailOut>(`/api/v1/admin/orders/${orderId}`);
}
export function updateOrderStatus(
  orderId: string,
  status: string,
  note?: string,
): Promise<AdminOrderDetailOut> {
  return apiFetch<AdminOrderDetailOut>(`/api/v1/admin/orders/${orderId}/status`, {
    method: "PATCH",
    body: JSON.stringify({ status, note: note ?? null }),
  });
}
export function retryOdooSync(orderId: string): Promise<AdminRetryResponseOut> {
  return apiFetch<AdminRetryResponseOut>(`/api/v1/admin/orders/${orderId}/retry-odoo-sync`, {
    method: "POST",
  });
}
export function retryNotification(orderId: string): Promise<AdminRetryResponseOut> {
  return apiFetch<AdminRetryResponseOut>(`/api/v1/admin/orders/${orderId}/retry-notification`, {
    method: "POST",
  });
}

export function useAdminOrders(
  filters: AdminOrderFilters = {},
): UseQueryResult<AdminOrderListOut, AdminApiError> {
  return useQuery({
    queryKey: ["admin", "orders", filters],
    queryFn: () => fetchAdminOrders(filters),
  });
}
export function useAdminOrder(
  orderId: string | undefined,
): UseQueryResult<AdminOrderDetailOut, AdminApiError> {
  return useQuery({
    queryKey: ["admin", "order", orderId],
    queryFn: () => fetchAdminOrder(orderId as string),
    enabled: Boolean(orderId),
  });
}

export function useUpdateOrderStatus() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ orderId, status, note }: { orderId: string; status: string; note?: string }) =>
      updateOrderStatus(orderId, status, note),
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({ queryKey: ["admin", "order", variables.orderId] });
      queryClient.invalidateQueries({ queryKey: ["admin", "orders"] });
      queryClient.invalidateQueries({ queryKey: ["admin", "dashboard"] });
    },
  });
}

export function useRetryOdooSync() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (orderId: string) => retryOdooSync(orderId),
    onSuccess: (_data, orderId) => {
      queryClient.invalidateQueries({ queryKey: ["admin", "order", orderId] });
      queryClient.invalidateQueries({ queryKey: ["admin", "dashboard"] });
    },
  });
}

export function useRetryNotification() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (orderId: string) => retryNotification(orderId),
    onSuccess: (_data, orderId) => {
      queryClient.invalidateQueries({ queryKey: ["admin", "order", orderId] });
      queryClient.invalidateQueries({ queryKey: ["admin", "dashboard"] });
    },
  });
}

// -- products ---------------------------------------------------------------------------

export type AdminProductListItemOut = {
  id: string;
  sku: string;
  name_en: string;
  category_name: string;
  price: string | null;
  currency: string | null;
  primary_image_url: string | null;
  active: boolean;
  featured: boolean;
  is_bestseller: boolean | null;
  is_new: boolean;
  odoo_mapped: boolean;
  last_synced_at: string | null;
};

export type AdminProductListOut = {
  items: AdminProductListItemOut[];
  total: number;
  limit: number;
  offset: number;
};

export type AdminProductFilters = {
  category?: string;
  active?: boolean;
  featured?: boolean;
  bestseller?: boolean;
  new?: boolean;
  search?: string;
  limit?: number;
  offset?: number;
};

export type AdminProductVariantOut = {
  id: string;
  sku: string;
  name_en: string;
  is_default: boolean;
  price: string | null;
  currency: string | null;
};

export type AdminProductMerchandisingOut = {
  storefront_visible: boolean;
  featured: boolean;
  is_new: boolean;
  is_bestseller: boolean | null;
  display_order: number;
  badge_en: string | null;
  badge_ar: string | null;
};

export type AdminProductDetailOut = {
  id: string;
  sku: string;
  slug: string;
  name_en: string;
  name_ar: string | null;
  category_name: string;
  active: boolean;
  sellable: boolean;
  odoo_product_template_id: number | null;
  last_synced_at: string | null;
  variants: AdminProductVariantOut[];
  image_urls: string[];
  merchandising: AdminProductMerchandisingOut;
  moment_names: string[];
  recipient_names: string[];
};

export type AdminProductMerchandisingUpdate = Partial<{
  featured: boolean;
  is_new: boolean;
  is_bestseller: boolean | null;
  storefront_visible: boolean;
  display_order: number;
  badge_en: string | null;
  badge_ar: string | null;
}>;

export function fetchAdminProducts(
  filters: AdminProductFilters = {},
): Promise<AdminProductListOut> {
  return apiFetch<AdminProductListOut>(`/api/v1/admin/products${buildQuery(filters)}`);
}
export function fetchAdminProduct(productId: string): Promise<AdminProductDetailOut> {
  return apiFetch<AdminProductDetailOut>(`/api/v1/admin/products/${productId}`);
}
export function updateProductMerchandising(
  productId: string,
  updates: AdminProductMerchandisingUpdate,
): Promise<AdminProductDetailOut> {
  return apiFetch<AdminProductDetailOut>(`/api/v1/admin/products/${productId}/merchandising`, {
    method: "PATCH",
    body: JSON.stringify(updates),
  });
}

export function useAdminProducts(
  filters: AdminProductFilters = {},
): UseQueryResult<AdminProductListOut, AdminApiError> {
  return useQuery({
    queryKey: ["admin", "products", filters],
    queryFn: () => fetchAdminProducts(filters),
  });
}
export function useAdminProduct(
  productId: string | undefined,
): UseQueryResult<AdminProductDetailOut, AdminApiError> {
  return useQuery({
    queryKey: ["admin", "product", productId],
    queryFn: () => fetchAdminProduct(productId as string),
    enabled: Boolean(productId),
  });
}
export function useUpdateProductMerchandising() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      productId,
      updates,
    }: {
      productId: string;
      updates: AdminProductMerchandisingUpdate;
    }) => updateProductMerchandising(productId, updates),
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({ queryKey: ["admin", "products"] });
      queryClient.invalidateQueries({ queryKey: ["admin", "product", variables.productId] });
    },
  });
}

// -- catalogue sync (Odoo -> PostgreSQL product pull) ------------------------------------

export type AdminSyncRunOut = {
  id: string;
  trigger: "SCHEDULED" | "MANUAL";
  status: "PENDING" | "RUNNING" | "SUCCEEDED" | "FAILED" | "PARTIALLY_COMPLETED";
  full_resync: boolean;
  started_at: string;
  completed_at: string | null;
  initiated_by: string;
  total_created: number;
  total_updated: number;
  total_skipped: number;
  total_failed: number;
  counts_by_entity: Record<string, { created: number; updated: number; skipped: number; failed: number }> | null;
  error_summary: string | null;
};

export type AdminSyncRunListOut = {
  items: AdminSyncRunOut[];
  total: number;
  limit: number;
  offset: number;
};

export type AdminSyncTriggerResponseOut = {
  queued: boolean;
  worker_dispatched: boolean;
  message: string;
};

export function fetchSyncRuns(limit = 20): Promise<AdminSyncRunListOut> {
  return apiFetch<AdminSyncRunListOut>(`/api/v1/admin/catalogue-sync/runs${buildQuery({ limit })}`);
}
export function triggerCatalogueSync(fullResync = false): Promise<AdminSyncTriggerResponseOut> {
  return apiFetch<AdminSyncTriggerResponseOut>("/api/v1/admin/catalogue-sync/trigger", {
    method: "POST",
    body: JSON.stringify({ full_resync: fullResync }),
  });
}

export function useSyncRuns(limit = 20): UseQueryResult<AdminSyncRunListOut, AdminApiError> {
  return useQuery({
    queryKey: ["admin", "catalogue-sync", "runs", limit],
    queryFn: () => fetchSyncRuns(limit),
  });
}
export function useTriggerCatalogueSync() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (fullResync: boolean) => triggerCatalogueSync(fullResync),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin", "catalogue-sync"] });
      queryClient.invalidateQueries({ queryKey: ["admin", "products"] });
    },
  });
}

// -- promo codes ------------------------------------------------------------------------

export type PromoCodeOut = {
  id: string;
  code: string;
  description: string | null;
  discount_type: "PERCENTAGE" | "FIXED_AMOUNT";
  discount_value: string;
  minimum_order_amount: string;
  maximum_discount_amount: string | null;
  valid_from: string | null;
  valid_until: string | null;
  usage_limit: number | null;
  usage_count: number;
  per_customer_limit: number | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
};

export type PromoCodeListOut = {
  items: PromoCodeOut[];
  total: number;
  limit: number;
  offset: number;
};

export type PromoCodeInput = {
  code?: string;
  description?: string | null;
  discount_type?: "PERCENTAGE" | "FIXED_AMOUNT";
  discount_value?: number;
  minimum_order_amount?: number;
  maximum_discount_amount?: number | null;
  valid_from?: string | null;
  valid_until?: string | null;
  usage_limit?: number | null;
  per_customer_limit?: number | null;
  is_active?: boolean;
};

export function fetchPromoCodes(
  params: { is_active?: boolean; search?: string; limit?: number; offset?: number } = {},
): Promise<PromoCodeListOut> {
  return apiFetch<PromoCodeListOut>(`/api/v1/admin/promo-codes${buildQuery(params)}`);
}
export function createPromoCode(input: PromoCodeInput): Promise<PromoCodeOut> {
  return apiFetch<PromoCodeOut>("/api/v1/admin/promo-codes", {
    method: "POST",
    body: JSON.stringify(input),
  });
}
export function updatePromoCode(promoId: string, input: PromoCodeInput): Promise<PromoCodeOut> {
  return apiFetch<PromoCodeOut>(`/api/v1/admin/promo-codes/${promoId}`, {
    method: "PATCH",
    body: JSON.stringify(input),
  });
}
export function deletePromoCode(promoId: string): Promise<void> {
  return apiFetch<void>(`/api/v1/admin/promo-codes/${promoId}`, { method: "DELETE" });
}

export function usePromoCodes(
  params: { is_active?: boolean; search?: string } = {},
): UseQueryResult<PromoCodeListOut, AdminApiError> {
  return useQuery({
    queryKey: ["admin", "promo-codes", params],
    queryFn: () => fetchPromoCodes(params),
  });
}
export function useCreatePromoCode() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: PromoCodeInput) => createPromoCode(input),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["admin", "promo-codes"] }),
  });
}
export function useUpdatePromoCode() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ promoId, input }: { promoId: string; input: PromoCodeInput }) =>
      updatePromoCode(promoId, input),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["admin", "promo-codes"] }),
  });
}
export function useDeletePromoCode() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (promoId: string) => deletePromoCode(promoId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["admin", "promo-codes"] }),
  });
}

// -- delivery settings + slots ------------------------------------------------------------

export type DeliverySettingsOut = {
  delivery_enabled: boolean;
  flat_delivery_fee: string;
  free_delivery_threshold: string;
  minimum_order_amount: string;
  same_day_delivery_enabled: boolean;
  same_day_cutoff_time: string | null;
  available_days: number[];
};

export type DeliverySettingsInput = Partial<{
  delivery_enabled: boolean;
  flat_delivery_fee: number;
  free_delivery_threshold: number;
  minimum_order_amount: number;
  same_day_delivery_enabled: boolean;
  same_day_cutoff_time: string | null;
  available_days: number[];
}>;

export type DeliverySlotOut = {
  id: string;
  label: string;
  start_time: string;
  end_time: string;
  max_orders_per_slot: number | null;
  active: boolean;
  display_order: number;
};

export type DeliverySlotInput = Partial<{
  label: string;
  start_time: string;
  end_time: string;
  max_orders_per_slot: number | null;
  active: boolean;
  display_order: number;
}>;

export function fetchDeliverySettings(): Promise<DeliverySettingsOut> {
  return apiFetch<DeliverySettingsOut>("/api/v1/admin/delivery-settings");
}
export function updateDeliverySettings(input: DeliverySettingsInput): Promise<DeliverySettingsOut> {
  return apiFetch<DeliverySettingsOut>("/api/v1/admin/delivery-settings", {
    method: "PATCH",
    body: JSON.stringify(input),
  });
}
export function fetchDeliverySlots(): Promise<DeliverySlotOut[]> {
  return apiFetch<DeliverySlotOut[]>("/api/v1/admin/delivery-slots");
}
export function createDeliverySlot(input: DeliverySlotInput): Promise<DeliverySlotOut> {
  return apiFetch<DeliverySlotOut>("/api/v1/admin/delivery-slots", {
    method: "POST",
    body: JSON.stringify(input),
  });
}
export function updateDeliverySlot(
  slotId: string,
  input: DeliverySlotInput,
): Promise<DeliverySlotOut> {
  return apiFetch<DeliverySlotOut>(`/api/v1/admin/delivery-slots/${slotId}`, {
    method: "PATCH",
    body: JSON.stringify(input),
  });
}
export function deleteDeliverySlot(slotId: string): Promise<void> {
  return apiFetch<void>(`/api/v1/admin/delivery-slots/${slotId}`, { method: "DELETE" });
}

export function useDeliverySettings(): UseQueryResult<DeliverySettingsOut, AdminApiError> {
  return useQuery({ queryKey: ["admin", "delivery-settings"], queryFn: fetchDeliverySettings });
}
export function useDeliverySlots(): UseQueryResult<DeliverySlotOut[], AdminApiError> {
  return useQuery({ queryKey: ["admin", "delivery-slots"], queryFn: fetchDeliverySlots });
}
export function useUpdateDeliverySettings() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: DeliverySettingsInput) => updateDeliverySettings(input),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin", "delivery-settings"] });
      queryClient.invalidateQueries({ queryKey: ["checkout", "delivery-options"] });
    },
  });
}
export function useCreateDeliverySlot() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: DeliverySlotInput) => createDeliverySlot(input),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin", "delivery-slots"] });
      queryClient.invalidateQueries({ queryKey: ["checkout", "delivery-options"] });
    },
  });
}
export function useUpdateDeliverySlot() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ slotId, input }: { slotId: string; input: DeliverySlotInput }) =>
      updateDeliverySlot(slotId, input),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin", "delivery-slots"] });
      queryClient.invalidateQueries({ queryKey: ["checkout", "delivery-options"] });
    },
  });
}
export function useDeleteDeliverySlot() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (slotId: string) => deleteDeliverySlot(slotId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin", "delivery-slots"] });
      queryClient.invalidateQueries({ queryKey: ["checkout", "delivery-options"] });
    },
  });
}

// -- audit ------------------------------------------------------------------------------

export type AdminAuditEventOut = {
  id: string;
  admin_user_id: string | null;
  admin_email: string;
  action: string;
  entity_type: string;
  entity_id: string | null;
  before_state: Record<string, unknown> | null;
  after_state: Record<string, unknown> | null;
  reason: string | null;
  correlation_id: string | null;
  ip_address: string | null;
  created_at: string;
};

export type AdminAuditEventListOut = {
  items: AdminAuditEventOut[];
  total: number;
  limit: number;
  offset: number;
};

export type AdminAuditFilters = {
  admin_user_id?: string;
  action?: string;
  entity_type?: string;
  entity_id?: string;
  search?: string;
  date_from?: string;
  date_to?: string;
  limit?: number;
  offset?: number;
};

export function fetchAuditEvents(filters: AdminAuditFilters = {}): Promise<AdminAuditEventListOut> {
  return apiFetch<AdminAuditEventListOut>(`/api/v1/admin/audit-events${buildQuery(filters)}`);
}
export function useAuditEvents(
  filters: AdminAuditFilters = {},
): UseQueryResult<AdminAuditEventListOut, AdminApiError> {
  return useQuery({
    queryKey: ["admin", "audit-events", filters],
    queryFn: () => fetchAuditEvents(filters),
  });
}

// -- system status ----------------------------------------------------------------------

export type SystemStatusOut = {
  database: "up" | "down";
  redis: "up" | "down";
  celery_worker: "up" | "down";
  celery_beat: "up" | "down" | "unknown";
  odoo: "configured" | "not_configured";
  payment_provider_mode: string;
  notification_provider_mode: string;
  odoo_order_push_mode: string;
  stub_providers_active: boolean;
};

export function fetchSystemStatus(): Promise<SystemStatusOut> {
  return apiFetch<SystemStatusOut>("/api/v1/admin/system/status");
}
export function useSystemStatus(enabled = true): UseQueryResult<SystemStatusOut, AdminApiError> {
  return useQuery({
    queryKey: ["admin", "system-status"],
    queryFn: fetchSystemStatus,
    enabled,
    refetchInterval: 60_000,
  });
}

// -- public checkout delivery-options (no admin auth; Storefront-facing) ----------------

export type DeliveryOptionsOut = {
  delivery_enabled: boolean;
  flat_delivery_fee: string;
  free_delivery_threshold: string;
  minimum_order_amount: string;
  same_day_delivery_enabled: boolean;
  same_day_cutoff_time: string | null;
  available_days: number[];
  slots: DeliverySlotOut[];
};

export async function fetchDeliveryOptions(): Promise<DeliveryOptionsOut> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}/api/v1/checkout/delivery-options`);
  } catch {
    throw new AdminApiError(
      "Could not reach the delivery service. Check your connection and try again.",
    );
  }
  const body = await response.json().catch(() => null);
  if (!response.ok) {
    throw new AdminApiError(
      body?.error?.message ?? `Delivery options request failed (${response.status}).`,
      response.status,
    );
  }
  return body as DeliveryOptionsOut;
}

export function useDeliveryOptions(): UseQueryResult<DeliveryOptionsOut, AdminApiError> {
  return useQuery({ queryKey: ["checkout", "delivery-options"], queryFn: fetchDeliveryOptions });
}
