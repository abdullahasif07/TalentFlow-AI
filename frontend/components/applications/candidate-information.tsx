import {
  ExternalLink,
  Code2,
  Globe2,
  Network,
  Mail,
  Phone,
  UserRound,
} from "lucide-react";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { ApplicationDetail } from "@/lib/graphql/applications";
import { externalHttpUrl } from "@/lib/resume";

type Candidate = ApplicationDetail["candidate"];

function InformationRow({
  icon: Icon,
  label,
  value,
  href,
}: {
  icon: typeof Mail;
  label: string;
  value: string | null;
  href?: string | null;
}) {
  return (
    <div className="flex min-w-0 items-start gap-3 rounded-lg border bg-muted/25 p-3.5">
      <Icon className="mt-0.5 size-4 shrink-0 text-muted-foreground" aria-hidden="true" />
      <div className="min-w-0 flex-1">
        <p className="text-[10px] font-bold uppercase tracking-[0.08em] text-muted-foreground">
          {label}
        </p>
        {href && value ? (
          <a
            href={href}
            target={href.startsWith("http") ? "_blank" : undefined}
            rel={href.startsWith("http") ? "noreferrer" : undefined}
            className="mt-1 flex min-w-0 items-center gap-1.5 text-sm font-medium text-primary hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/30"
          >
            <span className="truncate">{value}</span>
            {href.startsWith("http") ? <ExternalLink className="size-3 shrink-0" /> : null}
          </a>
        ) : (
          <p className="mt-1 truncate text-sm font-medium text-foreground">
            {value || "Not provided"}
          </p>
        )}
      </div>
    </div>
  );
}

export function CandidateInformation({ candidate }: { candidate: Candidate }) {
  const linkedinUrl = externalHttpUrl(candidate.linkedinUrl);
  const githubUrl = externalHttpUrl(candidate.githubUrl);
  const portfolioUrl = externalHttpUrl(candidate.portfolioUrl);

  return (
    <Card>
      <CardHeader className="flex-row items-center gap-3">
        <div className="rounded-lg bg-muted p-2 text-muted-foreground">
          <UserRound className="size-4.5" />
        </div>
        <div>
          <CardTitle>Candidate information</CardTitle>
          <p className="mt-1 text-xs text-muted-foreground">
            Contact details and professional profiles supplied with the application.
          </p>
        </div>
      </CardHeader>
      <CardContent className="grid gap-3 sm:grid-cols-2">
        <InformationRow icon={Mail} label="Email" value={candidate.email} href={`mailto:${candidate.email}`} />
        <InformationRow
          icon={Phone}
          label="Phone"
          value={candidate.phone}
          href={candidate.phone ? `tel:${candidate.phone}` : null}
        />
        <InformationRow icon={Network} label="LinkedIn" value={candidate.linkedinUrl} href={linkedinUrl} />
        <InformationRow icon={Code2} label="GitHub" value={candidate.githubUrl} href={githubUrl} />
        <InformationRow icon={Globe2} label="Portfolio" value={candidate.portfolioUrl} href={portfolioUrl} />
      </CardContent>
    </Card>
  );
}
