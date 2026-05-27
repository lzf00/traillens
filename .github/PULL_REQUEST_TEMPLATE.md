<!--
谢谢提 PR!
小 PR 是好 PR — 一次只解决一件事更容易过 review。
-->

## 这个 PR 做了什么

<!-- 一两句话。不要 copy commit message。 -->

## 为什么(关联 issue / 计划)

<!-- 链到 issue / PRODUCT_PLAN 章节 / Sprint 计划。
     比如:Closes #42 — 实现 PRODUCT_PLAN §3.1 M4 的决策时间线 -->

## 测试

- [ ] `make test` 全绿(39+ 测试)
- [ ] `make verify` 通过(含 agent demo + aesthetic demo-metric)
- [ ] 新增功能有对应单测 / 契约测试
- [ ] 改了 schema → 同步更新 `tests/test_consistency.py`

## 风险与回滚

<!--
  这次改动可能在生产打哪些"鼻血"?
  - 改 schema:旧 client 可能崩
  - 改 SSE 事件名:前端要同步改
  - 改 MCP tool 签名:Claude Desktop 用户要重启
  如果坏了,如何回滚?(一般 `git revert`,如果有 migration / 配置变更要写明)
-->

## Screenshots / 关键输出

<!-- UI 改动必须放截图;agent 行为改动放 message 流截图 -->
