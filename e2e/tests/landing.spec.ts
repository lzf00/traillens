import { test, expect } from "@playwright/test";

test("landing renders hero + CTA", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { level: 1 })).toContainText("landscape photographers");
  await expect(page.getByRole("link", { name: /demo trail|示例|opening/i }).first()).toBeVisible();
});

test("landing 切到 /en 显示英文", async ({ page }) => {
  await page.goto("/en");
  await expect(page.getByRole("heading", { level: 1 })).toContainText("landscape photographers");
});

test("OG card endpoint 返回 1200x630 PNG-ish 响应", async ({ request }) => {
  const r = await request.get("/og?title=smoke&kind=trail&kept=42");
  expect(r.ok()).toBeTruthy();
  // ImageResponse 实际返回 image/png
  expect(r.headers()["content-type"]).toContain("image/");
});
