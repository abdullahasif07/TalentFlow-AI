import { graphqlUrl } from "@/lib/graphql/config";

/** Base URL of the backend (the GraphQL URL without its trailing /graphql path). */
export const apiBaseUrl = (
  process.env.NEXT_PUBLIC_API_URL ?? graphqlUrl.replace(/\/graphql\/?$/, "")
).replace(/\/$/, "");

export function apiUrl(path: string) {
  return `${apiBaseUrl}${path.startsWith("/") ? path : `/${path}`}`;
}

export function resumeDownloadUrl(applicationId: string) {
  return apiUrl(`/applications/${encodeURIComponent(applicationId)}/resume`);
}
