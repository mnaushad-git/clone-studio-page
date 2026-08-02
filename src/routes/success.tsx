import { createFileRoute, Link } from "@tanstack/react-router";
import { CheckCircle2, Download, Home, MapPin, Truck, ShoppingBag } from "lucide-react";
import jsPDF from "jspdf";
import { useStore } from "@/lib/store";
import { SiteHeader } from "@/components/SiteHeader";
import { OrderStatusTimeline } from "@/components/OrderStatusTimeline";
import { formatAttributes } from "@/lib/format-variant-attributes";
import { useT } from "@/lib/i18n";

export const Route = createFileRoute("/success")({
  component: SuccessPage,
  head: () => ({
    meta: [
      { title: "Order Confirmed — Terrific Bites" },
      { name: "description", content: "Thank you! Your Terrific Bites order is confirmed." },
      { property: "og:title", content: "Order Confirmed — Terrific Bites" },
      { property: "og:description", content: "Your sweet order is on its way." },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary_large_image" },
      { name: "robots", content: "noindex" },
    ],
  }),
});

function SuccessPage() {
  const t = useT();
  const lastOrderId = useStore((s) => s.lastOrderId);
  const order = useStore((s) => s.orders.find((o) => o.id === s.lastOrderId) ?? null);

  const downloadInvoice = () => {
    if (!order) return;
    const doc = new jsPDF({ unit: "pt", format: "a4" });
    const w = doc.internal.pageSize.getWidth();
    let y = 60;

    doc.setFont("helvetica", "bold");
    doc.setFontSize(22);
    doc.text("Terrific Bites", 40, y);
    doc.setFont("helvetica", "normal");
    doc.setFontSize(11);
    doc.text(t("checkoutInvoiceReceipt"), w - 40, y, { align: "right" });

    y += 30;
    doc.setDrawColor(200);
    doc.line(40, y, w - 40, y);
    y += 25;

    doc.setFontSize(10);
    doc.text(`${t("checkoutOrderNumberLabel")} ${order.id}`, 40, y);
    doc.text(`${t("checkoutDateLabel")} ${new Date(order.createdAt).toLocaleString()}`, w - 40, y, { align: "right" });
    y += 16;
    doc.text(`${t("checkoutCustomerLabel")} ${order.address?.name ?? t("checkoutGuestFallback")}`, 40, y);
    y += 16;
    doc.text(`${t("checkoutDeliverTo")}: ${order.address?.address ?? "—"}`, 40, y);
    y += 16;
    doc.text(`${t("checkoutStepPayment")}: ${order.method}`, 40, y);

    y += 30;
    doc.setFont("helvetica", "bold");
    doc.text(t("checkoutTableItem"), 40, y);
    doc.text(t("checkoutQty"), 320, y);
    doc.text(t("checkoutTablePrice"), 400, y);
    doc.text(t("checkoutTableTotal"), w - 40, y, { align: "right" });
    y += 8;
    doc.line(40, y, w - 40, y);
    y += 18;
    doc.setFont("helvetica", "normal");

    order.items.forEach((it) => {
      const variant = formatAttributes(it.attributes);
      doc.text(it.name + (variant ? ` (${variant})` : ""), 40, y);
      doc.text(String(it.qty), 320, y);
      doc.text(`SAR ${it.unitPrice.toFixed(2)}`, 400, y);
      doc.text(`SAR ${(it.qty * it.unitPrice).toFixed(2)}`, w - 40, y, { align: "right" });
      y += 18;
    });

    y += 10;
    doc.line(40, y, w - 40, y);
    y += 20;
    doc.text(t("checkoutSubtotal"), 400, y);
    doc.text(`SAR ${order.subtotal.toFixed(2)}`, w - 40, y, { align: "right" });
    if (order.discount > 0) {
      y += 16;
      doc.text(t("checkoutDiscount"), 400, y);
      doc.text(`-SAR ${order.discount.toFixed(2)}`, w - 40, y, { align: "right" });
    }
    y += 16;
    doc.text(t("checkoutDelivery"), 400, y);
    doc.text(order.deliveryFee === 0 ? t("checkoutFree") : `SAR ${order.deliveryFee.toFixed(2)}`, w - 40, y, { align: "right" });
    y += 16;
    doc.text(t("checkoutTax"), 400, y);
    doc.text(`SAR ${order.tax.toFixed(2)}`, w - 40, y, { align: "right" });
    y += 20;
    doc.setFont("helvetica", "bold");
    doc.setFontSize(12);
    doc.text(t("checkoutTableTotal"), 400, y);
    doc.text(`SAR ${order.total.toFixed(2)}`, w - 40, y, { align: "right" });

    y += 50;
    doc.setFont("helvetica", "normal");
    doc.setFontSize(10);
    doc.text(t("checkoutThankYouFooter"), 40, y);

    doc.save(`invoice-${order.id}.pdf`);
  };

  if (!lastOrderId || !order) {
    return (
      <div className="min-h-screen bg-background flex flex-col">
        <SiteHeader />
        <main className="flex-1 max-w-md w-full mx-auto px-6 py-16 text-center">
          <ShoppingBag className="h-12 w-12 mx-auto text-muted-foreground" />
          <h1 className="mt-4 font-display text-2xl text-primary">{t("checkoutNoRecentOrder")}</h1>
          <p className="text-sm text-muted-foreground mt-2">{t("checkoutNoOrderYet")}</p>
          <Link to="/chocolates" className="mt-6 inline-block bg-primary text-primary-foreground rounded-md px-6 py-3 text-sm">
            {t("checkoutBrowseProducts")}
          </Link>
        </main>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background text-foreground flex flex-col">
      <SiteHeader />

      <main className="flex-1 max-w-3xl w-full mx-auto px-6 py-10">
        <div className="bg-white rounded-2xl shadow-sm p-8 text-center">
          <div className="mx-auto h-16 w-16 rounded-full bg-primary/10 flex items-center justify-center">
            <CheckCircle2 className="h-9 w-9 text-primary" />
          </div>
          <h1 className="font-script text-4xl text-primary mt-4">{t("checkoutThankYou")}</h1>
          <p className="text-sm text-muted-foreground mt-2">{t("checkoutOrderConfirmedCopy")}</p>
          <div className="mt-4 inline-flex items-center gap-2 bg-secondary rounded-full px-4 py-1.5 text-sm">
            {t("checkoutOrderHash")} <span className="font-semibold">{order.id}</span>
          </div>
        </div>

        <div className="bg-white rounded-2xl shadow-sm p-6 mt-6">
          <div className="flex items-center justify-between mb-2">
            <h2 className="font-semibold">{t("checkoutOrderStatus")}</h2>
          </div>
          <OrderStatusTimeline order={order} />
          {order.trackingToken && (
            <div className="mt-4 flex items-center justify-between rounded-lg border border-border bg-secondary/40 px-3 py-2 text-xs">
              <span className="truncate">{t("checkoutShareTrackingLabel")} <span className="font-mono">/track/{order.trackingToken}</span></span>
              <div className="flex gap-2 shrink-0">
                <Link to="/track/$id" params={{ id: order.trackingToken }} className="text-primary font-medium hover:underline">{t("checkoutOpen")}</Link>
                <button
                  onClick={() => navigator.clipboard?.writeText(`${window.location.origin}/track/${order.trackingToken}`)}
                  className="text-primary font-medium hover:underline"
                >{t("checkoutCopyLink")}</button>
              </div>
            </div>
          )}
          {order.pointsEarned ? (
            <div className="mt-3 rounded-lg bg-primary/10 text-primary text-xs px-3 py-2 font-medium">
              🎉 {t("checkoutLoyaltyEarnedPrefix")} {order.pointsEarned} {t("checkoutLoyaltyEarnedSuffix")}
            </div>
          ) : null}
        </div>

        <div className="bg-white rounded-2xl shadow-sm p-6 mt-6">
          <h2 className="font-semibold mb-4">{t("checkoutOrderDetails")}</h2>
          <div className="divide-y divide-border">
            {order.items.map((it, i) => (
              <div key={i} className="flex items-center justify-between py-3 text-sm">
                <div>
                  <p className="font-medium">{it.name}</p>
                  <p className="text-xs text-muted-foreground">
                    {t("checkoutQty")} {it.qty}{formatAttributes(it.attributes) ? ` · ${formatAttributes(it.attributes)}` : ""}
                  </p>
                  {it.inscription && <p className="text-xs italic text-muted-foreground">"{it.inscription}"</p>}
                </div>
                <p>SAR {(it.qty * it.unitPrice).toFixed(2)}</p>
              </div>
            ))}
          </div>
          <div className="border-t border-border mt-4 pt-4 space-y-2 text-sm">
            <div className="flex justify-between"><span>{t("checkoutSubtotal")}</span><span>SAR {order.subtotal.toFixed(2)}</span></div>
            {order.discount > 0 && <div className="flex justify-between text-primary"><span>{t("checkoutDiscount")}</span><span>-SAR {order.discount.toFixed(2)}</span></div>}
            <div className="flex justify-between"><span>{t("checkoutDelivery")}</span><span>{order.deliveryFee === 0 ? t("checkoutFree") : `SAR ${order.deliveryFee.toFixed(2)}`}</span></div>
            <div className="flex justify-between"><span>{t("checkoutTax")}</span><span>SAR {order.tax.toFixed(2)}</span></div>
            <div className="flex justify-between font-semibold text-base pt-2 border-t border-border">
              <span>{t("checkoutTableTotal")}</span><span>SAR {order.total.toFixed(2)}</span>
            </div>
          </div>

          <div className="mt-6 grid sm:grid-cols-2 gap-3 text-sm">
            <div className="flex items-start gap-2">
              <MapPin className="h-4 w-4 text-primary mt-0.5" />
              <div>
                <p className="text-xs text-muted-foreground">{t("checkoutDeliverTo")}</p>
                <p className="font-medium">{order.address?.name ?? "—"}</p>
                <p className="text-xs text-muted-foreground">{order.address?.address ?? "—"}</p>
              </div>
            </div>
            <div className="flex items-start gap-2">
              <Truck className="h-4 w-4 text-primary mt-0.5" />
              <div>
                <p className="text-xs text-muted-foreground">{t("checkoutStepPayment")}</p>
                <p className="font-medium">{order.method}</p>
              </div>
            </div>
          </div>
        </div>

        <div className="mt-6 flex flex-col sm:flex-row gap-3">
          <button onClick={downloadInvoice} className="flex-1 bg-primary text-primary-foreground rounded-md py-3 font-semibold hover:opacity-90 inline-flex items-center justify-center gap-2">
            <Download className="h-4 w-4" /> {t("checkoutDownloadInvoice")}
          </button>
          <Link to="/" className="flex-1 border border-border rounded-md py-3 font-semibold hover:border-primary hover:text-primary inline-flex items-center justify-center gap-2">
            <Home className="h-4 w-4" /> {t("checkoutBackToHome")}
          </Link>
        </div>
      </main>
    </div>
  );
}
