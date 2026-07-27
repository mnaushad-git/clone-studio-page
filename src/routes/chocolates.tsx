import { createFileRoute } from "@tanstack/react-router";
import { ShopGrid } from "@/components/ShopGrid";
import { useT } from "@/lib/i18n";

export const Route = createFileRoute("/chocolates")({
  component: () => {
    const t = useT();
    return (
      <ShopGrid title={t("shopCategoryChocolates")} breadcrumb={[{ label: t("shopCategoryChocolates") }]} initialCategory="chocolates" lockCategory />
    );
  },
  head: () => ({
    meta: [
      { title: "Chocolates — Terrific Bites" },
      { name: "description", content: "Handmade truffles, pralines and ganache bites." },
      { property: "og:title", content: "Chocolates — Terrific Bites" },
      { property: "og:description", content: "Handmade truffles, pralines and ganache bites." },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary_large_image" },
    ],
  }),
});
