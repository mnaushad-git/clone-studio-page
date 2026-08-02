import { createFileRoute } from "@tanstack/react-router";
import { useState, useEffect } from "react";
import { toast } from "sonner";
import {
  useDeliverySettings,
  useUpdateDeliverySettings,
  useDeliverySlots,
  useCreateDeliverySlot,
  useUpdateDeliverySlot,
  useDeleteDeliverySlot,
  type DeliverySettingsInput,
} from "@/lib/admin-api";
import { Card, Button, Input, Toggle, Modal, Field, EmptyState } from "@/components/admin/ui";
import { Plus, Trash2, Pencil } from "lucide-react";

export const Route = createFileRoute("/admin/delivery")({ component: DeliveryPage });

const WEEKDAYS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];

function DeliverySettingsCard() {
  const { data: settings, isLoading } = useDeliverySettings();
  const update = useUpdateDeliverySettings();
  const [form, setForm] = useState<DeliverySettingsInput | null>(null);

  useEffect(() => {
    if (settings && !form) {
      setForm({
        delivery_enabled: settings.delivery_enabled,
        flat_delivery_fee: Number(settings.flat_delivery_fee),
        free_delivery_threshold: Number(settings.free_delivery_threshold),
        minimum_order_amount: Number(settings.minimum_order_amount),
        same_day_delivery_enabled: settings.same_day_delivery_enabled,
        same_day_cutoff_time: settings.same_day_cutoff_time,
        available_days: settings.available_days,
      });
    }
  }, [settings, form]);

  async function save() {
    if (!form) return;
    try {
      await update.mutateAsync(form);
      toast.success("Delivery settings updated — checkout reflects this immediately.");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to save.");
    }
  }

  function toggleDay(day: number) {
    if (!form) return;
    const days = form.available_days ?? [];
    setForm({
      ...form,
      available_days: days.includes(day) ? days.filter((d) => d !== day) : [...days, day].sort(),
    });
  }

  if (isLoading || !form)
    return (
      <Card title="Delivery settings">
        <div className="text-sm text-stone-500 py-6 text-center">Loading…</div>
      </Card>
    );

  return (
    <Card
      title="Delivery settings"
      action={
        <Button onClick={save} disabled={update.isPending}>
          Save
        </Button>
      }
    >
      <div className="space-y-4">
        <Toggle
          checked={form.delivery_enabled ?? true}
          onChange={(v) => setForm({ ...form, delivery_enabled: v })}
          label="Delivery enabled"
        />
        <div className="grid grid-cols-2 gap-3">
          <Field label="Flat delivery fee (SAR)">
            <Input
              type="number"
              value={form.flat_delivery_fee ?? 0}
              onChange={(e) => setForm({ ...form, flat_delivery_fee: Number(e.target.value) })}
            />
          </Field>
          <Field label="Free delivery threshold (SAR)" hint="0 disables">
            <Input
              type="number"
              value={form.free_delivery_threshold ?? 0}
              onChange={(e) =>
                setForm({ ...form, free_delivery_threshold: Number(e.target.value) })
              }
            />
          </Field>
          <Field label="Minimum order (SAR)">
            <Input
              type="number"
              value={form.minimum_order_amount ?? 0}
              onChange={(e) => setForm({ ...form, minimum_order_amount: Number(e.target.value) })}
            />
          </Field>
          <Field label="Same-day cutoff time">
            <Input
              type="time"
              value={form.same_day_cutoff_time ?? ""}
              onChange={(e) => setForm({ ...form, same_day_cutoff_time: e.target.value || null })}
            />
          </Field>
        </div>
        <Toggle
          checked={form.same_day_delivery_enabled ?? false}
          onChange={(v) => setForm({ ...form, same_day_delivery_enabled: v })}
          label="Same-day delivery enabled"
        />
        <div>
          <div className="text-xs font-medium text-stone-600 mb-2">Available delivery days</div>
          <div className="flex gap-2">
            {WEEKDAYS.map((label, day) => (
              <button
                key={day}
                onClick={() => toggleDay(day)}
                className={`h-9 w-12 rounded-lg text-xs font-medium border ${(form.available_days ?? []).includes(day) ? "bg-primary text-primary-foreground border-primary" : "border-stone-300 text-stone-600"}`}
              >
                {label}
              </button>
            ))}
          </div>
        </div>
      </div>
    </Card>
  );
}

function DeliverySlotsCard() {
  const { data: slots, isLoading } = useDeliverySlots();
  const create = useCreateDeliverySlot();
  const update = useUpdateDeliverySlot();
  const remove = useDeleteDeliverySlot();

  const [open, setOpen] = useState(false);
  const [editId, setEditId] = useState<string | null>(null);
  const [form, setForm] = useState({
    label: "",
    start_time: "08:00",
    end_time: "10:00",
    active: true,
    max_orders_per_slot: "",
  });

  function openNew() {
    setEditId(null);
    setForm({
      label: "",
      start_time: "08:00",
      end_time: "10:00",
      active: true,
      max_orders_per_slot: "",
    });
    setOpen(true);
  }

  async function submit() {
    const payload = {
      label: form.label,
      start_time: form.start_time,
      end_time: form.end_time,
      active: form.active,
      max_orders_per_slot: form.max_orders_per_slot ? Number(form.max_orders_per_slot) : null,
    };
    try {
      if (editId) await update.mutateAsync({ slotId: editId, input: payload });
      else await create.mutateAsync(payload);
      toast.success(editId ? "Slot updated." : "Slot created.");
      setOpen(false);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to save slot.");
    }
  }

  async function toggleActive(id: string, active: boolean) {
    try {
      await update.mutateAsync({ slotId: id, input: { active } });
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to update.");
    }
  }

  async function doDelete(id: string) {
    if (!confirm("Delete this delivery slot?")) return;
    try {
      await remove.mutateAsync(id);
      toast.success("Slot deleted.");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to delete.");
    }
  }

  return (
    <Card
      title={slots ? `Delivery slots (${slots.length})` : "Delivery slots"}
      action={
        <Button onClick={openNew}>
          <Plus className="h-4 w-4" /> Add slot
        </Button>
      }
    >
      {isLoading && <div className="text-sm text-stone-500 py-6 text-center">Loading…</div>}
      {!isLoading && slots && slots.length === 0 && (
        <EmptyState title="No delivery slots" hint="Add one so customers can pick a time." />
      )}
      {!isLoading && slots && slots.length > 0 && (
        <div className="divide-y">
          {slots.map((s) => (
            <div key={s.id} className="flex items-center gap-3 py-3">
              <div className="flex-1">
                <div className="font-medium">{s.label}</div>
                <div className="text-xs text-stone-500">
                  {s.start_time} – {s.end_time}
                  {s.max_orders_per_slot ? ` · max ${s.max_orders_per_slot} orders` : ""}
                </div>
              </div>
              <Toggle checked={s.active} onChange={(v) => toggleActive(s.id, v)} />
              <Button
                variant="ghost"
                onClick={() => {
                  setEditId(s.id);
                  setForm({
                    label: s.label,
                    start_time: s.start_time,
                    end_time: s.end_time,
                    active: s.active,
                    max_orders_per_slot: s.max_orders_per_slot?.toString() ?? "",
                  });
                  setOpen(true);
                }}
              >
                <Pencil className="h-4 w-4" />
              </Button>
              <Button variant="ghost" onClick={() => doDelete(s.id)}>
                <Trash2 className="h-4 w-4 text-red-500" />
              </Button>
            </div>
          ))}
        </div>
      )}

      <Modal
        open={open}
        onClose={() => setOpen(false)}
        title={editId ? "Edit slot" : "New slot"}
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
          <Field label="Label">
            <Input
              value={form.label}
              onChange={(e) => setForm({ ...form, label: e.target.value })}
              placeholder="10:00am - 12:00pm"
            />
          </Field>
          <Field label="Max orders" hint="Leave blank for no limit">
            <Input
              type="number"
              value={form.max_orders_per_slot}
              onChange={(e) => setForm({ ...form, max_orders_per_slot: e.target.value })}
            />
          </Field>
          <Field label="Start time">
            <Input
              type="time"
              value={form.start_time}
              onChange={(e) => setForm({ ...form, start_time: e.target.value })}
            />
          </Field>
          <Field label="End time">
            <Input
              type="time"
              value={form.end_time}
              onChange={(e) => setForm({ ...form, end_time: e.target.value })}
            />
          </Field>
          <div className="col-span-2">
            <Toggle
              checked={form.active}
              onChange={(v) => setForm({ ...form, active: v })}
              label="Active"
            />
          </div>
        </div>
      </Modal>
    </Card>
  );
}

function DeliveryPage() {
  return (
    <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
      <DeliverySettingsCard />
      <DeliverySlotsCard />
    </div>
  );
}
