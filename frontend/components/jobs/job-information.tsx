import { BookOpenCheck, BriefcaseBusiness, Sparkles } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { RecruiterJob } from "@/lib/graphql/jobs";
import { stringList } from "@/lib/graphql/jobs";

type JsonRecord = Record<string, unknown>;

function isRecord(value: unknown): value is JsonRecord {
  return Boolean(value) && typeof value === "object" && !Array.isArray(value);
}

function titleFromKey(value: string) {
  return value
    .replaceAll("_", " ")
    .replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function CriteriaValue({ value }: { value: unknown }) {
  if (Array.isArray(value)) {
    const textItems = value.filter(
      (item): item is string => typeof item === "string" && Boolean(item.trim()),
    );
    if (!textItems.length) return <span className="text-muted-foreground">None specified</span>;

    return (
      <div className="flex flex-wrap gap-2">
        {textItems.map((item) => (
          <Badge key={item} variant="secondary">{item}</Badge>
        ))}
      </div>
    );
  }

  if (typeof value === "number") return <span>{value}</span>;
  if (typeof value === "string" && value.trim()) return <span>{value}</span>;
  if (typeof value === "boolean") return <span>{value ? "Yes" : "No"}</span>;
  if (isRecord(value)) {
    return (
      <div className="space-y-2">
        {Object.entries(value).map(([key, item]) => (
          <div key={key} className="flex items-start justify-between gap-4">
            <span className="text-muted-foreground">{titleFromKey(key)}</span>
            <CriteriaValue value={item} />
          </div>
        ))}
      </div>
    );
  }

  return <span className="text-muted-foreground">Not specified</span>;
}

export function JobInformation({ job }: { job: RecruiterJob }) {
  const requiredSkills = stringList(job.requiredSkills);
  const preferredSkills = stringList(job.preferredSkills);
  const criteria = isRecord(job.evaluationCriteria) ? job.evaluationCriteria : {};
  const categories = Array.isArray(criteria.evaluation_categories)
    ? criteria.evaluation_categories.filter(isRecord)
    : [];
  const supportingCriteria = Object.entries(criteria).filter(
    ([key]) => key !== "evaluation_categories",
  );
  const hasCriteria = categories.length > 0 || supportingCriteria.length > 0;

  return (
    <div className="grid gap-6 xl:grid-cols-[minmax(0,1.35fr)_minmax(320px,0.85fr)]">
      <div className="space-y-6">
        <Card>
          <CardHeader className="flex-row items-center gap-3">
            <div className="rounded-lg bg-muted p-2 text-muted-foreground">
              <BriefcaseBusiness className="size-4.5" />
            </div>
            <CardTitle>Job description</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="whitespace-pre-line text-sm leading-7 text-muted-foreground">
              {job.description}
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex-row items-center gap-3">
            <div className="rounded-lg bg-muted p-2 text-muted-foreground">
              <BookOpenCheck className="size-4.5" />
            </div>
            <CardTitle>Role requirements</CardTitle>
          </CardHeader>
          <CardContent className="space-y-6">
            <div>
              <p className="text-xs font-bold uppercase tracking-[0.08em] text-muted-foreground">Experience requirement</p>
              <p className="mt-2 text-sm">{job.experienceRequirement || "Not specified"}</p>
            </div>
            <div>
              <p className="text-xs font-bold uppercase tracking-[0.08em] text-muted-foreground">Required skills</p>
              <div className="mt-2 flex flex-wrap gap-2">
                {requiredSkills.length
                  ? requiredSkills.map((skill) => <Badge key={skill} variant="secondary">{skill}</Badge>)
                  : <span className="text-sm text-muted-foreground">None listed</span>}
              </div>
            </div>
            <div>
              <p className="text-xs font-bold uppercase tracking-[0.08em] text-muted-foreground">Preferred skills</p>
              <div className="mt-2 flex flex-wrap gap-2">
                {preferredSkills.length
                  ? preferredSkills.map((skill) => <Badge key={skill} variant="outline">{skill}</Badge>)
                  : <span className="text-sm text-muted-foreground">None listed</span>}
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      <Card className="h-fit">
        <CardHeader className="flex-row items-center gap-3">
          <div className="rounded-lg bg-[#e8f3f0] p-2 text-primary">
            <Sparkles className="size-4.5" />
          </div>
          <div>
            <CardTitle>Evaluation criteria</CardTitle>
            <p className="mt-1 text-xs text-muted-foreground">The structured rubric used for candidate evaluation.</p>
          </div>
        </CardHeader>
        <CardContent className="space-y-5">
          {!hasCriteria ? (
            <div className="rounded-lg border border-dashed p-5 text-center">
              <p className="text-sm font-medium">No evaluation criteria yet</p>
              <p className="mt-1 text-xs leading-5 text-muted-foreground">Criteria will appear after AI job analysis is completed.</p>
            </div>
          ) : (
            <>
              {categories.length ? (
                <div className="space-y-3">
                  {categories.map((category, index) => (
                    <div key={`${String(category.name)}-${index}`} className="rounded-lg border p-3.5">
                      <div className="flex items-start justify-between gap-3">
                        <p className="text-sm font-semibold">{String(category.name ?? `Category ${index + 1}`)}</p>
                        {typeof category.weight === "number" ? (
                          <Badge variant="outline">{category.weight}%</Badge>
                        ) : null}
                      </div>
                      {typeof category.description === "string" ? (
                        <p className="mt-2 text-xs leading-5 text-muted-foreground">{category.description}</p>
                      ) : null}
                    </div>
                  ))}
                </div>
              ) : null}

              {supportingCriteria.length ? (
                <div className="space-y-4 border-t pt-5">
                  {supportingCriteria.map(([key, value]) => (
                    <div key={key}>
                      <p className="mb-2 text-xs font-bold uppercase tracking-[0.08em] text-muted-foreground">
                        {titleFromKey(key)}
                      </p>
                      <div className="text-sm"><CriteriaValue value={value} /></div>
                    </div>
                  ))}
                </div>
              ) : null}
            </>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
