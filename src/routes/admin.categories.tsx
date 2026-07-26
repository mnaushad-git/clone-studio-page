import { createFileRoute } from "@tanstack/react-router";
import { useState } from "react";
import { useAdmin, categoryStore } from "@/lib/admin-store";
import { Card, Button, Input, Toggle, Modal, Field } from "@/components/admin/ui";
import { Plus, Trash2, Pencil, ArrowUp, ArrowDown } from "lucide-react";

export const Route = createFileRoute("/admin/categories")({ component: CategoriesPage });

function CategoriesPage() {
  const cats = useAdmin((s) => [...s.categories].sort((a, b) => a.order - b.order));
  const [open, setOpen] = useState(false);
  const [editId, setEditId] = useState<string | null>(null);
  const [form, setForm] = useState({ label: "", slug: "", order: cats.length + 1, visible: true });

  function submit() {
    if (!form.label || !form.slug) return;
    if (editId) categoryStore.update(editId, form);
    else categoryStore.add(form);
    setOpen(false); setEditId(null); setForm({ label: "", slug: "", order: cats.length + 1, visible: true });
  }

  function move(id: string, dir: -1 | 1) {
    const arr = [...cats];
    const i = arr.findIndex((c) => c.id === id);
    const j = i + dir;
    if (j < 0 || j >= arr.length) return;
    const [a, b] = [arr[i], arr[j]];
    categoryStore.update(a.id, { order: b.order });
    categoryStore.update(b.id, { order: a.order });
  }

  return (
    <Card
      title={`Categories (${cats.length})`}
      action={<Button onClick={() => { setEditId(null); setForm({ label: "", slug: "", order: cats.length + 1, visible: true }); setOpen(true); }}><Plus className="h-4 w-4" /> Add category</Button>}
    >
      <div className="divide-y">
        {cats.map((c) => (
          <div key={c.id} className="flex items-center gap-3 py-3">
            <div className="flex flex-col gap-0.5">
              <button className="text-slate-400 hover:text-slate-800" onClick={() => move(c.id, -1)}><ArrowUp className="h-3 w-3" /></button>
              <button className="text-slate-400 hover:text-slate-800" onClick={() => move(c.id, 1)}><ArrowDown className="h-3 w-3" /></button>
            </div>
            <div className="flex-1">
              <div className="font-medium text-slate-800">{c.label}</div>
              <div className="text-xs text-slate-500">/{c.slug}</div>
            </div>
            <Toggle checked={c.visible} onChange={(v) => categoryStore.update(c.id, { visible: v })} label="Visible" />
            <Button variant="ghost" onClick={() => { setEditId(c.id); setForm({ label: c.label, slug: c.slug, order: c.order, visible: c.visible }); setOpen(true); }}><Pencil className="h-4 w-4" /></Button>
            <Button variant="ghost" onClick={() => { if (confirm("Delete this category?")) categoryStore.remove(c.id); }}><Trash2 className="h-4 w-4 text-red-500" /></Button>
          </div>
        ))}
      </div>

      <Modal open={open} onClose={() => setOpen(false)} title={editId ? "Edit category" : "Add category"} footer={<><Button variant="outline" onClick={() => setOpen(false)}>Cancel</Button><Button onClick={submit}>Save</Button></>}>
        <div className="space-y-3">
          <Field label="Label"><Input value={form.label} onChange={(e) => setForm({ ...form, label: e.target.value })} /></Field>
          <Field label="URL slug" hint="Lowercase, no spaces (e.g. cupcakes)"><Input value={form.slug} onChange={(e) => setForm({ ...form, slug: e.target.value.toLowerCase().replace(/\s+/g, "-") })} /></Field>
          <div className="flex items-center gap-6"><Toggle checked={form.visible} onChange={(v) => setForm({ ...form, visible: v })} label="Visible" /></div>
        </div>
      </Modal>
    </Card>
  );
}
