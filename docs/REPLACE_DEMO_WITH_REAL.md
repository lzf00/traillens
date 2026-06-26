# 把 demo trail 换成你的真徒步照片

> 5 分钟操作。**让 demo 用你真相机原片**(带 EXIF),游记会显示真焦段/光圈/ISO,
> 不再是 mock 的"Sony α7R IV"。这是 build-in-public 的"真"。

## 你需要

- 5-15 张你**相机原片**(jpg/jpeg/raw 都行,raw 会被存原文件)
- 这些原片**未经 web 平台压缩**(微信/小红书会剥 EXIF)
- 一个能跑 Python 3.11 的环境

## 步骤

### 1. 把照片放到本地一个目录

```bash
mkdir -p ~/traillens-real-trail
cp ~/Pictures/2026_yala/*.jpg ~/traillens-real-trail/
```

### 2. 用 CLI seed 上传 + 跑 Run

```bash
cd /Users/liuzf/Documents/Zoro_AI/TrailLens

python3 scripts/cli.py seed \
  --base https://traillens.zorotreeking.online \
  --email demo@traillens-builtinpublic.com \
  --password BuildInPublic2026 \
  --trail-name "2026.07 雅拉雪山实拍" \
  --location "四川 · 雅拉雪山自然保护区" \
  --photo-dir ~/traillens-real-trail \
  --count 8
```

跑完输出 trail_id 和 share URL,等约 2 分钟豆包跑分。

### 3. (可选)删掉旧 demo trail

新 trail 会自动成为 `/_demo/public` 的选择(按 photo_count 排序)。
要让旧 trail 不再被选到:

```bash
ssh root@110.40.142.199 'docker exec traillens-pg psql -U traillens -d traillens \
  -c "DELETE FROM trails WHERE name LIKE '\''Demo · 风光大片%'\'';"'
```

### 4. 验证

```bash
curl -sS https://traillens.zorotreeking.online/v1/trails/_demo/public \
  | python3 -m json.tool | head -10
```

应当看到你的 trail_name + 真 photo_count。

打开 `https://traillens.zorotreeking.online/trails/demo` 看 share 页 Hero 是不是你的照片。

### 5. (推荐)更新 README 截图

```bash
python3 scripts/record_demo.py
git add docs/screenshots/demo.gif docs/screenshots/demo.mp4
git commit -m "chore: re-record demo with real photos"
git push
```

## 为什么这件事重要

PRODUCT_PLAN 一直强调"自研 + build in public"。但 demo 用 Pexels stock 是**演示真**
而非**作品真**。用你自己的徒步照片,让访问者看到:

- 你真去过那地方(GPS 在 EXIF 里)
- 你真用 Sony α7R IV / Fuji X-T5 / 不管什么相机(机型在 EXIF)
- 你跑过这个产品给自己用(而不是只为了 demo)

这种 "founder dogfooding" 信号在 build-in-public 圈子里很重要 — 决定别人是否信你。
