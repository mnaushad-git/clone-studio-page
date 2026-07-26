import { createFileRoute } from "@tanstack/react-router";
import { useStore } from "@/lib/store";
import { Card, EmptyState, Badge } from "@/components/admin/ui";

export const Route = createFileRoute("/admin/customers")({ component: CustomersPage });

function CustomersPage() {
  const user = useStore((s) => s.user);
  const orders = useStore((s) => s.orders);
  const addresses = useStore((s) => s.addresses);

  // In demo mode we only track the currently signed-in user + guest checkouts by address
  type Row = { key: string; name: string; email?: string; phone?: string; orders: number; spent: number; source: "account" | "guest" };
  const map = new Map<string, Row>();
  if (user?.email || user?.phone) {
    const key = user.email ?? user.phone!;
    map.set(key, { key, name: user.name ?? "You", email: user.email, phone: user.phone, orders: 0, spent: 0, source: "account" });
  }
  orders.forEach((o) => {
    const key = user?.email ?? user?.phone ?? o.address?.phone ?? o.address?.name ?? "guest";
    const existing = map.get(key) ?? { key, name: o.address?.name ?? "Guest", phone: o.address?.phone, orders: 0, spent: 0, source: "guest" as const };
    existing.orders += 1;
    existing.spent += o.total;
    map.set(key, existing);
  });
  const rows = [...map.values()].sort((a, b) => b.spent - a.spent);

  return (
    <Card title={`Customers (${rows.length})`}>
      {rows.length === 0 ? (
        <EmptyState title="No customers yet" hint="Sign up or place a demo order to populate this list." />
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="text-left text-xs uppercase text-slate-500 border-b">
              <tr><th className="py-2">Name</th><th>Email</th><th>Phone</th><th>Orders</th><th>Spent</th><th>Addresses</th><th>Type</th></tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r.key} className="border-b last:border-0 hover:bg-slate-50">
                  <td className="py-2.5 font-medium">{r.name}</td>
                  <td className="text-slate-600">{r.email ?? "—"}</td>
                  <td className="text-slate-600">{r.phone ?? "—"}</td>
                  <td>{r.orders}</td>
                  <td>SAR {r.spent.toFixed(2)}</td>
                  <td>{r.source === "account" ? addresses.length : "—"}</td>
                  <td><Badge tone={r.source === "account" ? "success" : "default"}>{r.source}</Badge></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </Card>
  );
}
