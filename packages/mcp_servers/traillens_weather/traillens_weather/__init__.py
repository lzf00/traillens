"""traillens-weather: 天气查询 MCP server(Open-Meteo 代理)。

公开:
    weather_at(lat, lon, date=None) -> dict   # 与 agents.tools.clients.fetch_weather 兼容
    forecast(lat, lon, days=3) -> dict
"""

from .core import forecast, weather_at

__all__ = ["forecast", "weather_at"]
__version__ = "0.0.1"
