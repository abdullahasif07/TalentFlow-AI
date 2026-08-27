export function publicApplicationPath(jobId: string) {
  return `/jobs/${encodeURIComponent(jobId)}/apply`;
}

export function publicApplicationUrl(origin: string, jobId: string) {
  return new URL(publicApplicationPath(jobId), origin).toString();
}
