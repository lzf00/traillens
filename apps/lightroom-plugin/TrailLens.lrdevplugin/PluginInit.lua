--[[
  插件加载时调用。这里仅做基础初始化。
  Sprint 6 末注册 lightroom:// URL handler 实现"从浏览器 →LR 一键".
]]

local prefs = import "LrPrefs".prefsForPlugin()
prefs.apiBase = prefs.apiBase or "https://api.traillens.zorotreeking.online"
prefs.webBase = prefs.webBase or "https://traillens.zorotreeking.online"
