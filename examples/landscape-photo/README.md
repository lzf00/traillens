# Example: landscape-photo (TrailLens)

> 即仓库根目录的本体。把它当作"用 AgentSaaS template 做出来的第一个 app"。

## Live

- 在线: https://traillens.zorotreeking.online
- 公开 demo: https://traillens.zorotreeking.online/trails/demo

## 业务实现的 3 处(其他全是模板)

| 文件 | 改了什么 |
|---|---|
| `packages/agents/traillens_agents/nodes/business.py` | culling/critic/story/planner/HumanReview 5 节点 |
| `apps/web/app/page.tsx` | Landing 文案 "AI darkroom for landscape photographers" |
| `apps/web/styles/globals.css` | 主色 aurora 绿(token `--accent-aurora`) |

## 数据模型

- `trails` 表 = 一次徒步 = AgentSaaS 抽象里的 `resource`
- `photos` 表 = 一张照片 = `item`(归属 resource,带 jsonb meta)
- `photos.aesthetic / critique / embedding` = 业务特定字段

## 工作流

```
用户上传 N 张照片 (trail.create + photos.upload)
  → agent.culling: OpenCV blur/exposure 过滤 + 豆包 vision 八维评分
  → agent.critic:  对 keep 的写 critique
  → agent.story:   拼 markdown 游记(EXIF 时序)
  → agent.planner: 出"下次再来"拍摄建议
  → persist + auto-embed → share 页 + Library 可搜
```
