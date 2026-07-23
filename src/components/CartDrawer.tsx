import { Link } from "@tanstack/react-router";
import { useState } from "react";
import { X, Minus, Plus, ShoppingCart, MapPin, Truck, Tag } from "lucide-react";
import {
  useStore,
  cart,
  promo,
  selectSubtotal,
  selectDiscount,
  selectTax,
  selectTotal,
  selectDeliveryFee,
  selectCartCount,
} from "@/lib/store";
import { getProduct, products } from "@/lib/products";

const FREE_DELIVERY_THRESHOLD = 200;

export function CartDrawer({ open, onClose }: { open: boolean; onClose: () => void }) {
  const items = useStore((s) => s.cart);
  const subtotal = useStore(selectSubtotal);
  const discount = useStore(selectDiscount);
  const tax = useStore(selectTax);
  const total = useStore(selectTotal);
  const delivery = useStore(selectDeliveryFee);
  const count = useStore(selectCartCount);
  const activePromo = useStore((s) => s.promo);
  const [code, setCode] = useState("");
  const [err, setErr] = useState<string | null>(null);

  if (!open) return null;

  function applyPromo() {
    setErr(null);
    if (!code.trim()) return;
    const ok = promo.apply(code);
    if (!ok) setErr("Invalid promo code");
    else setCode("");
  }

  const remaining = Math.max(0, FREE_DELIVERY_THRESHOLD - subtotal);
  const progress = Math.min(100, (subtotal / FREE_DELIVERY_THRESHOLD) * 100);

  // Recommendations: products not currently in cart
  const inCartIds = new Set(items.map((i) => i.productId));
  const recs = products.filter((p) => !inCartIds.has(p.id)).slice(0, 6);

  return (
    <div className="fixed inset-0 z-50 flex justify-end">
      <button
        aria-label="Close cart"
        onClick={onClose}
        className="flex-1 bg-black/40"
      />

      {/* Recommendations rail */}
      <aside className="hidden md:flex w-72 bg-[#f7e6e6] h-full flex-col shadow-2xl">
        <div className="px-5 py-5 border-b border-black/5">
          <h3 className="font-display text-lg text-primary leading-tight">
            Complete Your<br />Order...
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
                <p className="text-xs text-muted-foreground mt-0.5">${p.price.toFixed(2)}</p>
              </div>
              <button
                onClick={() => cart.add({ productId: p.id, qty: 1 })}
                className="w-full bg-primary text-primary-foreground text-xs font-semibold py-2.5 rounded-md hover:opacity-90 transition"
              >
                Add To Cart
              </button>
            </div>
          ))}
        </div>
      </aside>

      {/* Main cart panel */}
      <aside className="w-full max-w-md bg-white h-full flex flex-col shadow-2xl">
        <div className="flex items-center justify-between px-6 py-5 border-b border-border">
          <h2 className="font-display text-xl text-primary flex items-center gap-2">
            <ShoppingCart className="h-5 w-5" /> Cart
          </h2>
          <button onClick={onClose} aria-label="Close" className="hover:text-primary">
            <X className="h-5 w-5" />
          </button>
        </div>

        {items.length === 0 ? (
          <div className="flex-1 flex flex-col items-center justify-center px-6 text-center">
            <p className="text-sm text-muted-foreground">Your cart is empty.</p>
            <Link
              to="/chocolates"
              onClick={onClose}
              className="mt-4 inline-block bg-primary text-primary-foreground rounded-md px-5 py-2 text-sm"
            >
              Browse Products
            </Link>
          </div>
        ) : (
          <div className="flex-1 overflow-y-auto px-6 py-5 space-y-5">
            {/* Intro */}
            <div>
              <h3 className="font-semibold text-primary">Exquisite Choice</h3>
              <p className="text-xs text-muted-foreground mt-1 leading-relaxed">
                Thank you for your selection. Review your order below and proceed to checkout when ready.
              </p>
            </div>

            {/* Free delivery tracker */}
            <div className="border border-border rounded-lg p-4">
              <div className="flex items-center gap-3">
                <Truck className="h-6 w-6 text-primary shrink-0" />
                <p className="text-sm flex-1">
                  {remaining > 0 ? (
                    <>Only <span className="font-semibold">${remaining.toFixed(2)}</span> to Go for Free Delivery!</>
                  ) : (
                    <span className="font-semibold text-primary">You've unlocked Free Delivery!</span>
                  )}
                </p>
              </div>
              <div className="mt-3 flex items-center gap-2">
                <div className="flex-1 h-1.5 bg-secondary rounded-full overflow-hidden">
                  <div className="h-full bg-primary rounded-full transition-all" style={{ width: `${progress}%` }} />
                </div>
                <span className="text-[11px] font-semibold text-muted-foreground">
                  ${subtotal.toFixed(2)}
                </span>
              </div>
            </div>

            {/* Order Summary */}
            <div className="border border-border rounded-lg overflow-hidden">
              <div className="px-4 py-3 border-b border-border">
                <h4 className="font-semibold text-primary">Order Summary</h4>
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
                      <span>${(it.unitPrice * it.qty).toFixed(2)}</span>
                    </div>
                  );
                })}
              </div>
              <div className="px-4 py-3 border-t border-border text-sm space-y-1.5">
                <div className="flex justify-between">
                  <span className="text-muted-foreground flex items-center gap-1.5">
                    <Truck className="h-4 w-4" /> Delivery
                  </span>
                  <span>{delivery === 0 ? "Free" : `$${delivery.toFixed(2)}`}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground flex items-center gap-1.5">
                    <MapPin className="h-4 w-4" /> Deliver to <span className="text-foreground font-medium">your address</span>
                  </span>
                </div>
              </div>
              <div className="px-4 py-3 border-t border-border text-sm space-y-1.5">
                <div className="flex justify-between">
                  <span>Amount</span>
                  <span>${subtotal.toFixed(2)}</span>
                </div>
                <div className="flex justify-between">
                  <span>Tax</span>
                  <span>${tax.toFixed(2)}</span>
                </div>
              </div>
              <div className="px-4 py-3 border-t border-border flex justify-between items-center">
                <span className="font-semibold">Order Total</span>
                <span className="font-semibold text-lg">${total.toFixed(2)}</span>
              </div>
            </div>

            {/* Actions */}
            <div className="space-y-2">
              <Link
                to="/customize"
                onClick={onClose}
                className="block text-center bg-primary text-primary-foreground rounded-md py-3 font-semibold hover:opacity-90 transition"
              >
                Checkout
              </Link>
              <button
                onClick={onClose}
                className="w-full text-center border border-primary text-primary rounded-md py-3 font-semibold hover:bg-primary/5 transition"
              >
                Continue Shopping
              </button>
            </div>

            {/* Your Items */}
            <div>
              <h4 className="font-semibold text-primary mb-3">Your Items ({count})</h4>
              <div className="space-y-4">
                {items.map((it) => {
                  const p = getProduct(it.productId);
                  return (
                    <div key={it.lineId} className="flex gap-3">
                      <img src={p?.image} alt={p?.name} className="w-20 h-20 object-cover rounded-md" />
                      <div className="flex-1 min-w-0">
                        <h5 className="font-semibold text-sm text-primary">{p?.name}</h5>
                        {(it.size || it.flavor) && (
                          <p className="text-[11px] text-muted-foreground mt-0.5">
                            {[it.size, it.flavor].filter(Boolean).join(" · ")}
                          </p>
                        )}
                        {it.inscription && (
                          <p className="text-[11px] italic text-muted-foreground truncate">"{it.inscription}"</p>
                        )}
                        <p className="text-[11px] text-muted-foreground mt-1">Delivery: Local</p>
                        <div className="mt-2 flex items-center border border-border rounded-md w-fit">
                          <button onClick={() => cart.setQty(it.lineId, it.qty - 1)} className="px-2 py-1">
                            <Minus className="h-3 w-3" />
                          </button>
                          <span className="px-3 text-sm">{it.qty}</span>
                          <button onClick={() => cart.setQty(it.lineId, it.qty + 1)} className="px-2 py-1">
                            <Plus className="h-3 w-3" />
                          </button>
                        </div>
                      </div>
                      <div className="flex flex-col items-end justify-between">
                        <span className="text-sm font-semibold">${(it.unitPrice * it.qty).toFixed(2)}</span>
                        <button
                          onClick={() => cart.remove(it.lineId)}
                          className="text-xs text-primary underline hover:no-underline"
                        >
                          Remove
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
