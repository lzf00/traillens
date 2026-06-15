# Next.js 15 标准多阶段构建
FROM node:20-slim AS deps
WORKDIR /app

# 国内源加速(腾讯云内部镜像)
RUN npm config set registry https://mirrors.cloud.tencent.com/npm/

COPY apps/web/package.json ./
RUN npm install --legacy-peer-deps --no-audit --no-fund

# ---------- builder ----------
FROM node:20-slim AS builder
WORKDIR /app
RUN npm config set registry https://mirrors.cloud.tencent.com/npm/
COPY --from=deps /app/node_modules ./node_modules
COPY apps/web/ .

# Next.js 构建(失败时立刻终止,不容错)
ENV NEXT_TELEMETRY_DISABLED=1
RUN npm run build

# ---------- runtime ----------
FROM node:20-slim AS runtime
WORKDIR /app

RUN groupadd --system nodejs && useradd --system --gid nodejs --home /app nextjs

ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1
ENV PORT=3000
ENV HOSTNAME="0.0.0.0"

# 复制构建产物 + 必要的 runtime 文件
COPY --from=builder /app/public ./public
COPY --from=builder /app/.next ./.next
COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/package.json ./package.json
COPY --from=builder /app/next.config.mjs ./next.config.mjs
COPY --from=builder /app/messages ./messages
COPY --from=builder /app/i18n.ts ./i18n.ts

USER nextjs

EXPOSE 3000
HEALTHCHECK --interval=30s --timeout=3s --start-period=20s --retries=3 \
  CMD node -e "fetch('http://localhost:3000/').then(r => r.ok ? 0 : process.exit(1))" || exit 1

CMD ["npm", "start"]
