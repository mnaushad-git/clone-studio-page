/**
 * Typed client for the read-only catalogue API (/api/v1/catalogue/*).
 *
 * This is the one place that knows the backend's wire shape (snake_case Pydantic
 * models) and translates it into the Storefront's existing `Product` shape
 * (src/lib/products.ts) — per docs/architecture/api-standards.md §3, the frontend
 * client layer is where that casing/shape translation belongs, not every call site.
 */
import { useQuery, type UseQueryResult } from "@tanstack/react-query";
import type { Category, Occasion, Product, Recipient } from "@/lib/products";
import { registerProducts, variantComboKey } from "@/lib/products";

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL as string | undefined) ?? "http://localhost:8000";

export class CatalogueApiError extends Error {
  status?: number;
  constructor(message: string, status?: number) {
    super(message);
    this.name = "CatalogueApiError";
    this.status = status;
  }
}

// -- wire types (exactly the backend's Pydantic response shapes) --------------------

export type CategoryOut = {
  id: string;
  external_key: string;
  code: string;
  slug: string;
  name_en: string;
  name_ar: string | null;
  description_en: string | null;
  description_ar: string | null;
  display_order: number;
};

export type MomentOut = {
  id: string;
  external_key: string;
  slug: string;
  name_en: string;
  name_ar: string | null;
  description_en: string | null;
  description_ar: string | null;
  display_order: number;
};

export type RecipientOut = MomentOut;

export type ImageOut = {
  url: string;
  role: string;
  alt_text_en: string | null;
  alt_text_ar: string | null;
  display_order: number;
};

export type VariantAttributeOut = {
  code: string;
  name_en: string;
  value_label_en: string;
};

export type VariantOut = {
  id: string;
  external_key: string;
  sku: string;
  name_en: string;
  is_default: boolean;
  attributes: VariantAttributeOut[];
  price: string | null;
  currency: string | null;
};

export type MerchandisingOut = {
  featured: boolean;
  is_new: boolean;
  is_bestseller: boolean | null;
  badge_en: string | null;
  badge_ar: string | null;
};

export type ProductSummaryOut = {
  id: string;
  external_key: string;
  sku: string;
  slug: string;
  name_en: string;
  name_ar: string | null;
  short_description_en: string | null;
  category: CategoryOut;
  price: string;
  currency: string;
  price_includes_tax: boolean | null;
  primary_image: ImageOut | null;
  merchandising: MerchandisingOut;
  moments: MomentOut[];
  recipients: RecipientOut[];
  availability_status: string;
};

export type ProductDetailOut = Omit<ProductSummaryOut, "short_description_en"> & {
  description_en: string | null;
  description_ar: string | null;
  gallery_images: ImageOut[];
  variants: VariantOut[];
  moments: MomentOut[];
  recipients: RecipientOut[];
};

export type PaginatedProductsOut = {
  items: ProductSummaryOut[];
  total: number;
  limit: number;
  offset: number;
};

export type HomepageOut = {
  hero: ProductSummaryOut[];
  gifts: ProductSummaryOut[];
  divine: ProductSummaryOut[];
  chocolates: ProductSummaryOut[];
  extras: ProductSummaryOut[];
  new: ProductSummaryOut[];
};

export type ProductFilters = {
  category?: string;
  moment?: string;
  recipient?: string;
  featured?: boolean;
  bestseller?: boolean;
  new?: boolean;
  search?: string;
  limit?: number;
  offset?: number;
};

// -- image resolution -----------------------------------------------------------------

// Every existing product image is still a bundled repo asset (media hasn't migrated to
// object storage yet — storage_url stays null server-side), so the API returns the
// repo-relative original_path; this glob resolves it back to the Vite-hashed asset URL
// by filename. Falls back to the raw path (or a real absolute URL, once storage_url is
// populated) if no matching bundled asset is found.
const bundledAssets = import.meta.glob<string>("/src/assets/*.{jpg,jpeg,png,webp}", {
  eager: true,
  import: "default",
});
const assetsByBasename: Record<string, string> = {};
for (const [path, url] of Object.entries(bundledAssets)) {
  const basename = path.split("/").pop();
  if (basename) assetsByBasename[basename] = url;
}

export function resolveImageUrl(pathOrUrl: string | undefined | null): string {
  if (!pathOrUrl) return "";
  if (/^https?:\/\//i.test(pathOrUrl)) return pathOrUrl;
  const basename = pathOrUrl.split("/").pop() ?? pathOrUrl;
  return assetsByBasename[basename] ?? pathOrUrl;
}

// -- fetch layer ------------------------------------------------------------------------

async function apiFetch<T>(path: string, params?: Record<string, string | number | boolean | undefined>): Promise<T> {
  const url = new URL(`${API_BASE_URL}/api/v1/catalogue${path}`);
  if (params) {
    for (const [key, value] of Object.entries(params)) {
      if (value !== undefined && value !== null && value !== "") {
        url.searchParams.set(key, String(value));
      }
    }
  }

  let response: Response;
  try {
    response = await fetch(url.toString());
  } catch {
    throw new CatalogueApiError("Could not reach the catalogue service. Check your connection and try again.");
  }

  if (!response.ok) {
    if (response.status === 404) {
      throw new CatalogueApiError("Not found", 404);
    }
    throw new CatalogueApiError(`Catalogue request failed (${response.status}).`, response.status);
  }

  return (await response.json()) as T;
}

export function fetchCategories(): Promise<CategoryOut[]> {
  return apiFetch<CategoryOut[]>("/categories");
}

export function fetchMoments(): Promise<MomentOut[]> {
  return apiFetch<MomentOut[]>("/moments");
}

export function fetchRecipients(): Promise<RecipientOut[]> {
  return apiFetch<RecipientOut[]>("/recipients");
}

export async function fetchProducts(filters: ProductFilters = {}): Promise<PaginatedProductsOut> {
  const page = await apiFetch<PaginatedProductsOut>("/products", filters);
  registerProducts(page.items.map(mapSummaryToProduct));
  return page;
}

export async function fetchProductDetail(slug: string): Promise<ProductDetailOut> {
  const detail = await apiFetch<ProductDetailOut>(`/products/${encodeURIComponent(slug)}`);
  registerProducts([mapDetailToProduct(detail)]);
  return detail;
}

export async function fetchHomepage(): Promise<HomepageOut> {
  const homepage = await apiFetch<HomepageOut>("/homepage");
  registerProducts(
    [...homepage.hero, ...homepage.gifts, ...homepage.divine, ...homepage.chocolates, ...homepage.extras, ...homepage.new].map(
      mapSummaryToProduct,
    ),
  );
  return homepage;
}

// -- React Query hooks --------------------------------------------------------------

export function useCatalogueCategories(): UseQueryResult<CategoryOut[], CatalogueApiError> {
  return useQuery({ queryKey: ["catalogue", "categories"], queryFn: fetchCategories });
}

export function useCatalogueMoments(): UseQueryResult<MomentOut[], CatalogueApiError> {
  return useQuery({ queryKey: ["catalogue", "moments"], queryFn: fetchMoments });
}

export function useCatalogueRecipients(): UseQueryResult<RecipientOut[], CatalogueApiError> {
  return useQuery({ queryKey: ["catalogue", "recipients"], queryFn: fetchRecipients });
}

export function useCatalogueProducts(filters: ProductFilters = {}): UseQueryResult<PaginatedProductsOut, CatalogueApiError> {
  return useQuery({
    queryKey: ["catalogue", "products", filters],
    queryFn: () => fetchProducts(filters),
  });
}

export function useCatalogueProductDetail(slug: string | undefined): UseQueryResult<ProductDetailOut, CatalogueApiError> {
  return useQuery({
    queryKey: ["catalogue", "product", slug],
    queryFn: () => fetchProductDetail(slug as string),
    enabled: Boolean(slug),
  });
}

export function useCatalogueHomepage(): UseQueryResult<HomepageOut, CatalogueApiError> {
  return useQuery({ queryKey: ["catalogue", "homepage"], queryFn: fetchHomepage });
}

// -- mapping: backend DTOs -> the Storefront's existing Product shape ---------------

export function mapSummaryToProduct(summary: ProductSummaryOut): Product {
  return {
    id: summary.slug,
    name: summary.name_en,
    price: Number(summary.price),
    image: resolveImageUrl(summary.primary_image?.url),
    category: summary.category.slug as Category,
    description: summary.short_description_en ?? undefined,
    isNew: summary.merchandising.is_new,
    occasions: summary.moments.map((m) => m.name_en as Occasion),
    recipients: summary.recipients.map((r) => r.name_en as Recipient),
  };
}

export function mapDetailToProduct(detail: ProductDetailOut): Product {
  const base: Product = {
    id: detail.slug,
    name: detail.name_en,
    price: Number(detail.price),
    image: resolveImageUrl(detail.primary_image?.url),
    category: detail.category.slug as Category,
    description: detail.description_en ?? undefined,
    isNew: detail.merchandising.is_new,
    occasions: detail.moments.map((m) => m.name_en as Occasion),
    recipients: detail.recipients.map((r) => r.name_en as Recipient),
  };

  const gallery = detail.gallery_images.map((img) => resolveImageUrl(img.url));
  if (gallery.length > 0) {
    base.thumbs = [base.image, ...gallery];
  }

  if (detail.variants.length > 1) {
    // One axis group per distinct attribute code across every variant, values in
    // first-seen order — generalizes what used to be two separate size/flavor dedupe
    // loops into one, for any number of ops-defined axes.
    const axesByCode = new Map<string, { code: string; name: string; values: string[] }>();
    const priceByKey: Record<string, number> = {};

    for (const v of detail.variants) {
      const selected: Record<string, string> = {};
      for (const attr of v.attributes) {
        selected[attr.code] = attr.value_label_en;
        let axis = axesByCode.get(attr.code);
        if (!axis) {
          axis = { code: attr.code, name: attr.name_en, values: [] };
          axesByCode.set(attr.code, axis);
        }
        if (!axis.values.includes(attr.value_label_en)) axis.values.push(attr.value_label_en);
      }
      if (Object.keys(selected).length > 0 && v.price != null) {
        priceByKey[variantComboKey(selected)] = Number(v.price);
      }
    }

    if (axesByCode.size > 0) {
      base.variantAxes = [...axesByCode.values()];
      base.variantPriceByKey = priceByKey;
    }
  }

  return base;
}
