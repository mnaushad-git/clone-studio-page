import { createFileRoute, Link } from "@tanstack/react-router";
import { useState } from "react";
import { useAdminOrders, type AdminOrderFilters } from "@/lib/admin-api";
import { Card, Badge, Select, Input, EmptyState, Button } from "@/components/admin/ui";
import { Eye, ChevronLeft, ChevronRight } from "lucide-react";

export const Route = createFileRoute("/admin/orders")({ component: OrdersPage });

const STATUSES = ["pending_payment", "paid", "processing", "delivered", "cancelled"];
const STATUS_TONE: Record<string, "success" | "info" | "warn" | "danger" | "default"> = {
  pending_payment: "warn",
  paid: "info",
  processing: "info",
  delivered: "success",
  cancelled: "danger",
};
const PAGE_SIZE = 20;

function OrdersPage() {
  const [orderNumber, setOrderNumber] = useState("");
  const [customerName, setCustomerName] = useState("");
  const [status, setStatus] = useState("");
  const [paymentStatus, setPaymentStatus] = useState("");
  const [odooSyncStatus, setOdooSyncStatus] = useState("");
  const [sort, setSort] = useState<AdminOrderFilters["sort"]>("newest");
  const [offset, setOffset] = useState(0);

  const filters: AdminOrderFilters = {
    order_number: orderNumber || undefined,
    customer_name: customerName || undefined,
    status: status || undefined,
    payment_status: paymentStatus || undefined,
    odoo_sync_status: odooSyncStatus || undefined,
    sort,
    limit: PAGE_SIZE,
    offset,
  };

  const { data, isLoading, isError, error } = useAdminOrders(filters);

  function resetAndFilter(fn: () => void) {
    fn();
    setOffset(0);
  }

  return (
    <Card
      title={data ? `Orders (${data.total})` : "Orders"}
      action={
        <div className="flex flex-wrap gap-2">
          <Input
            placeholder="Order number…"
            value={orderNumber}
            onChange={(e) => resetAndFilter(() => setOrderNumber(e.target.value))}
            className="w-40"
          />
          <Input
            placeholder="Customer name…"
            value={customerName}
            onChange={(e) => resetAndFilter(() => setCustomerName(e.target.value))}
            className="w-40"
          />
          <Select
            value={status}
            onChange={(e) => resetAndFilter(() => setStatus(e.target.value))}
            className="w-36"
          >
            <option value="">All statuses</option>
            {STATUSES.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </Select>
          <Select
            value={paymentStatus}
            onChange={(e) => resetAndFilter(() => setPaymentStatus(e.target.value))}
            className="w-32"
          >
            <option value="">Any payment</option>
            <option value="paid">Paid</option>
            <option value="unpaid">Unpaid</option>
          </Select>
          <Select
            value={odooSyncStatus}
            onChange={(e) => resetAndFilter(() => setOdooSyncStatus(e.target.value))}
            className="w-32"
          >
            <option value="">Any sync</option>
            <option value="not_synced">Not synced</option>
            <option value="synced">Synced</option>
            <option value="failed">Failed</option>
          </Select>
          <Select
            value={sort}
            onChange={(e) =>
              resetAndFilter(() => setSort(e.target.value as AdminOrderFilters["sort"]))
            }
            className="w-36"
          >
            <option value="newest">Newest first</option>
            <option value="oldest">Oldest first</option>
            <option value="total_desc">Highest total</option>
            <option value="total_asc">Lowest total</option>
            <option value="delivery_date">Delivery date</option>
          </Select>
        </div>
      }
    >
      {isLoading && <div className="text-sm text-stone-500 py-6 text-center">Loading orders…</div>}
      {isError && <div className="text-sm text-red-600 py-6 text-center">{error?.message}</div>}
      {!isLoading && data && data.items.length === 0 && (
        <EmptyState title="No orders match these filters" hint="Try clearing a filter." />
      )}
      {!isLoading && data && data.items.length > 0 && (
        <>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="text-left text-xs uppercase text-stone-500 border-b">
                <tr>
                  <th className="py-2">Order</th>
                  <th>Customer</th>
                  <th>Delivery</th>
                  <th>Items</th>
                  <th>Total</th>
                  <th>Payment</th>
                  <th>Status</th>
                  <th>Odoo</th>
                  <th>Notify</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {data.items.map((o) => (
                  <tr key={o.id} className="border-b last:border-0 hover:bg-stone-50">
                    <td className="py-2.5 font-mono text-xs">{o.order_number}</td>
                    <td>
                      {o.customer_name}
                      <div className="text-xs text-stone-500">{o.customer_phone}</div>
                    </td>
                    <td className="text-xs text-stone-500">
                      {o.delivery_date ?? "—"}
                      {o.delivery_time ? ` · ${o.delivery_time}` : ""}
                    </td>
                    <td>
                      {o.item_count}
                      {o.items_summary.length > 0 && (
                        <div className="text-xs text-stone-500 max-w-[220px]">
                          {o.items_summary.join(", ")}
                        </div>
                      )}
                    </td>
                    <td>SAR {o.total_amount}</td>
                    <td>
                      <Badge tone={o.payment_status === "paid" ? "success" : "warn"}>
                        {o.payment_status}
                      </Badge>
                    </td>
                    <td>
                      <Badge tone={STATUS_TONE[o.status] ?? "default"}>{o.status}</Badge>
                    </td>
                    <td>
                      <Badge
                        tone={
                          o.odoo_sync_status === "synced"
                            ? "success"
                            : o.odoo_sync_status === "failed"
                              ? "danger"
                              : "default"
                        }
                      >
                        {o.odoo_sync_status}
                      </Badge>
                    </td>
                    <td>
                      <Badge
                        tone={
                          o.notification_status === "sent"
                            ? "success"
                            : o.notification_status === "failed"
                              ? "danger"
                              : "default"
                        }
                      >
                        {o.notification_status}
                      </Badge>
                    </td>
                    <td>
                      <Link to="/admin/orders/$orderId" params={{ orderId: o.id }}>
                        <Button variant="ghost">
                          <Eye className="h-4 w-4" />
                        </Button>
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="flex items-center justify-between mt-4 text-sm text-stone-500">
            <span>
              {offset + 1}–{Math.min(offset + PAGE_SIZE, data.total)} of {data.total}
            </span>
            <div className="flex gap-2">
              <Button
                variant="outline"
                disabled={offset === 0}
                onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))}
              >
                <ChevronLeft className="h-4 w-4" /> Prev
              </Button>
              <Button
                variant="outline"
                disabled={offset + PAGE_SIZE >= data.total}
                onClick={() => setOffset(offset + PAGE_SIZE)}
              >
                Next <ChevronRight className="h-4 w-4" />
              </Button>
            </div>
          </div>
        </>
      )}
    </Card>
  );
}
