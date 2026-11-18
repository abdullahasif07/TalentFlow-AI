import { NextResponse, type NextRequest } from "next/server";

/**
 * Forwards /backend/* to the API (BACKEND_ORIGIN) so the browser only ever talks to
 * this site's own domain. That keeps the API's session cookie first-party: it is set
 * on, and sent back to, the frontend's domain, so browsers that block third-party
 * cookies (Safari, Chrome incognito) still keep recruiters signed in.
 *
 * Set NEXT_PUBLIC_GRAPHQL_URL=/backend/graphql to use it. Locally you can keep calling
 * http://localhost:8000 directly, in which case this file is never reached.
 */
const BACKEND_PREFIX = "/backend";

export function proxy(request: NextRequest) {
  const backendOrigin = process.env.BACKEND_ORIGIN;
  if (!backendOrigin) {
    return NextResponse.json(
      { detail: "BACKEND_ORIGIN is not configured on the frontend." },
      { status: 500 },
    );
  }

  const { pathname, search } = request.nextUrl;
  const target = new URL(pathname.slice(BACKEND_PREFIX.length) || "/", backendOrigin);
  target.search = search;

  const headers = new Headers(request.headers);
  headers.set("host", target.host);

  // Pass the visitor's address on for per-IP rate limits; otherwise every request
  // would appear to come from the proxy. The API trusts it only alongside the secret.
  headers.delete("x-tf-client-ip");
  headers.delete("x-tf-proxy-secret");
  const clientIp =
    request.headers.get("x-real-ip") ??
    request.headers.get("x-forwarded-for")?.split(",")[0]?.trim();
  if (clientIp) headers.set("x-tf-client-ip", clientIp);

  const secret = process.env.PROXY_SHARED_SECRET;
  if (secret) headers.set("x-tf-proxy-secret", secret);

  return NextResponse.rewrite(target, { request: { headers } });
}

export const config = {
  matcher: "/backend/:path*",
};
