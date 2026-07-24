import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { useState } from "react";
import {
  Check, MessageSquare, Minus, Plus, Ticket, Bike, MapPin, Truck, X, Link2, PenLine,
} from "lucide-react";
import { toast } from "sonner";
import { SiteHeader } from "@/components/SiteHeader";
import { SiteFooter } from "@/components/SiteFooter";
import giftCard from "@/assets/gift-card.jpg";
import giftCardRed from "@/assets/gift-card-red.jpg";
import giftCardCream from "@/assets/gift-card-cream.jpg";
import giftCardBrown from "@/assets/gift-card-brown.jpg";
import { useStore, cart, promo, selectSubtotal, selectDiscount, selectTax, selectDeliveryFee, selectTotal } from "@/lib/store";
import { featured, getProduct } from "@/lib/products";

const GIFT_CARDS = [
  { id: "classic", label: "Classic", image: giftCard },
  { id: "red", label: "Red Ribbon", image: giftCardRed },
  { id: "cream", label: "Cream", image: giftCardCream },
  { id: "brown", label: "Luxe Brown", image: giftCardBrown },
];

const SUGGESTED_MESSAGES = [
  "Wishing you a day as sweet as you are. Happy Birthday!",
  "Thank you for everything you do — you deserve all the treats.",
  "Just a little something to brighten your day.",
  "Congratulations! Celebrate with something delicious.",
  "Sending sweet hugs and love your way.",
];

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
  const [msgTo, setMsgTo] = useState("");
  const [msgFrom, setMsgFrom] = useState("");
  const [msgLink, setMsgLink] = useState("");
  const [showLinkField, setShowLinkField] = useState(false);
  const [showSuggested, setShowSuggested] = useState(false);
  const [showPreview, setShowPreview] = useState(false);
  const [giftModalOpen, setGiftModalOpen] = useState(false);
  const [giftTab, setGiftTab] = useState<"card" | "message">("card");
  const [selectedCard, setSelectedCard] = useState<string | null>(null);
  const [showExtras, setShowExtras] = useState(false);

  const giftCardSelected = selectedCard !== null;
  const activeCard = GIFT_CARDS.find((c) => c.id === selectedCard) ?? GIFT_CARDS[0];

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

      <main className="flex-1 max-w-6xl w-full mx-auto px-4 sm:px-6 py-6 sm:py-8">
        <div className="bg-white rounded-2xl shadow-sm px-3 sm:px-8 py-4 sm:py-5 flex items-center gap-2 sm:gap-4 mb-6">
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
                <button onClick={() => { setGiftTab("card"); setGiftModalOpen(true); }} className="group">
                  <div className={`aspect-square rounded-lg overflow-hidden border-2 ${giftCardSelected ? "border-primary" : "border-dashed border-border"}`}>
                    <img src={activeCard.image} alt="Gift card" loading="lazy" className="w-full h-full object-cover" />
                  </div>
                  <p className="text-center text-sm mt-3">{giftCardSelected ? `${activeCard.label} ✓` : "Select Gift Card"}</p>
                </button>
                <button onClick={() => { setGiftTab("message"); setGiftModalOpen(true); }} className="group">
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

      {giftModalOpen && (
        <div className="fixed inset-0 z-50 bg-black/40 flex items-start sm:items-center justify-center p-4 overflow-y-auto">
          <div className="bg-white rounded-2xl shadow-2xl w-full max-w-xl my-8 p-6 sm:p-8 relative">
            <button onClick={() => setGiftModalOpen(false)} aria-label="Close" className="absolute top-4 right-4 text-muted-foreground hover:text-foreground">
              <X className="h-5 w-5" />
            </button>
            <h3 className="font-semibold text-lg">Customize Gift Card</h3>
            <p className="text-sm text-muted-foreground mt-1">Choose a card design and add a personal message to make it extra special.</p>
            <div className="border-t border-border my-5" />

            <div className="grid grid-cols-2 rounded-lg overflow-hidden border border-border mb-6">
              <button
                onClick={() => setGiftTab("card")}
                className={`py-3 text-sm font-medium transition ${giftTab === "card" ? "bg-primary text-primary-foreground" : "bg-secondary/40 text-foreground"}`}
              >
                Select Card
              </button>
              <button
                onClick={() => setGiftTab("message")}
                className={`py-3 text-sm font-medium transition ${giftTab === "message" ? "bg-primary text-primary-foreground" : "bg-secondary/40 text-foreground"}`}
              >
                Add a Message
              </button>
            </div>

            {giftTab === "card" ? (
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                {GIFT_CARDS.map((c) => {
                  const active = selectedCard === c.id;
                  return (
                    <button
                      key={c.id}
                      onClick={() => setSelectedCard(c.id)}
                      className={`rounded-lg overflow-hidden border-2 transition ${active ? "border-primary" : "border-transparent hover:border-border"}`}
                    >
                      <div className="aspect-square bg-secondary/40">
                        <img src={c.image} alt={c.label} loading="lazy" className="w-full h-full object-cover" />
                      </div>
                      <p className="text-xs py-2 text-center">{c.label}{active ? " ✓" : ""}</p>
                    </button>
                  );
                })}
              </div>
            ) : (
              <div className="space-y-4">
                <input
                  value={msgTo}
                  onChange={(e) => setMsgTo(e.target.value)}
                  placeholder="To: (Optional)"
                  className="w-full border border-border rounded-md px-4 py-3 text-sm outline-none focus:border-primary"
                />
                <textarea
                  value={message}
                  onChange={(e) => setMessage(e.target.value.slice(0, 200))}
                  rows={4}
                  placeholder="Type your message and express your feelings"
                  className="w-full border border-border rounded-md p-3 text-sm outline-none focus:border-primary resize-none"
                />
                <div className="flex items-center justify-between text-sm">
                  <span className="text-muted-foreground">Not sure what to say?</span>
                  <button onClick={() => setShowSuggested((v) => !v)} className="text-[oklch(0.55_0.13_160)] font-medium hover:underline">
                    Try Suggested Messages
                  </button>
                </div>
                {showSuggested && (
                  <div className="space-y-2 bg-secondary/30 rounded-md p-3">
                    {SUGGESTED_MESSAGES.map((s) => (
                      <button
                        key={s}
                        onClick={() => { setMessage(s); setShowSuggested(false); }}
                        className="block w-full text-left text-xs text-foreground hover:text-primary py-1"
                      >
                        “{s}”
                      </button>
                    ))}
                  </div>
                )}
                <div className="relative">
                  <input
                    value={msgFrom}
                    onChange={(e) => setMsgFrom(e.target.value)}
                    placeholder="From: (Optional)"
                    className="w-full border border-border rounded-md px-4 py-3 pr-28 text-sm outline-none focus:border-primary"
                  />
                  <span className="absolute right-3 top-1/2 -translate-y-1/2 flex items-center gap-1 text-[oklch(0.55_0.13_160)] text-xs">
                    <PenLine className="h-3.5 w-3.5" /> Signature
                  </span>
                </div>
                {showLinkField ? (
                  <input
                    autoFocus
                    value={msgLink}
                    onChange={(e) => setMsgLink(e.target.value)}
                    placeholder="https://open.spotify.com/…"
                    className="w-full border border-border rounded-md px-4 py-3 text-sm outline-none focus:border-primary"
                  />
                ) : (
                  <button
                    onClick={() => setShowLinkField(true)}
                    className="w-full flex items-center justify-center gap-2 text-[oklch(0.55_0.13_160)] text-sm py-2 hover:underline"
                  >
                    <Link2 className="h-4 w-4" /> Paste a Link to a Song or Video
                  </button>
                )}
                <p className="text-xs text-muted-foreground text-right">{message.length}/200</p>
              </div>
            )}

            <div className="flex items-center justify-center gap-3 mt-6">
              <button
                onClick={() => setShowPreview(true)}
                className="border border-border rounded-md px-6 py-2.5 text-sm hover:bg-secondary/50 transition"
              >
                Preview
              </button>
              <button
                onClick={() => {
                  if (giftTab === "card" && !selectedCard) setSelectedCard(GIFT_CARDS[0].id);
                  setGiftModalOpen(false);
                  toast.success("Gift card saved");
                }}
                className="bg-primary text-primary-foreground rounded-md px-6 py-2.5 text-sm hover:opacity-90 transition"
              >
                Save & Continue
              </button>
            </div>
          </div>
        </div>
      )}

      {showPreview && (
        <div className="fixed inset-0 z-[60] bg-black/60 flex items-center justify-center p-4" onClick={() => setShowPreview(false)}>
          <div onClick={(e) => e.stopPropagation()} className="bg-white rounded-2xl shadow-2xl w-full max-w-sm p-6 relative">
            <button onClick={() => setShowPreview(false)} aria-label="Close" className="absolute top-4 right-4 text-muted-foreground hover:text-foreground">
              <X className="h-5 w-5" />
            </button>
            <div className="aspect-[4/3] rounded-lg overflow-hidden mb-4">
              <img src={activeCard.image} alt={activeCard.label} className="w-full h-full object-cover" />
            </div>
            {msgTo && <p className="text-sm font-medium">To: {msgTo}</p>}
            <p className="mt-2 text-sm whitespace-pre-wrap min-h-[3rem]">{message || "Your message preview will appear here."}</p>
            {msgFrom && <p className="mt-3 text-sm font-medium text-right">— {msgFrom}</p>}
            {msgLink && (
              <a href={msgLink} target="_blank" rel="noreferrer" className="mt-3 flex items-center gap-1 text-xs text-[oklch(0.55_0.13_160)] hover:underline">
                <Link2 className="h-3 w-3" /> {msgLink}
              </a>
            )}
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
    <div className="flex items-center gap-2 sm:gap-3 min-w-0">
      <div className={`h-8 w-8 sm:h-9 sm:w-9 shrink-0 rounded-full flex items-center justify-center text-sm font-semibold ${
        done ? "bg-[oklch(0.85_0.08_120)] text-primary" : active ? "bg-primary text-primary-foreground" : "bg-secondary text-foreground"
      }`}>
        {done ? <Check className="h-4 w-4" /> : n}
      </div>
      <span className={`hidden sm:inline text-sm truncate ${active || done ? "font-semibold" : "text-muted-foreground"}`}>{label}</span>
      {active && <span className="sm:hidden text-xs font-semibold truncate">{label}</span>}
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
