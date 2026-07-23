import { useSyncExternalStore } from "react";
import { getProduct } from "./products";

export type CartItem = {
  lineId: string;
  productId: string;
  qty: number;
  unitPrice: number;
  size?: string;
  flavor?: string;
  inscription?: string;
};

export type Address = {
  id: string;
  name: string;
  phone: string;
  area: string;
  address: string;
  extra?: string;
  isGift?: boolean;
  identitySecret?: boolean;
  timeSlot?: "tomorrow" | "another";
  deliveryDate?: string;
  deliveryTime?: string;
};

export type OrderStatus = "Processing" | "Paid" | "Delivered";
export const ORDER_STATUSES: OrderStatus[] = ["Processing", "Paid", "Delivered"];

export type Order = {
  id: string;
  items: { productId: string; name: string; qty: number; unitPrice: number; size?: string; flavor?: string; inscription?: string }[];
  subtotal: number;
  discount: number;
  tax: number;
  deliveryFee: number;
  total: number;
  address: Address | null;
  method: string;
  createdAt: number;
  status: OrderStatus;
  statusHistory: { status: OrderStatus; at: number }[];
};

export type User = {
  name?: string;
  email?: string;
  phone?: string;
  birthDate?: string;
};

export type Review = {
  id: string;
  productId: string;
  author: string;
  rating: number; // 1-5
  title?: string;
  body: string;
  createdAt: number;
};

type State = {
  cart: CartItem[];
  user: User | null;
  addresses: Address[];
  orders: Order[];
  promo: { code: string; percent: number } | null;
  lastOrderId: string | null;
  wishlist: string[];
  reviews: Review[];
  recentlyViewed: string[];
};

const STORAGE_KEY = "tb.state.v1";
const isBrowser = typeof window !== "undefined";

const seededReviews: Review[] = [
  { id: "r1", productId: "buttercream-cake", author: "Sara M.", rating: 5, title: "Absolutely divine!", body: "Ordered this for my daughter's birthday — everyone raved about it. Moist, beautifully decorated, and delivered on time.", createdAt: Date.now() - 86400000 * 3 },
  { id: "r2", productId: "buttercream-cake", author: "Ahmed K.", rating: 4, body: "Great taste and presentation. A little sweet for my liking but overall lovely.", createdAt: Date.now() - 86400000 * 8 },
  { id: "r3", productId: "choc-truffle", author: "Nadia F.", rating: 5, title: "Melt in your mouth", body: "Rich, silky, and perfectly bittersweet. Will order again.", createdAt: Date.now() - 86400000 * 12 },
  { id: "r4", productId: "swiss-frosting", author: "Layla H.", rating: 5, body: "Best cupcakes I've had in a long time. The frosting is not too sweet.", createdAt: Date.now() - 86400000 * 5 },
  { id: "r5", productId: "moose-cream", author: "Omar S.", rating: 4, body: "Very chocolatey and rich. Portion could be a bit bigger.", createdAt: Date.now() - 86400000 * 2 },
];

const initial: State = {
  cart: [],
  user: null,
  addresses: [],
  orders: [],
  promo: null,
  lastOrderId: null,
  wishlist: [],
  reviews: seededReviews,
  recentlyViewed: [],
};

function load(): State {
  if (!isBrowser) return initial;
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return initial;
    const parsed = { ...initial, ...JSON.parse(raw) } as State;
    parsed.orders = (parsed.orders ?? []).map((o) => ({
      ...o,
      status: o.status ?? "Processing",
      statusHistory: o.statusHistory ?? [{ status: o.status ?? "Processing", at: o.createdAt }],
    }));
    parsed.wishlist = parsed.wishlist ?? [];
    parsed.recentlyViewed = parsed.recentlyViewed ?? [];
    // Merge seeded reviews with any saved ones (keep custom ones)
    const savedReviews = parsed.reviews ?? [];
    const seededIds = new Set(seededReviews.map((r) => r.id));
    parsed.reviews = [
      ...seededReviews,
      ...savedReviews.filter((r) => !seededIds.has(r.id)),
    ];
    return parsed;
  } catch {
    return initial;
  }
}

let state: State = load();
const listeners = new Set<() => void>();

function persist() {
  if (!isBrowser) return;
  try { localStorage.setItem(STORAGE_KEY, JSON.stringify(state)); } catch {}
}

function emit() {
  persist();
  listeners.forEach((l) => l());
}

function subscribe(fn: () => void) {
  listeners.add(fn);
  return () => listeners.delete(fn);
}

export function useStore<T>(selector: (s: State) => T): T {
  return useSyncExternalStore(subscribe, () => selector(state), () => selector(initial));
}

// ---------- Cart ----------
const PROMOS: Record<string, number> = { WELCOME10: 10, SWEET15: 15, TB20: 20 };

export const cart = {
  add(input: {
    productId: string;
    qty?: number;
    size?: string;
    flavor?: string;
    inscription?: string;
    unitPrice?: number;
  }) {
    const p = getProduct(input.productId);
    if (!p) return;
    const unitPrice = input.unitPrice ?? (p.price + (p.sizes?.find((s) => s.label === input.size)?.delta ?? 0));
    const key = [input.productId, input.size ?? "", input.flavor ?? "", input.inscription ?? ""].join("|");
    const existing = state.cart.find((c) => c.lineId === key);
    if (existing) {
      existing.qty += input.qty ?? 1;
      state = { ...state, cart: [...state.cart] };
    } else {
      state = {
        ...state,
        cart: [
          ...state.cart,
          {
            lineId: key,
            productId: input.productId,
            qty: input.qty ?? 1,
            unitPrice,
            size: input.size,
            flavor: input.flavor,
            inscription: input.inscription,
          },
        ],
      };
    }
    emit();
  },
  setQty(lineId: string, qty: number) {
    state = {
      ...state,
      cart: state.cart
        .map((c) => (c.lineId === lineId ? { ...c, qty: Math.max(0, qty) } : c))
        .filter((c) => c.qty > 0),
    };
    emit();
  },
  remove(lineId: string) {
    state = { ...state, cart: state.cart.filter((c) => c.lineId !== lineId) };
    emit();
  },
  clear() {
    state = { ...state, cart: [], promo: null };
    emit();
  },
};

export const promo = {
  apply(code: string): boolean {
    const c = code.trim().toUpperCase();
    const percent = PROMOS[c];
    if (!percent) return false;
    state = { ...state, promo: { code: c, percent } };
    emit();
    return true;
  },
  clear() {
    state = { ...state, promo: null };
    emit();
  },
};

// ---------- Selectors ----------
export function selectSubtotal(s: State): number {
  return s.cart.reduce((sum, i) => sum + i.unitPrice * i.qty, 0);
}
export function selectDiscount(s: State): number {
  const sub = selectSubtotal(s);
  return s.promo ? +(sub * (s.promo.percent / 100)).toFixed(2) : 0;
}
export function selectDeliveryFee(s: State): number {
  const sub = selectSubtotal(s) - selectDiscount(s);
  return sub === 0 || sub >= 200 ? 0 : 15;
}
export function selectTax(s: State): number {
  return +((selectSubtotal(s) - selectDiscount(s)) * 0.05).toFixed(2);
}
export function selectTotal(s: State): number {
  return +(selectSubtotal(s) - selectDiscount(s) + selectTax(s) + selectDeliveryFee(s)).toFixed(2);
}
export function selectCartCount(s: State): number {
  return s.cart.reduce((n, i) => n + i.qty, 0);
}
export function selectWishlistCount(s: State): number {
  return s.wishlist.length;
}
export function selectIsWishlisted(id: string) {
  return (s: State) => s.wishlist.includes(id);
}
export function selectProductReviews(id: string) {
  return (s: State) => s.reviews.filter((r) => r.productId === id).sort((a, b) => b.createdAt - a.createdAt);
}
export function selectAverageRating(id: string) {
  return (s: State) => {
    const list = s.reviews.filter((r) => r.productId === id);
    if (!list.length) return 0;
    return +(list.reduce((sum, r) => sum + r.rating, 0) / list.length).toFixed(1);
  };
}

// ---------- Auth ----------
export const auth = {
  signIn(user: User) {
    state = { ...state, user: { ...state.user, ...user } };
    emit();
  },
  signOut() {
    state = { ...state, user: null };
    emit();
  },
  updateProfile(patch: Partial<User>) {
    state = { ...state, user: { ...(state.user ?? {}), ...patch } };
    emit();
  },
};

// ---------- Addresses ----------
export const addresses = {
  add(a: Omit<Address, "id">) {
    const id = "addr-" + Math.random().toString(36).slice(2, 8);
    state = { ...state, addresses: [...state.addresses, { ...a, id }] };
    emit();
    return id;
  },
  remove(id: string) {
    state = { ...state, addresses: state.addresses.filter((a) => a.id !== id) };
    emit();
  },
  update(id: string, patch: Partial<Address>) {
    state = {
      ...state,
      addresses: state.addresses.map((a) => (a.id === id ? { ...a, ...patch } : a)),
    };
    emit();
  },
};

// ---------- Wishlist ----------
export const wishlist = {
  toggle(productId: string): boolean {
    const has = state.wishlist.includes(productId);
    state = {
      ...state,
      wishlist: has ? state.wishlist.filter((id) => id !== productId) : [...state.wishlist, productId],
    };
    emit();
    return !has;
  },
  add(productId: string) {
    if (state.wishlist.includes(productId)) return;
    state = { ...state, wishlist: [...state.wishlist, productId] };
    emit();
  },
  remove(productId: string) {
    state = { ...state, wishlist: state.wishlist.filter((id) => id !== productId) };
    emit();
  },
  clear() {
    state = { ...state, wishlist: [] };
    emit();
  },
};

// ---------- Reviews ----------
export const reviews = {
  add(input: { productId: string; author: string; rating: number; title?: string; body: string }) {
    const r: Review = {
      id: "rv-" + Math.random().toString(36).slice(2, 8),
      createdAt: Date.now(),
      ...input,
    };
    state = { ...state, reviews: [r, ...state.reviews] };
    emit();
    return r;
  },
};

// ---------- Recently Viewed ----------
export const recentlyViewed = {
  track(productId: string) {
    const filtered = state.recentlyViewed.filter((id) => id !== productId);
    state = { ...state, recentlyViewed: [productId, ...filtered].slice(0, 12) };
    emit();
  },
};

// ---------- Orders ----------
export const orders = {
  place(input: { address: Address | null; method: string }): Order {
    const items = state.cart.map((c) => {
      const p = getProduct(c.productId);
      return {
        productId: c.productId,
        name: p?.name ?? c.productId,
        qty: c.qty,
        unitPrice: c.unitPrice,
        size: c.size,
        flavor: c.flavor,
        inscription: c.inscription,
      };
    });
    const subtotal = selectSubtotal(state);
    const discount = selectDiscount(state);
    const tax = selectTax(state);
    const deliveryFee = selectDeliveryFee(state);
    const total = selectTotal(state);
    const now = Date.now();
    const order: Order = {
      id: "TB-" + Math.random().toString(36).slice(2, 8).toUpperCase(),
      items,
      subtotal,
      discount,
      tax,
      deliveryFee,
      total,
      address: input.address,
      method: input.method,
      createdAt: now,
      status: "Processing",
      statusHistory: [{ status: "Processing", at: now }],
    };
    state = {
      ...state,
      orders: [order, ...state.orders],
      cart: [],
      promo: null,
      lastOrderId: order.id,
    };
    emit();
    return order;
  },
  setStatus(id: string, status: OrderStatus) {
    state = {
      ...state,
      orders: state.orders.map((o) =>
        o.id === id
          ? {
              ...o,
              status,
              statusHistory: o.statusHistory.some((h) => h.status === status)
                ? o.statusHistory
                : [...o.statusHistory, { status, at: Date.now() }],
            }
          : o,
      ),
    };
    emit();
  },
  advance(id: string) {
    const o = state.orders.find((x) => x.id === id);
    if (!o) return;
    const idx = ORDER_STATUSES.indexOf(o.status);
    const next = ORDER_STATUSES[idx + 1];
    if (next) this.setStatus(id, next);
  },
};

export function getLastOrder(): Order | null {
  if (!state.lastOrderId) return null;
  return state.orders.find((o) => o.id === state.lastOrderId) ?? null;
}
