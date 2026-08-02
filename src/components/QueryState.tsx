import { AlertTriangle } from "lucide-react";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Skeleton } from "@/components/ui/skeleton";
import { useT } from "@/lib/i18n";

type Props = {
  isLoading: boolean;
  isError: boolean;
  onRetry?: () => void;
  /** Grid/card skeleton count while loading. Defaults to a 4-card product grid. */
  skeletonCount?: number;
  children: React.ReactNode;
};

/** Shared loading/error presentation for catalogue-API-backed sections — keeps every
 * page's fetch states visually consistent without each one re-implementing them. */
export function QueryState({ isLoading, isError, onRetry, skeletonCount = 4, children }: Props) {
  const t = useT();

  if (isLoading) {
    return (
      <div className="grid grid-cols-2 md:grid-cols-4 gap-6" role="status" aria-label={t("loading")}>
        {Array.from({ length: skeletonCount }).map((_, i) => (
          <div key={i} className="space-y-3">
            <Skeleton className="aspect-square w-full rounded-md" />
            <Skeleton className="h-4 w-3/4" />
            <Skeleton className="h-3 w-1/2" />
          </div>
        ))}
      </div>
    );
  }

  if (isError) {
    return (
      <Alert variant="destructive" className="max-w-xl mx-auto">
        <AlertTriangle className="h-4 w-4" />
        <AlertDescription className="flex flex-col gap-3">
          <span>{t("errorDesc")}</span>
          {onRetry && (
            <button
              onClick={onRetry}
              className="self-start text-xs underline underline-offset-2 hover:text-foreground"
            >
              {t("tryAgain")}
            </button>
          )}
        </AlertDescription>
      </Alert>
    );
  }

  return <>{children}</>;
}
