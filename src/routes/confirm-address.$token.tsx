import { createFileRoute, Link } from "@tanstack/react-router";
import { useState } from "react";
import { Gift, PartyPopper, MessageSquare } from "lucide-react";
import { toast } from "sonner";
import { SiteHeader } from "@/components/SiteHeader";
import { SiteFooter } from "@/components/SiteFooter";
import { useStore, recipientConfirm } from "@/lib/store";

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
          <h1 className="font-display text-2xl text-primary">Link expired</h1>
          <p className="mt-2 text-sm text-muted-foreground">This gift confirmation link isn't valid on this device.</p>
          <Link to="/" className="mt-6 inline-block text-primary underline text-sm">Back home</Link>
        </main>
        <SiteFooter />
      </div>
    );
  }

  const senderName = order?.address?.identitySecret ? "Someone special" : order?.address?.name ?? "A friend";
  const items = order?.items ?? [];

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!address.trim() || !phone.trim()) { toast.error("Please fill address and phone"); return; }
    recipientConfirm.confirm(token, { address: address.trim(), phone: phone.trim(), timeSlot: slot });
    setDone(true);
    toast.success("Delivery details confirmed!");
  };

  if (done || record.confirmed) {
    return (
      <div className="min-h-screen bg-background text-foreground flex flex-col">
        <SiteHeader />
        <main className="flex-1 max-w-lg w-full mx-auto px-6 py-16 text-center">
          <div className="h-16 w-16 rounded-full bg-green-100 flex items-center justify-center mx-auto">
            <PartyPopper className="h-8 w-8 text-green-700" />
          </div>
          <h1 className="font-display text-2xl text-primary mt-4">You're all set!</h1>
          <p className="mt-2 text-sm text-muted-foreground">
            Your gift will arrive at the address you shared. We'll text you when the courier's on the way.
          </p>
          {order?.trackingToken && (
            <Link to="/track/$id" params={{ id: order.trackingToken }} className="mt-6 inline-block text-primary underline text-sm">
              Track this delivery
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
            <h1 className="font-display text-2xl sm:text-3xl text-primary mt-4">You have a gift!</h1>
            <p className="mt-2 text-sm text-muted-foreground">
              <span className="font-semibold text-foreground">{senderName}</span> sent you a Terrific Bites surprise 🎁
            </p>
          </div>

          {items.length > 0 && (
            <div className="mt-6 bg-muted/40 rounded-lg p-4 text-sm">
              <p className="text-xs uppercase tracking-wider text-muted-foreground mb-2">What's inside</p>
              <ul className="space-y-1">
                {items.map((it, i) => (
                  <li key={i} className="text-foreground">🍰 {it.qty} × {it.name}</li>
                ))}
              </ul>
            </div>
          )}

          <form onSubmit={submit} className="mt-6 space-y-4">
            <p className="text-sm font-semibold text-primary">Where should we deliver it?</p>
            <div>
              <label className="text-xs text-muted-foreground">Your full address</label>
              <textarea
                value={address}
                onChange={(e) => setAddress(e.target.value)}
                rows={3}
                placeholder="Building, street, area, city"
                className="mt-1 w-full border border-border rounded-md px-3 py-2 text-sm"
                required
              />
            </div>
            <div>
              <label className="text-xs text-muted-foreground">Your phone (for courier)</label>
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
              <label className="text-xs text-muted-foreground">Preferred delivery window</label>
              <select value={slot} onChange={(e) => setSlot(e.target.value)} className="mt-1 w-full border border-border rounded-md px-3 py-2 text-sm bg-white">
                <option>10:00 AM – 2:00 PM</option>
                <option>2:00 PM – 6:00 PM</option>
                <option>6:00 PM – 10:00 PM</option>
              </select>
            </div>
            <button type="submit" className="w-full bg-primary text-primary-foreground rounded-md py-3 text-sm font-semibold hover:bg-primary/90">
              Confirm delivery
            </button>
            <p className="text-[11px] text-muted-foreground text-center flex items-center justify-center gap-1">
              <MessageSquare className="h-3 w-3" /> Your details won't be shared back with the sender.
            </p>
          </form>
        </div>
      </main>
      <SiteFooter />
    </div>
  );
}
