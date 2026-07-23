import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { useState } from "react";
import {
  Check, MessageSquare, Minus, Plus, Ticket, Bike, MapPin, Truck, X,
} from "lucide-react";
import { toast } from "sonner";
import { SiteHeader } from "@/components/SiteHeader";
import { SiteFooter } from "@/components/SiteFooter";
import giftCard from "@/assets/gift-card.jpg";
import { useStore, cart, promo, selectSubtotal, selectDiscount, selectTax, selectDeliveryFee, selectTotal } from "@/lib/store";
import { featured, getProduct } from "@/lib/products";

export const Route = createFileRoute("/customize")({
  component: CustomizePage,
  head: () => ({
    meta: [
      { title: "Customize Your Order — Terrific Bites" },
      { name: "description", content: "Personalize your Terrific Bites order — add a gift card, message and extras before checkout." },
      { property: "og:title", content: "Customize Your Order — Terrific Bites" },
      { property: "og:description", content: "Add a gift card, message and extras to your order." },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary_large_image" },
    ],
  }),
});

function CustomizePage() {
  const navigate = useNavigate();
  const cartItems = useStore((s) => s.cart);
  const currentPromo = useStore((s) => s.promo);
  const subtotal = useStore(selectSubtotal);
  const discount = useStore(selectDiscount);
  const tax = useStore(selectTax);
  const deliveryFee = useStore(selectDeliveryFee);
  const total = useStore(selectTotal);

  const [promoInput, setPromoInput] = useState(currentPromo?.code ?? "");
  const [message, setMessage] = useState("");
  const [showMsg, setShowMsg] = useState(false);
  const [giftCardSelected, setGiftCardSelected] = useState(false);
  const [showExtras, setShowExtras] = useState(false);

  const remainingForFree = Math.max(0, 200 - (subtotal - discount));
  const progress = Math.min(100, ((subtotal - discount) / 200) * 100);

  const applyPromo = () => {
    if (!promoInput.trim()) return;
    if (promo.apply(promoInput)) toast.success("Promo code applied!");
    else toast.error("Invalid promo code");
  };

  const continueToDelivery = () => {
    if (cartItems.length === 0) {
      toast.error("Your cart is empty");
      return;
    }
    navigate({ to: "/delivery" });
  };

  return (
    <div className="min-h-screen bg-background text-foreground flex flex-col">
      <SiteHeader />

      <main className="flex-1 max-w-6xl w-full mx-auto px-6 py-8">
        <div className="bg-white rounded-2xl shadow-sm px-8 py-5 flex items-center gap-4 mb-6">
          <Step n={1} label="Customize" active done />
          <div className="flex-1 h-px bg-border" />
          <Step n={2} label="Delivery Details" />
          <div className="flex-1 h-px bg-border" />
          <Step n={3} label="Payment" />
        </div>

        <div className="grid lg:grid-cols-[1fr_400px] gap-6">
          <div className="space-y-6">
            <section className="bg-white rounded-2xl shadow-sm p-6">
              <div className="flex items-center justify-between mb-6">
                <div className="flex items-center gap-2">
                  <MessageSquare className="h-5 w-5 text-primary" />
                  <h2 className="font-semibold">Gift Card & Message</h2>
                </div>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <button onClick={() => setGiftCardSelected(!giftCardSelected)} className="group">
                  <div className={`aspect-square rounded-lg overflow-hidden border-2 ${giftCardSelected ? "border-primary" : "border-dashed border-border"}`}>
                    <img src={giftCard} alt="Gift card" loading="lazy" className="w-full h-full object-cover" />
                  </div>
                  <p className="text-center text-sm mt-3">{giftCardSelected ? "Gift Card ✓" : "Select Gift Card"}</p>
                </button>
                <button onClick={() => setShowMsg(true)} className="group">
                  <div className="aspect-square rounded-lg border-2 border-dashed border-border flex flex-col items-center justify-center gap-3 text-muted-foreground p-4 text-center">
                    <MessageSquare className="h-6 w-6" />
                    <span className="text-sm">{message ? `"${message.slice(0, 40)}${message.length > 40 ? "…" : ""}"` : "Tap to add message"}</span>
                  </div>
                  <p className="text-center text-sm mt-3">Add Message</p>
                </button>
              </div>
            </section>

            <section className="bg-white rounded-2xl shadow-sm p-6">
              <div className="flex items-center justify-between mb-5">
                <h2 className="font-semibold">Add a Little Extra for a Special Touch!</h2>
                <button onClick={() => setShowExtras(true)} className="text-sm text-primary hover:underline">View All</button>
              </div>
              <div className="grid grid-cols-3 gap-4">
                {featured.extras.slice(0, 3).map((e) => {
                  const inCart = cartItems.some((c) => c.productId === e.id);
                  return (
                    <div key={e.id} className="text-center">
                      <Link to="/product/$id" params={{ id: e.id }} className="block aspect-square rounded-full overflow-hidden bg-secondary">
                        <img src={e.image} alt={e.name} loading="lazy" className="w-full h-full object-cover" />
                      </Link>
                      <p className="mt-3 text-sm font-medium">{e.name}</p>
                      <p className="text-xs text-muted-foreground">${e.price.toFixed(2)}</p>
                      <button
                        onClick={() => {
                          cart.add({ productId: e.id });
                          toast.success(`${e.name} added`);
                        }}
                        className={`mt-3 w-full border rounded-md py-2 text-sm transition ${
                          inCart ? "bg-primary text-primary-foreground border-primary" : "border-border hover:border-primary hover:text-primary"
                        }`}
                      >
                        {inCart ? "Added" : "Add"}
                      </button>
                    </div>
                  );
                })}
              </div>
            </section>
          </div>

          <aside className="space-y-4">
            <div className="bg-white rounded-2xl shadow-sm p-5">
              <div className="flex items-center gap-3">
                <Bike className="h-8 w-8 text-primary shrink-0" />
                <div className="flex-1">
                  <p className="text-sm font-medium">
                    {remainingForFree > 0
                      ? `Only $${remainingForFree.toFixed(2)} to Go for Free Delivery!`
                      : "You've unlocked free delivery! 🎉"}
                  </p>
                </div>
              </div>
              <div className="mt-3 flex items-center gap-3">
                <div className="flex-1 h-1.5 bg-secondary rounded-full overflow-hidden">
                  <div className="h-full bg-primary rounded-full transition-all" style={{ width: `${progress}%` }} />
                </div>
                <span className="text-xs text-muted-foreground">$200</span>
              </div>
            </div>

            {cartItems.length === 0 ? (
              <div className="bg-white rounded-2xl shadow-sm p-8 text-center">
                <p className="text-sm text-muted-foreground">Your cart is empty.</p>
                <Link to="/chocolates" className="mt-3 inline-block text-sm text-primary underline">Browse products</Link>
              </div>
            ) : (
              cartItems.map((it) => {
                const p = getProduct(it.productId);
                return (
                  <div key={it.lineId} className="bg-white rounded-2xl shadow-sm p-5">
                    <div className="flex gap-4">
                      <img src={p?.image} alt={p?.name} className="w-24 h-24 rounded-lg object-cover" />
                      <div className="flex-1 min-w-0">
                        <h3 className="font-display text-primary truncate">{p?.name}</h3>
                        {(it.size || it.flavor) && (
                          <p className="text-xs text-muted-foreground mt-1">{[it.size, it.flavor].filter(Boolean).join(" · ")}</p>
                        )}
                        <div className="flex items-center justify-between mt-3">
                          <div className="flex items-center border border-border rounded-md">
                            <button onClick={() => cart.setQty(it.lineId, it.qty - 1)} className="px-2 py-1"><Minus className="h-3 w-3" /></button>
                            <span className="px-3 text-sm">{it.qty}</span>
                            <button onClick={() => cart.setQty(it.lineId, it.qty + 1)} className="px-2 py-1"><Plus className="h-3 w-3" /></button>
                          </div>
                        </div>
                      </div>
                    </div>
                    <div className="flex items-center justify-between mt-3">
                      <p className="font-semibold">${(it.unitPrice * it.qty).toFixed(2)}</p>
                      <button onClick={() => cart.remove(it.lineId)} className="text-xs text-primary underline">Remove</button>
                    </div>
                  </div>
                );
              })
            )}

            <div className="bg-white rounded-2xl shadow-sm p-3 flex items-center gap-2">
              <div className="flex items-center gap-2 flex-1 px-3">
                <Ticket className="h-4 w-4 text-muted-foreground" />
                <input
                  value={promoInput}
                  onChange={(e) => setPromoInput(e.target.value.toUpperCase())}
                  placeholder="Try WELCOME10 or SWEET15"
                  className="flex-1 text-sm outline-none bg-transparent py-2 placeholder:text-muted-foreground"
                />
              </div>
              <button onClick={applyPromo} className="bg-[oklch(0.72_0.08_160)] text-white rounded-md px-6 py-2 text-sm hover:opacity-90 transition">
                Apply
              </button>
            </div>
            {currentPromo && (
              <p className="text-xs text-primary px-2">Promo {currentPromo.code} — {currentPromo.percent}% off</p>
            )}

            <div className="bg-white rounded-2xl shadow-sm p-5 space-y-4">
              <h3 className="font-semibold">Order Summary</h3>
              <div className="space-y-2 text-sm">
                <Row label="Subtotal" val={`$${subtotal.toFixed(2)}`} />
                {discount > 0 && <Row label={`Discount (${currentPromo?.code})`} val={`-$${discount.toFixed(2)}`} />}
                <Row label="Delivery" val={deliveryFee === 0 ? "Free" : `$${deliveryFee.toFixed(2)}`} />
                <Row label="Tax (5%)" val={`$${tax.toFixed(2)}`} />
                <div className="flex items-center gap-2 text-xs text-foreground/80 pt-2">
                  <Truck className="h-3.5 w-3.5" /> Skinniy Express
                </div>
                <div className="flex items-center gap-2 text-xs text-foreground/80">
                  <MapPin className="h-3.5 w-3.5" /> Delivery details on next step
                </div>
              </div>
              <div className="border-t border-border pt-4 flex items-center justify-between">
                <span className="font-semibold">Order Total</span>
                <span className="font-semibold text-lg">${total.toFixed(2)}</span>
              </div>
            </div>

            <button
              onClick={continueToDelivery}
              disabled={cartItems.length === 0}
              className="w-full bg-primary text-primary-foreground rounded-md py-4 font-semibold hover:opacity-90 transition disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Continue to Delivery
            </button>
          </aside>
        </div>
      </main>

      {showMsg && (
        <div className="fixed inset-0 z-50 bg-black/40 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl shadow-2xl w-full max-w-md p-6 relative">
            <button onClick={() => setShowMsg(false)} className="absolute top-4 right-4"><X className="h-5 w-5" /></button>
            <h3 className="font-semibold mb-3">Add a personal message</h3>
            <textarea
              value={message}
              onChange={(e) => setMessage(e.target.value.slice(0, 200))}
              rows={4}
              placeholder="Happy Birthday!"
              className="w-full border border-border rounded-md p-3 text-sm outline-none focus:border-primary"
            />
            <p className="text-xs text-muted-foreground mt-1">{message.length}/200</p>
            <button onClick={() => setShowMsg(false)} className="mt-4 w-full bg-primary text-primary-foreground rounded-md py-3 text-sm">Save</button>
          </div>
        </div>
      )}

      {showExtras && (
        <div className="fixed inset-0 z-50 bg-black/40 flex items-start justify-center p-4 overflow-y-auto">
          <div className="bg-white rounded-2xl shadow-2xl w-full max-w-5xl mt-16 p-8 relative">
            <button onClick={() => setShowExtras(false)} aria-label="Close" className="absolute top-5 right-5 text-primary hover:opacity-70">
              <X className="h-5 w-5" />
            </button>
            <h3 className="text-lg font-semibold">Add a Little Extra for a Special Touch!</h3>
            <p className="text-sm text-muted-foreground mt-1">Perfect additions to complete your order.</p>
            <div className="mt-6 border-t border-border" />
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-6">
              {featured.extras.map((p) => {
                const inCart = cartItems.some((c) => c.productId === p.id);
                return (
                  <div key={p.id} className={`bg-secondary/40 rounded-xl p-3 ${inCart ? "ring-2 ring-primary" : ""}`}>
                    <div className="aspect-square rounded-lg overflow-hidden bg-white">
                      <img src={p.image} alt={p.name} loading="lazy" className="w-full h-full object-cover" />
                    </div>
                    <p className="text-center text-sm font-medium mt-3">{p.name}</p>
                    <p className="text-center text-sm mt-1">${p.price.toFixed(2)}</p>
                    <button
                      onClick={() => cart.add({ productId: p.id })}
                      className={`mt-3 w-full border rounded-md py-2 text-sm transition ${
                        inCart ? "bg-primary text-primary-foreground border-primary" : "border-primary text-primary hover:bg-primary hover:text-primary-foreground"
                      }`}
                    >
                      {inCart ? "Added" : "Shop now"}
                    </button>
                  </div>
                );
              })}
            </div>
            <div className="mt-8 flex items-center justify-between border-t border-border pt-6">
              <div className="flex items-center gap-3 text-sm">
                <span className="text-muted-foreground">Order Total</span>
                <span className="font-semibold text-base">${total.toFixed(2)}</span>
              </div>
              <button onClick={() => setShowExtras(false)} className="bg-primary text-primary-foreground rounded-md px-8 py-3 text-sm hover:opacity-90">
                Continue
              </button>
            </div>
          </div>
        </div>
      )}

      <SiteFooter />
    </div>
  );
}

function Step({ n, label, active, done }: { n: number; label: string; active?: boolean; done?: boolean }) {
  return (
    <div className="flex items-center gap-3">
      <div className={`h-9 w-9 rounded-full flex items-center justify-center text-sm font-semibold ${
        done ? "bg-[oklch(0.85_0.08_120)] text-primary" : active ? "bg-primary text-primary-foreground" : "bg-secondary text-foreground"
      }`}>
        {done ? <Check className="h-4 w-4" /> : n}
      </div>
      <span className={`text-sm ${active || done ? "font-semibold" : "text-muted-foreground"}`}>{label}</span>
    </div>
  );
}

function Row({ label, val }: { label: string; val: string }) {
  return (
    <div className="flex items-center justify-between">
      <span>{label}</span>
      <span>{val}</span>
    </div>
  );
}
