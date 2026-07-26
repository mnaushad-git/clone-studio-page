import { createFileRoute } from "@tanstack/react-router";
import { useState } from "react";
import { useAdmin, settingsStore, paymentStore } from "@/lib/admin-store";
import { Card, Field, Input, Toggle, Button, Modal } from "@/components/admin/ui";
import { Plus, Trash2 } from "lucide-react";

export const Route = createFileRoute("/admin/settings")({ component: SettingsPage });

function SettingsPage() {
  const s = useAdmin((x) => x.settings);
  const payments = useAdmin((x) => x.paymentMethods);
  const [pmOpen, setPmOpen] = useState(false);
  const [pmForm, setPmForm] = useState({ label: "", active: true, fee: 0 });

  function set<K extends keyof typeof s>(key: K, value: (typeof s)[K]) {
    settingsStore.update({ [key]: value } as any);
  }

  return (
    <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
      <Card title="Brand">
        <div className="grid grid-cols-2 gap-3">
          <Field label="Brand name"><Input value={s.brandName} onChange={(e) => set("brandName", e.target.value)} /></Field>
          <Field label="Support email"><Input value={s.supportEmail} onChange={(e) => set("supportEmail", e.target.value)} /></Field>
          <Field label="Support phone"><Input value={s.supportPhone} onChange={(e) => set("supportPhone", e.target.value)} /></Field>
          <Field label="Currency"><Input value={s.currency} onChange={(e) => set("currency", e.target.value)} /></Field>
        </div>
      </Card>

      <Card title="Commerce">
        <div className="grid grid-cols-2 gap-3">
          <Field label="Tax rate (%)"><Input type="number" value={s.taxRate} onChange={(e) => set("taxRate", Number(e.target.value))} /></Field>
          <Field label="Default delivery fee (SAR)"><Input type="number" value={s.defaultDeliveryFee} onChange={(e) => set("defaultDeliveryFee", Number(e.target.value))} /></Field>
          <Field label="Free delivery threshold (SAR)" hint="0 disables"><Input type="number" value={s.freeDeliveryThreshold} onChange={(e) => set("freeDeliveryThreshold", Number(e.target.value))} /></Field>
          <Field label="Minimum order (SAR)"><Input type="number" value={s.minOrder} onChange={(e) => set("minOrder", Number(e.target.value))} /></Field>
        </div>
      </Card>

      <Card title="Operations">
        <div className="grid grid-cols-2 gap-3">
          <Field label="Opens at"><Input type="time" value={s.operatingHours.open} onChange={(e) => set("operatingHours", { ...s.operatingHours, open: e.target.value })} /></Field>
          <Field label="Closes at"><Input type="time" value={s.operatingHours.close} onChange={(e) => set("operatingHours", { ...s.operatingHours, close: e.target.value })} /></Field>
        </div>
        <div className="mt-4 flex flex-col gap-3">
          <Toggle checked={s.maintenanceMode} onChange={(v) => set("maintenanceMode", v)} label="Maintenance mode (block storefront)" />
          <Toggle checked={s.guestCheckout} onChange={(v) => set("guestCheckout", v)} label="Allow guest checkout" />
        </div>
      </Card>

      <Card title="Languages">
        <div className="space-y-2">
          {s.languages.map((l, i) => (
            <div key={l.code} className="flex items-center gap-3 border rounded-lg px-3 py-2">
              <div className="flex-1">
                <div className="font-medium">{l.label}</div>
                <div className="text-xs text-stone-500">{l.code}</div>
              </div>
              <Toggle checked={l.enabled} onChange={(v) => { const langs = [...s.languages]; langs[i] = { ...l, enabled: v }; set("languages", langs); }} />
              <label className="text-xs flex items-center gap-1">
                <input type="radio" checked={s.defaultLanguage === l.code} onChange={() => set("defaultLanguage", l.code)} />
                Default
              </label>
            </div>
          ))}
        </div>
      </Card>

      <Card title="Social links">
        <div className="grid grid-cols-2 gap-3">
          <Field label="Instagram"><Input value={s.socials.instagram ?? ""} onChange={(e) => set("socials", { ...s.socials, instagram: e.target.value })} /></Field>
          <Field label="Twitter / X"><Input value={s.socials.twitter ?? ""} onChange={(e) => set("socials", { ...s.socials, twitter: e.target.value })} /></Field>
          <Field label="Facebook"><Input value={s.socials.facebook ?? ""} onChange={(e) => set("socials", { ...s.socials, facebook: e.target.value })} /></Field>
          <Field label="TikTok"><Input value={s.socials.tiktok ?? ""} onChange={(e) => set("socials", { ...s.socials, tiktok: e.target.value })} /></Field>
        </div>
      </Card>

      <Card
        title="Payment methods"
        action={<Button onClick={() => { setPmForm({ label: "", active: true, fee: 0 }); setPmOpen(true); }}><Plus className="h-4 w-4" /> Add method</Button>}
      >
        <div className="divide-y">
          {payments.map((p) => (
            <div key={p.id} className="flex items-center gap-3 py-3">
              <div className="flex-1">
                <div className="font-medium">{p.label}</div>
                {p.fee ? <div className="text-xs text-stone-500">Fee SAR {p.fee}</div> : null}
              </div>
              <Toggle checked={p.active} onChange={(v) => paymentStore.update(p.id, { active: v })} />
              <Button variant="ghost" onClick={() => { if (confirm("Delete this method?")) paymentStore.remove(p.id); }}><Trash2 className="h-4 w-4 text-red-500" /></Button>
            </div>
          ))}
        </div>
        <Modal open={pmOpen} onClose={() => setPmOpen(false)} title="Add payment method" footer={<><Button variant="outline" onClick={() => setPmOpen(false)}>Cancel</Button><Button onClick={() => { paymentStore.add(pmForm); setPmOpen(false); }}>Save</Button></>}>
          <div className="space-y-3">
            <Field label="Label"><Input value={pmForm.label} onChange={(e) => setPmForm({ ...pmForm, label: e.target.value })} /></Field>
            <Field label="Processing fee (SAR)"><Input type="number" value={pmForm.fee} onChange={(e) => setPmForm({ ...pmForm, fee: Number(e.target.value) })} /></Field>
            <Toggle checked={pmForm.active} onChange={(v) => setPmForm({ ...pmForm, active: v })} label="Active" />
          </div>
        </Modal>
      </Card>
    </div>
  );
}
