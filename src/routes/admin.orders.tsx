import { createFileRoute } from "@tanstack/react-router";
import { useState } from "react";
import { useStore, orders as ordersApi, ORDER_STATUSES, type Order } from "@/lib/store";
import { Card, Badge, Button, Select, Input, Modal, EmptyState } from "@/components/admin/ui";
import { Eye } from "lucide-react";

export const Route = createFileRoute("/admin/orders")({ component: OrdersPage });

function OrdersPage() {
  const orders = useStore((s) => s.orders);
  const [q, setQ] = useState("");
  const [status, setStatus] = useState<string>("all");
  const [view, setView] = useState<Order | null>(null);

  const filtered = orders.filter((o) => {
    if (status !== "all" && o.status !== status) return false;
    if (q && !(o.id.toLowerCase().includes(q.toLowerCase()) || o.address?.name?.toLowerCase().includes(q.toLowerCase()))) return false;
    return true;
  });

  return (
    <Card
      title={`Orders (${filtered.length})`}
      action={
        <div className="flex gap-2">
          <Input placeholder="Search order or customer…" value={q} onChange={(e) => setQ(e.target.value)} className="w-56" />
          <Select value={status} onChange={(e) => setStatus(e.target.value)} className="w-36">
            <option value="all">All statuses</option>
            {ORDER_STATUSES.map((s) => <option key={s} value={s}>{s}</option>)}
          </Select>
        </div>
      }
    >
      {filtered.length === 0 ? (
        <EmptyState title="No orders" hint="Place a demo order on the storefront to see it here." />
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="text-left text-xs uppercase text-slate-500 border-b">
              <tr><th className="py-2">Order</th><th>Customer</th><th>Items</th><th>Total</th><th>Placed</th><th>Status</th><th></th></tr>
            </thead>
            <tbody>
              {filtered.map((o) => (
                <tr key={o.id} className="border-b last:border-0 hover:bg-slate-50">
                  <td className="py-2.5 font-mono text-xs">{o.id}</td>
                  <td>{o.address?.name ?? "—"}<div className="text-xs text-slate-500">{o.address?.phone ?? ""}</div></td>
                  <td>{o.items.reduce((n, i) => n + i.qty, 0)}</td>
                  <td>SAR {o.total.toFixed(2)}</td>
                  <td className="text-slate-500">{new Date(o.createdAt).toLocaleString()}</td>
                  <td>
                    <Select value={o.status} onChange={(e) => ordersApi.setStatus(o.id, e.target.value as any)} className="w-32">
                      {ORDER_STATUSES.map((s) => <option key={s} value={s}>{s}</option>)}
                    </Select>
                  </td>
                  <td><Button variant="ghost" onClick={() => setView(o)}><Eye className="h-4 w-4" /></Button></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <Modal open={!!view} onClose={() => setView(null)} title={view ? `Order ${view.id}` : ""}>
        {view && (
          <div className="space-y-4 text-sm">
            <div className="grid grid-cols-2 gap-3">
              <div><div className="text-xs text-slate-500">Customer</div><div className="font-medium">{view.address?.name}</div></div>
              <div><div className="text-xs text-slate-500">Phone</div><div>{view.address?.phone}</div></div>
              <div><div className="text-xs text-slate-500">Area</div><div>{view.address?.area}</div></div>
              <div><div className="text-xs text-slate-500">Address</div><div>{view.address?.address}</div></div>
              <div><div className="text-xs text-slate-500">Payment</div><div>{view.method}</div></div>
              <div><div className="text-xs text-slate-500">Status</div><Badge tone={view.status === "Delivered" ? "success" : "info"}>{view.status}</Badge></div>
            </div>
            <div>
              <div className="text-xs text-slate-500 mb-1">Items</div>
              <div className="border rounded-lg divide-y">
                {view.items.map((it, i) => (
                  <div key={i} className="flex items-center justify-between px-3 py-2">
                    <div><div className="font-medium">{it.name}</div><div className="text-xs text-slate-500">{[it.size, it.flavor].filter(Boolean).join(" · ")} × {it.qty}</div></div>
                    <div>SAR {(it.qty * it.unitPrice).toFixed(2)}</div>
                  </div>
                ))}
              </div>
            </div>
            <div className="grid grid-cols-2 gap-2 text-xs">
              <div className="flex justify-between"><span className="text-slate-500">Subtotal</span><span>SAR {view.subtotal.toFixed(2)}</span></div>
              <div className="flex justify-between"><span className="text-slate-500">Discount</span><span>- SAR {view.discount.toFixed(2)}</span></div>
              <div className="flex justify-between"><span className="text-slate-500">Delivery</span><span>SAR {view.deliveryFee.toFixed(2)}</span></div>
              <div className="flex justify-between"><span className="text-slate-500">Tax</span><span>SAR {view.tax.toFixed(2)}</span></div>
              <div className="flex justify-between col-span-2 font-medium text-slate-900 border-t pt-2"><span>Total</span><span>SAR {view.total.toFixed(2)}</span></div>
            </div>
          </div>
        )}
      </Modal>
    </Card>
  );
}
