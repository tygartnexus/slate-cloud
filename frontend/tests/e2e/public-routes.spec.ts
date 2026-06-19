import { expect, test } from "@playwright/test";

const BASE_URL = "http://127.0.0.1:3210";

test("public home and pricing routes render bounded free-access claims", async ({
  page,
}) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: /broken AI animation/i })).toBeVisible();
  await expect(page.getByText(/MIT-licensed/i)).toBeVisible();

  await page.goto("/pricing");
  await expect(page.getByRole("heading", { name: /One free Slate/i })).toBeVisible();
  await expect(page.getByText(/There is no checkout/i)).toBeVisible();
});

test("dashboard initiates Clerk auth without exposing protected UI", async ({
  page,
}) => {
  let clerkHandshakeUrl: string | undefined;
  page.on("requestfailed", (request) => {
    if (request.url().includes("clerk.example/v1/client/handshake")) {
      clerkHandshakeUrl = request.url();
    }
  });

  const navigationError = await page
    .goto("/dashboard")
    .then(() => undefined)
    .catch((error: Error) => error);

  expect(navigationError?.message).toContain("ERR_NAME_NOT_RESOLVED");
  expect(clerkHandshakeUrl).toContain("/v1/client/handshake");
  expect(decodeURIComponent(clerkHandshakeUrl ?? "")).toContain(
    "http://127.0.0.1:3210/dashboard",
  );
  expect(await page.getByRole("heading", { name: "Verdicts" }).count()).toBe(0);
});

test("dashboard fixture cookie with wrong secret cannot bypass Clerk", async ({
  browser,
}) => {
  const context = await browser.newContext({
    baseURL: BASE_URL,
    extraHTTPHeaders: {
      "x-slate-e2e-auth": "wrong-e2e-secret-0000000000000000",
    },
  });
  const page = await context.newPage();
  await context.addCookies([
    {
      name: "slate_e2e_auth",
      value: "1",
      domain: "127.0.0.1",
      path: "/",
      sameSite: "Lax",
    },
  ]);

  let clerkHandshakeUrl: string | undefined;
  page.on("requestfailed", (request) => {
    if (request.url().includes("clerk.example/v1/client/handshake")) {
      clerkHandshakeUrl = request.url();
    }
  });

  const navigationError = await page
    .goto("/dashboard")
    .then(() => undefined)
    .catch((error: Error) => error);

  expect(navigationError?.message).toContain("ERR_NAME_NOT_RESOLVED");
  expect(clerkHandshakeUrl).toContain("/v1/client/handshake");
  expect(await page.getByRole("heading", { name: "Verdicts" }).count()).toBe(0);
  await context.close();
});

test("authenticated dashboard renders fixture verdict detail and mode switch", async ({
  page,
}) => {
  await page.context().addCookies([
    {
      name: "slate_e2e_auth",
      value: "1",
      domain: "127.0.0.1",
      path: "/",
      sameSite: "Lax",
    },
  ]);

  await page.goto("/dashboard");
  await expect(page.getByRole("heading", { name: "Verdicts" })).toBeVisible();
  await expect(page.getByText("1 verdict uploaded")).toBeVisible();
  await expect(page.getByText("village_walk_001")).toBeVisible();
  await expect(page.getByText("E2E user")).toBeVisible();

  await page.getByText("village_walk_001").click();
  await expect(page.getByText("PANEL_BLOCKED")).toBeVisible();
  await expect(page.getByText("Evidence-based answer")).toBeVisible();
  await expect(page.getByText("Source: payload.response_quality")).toBeVisible();

  await page.getByRole("button", { name: "Red Team Mode" }).click();
  await expect(page.getByText("Hostile red-team review")).toBeVisible();
  await expect(
    page.getByText("Source: panel.per_persona[0].response_quality"),
  ).toBeVisible();
});
