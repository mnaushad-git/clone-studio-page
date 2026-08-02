import { Link } from "@tanstack/react-router";
import { useState } from "react";
import { X, Minus, Plus, ShoppingCart, MapPin, Truck, Tag, Wallet } from "lucide-react";
import {
  useStore,
  cart,
  promo,
  loyalty,
  selectSubtotal,
  selectDiscount,
  selectPointsDiscount,
  selectTax,
  selectTotal,
  selectDeliveryFee,
  selectCartCount,
  selectMinOrder,
} from "@/lib/store";
import { useAdmin } from "@/lib/admin-store";
import { getProduct, products } from "@/lib/products";
import { formatAttributes } from "@/lib/format-variant-attributes";
import { useT } from "@/lib/i18n";

export function CartDrawer({ open, onClose }: { open: boolean; onClose: () => void }) {
  const t = useT();
  const items = useStore((s) => s.cart);
  const subtotal = useStore(selectSubtotal);
  const discountRaw = useStore(selectDiscount);
  const taxRaw = useStore(selectTax);
  const totalRaw = useStore(selectTotal);
  const deliveryRaw = useStore(selectDeliveryFee);
  const count = useStore(selectCartCount);
  const activePromo = useStore((s) => s.promo);
  const points = useStore((s) => s.loyaltyPoints);
  const redeemed = useStore((s) => s.redeemedPoints);
  const pointsDiscRaw = useStore(selectPointsDiscount);
  const user = useStore((s) => s.user);
  const isAuthed = !!user;
  const settings = useAdmin((s) => s.settings);
  const loyaltyCfg = useAdmin((s) => s.loyalty);
  const taxRate = (settings.taxRate ?? 5) / 100;
  const minOrder = selectMinOrder();
  const belowMin = minOrder > 0 && subtotal < minOrder;
  const [code, setCode] = useState("");
  const [ptsInput, setPtsInput] = useState("");
  const [err, setErr] = useState<string | null>(null);

  // Guests: hide delivery, promo, and points from the cart summary. Tax still uses the
  // VAT-inclusive formula (D08/D21) — prices already include VAT, so a guest total must
  // equal subtotal, never subtotal + tax (that would double-count VAT already in the price).
  const discount = isAuthed ? discountRaw : 0;
  const tax = isAuthed ? taxRaw : +((subtotal * taxRate) / (1 + taxRate)).toFixed(2);
  const delivery = isAuthed ? deliveryRaw : 0;
  const pointsDisc = isAuthed ? pointsDiscRaw : 0;
  const total = isAuthed ? totalRaw : subtotal;

  if (!open) return null;

  function applyPromo() {
    setErr(null);
    if (!code.trim()) return;
    const ok = promo.apply(code);
    if (!ok) setErr(t("cartInvalidPromoCode"));
    else setCode("");
  }

  // Recommendations: products not currently in cart
  const inCartIds = new Set(items.map((i) => i.productId));
  const recs = products.filter((p) => !inCartIds.has(p.id)).slice(0, 6);

  return (
    <div className="fixed inset-0 z-50 flex justify-end">
      <button
        aria-label={t("cartCloseCartAria")}
        onClick={onClose}
        className="flex-1 bg-black/40"
      />

      {/* Recommendations rail */}
      <aside className="hidden md:flex w-72 bg-[#f7e6e6] h-full flex-col shadow-2xl">
        <div className="px-5 py-5 border-b border-black/5">
          <h3 className="font-display text-lg text-primary leading-tight">
            {t("cartCompleteYourOrderLine1")}
            <br />
            {t("cartCompleteYourOrderLine2")}
          </h3>
        </div>
        <div className="flex-1 overflow-y-auto px-5 py-4 space-y-5">
          {recs.map((p) => (
            <div key={p.id} className="space-y-2">
              <div className="aspect-square bg-white rounded-md overflow-hidden">
                <img src={p.image} alt={p.name} className="w-full h-full object-cover" />
              </div>
              <div>
                <h4 className="font-semibold text-sm text-primary leading-snug">{p.name}</h4>
                <p className="text-xs text-muted-foreground mt-0.5">SAR {p.price.toFixed(2)}</p>
              </div>
              <button
                onClick={() => cart.add({ productId: p.id, qty: 1 })}
                className="w-full bg-primary text-primary-foreground text-xs font-semibold py-2.5 rounded-md hover:opacity-90 transition"
              >
                {t("cartAddToCart")}
              </button>
            </div>
          ))}
        </div>
      </aside>

      {/* Main cart panel */}
      <aside className="w-full max-w-md bg-white h-full flex flex-col shadow-2xl">
        <div className="flex items-center justify-between px-6 py-5 border-b border-border">
          <h2 className="font-display text-xl text-primary flex items-center gap-2">
            <ShoppingCart className="h-5 w-5" /> {t("cartHeading")}
          </h2>
          <button onClick={onClose} aria-label={t("cartCloseAria")} className="hover:text-primary">
            <X className="h-5 w-5" />
          </button>
        </div>

        {items.length === 0 ? (
          <div className="flex-1 flex flex-col items-center justify-center px-6 text-center">
            <p className="text-sm text-muted-foreground">{t("cartEmptyMessage")}</p>
            <Link
              to="/chocolates"
              onClick={onClose}
              className="mt-4 inline-block bg-primary text-primary-foreground rounded-md px-5 py-2 text-sm"
            >
              {t("cartBrowseProducts")}
            </Link>
          </div>
        ) : (
          <div className="flex-1 overflow-y-auto px-6 py-5 space-y-5">
            {/* Intro */}
            <div>
              <h3 className="font-semibold text-primary">{t("cartExquisiteChoice")}</h3>
              <p className="text-xs text-muted-foreground mt-1 leading-relaxed">
                {t("cartThankYouMessage")}
              </p>
            </div>

            {/* Order Summary */}
            <div className="border border-border rounded-lg overflow-hidden">
              <div className="px-4 py-3 border-b border-border">
                <h4 className="font-semibold text-primary">{t("cartOrderSummary")}</h4>
              </div>
              <div className="px-4 py-3 space-y-2 text-sm">
                {items.map((it) => {
                  const p = getProduct(it.productId);
                  return (
                    <div key={it.lineId} className="flex justify-between">
                      <span className="text-foreground/80">
                        <span className="text-muted-foreground me-2">x{it.qty}</span>
                        {p?.name}
                      </span>
                      <span>SAR {(it.unitPrice * it.qty).toFixed(2)}</span>
                    </div>
                  );
                })}
              </div>
              {isAuthed && (
                <div className="px-4 py-3 border-t border-border text-sm space-y-1.5">
                  <div className="flex justify-between">
                    <span className="text-muted-foreground flex items-center gap-1.5">
                      <Truck className="h-4 w-4" /> {t("cartDeliveryLabel")}
                    </span>
                    <span>
                      {delivery === 0 ? t("cartFreeLabel") : `SAR ${delivery.toFixed(2)}`}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground flex items-center gap-1.5">
                      <MapPin className="h-4 w-4" /> {t("cartDeliverToLabel")}{" "}
                      <span className="text-foreground font-medium">{t("cartYourAddress")}</span>
                    </span>
                  </div>
                </div>
              )}
              <div className="px-4 py-3 border-t border-border text-sm space-y-1.5">
                <div className="flex justify-between">
                  <span>{t("cartAmountLabel")}</span>
                  <span>SAR {subtotal.toFixed(2)}</span>
                </div>
                {isAuthed && discount > 0 && (
                  <div className="flex justify-between text-primary">
                    <span className="flex items-center gap-1.5">
                      <Tag className="h-4 w-4" /> {t("cartDiscountLabel")} ({activePromo?.code} −
                      {activePromo?.percent}%)
                    </span>
                    <span>−SAR {discount.toFixed(2)}</span>
                  </div>
                )}
                {isAuthed && pointsDisc > 0 && (
                  <div className="flex justify-between text-primary">
                    <span className="flex items-center gap-1.5">
                      <Wallet className="h-4 w-4" /> {t("cartPointsLabel")} ({redeemed}{" "}
                      {t("cartPtsAbbrev")})
                    </span>
                    <span>−SAR {pointsDisc.toFixed(2)}</span>
                  </div>
                )}
                <div className="flex justify-between">
                  <span>{t("cartTaxLabel")}</span>
                  <span>SAR {tax.toFixed(2)}</span>
                </div>
              </div>
              <div className="px-4 py-3 border-t border-border flex justify-between items-center">
                <span className="font-semibold">{t("cartOrderTotalLabel")}</span>
                <span className="font-semibold text-lg">SAR {total.toFixed(2)}</span>
              </div>
            </div>

            {/* Promo code (logged-in only) */}
            {isAuthed && (
              <div className="border border-border rounded-lg p-4 space-y-2">
                <label className="text-sm font-semibold text-primary flex items-center gap-1.5">
                  <Tag className="h-4 w-4" /> {t("cartPromoCodeLabel")}
                </label>
                {activePromo ? (
                  <div className="flex items-center justify-between text-sm">
                    <span>
                      <span className="font-semibold">{activePromo.code}</span>{" "}
                      <span className="text-muted-foreground">
                        {t("cartAppliedLabel")} (−{activePromo.percent}%)
                      </span>
                    </span>
                    <button
                      onClick={() => {
                        promo.clear();
                        setErr(null);
                      }}
                      className="text-xs text-primary underline hover:no-underline"
                    >
                      {t("cartRemove")}
                    </button>
                  </div>
                ) : (
                  <>
                    <div className="flex gap-2">
                      <input
                        value={code}
                        onChange={(e) => {
                          setCode(e.target.value);
                          setErr(null);
                        }}
                        onKeyDown={(e) => {
                          if (e.key === "Enter") applyPromo();
                        }}
                        placeholder={t("cartPromoPlaceholder")}
                        maxLength={20}
                        className="flex-1 border border-border rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary/30"
                      />
                      <button
                        onClick={applyPromo}
                        className="bg-primary text-primary-foreground rounded-md px-4 text-sm font-semibold hover:opacity-90 transition"
                      >
                        {t("cartApply")}
                      </button>
                    </div>
                    {err && <p className="text-xs text-destructive">{err}</p>}
                  </>
                )}
              </div>
            )}

            {/* Loyalty points (logged-in only) */}
            {isAuthed && points > 0 && (
              <div className="border border-border rounded-lg p-4 space-y-2">
                <label className="text-sm font-semibold text-primary flex items-center gap-1.5">
                  <Wallet className="h-4 w-4" /> {t("cartRedeemPoints")}
                </label>
                <p className="text-xs text-muted-foreground">
                  {t("cartBalanceLabel")} {points} {t("cartPtsAbbrev")} ({loyaltyCfg.redeemRate}{" "}
                  {t("cartPtsAbbrev")} = SAR 1)
                </p>
                {redeemed > 0 ? (
                  <div className="flex items-center justify-between text-sm">
                    <span>
                      {t("cartUsingLabel")} <span className="font-semibold">{redeemed}</span>{" "}
                      {t("cartPtsAbbrev")} (−SAR {pointsDisc.toFixed(2)})
                    </span>
                    <button
                      onClick={() => loyalty.clearRedeem()}
                      className="text-xs text-primary underline hover:no-underline"
                    >
                      {t("cartRemove")}
                    </button>
                  </div>
                ) : (
                  <div className="flex gap-2">
                    <input
                      type="number"
                      min={0}
                      max={points}
                      value={ptsInput}
                      onChange={(e) => setPtsInput(e.target.value)}
                      placeholder={`${t("cartPointsMaxPlaceholderLabel")} ${points}`}
                      className="flex-1 border border-border rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary/30"
                    />
                    <button
                      onClick={() => {
                        const n = Math.min(points, Math.max(0, parseInt(ptsInput || "0", 10)));
                        if (n > 0) {
                          loyalty.setRedeemPoints(n);
                          setPtsInput("");
                        }
                      }}
                      className="bg-primary text-primary-foreground rounded-md px-4 text-sm font-semibold hover:opacity-90 transition"
                    >
                      {t("cartApply")}
                    </button>
                  </div>
                )}
              </div>
            )}

            {/* Sign-in prompt for guests */}
            {!isAuthed && (
              <div className="border border-dashed border-primary/40 bg-primary/5 rounded-lg p-4 text-sm text-foreground/80">
                <p>
                  <Link
                    to="/login"
                    search={{ redirect: "/customize" } as never}
                    onClick={onClose}
                    className="font-semibold text-primary underline underline-offset-2"
                  >
                    {t("cartSignInLinkLabel")}
                  </Link>{" "}
                  {t("cartSignInPromptText")}
                </p>
              </div>
            )}

            {/* Actions */}
            <div className="space-y-2">
              {belowMin && (
                <p className="text-xs text-destructive text-center">
                  {t("cartMinOrderPrefix")} SAR {minOrder.toFixed(2)}. {t("cartMinOrderAddPrefix")}{" "}
                  SAR {(minOrder - subtotal).toFixed(2)} {t("cartMinOrderAddSuffix")}
                </p>
              )}
              {isAuthed ? (
                belowMin ? (
                  <button
                    disabled
                    className="block w-full text-center bg-primary/50 text-primary-foreground rounded-md py-3 font-semibold cursor-not-allowed"
                  >
                    {t("cartCheckout")}
                  </button>
                ) : (
                  <Link
                    to="/customize"
                    onClick={onClose}
                    className="block text-center bg-primary text-primary-foreground rounded-md py-3 font-semibold hover:opacity-90 transition"
                  >
                    {t("cartCheckout")}
                  </Link>
                )
              ) : (
                <Link
                  to="/login"
                  search={{ redirect: "/customize" } as never}
                  onClick={onClose}
                  className="block text-center bg-primary text-primary-foreground rounded-md py-3 font-semibold hover:opacity-90 transition"
                >
                  {t("cartSignInToCheckout")}
                </Link>
              )}
              <button
                onClick={onClose}
                className="w-full text-center border border-primary text-primary rounded-md py-3 font-semibold hover:bg-primary/5 transition"
              >
                {t("cartContinueShopping")}
              </button>
            </div>

            {/* Your Items */}
            <div>
              <h4 className="font-semibold text-primary mb-3">
                {t("cartYourItemsLabel")} ({count})
              </h4>
              <div className="space-y-4">
                {items.map((it) => {
                  const p = getProduct(it.productId);
                  return (
                    <div key={it.lineId} className="flex gap-3">
                      <img
                        src={p?.image}
                        alt={p?.name}
                        className="w-20 h-20 object-cover rounded-md"
                      />
                      <div className="flex-1 min-w-0">
                        <h5 className="font-semibold text-sm text-primary">{p?.name}</h5>
                        {it.attributes && Object.keys(it.attributes).length > 0 && (
                          <p className="text-[11px] text-muted-foreground mt-0.5">
                            {formatAttributes(it.attributes)}
                          </p>
                        )}
                        {it.inscription && (
                          <p className="text-[11px] italic text-muted-foreground truncate">
                            "{it.inscription}"
                          </p>
                        )}
                        <p className="text-[11px] text-muted-foreground mt-1">
                          {t("cartDeliveryLocal")}
                        </p>
                        <div className="mt-2 flex items-center border border-border rounded-md w-fit">
                          <button
                            onClick={() => cart.setQty(it.lineId, it.qty - 1)}
                            className="px-2 py-1"
                          >
                            <Minus className="h-3 w-3" />
                          </button>
                          <span className="px-3 text-sm">{it.qty}</span>
                          <button
                            onClick={() => cart.setQty(it.lineId, it.qty + 1)}
                            className="px-2 py-1"
                          >
                            <Plus className="h-3 w-3" />
                          </button>
                        </div>
                      </div>
                      <div className="flex flex-col items-end justify-between">
                        <span className="text-sm font-semibold">
                          SAR {(it.unitPrice * it.qty).toFixed(2)}
                        </span>
                        <button
                          onClick={() => cart.remove(it.lineId)}
                          className="text-xs text-primary underline hover:no-underline"
                        >
                          {t("cartRemove")}
                        </button>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>
        )}
      </aside>
    </div>
  );
}
