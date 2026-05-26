# traillens-sunmoon

MCP server: 日出 / 日落 / 蓝时刻 / 金时刻 / 月相 —— Planner 节点的核心数据源,也是任何摄影 AI 都用得到的能力。

## 工具

| Tool | 入参 | 出参关键字段 |
|---|---|---|
| `sun_moon_times` | `lat, lon, date` | `sunrise, sunset, golden_hour_am, golden_hour_pm, blue_hour_am, blue_hour_pm` |
| `moon_phase` | `date` | `phase (0-1), illumination, label` |

返回兼容 [`traillens_agents.tools.clients.sun_moon_times`](../../agents/traillens_agents/tools/clients.py)。

## 双实现策略

- 默认零依赖,用 NOAA 太阳轨道公式纯 Python 实现(精度约 ±1 分钟)。
- 装 `pip install ".[precise]"` 后启用 astral,精度更高 + 考虑大气折射。

## 在 Claude Desktop

```json
{
  "mcpServers": {
    "traillens-sunmoon": {
      "command": "uvx",
      "args": ["traillens-sunmoon"]
    }
  }
}
```

## License

MIT
