import { createFileRoute } from "@tanstack/react-router";
import { ShopGrid } from "@/components/ShopGrid";
import { useT } from "@/lib/i18n";

export const Route = createFileRoute("/donuts")({
  component: () => {
    const t = useT();
    return (
      <ShopGrid title={t("shopCategoryDonuts")} breadcrumb={[{ label: t("shopCategoryDonuts") }]} initialCategory="donuts" lockCategory />
    );
  },
  head: () => ({
    meta: [
      { title: "Donuts — Terrific Bites" },
      { name: "description", content: "Fluffy filled and glazed donuts baked daily." },
      { property: "og:title", content: "Donuts — Terrific Bites" },
      { property: "og:description", content: "Fluffy filled and glazed donuts baked daily." },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary_large_image" },
    ],
  }),
});
