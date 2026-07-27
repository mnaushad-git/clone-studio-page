import { createFileRoute } from "@tanstack/react-router";
import { ShopGrid } from "@/components/ShopGrid";
import { useT } from "@/lib/i18n";

export const Route = createFileRoute("/cakes")({
  component: () => {
    const t = useT();
    return (
      <ShopGrid title={t("shopCategoryCakes")} breadcrumb={[{ label: t("shopCategoryCakes") }]} initialCategory="cakes" lockCategory />
    );
  },
  head: () => ({
    meta: [
      { title: "Cakes — Terrific Bites" },
      { name: "description", content: "Layered celebration cakes, buttercream classics and made-to-order designs." },
      { property: "og:title", content: "Cakes — Terrific Bites" },
      { property: "og:description", content: "Layered celebration cakes handcrafted for every occasion." },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary_large_image" },
    ],
  }),
});
