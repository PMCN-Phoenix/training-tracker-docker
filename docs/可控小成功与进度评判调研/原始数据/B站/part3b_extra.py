# -*- coding: utf-8 -*-
"""补充筛选：按特定关键词找 PR测试/刻意练习/段位/反馈。"""
import json
from pathlib import Path
OUT = Path(r"D:\11.project\iwen-codex\codex-list\training-tracker-docker\docs\可控小成功与进度评判调研\原始数据\B站")
data = json.loads((OUT / "搜索清单.json").read_text(encoding="utf-8"))
vids = data["videos"]

QUERIES = {
    "PR测试/复测": ["PR", "复测", "测试周", "deload", "减载", "peak", "峰值周"],
    "刻意练习/反馈": ["刻意练习", "反馈", "动作质量", "技术动作", "纠错"],
    "段位/Aim": ["段位", "aim", "kovaak", "练枪", "fps 训练", "viscose"],
    "小胜利/心理学": ["小胜利", "心流", "掌控感", "胜任感", "自我效能", "多巴胺"],
    "假努力/打卡": ["打卡", "假努力", "自我感动", "仪式感"],
}

for label, kws in QUERIES.items():
    print(f"\n=== {label} ===")
    hits = []
    for v in vids:
        text = (v["title"] + " " + v.get("description","")).lower()
        score = sum(1 for k in kws if k.lower() in text)
        if score > 0:
            hits.append((score, v))
    hits.sort(key=lambda x: (-x[0], -(x[1].get("play") or 0)))
    for score, v in hits[:10]:
        print(f"  {v['bvid']} | {v['duration']:>8} | play={v.get('play',0):>8} | {v['title'][:60]}")
