--[[
  TrailLens HTTP API 客户端(供其它 .lua 调用)。

  端点:
    GET  /v1/trails/{id}                — 拿 trail 元数据
    GET  /v1/trails/{id}/photos         — 拿照片列表(含 verdict + aesthetic)
    GET  /v1/photos/{id}/download       — 拿原图二进制(用于落盘到 catalog)
]]

local LrHttp = import "LrHttp"
local LrTasks = import "LrTasks"
local JSON = require "JSON"  -- 第三方 lua-json,放在 lib/ 下,LrSDK 不自带

local prefs = import "LrPrefs".prefsForPlugin()

local M = {}

local function baseUrl()
  return prefs.apiBase or "https://api.traillens.app"
end

local function authHeaders()
  return {
    { field = "Authorization", value = "Bearer " .. (prefs.token or "") },
    { field = "Content-Type", value = "application/json" },
  }
end

--- 拉 trail 元数据(同步,从 LrTasks 内调用)。
function M.fetchTrail(trailId)
  local body, headers = LrHttp.get(baseUrl() .. "/v1/trails/" .. trailId, authHeaders())
  if not body then return nil, "no_response" end
  return JSON:decode(body)
end

--- 拉照片列表。
function M.fetchPhotos(trailId, verdict)
  local url = baseUrl() .. "/v1/trails/" .. trailId .. "/photos"
  if verdict then url = url .. "?verdict=" .. verdict end
  local body = LrHttp.get(url, authHeaders())
  if not body then return {} end
  return JSON:decode(body) or {}
end

--- 下载原图到本地路径。
function M.downloadPhoto(photoId, destPath)
  local url = baseUrl() .. "/v1/photos/" .. photoId .. "/download"
  local body, headers = LrHttp.get(url, authHeaders())
  if not body then return false, "download_failed" end
  local f = io.open(destPath, "wb")
  if not f then return false, "fs_open_failed" end
  f:write(body); f:close()
  return true
end

return M
