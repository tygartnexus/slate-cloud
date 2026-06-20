import { auth } from "@clerk/nextjs/server";
import { cookies, headers } from "next/headers";

const E2E_BYPASS_VALUE = "unsafe-local-only";
const E2E_CLERK_PUBLISHABLE_KEY = "pk_test_Y2xlcmsuZXhhbXBsZSQ";
const E2E_AUTH_HEADER = "x-slate-e2e-auth";
export const E2E_AUTH_COOKIE = "slate_e2e_auth";

export function isE2EAuthBypassConfigured(): boolean {
  return (
    (process.env.NODE_ENV !== "production" ||
      (process.env.PLAYWRIGHT_TEST === "1" &&
        process.env.SLATE_ALLOW_LOCAL_E2E_BUILD === "true")) &&
    process.env.SLATE_E2E_AUTH_BYPASS === E2E_BYPASS_VALUE &&
    process.env.NEXT_PUBLIC_SLATE_E2E_AUTH_BYPASS === E2E_BYPASS_VALUE &&
    process.env.SLATE_E2E_API_FIXTURE === "true" &&
    process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY === E2E_CLERK_PUBLISHABLE_KEY &&
    typeof process.env.SLATE_E2E_AUTH_SECRET === "string" &&
    process.env.SLATE_E2E_AUTH_SECRET.length >= 32
  );
}

export async function getDashboardAuth(): Promise<{
  userId: string | null;
  token: string | null;
  isBypass: boolean;
}> {
  const cookieStore = await cookies();
  const headerStore = await headers();
  const host = headerStore.get("host") ?? "";
  if (
    isE2EAuthBypassConfigured() &&
    isLocalhost(host) &&
    headerStore.get(E2E_AUTH_HEADER) === process.env.SLATE_E2E_AUTH_SECRET &&
    cookieStore.get(E2E_AUTH_COOKIE)?.value === "1"
  ) {
    return {
      userId: "e2e-user",
      token: process.env.SLATE_E2E_AUTH_SECRET,
      isBypass: true,
    };
  }

  const authResult = await auth();
  return {
    userId: authResult.userId,
    token: await authResult.getToken(),
    isBypass: false,
  };
}

function isLocalhost(host: string): boolean {
  return (
    host === "localhost" ||
    host.startsWith("localhost:") ||
    host === "127.0.0.1" ||
    host.startsWith("127.0.0.1:") ||
    host === "[::1]" ||
    host.startsWith("[::1]:")
  );
}
