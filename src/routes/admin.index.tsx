import { createFileRoute } from "@tanstack/react-router";
import { useDashboardSummary, useDashboardRecentOrders, useDashboardAlerts } from "@/lib/admin-api";
import { Stat, Card, Badge, EmptyState } from "@/components/admin/ui";
import { AlertTriangle, RefreshCw, ShoppingBag, TrendingUp } from "lucide-react";
import { Link } from "@tanstack/react-router";

export const Route = createFileRoute("/admin/")({ component: Dashboard });

const STATUS_TONE: Record<string, "success" | "info" | "warn" | "danger" | "default"> = {
  pending_payment: "warn",
  paid: "info",
  processing: "info",
  delivered: "success",
  cancelled: "danger",
};

function Dashboard() {
  const summary = useDashboardSummary();
  const recent = useDashboardRecentOrders();
  const alerts = useDashboardAlerts();

  if (summary.isLoading) {
    return <div className="text-sm text-stone-500 py-10 text-center">Loading dashboard…</div>;
  }
  if (summary.isError || !summary.data) {
    return (
      <Card>
        <div className="text-sm text-red-600 flex items-center gap-2 py-4 justify-center">
          <AlertTriangle className="h-4 w-4" /> Could not load the dashboard.{" "}
          {summary.error?.message}
        </div>
      </Card>
    );
  }

  const s = summary.data;

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <Stat
          label="Orders today"
          value={s.orders_today}
          hint={`${s.pending_payment_orders_today} awaiting payment`}
        />
        <Stat label="Revenue today" value={`SAR ${s.revenue_today}`} tone="up" />
        <Stat label="Paid orders today" value={s.paid_orders_today} tone="up" />
        <Stat
          label="Needs attention"
          value={s.orders_requiring_attention}
          hint={`${s.failed_odoo_sync} sync failed · ${s.failed_notifications} notify failed · ${s.stuck_orders} stuck`}
          tone={s.orders_requiring_attention > 0 ? "down" : "default"}
        />
      </div>

      {alerts.data && alerts.data.length > 0 && (
        <Card title="Operational alerts">
          <ul className="space-y-2">
            {alerts.data.map((a) => (
              <li
                key={a.type}
                className="flex items-center justify-between rounded-lg bg-amber-50 border border-amber-200 px-4 py-2.5 text-sm"
              >
                <span className="flex items-center gap-2 text-amber-800">
                  <AlertTriangle className="h-4 w-4" /> {a.message}
                </span>
                <Badge tone="warn">{a.count}</Badge>
              </li>
            ))}
          </ul>
        </Card>
      )}

      <Card
        title="Recent orders"
        action={
          <button
            onClick={() => recent.refetch()}
            className="text-xs text-stone-500 hover:text-stone-800 flex items-center gap-1"
          >
            <RefreshCw className="h-3 w-3" /> Refresh
          </button>
        }
      >
        {!recent.data || recent.data.length === 0 ? (
          <EmptyState
            title="No orders yet"
            hint="Real customer orders will appear here as they come in."
          />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="text-left text-xs uppercase text-stone-500 border-b">
                <tr>
                  <th className="py-2">Order</th>
                  <th>Customer</th>
                  <th>Phone</th>
                  <th>Total</th>
                  <th>Payment</th>
                  <th>Status</th>
                  <th>Odoo sync</th>
                  <th>Created</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {recent.data.map((o) => (
                  <tr key={o.id} className="border-b last:border-0">
                    <td className="py-2.5 font-mono text-xs">{o.order_number}</td>
                    <td>{o.customer_name}</td>
                    <td className="text-stone-500">{o.customer_phone}</td>
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
                    <td className="text-stone-500">{new Date(o.created_at).toLocaleString()}</td>
                    <td>
                      <Link
                        to="/admin/orders/$orderId"
                        params={{ orderId: o.id }}
                        className="text-xs text-primary hover:underline flex items-center gap-1"
                      >
                        <ShoppingBag className="h-3 w-3" /> Open
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      <Card title="This session">
        <div className="flex items-center gap-2 text-sm text-stone-600">
          <TrendingUp className="h-4 w-4" />
          Dashboard data is live from PostgreSQL via FastAPI — refresh anytime with the button
          above.
        </div>
      </Card>
    </div>
  );
}
