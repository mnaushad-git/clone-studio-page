import { createFileRoute } from "@tanstack/react-router";
import { useState } from "react";
import { useAdmin, promoStore, type PromoCode } from "@/lib/admin-store";
import { Card, Button, Input, Toggle, Modal, Field, Select, Badge } from "@/components/admin/ui";
import { Plus, Pencil, Trash2 } from "lucide-react";

export const Route = createFileRoute("/admin/promotions")({ component: PromosPage });

const empty: Omit<PromoCode, "id" | "used"> = { code: "", type: "percent", value: 10, active: true };

function PromosPage() {
  const promos = useAdmin((s) => s.promos);
  const [open, setOpen] = useState(false);
  const [editId, setEditId] = useState<string | null>(null);
  const [form, setForm] = useState({ ...empty });

  function submit() {
    if (!form.code) return;
    const payload = { ...form, code: form.code.toUpperCase() };
    if (editId) promoStore.update(editId, payload);
    else promoStore.add(payload);
    setOpen(false); setEditId(null); setForm({ ...empty });
  }

  return (
    <Card
      title={`Promo codes (${promos.length})`}
      action={<Button onClick={() => { setEditId(null); setForm({ ...empty }); setOpen(true); }}><Plus className="h-4 w-4" /> New promo</Button>}
    >
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="text-left text-xs uppercase text-stone-500 border-b">
            <tr><th className="py-2">Code</th><th>Type</th><th>Value</th><th>Min subtotal</th><th>Used / Limit</th><th>Window</th><th>Active</th><th></th></tr>
          </thead>
          <tbody>
            {promos.map((p) => (
              <tr key={p.id} className="border-b last:border-0 hover:bg-stone-50">
                <td className="py-2.5 font-mono font-medium">{p.code}</td>
                <td><Badge>{p.type}</Badge></td>
                <td>{p.type === "percent" ? `${p.value}%` : `SAR ${p.value}`}</td>
                <td>{p.minSubtotal ? `SAR ${p.minSubtotal}` : "—"}</td>
                <td>{p.used} / {p.usageLimit ?? "∞"}</td>
                <td className="text-xs text-stone-500">{p.startsAt ? `${p.startsAt} → ${p.endsAt ?? "…"}` : "Always"}</td>
                <td><Toggle checked={p.active} onChange={(v) => promoStore.update(p.id, { active: v })} /></td>
                <td className="flex gap-1 py-2">
                  <Button variant="ghost" onClick={() => { setEditId(p.id); setForm({ code: p.code, type: p.type, value: p.value, minSubtotal: p.minSubtotal, usageLimit: p.usageLimit, startsAt: p.startsAt, endsAt: p.endsAt, active: p.active }); setOpen(true); }}><Pencil className="h-4 w-4" /></Button>
                  <Button variant="ghost" onClick={() => { if (confirm("Delete this promo code?")) promoStore.remove(p.id); }}><Trash2 className="h-4 w-4 text-red-500" /></Button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <Modal open={open} onClose={() => setOpen(false)} title={editId ? "Edit promo" : "New promo"} footer={<><Button variant="outline" onClick={() => setOpen(false)}>Cancel</Button><Button onClick={submit}>Save</Button></>}>
        <div className="grid grid-cols-2 gap-3">
          <Field label="Code"><Input value={form.code} onChange={(e) => setForm({ ...form, code: e.target.value.toUpperCase() })} placeholder="WELCOME10" /></Field>
          <Field label="Discount type"><Select value={form.type} onChange={(e) => setForm({ ...form, type: e.target.value as any })}><option value="percent">Percent (%)</option><option value="fixed">Fixed SAR</option></Select></Field>
          <Field label="Value"><Input type="number" value={form.value} onChange={(e) => setForm({ ...form, value: Number(e.target.value) })} /></Field>
          <Field label="Min subtotal (SAR)"><Input type="number" value={form.minSubtotal ?? ""} onChange={(e) => setForm({ ...form, minSubtotal: e.target.value ? Number(e.target.value) : undefined })} /></Field>
          <Field label="Usage limit"><Input type="number" value={form.usageLimit ?? ""} onChange={(e) => setForm({ ...form, usageLimit: e.target.value ? Number(e.target.value) : undefined })} /></Field>
          <Field label="Starts at"><Input type="date" value={form.startsAt ?? ""} onChange={(e) => setForm({ ...form, startsAt: e.target.value || undefined })} /></Field>
          <Field label="Ends at"><Input type="date" value={form.endsAt ?? ""} onChange={(e) => setForm({ ...form, endsAt: e.target.value || undefined })} /></Field>
          <div className="col-span-2"><Toggle checked={form.active} onChange={(v) => setForm({ ...form, active: v })} label="Active" /></div>
        </div>
      </Modal>
    </Card>
  );
}
