# 给 `api.traillens.zorotreeking.online` 申请 SSL 证书

> 你 nginx 已经在为 `zorotreeking.online` 跑 HTTPS,但 `api.traillens` 子域**没有证书**。
> 三种方式,**推荐用方式 A**(腾讯云免费证书,10 分钟图形化操作)。

---

## 方式 A:腾讯云免费证书(推荐)

### A.1 申请

1. 打开 https://console.cloud.tencent.com/ssl
2. 点 **「申请免费证书」**
3. 弹窗填:
   - **证书品牌**:TrustAsia / SecureSite(都行,自动选)
   - **绑定域名**:`api.traillens.zorotreeking.online`(精确填,不带通配符)
   - **验证方式**:**DNS 验证**(因为腾讯云能自动加 TXT 记录)
   - **邮箱**:你常用的
4. 提交。如果 DNS 在腾讯云 DNSPod 里,**腾讯云自动加 TXT 记录,5-15 分钟签发完**;
   如果在阿里云/Cloudflare,会让你手动加一条 TXT 记录(腾讯云会显示要加什么)

### A.2 下载

签发后,在 SSL 控制台 → 我的证书 → 找到这个证书 → **「下载」**:
- 选 **「Nginx」** 格式
- 下载 zip 包,解压有两个文件:
  - `api.traillens.zorotreeking.online_bundle.crt`
  - `api.traillens.zorotreeking.online.key`

### A.3 上传到 CVM(在你 Mac 终端跑)

```bash
# 上传证书到 CVM 的 /etc/nginx/ssl/
ssh root@110.40.142.199 "mkdir -p /etc/nginx/ssl"

scp api.traillens.zorotreeking.online_bundle.crt \
    root@110.40.142.199:/etc/nginx/ssl/api.traillens.zorotreeking.online.crt

scp api.traillens.zorotreeking.online.key \
    root@110.40.142.199:/etc/nginx/ssl/api.traillens.zorotreeking.online.key

# 锁权限(只允许 root 读)
ssh root@110.40.142.199 "chmod 600 /etc/nginx/ssl/api.traillens.zorotreeking.online.*"
```

---

## 方式 B:acme.sh 自动签 + 续期(进阶)

证书自动续期(每 60 天),但配置稍复杂。命令清单:

```bash
# 在 CVM 上:
curl https://get.acme.sh | sh -s email=hello@zorotreeking.online
source ~/.bashrc

# DNS-01 验证(避免占 80 端口冲突)
# 如果你 DNS 在腾讯云 DNSPod:
export DP_Id="你的 DNSPod ID"
export DP_Key="你的 DNSPod token"
~/.acme.sh/acme.sh --issue --dns dns_dp -d api.traillens.zorotreeking.online

# 安装到 nginx
~/.acme.sh/acme.sh --install-cert -d api.traillens.zorotreeking.online \
  --key-file       /etc/nginx/ssl/api.traillens.zorotreeking.online.key \
  --fullchain-file /etc/nginx/ssl/api.traillens.zorotreeking.online.crt \
  --reloadcmd      "systemctl reload nginx"
```

---

## 方式 C:不签证书,用 HTTP(仅测试,**不推荐**)

如果只是想立刻验证 API 通,改 nginx 配置删掉 SSL 段,改 `listen 80;`。
但**所有走 https 的客户端**(包括我们 web 前端 / Lightroom 插件)都会失败。

---

## 推荐路径

1. **现在(10 分钟)**:方式 A 申请腾讯云免费证书
2. **3 个月后续期前**:换方式 B(acme.sh)实现自动续期
3. 别用方式 C
