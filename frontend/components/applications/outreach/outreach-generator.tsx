"use client";

import { LoaderCircle, Sparkles } from "lucide-react";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

const MAX_INSTRUCTION_LENGTH = 500;

export function OutreachGenerator({
  loading,
  onGenerate,
  compact = false,
}: {
  loading: boolean;
  onGenerate: (instruction: string | null) => Promise<boolean>;
  compact?: boolean;
}) {
  const [instruction, setInstruction] = useState("");

  return (
    <div className={compact ? "space-y-3" : "rounded-xl border bg-muted/25 p-4 sm:p-5"}>
      <div>
        <label htmlFor="outreach-instruction" className="text-sm font-semibold">
          Optional recruiter instruction
        </label>
        <p className="mt-1 text-xs leading-5 text-muted-foreground">
          Guide the tone or emphasis without changing the candidate facts.
        </p>
      </div>
      <Input
        id="outreach-instruction"
        value={instruction}
        maxLength={MAX_INSTRUCTION_LENGTH}
        disabled={loading}
        onChange={(event) => setInstruction(event.target.value)}
        placeholder="Focus on their backend experience"
      />
      <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <span className="text-[11px] text-muted-foreground">
          {instruction.length}/{MAX_INSTRUCTION_LENGTH}
        </span>
        <Button
          onClick={() => void onGenerate(instruction.trim() || null)}
          disabled={loading}
        >
          {loading ? (
            <LoaderCircle className="animate-spin" aria-hidden="true" />
          ) : (
            <Sparkles aria-hidden="true" />
          )}
          {loading ? "Generating outreach…" : "Generate outreach"}
        </Button>
      </div>
    </div>
  );
}
