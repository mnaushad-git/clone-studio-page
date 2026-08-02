import { createFileRoute } from "@tanstack/react-router";
import { useState } from "react";
import { toast } from "sonner";
import {
  useAdminProducts,
  useAdminProduct,
  useUpdateProductMerchandising,
  useSyncRuns,
  useTriggerCatalogueSync,
  type AdminProductMerchandisingUpdate,
} from "@/lib/admin-api";
import { resolveImageUrl } from "@/lib/catalogue-api";
import {
  Card,
  Badge,
  Button,
  Input,
  Select,
  Toggle,
  Modal,
  Field,
  EmptyState,
} from "@/components/admin/ui";
import { Pencil } from "lucide-react";

export const Route = createFileRoute("/admin/products")({ component: ProductsPage });

function ProductsPage() {
  const [search, setSearch] = useState("");
  const [active, setActive] = useState<string>("");
  const [editingId, setEditingId] = useState<string | null>(null);

  const { data, isLoading, isError, error } = useAdminProducts({
    search: search || undefined,
    active: active === "" ? undefined : active === "true",
    limit: 50,
  });
  const { data: syncRuns } = useSyncRuns(1);
  const triggerSync = useTriggerCatalogueSync();
  const lastRun = syncRuns?.items[0];

  async function handleSyncNow() {
    try {
      const result = await triggerSync.mutateAsync(false);
      if (result.worker_dispatched) {
        toast.success(result.message);
      } else {
        toast.info(result.message);
      }
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to trigger sync.");
    }
  }

  return (
    <Card
      title={data ? `Products (${data.total})` : "Products"}
      action={
        <div className="flex flex-wrap items-center gap-2">
          <Input
            placeholder="Search name or SKU…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-56"
          />
          <Select value={active} onChange={(e) => setActive(e.target.value)} className="w-32">
            <option value="">All</option>
            <option value="true">Active</option>
            <option value="false">Inactive</option>
          </Select>
          <div className="flex items-center gap-2 border-l pl-2 ml-1">
            {lastRun && (
              <span className="text-xs text-stone-500">
                Last Odoo sync:{" "}
                {lastRun.status === "RUNNING"
                  ? "running…"
                  : new Date(lastRun.completed_at ?? lastRun.started_at).toLocaleString()}
                {lastRun.status === "FAILED" && (
                  <span className="ml-1">
                    <Badge tone="warn">Failed</Badge>
                  </span>
                )}
                {lastRun.status === "PARTIALLY_COMPLETED" && (
                  <span className="ml-1">
                    <Badge tone="warn">Partial</Badge>
                  </span>
                )}
              </span>
            )}
            <Button
              variant="ghost"
              disabled={triggerSync.isPending || lastRun?.status === "RUNNING"}
              onClick={handleSyncNow}
            >
              Sync now
            </Button>
          </div>
        </div>
      }
    >
      {isLoading && (
        <div className="text-sm text-stone-500 py-6 text-center">Loading products…</div>
      )}
      {isError && <div className="text-sm text-red-600 py-6 text-center">{error?.message}</div>}
      {!isLoading && data && data.items.length === 0 && (
        <EmptyState title="No products match" hint="Try clearing search or filters." />
      )}
      {!isLoading && data && data.items.length > 0 && (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="text-left text-xs uppercase text-stone-500 border-b">
              <tr>
                <th className="py-2">Product</th>
                <th>SKU</th>
                <th>Category</th>
                <th>Price</th>
                <th>Active</th>
                <th>Featured</th>
                <th>Bestseller</th>
                <th>New</th>
                <th>Odoo</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {data.items.map((p) => (
                <tr key={p.id} className="border-b last:border-0 hover:bg-stone-50">
                  <td className="py-2">
                    <div className="flex items-center gap-3">
                      {p.primary_image_url && (
                        <img
                          src={resolveImageUrl(p.primary_image_url)}
                          alt=""
                          className="h-10 w-10 rounded object-cover"
                        />
                      )}
                      <div className="font-medium">{p.name_en}</div>
                    </div>
                  </td>
                  <td className="font-mono text-xs">{p.sku}</td>
                  <td>
                    <Badge>{p.category_name}</Badge>
                  </td>
                  <td>{p.price ? `SAR ${p.price}` : "—"}</td>
                  <td>
                    <Badge tone={p.active ? "success" : "default"}>
                      {p.active ? "Active" : "Inactive"}
                    </Badge>
                  </td>
                  <td>{p.featured ? <Badge tone="info">Featured</Badge> : "—"}</td>
                  <td>{p.is_bestseller ? <Badge tone="warn">Bestseller</Badge> : "—"}</td>
                  <td>{p.is_new ? <Badge tone="success">New</Badge> : "—"}</td>
                  <td>
                    <Badge tone={p.odoo_mapped ? "success" : "default"}>
                      {p.odoo_mapped ? "Mapped" : "Unmapped"}
                    </Badge>
                  </td>
                  <td>
                    <Button variant="ghost" onClick={() => setEditingId(p.id)}>
                      <Pencil className="h-4 w-4" />
                    </Button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {editingId && (
        <MerchandisingEditor productId={editingId} onClose={() => setEditingId(null)} />
      )}
    </Card>
  );
}

function MerchandisingEditor({ productId, onClose }: { productId: string; onClose: () => void }) {
  const { data: product, isLoading } = useAdminProduct(productId);
  const update = useUpdateProductMerchandising();
  const [form, setForm] = useState<AdminProductMerchandisingUpdate | null>(null);

  const merch = form ?? product?.merchandising ?? null;

  function patch(fields: AdminProductMerchandisingUpdate) {
    setForm({ ...(merch ?? {}), ...fields });
  }

  async function save() {
    if (!form) return onClose();
    try {
      await update.mutateAsync({ productId, updates: form });
      toast.success("Merchandising updated.");
      onClose();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to update.");
    }
  }

  return (
    <Modal
      open
      onClose={onClose}
      title={product ? `Merchandising — ${product.name_en}` : "Loading…"}
      footer={
        <>
          <Button variant="ghost" onClick={onClose}>
            Cancel
          </Button>
          <Button onClick={save} disabled={update.isPending}>
            Save
          </Button>
        </>
      }
    >
      {isLoading || !product || !merch ? (
        <div className="text-sm text-stone-500 py-6 text-center">Loading…</div>
      ) : (
        <div className="space-y-4">
          <div className="text-xs text-stone-500">
            SKU {product.sku} · {product.category_name} — identity, price, and Odoo mapping are
            managed in Odoo and read-only here.
          </div>
          <div className="flex flex-wrap gap-6">
            <Toggle
              checked={merch.featured ?? false}
              onChange={(v) => patch({ featured: v })}
              label="Featured"
            />
            <Toggle
              checked={merch.is_new ?? false}
              onChange={(v) => patch({ is_new: v })}
              label="New"
            />
            <Toggle
              checked={merch.is_bestseller ?? false}
              onChange={(v) => patch({ is_bestseller: v })}
              label="Bestseller"
            />
            <Toggle
              checked={merch.storefront_visible ?? true}
              onChange={(v) => patch({ storefront_visible: v })}
              label="Visible on storefront"
            />
          </div>
          <Field label="Display order">
            <Input
              type="number"
              value={merch.display_order ?? 0}
              onChange={(e) => patch({ display_order: Number(e.target.value) })}
            />
          </Field>
          <div className="grid grid-cols-2 gap-3">
            <Field label="Badge (English)">
              <Input
                value={merch.badge_en ?? ""}
                onChange={(e) => patch({ badge_en: e.target.value || null })}
              />
            </Field>
            <Field label="Badge (Arabic)">
              <Input
                value={merch.badge_ar ?? ""}
                onChange={(e) => patch({ badge_ar: e.target.value || null })}
              />
            </Field>
          </div>
          {product.moment_names.length > 0 && (
            <div className="text-xs text-stone-500">Moments: {product.moment_names.join(", ")}</div>
          )}
          {product.recipient_names.length > 0 && (
            <div className="text-xs text-stone-500">
              Recipients: {product.recipient_names.join(", ")}
            </div>
          )}
        </div>
      )}
    </Modal>
  );
}
