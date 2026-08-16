import type { LucideIcon } from "lucide-react";
import { Inbox } from "lucide-react";

import { Card, CardContent } from "@/components/ui/card";

interface EmptyStateProps {
  title: string;
  description: string;
  icon?: LucideIcon;
  action?: React.ReactNode;
}

export function EmptyState({ title, description, icon: Icon = Inbox, action }: EmptyStateProps) {
  return (
    <Card>
      <CardContent className="flex min-h-64 flex-col items-center justify-center px-6 py-12 text-center">
        <div className="rounded-xl border bg-muted p-3 text-muted-foreground">
          <Icon className="size-6" aria-hidden="true" />
        </div>
        <h3 className="mt-4 text-base font-semibold">{title}</h3>
        <p className="mt-1 max-w-md text-sm leading-6 text-muted-foreground">{description}</p>
        {action ? <div className="mt-5">{action}</div> : null}
      </CardContent>
    </Card>
  );
}
