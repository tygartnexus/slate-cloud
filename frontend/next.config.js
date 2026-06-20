/** @type {import('next').NextConfig} */
const productionBypassVars = [
  "SLATE_E2E_AUTH_BYPASS",
  "NEXT_PUBLIC_SLATE_E2E_AUTH_BYPASS",
  "SLATE_E2E_API_FIXTURE",
  "SLATE_E2E_AUTH_SECRET",
];

if (
  process.env.NODE_ENV === "production" &&
  !(
    process.env.PLAYWRIGHT_TEST === "1" &&
    process.env.SLATE_ALLOW_LOCAL_E2E_BUILD === "true"
  ) &&
  productionBypassVars.some((name) => process.env[name])
) {
  throw new Error("E2E fixture auth variables must not be set in production builds.");
}

const nextConfig = {
  typedRoutes: true,
};

module.exports = nextConfig;
