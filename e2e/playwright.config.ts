import { defineConfig, devices } from "@playwright/test";

/**
 * 假设 api 跑在 8000,web 跑在 3000(用 Makefile 的 e2e target 一起启)。
 * CI 通过 `webServer` 自动启,本地手动启更省事。
 */
export default defineConfig({
  testDir: "./tests",
  timeout: 30_000,
  expect: { timeout: 5_000 },
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 2 : undefined,
  reporter: [["list"], ["html", { open: "never" }]],

  use: {
    baseURL: process.env.E2E_BASE_URL || "http://localhost:3000",
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
    video: "retain-on-failure",
  },

  projects: [
    { name: "chromium", use: { ...devices["Desktop Chrome"] } },
    // mobile 只测关键路径
    { name: "mobile-safari", use: { ...devices["iPhone 14"] }, testMatch: /landing|share/ },
  ],

  // 仅 CI 自启服务(本地用 make api & make web-dev)
  ...(process.env.CI && {
    webServer: [
      {
        command: "cd ../apps/api && TRAILLENS_DISABLE_RATELIMIT=1 TRAILLENS_USE_STUBS=1 uvicorn traillens_api.main:app --port 8000",
        port: 8000,
        timeout: 30_000,
        reuseExistingServer: false,
      },
      {
        command: "cd ../apps/web && NEXT_PUBLIC_API_BASE=http://localhost:8000 npm run dev",
        port: 3000,
        timeout: 60_000,
        reuseExistingServer: false,
      },
    ],
  }),
});
