"""traillens-sunmoon: 日出/日落 + 蓝/金时间 + 月相 MCP server。

公开:
    sun_moon_times(lat, lon, date) -> dict       # 与 agents.tools.clients 同签名
    moon_phase(date) -> dict
"""

from .core import OUTPUT_FIELDS, moon_phase, sun_moon_times

__all__ = ["OUTPUT_FIELDS", "moon_phase", "sun_moon_times"]
__version__ = "0.0.1"
