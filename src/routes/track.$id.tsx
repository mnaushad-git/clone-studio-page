import { createFileRoute, notFound, Link } from "@tanstack/react-router";
import { Copy, Package, Phone, Share2, User } from "lucide-react";
import { toast } from "sonner";
import { SiteHeader } from "@/components/SiteHeader";
import { SiteFooter } from "@/components/SiteFooter";
import { OrderStatusTimeline } from "@/components/OrderStatusTimeline";
import { useStore } from "@/lib/store";
import { useT } from "@/lib/i18n";

export const Route = createFileRoute("/track/$id")({
  component: TrackPage,
  head: ({ params }) => ({
    meta: [
      { title: `Track order ${params.id} — Terrific Bites` },
      { name: "description", content: "Live delivery status for your Terrific Bites order." },
      { property: "og:title", content: "Track your Terrific Bites order" },
      { property: "og:description", content: "Live status and courier details." },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary_large_image" },
      { name: "robots", content: "noindex" },
    ],
  }),
});

function TrackPage() {
  const t = useT();
  const { id } = Route.useParams();
  const order = useStore((s) => s.orders.find((o) => o.trackingToken === id) ?? null);

  if (!order) {
    return (
      <div className="min-h-screen bg-background text-foreground flex flex-col">
        <SiteHeader />
        <main className="flex-1 max-w-2xl w-full mx-auto px-6 py-16 text-center">
          <Package className="h-10 w-10 text-muted-foreground mx-auto" />
          <h1 className="font-display text-2xl text-primary mt-4">{t("checkoutOrderNotFound")}</h1>
          <p className="mt-2 text-sm text-muted-foreground">
            {t("checkoutTrackingLinkInvalid")}
          </p>
          <Link to="/" className="mt-6 inline-block text-primary underline text-sm">{t("checkoutBackHome")}</Link>
        </main>
        <SiteFooter />
      </div>
    );
  }

  const shareUrl = typeof window !== "undefined" ? `${window.location.origin}/track/${order.trackingToken}` : "";

  const copyLink = async () => {
    try {
      await navigator.clipboard.writeText(shareUrl);
      toast.success(t("checkoutToastLinkCopied"));
    } catch { toast.error(t("checkoutToastCopyFailed")); }
  };

  const share = async () => {
    if (navigator.share) {
      try { await navigator.share({ title: `Terrific Bites order ${order.id}`, url: shareUrl }); } catch {}
    } else {
      copyLink();
    }
  };

  return (
    <div className="min-h-screen bg-background text-foreground flex flex-col">
      <SiteHeader />
      <main className="flex-1 max-w-3xl w-full mx-auto px-4 sm:px-6 py-8">
        <div className="bg-white rounded-2xl border border-border p-6 sm:p-8">
          <div className="flex items-start justify-between flex-wrap gap-3">
            <div>
              <p className="text-xs uppercase tracking-wider text-muted-foreground">{t("checkoutTrackingLabel")}</p>
              <h1 className="font-display text-2xl sm:text-3xl text-primary mt-1">{t("checkoutOrderPrefix")} {order.id}</h1>
              <p className="text-sm text-muted-foreground mt-1">
                {t("checkoutPlacedPrefix")} {new Date(order.createdAt).toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" })}
              </p>
            </div>
            <div className="flex gap-2">
              <button onClick={copyLink} className="inline-flex items-center gap-1 text-xs border border-border rounded-md px-3 py-2 hover:bg-muted">
                <Copy className="h-3 w-3" /> {t("checkoutCopyLink")}
              </button>
              <button onClick={share} className="inline-flex items-center gap-1 text-xs bg-primary text-primary-foreground rounded-md px-3 py-2 hover:bg-primary/90">
                <Share2 className="h-3 w-3" /> {t("checkoutShare")}
              </button>
            </div>
          </div>

          <div className="mt-8">
            <OrderStatusTimeline order={order} />
          </div>

          {order.courier && (
            <div className="mt-8 border-t border-border pt-6">
              <p className="text-xs uppercase tracking-wider text-muted-foreground">{t("checkoutYourCourier")}</p>
              <div className="mt-3 flex items-center justify-between flex-wrap gap-3">
                <div className="flex items-center gap-3">
                  <div className="h-12 w-12 rounded-full bg-primary/10 flex items-center justify-center">
                    <User className="h-5 w-5 text-primary" />
                  </div>
                  <div>
                    <div className="font-semibold text-primary">{order.courier.name}</div>
                    <div className="text-xs text-muted-foreground">{t("checkoutOnTheWayPartner")}</div>
                  </div>
                </div>
                <a href={`tel:${order.courier.phone}`} className="inline-flex items-center gap-1 text-sm text-primary underline">
                  <Phone className="h-4 w-4" /> {order.courier.phone}
                </a>
              </div>
            </div>
          )}

          <div className="mt-8 border-t border-border pt-6 grid sm:grid-cols-2 gap-6 text-sm">
            <div>
              <p className="text-xs uppercase tracking-wider text-muted-foreground">{t("checkoutDeliverTo")}</p>
              <p className="mt-2 font-semibold">{order.address?.name ?? "—"}</p>
              <p className="text-muted-foreground">{order.address?.address ?? "—"}</p>
              {order.address?.deliveryDate && (
                <p className="mt-2 text-xs text-muted-foreground">
                  {order.address.deliveryDate}{order.address.deliveryTime ? ` · ${order.address.deliveryTime}` : ""}
                </p>
              )}
            </div>
            <div>
              <p className="text-xs uppercase tracking-wider text-muted-foreground">{t("checkoutItems")}</p>
              <ul className="mt-2 space-y-1 text-muted-foreground">
                {order.items.map((it, i) => (
                  <li key={i}>{it.qty} × {it.name}{it.size ? ` (${it.size})` : ""}</li>
                ))}
              </ul>
              <p className="mt-3 font-semibold text-primary">{t("checkoutTableTotal")} ${order.total.toFixed(2)}</p>
            </div>
          </div>
        </div>
      </main>
      <SiteFooter />
    </div>
  );
}
