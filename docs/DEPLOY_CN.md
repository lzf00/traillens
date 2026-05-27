# 国内栈部署指引（推荐路径）

> 这是 100% 国内服务的部署组合,**免备案 + 免费起步**,适合你 `traillens.zorotreeking.online` 这类已备案子域名。
> 如需海外部署见 [DEPLOY.md](DEPLOY.md)。

---

## 推荐组合(全部免费起步)

| 用途 | 服务 | 免费额度 | 控制台 |
|---|---|---|---|
| **前端** | EdgeOne Pages(腾讯云) | 完全免费 + 国内 CDN | https://console.cloud.tencent.com/edgeone/pages |
| **后端 API** | Sealos Serverless | 每月 ¥10 额度免费 | https://cloud.sealos.run |
| **数据库** | Sealos Postgres(含 pgvector) | 1c1g 免费 | 同上 |
| **缓存** | Sealos Redis | 1c512m 免费 | 同上 |
| **照片存储** | 七牛云 Kodo | 10GB 永久免费 | https://portal.qiniu.com/kodo |
| **LLM** | 豆包(火山引擎方舟) | 注册送 50 万 tokens | https://console.volcengine.com/ark |
| **GPU 训练** | AutoDL | ¥1.6/h RTX 4090 | https://www.autodl.com |
| **代码仓库** | GitHub(主) + Gitee(镜像加速国内) | 都免费 | github.com/lzf00/traillens |
| **监控** | 自托管 Langfuse + Sentry(docker) | 永久免费 | 在 Sealos 一键起 |
| **域名 DNS** | 你的 zorotreeking.online 注册商 | — | — |

**起步总成本**:¥0/月,直到月用户量 > 100。

---

## 步骤 1:前端到 EdgeOne Pages(腾讯云)

```bash
# 1. 装 EdgeOne CLI
npm install -g edgeone

# 2. 登录(扫码,5 秒)
edgeone login

# 3. 关联项目(在 apps/web 目录下)
cd apps/web
edgeone link

# 4. 部署
edgeone pages deploy --build-command "npm run build" --output-directory ".next"
```

部署完拿到一个 `<random>.edgeone.app` 域名。然后:

1. 控制台 → Pages → 项目 → **自定义域名** → 添加 `traillens.zorotreeking.online`
2. 它会给你一个 CNAME 值(类似 `cname.edgeone.dnsv2.com`)
3. 去你的域名 DNS(zorotreeking.online 的注册商)添加记录:
   ```
   类型:CNAME    主机:traillens    记录值:cname.edgeone.dnsv2.com
   ```

5 分钟生效,自动配 HTTPS。

---

## 步骤 2:后端 API 到 Sealos

Sealos 提供"按秒计费 + 服务器零配置"体验,类似 Fly.io 但在国内。

```bash
# 1. 浏览器登录 https://cloud.sealos.run(扫码即可)
# 2. 在 App Store 找到 "App Launchpad" → 部署 Docker 镜像
# 3. 镜像构建 — 在本地:
cd apps/api
docker build -t traillens-api:0.0.1 .
docker tag traillens-api:0.0.1 registry.cn-shanghai.aliyuncs.com/lzf00/traillens-api:0.0.1

# 4. 推到阿里云容器镜像服务(免费):
# 先去 https://cr.console.aliyun.com 开通个人版,创空间 lzf00,密码登录:
docker login --username=<你的阿里云账号> registry.cn-shanghai.aliyuncs.com
docker push registry.cn-shanghai.aliyuncs.com/lzf00/traillens-api:0.0.1

# 5. 回 Sealos App Launchpad 部署:
#    - 镜像名: registry.cn-shanghai.aliyuncs.com/lzf00/traillens-api:0.0.1
#    - 端口: 8000
#    - CPU/内存: 0.5c / 512m(免费层够)
#    - 环境变量:全部从 .env 复制(ARK_API_KEY / DATABASE_URL / REDIS_URL ...)
#    - 自定义域名: api.traillens.zorotreeking.online
```

DNS 加:
```
类型:CNAME   主机:api.traillens   记录值:<sealos 给你的域名>
```

---

## 步骤 3:Postgres + Redis(Sealos 内一键)

```
Sealos 控制台 → 数据库 → 新建集群:
  - PostgreSQL 16 + pgvector 扩展(选模板时勾上)
  - 1c1g / 1GB 存储 → 免费
  - 拿到连接串:postgres://user:pass@host:5432/db
  → 写到 API service 的 DATABASE_URL env

同样新建 Redis 7,免费 1c512m,拿到 redis://... → REDIS_URL
```

第一次部署 API 后会自动跑 `alembic upgrade head`(已写在 release_command),5 张表建好。

---

## 步骤 4:照片存储到七牛云 Kodo

```bash
# 1. https://portal.qiniu.com/kodo/bucket 新建 bucket
#    - 名字: traillens-photos
#    - 区域: 华东(浙江)/华南(深圳)— 看你用户主要在哪
#    - 访问控制: 公开
#    - 永久免费 10GB 存储 + 10GB/月流量

# 2. 拿 AccessKey + SecretKey:
#    https://portal.qiniu.com/user/key

# 3. 写到 .env(全部 R2_xxx 变量改成七牛的 access/secret)
```

七牛 SDK 与 boto3 S3 协议不完全兼容,我会在下一轮把 `services/storage.py` 加七牛 fallback。当前 `services/storage.py` 的 SigV4 路径仍可用于阿里云 OSS / 腾讯云 COS(它们 100% S3 兼容)。

如果用阿里云 OSS / 腾讯云 COS,直接用 SigV4 路径即可,无需改代码,只填:
```
R2_ACCOUNT_ID=<oss-cn-shanghai 等区域>
R2_ACCESS_KEY_ID=<你的 ak>
R2_SECRET_ACCESS_KEY=<你的 sk>
R2_BUCKET=traillens-photos
R2_PUBLIC_BASE=https://photos.traillens.zorotreeking.online
```

---

## 步骤 5:豆包(已经选好,等你给 ARK_API_KEY)

```bash
# 1. https://console.volcengine.com/ark 注册 + 实名
# 2. 左侧 "API Key 管理" → 新建 Key → 复制
# 3. 写到本地 .env(不要上传 GitHub):
echo "ARK_API_KEY=你的_ark_key" >> .env

# 4. 测试调用(等下一轮我写个 test 脚本验)
python3 -c "
from packages.agents.traillens_agents.tools.llm import chat
print(chat(image_url='https://ark-project.tos-cn-beijing.volces.com/doc_image/ark_demo_img_1.png',
           text='你看见了什么?', purpose='vision'))
"
```

---

## 步骤 6:GPU 训练到 AutoDL

```bash
# 1. https://www.autodl.com 注册
# 2. 控制台 → 实例 → 新建实例
#    - GPU: RTX 4090(¥1.6/h)或 A100-80G(¥7/h)
#    - 镜像: PyTorch 2.4.0 + Python 3.11(社区镜像有现成的)
#    - 数据盘: 50GB 系统盘 + 100GB 数据盘
# 3. 实例启好后通过 JupyterLab / SSH 进入
# 4. clone 你的 repo:
#    git clone https://github.com/lzf00/traillens
#    cd traillens/packages/aesthetic
#    pip install torch transformers peft accelerate datasets
#    python train_qalign_lora.py train

# 关机省钱:用完点"关机"而非"释放",
# 关机不收 GPU 钱,只收 ¥0.0011/小时 的存储钱
```

我会在用户给照片后,写一份 AutoDL 端到端跑通脚本(替代 train_modal.py)。

---

## 监控自托管(可选,上线后再做)

Sealos 上一键起:
- **Langfuse**(LLM 调用追踪):App Store 搜 "langfuse" → 一键部署
- **Sentry**(错误监控):同上
- **Umami / PostHog**:产品分析,Umami 比 PostHog 轻得多,推荐

全部免费,Sealos 数据库可共用。

---

## 域名 DNS 总览(给 zorotreeking.online 解析配置)

| 类型 | 主机 | 记录值 | 用途 |
|---|---|---|---|
| CNAME | `traillens` | `cname.edgeone.dnsv2.com` | 前端 |
| CNAME | `api.traillens` | `<sealos 给的域名>` | 后端 API |
| CNAME | `photos.traillens` | `traillens-photos.s3.cn-shanghai.aliyuncs.com` | 照片(若用 OSS) |
| CNAME | `docs.traillens` | `cname.edgeone.dnsv2.com` | 文档站(同前端项目) |

**所有解析都加 HTTPS,EdgeOne / Sealos 自动签证书。**

---

## 起步成本对比

| 组件 | 海外栈(原)| 国内栈(本) |
|---|---|---|
| 前端 | Vercel $0(Hobby) | EdgeOne $0(免费) |
| 后端 | Fly.io $5-10/月 | Sealos $0(免费层) |
| DB | Neon $0 | Sealos PG $0 |
| 照片 | R2 $0 | 七牛 / OSS $0 |
| LLM | Anthropic $20-50/月 | 豆包 ¥0-50/月 |
| GPU | Modal $3/h | AutoDL ¥1.6/h |
| **总起步** | **$25/月起** | **¥0/月** |

---

## 备案问题

`traillens.zorotreeking.online` 是子域名 — 用主域 `zorotreeking.online` 的备案,**不需要单独备案**。前提是主域已经 ICP 备案(看起来已经备案,域名能解析到国内服务器)。

如果你想用 EdgeOne / Sealos 的**公网访问**,需要域名已备案(已具备)。

国内服务商部署"未备案"域名,80 端口会被屏蔽——所以用 443(HTTPS)是免备案绕路,但**EdgeOne / Sealos 这类合规云会强制检查**,所以**别绕,用备案域名**。

---

## 下一步

回我下面任一项,立刻配合:
1. **EdgeOne 账号注册好了** → 我帮你写一键部署脚本(`apps/web/edgeone-deploy.sh`)
2. **七牛 / OSS 选好了** → 我把 `storage.py` 加对应 SDK fallback
3. **AutoDL 实例起好了** → 我写训练入口脚本(替换 `train_modal.py`)
4. **ARK_API_KEY 写到本地 .env 了** → 我跑端到端豆包验证
