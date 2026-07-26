import { createFileRoute } from "@tanstack/react-router";
import { useStore } from "@/lib/store";
import { products, CATEGORY_LABEL, type Category } from "@/lib/products";
import { Card, Stat } from "@/components/admin/ui";

export const Route = createFileRoute("/admin/analytics")({ component: AnalyticsPage });

function AnalyticsPage() {
  const orders = useStore((s) => s.orders);

  const revenue = orders.reduce((s, o) => s + o.total, 0);
  const items = orders.flatMap((o) => o.items);
  const unitsSold = items.reduce((s, i) => s + i.qty, 0);

  // Top products
  const byProduct = new Map<string, { qty: number; revenue: number; name: string }>();
  items.forEach((i) => {
    const cur = byProduct.get(i.productId) ?? { qty: 0, revenue: 0, name: i.name };
    cur.qty += i.qty; cur.revenue += i.qty * i.unitPrice;
    byProduct.set(i.productId, cur);
  });
  const topProducts = [...byProduct.entries()].sort((a, b) => b[1].revenue - a[1].revenue).slice(0, 6);

  // Category split
  const byCat = new Map<Category, number>();
  items.forEach((i) => {
    const p = products.find((pp) => pp.id === i.productId);
    if (!p) return;
    byCat.set(p.category, (byCat.get(p.category) ?? 0) + i.qty * i.unitPrice);
  });
  const catTotal = [...byCat.values()].reduce((a, b) => a + b, 0);

  // Hour of day
  const hours = Array.from({ length: 24 }, () => 0);
  orders.forEach((o) => { hours[new Date(o.createdAt).getHours()] += 1; });
  const maxHour = Math.max(...hours, 1);

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 sm:grid-cols-4 gap-4">
        <Stat label="Revenue" value={`SAR ${revenue.toFixed(2)}`} />
        <Stat label="Orders" value={orders.length} />
        <Stat label="Units sold" value={unitsSold} />
        <Stat label="Avg order" value={`SAR ${orders.length ? (revenue / orders.length).toFixed(2) : "0.00"}`} />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card title="Top products by revenue">
          {topProducts.length === 0 ? <div className="text-sm text-slate-500 py-4 text-center">No sales yet</div> : (
            <div className="space-y-3">
              {topProducts.map(([id, r]) => {
                const max = topProducts[0][1].revenue;
                return (
                  <div key={id}>
                    <div className="flex justify-between text-sm mb-1"><span className="font-medium">{r.name}</span><span className="text-slate-500">SAR {r.revenue.toFixed(2)} · {r.qty} sold</span></div>
                    <div className="h-2 rounded bg-slate-100 overflow-hidden"><div className="h-full bg-amber-500" style={{ width: `${(r.revenue / max) * 100}%` }} /></div>
                  </div>
                );
              })}
            </div>
          )}
        </Card>

        <Card title="Revenue by category">
          {catTotal === 0 ? <div className="text-sm text-slate-500 py-4 text-center">No sales yet</div> : (
            <div className="space-y-3">
              {[...byCat.entries()].sort((a, b) => b[1] - a[1]).map(([cat, val]) => (
                <div key={cat}>
                  <div className="flex justify-between text-sm mb-1"><span className="font-medium">{CATEGORY_LABEL[cat]}</span><span className="text-slate-500">{((val / catTotal) * 100).toFixed(0)}% · SAR {val.toFixed(2)}</span></div>
                  <div className="h-2 rounded bg-slate-100 overflow-hidden"><div className="h-full bg-slate-800" style={{ width: `${(val / catTotal) * 100}%` }} /></div>
                </div>
              ))}
            </div>
          )}
        </Card>
      </div>

      <Card title="Orders by hour of day">
        <div className="flex items-end gap-1 h-32">
          {hours.map((v, i) => (
            <div key={i} className="flex-1 flex flex-col items-center gap-1">
              <div className="w-full bg-slate-800 rounded-t" style={{ height: `${(v / maxHour) * 100}%`, minHeight: 2 }} />
              <div className="text-[9px] text-slate-400">{i}</div>
            </div>
          ))}
        </div>
      </Card>
    </div>
  );
}
