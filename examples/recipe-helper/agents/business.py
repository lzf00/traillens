"""Recipe helper 的 3 个 agent 节点 stub。

对应 traillens_agents/nodes/business.py 的位置。fork 后你在这写业务逻辑。

state schema 简化版:
  input_text: str         用户输入食材,如 "土豆 牛肉 胡萝卜"
  items: list[Dish]       候选菜(每 Dish 有 name, recipe, nutrition)
  travelogue_md: str      最终推荐总结(用 story 节点位复用)

真实现要:
  - 换掉 stub_llm 调用为真 LLM
  - 加错误处理 + 限流
  - 每 Dish 加 uri(菜品配图)
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any


@dataclass
class Dish:
    name: str
    recipe: str | None = None
    nutrition: dict[str, Any] | None = None
    difficulty: int | None = None  # 1-5
    verdict: str | None = None  # "keep" / "skip" (类比 photo.verdict)


@dataclass
class RecipeState:
    input_text: str
    items: list[Dish] = field(default_factory=list)
    travelogue_md: str = ""

    def kept_items(self) -> list[Dish]:
        return [d for d in self.items if d.verdict == "keep"]


# --------------------------------------------------------------------------- #
# Agent 1: search — 用户输入食材 → 候选菜
# --------------------------------------------------------------------------- #
def search_node(state: RecipeState) -> dict:
    """[TODO] 换 stub 为真 LLM 调用(豆包 / DeepSeek)。"""
    # STUB: 假装豆包返 5 道候选
    candidates = [f"stub-dish-{i}" for i in range(5)]
    items = [Dish(name=c, verdict="keep") for c in candidates]
    return {"items": items, "messages": [{"role": "search", "content": f"找到 {len(items)} 道"}]}


# --------------------------------------------------------------------------- #
# Agent 2: recipe-gen — 对每道候选写步骤
# --------------------------------------------------------------------------- #
def recipe_node(state: RecipeState) -> dict:
    """[TODO] 真实现调 LLM 写详细步骤 + 难度评估。"""
    for d in state.items:
        d.recipe = f"stub 步骤:切、炒、煮、装盘"
        d.difficulty = 3
    return {"items": state.items, "messages": [{"role": "recipe", "content": "步骤生成完"}]}


# --------------------------------------------------------------------------- #
# Agent 3: nutrition — 算营养
# --------------------------------------------------------------------------- #
def nutrition_node(state: RecipeState) -> dict:
    """[TODO] 接 nutrition API 或本地食物数据库。"""
    for d in state.kept_items():
        d.nutrition = {"kcal": 500, "protein_g": 30, "carbs_g": 60}
    summary = "\n".join(
        f"- **{d.name}** · 难度 {d.difficulty}/5 · {d.nutrition['kcal']} kcal"
        for d in state.kept_items()
    )
    return {
        "items": state.items,
        "travelogue_md": f"# 今晚吃什么\n\n根据你的食材,推荐:\n\n{summary}",
        "messages": [{"role": "nutrition", "content": "营养算完"}],
    }
