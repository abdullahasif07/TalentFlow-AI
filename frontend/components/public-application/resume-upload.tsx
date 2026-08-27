"use client";

import { FileText, UploadCloud, X } from "lucide-react";
import { useRef, useState } from "react";

import { Button } from "@/components/ui/button";
import { formatFileSize } from "@/lib/public-application";
import { cn } from "@/lib/utils";

interface ResumeUploadProps {
  file: File | null;
  error?: string;
  maxSizeMb: number;
  disabled?: boolean;
  onChange: (file: File | null) => void;
}

export function ResumeUpload({
  file,
  error,
  maxSizeMb,
  disabled,
  onChange,
}: ResumeUploadProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragActive, setDragActive] = useState(false);

  function selectFile(files: FileList | null) {
    const selected = files?.item(0) ?? null;
    if (selected) onChange(selected);
    if (inputRef.current) inputRef.current.value = "";
  }

  return (
    <div>
      <label htmlFor="resume-upload" className="text-sm font-semibold">
        Resume PDF <span className="text-destructive">*</span>
      </label>
      <p id="resume-help" className="mt-1 text-xs leading-5 text-muted-foreground">
        Upload one PDF up to {maxSizeMb} MB. The recruiting team will receive this file.
      </p>

      <input
        ref={inputRef}
        id="resume-upload"
        type="file"
        accept=".pdf,application/pdf"
        className="sr-only"
        disabled={disabled}
        aria-invalid={Boolean(error)}
        aria-describedby={error ? "resume-help resume-error" : "resume-help"}
        onChange={(event) => selectFile(event.target.files)}
      />

      {file ? (
        <div
          className={cn(
            "mt-3 flex items-center gap-3 rounded-xl border bg-muted/25 p-3",
            error && "border-rose-300 bg-rose-50/40",
          )}
        >
          <span className="flex size-10 shrink-0 items-center justify-center rounded-lg bg-[#e8f3f0] text-primary">
            <FileText className="size-5" aria-hidden="true" />
          </span>
          <div className="min-w-0 flex-1">
            <p className="truncate text-sm font-semibold">{file.name}</p>
            <p className="mt-0.5 text-xs text-muted-foreground">
              PDF · {formatFileSize(file.size)}
            </p>
          </div>
          <Button
            type="button"
            size="sm"
            variant="ghost"
            disabled={disabled}
            onClick={() => onChange(null)}
            aria-label={`Remove ${file.name}`}
          >
            <X /> Remove
          </Button>
        </div>
      ) : (
        <div
          className={cn(
            "mt-3 rounded-xl border border-dashed px-5 py-7 text-center transition-colors",
            dragActive && "border-primary bg-accent/45",
            error ? "border-rose-300 bg-rose-50/35" : "bg-muted/15",
          )}
          onDragEnter={(event) => {
            event.preventDefault();
            if (!disabled) setDragActive(true);
          }}
          onDragOver={(event) => event.preventDefault()}
          onDragLeave={(event) => {
            event.preventDefault();
            if (!event.currentTarget.contains(event.relatedTarget as Node | null)) {
              setDragActive(false);
            }
          }}
          onDrop={(event) => {
            event.preventDefault();
            setDragActive(false);
            if (!disabled) selectFile(event.dataTransfer.files);
          }}
        >
          <UploadCloud className="mx-auto size-7 text-primary" aria-hidden="true" />
          <p className="mt-3 text-sm font-semibold">Drop your resume PDF here</p>
          <p className="mt-1 text-xs text-muted-foreground">or choose it from your device</p>
          <Button
            type="button"
            size="sm"
            variant="outline"
            className="mt-4"
            disabled={disabled}
            onClick={() => inputRef.current?.click()}
          >
            Choose PDF
          </Button>
        </div>
      )}

      {error ? (
        <p id="resume-error" role="alert" className="mt-2 text-xs font-medium text-rose-700">
          {error}
        </p>
      ) : null}
    </div>
  );
}
