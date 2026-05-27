# 把照片放这里

> 这个目录被 `.gitignore` 排除 — 照片不会被 commit 到 GitHub。
> 安心放,自动剥 GPS 后才会用作训练数据。

## 怎么放(任选一种)

### 方式 A:macOS Finder 拖拽(最简单)

1. 打开 Finder
2. 拷一段路径:`/Users/liuzf/Documents/Zoro_AI/TrailLens/packages/annotation/photos/`
3. `Cmd+Shift+G` 粘贴跳转
4. 把照片直接拖进来

### 方式 B:终端 cp

```bash
# 假设你照片在 ~/Pictures/landscape/
cp ~/Pictures/landscape/*.jpg \
   /Users/liuzf/Documents/Zoro_AI/TrailLens/packages/annotation/photos/

# 或一次性多目录
find ~/Pictures -name "*.jpg" -path "*landscape*" \
  -exec cp {} /Users/liuzf/Documents/Zoro_AI/TrailLens/packages/annotation/photos/ \;
```

## 对照片的要求(宽松)

- ✅ **任何风光照**:山、海、湖、草原、城市夜景、星空都行
- ✅ **任何相机**:手机、单反、微单
- ✅ **格式**:jpg / jpeg / png(raw 太大,先转 jpg)
- ✅ **分辨率**:最低短边 800px
- ✅ **数量**:30 张就能开始 sprint2 验证;200 张能做小批量训练;1000 张是正式训练目标
- ✅ **质量分布**:**好+中+差都要**(让模型学到差异),不要全是精选

## 放完之后告诉我

回我"放好了 N 张",我立刻跑:

```bash
make sprint2
# 自动:
#   ① 检查环境
#   ② 剥掉所有 EXIF GPS(隐私保护)
#   ③ 用豆包做 8 维预打分
#   ④ 启动标注 server(localhost:5555)
#   ⑤ 你按 1-9 校准,每张 30 秒
```

## 注意

- `.gitignore` 已经把 `photos/*` 排除 — 不会被 push 到 GitHub
- 删除 → 直接 `rm photos/*.jpg`(或 Finder 拖到废纸篓)
- 标注完成后想清空:`make clean-photos`(我可以加这个 target)
