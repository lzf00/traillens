# Week in Review · 2026-06-24

> TrailLens build-in-public 周记 #3。本周从「Canvas 能跑」做到「公开 demo 能分享」。

## TL;DR

- **公开 demo 上线**:`traillens.zorotreeking.online/trails/demo` 不需要登录,
  Hero 大图 + AI 点评 + 八维雷达 + 拍摄计划全在
- **真 auth + OAuth 路由就绪**(等 Google/GitHub 凭证)
- **Library 真接 pgvector**:豆包 embedding 写库,中文查询 score 0.8+ 区分准确
- **数据健康面板**:Settings 一眼看每个 trail 的 photos / critique / embedding 完整度
- **下载 keep zip**:Canvas 菜单一键拿原图(文件名带分数前缀方便挑片)

## 本周做了什么

按主题(非时间)整理。

### 1. 真实闭环关口:`/trails/demo` 自动选 trail

之前 hardcode 一个 trail_id,trail 被删后 demo 404。改成后端 `pick_demo_trail()`
按 `(travelogue 非空 + photo 多 + 最新)` 自动选,前端 redirect 拿到。结果:
- demo trail 内容随我自己上传的真实数据迭代
- 我无须改前端代码

```sql
SELECT t.* FROM trails t
WHERE (SELECT COUNT(*) FROM photos WHERE trail_id=t.id) > 0
ORDER BY (t.travelogue_md IS NOT NULL) DESC,
         (SELECT COUNT(*) FROM photos WHERE trail_id=t.id) DESC,
         t.updated_at DESC
LIMIT 1;
```

### 2. share 页:从"功能演示"改成"作品集"

之前的 share 页是网格 + 游记 pre 块,很工程师审美。改成:

- **Hero 70vh 全屏首图**,渐变遮罩 + 标题叠在底部
- **拍摄计划用 `<dl>` 结构化**,key 中文映射(`best_windows` → "最佳时间窗")
- 底部加 **引流 CTA** "用 TrailLens 整理自己的徒步"
- OG meta 优先用 keep 首图(微信/小红书转发更视觉)

### 3. Library:从 stub 到真 pgvector

之前 Library 是"暂无结果,Sprint 5 末才接 pgvector"的占位。本周接通:

- 豆包 `doubao-embedding-text-240715` 编码 critique → `vector(768)` 列
- `orchestrator` 跑完 Run 自动 embed,Library 立刻能搜
- search 端点优先 cosine 距离,无 embedding fallback 三路 ILIKE(name/location/travelogue)
- 加 `?trail_id=` 过滤(Canvas 顶部"搜本组"跳过来)
- 结果按 trail 分组渲染

实测中文查询:
```
搜「雪山日落」 → snow.jpg 0.910 > cloud.jpg 0.849  ✓
搜「云海长焦」 → cloud.jpg 0.868 > snow.jpg 0.808  ✓
搜「暖色调」    → snow.jpg 0.849 > cloud.jpg 0.800  ✓
```

### 4. Auth 真实化:从 dev 桥到 JWT + OAuth 路由

旧 dev 桥用 `traillens_user_id` cookie 直接当 user_id(任何邮箱都能"登录")。
本周替换为:
- `/v1/auth/sign-up` / `sign-in`:bcrypt + JWT(`traillens_session` HttpOnly cookie)
- `/v1/auth/me` 解码 cookie 返 profile,Nav SSR 调它判登录态
- `/v1/auth/sign-out`:browser POST 走 303 redirect 到 `/`,fetch 走 JSON(避免裸 JSON 暴露)
- OAuth start/callback 骨架完整,等 Google/GitHub console 凭证

兼容性:sign-in 同时写 `traillens_user_email` cookie,让老的标注后台无缝兼容。

### 5. seed_demo 脚本

`scripts/seed_demo.py` 纯 stdlib(urllib),一键:
注册 → 创建 trail → 上传 N 张 → 触发 Run → 消费 SSE。新部署/fork 后跑一行就能演示。

### 6. 踩到的坑

**A. Next 15 把 `cookies()` 调用的页面静态化了**

`/` 和 `/trails` 用 `cookies()` 判断登录态,Next 15 build 时 cookie store 空,
prerender 出 false 分支的 HTML + `s-maxage=31536000` 缓存 1 年。
浏览器永远看到"未登录"版本,即使 cookie 在。

修:显式 `export const dynamic = "force-dynamic"`。

**B. 宝塔 nginx 全局 `proxy_cache cache_one`**

第一个访问 `/` 的用户的 RSC 输出被缓存,所有人都看到他的版本。修:`location /` 加
`proxy_cache off; proxy_no_cache 1; proxy_cache_bypass 1`。

**C. Content-Disposition `UnicodeEncodeError`**

下载 zip 端点 trail 名"zip 中文测试",`Content-Disposition: filename=...` 必须
latin-1。`isalnum()` 在 Python 对汉字返 True,过滤没过滤住。修:RFC 5987 双写
`filename="ascii_fallback" filename*=UTF-8''<percent-encoded>`。

**D. Pydantic email 拒 `.local` 域**

E2E 注册 `e2e@traillens.local` → 422 "special-use or reserved name"。
改用 `@example.com`。

### 7. Playwright E2E

写了 `tl-e2e-browser.py` 跑 9 步(Landing/注册/新建/Library/Settings/share/登出),
真打开 Chromium 看渲染。发现并修了 2 个 bug:

1. **登出后看到裸 `{"ok":true}` JSON 页面** — 修 sign-out 按 Accept header 区分浏览器 vs fetch
2. **新 auth 用户访问标注后台 403** — 修 sign-in 兼容写 `traillens_user_email`

## 在线体验

- **demo trail**(免登录):https://traillens.zorotreeking.online/trails/demo
- **注册自己跑**:https://traillens.zorotreeking.online/signup
- **代码**:https://github.com/<...>/traillens(本周 +24 commits)

## 下周

继续推:
- 真接 EXIF MCP server 让游记 EXIF 不再是 stub
- 标注到 200+ 启动 Q-Align LoRA 训练(packages/aesthetic/train_qalign_lora.py)
- dark/light theme toggle(目前 dark only)
- 写一份"我是怎么用 LangGraph + 豆包做多智能体的"技术深度博客
