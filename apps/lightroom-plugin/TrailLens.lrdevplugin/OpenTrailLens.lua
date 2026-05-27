--[[
  Library 菜单的便利项:在浏览器打开当前 catalog 对应的 web app。
]]

local LrHttp = import "LrHttp"
local prefs = import "LrPrefs".prefsForPlugin()

local webBase = (prefs.webBase or "https://traillens.zorotreeking.online")
LrHttp.openUrlInBrowser(webBase .. "/app/trails")
