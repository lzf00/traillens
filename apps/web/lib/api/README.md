# Typed API client

> 不要手写 fetch 调 `/v1/...`。
> 用这里的 `api` client,所有路径、参数、返回类型由 OpenAPI 自动生成。

## 重新生成(改了 api schema 后)

```bash
# 1) 从 api 服务导出 OpenAPI
python scripts/export_openapi.py --out apps/web/lib/api/openapi.json

# 2) 生成 TS 类型
cd apps/web
npx openapi-typescript lib/api/openapi.json -o lib/api/schema.d.ts

# 3) Done — client.ts 自动用上新类型
```

CI 在 `.github/workflows/deploy.yml` 的 `publish-openapi` job 会把 spec 作为 artifact 发布。

## 用法

```ts
import { api } from "@/lib/api/client";

const { data, error } = await api.GET("/v1/trails/{trail_id}", {
  params: { path: { trail_id: "xxx" } },
});
if (error) throw error;
// data 现在是 TrailOut,有完整类型补全
```
