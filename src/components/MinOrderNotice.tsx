import { selectMinOrder, selectMinOrderShortfall, useStore } from "@/lib/store";
import { useT } from "@/lib/i18n";

/** The one minimum-order rule and wording for every step before payment. */
export function useMinOrder() {
  const t = useT();
  const shortfall = useStore(selectMinOrderShortfall);
  const message =
    shortfall > 0
      ? `${t("cartMinOrderPrefix")} SAR ${selectMinOrder().toFixed(2)}. ` +
        `${t("cartMinOrderAddPrefix")} SAR ${shortfall.toFixed(2)} ${t("cartMinOrderAddSuffix")}`
      : null;
  return { blocked: shortfall > 0, message };
}

export function MinOrderNotice({ message }: { message: string | null }) {
  if (!message) return null;
  return (
    <p role="alert" className="text-xs text-destructive text-center">
      {message}
    </p>
  );
}
