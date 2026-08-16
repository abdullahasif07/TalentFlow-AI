import type { LucideIcon } from "lucide-react";

import { Card, CardContent } from "@/components/ui/card";
import { cn } from "@/lib/utils";

interface StatCardProps {
  label: string;
  value: number | string;
  detail?: string;
  icon: LucideIcon;
  className?: string;
}

export function StatCard({ label, value, detail, icon: Icon, className }: StatCardProps) {
  return (
    <Card className={cn("overflow-hidden", className)}>
      <CardContent className="p-5">
        <div className="flex items-start justify-between gap-4">
          <div>
            <p className="text-sm font-medium text-muted-foreground">{label}</p>
            <p className="mt-2 text-3xl font-semibold tracking-tight text-foreground">{value}</p>
            {detail ? <p className="mt-2 text-xs text-muted-foreground">{detail}</p> : null}
          </div>
          <div className="rounded-lg border border-[#d7e8e3] bg-[#eef7f4] p-2.5 text-primary">
            <Icon className="size-5" aria-hidden="true" />
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
