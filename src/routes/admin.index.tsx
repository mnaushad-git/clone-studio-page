import { createFileRoute } from "@tanstack/react-router";
import { useStore } from "@/lib/store";
import { useAdmin } from "@/lib/admin-store";
import { products } from "@/lib/products";
import { Stat, Card, Badge } from "@/components/admin/ui";
import { TrendingUp, ShoppingBag, Users, Star } from "lucide-react";

export const Route = createFileRoute("/admin/")({ component: Dashboard });

function Dashboard() {
  const orders = useStore((s) => s.orders);
  const reviews = useStore((s) => s.reviews);
  const users = useStore((s) => s.user);
  const staff = useAdmin((s) => s.staff);

  const revenue = orders.reduce((sum, o) => sum + o.total, 0);
  const avg = orders.length ? revenue / orders.length : 0;
  const pending = orders.filter((o) => o.status !== "Delivered").length;
  const avgRating = reviews.length ? (reviews.reduce((s, r) => s + r.rating, 0) / reviews.length).toFixed(1) : "—";

  // Simple sparkline data (last 7 buckets)
  const now = Date.now();
  const buckets = Array.from({ length: 7 }, (_, i) => {
    const start = now - (6 - i) * 86400000;
    const end = start + 86400000;
    return orders.filter((o) => o.createdAt >= start && o.createdAt < end).reduce((s, o) => s + o.total, 0);
  });
  const maxBucket = Math.max(...buckets, 1);

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <Stat label="Total revenue" value={`SAR ${revenue.toFixed(2)}`} hint="All time" tone="up" />
        <Stat label="Orders" value={orders.length} hint={`${pending} pending`} />
        <Stat label="Avg order value" value={`SAR ${avg.toFixed(2)}`} />
        <Stat label="Avg rating" value={avgRating} hint={`${reviews.length} reviews`} tone="up" />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <Card title="Revenue — last 7 days" className="lg:col-span-2">
          <div className="flex items-end gap-2 h-40">
            {buckets.map((v, i) => (
              <div key={i} className="flex-1 flex flex-col items-center gap-2">
                <div className="w-full bg-amber-100 rounded-t" style={{ height: `${(v / maxBucket) * 100}%`, minHeight: 4 }}>
                  <div className="w-full h-full bg-gradient-to-t from-amber-500 to-amber-300 rounded-t" />
                </div>
                <div className="text-[10px] text-stone-500">Day {i + 1}</div>
              </div>
            ))}
          </div>
        </Card>

        <Card title="Quick stats">
          <ul className="space-y-3 text-sm">
            <li className="flex items-center justify-between"><span className="flex items-center gap-2 text-stone-600"><ShoppingBag className="h-4 w-4" /> Catalog products</span><span className="font-medium">{products.length}</span></li>
            <li className="flex items-center justify-between"><span className="flex items-center gap-2 text-stone-600"><Users className="h-4 w-4" /> Staff members</span><span className="font-medium">{staff.filter((s) => s.active).length}</span></li>
            <li className="flex items-center justify-between"><span className="flex items-center gap-2 text-stone-600"><Star className="h-4 w-4" /> Reviews</span><span className="font-medium">{reviews.length}</span></li>
            <li className="flex items-center justify-between"><span className="flex items-center gap-2 text-stone-600"><TrendingUp className="h-4 w-4" /> Registered customers</span><span className="font-medium">{users ? 1 : 0}</span></li>
          </ul>
        </Card>
      </div>

      <Card title="Recent orders">
        {orders.length === 0 ? (
          <div className="text-sm text-stone-500 py-6 text-center">No orders yet. Place a demo order from the storefront to see it here.</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="text-left text-xs uppercase text-stone-500 border-b">
                <tr><th className="py-2">Order</th><th>Customer</th><th>Date</th><th>Total</th><th>Status</th></tr>
              </thead>
              <tbody>
                {orders.slice(0, 6).map((o) => (
                  <tr key={o.id} className="border-b last:border-0">
                    <td className="py-2.5 font-mono text-xs">{o.id}</td>
                    <td>{o.address?.name ?? "—"}</td>
                    <td className="text-stone-500">{new Date(o.createdAt).toLocaleDateString()}</td>
                    <td>SAR {o.total.toFixed(2)}</td>
                    <td>
                      <Badge tone={o.status === "Delivered" ? "success" : o.status === "Paid" ? "info" : "warn"}>{o.status}</Badge>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </div>
  );
}
