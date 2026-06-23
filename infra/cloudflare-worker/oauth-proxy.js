/**
 * TrailLens OAuth Proxy — 把国内服务器访问不到的 OAuth endpoint 通过 CF Worker 中转。
 *
 * 路由映射:
 *   /google/token       → https://oauth2.googleapis.com/token
 *   /google/userinfo    → https://www.googleapis.com/oauth2/v3/userinfo
 *   /github/token       → https://github.com/login/oauth/access_token
 *   /github/user        → https://api.github.com/user
 *
 * 部署:
 *   1. https://dash.cloudflare.com → Workers & Pages → Create
 *   2. 选 "Hello World" 模板,Worker 名: traillens-oauth-proxy
 *   3. Quick Edit / Edit Code → 把整个文件内容粘进去 → Save and Deploy
 *   4. 拿 URL: https://traillens-oauth-proxy.<your-account>.workers.dev
 *   5. 写入服务器 .env: OAUTH_PROXY_BASE=https://traillens-oauth-proxy.xxx.workers.dev
 *   6. 重启 api 容器
 */

const ROUTES = {
  "/google/token":    "https://oauth2.googleapis.com/token",
  "/google/userinfo": "https://www.googleapis.com/oauth2/v3/userinfo",
  "/github/token":    "https://github.com/login/oauth/access_token",
  "/github/user":     "https://api.github.com/user",
};

export default {
  async fetch(request) {
    const url = new URL(request.url);
    const target = ROUTES[url.pathname];
    if (!target) {
      return new Response(JSON.stringify({
        error: "unknown_route",
        path: url.pathname,
        available: Object.keys(ROUTES),
      }), {
        status: 404,
        headers: { "Content-Type": "application/json" },
      });
    }

    // 透传 method / headers / body
    const headers = new Headers(request.headers);
    // 去掉 CF 自动加的不该转发的头
    headers.delete("host");
    headers.delete("cf-connecting-ip");
    headers.delete("cf-ray");
    headers.delete("cf-visitor");
    headers.delete("x-forwarded-for");
    headers.delete("x-forwarded-proto");

    const init = {
      method: request.method,
      headers,
      body: ["GET", "HEAD"].includes(request.method) ? undefined : request.body,
      // CF Workers 默认 fetch 不跟 redirect,这里允许
      redirect: "follow",
    };

    try {
      const resp = await fetch(target, init);
      // 把响应原样返回
      const respHeaders = new Headers(resp.headers);
      respHeaders.set("access-control-allow-origin", "*");
      return new Response(resp.body, {
        status: resp.status,
        statusText: resp.statusText,
        headers: respHeaders,
      });
    } catch (e) {
      return new Response(JSON.stringify({ error: "upstream_failed", message: e.message }), {
        status: 502,
        headers: { "Content-Type": "application/json" },
      });
    }
  },
};
