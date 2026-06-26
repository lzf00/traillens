# Example: recipe-helper

> 用同一个 AgentSaaS template 做的另一个 app:**"我有这些食材,推荐 3 道菜"**。
> 当前只有 stub 结构,实际跑通是 C Phase 3 工作。

## 业务定义

| 抽象 | 对应 |
|---|---|
| `resource` | session(一次做菜会话) |
| `item` | dish(候选菜品) |
| **agent 1** `search` | 用户输入食材 → 搜可做的菜(中餐/西餐/粤菜) |
| **agent 2** `recipe-gen` | 对每道候选生成步骤 + 配料表 + 难度 |
| **agent 3** `nutrition` | 算热量 / 蛋白质 / 适合谁吃 |
| 公开 demo | `/sessions/demo` 显示几道家常菜推荐 |

## fork 这个 example 你需要改什么

(假设已经跑过 `scripts/init_template.sh --apply` 把 traillens → recipe-helper)

```python
# packages/agents/recipe_helper_agents/nodes/business.py
def search_node(state: GraphState) -> dict:
    """根据用户输入食材搜可做的菜。"""
    ingredients = state.input_text   # ["土豆", "牛肉", "胡萝卜"]
    candidates = clients.call_doubao(f"用 {ingredients} 能做哪些菜?给 5 个候选")
    return {"items": [Dish(name=c) for c in candidates]}

def recipe_node(state: GraphState) -> dict:
    """对每道候选写步骤 + 难度。"""
    for d in state.items:
        d.recipe = clients.call_doubao(f"如何做 {d.name}?写步骤 + 难度 1-5")
    return {"items": state.items}

def nutrition_node(state: GraphState) -> dict:
    """算营养信息。"""
    for d in state.kept_items():
        d.nutrition = nutri_api(d.recipe)
    return {"items": state.items}
```

```css
/* apps/web/styles/globals.css — 改主色 */
--accent-primary: #E94B3C;   /* tomato 红 替代 aurora 绿 */
```

```tsx
// apps/web/app/page.tsx — Landing 文案
<h1>What's for dinner?</h1>
<p>把你冰箱里有的食材丢进去,AI 推荐 3 道菜 + 完整菜谱 + 营养信息</p>
```

**仅此 3 改**。其他(auth / DB / 上传 / SSE / 持久化 / 分享 / theme) 直接继承模板。

## 上线流程(假设 template 已经成熟)

```bash
git clone https://github.com/<you>/agentsaas-template recipe-helper
cd recipe-helper
./scripts/init_template.sh --apply  # 问 app/agents/domain
$EDITOR packages/agents/recipe_helper_agents/nodes/business.py  # 改 3 个 agent
cp .env.example .env && $EDITOR .env  # 填 LLM key
docker compose up -d
open http://localhost:3000
```

## 跟 landscape-photo 的相似度

90%+ 代码一致。差异仅在:
- agent 节点业务逻辑
- 数据 schema 命名(jsonb meta 装不同业务字段)
- Landing / share 页文案 + 颜色
