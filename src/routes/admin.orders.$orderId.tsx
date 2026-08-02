import { createFileRoute, Link, useParams } from "@tanstack/react-router";
import { useState } from "react";
import { toast } from "sonner";
import {
  useAdminOrder,
  useUpdateOrderStatus,
  useRetryOdooSync,
  useRetryNotification,
} from "@/lib/admin-api";
import { Card, Badge, Button, Select, Modal, Field, Textarea } from "@/components/admin/ui";
import { formatAttributes } from "@/lib/format-variant-attributes";
import { ArrowLeft, RefreshCw, AlertTriangle } from "lucide-react";

export const Route = createFileRoute("/admin/orders/$orderId")({ component: OrderDetailPage });

const STATUS_TRANSITIONS: Record<string, string[]> = {
  pending_payment: ["cancelled"],
  paid: ["processing", "cancelled"],
  processing: ["delivered", "cancelled"],
  delivered: [],
  cancelled: [],
};

const STATUS_TONE: Record<string, "success" | "info" | "warn" | "danger" | "default"> = {
  pending_payment: "warn",
  paid: "info",
  processing: "info",
  delivered: "success",
  cancelled: "danger",
};

function money(v: string) {
  return `SAR ${v}`;
}

function OrderDetailPage() {
  const { orderId } = useParams({ from: "/admin/orders/$orderId" });
  const { data: order, isLoading, isError, error } = useAdminOrder(orderId);
  const updateStatus = useUpdateOrderStatus();
  const retrySync = useRetryOdooSync();
  const retryNotify = useRetryNotification();

  const [pendingStatus, setPendingStatus] = useState("");
  const [note, setNote] = useState("");
  const [modalOpen, setModalOpen] = useState(false);

  if (isLoading)
    return <div className="text-sm text-stone-500 py-10 text-center">Loading order…</div>;
  if (isError || !order) {
    return (
      <Card>
        <div className="text-sm text-red-600 py-6 text-center flex items-center gap-2 justify-center">
          <AlertTriangle className="h-4 w-4" /> {error?.message ?? "Order not found."}
        </div>
      </Card>
    );
  }

  const allowedNext = STATUS_TRANSITIONS[order.status] ?? [];

  function openStatusModal(next: string) {
    setPendingStatus(next);
    setNote("");
    setModalOpen(true);
  }

  async function confirmStatusChange() {
    if (pendingStatus === "cancelled" && !note.trim()) {
      toast.error("A reason is required to cancel an order.");
      return;
    }
    try {
      await updateStatus.mutateAsync({ orderId, status: pendingStatus, note: note || undefined });
      toast.success(`Order moved to ${pendingStatus}.`);
      setModalOpen(false);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to update status.");
    }
  }

  async function doRetrySync() {
    try {
      const res = await retrySync.mutateAsync(orderId);
      toast[res.worker_dispatched ? "success" : "warning"](res.message);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Retry failed.");
    }
  }

  async function doRetryNotify() {
    try {
      const res = await retryNotify.mutateAsync(orderId);
      toast[res.worker_dispatched ? "success" : "warning"](res.message);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Retry failed.");
    }
  }

  return (
    <div className="space-y-4">
      <Link
        to="/admin/orders"
        className="text-sm text-stone-500 hover:text-stone-800 flex items-center gap-1 w-fit"
      >
        <ArrowLeft className="h-4 w-4" /> Back to orders
      </Link>

      <Card
        title={`Order ${order.order_number}`}
        action={
          <div className="flex items-center gap-2">
            <Badge tone={STATUS_TONE[order.status] ?? "default"}>{order.status}</Badge>
            {allowedNext.length > 0 && (
              <Select
                value=""
                onChange={(e) => e.target.value && openStatusModal(e.target.value)}
                className="w-44"
              >
                <option value="">Change status…</option>
                {allowedNext.map((s) => (
                  <option key={s} value={s}>
                    {s}
                  </option>
                ))}
              </Select>
            )}
          </div>
        }
      >
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
          <div>
            <div className="text-xs text-stone-500 mb-1">Customer</div>
            <div className="font-medium">{order.customer.name}</div>
            <div className="text-stone-500">{order.customer.phone}</div>
            {order.customer.email && <div className="text-stone-500">{order.customer.email}</div>}
          </div>
          <div>
            <div className="text-xs text-stone-500 mb-1">Delivery</div>
            <div>
              {order.delivery.recipient_name} · {order.delivery.recipient_phone}
            </div>
            <div className="text-stone-500">
              {[order.delivery.area, order.delivery.address].filter(Boolean).join(", ") || "—"}
            </div>
            <div className="text-stone-500">
              {order.delivery.delivery_date} {order.delivery.delivery_time}
            </div>
          </div>
          <div>
            <div className="text-xs text-stone-500 mb-1">Totals</div>
            <div className="text-stone-500">Subtotal: {money(order.subtotal_amount)}</div>
            {order.promo_code && (
              <div className="text-stone-500">
                Discount ({order.promo_code}): -{money(order.discount_amount)}
              </div>
            )}
            <div className="text-stone-500">Delivery: {money(order.delivery_fee_amount)}</div>
            <div className="text-stone-500">Tax: {money(order.tax_amount)}</div>
            <div className="font-medium text-stone-900">Total: {money(order.total_amount)}</div>
          </div>
        </div>

        {order.cancellation_reason && (
          <div className="mt-4 rounded-lg bg-red-50 border border-red-200 px-4 py-2.5 text-sm text-red-800">
            <div className="font-medium">Cancelled: {order.cancellation_reason}</div>
            {order.refund_status === "pending" && (
              <div className="mt-1">
                Refund required — process manually with the payment provider (no automated refund
                integration).
              </div>
            )}
          </div>
        )}
      </Card>

      <Card title="Items">
        <div className="border rounded-lg divide-y">
          {order.items.map((it) => (
            <div key={it.id} className="flex items-center justify-between px-3 py-2 text-sm">
              <div>
                <div className="font-medium">{it.name_en}</div>
                <div className="text-xs text-stone-500">
                  {formatAttributes(it.attributes)} × {it.quantity}{" "}
                  {it.inscription && `· "${it.inscription}"`}
                </div>
              </div>
              <div>{money(it.line_total)}</div>
            </div>
          ))}
        </div>
      </Card>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <Card title="Payments">
          {order.payments.length === 0 ? (
            <div className="text-sm text-stone-500 text-center py-4">No payment attempts yet.</div>
          ) : (
            <div className="space-y-2">
              {order.payments.map((p) => (
                <div
                  key={p.id}
                  className="flex items-center justify-between text-sm border-b last:border-0 pb-2 last:pb-0"
                >
                  <div>
                    <div className="font-medium">
                      Attempt {p.attempt_number} · {p.method_label}
                    </div>
                    <div className="text-xs text-stone-500">
                      {p.provider} · {new Date(p.created_at).toLocaleString()}
                    </div>
                  </div>
                  <Badge tone={p.status === "succeeded" ? "success" : "danger"}>{p.status}</Badge>
                </div>
              ))}
            </div>
          )}
        </Card>

        <Card
          title="Odoo sync"
          action={
            <Button variant="outline" onClick={doRetrySync} disabled={retrySync.isPending}>
              <RefreshCw className="h-3.5 w-3.5" /> Retry
            </Button>
          }
        >
          <div className="text-sm space-y-1">
            <div>
              Status:{" "}
              <Badge
                tone={
                  order.odoo.sync_status === "synced"
                    ? "success"
                    : order.odoo.sync_status === "failed"
                      ? "danger"
                      : "default"
                }
              >
                {order.odoo.sync_status}
              </Badge>
            </div>
            {order.odoo.sale_order_id && (
              <div className="text-stone-500">Odoo sale order #{order.odoo.sale_order_id}</div>
            )}
            {order.odoo.last_synced_at && (
              <div className="text-stone-500">
                Last synced: {new Date(order.odoo.last_synced_at).toLocaleString()}
              </div>
            )}
          </div>
          {order.odoo.outbox_events.length > 0 && (
            <div className="mt-3 space-y-1 text-xs text-stone-500 border-t pt-2">
              {order.odoo.outbox_events.map((e) => (
                <div key={e.id} className="flex justify-between">
                  <span>
                    {e.status} · attempt {e.attempts}
                  </span>
                  {e.last_error && (
                    <span className="text-red-600 truncate max-w-[60%]">{e.last_error}</span>
                  )}
                </div>
              ))}
            </div>
          )}
        </Card>

        <Card
          title="Notifications"
          action={
            <Button variant="outline" onClick={doRetryNotify} disabled={retryNotify.isPending}>
              <RefreshCw className="h-3.5 w-3.5" /> Retry
            </Button>
          }
        >
          {order.notifications.length === 0 ? (
            <div className="text-sm text-stone-500 text-center py-4">
              No notifications sent yet.
            </div>
          ) : (
            <div className="space-y-2">
              {order.notifications.map((n) => (
                <div
                  key={n.id}
                  className="flex items-center justify-between text-sm border-b last:border-0 pb-2 last:pb-0"
                >
                  <div>
                    <div className="font-medium">
                      {n.channel} · {n.template}
                    </div>
                    <div className="text-xs text-stone-500">{n.recipient}</div>
                  </div>
                  <Badge tone={n.status === "sent" ? "success" : "danger"}>{n.status}</Badge>
                </div>
              ))}
            </div>
          )}
        </Card>

        <Card title="Status history">
          <div className="space-y-2 text-sm">
            {order.status_history.map((e, i) => (
              <div
                key={i}
                className="flex items-center justify-between border-b last:border-0 pb-2 last:pb-0"
              >
                <div>
                  <Badge tone={STATUS_TONE[e.status] ?? "default"}>{e.status}</Badge>
                  {e.note && <div className="text-xs text-stone-500 mt-1">{e.note}</div>}
                </div>
                <span className="text-xs text-stone-500">
                  {new Date(e.occurred_at).toLocaleString()}
                </span>
              </div>
            ))}
          </div>
        </Card>
      </div>

      {order.audit_events.length > 0 && (
        <Card title="Related audit history">
          <div className="space-y-2 text-sm">
            {order.audit_events.map((a) => (
              <div
                key={a.id}
                className="flex items-center justify-between border-b last:border-0 pb-2 last:pb-0"
              >
                <div>
                  <div className="font-medium">{a.action}</div>
                  <div className="text-xs text-stone-500">
                    {a.admin_email}
                    {a.reason ? ` — ${a.reason}` : ""}
                  </div>
                </div>
                <span className="text-xs text-stone-500">
                  {new Date(a.created_at).toLocaleString()}
                </span>
              </div>
            ))}
          </div>
        </Card>
      )}

      <Modal
        open={modalOpen}
        onClose={() => setModalOpen(false)}
        title={`Move to ${pendingStatus}`}
        footer={
          <>
            <Button variant="ghost" onClick={() => setModalOpen(false)}>
              Cancel
            </Button>
            <Button
              variant={pendingStatus === "cancelled" ? "danger" : "primary"}
              onClick={confirmStatusChange}
              disabled={updateStatus.isPending}
            >
              Confirm
            </Button>
          </>
        }
      >
        <Field
          label={
            pendingStatus === "cancelled" ? "Cancellation reason (required)" : "Note (optional)"
          }
        >
          <Textarea value={note} onChange={(e) => setNote(e.target.value)} rows={3} />
        </Field>
      </Modal>
    </div>
  );
}
