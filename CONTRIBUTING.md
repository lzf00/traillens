# 贡献 TrailLens

> 5 分钟规则:从 clone 到 `make verify` 全绿,应该 < 5 分钟。
> 如果你跑超了,**这就是个 issue** — 麻烦在 [`#dev-experience`](https://github.com/your-handle/traillens/labels/dev-experience) 报告。

## 0. 5 分钟 onboarding

```bash
git clone https://github.com/your-handle/traillens
cd traillens
make verify       # ← 全套测试 + demo + 美学评估自检
```

不需要装 Docker / Postgres / Node — 这个命令应该 100% 跑通。如果不通,要么是你的 Python < 3.10,要么是我的问题。

## 1. 找一个 issue 开始

最好上手的:

- 🌱 [`good first issue`](https://github.com/your-handle/traillens/labels/good%20first%20issue) — 改 docs / 加 test / 修小 bug
- 📷 [`bias-audit`](https://github.com/your-handle/traillens/labels/bias-audit) — 找模型评错的照片(连用户都能贡献)
- 🛠️ [`mcp`](https://github.com/your-handle/traillens/labels/mcp) — 写新 MCP server(参考 traillens-exif 的 layout)

## 2. 分支 + commit 规范

```bash
git checkout -b <topic>/<short-slug>
# topic 范围:
#   feat   feature
#   fix    bug fix
#   chore  infra / build / deps
#   docs
#   refactor
#   test
#   perf
```

Commit 信息走 Conventional Commits:

```
feat(agents): add HITL interrupt support to culling node

Wires LangGraph's interrupt() into the human_review path so the user can
pause-resume from the web UI. Adds 2 contract tests for the resume path.

Closes #142
```

## 3. 写代码前先看的 3 份文档

1. [`docs/PRODUCT_PLAN.md`](docs/PRODUCT_PLAN.md) — 当前 sprint 在做什么
2. [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — 模块边界
3. [`tests/test_consistency.py`](tests/test_consistency.py) — 跨模块契约(改 schema 必须更新这里)

## 4. PR 检查清单(也在 [`.github/PULL_REQUEST_TEMPLATE.md`](.github/PULL_REQUEST_TEMPLATE.md))

- [ ] `make verify` 全绿
- [ ] 改 schema 同步更新 contract test
- [ ] 新功能有单测 / 契约测试
- [ ] UI 改动放截图
- [ ] 风险段说明回滚方法

## 5. 决策记录(ADR)

重大架构决策写到 `docs/PRODUCT_PLAN.md` 的"决策日志"附录(§附录 B)。
小决策直接在 PR 描述里讨论;讨论沉淀的结论搬到代码注释。

## 6. 行为准则

- **真诚优于客气**:有意见直接说;不要 "lgtm + 私下 dm 不同意"
- **代码不属于个人**:任何人都可以改任何文件
- **修改 RESEARCH/EVAL 前先 issue**:这两份文件影响外部信任,改动需要讨论
- **不容忍人身攻击**;有问题联系 hello@traillens.app

## 7. 翻译 / 国际化

中英文文档我们都接受 PR。规则:
- 代码 + 测试名 / commit message **永远英文**
- README / docs 中英都行,标题加上 `[zh]` 或 `[en]` 区分翻译版本
- 用户面向 UI 默认中文,英文 i18n 由 `next-intl` 管理

## 8. 数据贡献

风光照片样本是项目核心:
- 走 [data_concern issue 模板](.github/ISSUE_TEMPLATE/data_concern.yml) 提报模型错判的例子
- 想批量贡献标注?读 [docs/RECRUITMENT.md](docs/RECRUITMENT.md),邮件 hello@traillens.app

## 9. 如何被致谢

- 任何 merge 的 PR 都进 [CHANGELOG.md](CHANGELOG.md)
- 5+ PR 进 [README.md](README.md) Contributors 段
- 数据 / 算法贡献会在 arXiv preprint(如有)正式致谢
