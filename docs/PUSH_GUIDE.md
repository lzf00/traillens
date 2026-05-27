# Push 到 GitHub 指引

本地已 init 为独立 git repo,16 个 commit(1 init + 15 PR)就绪。

## 选项 A:GitHub(推荐 — 国际曝光 / build-in-public)

```bash
# 1. 在 https://github.com/new 创建空 repo(不要勾任何 README/license,会冲突)
#    建议:org "traillens"(可注册),repo "traillens"

# 2. 关联 remote 并 push
cd /Users/liuzf/Documents/Zoro_AI/TrailLens
git remote add origin git@github.com:<你的-org>/traillens.git
git push -u origin main

# 3. 配置 repo 设置(在 GitHub 网页上):
#    - About → website: https://traillens.zorotreeking.online
#    - Topics: ai-agent, mcp, langgraph, photography, mllm, q-align
#    - Branch protection: main 必须 PR + CI 通过
```

## 选项 B:同时镜像到 Gitee(国内访问加速)

```bash
git remote set-url --add --push origin git@gitee.com:<你的-用户名>/traillens.git
git remote set-url --add --push origin git@github.com:<你的-org>/traillens.git
git push origin main
# → 一次 push 同步到两边
```

## 选项 C:阿里云 codeup(企业可见 / 不公开)

```bash
git remote add origin https://codeup.aliyun.com/<id>/traillens/traillens.git
git push -u origin main
```

## 验证

```bash
git log --oneline    # 应看到 16 条
# 6cbcdcb docs: CHANGELOG + ...
# ...
# 4be4428 chore: init project hygiene
```

## 后续 PR 工作流

```bash
git checkout -b feat/sprint-2-data-annotation
# ...写代码...
git push -u origin feat/sprint-2-data-annotation
# 在 GitHub 开 PR → CI 跑 → review → merge
```
