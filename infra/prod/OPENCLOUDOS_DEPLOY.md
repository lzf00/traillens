# OpenCloudOS 9 上一键部署 TrailLens

> 你的 CVM:`110.40.142.199`,系统 `OpenCloudOS 9`(RHEL/CentOS 衍生,用 `dnf`/`yum`)。
> 域名 `traillens.zorotreeking.online` + `api.traillens.zorotreeking.online` 已经解析到此 IP(已验证)。

## 一、SSH 登服务器

在你 Mac 终端:

```bash
ssh root@110.40.142.199
# 若不是 root 用户(腾讯云默认可能是 ubuntu / opencloudos),换成对应用户名
# 第一次 ssh 接受 fingerprint 输 yes
```

## 二、装 Docker(OpenCloudOS 9)

```bash
# 1) 系统包基础
dnf install -y yum-utils device-mapper-persistent-data lvm2 git nano

# 2) 加 Docker 官方 repo(腾讯云国内镜像加速)
dnf config-manager --add-repo https://mirrors.aliyun.com/docker-ce/linux/centos/docker-ce.repo

# 3) 装 docker + compose 插件
dnf install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

# 4) 启 + 开机自启
systemctl enable --now docker

# 5) 验证
docker --version           # 应显示 Docker version 27.x
docker compose version     # 应显示 Docker Compose version v2.x
docker info                # 看 Server 信息有没有正常起来

# 6) 把当前用户加 docker 组(避免每次 sudo;若你是 root 可跳过)
# usermod -aG docker $USER  &&  newgrp docker
```

**国内拉镜像加速**(可选,推荐):

```bash
mkdir -p /etc/docker
cat > /etc/docker/daemon.json <<EOF
{
  "registry-mirrors": [
    "https://mirror.ccs.tencentyun.com",
    "https://docker.m.daocloud.io"
  ]
}
EOF
systemctl restart docker
```

## 三、拉代码 + 配 .env

```bash
# 1) clone 到 /opt/traillens
cd /opt
git clone https://github.com/lzf00/traillens
cd traillens

# 2) 复制 .env 模板 + 编辑
cp .env.example .env
nano .env

# 至少改这几个值(其它留空也行):
#   POSTGRES_PASSWORD=<openssl rand -hex 16 生成强密码>
#   ARK_API_KEY=<你的豆包 key>
#   COS_SECRET_ID=<腾讯云 CAM 密钥 SecretId>
#   COS_SECRET_KEY=<腾讯云 CAM 密钥 SecretKey>
#   COS_BUCKET=<带 appid 的桶名,如 traillens-photos-1305566123>
#   COS_REGION=<和 CVM 同区,你 CVM 在 ap-shanghai 就填这个>
```

**生成 Postgres 密码**:

```bash
openssl rand -hex 16
# 复制输出,粘到 nano 里的 POSTGRES_PASSWORD=
```

## 四、运行部署

```bash
bash infra/prod/deploy.sh
```

脚本会自动:
1. 检查环境(docker / docker compose / .env 必填项)
2. 构建 API 镜像
3. 启 postgres + redis,等 healthy
4. 跑 alembic migration(建 5 张表)
5. 启 API + Caddy(自动签 Let's Encrypt HTTPS)
6. 烟测 healthz

预计 5-10 分钟。第一次构建镜像最慢(下载 base image 1.5G)。

## 五、验证

```bash
# 在服务器上 — 内部检查
curl -fsS http://localhost:8000/healthz
# 期望: {"status":"ok","version":"0.0.1"}

docker compose -f infra/prod/docker-compose.prod.yml ps
# 期望: postgres / redis / api / caddy 都 Up
```

5 分钟后**在你 Mac 浏览器**:

- https://api.traillens.zorotreeking.online/healthz — API 存活
- https://api.traillens.zorotreeking.online/docs — Swagger UI(17 个 endpoint)
- https://api.traillens.zorotreeking.online/readyz — 深度检查(看 DB/Redis 都 ok)

第一次访问 Caddy 会自动找 Let's Encrypt 签证书,**前 30 秒可能慢**,之后秒回。

## 六、常见问题

| 问题 | 解决 |
|---|---|
| `dnf install docker-ce` 报 conflict | 先卸旧的:`dnf remove -y podman buildah` 再装 |
| `Cannot connect to the Docker daemon` | `systemctl start docker;systemctl enable docker` |
| Caddy 签证书失败 / 一直 PENDING | 1) 80 端口要放行(已验证 ✓);2) 域名解析要生效(已验证 ✓);3) 看日志 `docker compose logs caddy` |
| API 起来但 502 | `docker compose logs api`,90% 是 .env 漏填了什么 |
| `pg_isready` 一直不 ready | 第一次启动需要 init schema,等 30 秒;还不行看 `docker compose logs postgres` |

## 七、安全清单(强烈建议立刻做)

```bash
# 1) 腾讯云控制台 → 安全组 → 只放 22 (你 IP) / 80 / 443
#    其它端口全关(数据库 / Redis 不应公网暴露)

# 2) SSH 改成密钥登录,禁止密码
nano /etc/ssh/sshd_config
# 改:PasswordAuthentication no
systemctl restart sshd

# 3) 装 fail2ban(防 SSH 暴力破解)
dnf install -y epel-release
dnf install -y fail2ban
systemctl enable --now fail2ban

# 4) 自动安全更新
dnf install -y dnf-automatic
systemctl enable --now dnf-automatic.timer

# 5) .env 文件 chmod 600
chmod 600 /opt/traillens/.env
```

## 八、升级 / 回滚

```bash
# 升级(我每次 push 新代码后)
cd /opt/traillens && git pull && bash infra/prod/deploy.sh

# 回滚到上一版
git log --oneline -5
git checkout <要回到的 commit hash>
bash infra/prod/deploy.sh

# 查日志
docker compose -f infra/prod/docker-compose.prod.yml logs -f api --tail 100
```

## 九、备份(每周自动)

```bash
# 在 /opt/traillens/scripts/ 加个备份脚本
mkdir -p /opt/backup
cat > /opt/backup/backup.sh <<'EOF'
#!/bin/bash
DATE=$(date +%Y%m%d-%H%M)
cd /opt/traillens
docker compose -f infra/prod/docker-compose.prod.yml exec -T postgres \
  pg_dump -U traillens traillens | gzip > /opt/backup/db-$DATE.sql.gz
# 保留最近 7 天
find /opt/backup -name "db-*.sql.gz" -mtime +7 -delete
EOF
chmod +x /opt/backup/backup.sh

# 加到 crontab(每天凌晨 3 点)
(crontab -l 2>/dev/null; echo "0 3 * * * /opt/backup/backup.sh") | crontab -
```

## 十、与本地开发的关系

- **生产**:CVM 上的 `/opt/traillens` — 用户访问;你不直接改这里的代码
- **本地**:你 Mac 上的 `/Users/liuzf/Documents/Zoro_AI/TrailLens` — 你改代码 + git push
- **流程**:本地改 → `git push` → ssh CVM → `git pull && bash infra/prod/deploy.sh`

我下一步可以加 **GitHub Actions 自动部署**(push 到 main → 自动 ssh CVM 跑 deploy.sh),需要把 CVM 的 SSH 私钥放到 GitHub Secrets。
