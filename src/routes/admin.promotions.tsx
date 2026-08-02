import { createFileRoute } from "@tanstack/react-router";
import { useState } from "react";
import { toast } from "sonner";
import {
  usePromoCodes,
  useCreatePromoCode,
  useUpdatePromoCode,
  useDeletePromoCode,
  type PromoCodeInput,
  type PromoCodeOut,
} from "@/lib/admin-api";
import {
  Card,
  Button,
  Input,
  Toggle,
  Modal,
  Field,
  Select,
  Badge,
  EmptyState,
} from "@/components/admin/ui";
import { Plus, Pencil, Trash2 } from "lucide-react";

export const Route = createFileRoute("/admin/promotions")({ component: PromosPage });

const empty: PromoCodeInput = {
  code: "",
  discount_type: "PERCENTAGE",
  discount_value: 10,
  is_active: true,
};

function toDateInput(iso: string | null): string {
  return iso ? iso.slice(0, 10) : "";
}
function fromDateInput(v: string): string | null {
  return v ? new Date(v).toISOString() : null;
}

function PromosPage() {
  const { data, isLoading, isError, error } = usePromoCodes();
  const create = useCreatePromoCode();
  const update = useUpdatePromoCode();
  const remove = useDeletePromoCode();

  const [open, setOpen] = useState(false);
  const [editId, setEditId] = useState<string | null>(null);
  const [form, setForm] = useState<PromoCodeInput>({ ...empty });

  function openNew() {
    setEditId(null);
    setForm({ ...empty });
    setOpen(true);
  }
  function openEdit(p: PromoCodeOut) {
    setEditId(p.id);
    setForm({
      code: p.code,
      discount_type: p.discount_type,
      discount_value: Number(p.discount_value),
      minimum_order_amount: Number(p.minimum_order_amount),
      maximum_discount_amount: p.maximum_discount_amount ? Number(p.maximum_discount_amount) : null,
      valid_from: p.valid_from,
      valid_until: p.valid_until,
      usage_limit: p.usage_limit,
      per_customer_limit: p.per_customer_limit,
      is_active: p.is_active,
    });
    setOpen(true);
  }

  async function submit() {
    if (!form.code?.trim()) return;
    try {
      if (editId) {
        const { code: _code, ...updatable } = form;
        await update.mutateAsync({ promoId: editId, input: updatable });
      } else {
        await create.mutateAsync(form);
      }
      toast.success(editId ? "Promo code updated." : "Promo code created.");
      setOpen(false);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to save promo code.");
    }
  }

  async function toggleActive(p: PromoCodeOut) {
    try {
      await update.mutateAsync({ promoId: p.id, input: { is_active: !p.is_active } });
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to update.");
    }
  }

  async function doDelete(p: PromoCodeOut) {
    if (!confirm(`Delete promo code ${p.code}?`)) return;
    try {
      await remove.mutateAsync(p.id);
      toast.success("Promo code deleted.");
    } catch (err) {
      toast.error(
        err instanceof Error
          ? err.message
          : "Could not delete — deactivate it instead if it's been used.",
      );
    }
  }

  return (
    <Card
      title={data ? `Promo codes (${data.total})` : "Promo codes"}
      action={
        <Button onClick={openNew}>
          <Plus className="h-4 w-4" /> New promo
        </Button>
      }
    >
      {isLoading && <div className="text-sm text-stone-500 py-6 text-center">Loading…</div>}
      {isError && <div className="text-sm text-red-600 py-6 text-center">{error?.message}</div>}
      {!isLoading && data && data.items.length === 0 && (
        <EmptyState title="No promo codes yet" hint="Create one to get started." />
      )}
      {!isLoading && data && data.items.length > 0 && (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="text-left text-xs uppercase text-stone-500 border-b">
              <tr>
                <th className="py-2">Code</th>
                <th>Type</th>
                <th>Value</th>
                <th>Min order</th>
                <th>Used / Limit</th>
                <th>Window</th>
                <th>Active</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {data.items.map((p) => (
                <tr key={p.id} className="border-b last:border-0 hover:bg-stone-50">
                  <td className="py-2.5 font-mono font-medium">{p.code}</td>
                  <td>
                    <Badge>{p.discount_type === "PERCENTAGE" ? "Percent" : "Fixed"}</Badge>
                  </td>
                  <td>
                    {p.discount_type === "PERCENTAGE"
                      ? `${p.discount_value}%`
                      : `SAR ${p.discount_value}`}
                  </td>
                  <td>
                    {Number(p.minimum_order_amount) > 0 ? `SAR ${p.minimum_order_amount}` : "—"}
                  </td>
                  <td>
                    {p.usage_count} / {p.usage_limit ?? "∞"}
                  </td>
                  <td className="text-xs text-stone-500">
                    {p.valid_from
                      ? `${toDateInput(p.valid_from)} → ${toDateInput(p.valid_until) || "…"}`
                      : "Always"}
                  </td>
                  <td>
                    <Toggle checked={p.is_active} onChange={() => toggleActive(p)} />
                  </td>
                  <td className="flex gap-1 py-2">
                    <Button variant="ghost" onClick={() => openEdit(p)}>
                      <Pencil className="h-4 w-4" />
                    </Button>
                    <Button variant="ghost" onClick={() => doDelete(p)}>
                      <Trash2 className="h-4 w-4 text-red-500" />
                    </Button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <Modal
        open={open}
        onClose={() => setOpen(false)}
        title={editId ? "Edit promo" : "New promo"}
        footer={
          <>
            <Button variant="outline" onClick={() => setOpen(false)}>
              Cancel
            </Button>
            <Button onClick={submit} disabled={create.isPending || update.isPending}>
              Save
            </Button>
          </>
        }
      >
        <div className="grid grid-cols-2 gap-3">
          <Field label="Code">
            <Input
              value={form.code ?? ""}
              disabled={!!editId}
              onChange={(e) => setForm({ ...form, code: e.target.value.toUpperCase() })}
              placeholder="WELCOME10"
            />
          </Field>
          <Field label="Discount type">
            <Select
              value={form.discount_type}
              onChange={(e) =>
                setForm({
                  ...form,
                  discount_type: e.target.value as PromoCodeInput["discount_type"],
                })
              }
            >
              <option value="PERCENTAGE">Percent (%)</option>
              <option value="FIXED_AMOUNT">Fixed SAR</option>
            </Select>
          </Field>
          <Field label="Value">
            <Input
              type="number"
              value={form.discount_value ?? 0}
              onChange={(e) => setForm({ ...form, discount_value: Number(e.target.value) })}
            />
          </Field>
          <Field label="Min order (SAR)">
            <Input
              type="number"
              value={form.minimum_order_amount ?? ""}
              onChange={(e) =>
                setForm({
                  ...form,
                  minimum_order_amount: e.target.value ? Number(e.target.value) : undefined,
                })
              }
            />
          </Field>
          <Field label="Max discount (SAR)" hint="Caps a percentage discount">
            <Input
              type="number"
              value={form.maximum_discount_amount ?? ""}
              onChange={(e) =>
                setForm({
                  ...form,
                  maximum_discount_amount: e.target.value ? Number(e.target.value) : null,
                })
              }
            />
          </Field>
          <Field label="Usage limit">
            <Input
              type="number"
              value={form.usage_limit ?? ""}
              onChange={(e) =>
                setForm({ ...form, usage_limit: e.target.value ? Number(e.target.value) : null })
              }
            />
          </Field>
          <Field label="Valid from">
            <Input
              type="date"
              value={toDateInput(form.valid_from ?? null)}
              onChange={(e) => setForm({ ...form, valid_from: fromDateInput(e.target.value) })}
            />
          </Field>
          <Field label="Valid until">
            <Input
              type="date"
              value={toDateInput(form.valid_until ?? null)}
              onChange={(e) => setForm({ ...form, valid_until: fromDateInput(e.target.value) })}
            />
          </Field>
          <Field label="Description">
            <Input
              value={form.description ?? ""}
              onChange={(e) => setForm({ ...form, description: e.target.value || null })}
            />
          </Field>
          <div className="col-span-2">
            <Toggle
              checked={form.is_active ?? true}
              onChange={(v) => setForm({ ...form, is_active: v })}
              label="Active"
            />
          </div>
        </div>
      </Modal>
    </Card>
  );
}
