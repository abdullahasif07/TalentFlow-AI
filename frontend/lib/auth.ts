import { apiUrl } from "@/lib/api";

export interface RecruiterSession {
  id: string;
  name: string;
  email: string;
  role: string;
  companyId: string;
  companyName: string;
  isDemo: boolean;
}

export interface AuthConfig {
  demoMode: boolean;
  demoEmail: string | null;
}

export class AuthRequestError extends Error {
  constructor(
    message: string,
    readonly status: number | null = null,
  ) {
    super(message);
  }
}

interface SessionResponse {
  id: string;
  name: string;
  email: string;
  role: string;
  company_id: string;
  company_name: string;
  is_demo: boolean;
}

function toSession(payload: SessionResponse): RecruiterSession {
  return {
    id: payload.id,
    name: payload.name,
    email: payload.email,
    role: payload.role,
    companyId: payload.company_id,
    companyName: payload.company_name,
    isDemo: payload.is_demo,
  };
}

async function request(path: string, init?: RequestInit): Promise<Response> {
  try {
    return await fetch(apiUrl(path), {
      ...init,
      credentials: "include",
      headers: { "Content-Type": "application/json", ...init?.headers },
    });
  } catch {
    throw new AuthRequestError(
      "We couldn’t reach the TalentFlow API. Check that the backend is running.",
    );
  }
}

async function errorDetail(response: Response, fallback: string) {
  try {
    const body = (await response.json()) as { detail?: unknown };
    return typeof body.detail === "string" ? body.detail : fallback;
  } catch {
    return fallback;
  }
}

export async function fetchSession(): Promise<RecruiterSession | null> {
  const response = await request("/auth/me");
  if (response.status === 401) return null;
  if (!response.ok) {
    throw new AuthRequestError("Unable to check your session.", response.status);
  }
  return toSession((await response.json()) as SessionResponse);
}

export async function fetchAuthConfig(): Promise<AuthConfig> {
  const response = await request("/auth/config");
  if (!response.ok) return { demoMode: false, demoEmail: null };
  const body = (await response.json()) as { demo_mode: boolean; demo_email: string | null };
  return { demoMode: body.demo_mode, demoEmail: body.demo_email };
}

export async function signIn(email: string, password: string): Promise<RecruiterSession> {
  const response = await request("/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
  if (!response.ok) {
    throw new AuthRequestError(
      await errorDetail(response, "Unable to sign in. Please try again."),
      response.status,
    );
  }
  return toSession((await response.json()) as SessionResponse);
}

export async function signInAsDemo(): Promise<RecruiterSession> {
  const response = await request("/auth/demo", { method: "POST" });
  if (!response.ok) {
    throw new AuthRequestError(
      await errorDetail(response, "The demo account is unavailable right now."),
      response.status,
    );
  }
  return toSession((await response.json()) as SessionResponse);
}

export async function signOut(): Promise<void> {
  await request("/auth/logout", { method: "POST" });
}

/** Only allow same-site relative redirects after sign-in. */
export function safeNextPath(value: string | null | undefined) {
  if (!value || !value.startsWith("/") || value.startsWith("//")) return "/dashboard";
  return value;
}

export const UNAUTHENTICATED_EVENT = "talentflow:unauthenticated";
