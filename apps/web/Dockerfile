# Next.js 15 standalone 多阶段构建
FROM node:20-slim AS deps
WORKDIR /app
RUN npm config set registry https://mirrors.cloud.tencent.com/npm/
COPY apps/web/package.json ./
RUN npm install --legacy-peer-deps --no-audit --no-fund

# ---------- builder ----------
FROM node:20-slim AS builder
WORKDIR /app
RUN npm config set registry https://mirrors.cloud.tencent.com/npm/
COPY --from=deps /app/node_modules ./node_modules
COPY apps/web/ .

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

# Next 15 standalone:server.js + 必要的最小 node_modules 自带
COPY --from=builder /app/public ./public
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static

USER nextjs

EXPOSE 3000
HEALTHCHECK --interval=30s --timeout=3s --start-period=20s --retries=3 \
  CMD node -e "fetch('http://localhost:3000/').then(r => r.ok ? 0 : process.exit(1))" || exit 1

CMD ["node", "server.js"]
