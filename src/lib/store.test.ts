import { act, renderHook } from "@testing-library/react";
import { beforeEach, describe, expect, it } from "vitest";
import { cart, selectCartCount, selectDeliveryFee, selectSubtotal, selectTax, selectTotal, useStore } from "@/lib/store";
import { registerProducts, type Product } from "@/lib/products";

// These exercise the pure selectors directly against a hand-built State object rather
// than going through the module's internal mutable `state` + cart.add() (which depends
// on getProduct() catalogue-cache lookups now that products.ts is API-backed) — the
// point here is verifying the VAT arithmetic itself (D08/D21), not cart mutation.
type State = Parameters<typeof selectSubtotal>[0];

function makeState(items: { unitPrice: number; qty: number }[]): State {
  return {
    cart: items.map((i, idx) => ({
      lineId: `line-${idx}`,
      productId: `product-${idx}`,
      qty: i.qty,
      unitPrice: i.unitPrice,
    })),
    user: null,
    addresses: [],
    orders: [],
    promo: null,
    redeemedPoints: 0,
    lastOrderId: null,
    wishlist: [],
    reviews: [],
    recentlyViewed: [],
    location: null,
    loyaltyPoints: 0,
    loyaltyHistory: [],
    recipientConfirmations: [],
  } as unknown as State;
}

describe("VAT-inclusive checkout math (D08/D21)", () => {
  it("selectTotal never adds a separate VAT amount on top of the subtotal", () => {
    const state = makeState([{ unitPrice: 100, qty: 1 }]);

    const subtotal = selectSubtotal(state);
    const total = selectTotal(state);

    // Prices are VAT-inclusive: total = subtotal - discount + delivery, and must NOT
    // equal subtotal + tax (the pre-fix double-counting bug).
    expect(total).toBe(+(subtotal + selectDeliveryFee(state)).toFixed(2));
    expect(total).not.toBe(+(subtotal + selectTax(state) + selectDeliveryFee(state)).toFixed(2));
  });

  it("selectTax reports the VAT portion already included in the subtotal, not an add-on", () => {
    const state = makeState([{ unitPrice: 105, qty: 1 }]);

    // At a 5% rate, SAR 105 inclusive of VAT contains exactly SAR 5 of VAT
    // (105 / 1.05 = 100 net, 100 * 0.05 = 5) — not 105 * 0.05 = 5.25, which is what
    // the old (buggy) "VAT added on top" formula would have produced.
    expect(selectTax(state)).toBe(5);
  });

  it("an empty cart has zero subtotal, tax, and total", () => {
    const state = makeState([]);

    expect(selectSubtotal(state)).toBe(0);
    expect(selectTax(state)).toBe(0);
    expect(selectTotal(state)).toBe(0);
  });
});

describe("useStore is exported for components to subscribe to cart state", () => {
  it("is a function", () => {
    expect(typeof useStore).toBe("function");
    expect(typeof cart.add).toBe("function");
  });
});

describe("cart mutations", () => {
  const productA: Product = { id: "test-product-a", name: "Test Cake", price: 40, image: "a.jpg", category: "cakes" };
  const productB: Product = { id: "test-product-b", name: "Test Cupcake", price: 12, image: "b.jpg", category: "cupcakes" };

  beforeEach(() => {
    registerProducts([productA, productB]);
    act(() => cart.clear());
  });

  // renderHook subscribes a real component tree to the store, so result.current stays
  // in sync as cart.*() mutations fire — the same path components use, unlike reaching
  // into the module's private `state` variable (which isn't exported).
  function renderCartState() {
    return renderHook(() => useStore((s) => s)).result;
  }

  it("adding an unknown product id is a no-op (never adds a line with no product data)", () => {
    const state = renderCartState();
    act(() => cart.add({ productId: "does-not-exist" }));
    expect(selectCartCount(state.current)).toBe(0);
  });

  it("adding the same product+options twice increments quantity on one line, not two lines", () => {
    const state = renderCartState();
    act(() => cart.add({ productId: productA.id, qty: 1 }));
    act(() => cart.add({ productId: productA.id, qty: 2 }));

    expect(state.current.cart).toHaveLength(1);
    expect(state.current.cart[0].qty).toBe(3);
    expect(selectCartCount(state.current)).toBe(3);
  });

  it("adding the same product with different attributes creates separate lines", () => {
    const state = renderCartState();
    act(() => cart.add({ productId: productA.id, attributes: { size: "Small" } }));
    act(() => cart.add({ productId: productA.id, attributes: { size: "Large" } }));

    expect(state.current.cart).toHaveLength(2);
  });

  it("setQty updates the line quantity and removes the line once it reaches zero", () => {
    const state = renderCartState();
    act(() => cart.add({ productId: productA.id, qty: 1 }));
    const lineId = state.current.cart[0].lineId;

    act(() => cart.setQty(lineId, 5));
    expect(state.current.cart[0].qty).toBe(5);

    act(() => cart.setQty(lineId, 0));
    expect(state.current.cart).toHaveLength(0);
  });

  it("remove drops only the targeted line", () => {
    const state = renderCartState();
    act(() => cart.add({ productId: productA.id }));
    act(() => cart.add({ productId: productB.id }));
    const [lineA] = state.current.cart;

    act(() => cart.remove(lineA.lineId));

    expect(state.current.cart).toHaveLength(1);
    expect(state.current.cart[0].productId).toBe(productB.id);
  });

  it("clear empties the cart and resets any applied promo", () => {
    const state = renderCartState();
    act(() => cart.add({ productId: productA.id }));
    act(() => cart.clear());
    expect(state.current.cart).toHaveLength(0);
    expect(state.current.promo).toBeNull();
  });

  it("subtotal reflects live catalogue prices for every line in the cart", () => {
    const state = renderCartState();
    act(() => cart.add({ productId: productA.id, qty: 2 })); // 2 * 40
    act(() => cart.add({ productId: productB.id, qty: 3 })); // 3 * 12
    expect(selectSubtotal(state.current)).toBe(116);
  });
});
