import { createFileRoute } from "@tanstack/react-router";
import { useState } from "react";
import { useAdmin, zoneStore, slotStore } from "@/lib/admin-store";
import { Card, Button, Input, Toggle, Modal, Field } from "@/components/admin/ui";
import { Plus, Trash2, Pencil } from "lucide-react";

export const Route = createFileRoute("/admin/delivery")({ component: DeliveryPage });

function DeliveryPage() {
  const zones = useAdmin((s) => s.zones);
  const slots = useAdmin((s) => s.slots);
  const [zOpen, setZOpen] = useState(false);
  const [zEdit, setZEdit] = useState<string | null>(null);
  const [zForm, setZForm] = useState({ name: "", fee: 15, etaMinutes: 60, active: true });
  const [sOpen, setSOpen] = useState(false);
  const [sEdit, setSEdit] = useState<string | null>(null);
  const [sForm, setSForm] = useState({ label: "", from: "08:00", to: "10:00", capacity: 20, active: true });

  return (
    <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
      <Card
        title={`Delivery zones (${zones.length})`}
        action={<Button onClick={() => { setZEdit(null); setZForm({ name: "", fee: 15, etaMinutes: 60, active: true }); setZOpen(true); }}><Plus className="h-4 w-4" /> Add zone</Button>}
      >
        <div className="divide-y">
          {zones.map((z) => (
            <div key={z.id} className="flex items-center gap-3 py-3">
              <div className="flex-1">
                <div className="font-medium">{z.name}</div>
                <div className="text-xs text-stone-500">SAR {z.fee} · ~{z.etaMinutes} min ETA</div>
              </div>
              <Toggle checked={z.active} onChange={(v) => zoneStore.update(z.id, { active: v })} />
              <Button variant="ghost" onClick={() => { setZEdit(z.id); setZForm({ name: z.name, fee: z.fee, etaMinutes: z.etaMinutes, active: z.active }); setZOpen(true); }}><Pencil className="h-4 w-4" /></Button>
              <Button variant="ghost" onClick={() => { if (confirm("Delete this zone?")) zoneStore.remove(z.id); }}><Trash2 className="h-4 w-4 text-red-500" /></Button>
            </div>
          ))}
        </div>
        <Modal open={zOpen} onClose={() => setZOpen(false)} title={zEdit ? "Edit zone" : "New zone"} footer={<><Button variant="outline" onClick={() => setZOpen(false)}>Cancel</Button><Button onClick={() => { if (zEdit) zoneStore.update(zEdit, zForm); else zoneStore.add(zForm); setZOpen(false); }}>Save</Button></>}>
          <div className="grid grid-cols-2 gap-3">
            <Field label="Zone name"><Input value={zForm.name} onChange={(e) => setZForm({ ...zForm, name: e.target.value })} /></Field>
            <Field label="Delivery fee (SAR)"><Input type="number" value={zForm.fee} onChange={(e) => setZForm({ ...zForm, fee: Number(e.target.value) })} /></Field>
            <Field label="ETA minutes"><Input type="number" value={zForm.etaMinutes} onChange={(e) => setZForm({ ...zForm, etaMinutes: Number(e.target.value) })} /></Field>
            <div className="flex items-end"><Toggle checked={zForm.active} onChange={(v) => setZForm({ ...zForm, active: v })} label="Active" /></div>
          </div>
        </Modal>
      </Card>

      <Card
        title={`Delivery slots (${slots.length})`}
        action={<Button onClick={() => { setSEdit(null); setSForm({ label: "", from: "08:00", to: "10:00", capacity: 20, active: true }); setSOpen(true); }}><Plus className="h-4 w-4" /> Add slot</Button>}
      >
        <div className="divide-y">
          {slots.map((s) => (
            <div key={s.id} className="flex items-center gap-3 py-3">
              <div className="flex-1">
                <div className="font-medium">{s.label}</div>
                <div className="text-xs text-stone-500">{s.from} – {s.to} · capacity {s.capacity}</div>
              </div>
              <Toggle checked={s.active} onChange={(v) => slotStore.update(s.id, { active: v })} />
              <Button variant="ghost" onClick={() => { setSEdit(s.id); setSForm({ label: s.label, from: s.from, to: s.to, capacity: s.capacity, active: s.active }); setSOpen(true); }}><Pencil className="h-4 w-4" /></Button>
              <Button variant="ghost" onClick={() => { if (confirm("Delete this slot?")) slotStore.remove(s.id); }}><Trash2 className="h-4 w-4 text-red-500" /></Button>
            </div>
          ))}
        </div>
        <Modal open={sOpen} onClose={() => setSOpen(false)} title={sEdit ? "Edit slot" : "New slot"} footer={<><Button variant="outline" onClick={() => setSOpen(false)}>Cancel</Button><Button onClick={() => { if (sEdit) slotStore.update(sEdit, sForm); else slotStore.add(sForm); setSOpen(false); }}>Save</Button></>}>
          <div className="grid grid-cols-2 gap-3">
            <Field label="Label"><Input value={sForm.label} onChange={(e) => setSForm({ ...sForm, label: e.target.value })} placeholder="10:00 AM – 12:00 PM" /></Field>
            <Field label="Capacity"><Input type="number" value={sForm.capacity} onChange={(e) => setSForm({ ...sForm, capacity: Number(e.target.value) })} /></Field>
            <Field label="From"><Input type="time" value={sForm.from} onChange={(e) => setSForm({ ...sForm, from: e.target.value })} /></Field>
            <Field label="To"><Input type="time" value={sForm.to} onChange={(e) => setSForm({ ...sForm, to: e.target.value })} /></Field>
            <div className="col-span-2"><Toggle checked={sForm.active} onChange={(v) => setSForm({ ...sForm, active: v })} label="Active" /></div>
          </div>
        </Modal>
      </Card>
    </div>
  );
}
