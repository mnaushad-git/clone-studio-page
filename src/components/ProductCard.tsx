import { Link } from "@tanstack/react-router";
import { Heart, Plus, Star } from "lucide-react";
import { toast } from "sonner";
import type { Product } from "@/lib/products";
import { cart, wishlist, useStore, selectIsWishlisted, selectAverageRating } from "@/lib/store";

export function ProductCard({ product }: { product: Product }) {
  const wished = useStore(selectIsWishlisted(product.id));
  const avg = useStore(selectAverageRating(product.id));

  const toggle = (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    const added = wishlist.toggle(product.id);
    toast.success(added ? `${product.name} added to wishlist` : `${product.name} removed from wishlist`);
  };

  const add = () => {
    cart.add({ productId: product.id });
    toast.success(`${product.name} added to cart`);
  };

  return (
    <div className="bg-white rounded-md overflow-hidden border border-border flex flex-col group">
      <div className="relative">
        <Link to="/product/$id" params={{ id: product.id }} className="aspect-square overflow-hidden block">
          <img
            src={product.image}
            alt={product.name}
            loading="lazy"
            className="w-full h-full object-cover group-hover:scale-105 transition duration-500"
          />
        </Link>
        <button
          onClick={toggle}
          aria-label={wished ? "Remove from wishlist" : "Add to wishlist"}
          className="absolute top-3 end-3 h-9 w-9 rounded-full bg-white/90 backdrop-blur flex items-center justify-center shadow hover:scale-110 transition"
        >
          <Heart
            className={`h-4 w-4 ${wished ? "text-red-500 fill-red-500" : "text-foreground"}`}
          />
        </button>
        {product.isNew && (
          <span className="absolute top-3 start-3 bg-primary text-primary-foreground text-[10px] uppercase tracking-wider px-2 py-1 rounded">
            New
          </span>
        )}
      </div>
      <div className="p-4 flex-1 flex flex-col">
        <div className="flex items-center justify-between gap-2">
          <Link
            to="/product/$id"
            params={{ id: product.id }}
            className="font-display text-sm text-primary uppercase tracking-wider hover:underline"
          >
            {product.name}
          </Link>
          <span className="text-sm text-primary font-semibold whitespace-nowrap">${product.price.toFixed(2)}</span>
        </div>
        {avg > 0 && (
          <div className="mt-1 flex items-center gap-1 text-[11px] text-muted-foreground">
            <Star className="h-3 w-3 fill-yellow-400 text-yellow-400" />
            <span>{avg.toFixed(1)}</span>
          </div>
        )}
        <p className="mt-1 text-xs text-muted-foreground line-clamp-2 flex-1">
          {product.description ?? "Handmade with love and the finest ingredients."}
        </p>
        <button
          onClick={add}
          className="mt-3 w-full border border-border rounded-md py-2 text-xs font-medium hover:bg-primary hover:text-primary-foreground hover:border-primary transition inline-flex items-center justify-center gap-1"
        >
          <Plus className="h-3 w-3" /> Add to Cart
        </button>
      </div>
    </div>
  );
}
