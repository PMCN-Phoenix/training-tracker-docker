# -*- coding: utf-8 -*-
"""打印每个精选视频的 top 评论（按点赞排序）。"""
import json
from pathlib import Path
CMT = Path(r"D:\11.project\iwen-codex\codex-list\training-tracker-docker\docs\可控小成功与进度评判调研\原始数据\B站\评论")

for f in sorted(CMT.glob("*.json")):
    d = json.loads(f.read_text(encoding="utf-8"))
    print(f"\n=== {d['bvid']} | {d['title'][:50]} | total={d['count']} ===")
    cs = sorted(d["comments"], key=lambda x: -x.get("like",0))[:10]
    for c in cs:
        print(f"  [{c['like']:>5}赞] {c['uname']}: {c['message'][:120].replace(chr(10),' ')}")
        for sub in sorted(c.get("subs",[]), key=lambda x:-x.get("like",0))[:2]:
            print(f"        ↳ [{sub['like']:>3}] {sub['uname']}: {sub['message'][:100].replace(chr(10),' ')}")
