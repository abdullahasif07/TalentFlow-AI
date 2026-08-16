import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";

export function LoadingState({ cards = 4 }: { cards?: number }) {
  return (
    <div className="space-y-6" aria-busy="true" aria-label="Loading content">
      <div className={cn("grid gap-4 sm:grid-cols-2", cards === 5 ? "xl:grid-cols-5" : "xl:grid-cols-4")}>
        {Array.from({ length: cards }, (_, index) => (
          <div key={index} className="rounded-xl border bg-card p-5">
            <Skeleton className="h-4 w-28" />
            <Skeleton className="mt-4 h-9 w-16" />
            <Skeleton className="mt-3 h-3 w-36" />
          </div>
        ))}
      </div>
      <div className="rounded-xl border bg-card p-5">
        <Skeleton className="h-5 w-40" />
        <div className="mt-6 space-y-4">
          {Array.from({ length: 4 }, (_, index) => (
            <Skeleton key={index} className="h-14 w-full" />
          ))}
        </div>
      </div>
    </div>
  );
}
