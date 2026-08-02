import { createFileRoute } from "@tanstack/react-router";
import { useSystemStatus } from "@/lib/admin-api";
import { Card, Badge } from "@/components/admin/ui";
import { RefreshCw } from "lucide-react";

export const Route = createFileRoute("/admin/system")({ component: SystemStatusPage });

function StatusRow({
  label,
  value,
  tone,
}: {
  label: string;
  value: string;
  tone: "success" | "danger" | "warn" | "default" | "info";
}) {
  return (
    <div className="flex items-center justify-between py-2.5 border-b last:border-0 text-sm">
      <span className="text-stone-600">{label}</span>
      <Badge tone={tone}>{value}</Badge>
    </div>
  );
}

function toneFor(v: string): "success" | "danger" | "warn" | "default" {
  if (["up", "synced", "configured"].includes(v)) return "success";
  if (["down", "failed"].includes(v)) return "danger";
  if (v === "unknown" || v === "not_configured") return "warn";
  return "default";
}

function SystemStatusPage() {
  const { data, isLoading, isError, error, refetch, isFetching } = useSystemStatus();

  return (
    <Card
      title="System status"
      action={
        <button
          onClick={() => refetch()}
          className="text-xs text-stone-500 hover:text-stone-800 flex items-center gap-1"
        >
          <RefreshCw className={`h-3 w-3 ${isFetching ? "animate-spin" : ""}`} /> Refresh
        </button>
      }
    >
      {isLoading && <div className="text-sm text-stone-500 py-6 text-center">Loading…</div>}
      {isError && <div className="text-sm text-red-600 py-6 text-center">{error?.message}</div>}
      {data && (
        <div className="max-w-lg space-y-1">
          {data.stub_providers_active && (
            <div className="mb-4 rounded-lg bg-amber-50 border border-amber-200 px-4 py-3 text-sm text-amber-800">
              Development mode: one or more providers below are running as stubs. No real payments,
              Odoo orders, or notifications are being sent.
            </div>
          )}
          <StatusRow label="PostgreSQL" value={data.database} tone={toneFor(data.database)} />
          <StatusRow label="Redis" value={data.redis} tone={toneFor(data.redis)} />
          <StatusRow
            label="Celery worker"
            value={data.celery_worker}
            tone={toneFor(data.celery_worker)}
          />
          <StatusRow
            label="Celery beat"
            value={data.celery_beat}
            tone={toneFor(data.celery_beat)}
          />
          <StatusRow label="Odoo connectivity" value={data.odoo} tone={toneFor(data.odoo)} />
          <StatusRow
            label="Payment provider"
            value={data.payment_provider_mode}
            tone={data.payment_provider_mode === "stub" ? "warn" : "success"}
          />
          <StatusRow
            label="Notification provider"
            value={data.notification_provider_mode}
            tone={data.notification_provider_mode === "stub" ? "warn" : "success"}
          />
          <StatusRow
            label="Odoo order push"
            value={data.odoo_order_push_mode}
            tone={data.odoo_order_push_mode === "stub" ? "warn" : "success"}
          />
        </div>
      )}
    </Card>
  );
}
