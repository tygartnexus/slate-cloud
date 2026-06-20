import { clerkMiddleware, createRouteMatcher } from "@clerk/nextjs/server";
import { type NextFetchEvent, type NextRequest, NextResponse } from "next/server";

const isProtectedRoute = createRouteMatcher(["/dashboard(.*)"]);
const E2E_AUTH_BYPASS_VALUE = "unsafe-local-only";
const E2E_AUTH_COOKIE = "slate_e2e_auth";
const E2E_AUTH_HEADER = "x-slate-e2e-auth";
const E2E_CLERK_PUBLISHABLE_KEY = "pk_test_Y2xlcmsuZXhhbXBsZSQ";

function isE2EFixtureRequest(req: NextRequest): boolean {
  const secret = process.env.SLATE_E2E_AUTH_SECRET;
  return (
    (process.env.NODE_ENV !== "production" ||
      (process.env.PLAYWRIGHT_TEST === "1" &&
        process.env.SLATE_ALLOW_LOCAL_E2E_BUILD === "true")) &&
    isLocalhost(req.nextUrl.hostname) &&
    process.env.SLATE_E2E_AUTH_BYPASS === E2E_AUTH_BYPASS_VALUE &&
    process.env.NEXT_PUBLIC_SLATE_E2E_AUTH_BYPASS === E2E_AUTH_BYPASS_VALUE &&
    process.env.SLATE_E2E_API_FIXTURE === "true" &&
    process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY === E2E_CLERK_PUBLISHABLE_KEY &&
    typeof secret === "string" &&
    secret.length >= 32 &&
    req.headers.get(E2E_AUTH_HEADER) === secret &&
    req.cookies.get(E2E_AUTH_COOKIE)?.value === "1"
  );
}

function isLocalhost(hostname: string): boolean {
  return hostname === "localhost" || hostname === "127.0.0.1" || hostname === "::1";
}

const clerkGuard = clerkMiddleware(async (auth, req) => {
  if (!isProtectedRoute(req)) return;
  await auth.protect();
});

export default function middleware(req: NextRequest, event: NextFetchEvent) {
  if (isProtectedRoute(req) && isE2EFixtureRequest(req)) {
    return NextResponse.next();
  }
  return clerkGuard(req, event);
}

export const config = {
  matcher: ["/dashboard(.*)"],
};
