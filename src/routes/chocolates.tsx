import { createFileRoute, Link } from "@tanstack/react-router";
import { useMemo, useState } from "react";
import { ChevronDown, ChevronRight, Plus } from "lucide-react";
import { toast } from "sonner";
import { SiteHeader } from "@/components/SiteHeader";
import { SiteFooter } from "@/components/SiteFooter";
import { products, type Product } from "@/lib/products";
import { cart } from "@/lib/store";

export const Route = createFileRoute("/chocolates")({
  component: ChocolatesPage,
  head: () => ({
    meta: [
      { title: "Shop All Desserts — Terrific Bites" },
      { name: "description", content: "Browse our full collection of artisan chocolates, cupcakes, cakes and gift boxes." },
      { property: "og:title", content: "Shop — Terrific Bites" },
      { property: "og:description", content: "All our handmade desserts, chocolates and gift boxes in one place." },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary_large_image" },
    ],
  }),
});

const CATEGORIES: { key: Product["category"] | "all"; label: string }[] = [
  { key: "all", label: "All" },
  { key: "cupcakes", label: "Cupcakes" },
  { key: "cakes", label: "Cakes" },
  { key: "chocolates", label: "Chocolates" },
  { key: "donuts", label: "Donuts" },
  { key: "gifts", label: "Gifts" },
  { key: "extras", label: "Extras" },
];

const PRICE_BUCKETS = [
  { label: "Under $10", min: 0, max: 10 },
  { label: "$10 – $25", min: 10, max: 25 },
  { label: "$25 – $100", min: 25, max: 100 },
  { label: "$100+", min: 100, max: Infinity },
];

function ChocolatesPage() {
  const [category, setCategory] = useState<Product["category"] | "all">("all");
  const [prices, setPrices] = useState<number[]>([]);
  const [sort, setSort] = useState<"featured" | "low" | "high" | "name">("featured");

  const filtered = useMemo(() => {
    let list = category === "all" ? products : products.filter((p) => p.category === category);
    if (prices.length > 0) {
      list = list.filter((p) =>
        prices.some((i) => p.price >= PRICE_BUCKETS[i].min && p.price < PRICE_BUCKETS[i].max),
      );
    }
    if (sort === "low") list = [...list].sort((a, b) => a.price - b.price);
    else if (sort === "high") list = [...list].sort((a, b) => b.price - a.price);
    else if (sort === "name") list = [...list].sort((a, b) => a.name.localeCompare(b.name));
    return list;
  }, [category, prices, sort]);

  const toggle = <T,>(arr: T[], set: (v: T[]) => void, val: T) =>
    set(arr.includes(val) ? arr.filter((x) => x !== val) : [...arr, val]);

  return (
    <div className="min-h-screen bg-background text-foreground">
      <SiteHeader />

      <div className="max-w-7xl mx-auto px-6 pt-10 pb-6 text-center">
        <h1 className="font-display text-4xl md:text-5xl text-primary">
          {CATEGORIES.find((c) => c.key === category)?.label ?? "Shop"}
        </h1>
        <nav className="mt-3 flex items-center justify-center gap-2 text-xs text-muted-foreground">
          <Link to="/" className="hover:text-primary">Home</Link>
          <ChevronRight className="h-3 w-3" />
          <span className="text-primary">{CATEGORIES.find((c) => c.key === category)?.label}</span>
        </nav>
      </div>

      {/* Category chips */}
      <div className="max-w-7xl mx-auto px-6 pb-8">
        <div className="flex flex-wrap gap-3 justify-center">
          {CATEGORIES.map((c) => {
            const sample = c.key === "all" ? products[0] : products.find((p) => p.category === c.key);
            const active = category === c.key;
            return (
              <button
                key={c.key}
                onClick={() => setCategory(c.key)}
                className={`flex items-center gap-2 rounded-md border px-3 py-2 text-xs transition ${
                  active ? "bg-primary text-primary-foreground border-primary" : "bg-white border-border hover:border-primary"
                }`}
              >
                {sample && <img src={sample.image} alt={c.label} className="h-7 w-7 rounded object-cover" />}
                <span>{c.label}</span>
              </button>
            );
          })}
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-6 pb-16 grid grid-cols-1 md:grid-cols-[240px_1fr] gap-8">
        {/* Sidebar */}
        <aside className="border border-border rounded-md p-5 h-fit bg-white">
          <div className="flex items-center justify-between pb-4 border-b border-border">
            <h3 className="font-display text-base text-primary">Filters</h3>
            <ChevronDown className="h-4 w-4 text-muted-foreground" />
          </div>

          <div className="pt-5 space-y-6">
            <div>
              <h4 className="text-sm font-semibold mb-3">Category</h4>
              <ul className="space-y-2">
                {CATEGORIES.filter((c) => c.key !== "all").map((c) => {
                  const count = products.filter((p) => p.category === c.key).length;
                  return (
                    <li key={c.key} className="flex items-center justify-between text-xs">
                      <label className="flex items-center gap-2 cursor-pointer">
                        <input
                          type="radio"
                          name="cat"
                          checked={category === c.key}
                          onChange={() => setCategory(c.key)}
                          className="accent-primary"
                        />
                        <span>{c.label}</span>
                      </label>
                      <span className="text-muted-foreground">({count})</span>
                    </li>
                  );
                })}
              </ul>
              <button onClick={() => setCategory("all")} className="mt-2 text-xs underline text-foreground">
                Clear category
              </button>
            </div>

            <div>
              <h4 className="text-sm font-semibold mb-3">Price</h4>
              <ul className="space-y-2">
                {PRICE_BUCKETS.map((b, i) => (
                  <li key={b.label} className="flex items-center gap-2 text-xs">
                    <label className="flex items-center gap-2 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={prices.includes(i)}
                        onChange={() => toggle(prices, setPrices, i)}
                        className="accent-primary"
                      />
                      <span>{b.label}</span>
                    </label>
                  </li>
                ))}
              </ul>
            </div>

            <div>
              <h4 className="text-sm font-semibold mb-3">Sort by</h4>
              <select
                value={sort}
                onChange={(e) => setSort(e.target.value as typeof sort)}
                className="w-full border border-border rounded-md px-2 py-2 text-xs bg-white"
              >
                <option value="featured">Featured</option>
                <option value="low">Price: Low to High</option>
                <option value="high">Price: High to Low</option>
                <option value="name">Name</option>
              </select>
            </div>
          </div>
        </aside>

        {/* Product grid */}
        <div>
          <p className="text-xs text-muted-foreground mb-4">{filtered.length} product{filtered.length !== 1 && "s"}</p>
          {filtered.length === 0 ? (
            <div className="text-center py-24 border border-dashed border-border rounded-lg">
              <p className="text-sm text-muted-foreground">No products match your filters.</p>
            </div>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
              {filtered.map((p) => (
                <div key={p.id} className="bg-white rounded-md overflow-hidden border border-border flex flex-col">
                  <Link to="/product/$id" params={{ id: p.id }} className="aspect-square overflow-hidden block">
                    <img src={p.image} alt={p.name} loading="lazy" className="w-full h-full object-cover hover:scale-105 transition duration-500" />
                  </Link>
                  <div className="p-4 flex-1 flex flex-col">
                    <div className="flex items-center justify-between">
                      <Link to="/product/$id" params={{ id: p.id }} className="font-display text-sm text-primary uppercase tracking-wider hover:underline">
                        {p.name}
                      </Link>
                      <span className="text-sm text-primary font-semibold">${p.price.toFixed(2)}</span>
                    </div>
                    <p className="mt-1 text-xs text-muted-foreground line-clamp-2 flex-1">
                      {p.description ?? "Handmade with love and the finest ingredients."}
                    </p>
                    <button
                      onClick={() => {
                        cart.add({ productId: p.id });
                        toast.success(`${p.name} added to cart`);
                      }}
                      className="mt-3 w-full border border-border rounded-md py-2 text-xs font-medium hover:bg-primary hover:text-primary-foreground hover:border-primary transition inline-flex items-center justify-center gap-1"
                    >
                      <Plus className="h-3 w-3" /> Add to Cart
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      <SiteFooter />
    </div>
  );
}
