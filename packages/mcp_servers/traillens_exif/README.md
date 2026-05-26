# traillens-exif

> 把照片的 EXIF 元数据通过 [Model Context Protocol](https://modelcontextprotocol.io) 暴露给 LLM 客户端
> (Claude Desktop / Cursor / ChatGPT Apps / 自研 agent)。

TrailLens 项目族的第一个独立 MCP server。
设计目标:**摄影师真正用得到的字段优先于完备性**——只解析 8 个字段(焦距/光圈/ISO/快门/拍摄时间/GPS×2/机型),不解析厂商私有标签。

## 工具

| Tool | 入参 | 出参(关键字段) |
|---|---|---|
| `read_exif` | `path: string` | `focal_length_mm, aperture_f, iso, shutter, captured_at, gps_lat, gps_lon, camera_model` |
| `summarize_batch` | `paths: string[]` | `n_photos, focal_range_mm, iso_range, gps_bbox, cameras` |

返回值与 [`traillens_agents.state.schema.ExifMeta`](../../agents/traillens_agents/state/schema.py) 严格对齐——保证在 TrailLens agent 里可零成本消费。

## 在 Claude Desktop 中安装

编辑 `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "traillens-exif": {
      "command": "uvx",
      "args": ["traillens-exif"]
    }
  }
}
```

或者本地开发模式:

```json
{
  "mcpServers": {
    "traillens-exif": {
      "command": "python",
      "args": ["-m", "traillens_exif"],
      "cwd": "/abs/path/to/TrailLens/packages/mcp_servers/traillens_exif"
    }
  }
}
```

## 本地开发

```bash
# 装核心依赖(Pillow)
pip install -e .

# 装 MCP SDK(发布到 Claude Desktop 前)
pip install -e ".[mcp]"

# 跑单元测试
python -m unittest discover ../../tests -v
```

## 设计抉择

- **Pillow 优先,无 Pillow 也能跑(只是字段全 None)**——保持 TrailLens 一贯的"零依赖 fallback"哲学。
- **不依赖 mcp SDK 也可启动**:无 SDK 时启动手写最小 JSON-RPC over stdio loop,仅供本地 dev 排错;生产请装 `[mcp]` extra。
- **返回 schema 由 contract test 守护**:`tests/test_exif_server.py::TestContract6` 断言 EXIF_FIELDS == ExifMeta 字段。任何一侧改字段名,CI 红。

## License

MIT
