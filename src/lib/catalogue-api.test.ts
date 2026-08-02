import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
  CatalogueApiError,
  fetchCategories,
  fetchProductDetail,
  fetchProducts,
  mapDetailToProduct,
  mapSummaryToProduct,
  resolveImageUrl,
  type ProductDetailOut,
  type ProductSummaryOut,
} from "@/lib/catalogue-api";
import { getProduct } from "@/lib/products";

const category = {
  id: "cat-1",
  external_key: "terrific_bites.category.cupcakes",
  code: "CUP",
  slug: "cupcakes",
  name_en: "Cupcakes",
  name_ar: null,
  description_en: null,
  description_ar: null,
  display_order: 1,
};

function makeSummary(overrides: Partial<ProductSummaryOut> = {}): ProductSummaryOut {
  return {
    id: "prod-1",
    external_key: "terrific_bites.product.swiss-frosting",
    sku: "TB-CUP-001",
    slug: "swiss-frosting",
    name_en: "Swiss Frosting",
    name_ar: null,
    short_description_en: null,
    category,
    price: "12.50",
    currency: "SAR",
    price_includes_tax: true,
    primary_image: { url: "src/assets/prod-swiss.jpg", role: "PRIMARY", alt_text_en: null, alt_text_ar: null, display_order: 0 },
    merchandising: { featured: false, is_new: true, is_bestseller: null, badge_en: null, badge_ar: null },
    moments: [{ id: "m1", external_key: "x", slug: "birthday", name_en: "Birthday", name_ar: null, description_en: null, description_ar: null, display_order: 1 }],
    recipients: [{ id: "r1", external_key: "x", slug: "for-her", name_en: "For Her", name_ar: null, description_en: null, description_ar: null, display_order: 1 }],
    availability_status: "UNKNOWN",
    ...overrides,
  };
}

function makeDetail(overrides: Partial<ProductDetailOut> = {}): ProductDetailOut {
  const summary = makeSummary();
  return {
    ...summary,
    description_en: "A cupcake.",
    description_ar: null,
    gallery_images: [],
    variants: [
      {
        id: "v1",
        external_key: "x.variant.default",
        sku: "TB-CUP-001",
        name_en: "Swiss Frosting",
        is_default: true,
        attributes: [],
        price: "12.50",
        currency: "SAR",
      },
    ],
    ...overrides,
  } as ProductDetailOut;
}

describe("resolveImageUrl", () => {
  it("returns an absolute URL unchanged", () => {
    expect(resolveImageUrl("https://cdn.example.com/a.jpg")).toBe("https://cdn.example.com/a.jpg");
  });

  it("falls back to the raw path when no bundled asset matches", () => {
    expect(resolveImageUrl("src/assets/does-not-exist.jpg")).toBe("src/assets/does-not-exist.jpg");
  });

  it("returns an empty string for a missing path", () => {
    expect(resolveImageUrl(null)).toBe("");
    expect(resolveImageUrl(undefined)).toBe("");
  });
});

describe("mapSummaryToProduct", () => {
  it("maps the backend summary shape onto the Storefront Product shape", () => {
    const product = mapSummaryToProduct(makeSummary());

    expect(product.id).toBe("swiss-frosting");
    expect(product.name).toBe("Swiss Frosting");
    expect(product.price).toBe(12.5);
    expect(product.category).toBe("cupcakes");
    expect(product.isNew).toBe(true);
    expect(product.occasions).toEqual(["Birthday"]);
    expect(product.recipients).toEqual(["For Her"]);
  });
});

describe("mapDetailToProduct", () => {
  it("includes variantAxes/variantPriceByKey only for genuine multi-variant products", () => {
    const single = mapDetailToProduct(makeDetail());
    expect(single.variantAxes).toBeUndefined();
    expect(single.variantPriceByKey).toBeUndefined();

    const multi = mapDetailToProduct(
      makeDetail({
        price: "300.00",
        variants: [
          {
            id: "v1",
            external_key: "x.variant.6in.vanilla",
            sku: "TB-CAK-001-6IN-VAN",
            name_en: "6 inch — Vanilla",
            is_default: true,
            attributes: [
              { code: "size", name_en: "Size", value_label_en: "6 INCH" },
              { code: "flavor", name_en: "Flavor", value_label_en: "Vanilla" },
            ],
            price: "300.00",
            currency: "SAR",
          },
          {
            id: "v2",
            external_key: "x.variant.6in.chocolate",
            sku: "TB-CAK-001-6IN-CHO",
            name_en: "6 inch — Chocolate",
            is_default: false,
            attributes: [
              { code: "size", name_en: "Size", value_label_en: "6 INCH" },
              { code: "flavor", name_en: "Flavor", value_label_en: "Chocolate" },
            ],
            price: "300.00",
            currency: "SAR",
          },
          {
            id: "v3",
            external_key: "x.variant.9in.vanilla",
            sku: "TB-CAK-001-9IN-VAN",
            name_en: "9 inch — Vanilla",
            is_default: false,
            attributes: [
              { code: "size", name_en: "Size", value_label_en: "9 INCH" },
              { code: "flavor", name_en: "Flavor", value_label_en: "Vanilla" },
            ],
            price: "380.00",
            currency: "SAR",
          },
          {
            id: "v4",
            external_key: "x.variant.9in.chocolate",
            sku: "TB-CAK-001-9IN-CHO",
            name_en: "9 inch — Chocolate",
            is_default: false,
            attributes: [
              { code: "size", name_en: "Size", value_label_en: "9 INCH" },
              { code: "flavor", name_en: "Flavor", value_label_en: "Chocolate" },
            ],
            price: "380.00",
            currency: "SAR",
          },
        ],
      }),
    );

    // Two variants share each size value (differing only by flavor) — the size axis
    // still dedupes to one entry per label, and flavor collects the distinct set
    // across all combinations. variantPriceByKey carries the exact price per
    // combination rather than an additive delta.
    expect(multi.variantAxes).toEqual([
      { code: "size", name: "Size", values: ["6 INCH", "9 INCH"] },
      { code: "flavor", name: "Flavor", values: ["Vanilla", "Chocolate"] },
    ]);
    expect(multi.variantPriceByKey).toEqual({
      "flavor=Vanilla|size=6 INCH": 300,
      "flavor=Chocolate|size=6 INCH": 300,
      "flavor=Vanilla|size=9 INCH": 380,
      "flavor=Chocolate|size=9 INCH": 380,
    });
  });

  it("builds thumbs from primary + gallery images", () => {
    const detail = makeDetail({
      gallery_images: [
        { url: "src/assets/cake-thumb-2.jpg", role: "GALLERY", alt_text_en: null, alt_text_ar: null, display_order: 1 },
      ],
    });
    const product = mapDetailToProduct(detail);
    expect(product.thumbs).toHaveLength(2);
  });
});

describe("fetch layer", () => {
  const originalFetch = global.fetch;

  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn());
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    global.fetch = originalFetch;
  });

  it("fetchCategories returns the parsed JSON on a 200 response", async () => {
    const payload = [category];
    vi.mocked(fetch).mockResolvedValueOnce(new Response(JSON.stringify(payload), { status: 200 }));

    const result = await fetchCategories();

    expect(result).toEqual(payload);
  });

  it("throws a CatalogueApiError with status 404 on a not-found response", async () => {
    vi.mocked(fetch).mockResolvedValueOnce(new Response("{}", { status: 404 }));

    await expect(fetchProductDetail("missing")).rejects.toMatchObject({
      name: "CatalogueApiError",
      status: 404,
    });
  });

  it("throws a CatalogueApiError when the network request itself fails", async () => {
    vi.mocked(fetch).mockRejectedValueOnce(new TypeError("network down"));

    await expect(fetchCategories()).rejects.toBeInstanceOf(CatalogueApiError);
  });

  it("throws a CatalogueApiError with the response status for other non-2xx responses", async () => {
    vi.mocked(fetch).mockResolvedValueOnce(new Response("{}", { status: 500 }));

    await expect(fetchCategories()).rejects.toMatchObject({ status: 500 });
  });

  it("registers fetched products into the shared cache so getProduct() finds them", async () => {
    const page = { items: [makeSummary({ slug: "cache-test-product" })], total: 1, limit: 20, offset: 0 };
    vi.mocked(fetch).mockResolvedValueOnce(new Response(JSON.stringify(page), { status: 200 }));

    await fetchProducts({});

    expect(getProduct("cache-test-product")).toBeDefined();
    expect(getProduct("cache-test-product")?.name).toBe("Swiss Frosting");
  });
});
