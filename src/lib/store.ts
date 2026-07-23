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
};

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
};

export type User = {
  name?: string;
  email?: string;
  phone?: string;
  birthDate?: string;
};

type State = {
  cart: CartItem[];
  user: User | null;
  addresses: Address[];
  orders: Order[];
  promo: { code: string; percent: number } | null;
  lastOrderId: string | null;
};

const STORAGE_KEY = "tb.state.v1";
const isBrowser = typeof window !== "undefined";

const initial: State = {
  cart: [],
  user: null,
  addresses: [],
  orders: [],
  promo: null,
  lastOrderId: null,
};

function load(): State {
  if (!isBrowser) return initial;
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return initial;
    return { ...initial, ...JSON.parse(raw) };
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

function getSnapshot() {
  return state;
}
function getServerSnapshot() {
  return initial;
}

export function useStore<T>(selector: (s: State) => T): T {
  const snap = useSyncExternalStore(subscribe, () => selector(state), () => selector(initial));
  return snap;
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
      createdAt: Date.now(),
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
};

export function getLastOrder(): Order | null {
  if (!state.lastOrderId) return null;
  return state.orders.find((o) => o.id === state.lastOrderId) ?? null;
}
