import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { useState } from "react";
import {
  Check, MessageSquare, Minus, Plus, Ticket, MapPin, Truck, X, Link2, PenLine,
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
import { useT, type TKey } from "@/lib/i18n";

const GIFT_CARDS: { id: string; labelKey: TKey; image: string }[] = [
  { id: "classic", labelKey: "cdGiftCardClassic", image: giftCard },
  { id: "red", labelKey: "cdGiftCardRedRibbon", image: giftCardRed },
  { id: "cream", labelKey: "cdGiftCardCream", image: giftCardCream },
  { id: "brown", labelKey: "cdGiftCardLuxeBrown", image: giftCardBrown },
];

const SUGGESTED_MESSAGE_KEYS: TKey[] = [
  "cdSuggestedMsg1",
  "cdSuggestedMsg2",
  "cdSuggestedMsg3",
  "cdSuggestedMsg4",
  "cdSuggestedMsg5",
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
  const t = useT();
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

  const applyPromo = () => {
    if (!promoInput.trim()) return;
    if (promo.apply(promoInput)) toast.success(t("cdPromoApplied"));
    else toast.error(t("cdInvalidPromoCode"));
  };

  const continueToDelivery = () => {
    if (cartItems.length === 0) {
      toast.error(t("cdCartEmptyToast"));
      return;
    }
    navigate({ to: "/delivery" });
  };

  return (
    <div className="min-h-screen bg-background text-foreground flex flex-col">
      <SiteHeader />

      <main className="flex-1 max-w-6xl w-full mx-auto px-4 sm:px-6 py-6 sm:py-8">
        <div className="bg-white rounded-2xl shadow-sm px-3 sm:px-8 py-4 sm:py-5 flex items-center gap-2 sm:gap-4 mb-6">
          <Step n={1} label={t("cdStepCustomize")} active done />
          <div className="flex-1 h-px bg-border" />
          <Step n={2} label={t("cdStepDelivery")} />
          <div className="flex-1 h-px bg-border" />
          <Step n={3} label={t("cdStepPayment")} />
        </div>

        <div className="grid lg:grid-cols-[1fr_400px] gap-6">
          <div className="space-y-6">
            <section className="bg-white rounded-2xl shadow-sm p-6">
              <div className="flex items-center justify-between mb-6">
                <div className="flex items-center gap-2">
                  <MessageSquare className="h-5 w-5 text-primary" />
                  <h2 className="font-semibold">{t("cdGiftCardMessage")}</h2>
                </div>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <button onClick={() => { setGiftTab("card"); setGiftModalOpen(true); }} className="group">
                  <div className={`aspect-square rounded-lg overflow-hidden border-2 ${giftCardSelected ? "border-primary" : "border-dashed border-border"}`}>
                    <img src={activeCard.image} alt={t("cdGiftCardAlt")} loading="lazy" className="w-full h-full object-cover" />
                  </div>
                  <p className="text-center text-sm mt-3">{giftCardSelected ? `${t(activeCard.labelKey)} ✓` : t("cdSelectGiftCard")}</p>
                </button>
                <button onClick={() => { setGiftTab("message"); setGiftModalOpen(true); }} className="group">
                  <div className="aspect-square rounded-lg border-2 border-dashed border-border flex flex-col items-center justify-center gap-3 text-muted-foreground p-4 text-center">
                    <MessageSquare className="h-6 w-6" />
                    <span className="text-sm">{message ? `"${message.slice(0, 40)}${message.length > 40 ? "…" : ""}"` : t("cdTapToAddMessage")}</span>
                  </div>
                  <p className="text-center text-sm mt-3">{t("cdAddMessage")}</p>
                </button>
              </div>
            </section>

            <section className="bg-white rounded-2xl shadow-sm p-6">
              <div className="flex items-center justify-between mb-5">
                <h2 className="font-semibold">{t("cdAddExtraTouch")}</h2>
                <button onClick={() => setShowExtras(true)} className="text-sm text-primary hover:underline">{t("cdViewAll")}</button>
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
                      <p className="text-xs text-muted-foreground">SAR {e.price.toFixed(2)}</p>
                      <button
                        onClick={() => {
                          cart.add({ productId: e.id });
                          toast.success(`${e.name} ${t("cdAddedToastSuffix")}`);
                        }}
                        className={`mt-3 w-full border rounded-md py-2 text-sm transition ${
                          inCart ? "bg-primary text-primary-foreground border-primary" : "border-border hover:border-primary hover:text-primary"
                        }`}
                      >
                        {inCart ? t("cdAdded") : t("cdAdd")}
                      </button>
                    </div>
                  );
                })}
              </div>
            </section>
          </div>

          <aside className="space-y-4">
            {cartItems.length === 0 ? (
              <div className="bg-white rounded-2xl shadow-sm p-8 text-center">
                <p className="text-sm text-muted-foreground">{t("cdCartEmpty")}</p>
                <Link to="/chocolates" className="mt-3 inline-block text-sm text-primary underline">{t("cdBrowseProducts")}</Link>
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
                      <p className="font-semibold">SAR {(it.unitPrice * it.qty).toFixed(2)}</p>
                      <button onClick={() => cart.remove(it.lineId)} className="text-xs text-primary underline">{t("cdRemove")}</button>
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
                  placeholder={t("cdPromoPlaceholder")}
                  className="flex-1 text-sm outline-none bg-transparent py-2 placeholder:text-muted-foreground"
                />
              </div>
              <button onClick={applyPromo} className="bg-[oklch(0.72_0.08_160)] text-white rounded-md px-6 py-2 text-sm hover:opacity-90 transition">
                {t("cdApply")}
              </button>
            </div>
            {currentPromo && (
              <p className="text-xs text-primary px-2">{t("cdPromoLabelPrefix")} {currentPromo.code} — {currentPromo.percent}{t("cdPercentOff")}</p>
            )}

            <div className="bg-white rounded-2xl shadow-sm p-5 space-y-4">
              <h3 className="font-semibold">{t("cdOrderSummary")}</h3>
              <div className="space-y-2 text-sm">
                <Row label={t("cdSubtotal")} val={`SAR ${subtotal.toFixed(2)}`} />
                {discount > 0 && <Row label={`${t("cdDiscount")} (${currentPromo?.code})`} val={`-SAR ${discount.toFixed(2)}`} />}
                <Row label={t("cdDelivery")} val={deliveryFee === 0 ? t("cdFree") : `SAR ${deliveryFee.toFixed(2)}`} />
                <Row label={t("cdTaxWithPercent")} val={`SAR ${tax.toFixed(2)}`} />
                <div className="flex items-center gap-2 text-xs text-foreground/80 pt-2">
                  <Truck className="h-3.5 w-3.5" /> {t("cdSkinniyExpress")}
                </div>
                <div className="flex items-center gap-2 text-xs text-foreground/80">
                  <MapPin className="h-3.5 w-3.5" /> {t("cdDeliveryDetailsNextStep")}
                </div>
              </div>
              <div className="border-t border-border pt-4 flex items-center justify-between">
                <span className="font-semibold">{t("cdOrderTotal")}</span>
                <span className="font-semibold text-lg">SAR {total.toFixed(2)}</span>
              </div>
            </div>

            <button
              onClick={continueToDelivery}
              disabled={cartItems.length === 0}
              className="w-full bg-primary text-primary-foreground rounded-md py-4 font-semibold hover:opacity-90 transition disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {t("cdContinueToDelivery")}
            </button>
          </aside>
        </div>
      </main>

      {giftModalOpen && (
        <div className="fixed inset-0 z-50 bg-black/40 flex items-start sm:items-center justify-center p-4 overflow-y-auto">
          <div className="bg-white rounded-2xl shadow-2xl w-full max-w-xl my-8 p-6 sm:p-8 relative">
            <button onClick={() => setGiftModalOpen(false)} aria-label={t("cdClose")} className="absolute top-4 right-4 text-muted-foreground hover:text-foreground">
              <X className="h-5 w-5" />
            </button>
            <h3 className="font-semibold text-lg">{t("cdCustomizeGiftCard")}</h3>
            <p className="text-sm text-muted-foreground mt-1">{t("cdChooseCardDesign")}</p>
            <div className="border-t border-border my-5" />

            <div className="grid grid-cols-2 rounded-lg overflow-hidden border border-border mb-6">
              <button
                onClick={() => setGiftTab("card")}
                className={`py-3 text-sm font-medium transition ${giftTab === "card" ? "bg-primary text-primary-foreground" : "bg-secondary/40 text-foreground"}`}
              >
                {t("cdSelectCard")}
              </button>
              <button
                onClick={() => setGiftTab("message")}
                className={`py-3 text-sm font-medium transition ${giftTab === "message" ? "bg-primary text-primary-foreground" : "bg-secondary/40 text-foreground"}`}
              >
                {t("cdAddAMessageTab")}
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
                        <img src={c.image} alt={t(c.labelKey)} loading="lazy" className="w-full h-full object-cover" />
                      </div>
                      <p className="text-xs py-2 text-center">{t(c.labelKey)}{active ? " ✓" : ""}</p>
                    </button>
                  );
                })}
              </div>
            ) : (
              <div className="space-y-4">
                <input
                  value={msgTo}
                  onChange={(e) => setMsgTo(e.target.value)}
                  placeholder={t("cdToOptional")}
                  className="w-full border border-border rounded-md px-4 py-3 text-sm outline-none focus:border-primary"
                />
                <textarea
                  value={message}
                  onChange={(e) => setMessage(e.target.value.slice(0, 200))}
                  rows={4}
                  placeholder={t("cdMessagePlaceholder")}
                  className="w-full border border-border rounded-md p-3 text-sm outline-none focus:border-primary resize-none"
                />
                <div className="flex items-center justify-between text-sm">
                  <span className="text-muted-foreground">{t("cdNotSureWhatToSay")}</span>
                  <button onClick={() => setShowSuggested((v) => !v)} className="text-[oklch(0.55_0.13_160)] font-medium hover:underline">
                    {t("cdTrySuggestedMessages")}
                  </button>
                </div>
                {showSuggested && (
                  <div className="space-y-2 bg-secondary/30 rounded-md p-3">
                    {SUGGESTED_MESSAGE_KEYS.map((k) => (
                      <button
                        key={k}
                        onClick={() => { setMessage(t(k)); setShowSuggested(false); }}
                        className="block w-full text-left text-xs text-foreground hover:text-primary py-1"
                      >
                        “{t(k)}”
                      </button>
                    ))}
                  </div>
                )}
                <div className="relative">
                  <input
                    value={msgFrom}
                    onChange={(e) => setMsgFrom(e.target.value)}
                    placeholder={t("cdFromOptional")}
                    className="w-full border border-border rounded-md px-4 py-3 pr-28 text-sm outline-none focus:border-primary"
                  />
                  <span className="absolute right-3 top-1/2 -translate-y-1/2 flex items-center gap-1 text-[oklch(0.55_0.13_160)] text-xs">
                    <PenLine className="h-3.5 w-3.5" /> {t("cdSignature")}
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
                    <Link2 className="h-4 w-4" /> {t("cdPasteLink")}
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
                {t("cdPreview")}
              </button>
              <button
                onClick={() => {
                  if (giftTab === "card" && !selectedCard) setSelectedCard(GIFT_CARDS[0].id);
                  setGiftModalOpen(false);
                  toast.success(t("cdGiftCardSaved"));
                }}
                className="bg-primary text-primary-foreground rounded-md px-6 py-2.5 text-sm hover:opacity-90 transition"
              >
                {t("cdSaveAndContinue")}
              </button>
            </div>
          </div>
        </div>
      )}

      {showPreview && (
        <div className="fixed inset-0 z-[60] bg-black/60 flex items-center justify-center p-4" onClick={() => setShowPreview(false)}>
          <div onClick={(e) => e.stopPropagation()} className="bg-white rounded-2xl shadow-2xl w-full max-w-sm p-6 relative">
            <button onClick={() => setShowPreview(false)} aria-label={t("cdClose")} className="absolute top-4 right-4 text-muted-foreground hover:text-foreground">
              <X className="h-5 w-5" />
            </button>
            <div className="aspect-[4/3] rounded-lg overflow-hidden mb-4">
              <img src={activeCard.image} alt={t(activeCard.labelKey)} className="w-full h-full object-cover" />
            </div>
            {msgTo && <p className="text-sm font-medium">{t("cdToLabel")} {msgTo}</p>}
            <p className="mt-2 text-sm whitespace-pre-wrap min-h-[3rem]">{message || t("cdMessagePreviewPlaceholder")}</p>
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
            <button onClick={() => setShowExtras(false)} aria-label={t("cdClose")} className="absolute top-5 right-5 text-primary hover:opacity-70">
              <X className="h-5 w-5" />
            </button>
            <h3 className="text-lg font-semibold">{t("cdAddExtraTouch")}</h3>
            <p className="text-sm text-muted-foreground mt-1">{t("cdPerfectAdditions")}</p>
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
                    <p className="text-center text-sm mt-1">SAR {p.price.toFixed(2)}</p>
                    <button
                      onClick={() => cart.add({ productId: p.id })}
                      className={`mt-3 w-full border rounded-md py-2 text-sm transition ${
                        inCart ? "bg-primary text-primary-foreground border-primary" : "border-primary text-primary hover:bg-primary hover:text-primary-foreground"
                      }`}
                    >
                      {inCart ? t("cdAdded") : t("cdShopNow")}
                    </button>
                  </div>
                );
              })}
            </div>
            <div className="mt-8 flex items-center justify-between border-t border-border pt-6">
              <div className="flex items-center gap-3 text-sm">
                <span className="text-muted-foreground">{t("cdOrderTotal")}</span>
                <span className="font-semibold text-base">SAR {total.toFixed(2)}</span>
              </div>
              <button onClick={() => setShowExtras(false)} className="bg-primary text-primary-foreground rounded-md px-8 py-3 text-sm hover:opacity-90">
                {t("cdContinue")}
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
