# traillens-weather

MCP server: 天气查询(Open-Meteo 代理)。**无需 API key**,Open-Meteo 对个人/开源项目免费。

## 工具

| Tool | 入参 | 出参关键字段 |
|---|---|---|
| `weather_at` | `lat, lon, date?` | `summary, weather_label, cloud_cover, visibility_km, temperature_c` |
| `forecast` | `lat, lon, days=3` | `days[]: {date, weather_label, t_max_c, t_min_c, precip_mm, sunrise, sunset}` |

返回兼容 [`traillens_agents.tools.clients.fetch_weather`](../../agents/traillens_agents/tools/clients.py)。

## 设计

- 标准库 urllib(无 requests/httpx 依赖)。
- 网络失败返回 `source: "stub"`,不抛异常,Agent 不会被外部依赖打断。
- WMO weather code 映射到中文摄影友好描述。

## License

MIT
