import { createFileRoute } from "@tanstack/react-router";
import { ShopGrid } from "@/components/ShopGrid";
import { useT } from "@/lib/i18n";

export const Route = createFileRoute("/shop")({
  component: () => {
    const t = useT();
    return (
      <ShopGrid
        title={t("shopAllTitle")}
        breadcrumb={[{ label: t("shopBreadcrumbShop") }]}
        initialCategory="all"
      />
    );
  },
  head: () => ({
    meta: [
      { title: "Shop All Desserts — Terrific Bites" },
      { name: "description", content: "Search and filter our full range of cakes, cupcakes, chocolates, donuts and gifts." },
      { property: "og:title", content: "Shop — Terrific Bites" },
      { property: "og:description", content: "Search and filter all our handmade desserts and gifts." },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary_large_image" },
    ],
  }),
});
