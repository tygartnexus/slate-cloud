import { randomUUID } from "node:crypto";

import { defineConfig, devices } from "@playwright/test";

const e2eAuthSecret = process.env.SLATE_E2E_AUTH_SECRET ?? randomUUID();
process.env.SLATE_E2E_AUTH_SECRET = e2eAuthSecret;

export default defineConfig({
  testDir: "./tests/e2e",
  fullyParallel: true,
  forbidOnly: Boolean(process.env.CI),
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: [["list"], ["html", { outputFolder: "playwright-report", open: "never" }]],
  use: {
    baseURL: process.env.BASE_URL ?? "http://127.0.0.1:3210",
    extraHTTPHeaders: {
      "x-slate-e2e-auth": e2eAuthSecret,
    },
    trace: "on-first-retry",
    screenshot: "only-on-failure",
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
  webServer: {
    command: "npm run build && npm run start -- -p 3210",
    url: "http://127.0.0.1:3210",
    reuseExistingServer: false,
    timeout: 120000,
    env: {
      NEXT_PUBLIC_SLATE_REPO_URL: "https://github.com/tygartnexus/slate",
      NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY: "pk_test_Y2xlcmsuZXhhbXBsZSQ",
      NEXT_PUBLIC_SLATE_E2E_AUTH_BYPASS: "unsafe-local-only",
      CLERK_SECRET_KEY: "sk_test_dummy",
      SLATE_E2E_AUTH_BYPASS: "unsafe-local-only",
      SLATE_E2E_API_FIXTURE: "true",
      SLATE_E2E_AUTH_SECRET: e2eAuthSecret,
      SLATE_API_URL: "http://127.0.0.1:8000",
    },
  },
});
