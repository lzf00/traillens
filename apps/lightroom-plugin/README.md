# TrailLens — Lightroom Classic Plugin

> 把 TrailLens 选片结果一键导入 Lightroom 的 collection。
> 这是摄影师群体的核心付费转化点(参考 Aftershoot 的成功路径)。

## 安装(开发模式)

1. 打开 Lightroom Classic
2. File → Plug-in Manager → Add → 选择 `apps/lightroom-plugin/TrailLens.lrdevplugin`
3. 在右下角 Export 面板看到 "TrailLens — Import Curated Set"

## 用户流程

```
1) 用户在 TrailLens web 跑完 trail → 导出菜单选 "Open in Lightroom"
2) 浏览器调用 LR 协议 URL: lightroom://traillens?trail_id=xxx
3) 插件接收 → 拉 /v1/trails/xxx/photos?verdict=keep → 下载到本地缓存
4) 写入 LR catalog,创建名为 "TrailLens · {trail.name}" 的 collection
5) Star rating 按 aesthetic.overall 映射:>=8 → 5★, >=6 → 4★, >=4 → 3★
6) Label 按 verdict 染色:keep=green, review=yellow
```

## Adobe LrSDK 注册

- 免费,只需 Adobe ID
- https://partners.adobe.com/exchangeprogram/creativecloud/ 注册 partner
- 提交 plugin 走 marketplace 审核(2-4 周)

## Lua 开发资源

- 官方文档:https://www.adobe.com/devnet/photoshoplightroom.html
- SDK 下载:https://www.adobe.io/photoshop/lightroom-classic/
- 参考:[`LrTasks`](https://www.adobe.io/lightroom/lightroom-cc/api/LrTasks.html) 是异步入口

## 当前状态(2026-05-26)

骨架:
- Info.lua ✓
- TrailLensExport.lua ✓ (导出菜单入口)
- TrailLensApi.lua ✓ (HTTP 客户端)
- TrailLensImport.lua _TODO Sprint 6_ (真正的 catalog 写入)
