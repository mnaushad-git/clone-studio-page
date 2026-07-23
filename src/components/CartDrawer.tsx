import { Link } from "@tanstack/react-router";
import { X, Minus, Plus, ShoppingBag, Trash2 } from "lucide-react";
import { useStore, cart, selectSubtotal, selectCartCount } from "@/lib/store";
import { getProduct } from "@/lib/products";

export function CartDrawer({ open, onClose }: { open: boolean; onClose: () => void }) {
  const items = useStore((s) => s.cart);
  const subtotal = useStore(selectSubtotal);
  const count = useStore(selectCartCount);

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex">
      <button
        aria-label="Close cart"
        onClick={onClose}
        className="flex-1 bg-black/40"
      />
      <aside className="w-full max-w-md bg-white h-full flex flex-col shadow-2xl">
        <div className="flex items-center justify-between px-6 py-5 border-b border-border">
          <h2 className="font-display text-xl text-primary flex items-center gap-2">
            <ShoppingBag className="h-5 w-5" /> Your Cart ({count})
          </h2>
          <button onClick={onClose} aria-label="Close" className="hover:text-primary"><X className="h-5 w-5" /></button>
        </div>

        <div className="flex-1 overflow-y-auto px-6 py-5 space-y-4">
          {items.length === 0 && (
            <div className="text-center py-16">
              <p className="text-sm text-muted-foreground">Your cart is empty.</p>
              <Link to="/chocolates" onClick={onClose} className="mt-4 inline-block bg-primary text-primary-foreground rounded-md px-5 py-2 text-sm">
                Browse Products
              </Link>
            </div>
          )}
          {items.map((it) => {
            const p = getProduct(it.productId);
            return (
              <div key={it.lineId} className="flex gap-3 border-b border-border pb-4">
                <img src={p?.image} alt={p?.name} className="w-20 h-20 object-cover rounded-md" />
                <div className="flex-1 min-w-0">
                  <div className="flex items-start justify-between gap-2">
                    <div className="min-w-0">
                      <h3 className="font-medium text-sm truncate">{p?.name}</h3>
                      {(it.size || it.flavor) && (
                        <p className="text-[11px] text-muted-foreground mt-0.5">
                          {[it.size, it.flavor].filter(Boolean).join(" · ")}
                        </p>
                      )}
                      {it.inscription && (
                        <p className="text-[11px] italic text-muted-foreground truncate">"{it.inscription}"</p>
                      )}
                    </div>
                    <button
                      onClick={() => cart.remove(it.lineId)}
                      aria-label="Remove"
                      className="text-muted-foreground hover:text-destructive"
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>
                  </div>
                  <div className="mt-2 flex items-center justify-between">
                    <div className="flex items-center border border-border rounded-md">
                      <button onClick={() => cart.setQty(it.lineId, it.qty - 1)} className="px-2 py-1"><Minus className="h-3 w-3" /></button>
                      <span className="px-3 text-sm">{it.qty}</span>
                      <button onClick={() => cart.setQty(it.lineId, it.qty + 1)} className="px-2 py-1"><Plus className="h-3 w-3" /></button>
                    </div>
                    <span className="text-sm font-semibold">${(it.unitPrice * it.qty).toFixed(2)}</span>
                  </div>
                </div>
              </div>
            );
          })}
        </div>

        {items.length > 0 && (
          <div className="border-t border-border p-6 space-y-3">
            <div className="flex items-center justify-between text-sm">
              <span>Subtotal</span>
              <span className="font-semibold">${subtotal.toFixed(2)}</span>
            </div>
            <p className="text-[11px] text-muted-foreground">Shipping and taxes calculated at checkout.</p>
            <Link
              to="/customize"
              onClick={onClose}
              className="block text-center bg-primary text-primary-foreground rounded-md py-3 font-semibold hover:opacity-90 transition"
            >
              Checkout
            </Link>
          </div>
        )}
      </aside>
    </div>
  );
}
