# -*- coding: utf-8 -*-
"""从原始搜索清单里捞反面/争议 + 各子问题候选，供人工精选。"""
import json, pathlib

OUT = pathlib.Path(r"D:\11.project\iwen-codex\codex-list\training-tracker-docker\docs\不确定性下的坚持调研\原始数据\B站")
d = json.loads((OUT / "搜索清单-原始.json").read_text(encoding="utf-8"))

groups = {
    "反面/放弃/沉没成本": ["沉没成本", "放弃", "执念", "执着", "过度", "耗死", "及时止损"],
    "倦怠/burnout/内耗": ["倦怠", "burnout", "内耗", "崩溃", "劝退", "躺平", "摆烂"],
    "不确定/焦虑/控制感": ["焦虑", "不确定", "控制感", "失控", "容忍"],
    "复盘": ["复盘", "反思"],
    "过程vs结果": ["过程", "享受"],
    "动机/长期主义/坚持": ["长期主义", "坚持", "动机", "意志力", "grit", "坚毅"],
    "成长型/自我效能": ["成长型", "固定型", "自我效能", "自信"],
}

for gname, kws in groups.items():
    print(f"\n===== {gname} =====")
    hits = [v for v in d if any(k in (v["title"] + v["description"]) for k in kws) and v["play"] > 8000]
    hits.sort(key=lambda x: -x["_score"])
    for v in hits[:10]:
        print(f"  {v['_score']:5.1f} | p={v['play']:>8} | {v['duration']:>5}s | {v['title'][:44]} | {v['bvid']}")
