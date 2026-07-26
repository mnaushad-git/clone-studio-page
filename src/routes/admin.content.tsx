import { createFileRoute } from "@tanstack/react-router";
import { useState } from "react";
import { useAdmin, bannerStore, homepageStore } from "@/lib/admin-store";
import { Card, Button, Input, Toggle, Modal, Field, Select, Textarea, Badge } from "@/components/admin/ui";
import { Plus, Pencil, Trash2, ArrowUp, ArrowDown } from "lucide-react";

export const Route = createFileRoute("/admin/content")({ component: ContentPage });

function ContentPage() {
  const banners = useAdmin((s) => [...s.banners].sort((a, b) => a.order - b.order));
  const sections = useAdmin((s) => [...s.homepageSections].sort((a, b) => a.order - b.order));
  const [open, setOpen] = useState(false);
  const [editId, setEditId] = useState<string | null>(null);
  const [form, setForm] = useState<{ title: string; subtitle: string; ctaLabel: string; ctaLink: string; image: string; position: "hero" | "midpage" | "footer"; active: boolean; order: number }>({ title: "", subtitle: "", ctaLabel: "", ctaLink: "", image: "", position: "hero", active: true, order: banners.length + 1 });

  function moveSection(id: string, dir: -1 | 1) {
    const arr = [...sections];
    const i = arr.findIndex((s) => s.id === id);
    const j = i + dir;
    if (j < 0 || j >= arr.length) return;
    const [a, b] = [arr[i], arr[j]];
    homepageStore.update(a.id, { order: b.order });
    homepageStore.update(b.id, { order: a.order });
  }

  return (
    <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
      <Card
        title={`Banners (${banners.length})`}
        action={<Button onClick={() => { setEditId(null); setForm({ title: "", subtitle: "", ctaLabel: "", ctaLink: "", image: "", position: "hero", active: true, order: banners.length + 1 }); setOpen(true); }}><Plus className="h-4 w-4" /> Add banner</Button>}
      >
        <div className="space-y-3">
          {banners.map((b) => (
            <div key={b.id} className="border rounded-lg p-3 flex gap-3">
              <div className="h-16 w-24 rounded bg-stone-100 flex items-center justify-center text-stone-400 text-xs">
                {b.image ? <img src={b.image} className="h-full w-full object-cover rounded" alt="" /> : "No image"}
              </div>
              <div className="flex-1">
                <div className="flex items-center gap-2">
                  <div className="font-medium">{b.title}</div>
                  <Badge tone="info">{b.position}</Badge>
                </div>
                <div className="text-xs text-stone-500">{b.subtitle}</div>
                {b.ctaLabel && <div className="text-xs text-stone-500 mt-1">CTA: {b.ctaLabel} → {b.ctaLink}</div>}
              </div>
              <div className="flex flex-col items-end gap-2">
                <Toggle checked={b.active} onChange={(v) => bannerStore.update(b.id, { active: v })} />
                <div className="flex gap-1">
                  <Button variant="ghost" onClick={() => { setEditId(b.id); setForm({ title: b.title, subtitle: b.subtitle ?? "", ctaLabel: b.ctaLabel ?? "", ctaLink: b.ctaLink ?? "", image: b.image ?? "", position: b.position, active: b.active, order: b.order }); setOpen(true); }}><Pencil className="h-4 w-4" /></Button>
                  <Button variant="ghost" onClick={() => { if (confirm("Delete banner?")) bannerStore.remove(b.id); }}><Trash2 className="h-4 w-4 text-red-500" /></Button>
                </div>
              </div>
            </div>
          ))}
        </div>
        <Modal open={open} onClose={() => setOpen(false)} title={editId ? "Edit banner" : "New banner"} footer={<><Button variant="outline" onClick={() => setOpen(false)}>Cancel</Button><Button onClick={() => { if (editId) bannerStore.update(editId, form); else bannerStore.add(form); setOpen(false); }}>Save</Button></>}>
          <div className="space-y-3">
            <Field label="Title"><Input value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} /></Field>
            <Field label="Subtitle"><Textarea rows={2} value={form.subtitle} onChange={(e) => setForm({ ...form, subtitle: e.target.value })} /></Field>
            <div className="grid grid-cols-2 gap-3">
              <Field label="CTA label"><Input value={form.ctaLabel} onChange={(e) => setForm({ ...form, ctaLabel: e.target.value })} /></Field>
              <Field label="CTA link"><Input value={form.ctaLink} onChange={(e) => setForm({ ...form, ctaLink: e.target.value })} placeholder="/cupcakes" /></Field>
              <Field label="Position"><Select value={form.position} onChange={(e) => setForm({ ...form, position: e.target.value as any })}><option value="hero">Hero</option><option value="midpage">Mid-page</option><option value="footer">Footer</option></Select></Field>
              <Field label="Order"><Input type="number" value={form.order} onChange={(e) => setForm({ ...form, order: Number(e.target.value) })} /></Field>
            </div>
            <Field label="Image URL" hint="Paste a public URL or asset path"><Input value={form.image} onChange={(e) => setForm({ ...form, image: e.target.value })} /></Field>
            <Toggle checked={form.active} onChange={(v) => setForm({ ...form, active: v })} label="Active" />
          </div>
        </Modal>
      </Card>

      <Card title="Homepage sections">
        <div className="text-xs text-stone-500 mb-3">Toggle visibility and reorder the homepage.</div>
        <div className="divide-y">
          {sections.map((s) => (
            <div key={s.id} className="flex items-center gap-3 py-3">
              <div className="flex flex-col gap-0.5">
                <button className="text-stone-400 hover:text-stone-800" onClick={() => moveSection(s.id, -1)}><ArrowUp className="h-3 w-3" /></button>
                <button className="text-stone-400 hover:text-stone-800" onClick={() => moveSection(s.id, 1)}><ArrowDown className="h-3 w-3" /></button>
              </div>
              <div className="flex-1 font-medium text-stone-800">{s.label}</div>
              <Toggle checked={s.visible} onChange={(v) => homepageStore.update(s.id, { visible: v })} />
            </div>
          ))}
        </div>
      </Card>
    </div>
  );
}
