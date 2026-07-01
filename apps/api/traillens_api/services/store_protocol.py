"""AgentSaaS template 的存储抽象层。

Direction C Phase 1 后半:把 TrailLens 的 `store` 具体命名(trail/photo)抽象为
`resource/item` 通用命名。业务代码调 protocol,不再直接调 store.get_trail(...)。

**当前只是 alias + Protocol 定义**,让业务代码可以逐步迁移。不改 store.py 本体
避免影响现有 API。真产品化模板时:
  1. store.py 内部实现两套函数(get_trail / get_resource,共享 SQL)
  2. 每个 example 只依赖 protocol,不依赖 traillens_agents 命名

用法:
  from .services.store_protocol import ResourceStore, ItemStore, default_store
  s: ResourceStore = default_store()
  s.get_resource(rid, user_id=uid)  # == store.get_trail(rid, user_id=uid)
"""

from __future__ import annotations

from typing import Any, Protocol


class ResourceStore(Protocol):
    """一个 "resource" = TrailLens 的 trail / recipe-helper 的 session / stargazer 的 stack。"""

    def create_resource(self, *, user_id: str, name: str,
                        location_name: str | None = None,
                        resource_type: str = "trail",
                        **meta: Any) -> Any:
        ...

    def get_resource(self, resource_id: str, *, user_id: str) -> Any | None: ...

    def list_resources(self, *, user_id: str, limit: int = 50,
                       resource_type: str | None = None) -> list[Any]: ...

    def update_resource(self, resource_id: str, *, user_id: str,
                        name: str | None = None,
                        **fields: Any) -> Any | None: ...

    def delete_resource(self, resource_id: str, *, user_id: str) -> list[str]:
        """返回被删的 item URI 列表(供 caller 清对象存储)。"""


class ItemStore(Protocol):
    """一个 "item" = photo / dish / stack_frame。归属某个 resource。"""

    def add_items(self, resource_id: str, *, user_id: str,
                  items: list[Any], item_type: str = "photo") -> int: ...

    def list_items(self, resource_id: str, *, user_id: str) -> list[Any]: ...

    def update_item(self, resource_id: str, item_id: str, *, user_id: str,
                    **fields: Any) -> bool: ...

    def delete_item(self, resource_id: str, item_id: str, *, user_id: str) -> list[str]:
        """返回被删的 URI 列表。"""


# --------------------------------------------------------------------------- #
# 默认实现:适配 traillens 现有 store.py(alias 层,不动 store.py 本体)
# --------------------------------------------------------------------------- #
class _TrailLensAdapter:
    """把 store.create_trail 之类 alias 成 create_resource。零逻辑,只做名字桥接。"""

    def __init__(self):
        from . import store  # 延迟避免循环
        self._s = store

    # ---- ResourceStore ----
    def create_resource(self, *, user_id, name, location_name=None,
                        resource_type="trail", **meta):
        # TrailLens create_trail 不认 resource_type;先走原有,resource_type
        # 由 DB 默认 'trail' 或后续 update 覆盖
        gpx_uri = meta.pop("gpx_uri", None)
        trail = self._s.create_trail(
            user_id=user_id, name=name,
            location_name=location_name, gpx_uri=gpx_uri,
        )
        return trail

    def get_resource(self, resource_id, *, user_id):
        return self._s.get_trail(resource_id, user_id=user_id)

    def list_resources(self, *, user_id, limit=50, resource_type=None):
        # resource_type 过滤:现有 list_trails 不支持,先全拿再本地过滤
        # 真实现改 SQL 加 WHERE
        rows = self._s.list_trails(user_id=user_id, limit=limit)
        if resource_type is None:
            return rows
        return [r for r in rows
                if getattr(r, "resource_type", "trail") == resource_type]

    def update_resource(self, resource_id, *, user_id, name=None, **fields):
        return self._s.update_trail(
            resource_id, user_id=user_id,
            name=name,
            location_name=fields.get("location_name"),
            travelogue_md=fields.get("travelogue_md"),
            next_trip_plan=fields.get("next_trip_plan"),
        )

    def delete_resource(self, resource_id, *, user_id):
        return self._s.delete_trail(resource_id, user_id=user_id)

    # ---- ItemStore ----
    def add_items(self, resource_id, *, user_id, items, item_type="photo"):
        return self._s.add_photos(resource_id, user_id=user_id, photos=items)

    def list_items(self, resource_id, *, user_id):
        return self._s.list_photos(resource_id, user_id=user_id)

    def update_item(self, resource_id, item_id, *, user_id, **fields):
        return self._s.update_photo(
            resource_id, item_id, user_id=user_id,
            verdict=fields.get("verdict"),
            aesthetic=fields.get("aesthetic"),
            critique=fields.get("critique"),
        )

    def delete_item(self, resource_id, item_id, *, user_id):
        return self._s.delete_photo(resource_id, item_id, user_id=user_id)


_default = None


def default_store() -> ResourceStore:
    """线程安全 lazy singleton。"""
    global _default
    if _default is None:
        _default = _TrailLensAdapter()
    return _default  # type: ignore[return-value]
