--[[
  TrailLens Import — 用户点击 "TrailLens — Import Curated Set" 时入口。

  流程:
    1. 弹窗输入 trail_id(或从 prefs 读上次)
    2. 调 API 拿 keep 状态的照片列表
    3. 下载到本地缓存目录
    4. 创建 collection "TrailLens · {trail.name}"
    5. import 到 catalog,设置 star rating 与 color label
]]

local LrApplication = import "LrApplication"
local LrDialogs = import "LrDialogs"
local LrFunctionContext = import "LrFunctionContext"
local LrPathUtils = import "LrPathUtils"
local LrFileUtils = import "LrFileUtils"
local LrTasks = import "LrTasks"
local LrProgressScope = import "LrProgressScope"

local prefs = import "LrPrefs".prefsForPlugin()
local Api = require "TrailLensApi"

local CACHE_DIR = LrPathUtils.child(LrPathUtils.getStandardFilePath("temp"), "traillens-cache")
LrFileUtils.createAllDirectories(CACHE_DIR)

local function ratingFromAesthetic(overall)
  if overall == nil then return nil end
  if overall >= 8 then return 5 end
  if overall >= 6 then return 4 end
  if overall >= 4 then return 3 end
  if overall >= 2 then return 2 end
  return 1
end

local function colorLabelFromVerdict(verdict)
  if verdict == "keep" then return "green" end
  if verdict == "review" then return "yellow" end
  return "red"
end

LrFunctionContext.callWithContext("TrailLensImport", function(context)
  LrTasks.startAsyncTask(function()
    local trailId = LrDialogs.runOpenPanel({  -- 简化版:Sprint 6 改为文本输入
      title = "Enter TrailLens Trail ID",
      canChooseFiles = false, canChooseDirectories = false, canCreateDirectories = false,
    })
    if not trailId then return end

    local trail, err = Api.fetchTrail(trailId)
    if not trail then
      LrDialogs.message("TrailLens", "Failed to fetch trail: " .. (err or "?"))
      return
    end

    local photos = Api.fetchPhotos(trailId, "keep")
    if #photos == 0 then
      LrDialogs.message("TrailLens", "No KEEP photos in this trail.")
      return
    end

    local prog = LrProgressScope({ title = "TrailLens · " .. trail.name, functionContext = context })
    prog:setPortionComplete(0, #photos)

    local catalog = LrApplication.activeCatalog()
    catalog:withWriteAccessDo("TrailLens import", function()
      local collection = catalog:createCollection("TrailLens · " .. trail.name, nil, true)
      for i, p in ipairs(photos) do
        local localPath = LrPathUtils.child(CACHE_DIR, p.photo_id .. ".jpg")
        if not LrFileUtils.exists(localPath) then
          Api.downloadPhoto(p.photo_id, localPath)
        end
        local lrPhoto = catalog:addPhoto(localPath)
        if lrPhoto then
          collection:addPhotos({ lrPhoto })
          if p.aesthetic and p.aesthetic.overall then
            lrPhoto:setRawMetadata("rating", ratingFromAesthetic(p.aesthetic.overall))
          end
          lrPhoto:setRawMetadata("colorNameForLabel", colorLabelFromVerdict(p.verdict))
        end
        prog:setPortionComplete(i, #photos)
      end
    end)

    prog:done()
    LrDialogs.message("TrailLens", "Imported " .. #photos .. " photos into collection.")
  end)
end)
