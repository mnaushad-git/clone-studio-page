import { createFileRoute, Link } from "@tanstack/react-router";
import { Heart, ChevronRight } from "lucide-react";
import { SiteHeader } from "@/components/SiteHeader";
import { SiteFooter } from "@/components/SiteFooter";
import { ProductCard } from "@/components/ProductCard";
import { useStore, wishlist as wishlistApi } from "@/lib/store";
import { getProduct } from "@/lib/products";

export const Route = createFileRoute("/wishlist")({
  component: WishlistPage,
  head: () => ({
    meta: [
      { title: "My Wishlist — Terrific Bites" },
      { name: "description", content: "Your saved desserts and gift boxes." },
      { property: "og:title", content: "My Wishlist — Terrific Bites" },
      { property: "og:description", content: "Your saved desserts and gift boxes." },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary_large_image" },
      { name: "robots", content: "noindex" },
    ],
  }),
});

function WishlistPage() {
  const ids = useStore((s) => s.wishlist);
  const items = ids.map((id) => getProduct(id)).filter((p): p is NonNullable<ReturnType<typeof getProduct>> => !!p);

  return (
    <div className="min-h-screen bg-background text-foreground">
      <SiteHeader />

      <div className="max-w-7xl mx-auto px-6 pt-10 pb-6 text-center">
        <h1 className="font-display text-4xl md:text-5xl text-primary">My Wishlist</h1>
        <nav className="mt-3 flex items-center justify-center gap-2 text-xs text-muted-foreground">
          <Link to="/" className="hover:text-primary">Home</Link>
          <ChevronRight className="h-3 w-3" />
          <span className="text-primary">Wishlist</span>
        </nav>
      </div>

      <div className="max-w-7xl mx-auto px-6 pb-16">
        {items.length === 0 ? (
          <div className="text-center py-24 border border-dashed border-border rounded-lg bg-white">
            <Heart className="h-10 w-10 mx-auto text-muted-foreground/60" />
            <p className="mt-3 text-sm text-muted-foreground">Your wishlist is empty.</p>
            <Link to="/shop" className="mt-4 inline-block bg-primary text-primary-foreground rounded-md px-5 py-2 text-sm font-medium hover:opacity-90">
              Discover treats
            </Link>
          </div>
        ) : (
          <>
            <div className="flex items-center justify-between mb-4">
              <p className="text-xs text-muted-foreground">{items.length} saved item{items.length !== 1 && "s"}</p>
              <button onClick={() => wishlistApi.clear()} className="text-xs underline text-muted-foreground hover:text-foreground">
                Clear wishlist
              </button>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
              {items.map((p) => (
                <ProductCard key={p.id} product={p} />
              ))}
            </div>
          </>
        )}
      </div>

      <SiteFooter />
    </div>
  );
}
