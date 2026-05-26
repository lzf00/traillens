--[[
  Preferences 面板:让用户填 API base + token。
]]

local LrView = import "LrView"
local prefs = import "LrPrefs".prefsForPlugin()

return {
  sectionsForTopOfDialog = function(f, props)
    return {
      {
        title = "TrailLens 连接设置",
        f:row {
          f:static_text { title = "API Base:", width = 80 },
          f:edit_field { value = LrView.bind { object = prefs, key = "apiBase" }, width = 320 },
        },
        f:row {
          f:static_text { title = "Bearer Token:", width = 80 },
          f:password_field { value = LrView.bind { object = prefs, key = "token" }, width = 320 },
        },
        f:row {
          f:static_text {
            title = "从 traillens.app/app/settings 复制 token",
            text_color = import "LrColor"(0.5, 0.5, 0.5),
          },
        },
      },
    }
  end,
}
