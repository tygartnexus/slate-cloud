/** @type {import('next').NextConfig} */
const nextConfig = {
  typedRoutes: true,
  env: {
    NEXT_PUBLIC_SLATE_E2E_AUTH_BYPASS:
      process.env.NEXT_PUBLIC_SLATE_E2E_AUTH_BYPASS,
    SLATE_E2E_AUTH_BYPASS: process.env.SLATE_E2E_AUTH_BYPASS,
    SLATE_E2E_API_FIXTURE: process.env.SLATE_E2E_API_FIXTURE,
  },
};

module.exports = nextConfig;
