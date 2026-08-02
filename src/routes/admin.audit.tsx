import { createFileRoute } from "@tanstack/react-router";
import { useState } from "react";
import { useAuditEvents, type AdminAuditFilters } from "@/lib/admin-api";
import { Card, Badge, Input, Select, EmptyState, Button } from "@/components/admin/ui";
import { ChevronLeft, ChevronRight } from "lucide-react";

export const Route = createFileRoute("/admin/audit")({ component: AuditPage });

const PAGE_SIZE = 25;

const ACTIONS = [
  "admin.login_succeeded",
  "admin.login_failed",
  "admin.logout",
  "admin.password_changed",
  "admin.order_status_updated",
  "admin.odoo_sync_retry_requested",
  "admin.notification_retry_requested",
  "admin.product_merchandising_updated",
  "admin.promo_code_created",
  "admin.promo_code_updated",
  "admin.promo_code_deleted",
  "admin.delivery_settings_updated",
  "admin.delivery_slot_created",
  "admin.delivery_slot_updated",
  "admin.delivery_slot_deleted",
];

function AuditPage() {
  const [search, setSearch] = useState("");
  const [action, setAction] = useState("");
  const [entityType, setEntityType] = useState("");
  const [offset, setOffset] = useState(0);

  const filters: AdminAuditFilters = {
    search: search || undefined,
    action: action || undefined,
    entity_type: entityType || undefined,
    limit: PAGE_SIZE,
    offset,
  };
  const { data, isLoading, isError, error } = useAuditEvents(filters);

  function resetAndFilter(fn: () => void) {
    fn();
    setOffset(0);
  }

  return (
    <Card
      title={data ? `Audit log (${data.total})` : "Audit log"}
      action={
        <div className="flex flex-wrap gap-2">
          <Input
            placeholder="Search admin/action…"
            value={search}
            onChange={(e) => resetAndFilter(() => setSearch(e.target.value))}
            className="w-56"
          />
          <Select
            value={action}
            onChange={(e) => resetAndFilter(() => setAction(e.target.value))}
            className="w-56"
          >
            <option value="">All actions</option>
            {ACTIONS.map((a) => (
              <option key={a} value={a}>
                {a}
              </option>
            ))}
          </Select>
          <Select
            value={entityType}
            onChange={(e) => resetAndFilter(() => setEntityType(e.target.value))}
            className="w-36"
          >
            <option value="">All entities</option>
            <option value="admin_user">Admin user</option>
            <option value="order">Order</option>
            <option value="product">Product</option>
            <option value="promo_code">Promo code</option>
            <option value="delivery_settings">Delivery settings</option>
            <option value="delivery_slot">Delivery slot</option>
          </Select>
        </div>
      }
    >
      {isLoading && <div className="text-sm text-stone-500 py-6 text-center">Loading…</div>}
      {isError && <div className="text-sm text-red-600 py-6 text-center">{error?.message}</div>}
      {!isLoading && data && data.items.length === 0 && (
        <EmptyState title="No matching audit events" />
      )}
      {!isLoading && data && data.items.length > 0 && (
        <>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="text-left text-xs uppercase text-stone-500 border-b">
                <tr>
                  <th className="py-2">When</th>
                  <th>Admin</th>
                  <th>Action</th>
                  <th>Entity</th>
                  <th>Reason</th>
                </tr>
              </thead>
              <tbody>
                {data.items.map((e) => (
                  <tr key={e.id} className="border-b last:border-0">
                    <td className="py-2.5 text-xs text-stone-500">
                      {new Date(e.created_at).toLocaleString()}
                    </td>
                    <td>{e.admin_email}</td>
                    <td>
                      <Badge tone="info">{e.action}</Badge>
                    </td>
                    <td className="text-xs text-stone-500">
                      {e.entity_type}
                      {e.entity_id ? ` · ${e.entity_id.slice(0, 8)}…` : ""}
                    </td>
                    <td className="text-xs text-stone-500 max-w-xs truncate">{e.reason ?? "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="flex items-center justify-between mt-4 text-sm text-stone-500">
            <span>
              {offset + 1}–{Math.min(offset + PAGE_SIZE, data.total)} of {data.total}
            </span>
            <div className="flex gap-2">
              <Button
                variant="outline"
                disabled={offset === 0}
                onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))}
              >
                <ChevronLeft className="h-4 w-4" /> Prev
              </Button>
              <Button
                variant="outline"
                disabled={offset + PAGE_SIZE >= data.total}
                onClick={() => setOffset(offset + PAGE_SIZE)}
              >
                Next <ChevronRight className="h-4 w-4" />
              </Button>
            </div>
          </div>
        </>
      )}
    </Card>
  );
}
