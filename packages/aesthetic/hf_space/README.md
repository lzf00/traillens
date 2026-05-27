---
title: TrailLens — Landscape Aesthetic Scoring
emoji: ⛰️
colorFrom: green
colorTo: blue
sdk: gradio
sdk_version: 4.44.0
app_file: app.py
pinned: false
license: cc-by-nc-4.0
models:
  - traillens/qalign-landscape-lora-v0
---

# TrailLens — Landscape Aesthetic Scoring

Drop a landscape photo, get an 8-dim aesthetic breakdown.

Backbone: Q-Align(ICML 2024) + landscape LoRA fine-tuned on 1000 expert-labeled samples.

[Blog post](https://traillens.zorotreeking.online/blog/beyond-ava-landscape-aesthetics) · [Code](https://github.com/lzf00/traillens) · [Paper(WIP)]

## Caveats

This model is *not* an objective taste arbiter. It encodes a particular school of landscape aesthetics (traditional / Outdoor Photographer / National Geographic). It's biased toward certain styles. See [RESEARCH.md §3.3 Bias Statement](https://github.com/lzf00/traillens/blob/main/docs/RESEARCH.md).

For personalized scoring(PIAA),use the full TrailLens product at [traillens.zorotreeking.online](https://traillens.zorotreeking.online).
