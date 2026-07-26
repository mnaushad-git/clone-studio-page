import { createFileRoute } from "@tanstack/react-router";
import { useState } from "react";
import { products, CATEGORY_LABEL, type Category } from "@/lib/products";
import { useAdmin, productOverrideStore, type ProductSizeOption } from "@/lib/admin-store";
import { Card, Badge, Button, Input, Select, Toggle, Modal, Field } from "@/components/admin/ui";
import { Pencil, Plus, Trash2, RotateCcw } from "lucide-react";

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
          <thead className="text-left text-xs uppercase text-stone-500 border-b">
            <tr><th className="py-2">Product</th><th>Category</th><th>Price (SAR)</th><th>Stock</th><th>Featured</th><th>Visible</th><th></th></tr>
          </thead>
          <tbody>
            {rows.map((p) => {
              const o = overrides[p.id];
              const price = o?.priceOverride ?? p.price;
              return (
                <tr key={p.id} className="border-b last:border-0 hover:bg-stone-50">
                  <td className="py-2">
                    <div className="flex items-center gap-3">
                      <img src={p.image} alt={p.name} className="h-10 w-10 rounded object-cover" />
                      <div>
                        <div className="font-medium">{p.name}</div>
                        <div className="text-xs text-stone-500">{p.id}</div>
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
          <ProductEditor
            productId={editingProduct.id}
            baseName={editingProduct.name}
            baseCategory={editingProduct.category as Category}
            baseImage={editingProduct.image}
            basePrice={editingProduct.price}
            baseDescription={editingProduct.description}
            override={editingOverride}
          />
        )}
      </Modal>
    </Card>
  );
}

function ProductEditor({
  productId,
  baseName,
  baseCategory,
  baseImage,
  basePrice,
  baseDescription,
  override,
}: {
  productId: string;
  baseName: string;
  baseCategory: Category;
  baseImage: string;
  basePrice: number;
  baseDescription?: string;
  override: ReturnType<typeof useAdmin<Record<string, any>>> extends any ? any : never;
}) {
  const set = (patch: Record<string, unknown>) => productOverrideStore.set(productId, patch);
  const sizes: ProductSizeOption[] = override?.sizes ?? [];
  const flavors: string[] = override?.flavors ?? [];

  const updateSize = (i: number, patch: Partial<ProductSizeOption>) => {
    const next = sizes.map((s, idx) => (idx === i ? { ...s, ...patch } : s));
    set({ sizes: next });
  };
  const addSize = () => set({ sizes: [...sizes, { label: "NEW SIZE", delta: 0 }] });
  const removeSize = (i: number) => set({ sizes: sizes.filter((_, idx) => idx !== i) });
  const resetSizes = () => set({ sizes: undefined });

  const updateFlavor = (i: number, v: string) => set({ flavors: flavors.map((f, idx) => (idx === i ? v : f)) });
  const addFlavor = () => set({ flavors: [...flavors, "New Flavor"] });
  const removeFlavor = (i: number) => set({ flavors: flavors.filter((_, idx) => idx !== i) });
  const resetFlavors = () => set({ flavors: undefined });

  return (
    <div className="space-y-5">
      <div className="flex items-center gap-3">
        <img src={override?.imageOverride || baseImage} alt="" className="h-16 w-16 rounded object-cover" />
        <div>
          <div className="font-medium">{override?.nameOverride || baseName}</div>
          <div className="text-xs text-stone-500">{CATEGORY_LABEL[baseCategory]} · base SAR {basePrice.toFixed(2)}</div>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-3">
        <Field label="Display name override">
          <Input defaultValue={override?.nameOverride ?? ""} placeholder={baseName} onBlur={(e) => set({ nameOverride: e.target.value || undefined })} />
        </Field>
        <Field label="Image URL override" hint="Public URL to replace product image">
          <Input defaultValue={override?.imageOverride ?? ""} placeholder="https://…" onBlur={(e) => set({ imageOverride: e.target.value || undefined })} />
        </Field>
        <Field label="Price override (SAR)" hint="Leave blank to keep base price">
          <Input type="number" step="0.01" defaultValue={override?.priceOverride ?? ""} onBlur={(e) => set({ priceOverride: e.target.value ? Number(e.target.value) : undefined })} />
        </Field>
        <Field label="Stock quantity">
          <Input type="number" defaultValue={override?.stock ?? ""} onBlur={(e) => set({ stock: e.target.value ? Number(e.target.value) : undefined })} />
        </Field>
        <Field label="Max qty per order">
          <Input type="number" defaultValue={override?.maxQty ?? ""} onBlur={(e) => set({ maxQty: e.target.value ? Number(e.target.value) : undefined })} />
        </Field>
        <Field label="Badge label" hint="e.g. New, Bestseller, Limited">
          <Input defaultValue={override?.badge ?? ""} onBlur={(e) => set({ badge: e.target.value || undefined })} />
        </Field>
      </div>

      <Field label="Description override" hint="Shown on the product page">
        <textarea
          defaultValue={override?.descriptionOverride ?? ""}
          placeholder={baseDescription ?? "Product description"}
          onBlur={(e) => set({ descriptionOverride: e.target.value || undefined })}
          className="w-full min-h-[70px] px-3 py-2 rounded-lg border border-stone-300 focus:border-stone-900 focus:outline-none text-sm"
        />
      </Field>

      <Field label="Tags (comma-separated)" hint="Used for filters and recommendations">
        <Input
          defaultValue={(override?.tags ?? []).join(", ")}
          onBlur={(e) => set({ tags: e.target.value ? e.target.value.split(",").map((t) => t.trim()).filter(Boolean) : undefined })}
        />
      </Field>

      <div className="border rounded-lg p-3">
        <div className="flex items-center justify-between mb-2">
          <div className="font-medium text-sm">Size options</div>
          <div className="flex gap-2">
            <Button variant="ghost" onClick={resetSizes}><RotateCcw className="h-3 w-3 mr-1" />Use defaults</Button>
            <Button variant="secondary" onClick={addSize}><Plus className="h-3 w-3 mr-1" />Add size</Button>
          </div>
        </div>
        {sizes.length === 0 ? (
          <div className="text-xs text-stone-500">Using category defaults. Click "Add size" to customize.</div>
        ) : (
          <div className="space-y-2">
            {sizes.map((s, i) => (
              <div key={i} className="grid grid-cols-[1fr_1fr_110px_auto] gap-2 items-center">
                <Input defaultValue={s.label} placeholder="LABEL" onBlur={(e) => updateSize(i, { label: e.target.value })} />
                <Input defaultValue={s.sub ?? ""} placeholder="Subtext (optional)" onBlur={(e) => updateSize(i, { sub: e.target.value || undefined })} />
                <Input type="number" step="0.01" defaultValue={s.delta ?? 0} placeholder="Δ price" onBlur={(e) => updateSize(i, { delta: Number(e.target.value) || 0 })} />
                <Button variant="ghost" onClick={() => removeSize(i)}><Trash2 className="h-3 w-3" /></Button>
              </div>
            ))}
          </div>
        )}
      </div>

      <div className="border rounded-lg p-3">
        <div className="flex items-center justify-between mb-2">
          <div className="font-medium text-sm">Flavor options</div>
          <div className="flex gap-2">
            <Button variant="ghost" onClick={resetFlavors}><RotateCcw className="h-3 w-3 mr-1" />Use defaults</Button>
            <Button variant="secondary" onClick={addFlavor}><Plus className="h-3 w-3 mr-1" />Add flavor</Button>
          </div>
        </div>
        {flavors.length === 0 ? (
          <div className="text-xs text-stone-500">Using category defaults. Click "Add flavor" to customize.</div>
        ) : (
          <div className="space-y-2">
            {flavors.map((f, i) => (
              <div key={i} className="flex gap-2 items-center">
                <Input defaultValue={f} onBlur={(e) => updateFlavor(i, e.target.value)} />
                <Button variant="ghost" onClick={() => removeFlavor(i)}><Trash2 className="h-3 w-3" /></Button>
              </div>
            ))}
          </div>
        )}
      </div>

      <div className="flex flex-wrap items-center gap-6 border-t pt-4">
        <Toggle checked={override?.visible ?? true} onChange={(v) => set({ visible: v })} label="Visible on storefront" />
        <Toggle checked={override?.featured ?? false} onChange={(v) => set({ featured: v })} label="Featured on homepage" />
        <Toggle checked={override?.allowInscription ?? baseCategory === "cakes"} onChange={(v) => set({ allowInscription: v })} label="Allow inscription" />
      </div>
    </div>
  );
}
      </Modal>
    </Card>
  );
}
