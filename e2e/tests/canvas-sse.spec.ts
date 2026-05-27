/**
 * 核心端到端:创 trail → 触发 run → 收 SSE 事件流。
 *
 * 这是最有价值的 e2e — 它跨 web → api → agent → SSE 协议全链路。
 * 任何一层挂了这个测试都会红。
 */

import { test, expect, request } from "@playwright/test";

const API = process.env.API_BASE || "http://localhost:8000";

test("create trail → run → SSE stream completes", async () => {
  const ctx = await request.newContext({ baseURL: API });

  // 1. 创 trail
  const createResp = await ctx.post("/v1/trails", { data: { name: "e2e smoke" } });
  expect(createResp.ok()).toBeTruthy();
  const trail = await createResp.json();
  expect(trail.id).toBeTruthy();

  // 2. 触发 run + 解析 SSE
  const runResp = await ctx.post(`/v1/trails/${trail.id}/run`);
  expect(runResp.ok()).toBeTruthy();
  expect(runResp.headers()["content-type"]).toContain("text/event-stream");

  const body = await runResp.text();
  expect(body).toContain("event: run.started");
  expect(body).toContain("event: run.finished");
  // 至少出现 culling 阶段
  expect(body).toMatch(/event: culling\.(progress|photo_scored)/);
});

test("404 on unknown trail", async () => {
  const ctx = await request.newContext({ baseURL: API });
  const r = await ctx.get("/v1/trails/nonexistent");
  expect(r.status()).toBe(404);
});

test("healthz reachable", async () => {
  const ctx = await request.newContext({ baseURL: API });
  const r = await ctx.get("/healthz");
  expect(r.ok()).toBeTruthy();
  const data = await r.json();
  expect(data.status).toBe("ok");
});
