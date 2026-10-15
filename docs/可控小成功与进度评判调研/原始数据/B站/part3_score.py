# -*- coding: utf-8 -*-
"""对搜索结果打分，输出按主题分组的 top 候选。"""
import json, re
from pathlib import Path
from collections import defaultdict

OUT = Path(r"D:\11.project\iwen-codex\codex-list\training-tracker-docker\docs\可控小成功与进度评判调研\原始数据\B站")
data = json.loads((OUT / "搜索清单.json").read_text(encoding="utf-8"))
vids = data["videos"]

# 主题词权重（标题+简介里命中即加分）
THEMES = {
    "进度可观测性": [
        ("进度", 3), ("追踪", 3), ("日志", 3), ("台账", 3), ("账本", 3),
        ("指标", 3), ("监控", 3), ("leading", 2), ("滞后", 2), ("前置", 2),
        ("RPE", 3), ("反馈", 2), ("仪表盘", 2), ("可视化", 3), ("记录", 2),
    ],
    "小成功小目标": [
        ("小胜利", 4), ("小成功", 4), ("小目标", 3), ("微习惯", 4),
        ("渐进", 2), ("积少成多", 3), ("微小进步", 3), ("小步", 2),
    ],
    "方法论清单": [
        ("5x5", 4), ("三分化", 4), ("3分化", 4), ("线性计划", 4),
        ("周期化", 3), ("训练计划", 2), ("清单", 3), ("方法论", 2),
    ],
    "定期测试": [
        ("PR测试", 4), ("测试周期", 4), ("段位测试", 3), ("复测", 3),
        ("PR 周期", 3), ("定期测试", 3),
    ],
    "虚假进步反面": [
        ("垃圾容量", 5), ("无效训练", 4), ("刷指标", 4), ("伪进步", 4),
        ("Goodhart", 5), ("vanity", 4), ("假努力", 3), ("自我感动", 3),
        ("练习不等于", 4), ("练习≠", 4),
    ],
    "从零构建系统": [
        ("搭建", 3), ("自己做", 2), ("个人系统", 3), ("训练系统", 3),
        ("数据分析", 2), ("自定义", 2), ("excel", 2), ("表格", 2),
    ],
}

def score(v):
    text = (v["title"] + " " + v.get("description","")).lower()
    s = 0.0
    hit_themes = defaultdict(float)
    for theme, kws in THEMES.items():
        for kw, w in kws:
            if kw.lower() in text:
                s += w
                hit_themes[theme] += w
    # 播放量
    p = v.get("play", 0) or 0
    if p > 500000: s += 3
    elif p > 100000: s += 2
    elif p > 30000: s += 1
    elif p < 1000: s -= 2
    # 时长：3-30 分钟最佳
    d = v.get("dur_s", 0)
    if d < 90: s -= 3
    elif d < 180: s -= 1
    elif d > 3600: s -= 1
    # 关键词命中次数
    s += min(len(v["_from_kw"]), 5) * 0.5
    return s, dict(hit_themes)

ranked = []
for v in vids:
    s, themes = score(v)
    ranked.append((s, themes, v))
ranked.sort(key=lambda x: -x[0])

# 输出整体 top 60
print("=== 整体 Top 60 ===")
for s, themes, v in ranked[:60]:
    th = ",".join(f"{k}:{int(x)}" for k,x in sorted(themes.items(), key=lambda x:-x[1])[:2])
    print(f"{s:6.1f} | {v['bvid']} | {v['duration']:>8} | play={v.get('play',0):>8} | {v['title'][:50]} | {th}")

# 按主题各自 top 8
print("\n\n=== 分主题 Top ===")
for theme in THEMES:
    print(f"\n--- {theme} ---")
    picked = [x for x in ranked if x[1].get(theme,0) > 0]
    for s, themes, v in picked[:8]:
        print(f"  {s:6.1f} | {v['bvid']} | {v['duration']:>8} | play={v.get('play',0):>8} | {v['title'][:55]}")

# 落盘 top 100 供人工选
top100 = []
for s, themes, v in ranked[:150]:
    top100.append({"score": round(s,1), "themes": themes, **{k:v[k] for k in ["bvid","title","author","play","duration","dur_s","description","_from_kw"]}})
(OUT / "打分Top150.json").write_text(json.dumps(top100, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"\n[done] top150 -> 打分Top150.json")
