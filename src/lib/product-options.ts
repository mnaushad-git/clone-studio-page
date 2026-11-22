import { variantComboKey, type Product } from "@/lib/products";

/** One selector group on the product page. Built only from the product's real
 * catalogue variants: a product with a single variant gets no selectors at all. */
export type SelectorAxis = { code: string; name: string; values: string[] };

export function selectorAxes(product: Pick<Product, "variantAxes">): SelectorAxis[] {
  return product.variantAxes?.filter((a) => a.values.length > 0) ?? [];
}

export type Selection = {
  /** Attributes sent with the cart line; undefined when the product has no options. */
  attributes: Record<string, string> | undefined;
  unitPrice: number;
  sku: string | undefined;
  /** False when the chosen combination has no real variant behind it. Such a
   * selection must not be added to the cart: the server would substitute the default
   * variant, which is not what the customer chose. */
  available: boolean;
};

export function resolveSelection(
  product: Pick<Product, "price" | "sku" | "variantAxes" | "variantPriceByKey" | "variantSkuByKey">,
  selectedIndices: Record<string, number>,
): Selection {
  const axes = selectorAxes(product);
  if (axes.length === 0) {
    return { attributes: undefined, unitPrice: product.price, sku: product.sku, available: true };
  }
  const attributes: Record<string, string> = {};
  for (const axis of axes) {
    attributes[axis.code] = axis.values[selectedIndices[axis.code] ?? 0] ?? axis.values[0];
  }
  const key = variantComboKey(attributes);
  const price = product.variantPriceByKey?.[key];
  if (price === undefined) {
    return { attributes, unitPrice: product.price, sku: undefined, available: false };
  }
  return { attributes, unitPrice: price, sku: product.variantSkuByKey?.[key], available: true };
}

/** The product's own images only: its primary image plus its catalogue gallery,
 * without duplicates. Never images of other products. */
export function productGallery(product: Pick<Product, "image" | "thumbs">): string[] {
  const images = product.thumbs && product.thumbs.length > 0 ? product.thumbs : [product.image];
  return [...new Set(images.filter(Boolean))];
}
