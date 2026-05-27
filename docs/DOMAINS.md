# 域名采购清单(你执行,我不能替买)

## 推荐优先级

| 域名 | 用途 | 估价(US$/年) | 必要性 |
|---|---|---|---|
| **traillens.zorotreeking.online** | 主站(production) | ~14 | ★★★★★ |
| **traillens.ai** | 备选 / 落地 | ~95 | ★★★ |
| **traillens.dev** | 工程 / 文档子站(可后期) | ~14 | ★★ |
| **traillens.com** | 强建议尽早抢(防被抢注) | ~12 | ★★★★ |

## 购买注册商对比

| 注册商 | 优点 | 缺点 |
|---|---|---|
| **Namecheap** | 价格透明,whoisguard 免费,UX 好 | 国内访问偶尔慢 |
| **Cloudflare Registrar** | 价格 = wholesale + 0(最便宜) | 必须域名解析也用 CF |
| **阿里云万网** | 国内备案友好,支付宝付 | 国际 TLD 贵 ~30% |

**推荐**:Cloudflare Registrar 买 `.app` + `.com`,因为后续 R2/Workers 都在 CF。

## 买完后立即做

```bash
# 1. CF 解析记录
A      @         <your-fly.io-ip>
CNAME  www       traillens.zorotreeking.online
CNAME  api       <api.fly.io>
CNAME  app       cname.vercel-dns.com.

# 2. 邮箱(收 PH/HN 反馈)
# CF 不提供邮件,推荐 Resend 或 Cloudflare Email Routing(免费):
#   hello@zorotreeking.online  →  你的 gmail
#   feedback@traillens.zorotreeking.online → 同上
#   abuse@traillens.zorotreeking.online → 同上(法律合规)

# 3. 反向 DNS / TXT 记录(为 PH 验证用)
TXT    @         google-site-verification=...
TXT    _dmarc    v=DMARC1; p=quarantine; rua=mailto:hello@zorotreeking.online

# 4. SSL/TLS 模式 → Full (strict)
```

## 商标 / 公司(可选,长期)

- **traillens** 中国大陆商标查询:[商标局官网](http://sbj.cnipa.gov.cn) — 第 9 / 42 类
- **traillens** 美国 USPTO 查询:tess2.uspto.gov
- 如做 SaaS 收款,需要主体(LLC / 个体户)。Stripe Atlas 美国 LLC ≈ $500,Lemon Squeezy 不需要(它代收)。

## 完成后请回复给我

把买到的域名告诉我,我会把:
- `apps/web/app/page.tsx` 的 GitHub 链接换成 `traillens/traillens`
- `apps/web/app/layout.tsx` 的 metadata.canonical 加上域名
- `.env.example` 的 R2_PUBLIC_BASE 换成 `https://photos.<你的域名>`
- `next.config.mjs` 的 remotePatterns 加上自定义域
