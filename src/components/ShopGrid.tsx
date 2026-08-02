import { Link } from "@tanstack/react-router";
import { useMemo, useState } from "react";
import { ChevronDown, ChevronRight, Search, X } from "lucide-react";
import { SiteHeader } from "@/components/SiteHeader";
import { SiteFooter } from "@/components/SiteFooter";
import { ProductCard } from "@/components/ProductCard";
import { QueryState } from "@/components/QueryState";
import { useT, type TKey } from "@/lib/i18n";
import { type Category, type Occasion, type Recipient, OCCASIONS, RECIPIENTS } from "@/lib/products";
import { mapSummaryToProduct, useCatalogueProducts } from "@/lib/catalogue-api";

// Every active product, fetched once and filtered/sorted client-side below — the
// catalogue is small (26 SKUs) and this preserves ShopGrid's existing filter UX
// (category counts, price buckets, occasion/recipient checkboxes, search, sort)
// exactly, now sourced from the catalogue API instead of a static import.
const CATALOGUE_PAGE_SIZE = 100;

const CATEGORIES: { key: Category | "all"; labelKey: TKey }[] = [
  { key: "all", labelKey: "shopCategoryAll" },
  { key: "cupcakes", labelKey: "shopCategoryCupcakes" },
  { key: "cakes", labelKey: "shopCategoryCakes" },
  { key: "chocolates", labelKey: "shopCategoryChocolates" },
  { key: "donuts", labelKey: "shopCategoryDonuts" },
  { key: "gifts", labelKey: "shopCategoryGifts" },
  { key: "extras", labelKey: "shopCategoryExtras" },
];

const OCCASION_LABEL_KEYS: Record<Occasion, TKey> = {
  Birthday: "shopOccasionBirthday",
  Anniversary: "shopOccasionAnniversary",
  Wedding: "shopOccasionWedding",
  Graduation: "shopOccasionGraduation",
  Congratulations: "shopOccasionCongratulations",
  "Thank You": "shopOccasionThankYou",
};

const RECIPIENT_LABEL_KEYS: Record<Recipient, TKey> = {
  "For Him": "shopRecipientForHim",
  "For Her": "shopRecipientForHer",
  "For Kids": "shopRecipientForKids",
  "For Family": "shopRecipientForFamily",
};

const PRICE_BUCKETS: { labelKey: TKey; min: number; max: number }[] = [
  { labelKey: "shopPriceUnder10", min: 0, max: 10 },
  { labelKey: "shopPrice10to25", min: 10, max: 25 },
  { labelKey: "shopPrice25to100", min: 25, max: 100 },
  { labelKey: "shopPrice100Plus", min: 100, max: Infinity },
];

type Props = {
  title: string;
  breadcrumb?: { label: string; to?: string }[];
  initialCategory?: Category | "all";
  lockCategory?: boolean;
  forcedOccasion?: Occasion;
  forcedRecipient?: Recipient;
  showSearch?: boolean;
  hideHeader?: boolean;
  hero?: React.ReactNode;
};

export function ShopGrid({
  title,
  breadcrumb,
  initialCategory = "all",
  lockCategory = false,
  forcedOccasion,
  forcedRecipient,
  showSearch = true,
  hideHeader = false,
  hero,
}: Props) {
  const [category, setCategory] = useState<Category | "all">(initialCategory);
  const [prices, setPrices] = useState<number[]>([]);
  const [occasions, setOccasions] = useState<Occasion[]>(forcedOccasion ? [forcedOccasion] : []);
  const [recipients, setRecipients] = useState<Recipient[]>(forcedRecipient ? [forcedRecipient] : []);
  const [sort, setSort] = useState<"featured" | "low" | "high" | "name">("featured");
  const [query, setQuery] = useState("");
  const t = useT();

  const {
    data: page,
    isLoading,
    isError,
    refetch,
  } = useCatalogueProducts({ limit: CATALOGUE_PAGE_SIZE });
  const products = useMemo(() => (page ? page.items.map(mapSummaryToProduct) : []), [page]);

  const filtered = useMemo(() => {
    let list = category === "all" ? products : products.filter((p) => p.category === category);
    if (query.trim()) {
      const q = query.trim().toLowerCase();
      list = list.filter(
        (p) =>
          p.name.toLowerCase().includes(q) ||
          p.description?.toLowerCase().includes(q) ||
          p.category.toLowerCase().includes(q),
      );
    }
    if (prices.length > 0) {
      list = list.filter((p) =>
        prices.some((i) => p.price >= PRICE_BUCKETS[i].min && p.price < PRICE_BUCKETS[i].max),
      );
    }
    if (occasions.length > 0) {
      list = list.filter((p) => p.occasions?.some((o) => occasions.includes(o)));
    }
    if (recipients.length > 0) {
      list = list.filter((p) => p.recipients?.some((r) => recipients.includes(r)));
    }
    if (sort === "low") list = [...list].sort((a, b) => a.price - b.price);
    else if (sort === "high") list = [...list].sort((a, b) => b.price - a.price);
    else if (sort === "name") list = [...list].sort((a, b) => a.name.localeCompare(b.name));
    return list;
  }, [products, category, prices, occasions, recipients, sort, query]);

  const toggle = <T,>(arr: T[], set: (v: T[]) => void, val: T) =>
    set(arr.includes(val) ? arr.filter((x) => x !== val) : [...arr, val]);

  const clearAll = () => {
    if (!lockCategory) setCategory("all");
    setPrices([]);
    if (!forcedOccasion) setOccasions([]);
    if (!forcedRecipient) setRecipients([]);
    setQuery("");
    setSort("featured");
  };

  return (
    <div className="min-h-screen bg-background text-foreground">
      {!hideHeader && <SiteHeader />}

      {hero ? (
        <div>{hero}</div>
      ) : (
        <div className="max-w-7xl mx-auto px-6 pt-10 pb-6 text-center">
          <h1 className="font-display text-4xl md:text-5xl text-primary">{title}</h1>
          <nav className="mt-3 flex items-center justify-center gap-2 text-xs text-muted-foreground flex-wrap">
            <Link to="/" className="hover:text-primary">{t("shopBreadcrumbHome")}</Link>
            {(breadcrumb ?? []).map((b, i) => (
              <span key={i} className="flex items-center gap-2">
                <ChevronRight className="h-3 w-3" />
                {b.to ? (
                  <Link to={b.to} className="hover:text-primary">{b.label}</Link>
                ) : (
                  <span className="text-primary">{b.label}</span>
                )}
              </span>
            ))}
          </nav>
        </div>
      )}

      {showSearch && (
        <div className="max-w-3xl mx-auto px-6 pb-6">
          <div className="relative">
            <Search className="absolute start-4 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder={t("shopSearchPlaceholder")}
              className="w-full ps-11 pe-10 py-3 rounded-full border border-border bg-white text-sm focus:outline-none focus:ring-2 focus:ring-primary/30"
            />
            {query && (
              <button onClick={() => setQuery("")} aria-label={t("shopClearSearchAria")} className="absolute end-3 top-1/2 -translate-y-1/2 p-1 text-muted-foreground hover:text-foreground">
                <X className="h-4 w-4" />
              </button>
            )}
          </div>
        </div>
      )}

      {/* Category chips */}
      {!lockCategory && (
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
                  {sample && <img src={sample.image} alt={t(c.labelKey)} className="h-7 w-7 rounded object-cover" />}
                  <span>{t(c.labelKey)}</span>
                </button>
              );
            })}
          </div>
        </div>
      )}

      <div className="max-w-7xl mx-auto px-6 pb-16 grid grid-cols-1 md:grid-cols-[240px_1fr] gap-8">
        {/* Sidebar */}
        <aside className="border border-border rounded-md p-5 h-fit bg-white">
          <div className="flex items-center justify-between pb-4 border-b border-border">
            <h3 className="font-display text-base text-primary">{t("shopFiltersHeading")}</h3>
            <button onClick={clearAll} className="text-[11px] underline text-muted-foreground hover:text-foreground">
              {t("shopClearAll")}
            </button>
          </div>

          <div className="pt-5 space-y-6">
            {!lockCategory && (
              <FilterGroup title={t("shopFilterCategory")}>
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
                          <span>{t(c.labelKey)}</span>
                        </label>
                        <span className="text-muted-foreground">({count})</span>
                      </li>
                    );
                  })}
                </ul>
              </FilterGroup>
            )}

            <FilterGroup title={t("shopFilterOccasions")}>
              <ul className="space-y-2">
                {OCCASIONS.map((o) => (
                  <li key={o} className="text-xs">
                    <label className="flex items-center gap-2 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={occasions.includes(o)}
                        disabled={forcedOccasion === o}
                        onChange={() => toggle(occasions, setOccasions, o)}
                        className="accent-primary"
                      />
                      <span>{t(OCCASION_LABEL_KEYS[o])}</span>
                    </label>
                  </li>
                ))}
              </ul>
            </FilterGroup>

            <FilterGroup title={t("shopFilterRecipient")}>
              <ul className="space-y-2">
                {RECIPIENTS.map((r) => (
                  <li key={r} className="text-xs">
                    <label className="flex items-center gap-2 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={recipients.includes(r)}
                        disabled={forcedRecipient === r}
                        onChange={() => toggle(recipients, setRecipients, r)}
                        className="accent-primary"
                      />
                      <span>{t(RECIPIENT_LABEL_KEYS[r])}</span>
                    </label>
                  </li>
                ))}
              </ul>
            </FilterGroup>

            <FilterGroup title={t("shopFilterPrice")}>
              <ul className="space-y-2">
                {PRICE_BUCKETS.map((b, i) => (
                  <li key={b.labelKey} className="text-xs">
                    <label className="flex items-center gap-2 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={prices.includes(i)}
                        onChange={() => toggle(prices, setPrices, i)}
                        className="accent-primary"
                      />
                      <span>{t(b.labelKey)}</span>
                    </label>
                  </li>
                ))}
              </ul>
            </FilterGroup>

            <FilterGroup title={t("shopFilterSortBy")}>
              <select
                value={sort}
                onChange={(e) => setSort(e.target.value as typeof sort)}
                className="w-full border border-border rounded-md px-2 py-2 text-xs bg-white"
              >
                <option value="featured">{t("shopSortFeatured")}</option>
                <option value="low">{t("shopSortPriceLowHigh")}</option>
                <option value="high">{t("shopSortPriceHighLow")}</option>
                <option value="name">{t("shopSortName")}</option>
              </select>
            </FilterGroup>
          </div>
        </aside>

        {/* Product grid */}
        <div>
          <QueryState isLoading={isLoading} isError={isError} onRetry={() => refetch()} skeletonCount={6}>
            <p className="text-xs text-muted-foreground mb-4">
              {filtered.length} {filtered.length === 1 ? t("shopProductSingular") : t("shopProductPlural")}
              {category !== "all" &&
                ` ${t("shopInCategory")} ${t(CATEGORIES.find((c) => c.key === category)!.labelKey)}`}
            </p>
            {filtered.length === 0 ? (
              <div className="text-center py-24 border border-dashed border-border rounded-lg">
                <p className="text-sm text-muted-foreground">{t("shopNoProductsMatch")}</p>
                <button onClick={clearAll} className="mt-3 text-xs underline text-primary">{t("shopResetFilters")}</button>
              </div>
            ) : (
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
                {filtered.map((p) => (
                  <ProductCard key={p.id} product={p} />
                ))}
              </div>
            )}
          </QueryState>
        </div>
      </div>

      <SiteFooter />
    </div>
  );
}

function FilterGroup({ title, children }: { title: string; children: React.ReactNode }) {
  const [open, setOpen] = useState(true);
  return (
    <div>
      <button onClick={() => setOpen((v) => !v)} className="w-full flex items-center justify-between text-sm font-semibold mb-3">
        <span>{title}</span>
        <ChevronDown className={`h-3.5 w-3.5 transition ${open ? "" : "-rotate-90"}`} />
      </button>
      {open && children}
    </div>
  );
}
