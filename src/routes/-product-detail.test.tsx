import { act } from "react";
import { renderToString } from "react-dom/server";
import { hydrateRoot, type Root } from "react-dom/client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const loader = vi.hoisted(() => ({ current: null as unknown }));

vi.mock("@tanstack/react-router", () => ({
  createFileRoute: () => (opts: Record<string, unknown>) => ({ ...opts, useLoaderData: () => loader.current }),
  Link: ({ children, className }: { children: React.ReactNode; className?: string }) => <a className={className}>{children}</a>,
  useNavigate: () => vi.fn(),
  notFound: () => new Error("not found"),
}));
vi.mock("@/components/SiteHeader", () => ({ SiteHeader: () => null }));
vi.mock("@/components/SiteFooter", () => ({ SiteFooter: () => null }));
vi.mock("@/components/ProductReviews", () => ({ ProductReviews: () => null }));
vi.mock("@/components/ProductCard", () => ({
  ProductCard: ({ product }: { product: { name: string } }) => <div data-testid="related-card">{product.name}</div>,
}));

import { Route } from "./product.$id";
import { mapDetailToProduct, type ProductDetailOut, type VariantOut } from "@/lib/catalogue-api";
import { products, registerProducts, type Product } from "@/lib/products";
import { cart } from "@/lib/store";
import { setLang } from "@/lib/i18n";

const cupcakes = {
  id: "cat-cupcakes",
  external_key: "terrific_bites.category.cupcakes",
  code: "CUP",
  slug: "cupcakes",
  name_en: "Cupcakes",
  name_ar: null,
  description_en: null,
  description_ar: null,
  display_order: 1,
};

function image(url: string) {
  return { url, role: "PRIMARY", alt_text_en: null, alt_text_ar: null, display_order: 0 };
}

function detail(slug: string, name: string, price: string, variants: VariantOut[]): ProductDetailOut {
  return {
    id: slug,
    external_key: `x.${slug}`,
    sku: variants[0].sku,
    slug,
    name_en: name,
    name_ar: null,
    description_en: `${name} description.`,
    description_ar: null,
    category: cupcakes,
    price,
    currency: "SAR",
    price_includes_tax: true,
    primary_image: image(`https://api.example/media/${slug}.jpg`),
    gallery_images: [],
    merchandising: { featured: false, is_new: false, is_bestseller: null, badge_en: null, badge_ar: null },
    moments: [],
    recipients: [],
    availability_status: "UNKNOWN",
    variants,
  } as ProductDetailOut;
}

function variant(sku: string, price: string, isDefault: boolean, size?: string): VariantOut {
  return {
    id: sku,
    external_key: `x.${sku}`,
    sku,
    name_en: sku,
    is_default: isDefault,
    attributes: size ? [{ code: "size", name_en: "Size", value_label_en: size }] : [],
    price,
    currency: "SAR",
  };
}

// The Odoo-created staging product: a single variant, no attributes, no gallery.
const ROYAL = mapDetailToProduct(
  detail("royal-chocolate-cupcake", "Royal Chocolate Cupcake", "19.00", [variant("TB-DEMO-001", "19.00", true)]),
);
// An existing product with two real size variants.
const SWISS = mapDetailToProduct(
  detail("swiss-frosting", "Swiss Frosting", "40.00", [
    variant("TB-CUP-SWISS-6", "40.00", true, "Pack of 6"),
    variant("TB-CUP-SWISS-12", "75.00", false, "Pack of 12"),
  ]),
);
// Another cupcake returned for "related products"; its image must never show in the gallery.
const OTHER: Product = { ...SWISS, id: "light-sponge", name: "Light Sponge", image: "https://api.example/media/light-sponge.jpg" };

function summaryPage() {
  const s = (p: Product) => ({
    id: p.id, external_key: p.id, sku: p.id, slug: p.id, name_en: p.name, name_ar: null, short_description_en: null,
    category: cupcakes, price: String(p.price), currency: "SAR", price_includes_tax: true, primary_image: image(p.image),
    merchandising: { featured: false, is_new: false, is_bestseller: null, badge_en: null, badge_ar: null },
    moments: [], recipients: [], availability_status: "UNKNOWN",
  });
  const items = [s(ROYAL), s(SWISS), s(OTHER)];
  return new Response(JSON.stringify({ items, total: items.length, limit: 8, offset: 0 }), {
    status: 200,
    headers: { "Content-Type": "application/json" },
  });
}

function ProductApp({ client }: { client: QueryClient }) {
  const Page = (Route as unknown as { component: React.ComponentType }).component;
  return (
    <QueryClientProvider client={client}>
      <Page />
    </QueryClientProvider>
  );
}

function cartLines() {
  return JSON.parse(localStorage.getItem("tb.state.v1") ?? "{}").cart ?? [];
}

describe("product detail page options and images", () => {
  let root: Root | undefined;
  let container: HTMLDivElement;
  let recoverableErrors: unknown[];

  async function openProduct(product: Product) {
    loader.current = { product };
    container.innerHTML = renderToString(<ProductApp client={new QueryClient()} />);
    await act(async () => {
      root = hydrateRoot(container, <ProductApp client={new QueryClient()} />, {
        onRecoverableError: (error) => recoverableErrors.push(error),
      });
    });
    await waitFor(() => expect(screen.getAllByTestId("related-card").length).toBeGreaterThan(0));
  }

  const galleryImages = () => [...container.querySelectorAll("section img")].map((i) => i.getAttribute("src"));

  beforeEach(() => {
    recoverableErrors = [];
    registerProducts([ROYAL, SWISS, OTHER]);
    cart.clear();
    vi.stubGlobal("fetch", vi.fn(async () => summaryPage()));
    container = document.createElement("div");
    document.body.appendChild(container);
  });

  afterEach(() => {
    act(() => root?.unmount());
    root = undefined;
    container.remove();
    products.length = 0;
    act(() => setLang("en"));
    vi.unstubAllGlobals();
  });

  it("shows no invented options for a product without variants, and buys its real variant", async () => {
    await openProduct(ROYAL);
    expect(recoverableErrors).toEqual([]);

    expect(screen.getByRole("heading", { name: "Royal Chocolate Cupcake" })).toBeInTheDocument();
    expect(screen.getByText("SAR 19.00")).toBeInTheDocument();
    expect(screen.getByTestId("product-sku")).toHaveTextContent("SKU: TB-DEMO-001");
    for (const fake of [/Pack of 6/i, /Pack of 12/i, /^Vanilla$/i, /^Chocolate$/i]) {
      expect(screen.queryByRole("button", { name: fake })).not.toBeInTheDocument();
    }
    // Only its own image: no thumbnail strip, and no other product's photo.
    expect(galleryImages()).toEqual(["https://api.example/media/royal-chocolate-cupcake.jpg"]);

    fireEvent.click(screen.getByRole("button", { name: "Add To Cart" }));
    expect(cartLines()).toEqual([
      expect.objectContaining({ productId: "royal-chocolate-cupcake", qty: 1, unitPrice: 19 }),
    ]);
    expect(cartLines()[0].attributes).toBeUndefined();
  });

  it("keeps real variant selectors and switches SKU and price with the selection", async () => {
    await openProduct(SWISS);
    expect(recoverableErrors).toEqual([]);

    expect(screen.getByText("SAR 40.00")).toBeInTheDocument();
    expect(screen.getByTestId("product-sku")).toHaveTextContent("TB-CUP-SWISS-6");
    expect(galleryImages()).toEqual(["https://api.example/media/swiss-frosting.jpg"]);

    fireEvent.click(screen.getByRole("button", { name: /Pack of 12/ }));
    expect(screen.getByText("SAR 75.00")).toBeInTheDocument();
    expect(screen.getByTestId("product-sku")).toHaveTextContent("TB-CUP-SWISS-12");

    fireEvent.click(screen.getByRole("button", { name: "Add To Cart" }));
    expect(cartLines()).toEqual([
      expect.objectContaining({ productId: "swiss-frosting", unitPrice: 75, attributes: { size: "Pack of 12" } }),
    ]);
  });

  it("renders the same way in Arabic", async () => {
    act(() => setLang("ar"));
    await openProduct(ROYAL);
    expect(screen.getByTestId("product-sku")).toHaveTextContent("رمز المنتج: TB-DEMO-001");
    expect(screen.getByRole("button", { name: "أضف إلى السلة" })).toBeEnabled();
    expect(galleryImages()).toHaveLength(1);
  });
});
