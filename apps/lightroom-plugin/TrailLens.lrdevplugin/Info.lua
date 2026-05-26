--[[
  TrailLens — Lightroom Classic Plugin manifest。
  LrSDK 6+ 兼容。详见 https://www.adobe.com/devnet/photoshoplightroom.html

  Sprint 6 末:把 _TODO 项替换为真实实现。
]]

return {
  LrSdkVersion = 6.0,
  LrSdkMinimumVersion = 6.0,
  LrToolkitIdentifier = "app.traillens.lightroom",
  LrPluginName = "TrailLens",
  LrPluginInfoUrl = "https://traillens.app",

  -- 出现在 File → Plug-in Extras 菜单
  LrExportMenuItems = {
    {
      title = "TrailLens — Import Curated Set",
      file = "TrailLensImport.lua",
    },
  },

  -- 出现在 Library → Plug-in Extras 菜单
  LrLibraryMenuItems = {
    {
      title = "Open TrailLens",
      file = "OpenTrailLens.lua",
    },
  },

  -- 在 Preferences 看到这个 plugin
  LrPluginInfoProvider = "PluginInfoProvider.lua",

  -- 注册自定义 URL handler:lightroom://traillens?trail_id=xxx
  LrInitPlugin = "PluginInit.lua",

  VERSION = { major = 0, minor = 0, revision = 1, build = 0 },
}
