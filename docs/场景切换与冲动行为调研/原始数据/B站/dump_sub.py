# -*- coding: utf-8 -*-
"""批量输出关键视频字幕（带时间戳）"""
import json, sys
from pathlib import Path

BASE = Path(r"D:\11.project\iwen-codex\codex-list\training-tracker-docker\docs\场景切换与冲动行为调研\原始数据\B站")
SUB_DIR = BASE / "字幕"

def fmt_ts(sec):
    m, s = divmod(int(sec), 60)
    h, m = divmod(m, 60)
    if h: return f"{h:02d}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"

def dump(bvid):
    p = SUB_DIR / f"{bvid}.json"
    if not p.exists():
        return f"[无字幕] {bvid}"
    segs = json.loads(p.read_text(encoding='utf-8'))
    return '\n'.join(f"[{fmt_ts(s['from'])}] {s['content']}" for s in segs)

targets = sys.argv[1:]
for bvid in targets:
    print("="*80)
    print(f"【{bvid}】")
    print("="*80)
    print(dump(bvid))
    print()
