import { Check, Loader2 } from "lucide-react";
import { ORDER_STATUSES, type Order, type OrderStatus } from "@/lib/store";

export function OrderStatusTimeline({ order, compact = false }: { order: Order; compact?: boolean }) {
  const currentIdx = ORDER_STATUSES.indexOf(order.status);

  return (
    <div className={compact ? "py-2" : "py-4"}>
      <div className="flex items-center">
        {ORDER_STATUSES.map((s: OrderStatus, i) => {
          const reached = i <= currentIdx;
          const isCurrent = i === currentIdx;
          const entry = order.statusHistory.find((h) => h.status === s);
          return (
            <div key={s} className="flex-1 flex items-center">
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
                  {s}
                </p>
                {!compact && entry && (
                  <p className="text-[10px] text-muted-foreground mt-0.5">
                    {new Date(entry.at).toLocaleDateString(undefined, { month: "short", day: "numeric" })}
                  </p>
                )}
              </div>
              {i < ORDER_STATUSES.length - 1 && (
                <div className={`h-0.5 flex-1 -mx-2 ${i < currentIdx ? "bg-primary" : "bg-border"}`} />
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
