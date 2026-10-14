# -*- coding: utf-8 -*-
"""打印每个视频的：元信息 + top10高赞主评论 + top3楼中楼。"""
import json, pathlib

OUT = pathlib.Path(r"D:\11.project\iwen-codex\codex-list\training-tracker-docker\docs\不确定性下的坚持调研\原始数据\B站")
d = json.loads((OUT / "深抓结果.json").read_text(encoding="utf-8"))

for bvid, v in d.items():
    print(f"\n{'='*70}")
    print(f"[{bvid}] {v['title']}")
    print(f"  UP={v['owner']} | dur={v['duration']}s | 字幕={v['subtitle_chars']}字 | 评论={v['comment_count']}")
    print(f"  desc: {(v.get('desc') or '')[:120]}")
    cs = sorted(v.get("comments") or [], key=lambda x: -x.get("like", 0))
    print(f"  --- 高赞主评论 top10 ---")
    for c in cs[:10]:
        msg = c["message"].replace("\n", " ")[:180]
        print(f"    [{c['like']:>4}赞 rcount={c['rcount']}] {c['uname']}: {msg}")
        for s in (c.get("subs") or [])[:3]:
            sm = s["message"].replace("\n", " ")[:120]
            print(f"        └[{s['like']:>3}] {s['uname']}: {sm}")
