"""traillens-exif: 把 RAW/JPG 的 EXIF 元数据暴露为 MCP 工具。

公开两类入口:
1. CLI / stdio MCP server (`python -m traillens_exif`)
2. 纯函数 `extract_exif(path) -> dict`,供 agent 内进程调用与单测。
"""

from .core import EXIF_FIELDS, ExifResult, extract_exif

__all__ = ["EXIF_FIELDS", "ExifResult", "extract_exif"]
__version__ = "0.0.1"
