import { useSyncExternalStore } from "react";
import { getProduct } from "./products";
import { getAdminState } from "./admin-store";

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
  isDefault?: boolean;
  identitySecret?: boolean;
  timeSlot?: "tomorrow" | "another";
  deliveryDate?: string;
  deliveryTime?: string;
  recipientName?: string;
  recipientPhone?: string;
};

export type OrderStatus = "Processing" | "Paid" | "Delivered";
export const ORDER_STATUSES: OrderStatus[] = ["Processing", "Paid", "Delivered"];

export type Order = {
  id: string;
  items: { productId: string; name: string; qty: number; unitPrice: number; size?: string; flavor?: string; inscription?: string }[];
  subtotal: number;
  discount: number;
  pointsRedeemed?: number;
  pointsRedeemedValue?: number;
  tax: number;
  deliveryFee: number;
  total: number;
  address: Address | null;
  method: string;
  createdAt: number;
  status: OrderStatus;
  statusHistory: { status: OrderStatus; at: number }[];
  pointsEarned?: number;
  trackingToken?: string;
  recipientConfirmationToken?: string;
  courier?: { name: string; phone: string };
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
  rating: number;
  title?: string;
  body: string;
  createdAt: number;
  photos?: string[];
  verified?: boolean;
};

export type City = { country: string; countryCode: string; city: string; slug: string; currency: string; sameDayCutoffHour: number };
export type LoyaltyEntry = { id: string; type: "earn" | "redeem"; points: number; note: string; at: number };
export const RIYADH_AREAS = [
  "Al Aarid",
  "Al Aqiq",
  "Al Andalus",
  "Al Awali",
  "Al Badiyah",
  "Al Bandariyah",
  "Al Batha",
  "Al Dirah",
  "Al Faiha",
  "Al Farazdaq",
  "Al Faisaliyah",
  "Al Ghadir",
  "Al Hada",
  "Al Hamra",
  "Al Izdihar",
  "Al Janadriyah",
  "Al Jazeera",
  "Al Jazirah",
  "Al Khadir",
  "Al Khaleej",
  "Al Khalidiyah",
  "Al Khazan",
  "Al Maizilah",
  "Al Malaz",
  "Al Manakh",
  "Al Manar",
  "Al Manfuha",
  "Al Manfuha Al Jadidah",
  "Al Manfuha Ash Shamaliyah",
  "Al Margab",
  "Al Marqab",
  "Al Marwah",
  "Al Masif",
  "Al Mathar",
  "Al Mohammadiyah",
  "Al Munsiyah",
  "Al Murooj",
  "Al Murabba",
  "Al Naseem",
  "Al Naseem Al Gharbi",
  "Al Naseem Ash Sharqi",
  "An Nadhim",
  "An Nahdah",
  "An Narjis",
  "An Nuzha",
  "Al Olaya",
  "Al Oud",
  "Al Oud Al Janubi",
  "Al Oud Al Shamali",
  "Al Qadisiyah",
  "Al Qirawan",
  "Al Qurtubah",
  "Al Rabwah",
  "Al Rawabi",
  "Al Rawdah",
  "Al Rayyan",
  "Al Rimal",
  "Al Riyadh Al Khabra",
  "Al Sahafah",
  "Al Shifa",
  "Al Shuhada",
  "Al Sinaiyah",
  "Al Sulay",
  "Al Uraija",
  "Al Uraija Al Gharbiah",
  "Al Uraija Ash Sharqiah",
  "Al Wadi",
  "Al Waha",
  "Al Worood",
  "Al Wurud",
  "Al Yasmin",
  "Ar Rabi",
  "As Sahafah",
  "Dhahrat Laban",
  "Tuwaiq",
] as const;
export type RecipientConfirmation = {
  token: string;
  orderId: string;
  confirmed: boolean;
  address?: string;
  phone?: string;
  timeSlot?: string;
  confirmedAt?: number;
};

type State = {
  cart: CartItem[];
  user: User | null;
  addresses: Address[];
  orders: Order[];
  promo: { code: string; percent: number } | null;
  redeemedPoints: number;
  lastOrderId: string | null;
  wishlist: string[];
  reviews: Review[];
  recentlyViewed: string[];
  location: City | null;
  loyaltyPoints: number;
  loyaltyHistory: LoyaltyEntry[];
  recipientConfirmations: RecipientConfirmation[];
};

const STORAGE_KEY = "tb.state.v1";
const isBrowser = typeof window !== "undefined";
export const POINTS_PER_DOLLAR = 1;
export const POINTS_REDEEM_RATE = 20; // 20 pts = SAR 1

const seededReviews: Review[] = [
  { id: "r1", productId: "buttercream-cake", author: "Sara M.", rating: 5, title: "Absolutely divine!", body: "Ordered this for my daughter's birthday — everyone raved about it. Moist, beautifully decorated, and delivered on time.", createdAt: Date.now() - 86400000 * 3, verified: true },
  { id: "r2", productId: "buttercream-cake", author: "Ahmed K.", rating: 4, body: "Great taste and presentation. A little sweet for my liking but overall lovely.", createdAt: Date.now() - 86400000 * 8, verified: true },
  { id: "r3", productId: "choc-truffle", author: "Nadia F.", rating: 5, title: "Melt in your mouth", body: "Rich, silky, and perfectly bittersweet. Will order again.", createdAt: Date.now() - 86400000 * 12, verified: true },
  { id: "r4", productId: "swiss-frosting", author: "Layla H.", rating: 5, body: "Best cupcakes I've had in a long time. The frosting is not too sweet.", createdAt: Date.now() - 86400000 * 5, verified: true },
  { id: "r5", productId: "moose-cream", author: "Omar S.", rating: 4, body: "Very chocolatey and rich. Portion could be a bit bigger.", createdAt: Date.now() - 86400000 * 2 },
];

const initial: State = {
  cart: [],
  user: null,
  addresses: [],
  orders: [],
  promo: null,
  redeemedPoints: 0,
  lastOrderId: null,
  wishlist: [],
  reviews: seededReviews,
  recentlyViewed: [],
  location: { country: "Saudi Arabia", countryCode: "SA", city: "Riyadh", slug: "sa-riyadh", currency: "SAR", sameDayCutoffHour: 15 },
  loyaltyPoints: 0,
  loyaltyHistory: [],
  recipientConfirmations: [],
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
    parsed.loyaltyPoints = parsed.loyaltyPoints ?? 0;
    parsed.loyaltyHistory = parsed.loyaltyHistory ?? [];
    parsed.recipientConfirmations = parsed.recipientConfirmations ?? [];
    parsed.redeemedPoints = parsed.redeemedPoints ?? 0;
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
    state = { ...state, cart: [], promo: null, redeemedPoints: 0 };
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

// ---------- Location ----------
export const location = {
  set(city: City) {
    state = { ...state, location: city };
    emit();
  },
  clear() {
    state = { ...state, location: null };
    emit();
  },
};

// ---------- Loyalty ----------
export const loyalty = {
  earn(points: number, note: string) {
    if (points <= 0) return;
    const entry: LoyaltyEntry = { id: "l-" + Math.random().toString(36).slice(2, 8), type: "earn", points, note, at: Date.now() };
    state = { ...state, loyaltyPoints: state.loyaltyPoints + points, loyaltyHistory: [entry, ...state.loyaltyHistory] };
    emit();
  },
  redeem(points: number, note: string) {
    if (points <= 0 || points > state.loyaltyPoints) return false;
    const entry: LoyaltyEntry = { id: "l-" + Math.random().toString(36).slice(2, 8), type: "redeem", points, note, at: Date.now() };
    state = { ...state, loyaltyPoints: state.loyaltyPoints - points, loyaltyHistory: [entry, ...state.loyaltyHistory] };
    emit();
    return true;
  },
  setRedeemPoints(points: number) {
    const capped = Math.max(0, Math.min(points, state.loyaltyPoints));
    state = { ...state, redeemedPoints: capped };
    emit();
  },
  clearRedeem() {
    state = { ...state, redeemedPoints: 0 };
    emit();
  },
};

// ---------- Selectors ----------
export function selectSubtotal(s: State): number {
  return s.cart.reduce((sum, i) => sum + i.unitPrice * i.qty, 0);
}
export function selectPromoDiscount(s: State): number {
  const sub = selectSubtotal(s);
  return s.promo ? +(sub * (s.promo.percent / 100)).toFixed(2) : 0;
}
export function selectPointsDiscount(s: State): number {
  return +((s.redeemedPoints ?? 0) / POINTS_REDEEM_RATE).toFixed(2);
}
export function selectDiscount(s: State): number {
  return +(selectPromoDiscount(s) + selectPointsDiscount(s)).toFixed(2);
}
export function selectDeliveryFee(s: State): number {
  const sub = selectSubtotal(s) - selectDiscount(s);
  if (sub <= 0) return 0;
  const a = getAdminState();
  const threshold = a.settings.freeDeliveryThreshold ?? 0;
  if (threshold > 0 && sub >= threshold) return 0;
  return a.settings.defaultDeliveryFee ?? 15;
}
export function selectTax(s: State): number {
  const rate = (getAdminState().settings.taxRate ?? 5) / 100;
  return +(Math.max(0, selectSubtotal(s) - selectDiscount(s)) * rate).toFixed(2);
}
export function selectTotal(s: State): number {
  return +(Math.max(0, selectSubtotal(s) - selectDiscount(s)) + selectTax(s) + selectDeliveryFee(s)).toFixed(2);
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
export function selectAverageRating(id: string) {
  return (s: State) => {
    const list = s.reviews.filter((r) => r.productId === id);
    if (!list.length) return 0;
    return +(list.reduce((sum, r) => sum + r.rating, 0) / list.length).toFixed(1);
  };
}
export function selectHasPurchased(productId: string) {
  return (s: State) => s.orders.some((o) => o.items.some((it) => it.productId === productId));
}

// ---------- Auth ----------
export const auth = {
  signIn(user: User) {
    const clean = Object.fromEntries(Object.entries(user).filter(([, v]) => v !== undefined)) as Partial<User>;
    state = { ...state, user: { ...(state.user ?? {}), ...clean } };
    emit();
  },
  signOut() {
    state = { ...state, user: null };
    emit();
  },
  updateProfile(patch: Partial<User>) {
    const clean = Object.fromEntries(Object.entries(patch).filter(([, v]) => v !== undefined)) as Partial<User>;
    state = { ...state, user: { ...(state.user ?? {}), ...clean } };
    emit();
  },
};

// ---------- Addresses ----------
export const addresses = {
  add(a: Omit<Address, "id">) {
    const id = "addr-" + Math.random().toString(36).slice(2, 8);
    const shouldBeDefault = a.isDefault || state.addresses.filter((x) => !x.isGift).length === 0;
    const next: Address = { ...a, id, isDefault: shouldBeDefault && !a.isGift };
    let list = [...state.addresses, next];
    if (next.isDefault) list = list.map((x) => (x.id === id ? x : { ...x, isDefault: false }));
    state = { ...state, addresses: list };
    emit();
    return id;
  },
  remove(id: string) {
    const wasDefault = state.addresses.find((a) => a.id === id)?.isDefault;
    let list = state.addresses.filter((a) => a.id !== id);
    if (wasDefault) {
      const firstSelf = list.find((a) => !a.isGift);
      if (firstSelf) list = list.map((a) => (a.id === firstSelf.id ? { ...a, isDefault: true } : a));
    }
    state = { ...state, addresses: list };
    emit();
  },
  update(id: string, patch: Partial<Address>) {
    state = {
      ...state,
      addresses: state.addresses.map((a) => (a.id === id ? { ...a, ...patch } : a)),
    };
    emit();
  },
  setDefault(id: string) {
    state = {
      ...state,
      addresses: state.addresses.map((a) => ({ ...a, isDefault: a.id === id })),
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
  add(input: { productId: string; author: string; rating: number; title?: string; body: string; photos?: string[]; verified?: boolean }) {
    const r: Review = {
      id: "rv-" + Math.random().toString(36).slice(2, 8),
      createdAt: Date.now(),
      ...input,
    };
    state = { ...state, reviews: [r, ...state.reviews] };
    emit();
    return r;
  },
  remove(id: string) {
    state = { ...state, reviews: state.reviews.filter((r) => r.id !== id) };
    emit();
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

// ---------- Recipient Confirmation ----------
export const recipientConfirm = {
  create(orderId: string): string {
    const token = "gc-" + Math.random().toString(36).slice(2, 10);
    const rec: RecipientConfirmation = { token, orderId, confirmed: false };
    state = { ...state, recipientConfirmations: [rec, ...state.recipientConfirmations] };
    emit();
    return token;
  },
  get(token: string): RecipientConfirmation | undefined {
    return state.recipientConfirmations.find((r) => r.token === token);
  },
  confirm(token: string, patch: { address: string; phone: string; timeSlot?: string }) {
    state = {
      ...state,
      recipientConfirmations: state.recipientConfirmations.map((r) =>
        r.token === token ? { ...r, ...patch, confirmed: true, confirmedAt: Date.now() } : r,
      ),
    };
    emit();
  },
};

// ---------- Orders ----------
const COURIERS = [
  { name: "Youssef Ali", phone: "+966 55 000 0011" },
  { name: "Karim Nasser", phone: "+966 55 000 0022" },
  { name: "Reem Hassan", phone: "+966 55 000 0033" },
];

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
    const promoDisc = selectPromoDiscount(state);
    const pointsDisc = selectPointsDiscount(state);
    const tax = selectTax(state);
    const deliveryFee = selectDeliveryFee(state);
    const total = selectTotal(state);
    const now = Date.now();
    const orderId = "TB-" + Math.random().toString(36).slice(2, 8).toUpperCase();
    const netForPoints = Math.max(0, subtotal - promoDisc);
    const pointsEarned = Math.floor(netForPoints * POINTS_PER_DOLLAR);
    const pointsRedeemed = state.redeemedPoints || 0;
    const courier = COURIERS[Math.floor(Math.random() * COURIERS.length)];
    const trackingToken = "tk-" + orderId.toLowerCase().replace(/[^a-z0-9]/g, "");
    const recipientConfirmationToken = input.address?.isGift ? "gc-" + Math.random().toString(36).slice(2, 10) : undefined;

    const order: Order = {
      id: orderId,
      items,
      subtotal,
      discount,
      pointsRedeemed: pointsRedeemed || undefined,
      pointsRedeemedValue: pointsDisc || undefined,
      tax,
      deliveryFee,
      total,
      address: input.address,
      method: input.method,
      createdAt: now,
      status: "Processing",
      statusHistory: [{ status: "Processing", at: now }],
      pointsEarned,
      trackingToken,
      recipientConfirmationToken,
      courier,
    };

    const newHistory: LoyaltyEntry[] = [];
    if (pointsRedeemed > 0) {
      newHistory.push({ id: "l-" + Math.random().toString(36).slice(2, 8), type: "redeem", points: pointsRedeemed, note: `Redeemed on ${orderId}`, at: now });
    }
    if (pointsEarned > 0) {
      newHistory.push({ id: "l-" + Math.random().toString(36).slice(2, 8), type: "earn", points: pointsEarned, note: `Earned from ${orderId}`, at: now + 1 });
    }

    const newRecipientConfirmations = recipientConfirmationToken
      ? [{ token: recipientConfirmationToken, orderId, confirmed: false } as RecipientConfirmation, ...state.recipientConfirmations]
      : state.recipientConfirmations;

    state = {
      ...state,
      orders: [order, ...state.orders],
      cart: [],
      promo: null,
      redeemedPoints: 0,
      lastOrderId: order.id,
      loyaltyPoints: state.loyaltyPoints - pointsRedeemed + pointsEarned,
      loyaltyHistory: [...newHistory, ...state.loyaltyHistory],
      recipientConfirmations: newRecipientConfirmations,
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
  findByTrackingToken(token: string): Order | undefined {
    return state.orders.find((o) => o.trackingToken === token);
  },
};

export function getLastOrder(): Order | null {
  if (!state.lastOrderId) return null;
  return state.orders.find((o) => o.id === state.lastOrderId) ?? null;
}
