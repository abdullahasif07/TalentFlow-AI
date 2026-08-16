import { CircleAlert, RefreshCw } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";

interface ErrorStateProps {
  title?: string;
  description?: string;
  onRetry?: () => void;
}

export function ErrorState({
  title = "We couldn’t load this data",
  description = "Check that the API is running, then try again.",
  onRetry,
}: ErrorStateProps) {
  return (
    <Card className="border-rose-200">
      <CardContent className="flex min-h-56 flex-col items-center justify-center p-8 text-center">
        <div className="rounded-xl bg-rose-50 p-3 text-rose-600">
          <CircleAlert className="size-6" aria-hidden="true" />
        </div>
        <h3 className="mt-4 font-semibold">{title}</h3>
        <p className="mt-1 max-w-md text-sm text-muted-foreground">{description}</p>
        {onRetry ? (
          <Button className="mt-5" variant="outline" onClick={onRetry}>
            <RefreshCw /> Try again
          </Button>
        ) : null}
      </CardContent>
    </Card>
  );
}
