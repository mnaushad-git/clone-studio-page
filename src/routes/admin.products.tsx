import { createFileRoute } from "@tanstack/react-router";
import { useState } from "react";
import { products, CATEGORY_LABEL, type Category } from "@/lib/products";
import { useAdmin, productOverrideStore } from "@/lib/admin-store";
import { Card, Badge, Button, Input, Select, Toggle, Modal, Field } from "@/components/admin/ui";
import { Pencil } from "lucide-react";

export const Route = createFileRoute("/admin/products")({ component: ProductsPage });

function ProductsPage() {
  const overrides = useAdmin((s) => s.productOverrides);
  const [q, setQ] = useState("");
  const [cat, setCat] = useState<string>("all");
  const [editing, setEditing] = useState<string | null>(null);

  const rows = products.filter((p) => {
    if (cat !== "all" && p.category !== cat) return false;
    if (q && !p.name.toLowerCase().includes(q.toLowerCase())) return false;
    return true;
  });

  const editingProduct = editing ? products.find((p) => p.id === editing) : null;
  const editingOverride = editing ? overrides[editing] : undefined;

  return (
    <Card
      title={`Products (${rows.length})`}
      action={
        <div className="flex gap-2">
          <Input placeholder="Search products…" value={q} onChange={(e) => setQ(e.target.value)} className="w-56" />
          <Select value={cat} onChange={(e) => setCat(e.target.value)} className="w-36">
            <option value="all">All categories</option>
            {Object.entries(CATEGORY_LABEL).map(([v, l]) => <option key={v} value={v}>{l}</option>)}
          </Select>
        </div>
      }
    >
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="text-left text-xs uppercase text-slate-500 border-b">
            <tr><th className="py-2">Product</th><th>Category</th><th>Price (SAR)</th><th>Stock</th><th>Featured</th><th>Visible</th><th></th></tr>
          </thead>
          <tbody>
            {rows.map((p) => {
              const o = overrides[p.id];
              const price = o?.priceOverride ?? p.price;
              return (
                <tr key={p.id} className="border-b last:border-0 hover:bg-slate-50">
                  <td className="py-2">
                    <div className="flex items-center gap-3">
                      <img src={p.image} alt={p.name} className="h-10 w-10 rounded object-cover" />
                      <div>
                        <div className="font-medium">{p.name}</div>
                        <div className="text-xs text-slate-500">{p.id}</div>
                      </div>
                    </div>
                  </td>
                  <td><Badge>{CATEGORY_LABEL[p.category as Category]}</Badge></td>
                  <td>{price.toFixed(2)} {o?.priceOverride ? <Badge tone="info">override</Badge> : null}</td>
                  <td>{o?.stock ?? "—"}</td>
                  <td><Toggle checked={o?.featured ?? false} onChange={(v) => productOverrideStore.set(p.id, { featured: v })} /></td>
                  <td><Toggle checked={o?.visible ?? true} onChange={(v) => productOverrideStore.set(p.id, { visible: v })} /></td>
                  <td><Button variant="ghost" onClick={() => setEditing(p.id)}><Pencil className="h-4 w-4" /></Button></td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      <Modal
        open={!!editing}
        onClose={() => setEditing(null)}
        title={editingProduct ? `Edit — ${editingProduct.name}` : ""}
        footer={<Button onClick={() => setEditing(null)}>Done</Button>}
      >
        {editingProduct && (
          <div className="space-y-4">
            <div className="flex items-center gap-3">
              <img src={editingProduct.image} alt="" className="h-16 w-16 rounded object-cover" />
              <div>
                <div className="font-medium">{editingProduct.name}</div>
                <div className="text-xs text-slate-500">{CATEGORY_LABEL[editingProduct.category as Category]} · base SAR {editingProduct.price.toFixed(2)}</div>
              </div>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <Field label="Price override (SAR)" hint="Leave blank to keep base price">
                <Input type="number" step="0.01" defaultValue={editingOverride?.priceOverride ?? ""} onBlur={(e) => productOverrideStore.set(editingProduct.id, { priceOverride: e.target.value ? Number(e.target.value) : undefined })} />
              </Field>
              <Field label="Stock quantity">
                <Input type="number" defaultValue={editingOverride?.stock ?? ""} onBlur={(e) => productOverrideStore.set(editingProduct.id, { stock: e.target.value ? Number(e.target.value) : undefined })} />
              </Field>
              <Field label="Badge label" hint="e.g. New, Bestseller, Limited">
                <Input defaultValue={editingOverride?.badge ?? ""} onBlur={(e) => productOverrideStore.set(editingProduct.id, { badge: e.target.value || undefined })} />
              </Field>
            </div>
            <div className="flex items-center gap-6">
              <Toggle checked={editingOverride?.visible ?? true} onChange={(v) => productOverrideStore.set(editingProduct.id, { visible: v })} label="Visible on storefront" />
              <Toggle checked={editingOverride?.featured ?? false} onChange={(v) => productOverrideStore.set(editingProduct.id, { featured: v })} label="Featured on homepage" />
            </div>
            {editingProduct.description && <div className="text-xs text-slate-500 bg-slate-50 border rounded-lg p-3">{editingProduct.description}</div>}
          </div>
        )}
      </Modal>
    </Card>
  );
}
