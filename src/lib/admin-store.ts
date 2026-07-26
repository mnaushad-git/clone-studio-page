import { useSyncExternalStore } from "react";

// ============================================================
// Admin Configuration Store (localStorage-backed, no DB)
// Everything here is frontend-only and ready to be swapped
// with a FastAPI + Postgres backend later.
// ============================================================

export type Role = "owner" | "admin" | "manager" | "support" | "kitchen";
export const ROLES: Role[] = ["owner", "admin", "manager", "support", "kitchen"];

export type StaffMember = {
  id: string;
  name: string;
  email: string;
  phone?: string;
  role: Role;
  active: boolean;
  createdAt: number;
};

export type PromoCode = {
  id: string;
  code: string;
  type: "percent" | "fixed";
  value: number;
  minSubtotal?: number;
  usageLimit?: number;
  used: number;
  startsAt?: string;
  endsAt?: string;
  active: boolean;
};

export type DeliveryZone = {
  id: string;
  name: string;
  fee: number;
  etaMinutes: number;
  active: boolean;
};

export type DeliverySlot = {
  id: string;
  label: string;
  from: string; // HH:mm
  to: string;
  capacity: number;
  active: boolean;
};

export type Banner = {
  id: string;
  title: string;
  subtitle?: string;
  ctaLabel?: string;
  ctaLink?: string;
  image?: string;
  position: "hero" | "midpage" | "footer";
  active: boolean;
  order: number;
};

export type CategoryConfig = {
  id: string;
  label: string;
  slug: string;
  icon?: string;
  visible: boolean;
  order: number;
};

export type PaymentMethod = {
  id: string;
  label: string;
  active: boolean;
  fee?: number;
};

export type LoyaltyConfig = {
  enabled: boolean;
  pointsPerSar: number;
  redeemRate: number; // pts = SAR 1
  signupBonus: number;
  birthdayBonus: number;
};

export type SiteSettings = {
  brandName: string;
  supportEmail: string;
  supportPhone: string;
  currency: string;
  taxRate: number; // percent
  defaultDeliveryFee: number;
  freeDeliveryThreshold: number;
  minOrder: number;
  languages: { code: string; label: string; enabled: boolean }[];
  defaultLanguage: string;
  operatingHours: { open: string; close: string };
  socials: { instagram?: string; twitter?: string; facebook?: string; tiktok?: string };
  maintenanceMode: boolean;
  guestCheckout: boolean;
};

export type ProductOverride = {
  id: string; // productId
  priceOverride?: number;
  stock?: number;
  visible: boolean;
  featured: boolean;
  badge?: string;
};

export type HomepageSection = {
  id: string;
  label: string;
  visible: boolean;
  order: number;
};

export type AdminNotification = {
  id: string;
  title: string;
  body: string;
  at: number;
  read: boolean;
};

export type AdminTheme = {
  primary: string;
  primaryForeground: string;
  accent: string;
  background: string;
  sidebarActive: string;
};

export const DEFAULT_ADMIN_THEME: AdminTheme = {
  primary: "#3d2817",
  primaryForeground: "#faf7f2",
  accent: "#f59e0b",
  background: "#f5efe4",
  sidebarActive: "#fcd34d",
};

export const ADMIN_THEME_PRESETS: { name: string; theme: AdminTheme }[] = [
  { name: "Terrific Brown", theme: DEFAULT_ADMIN_THEME },
  { name: "Midnight", theme: { primary: "#1e293b", primaryForeground: "#f8fafc", accent: "#38bdf8", background: "#f1f5f9", sidebarActive: "#38bdf8" } },
  { name: "Emerald", theme: { primary: "#064e3b", primaryForeground: "#ecfdf5", accent: "#10b981", background: "#f0fdf4", sidebarActive: "#34d399" } },
  { name: "Rose", theme: { primary: "#881337", primaryForeground: "#fff1f2", accent: "#f43f5e", background: "#fff1f2", sidebarActive: "#fda4af" } },
  { name: "Indigo", theme: { primary: "#312e81", primaryForeground: "#eef2ff", accent: "#818cf8", background: "#eef2ff", sidebarActive: "#a5b4fc" } },
];

type AdminState = {
  staff: StaffMember[];
  promos: PromoCode[];
  zones: DeliveryZone[];
  slots: DeliverySlot[];
  banners: Banner[];
  categories: CategoryConfig[];
  paymentMethods: PaymentMethod[];
  loyalty: LoyaltyConfig;
  settings: SiteSettings;
  theme: AdminTheme;
  productOverrides: Record<string, ProductOverride>;
  homepageSections: HomepageSection[];
  notifications: AdminNotification[];
  adminSession: { email: string; role: Role } | null;
};

const KEY = "tb.admin.v1";
const isBrowser = typeof window !== "undefined";

const initial: AdminState = {
  staff: [
    { id: "s1", name: "Owner", email: "owner@terrificbites.sa", role: "owner", active: true, createdAt: Date.now() - 86400000 * 90 },
    { id: "s2", name: "Layla A.", email: "layla@terrificbites.sa", role: "manager", active: true, createdAt: Date.now() - 86400000 * 60 },
    { id: "s3", name: "Omar F.", email: "omar@terrificbites.sa", role: "support", active: true, createdAt: Date.now() - 86400000 * 30 },
    { id: "s4", name: "Chef Noura", email: "noura@terrificbites.sa", role: "kitchen", active: true, createdAt: Date.now() - 86400000 * 20 },
  ],
  promos: [
    { id: "p1", code: "WELCOME10", type: "percent", value: 10, used: 42, active: true },
    { id: "p2", code: "SWEET15", type: "percent", value: 15, minSubtotal: 100, used: 18, active: true },
    { id: "p3", code: "TB20", type: "percent", value: 20, minSubtotal: 200, used: 7, active: true },
  ],
  zones: [
    { id: "z1", name: "Riyadh — North", fee: 15, etaMinutes: 60, active: true },
    { id: "z2", name: "Riyadh — Central", fee: 15, etaMinutes: 45, active: true },
    { id: "z3", name: "Riyadh — East", fee: 20, etaMinutes: 75, active: true },
    { id: "z4", name: "Riyadh — West", fee: 20, etaMinutes: 75, active: true },
    { id: "z5", name: "Riyadh — South", fee: 20, etaMinutes: 80, active: true },
  ],
  slots: [
    { id: "sl1", label: "8:00 AM – 10:00 AM", from: "08:00", to: "10:00", capacity: 20, active: true },
    { id: "sl2", label: "10:00 AM – 12:00 PM", from: "10:00", to: "12:00", capacity: 25, active: true },
    { id: "sl3", label: "12:00 PM – 2:00 PM", from: "12:00", to: "14:00", capacity: 25, active: true },
    { id: "sl4", label: "2:00 PM – 4:00 PM", from: "14:00", to: "16:00", capacity: 25, active: true },
    { id: "sl5", label: "4:00 PM – 6:00 PM", from: "16:00", to: "18:00", capacity: 25, active: true },
    { id: "sl6", label: "6:00 PM – 8:00 PM", from: "18:00", to: "20:00", capacity: 20, active: true },
  ],
  banners: [
    { id: "b1", title: "Fresh Cupcakes Daily", subtitle: "Handcrafted in Riyadh", ctaLabel: "Shop now", ctaLink: "/cupcakes", position: "hero", active: true, order: 1 },
    { id: "b2", title: "Corporate Gifting", subtitle: "Bulk orders with 15% off", ctaLabel: "Learn more", ctaLink: "/corporate", position: "midpage", active: true, order: 2 },
  ],
  categories: [
    { id: "c1", label: "Cupcakes", slug: "cupcakes", visible: true, order: 1 },
    { id: "c2", label: "Cakes", slug: "cakes", visible: true, order: 2 },
    { id: "c3", label: "Chocolates", slug: "chocolates", visible: true, order: 3 },
    { id: "c4", label: "Donuts", slug: "donuts", visible: true, order: 4 },
    { id: "c5", label: "Gifts", slug: "gifts", visible: true, order: 5 },
    { id: "c6", label: "Extras", slug: "extras", visible: true, order: 6 },
  ],
  paymentMethods: [
    { id: "pm1", label: "Credit / Debit Card", active: true },
    { id: "pm2", label: "Apple Pay", active: true },
    { id: "pm3", label: "Mada", active: true },
    { id: "pm4", label: "STC Pay", active: true },
    { id: "pm5", label: "Cash on Delivery", active: false },
  ],
  loyalty: { enabled: true, pointsPerSar: 1, redeemRate: 20, signupBonus: 50, birthdayBonus: 100 },
  settings: {
    brandName: "Terrific Bites",
    supportEmail: "hello@terrificbites.sa",
    supportPhone: "+966 11 000 0000",
    currency: "SAR",
    taxRate: 5,
    defaultDeliveryFee: 15,
    freeDeliveryThreshold: 0,
    minOrder: 30,
    languages: [
      { code: "en", label: "English", enabled: true },
      { code: "ar", label: "العربية", enabled: true },
    ],
    defaultLanguage: "en",
    operatingHours: { open: "08:00", close: "22:00" },
    socials: { instagram: "@terrificbites", twitter: "@terrificbites" },
    maintenanceMode: false,
    guestCheckout: false,
  },
  productOverrides: {},
  homepageSections: [
    { id: "hero", label: "Hero banner", visible: true, order: 1 },
    { id: "categories", label: "Category circles", visible: true, order: 2 },
    { id: "featured", label: "Featured cupcakes", visible: true, order: 3 },
    { id: "divine", label: "Divine treats carousel", visible: true, order: 4 },
    { id: "gifts", label: "Gift boxes", visible: true, order: 5 },
    { id: "chocolates", label: "Chocolates grid", visible: true, order: 6 },
    { id: "extras", label: "Add extras", visible: true, order: 7 },
    { id: "testimonials", label: "Testimonials", visible: true, order: 8 },
  ],
  notifications: [
    { id: "n1", title: "New order", body: "Order #TB-1042 placed", at: Date.now() - 1000 * 60 * 5, read: false },
    { id: "n2", title: "Low stock", body: "Buttercream Cake (9 IN) below 5 units", at: Date.now() - 1000 * 60 * 45, read: false },
    { id: "n3", title: "New review", body: "5★ review on Chocolate Truffle", at: Date.now() - 1000 * 60 * 120, read: true },
  ],
  adminSession: null,
  theme: DEFAULT_ADMIN_THEME,
};

function load(): AdminState {
  if (!isBrowser) return initial;
  try {
    const raw = localStorage.getItem(KEY);
    if (!raw) return initial;
    const parsed = JSON.parse(raw);
    return { ...initial, ...parsed, settings: { ...initial.settings, ...(parsed.settings ?? {}) }, loyalty: { ...initial.loyalty, ...(parsed.loyalty ?? {}) } };
  } catch {
    return initial;
  }
}

let state: AdminState = load();
const listeners = new Set<() => void>();
function persist() {
  if (!isBrowser) return;
  try { localStorage.setItem(KEY, JSON.stringify(state)); } catch {}
}
function emit() { persist(); listeners.forEach((l) => l()); }
function subscribe(fn: () => void) { listeners.add(fn); return () => listeners.delete(fn); }

export function useAdmin<T>(selector: (s: AdminState) => T): T {
  const snap = useSyncExternalStore(subscribe, () => state, () => initial);
  return selector(snap);
}

export function getAdminState(): AdminState { return state; }

function update(patch: Partial<AdminState>) { state = { ...state, ...patch }; emit(); }

const rid = () => Math.random().toString(36).slice(2, 10);

// ---------- Auth (mock) ----------
export const adminAuth = {
  signIn(email: string, password: string): { ok: boolean; error?: string } {
    // Mock: any staff email + password "admin123" works, or "owner@…" always.
    const staff = state.staff.find((s) => s.email.toLowerCase() === email.toLowerCase() && s.active);
    if (!staff) return { ok: false, error: "No active staff account with that email." };
    if (password !== "admin123") return { ok: false, error: "Invalid password. (Demo: admin123)" };
    update({ adminSession: { email: staff.email, role: staff.role } });
    return { ok: true };
  },
  signOut() { update({ adminSession: null }); },
};

// ---------- CRUD helpers ----------
export const staffStore = {
  add(m: Omit<StaffMember, "id" | "createdAt">) { update({ staff: [{ ...m, id: rid(), createdAt: Date.now() }, ...state.staff] }); },
  update(id: string, patch: Partial<StaffMember>) { update({ staff: state.staff.map((s) => (s.id === id ? { ...s, ...patch } : s)) }); },
  remove(id: string) { update({ staff: state.staff.filter((s) => s.id !== id) }); },
};

export const promoStore = {
  add(p: Omit<PromoCode, "id" | "used">) { update({ promos: [{ ...p, id: rid(), used: 0 }, ...state.promos] }); },
  update(id: string, patch: Partial<PromoCode>) { update({ promos: state.promos.map((p) => (p.id === id ? { ...p, ...patch } : p)) }); },
  remove(id: string) { update({ promos: state.promos.filter((p) => p.id !== id) }); },
};

export const zoneStore = {
  add(z: Omit<DeliveryZone, "id">) { update({ zones: [...state.zones, { ...z, id: rid() }] }); },
  update(id: string, patch: Partial<DeliveryZone>) { update({ zones: state.zones.map((z) => (z.id === id ? { ...z, ...patch } : z)) }); },
  remove(id: string) { update({ zones: state.zones.filter((z) => z.id !== id) }); },
};

export const slotStore = {
  add(s: Omit<DeliverySlot, "id">) { update({ slots: [...state.slots, { ...s, id: rid() }] }); },
  update(id: string, patch: Partial<DeliverySlot>) { update({ slots: state.slots.map((s) => (s.id === id ? { ...s, ...patch } : s)) }); },
  remove(id: string) { update({ slots: state.slots.filter((s) => s.id !== id) }); },
};

export const bannerStore = {
  add(b: Omit<Banner, "id">) { update({ banners: [...state.banners, { ...b, id: rid() }] }); },
  update(id: string, patch: Partial<Banner>) { update({ banners: state.banners.map((b) => (b.id === id ? { ...b, ...patch } : b)) }); },
  remove(id: string) { update({ banners: state.banners.filter((b) => b.id !== id) }); },
};

export const categoryStore = {
  add(c: Omit<CategoryConfig, "id">) { update({ categories: [...state.categories, { ...c, id: rid() }] }); },
  update(id: string, patch: Partial<CategoryConfig>) { update({ categories: state.categories.map((c) => (c.id === id ? { ...c, ...patch } : c)) }); },
  remove(id: string) { update({ categories: state.categories.filter((c) => c.id !== id) }); },
};

export const paymentStore = {
  add(p: Omit<PaymentMethod, "id">) { update({ paymentMethods: [...state.paymentMethods, { ...p, id: rid() }] }); },
  update(id: string, patch: Partial<PaymentMethod>) { update({ paymentMethods: state.paymentMethods.map((p) => (p.id === id ? { ...p, ...patch } : p)) }); },
  remove(id: string) { update({ paymentMethods: state.paymentMethods.filter((p) => p.id !== id) }); },
};

export const loyaltyConfig = {
  update(patch: Partial<LoyaltyConfig>) { update({ loyalty: { ...state.loyalty, ...patch } }); },
};

export const settingsStore = {
  update(patch: Partial<SiteSettings>) { update({ settings: { ...state.settings, ...patch } }); },
};

export const productOverrideStore = {
  set(id: string, patch: Partial<ProductOverride>) {
    const current: ProductOverride = state.productOverrides[id] ?? { id, visible: true, featured: false };
    update({ productOverrides: { ...state.productOverrides, [id]: { ...current, ...patch } } });
  },
};

export const homepageStore = {
  update(id: string, patch: Partial<HomepageSection>) { update({ homepageSections: state.homepageSections.map((s) => (s.id === id ? { ...s, ...patch } : s)) }); },
  reorder(ids: string[]) {
    const map = new Map(ids.map((id, i) => [id, i + 1]));
    update({ homepageSections: state.homepageSections.map((s) => ({ ...s, order: map.get(s.id) ?? s.order })).sort((a, b) => a.order - b.order) });
  },
};

export const notificationStore = {
  markRead(id: string) { update({ notifications: state.notifications.map((n) => (n.id === id ? { ...n, read: true } : n)) }); },
  markAllRead() { update({ notifications: state.notifications.map((n) => ({ ...n, read: true })) }); },
  clear() { update({ notifications: [] }); },
};
