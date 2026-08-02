/** Renders a cart/order line's selected variant attributes (any number of axes) as a
 * single display string, e.g. "9 INCH · Chocolate". Replaces what used to be several
 * independent `[size, flavor].filter(Boolean).join(" · ")` copies across the app.
 * Accepts either the local cart/Order shape (`Record<code, value_label_en>`) or the
 * backend wire shape (`{code, name_en, value_label_en}[]`, e.g. AdminOrderItemOut).
 */
export function formatAttributes(
  attributes: Record<string, string> | { value_label_en: string }[] | undefined | null,
): string {
  if (!attributes) return "";
  const values = Array.isArray(attributes)
    ? attributes.map((a) => a.value_label_en)
    : Object.values(attributes);
  return values.filter(Boolean).join(" · ");
}
