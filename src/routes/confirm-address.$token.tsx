import { createFileRoute, Link } from "@tanstack/react-router";
import { useState } from "react";
import { Gift, PartyPopper, MessageSquare } from "lucide-react";
import { toast } from "sonner";
import { SiteHeader } from "@/components/SiteHeader";
import { SiteFooter } from "@/components/SiteFooter";
import { useStore, recipientConfirm } from "@/lib/store";
import { useT } from "@/lib/i18n";

export const Route = createFileRoute("/confirm-address/$token")({
  component: ConfirmPage,
  head: () => ({
    meta: [
      { title: "You have a gift — Terrific Bites" },
      { name: "description", content: "A sweet surprise is on its way. Confirm your delivery details." },
      { property: "og:title", content: "You have a gift 🎁" },
      { property: "og:description", content: "Someone sent you a Terrific Bites treat. Confirm delivery." },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary_large_image" },
      { name: "robots", content: "noindex" },
    ],
  }),
});

function ConfirmPage() {
  const t = useT();
  const { token } = Route.useParams();
  const record = useStore((s) => s.recipientConfirmations.find((r) => r.token === token) ?? null);
  const order = useStore((s) => (record ? s.orders.find((o) => o.id === record.orderId) : null));
  const [address, setAddress] = useState("");
  const [phone, setPhone] = useState("");
  const [slot, setSlot] = useState("10:00 AM – 2:00 PM");
  const [done, setDone] = useState(false);

  if (!record) {
    return (
      <div className="min-h-screen bg-background text-foreground flex flex-col">
        <SiteHeader />
        <main className="flex-1 max-w-lg w-full mx-auto px-6 py-16 text-center">
          <h1 className="font-display text-2xl text-primary">{t("checkoutLinkExpired")}</h1>
          <p className="mt-2 text-sm text-muted-foreground">{t("checkoutLinkExpiredCopy")}</p>
          <Link to="/" className="mt-6 inline-block text-primary underline text-sm">{t("checkoutBackHome")}</Link>
        </main>
        <SiteFooter />
      </div>
    );
  }

  const senderName = order?.address?.identitySecret ? t("checkoutSenderSomeoneSpecial") : order?.address?.name ?? t("checkoutSenderAFriend");
  const items = order?.items ?? [];

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!address.trim() || !phone.trim()) { toast.error(t("checkoutToastFillAddressPhone")); return; }
    recipientConfirm.confirm(token, { address: address.trim(), phone: phone.trim(), timeSlot: slot });
    setDone(true);
    toast.success(t("checkoutToastDeliveryConfirmed"));
  };

  if (done || record.confirmed) {
    return (
      <div className="min-h-screen bg-background text-foreground flex flex-col">
        <SiteHeader />
        <main className="flex-1 max-w-lg w-full mx-auto px-6 py-16 text-center">
          <div className="h-16 w-16 rounded-full bg-green-100 flex items-center justify-center mx-auto">
            <PartyPopper className="h-8 w-8 text-green-700" />
          </div>
          <h1 className="font-display text-2xl text-primary mt-4">{t("checkoutAllSet")}</h1>
          <p className="mt-2 text-sm text-muted-foreground">
            {t("checkoutGiftArrivalCopy")}
          </p>
          {order?.trackingToken && (
            <Link to="/track/$id" params={{ id: order.trackingToken }} className="mt-6 inline-block text-primary underline text-sm">
              {t("checkoutTrackThisDelivery")}
            </Link>
          )}
        </main>
        <SiteFooter />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background text-foreground flex flex-col">
      <SiteHeader />
      <main className="flex-1 max-w-2xl w-full mx-auto px-4 sm:px-6 py-8">
        <div className="bg-white rounded-2xl border border-border p-6 sm:p-8">
          <div className="text-center">
            <div className="h-16 w-16 rounded-full bg-primary/10 flex items-center justify-center mx-auto">
              <Gift className="h-8 w-8 text-primary" />
            </div>
            <h1 className="font-display text-2xl sm:text-3xl text-primary mt-4">{t("checkoutYouHaveGift")}</h1>
            <p className="mt-2 text-sm text-muted-foreground">
              <span className="font-semibold text-foreground">{senderName}</span> {t("checkoutGiftSentSuffix")}
            </p>
          </div>

          {items.length > 0 && (
            <div className="mt-6 bg-muted/40 rounded-lg p-4 text-sm">
              <p className="text-xs uppercase tracking-wider text-muted-foreground mb-2">{t("checkoutWhatsInside")}</p>
              <ul className="space-y-1">
                {items.map((it, i) => (
                  <li key={i} className="text-foreground">🍰 {it.qty} × {it.name}</li>
                ))}
              </ul>
            </div>
          )}

          <form onSubmit={submit} className="mt-6 space-y-4">
            <p className="text-sm font-semibold text-primary">{t("checkoutWhereDeliver")}</p>
            <div>
              <label className="text-xs text-muted-foreground">{t("checkoutYourFullAddress")}</label>
              <textarea
                value={address}
                onChange={(e) => setAddress(e.target.value)}
                rows={3}
                placeholder={t("checkoutAddressPlaceholder")}
                className="mt-1 w-full border border-border rounded-md px-3 py-2 text-sm"
                required
              />
            </div>
            <div>
              <label className="text-xs text-muted-foreground">{t("checkoutYourPhone")}</label>
              <input
                type="tel"
                value={phone}
                onChange={(e) => setPhone(e.target.value)}
                placeholder="+966 5X XXX XXXX"
                className="mt-1 w-full border border-border rounded-md px-3 py-2 text-sm"
                required
              />
            </div>
            <div>
              <label className="text-xs text-muted-foreground">{t("checkoutPreferredWindow")}</label>
              <select value={slot} onChange={(e) => setSlot(e.target.value)} className="mt-1 w-full border border-border rounded-md px-3 py-2 text-sm bg-white">
                <option value="10:00 AM – 2:00 PM">{t("checkoutSlotMorning")}</option>
                <option value="2:00 PM – 6:00 PM">{t("checkoutSlotAfternoon")}</option>
                <option value="6:00 PM – 10:00 PM">{t("checkoutSlotEvening")}</option>
              </select>
            </div>
            <button type="submit" className="w-full bg-primary text-primary-foreground rounded-md py-3 text-sm font-semibold hover:bg-primary/90">
              {t("checkoutConfirmDelivery")}
            </button>
            <p className="text-[11px] text-muted-foreground text-center flex items-center justify-center gap-1">
              <MessageSquare className="h-3 w-3" /> {t("checkoutDetailsPrivacy")}
            </p>
          </form>
        </div>
      </main>
      <SiteFooter />
    </div>
  );
}
