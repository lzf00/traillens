"""/v1/recipe — Example: recipe-helper 的最简 hello-world 端点。

调用 examples/recipe-helper/agents 的 3 节点串行跑 → 返回推荐 markdown。
证明 template 抽象:同一 template 上跑另一业务 = 一个新路由 + 3 节点。
"""

from __future__ import annotations

import sys
from pathlib import Path

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from ..deps import CurrentUser, get_current_user

# 允许 import examples/recipe-helper/agents(monorepo pattern)
_EX = Path(__file__).resolve().parents[3] / "examples" / "recipe-helper"
if str(_EX) not in sys.path:
    sys.path.insert(0, str(_EX))

router = APIRouter()


class RecipeSuggestBody(BaseModel):
    ingredients: str = Field(..., min_length=1, max_length=200,
                              description="逗号或空格分隔,如 '土豆 牛肉 胡萝卜'")


class DishOut(BaseModel):
    name: str
    difficulty: int | None = None
    recipe: str | None = None
    nutrition: dict | None = None


class RecipeSuggestOut(BaseModel):
    dishes: list[DishOut]
    travelogue_md: str


@router.post("/suggest", response_model=RecipeSuggestOut)
def suggest(
    body: RecipeSuggestBody,
    user: CurrentUser = Depends(get_current_user),
) -> RecipeSuggestOut:
    """接食材 → 走 recipe-helper 3 节点 → 返推荐 markdown。

    当前所有节点都是 stub(见 examples/recipe-helper/agents/business.py)。
    真接 LLM 是 Phase 3 工作。
    """
    from agents import RecipeState, search_node, recipe_node, nutrition_node  # type: ignore

    state = RecipeState(input_text=body.ingredients)
    state.items = search_node(state)["items"]
    state.items = recipe_node(state)["items"]
    nutri_out = nutrition_node(state)
    state.travelogue_md = nutri_out["travelogue_md"]

    return RecipeSuggestOut(
        dishes=[
            DishOut(name=d.name, difficulty=d.difficulty,
                    recipe=d.recipe, nutrition=d.nutrition)
            for d in state.items
        ],
        travelogue_md=state.travelogue_md,
    )
