/**
 * Catalogue vocabulary and a runtime product cache.
 *
 * Product data itself no longer lives here as static literals — it's fetched from the
 * catalogue API (src/lib/catalogue-api.ts) and registered into the cache below as it
 * arrives, so `getProduct`/`products`/`featured` keep working synchronously for call
 * sites (cart, checkout, wishlist, admin) that aren't wired to the API directly in
 * this phase. Category/occasion/recipient vocabulary stays static: it's a stable,
 * already-approved taxonomy (matches data/catalogue/{categories,moments,recipients}.json
 * 1:1), not mock product data.
 */

export type Category = "cupcakes" | "cakes" | "chocolates" | "donuts" | "gifts" | "extras";

export const OCCASIONS = [
  "Birthday",
  "Anniversary",
  "Wedding",
  "Graduation",
  "Congratulations",
  "Thank You",
] as const;
export type Occasion = (typeof OCCASIONS)[number];

export const RECIPIENTS = ["For Him", "For Her", "For Kids", "For Family"] as const;
export type Recipient = (typeof RECIPIENTS)[number];

export type Product = {
  id: string;
  name: string;
  price: number;
  image: string;
  thumbs?: string[];
  category: Category;
  tags?: string[];
  // One entry per variant attribute axis this product's variants carry (any number —
  // not just the legacy "size"/"flavor" pair), each axis's distinct values in
  // first-seen order across the product's variants.
  variantAxes?: { code: string; name: string; values: string[] }[];
  // Exact price for one specific combination of selected values, keyed by
  // variantComboKey() — replaces the old size-delta-additive approximation, which
  // stops being a safe assumption once a product can have more than one
  // price-bearing axis.
  variantPriceByKey?: Record<string, number>;
  description?: string;
  isNew?: boolean;
  occasions?: Occasion[];
  recipients?: Recipient[];
};

/** Deterministic combination key for `Product.variantPriceByKey` — sorted by axis
 * code so selection order never affects the lookup. */
export function variantComboKey(selected: Record<string, string>): string {
  return Object.entries(selected)
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([code, value]) => `${code}=${value}`)
    .join("|");
}

const productCache = new Map<string, Product>();

/** Every product fetched so far this session — mutated in place (never reassigned)
 * so existing `products.filter(...)`/`products.find(...)` call sites keep working
 * unchanged as the cache grows.
 */
export const products: Product[] = [];

/** Populated by catalogue-api.ts fetch functions as API responses arrive. */
export function registerProducts(items: Product[]): void {
  for (const item of items) {
    const existingIndex = products.findIndex((p) => p.id === item.id);
    if (existingIndex >= 0) products[existingIndex] = item;
    else products.push(item);
    productCache.set(item.id, item);
  }
}

export function getProduct(id: string): Product | undefined {
  return productCache.get(id);
}

/** Same slices as the old static `featured` object, now computed live off whatever's
 * in the cache — kept only for the customize (gift builder) page, which isn't wired
 * to the catalogue API directly in this phase. The homepage itself uses
 * useCatalogueHomepage() instead (see src/routes/index.tsx).
 */
export const featured = {
  get extras() {
    return products.filter((p) => p.category === "extras");
  },
};

export const CATEGORY_LABEL: Record<Category, string> = {
  cupcakes: "Cupcakes",
  cakes: "Cakes",
  chocolates: "Chocolates",
  donuts: "Donuts",
  gifts: "Gifts",
  extras: "Extras",
};

export function slugToOccasion(slug: string): Occasion | undefined {
  return OCCASIONS.find((o) => o.toLowerCase().replace(/\s+/g, "-") === slug.toLowerCase());
}
export function slugToRecipient(slug: string): Recipient | undefined {
  return RECIPIENTS.find((r) => r.toLowerCase().replace(/\s+/g, "-") === slug.toLowerCase());
}
export function occasionToSlug(o: Occasion) {
  return o.toLowerCase().replace(/\s+/g, "-");
}
export function recipientToSlug(r: Recipient) {
  return r.toLowerCase().replace(/\s+/g, "-");
}
