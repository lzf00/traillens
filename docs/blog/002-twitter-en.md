# Twitter/X thread (英文, 4 tweets)

> Copy each tweet (separator: ─── or numbered). Post as a thread.

---

**Tweet 1/4** (the hook)

I asked Doubao Vision to rate 5 of my landscape photos on 8 aesthetic
dimensions. Then I rated them myself.

Doubao vs me:
#1  8.3 → 9.0  (it underrated my favorite)
#2  7.8 → 7.5
#3  7.8 → 8.0
#4  7.1 → 6.5  (it overrated — I'm pickier)
#5  7.5 = 7.5

Mean signed bias: +0.00.
Mean absolute: ±0.36.

A thread on what this means 🧵

───

**Tweet 2/4** (the insight)

Doubao's vision model is "good enough" for landscapes overall — no
systematic bias.

But 2 of 5 photos show clear divergence:
- #1: it didn't see what makes this my favorite
- #4: it missed flaws I noticed

This is the entire reason PIAA (Personalized Image Aesthetics
Assessment) is a real research problem. We don't need just one
"correct" aesthetic model — we need ones that learn YOUR taste.

───

**Tweet 3/4** (the stack)

Stack I'm using for TrailLens:
- Doubao Vision (doubao-seed-2-0-pro) for prefill scoring
  Responses API, ¥0.02/photo
- 100-line Python http.server for annotation UI
- 8 dim schema aligned with ArtiMuse paper
  (composition, technical, emotion, gestalt, etc.)
- Tencent CVM + nginx + Lighthouse COS for storage

Zero proprietary deps — everything reproducible.

───

**Tweet 4/4** (the ask)

Plan for the next 4 weeks:
W1: collect 200+ of my own landscapes
W2: validate LoRA pipeline on Modal A10G
W3: full A100 training
W4: HF Space + reproducible eval

If you'd like to contribute 100 landscape photos of your own (kept
private, EXIF stripped) — DM me. Looking for 2-3 collaborators.

Code: github.com/lzf00/traillens

#buildinpublic #ml #computervision #photography
