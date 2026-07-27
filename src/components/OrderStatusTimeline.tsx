import { Check, Loader2 } from "lucide-react";
import { ORDER_STATUSES, type Order, type OrderStatus } from "@/lib/store";
import { useT } from "@/lib/i18n";

function formatStamp(at: number) {
  const d = new Date(at);
  return {
    date: d.toLocaleDateString(undefined, { month: "short", day: "numeric" }),
    time: d.toLocaleTimeString(undefined, { hour: "numeric", minute: "2-digit" }),
  };
}

const statusKey: Record<OrderStatus, "checkoutStatusProcessing" | "checkoutStatusPaid" | "checkoutStatusDelivered"> = {
  Processing: "checkoutStatusProcessing",
  Paid: "checkoutStatusPaid",
  Delivered: "checkoutStatusDelivered",
};

export function OrderStatusTimeline({ order, compact = false }: { order: Order; compact?: boolean }) {
  const t = useT();
  const currentIdx = ORDER_STATUSES.indexOf(order.status);

  return (
    <div className={compact ? "py-2" : "py-4"}>
      <div className="flex items-start">
        {ORDER_STATUSES.map((s: OrderStatus, i) => {
          const reached = i <= currentIdx;
          const isCurrent = i === currentIdx;
          const entry = order.statusHistory.find((h) => h.status === s);
          const stamp = entry ? formatStamp(entry.at) : null;
          return (
            <div key={s} className="flex-1 flex items-start">
              <div className="flex flex-col items-center flex-1">
                <div
                  className={`h-8 w-8 rounded-full flex items-center justify-center text-xs font-semibold transition ${
                    reached
                      ? "bg-primary text-primary-foreground"
                      : "bg-secondary text-muted-foreground"
                  }`}
                >
                  {isCurrent && s !== "Delivered" ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : reached ? (
                    <Check className="h-4 w-4" />
                  ) : (
                    i + 1
                  )}
                </div>
                <p className={`mt-2 text-xs font-medium ${reached ? "text-foreground" : "text-muted-foreground"}`}>
                  {t(statusKey[s])}
                </p>
                {stamp ? (
                  <>
                    <p className="text-[10px] text-muted-foreground mt-0.5">{stamp.date}</p>
                    <p className="text-[10px] text-muted-foreground leading-tight">{stamp.time}</p>
                  </>
                ) : (
                  <p className="text-[10px] text-muted-foreground/60 mt-0.5">{t("checkoutStatusPending")}</p>
                )}
              </div>
              {i < ORDER_STATUSES.length - 1 && (
                <div className={`h-0.5 flex-1 mt-4 -mx-2 ${i < currentIdx ? "bg-primary" : "bg-border"}`} />
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

