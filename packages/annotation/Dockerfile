# 极简 stdlib http.server 镜像 — 仅依赖 python:3.11-slim
FROM python:3.11-slim
WORKDIR /app

# 拷贝代码 + 静态资源 + 照片(打包进镜像,改照片要重 build)
COPY packages/annotation/server/ /app/server/
COPY packages/annotation/static/ /app/static/
COPY packages/annotation/photos/ /app/photos/

# data 初始内容(prefill 等)烘进镜像;docker named volume 第一次 mount 时
# 会把镜像里的 /app/data 内容拷进 volume,之后由 volume 持久化覆盖
COPY packages/annotation/data/ /app/data/

ENV PORT=5555
ENV HOST=0.0.0.0
EXPOSE 5555

CMD ["python", "/app/server/serve.py"]
