import { useQueries } from "@tanstack/react-query";
import { fetchProductDetail } from "@/lib/catalogue-api";
import { getProduct } from "@/lib/products";
import { useStore } from "@/lib/store";

/**
 * The cart is saved in the browser but the product lookup behind getProduct() is in memory,
 * so after a refresh a cart line has a quantity and price but no name or image. This loads
 * whatever is missing and re-renders the calling component when it arrives.
 */
export function useCartProducts(): void {
  const productIds = useStore((s) => s.cart.map((line) => line.productId).join("\n"));
  const ids = productIds ? [...new Set(productIds.split("\n"))] : [];

  useQueries({
    queries: ids.map((id) => ({
      queryKey: ["catalogue", "cart-product", id],
      queryFn: () => fetchProductDetail(id),
      enabled: !getProduct(id),
      staleTime: 5 * 60 * 1000,
    })),
  });
}
