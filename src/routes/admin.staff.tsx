import { createFileRoute } from "@tanstack/react-router";
import { useState } from "react";
import { useAdmin, staffStore, ROLES, type Role } from "@/lib/admin-store";
import { Card, Button, Input, Select, Toggle, Modal, Field, Badge } from "@/components/admin/ui";
import { Plus, Pencil, Trash2 } from "lucide-react";

export const Route = createFileRoute("/admin/staff")({ component: StaffPage });

function StaffPage() {
  const staff = useAdmin((s) => s.staff);
  const [open, setOpen] = useState(false);
  const [editId, setEditId] = useState<string | null>(null);
  const [form, setForm] = useState({ name: "", email: "", phone: "", role: "support" as Role, active: true });

  function submit() {
    if (!form.name || !form.email) return;
    if (editId) staffStore.update(editId, form);
    else staffStore.add(form);
    setOpen(false); setEditId(null); setForm({ name: "", email: "", phone: "", role: "support", active: true });
  }

  return (
    <Card
      title={`Staff (${staff.length})`}
      action={<Button onClick={() => { setEditId(null); setForm({ name: "", email: "", phone: "", role: "support", active: true }); setOpen(true); }}><Plus className="h-4 w-4" /> Invite staff</Button>}
    >
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="text-left text-xs uppercase text-slate-500 border-b">
            <tr><th className="py-2">Name</th><th>Email</th><th>Phone</th><th>Role</th><th>Active</th><th>Joined</th><th></th></tr>
          </thead>
          <tbody>
            {staff.map((m) => (
              <tr key={m.id} className="border-b last:border-0 hover:bg-slate-50">
                <td className="py-2.5 font-medium">{m.name}</td>
                <td>{m.email}</td>
                <td className="text-slate-500">{m.phone ?? "—"}</td>
                <td><Badge tone={m.role === "owner" ? "warn" : m.role === "admin" ? "info" : "default"}>{m.role}</Badge></td>
                <td><Toggle checked={m.active} onChange={(v) => staffStore.update(m.id, { active: v })} /></td>
                <td className="text-slate-500 text-xs">{new Date(m.createdAt).toLocaleDateString()}</td>
                <td className="flex gap-1 py-2">
                  <Button variant="ghost" onClick={() => { setEditId(m.id); setForm({ name: m.name, email: m.email, phone: m.phone ?? "", role: m.role, active: m.active }); setOpen(true); }}><Pencil className="h-4 w-4" /></Button>
                  {m.role !== "owner" && <Button variant="ghost" onClick={() => { if (confirm("Remove this staff member?")) staffStore.remove(m.id); }}><Trash2 className="h-4 w-4 text-red-500" /></Button>}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <Modal open={open} onClose={() => setOpen(false)} title={editId ? "Edit staff" : "Invite staff"} footer={<><Button variant="outline" onClick={() => setOpen(false)}>Cancel</Button><Button onClick={submit}>Save</Button></>}>
        <div className="grid grid-cols-2 gap-3">
          <Field label="Full name"><Input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} /></Field>
          <Field label="Work email"><Input type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} /></Field>
          <Field label="Phone"><Input value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} /></Field>
          <Field label="Role"><Select value={form.role} onChange={(e) => setForm({ ...form, role: e.target.value as Role })}>{ROLES.map((r) => <option key={r} value={r}>{r}</option>)}</Select></Field>
          <div className="col-span-2"><Toggle checked={form.active} onChange={(v) => setForm({ ...form, active: v })} label="Active" /></div>
        </div>
      </Modal>
    </Card>
  );
}
