import { act } from "react";
import { renderToString } from "react-dom/server";
import { hydrateRoot, type Root } from "react-dom/client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("@tanstack/react-router", () => ({
  createFileRoute: () => (opts: { component: React.ComponentType }) => opts,
  Link: ({ children, className }: { children: React.ReactNode; className?: string }) => (
    <a className={className}>{children}</a>
  ),
  useNavigate: () => vi.fn(),
}));
vi.mock("@/components/SiteHeader", () => ({ SiteHeader: () => null }));
vi.mock("@/components/SiteFooter", () => ({ SiteFooter: () => null }));

import { Route } from "./customize";
import { mapSummaryToProduct, type ProductSummaryOut } from "@/lib/catalogue-api";
import { products, registerProducts } from "@/lib/products";

const extrasCategory = {
  id: "cat-extras",
  external_key: "terrific_bites.category.extras",
  code: "EXT",
  slug: "extras",
  name_en: "Extras",
  name_ar: null,
  description_en: null,
  description_ar: null,
  display_order: 6,
};

function extra(slug: string, name: string, price: string): ProductSummaryOut {
  return {
    id: slug,
    external_key: `terrific_bites.product.${slug}`,
    sku: slug.toUpperCase(),
    slug,
    name_en: name,
    name_ar: null,
    short_description_en: null,
    category: extrasCategory,
    price,
    currency: "SAR",
    price_includes_tax: true,
    primary_image: null,
    merchandising: { featured: false, is_new: false, is_bestseller: null, badge_en: null, badge_ar: null },
    moments: [],
    recipients: [],
    availability_status: "UNKNOWN",
  } as ProductSummaryOut;
}

const EXTRAS = [
  extra("extra-donut", "Extra Donut", "4.89"),
  extra("extra-icecream", "Extra Ice Cream", "5.49"),
  extra("extra-cheesecake", "Extra Cheesecake", "6.29"),
  extra("extra-donuts-pair", "Extra Donuts Pair", "7.89"),
];

const requestedUrls: string[] = [];

function page(items: ProductSummaryOut[]) {
  return new Response(JSON.stringify({ items, total: items.length, limit: 100, offset: 0 }), {
    status: 200,
    headers: { "Content-Type": "application/json" },
  });
}

function CustomizeApp({ client }: { client: QueryClient }) {
  const CustomizePage = (Route as unknown as { component: React.ComponentType }).component;
  return (
    <QueryClientProvider client={client}>
      <CustomizePage />
    </QueryClientProvider>
  );
}

describe("/customize extras", () => {
  let root: Root | undefined;
  let container: HTMLDivElement;

  beforeEach(() => {
    requestedUrls.length = 0;
    products.length = 0;
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: string) => {
        requestedUrls.push(input);
        const url = new URL(input);
        return page(url.searchParams.get("category") === "extras" ? EXTRAS : []);
      }),
    );
    container = document.createElement("div");
    document.body.appendChild(container);
  });

  afterEach(() => {
    act(() => root?.unmount());
    root = undefined;
    container.remove();
    products.length = 0;
    vi.unstubAllGlobals();
  });

  it("hydrates without a mismatch and loads the extras on a direct page load", async () => {
    // The SSR server's in-memory product cache outlives a request: other pages it has
    // rendered leave the extras in it. A browser opening /customize directly starts with
    // an empty cache. Rendering from that cache made the two disagree (React #418).
    registerProducts(EXTRAS.map(mapSummaryToProduct));
    container.innerHTML = renderToString(<CustomizeApp client={new QueryClient()} />);
    products.length = 0;

    const recoverableErrors: unknown[] = [];
    await act(async () => {
      root = hydrateRoot(container, <CustomizeApp client={new QueryClient()} />, {
        onRecoverableError: (error) => recoverableErrors.push(error),
      });
    });

    await waitFor(() => expect(screen.getAllByText("Extra Donut").length).toBeGreaterThan(0));
    expect(recoverableErrors).toEqual([]);
    expect(screen.getByText("Extra Ice Cream")).toBeInTheDocument();
    expect(screen.getByText("Extra Cheesecake")).toBeInTheDocument();
    expect(screen.getByText("SAR 4.89")).toBeInTheDocument();
    // The upsell row shows the first three; the fourth only appears in "View all".
    expect(screen.queryByText("Extra Donuts Pair")).not.toBeInTheDocument();

    const extrasRequest = requestedUrls.map((u) => new URL(u)).find((u) => u.searchParams.get("category") === "extras");
    expect(extrasRequest?.pathname).toBe("/api/v1/catalogue/products");
  });
});
