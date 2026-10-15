# -*- coding: utf-8 -*-
"""提取评论区高赞评论"""
import json
from pathlib import Path

BASE = Path(r"D:\11.project\iwen-codex\codex-list\training-tracker-docker\docs\场景切换与冲动行为调研\原始数据\B站")
data = json.loads((BASE / "视频评论.json").read_text(encoding='utf-8'))

# 收集所有评论（主评论+楼中楼），按赞数排序
all_comments = []
for bvid, v in data.items():
    title = v.get('title','')
    for c in v.get('comments', []):
        all_comments.append({
            'bvid': bvid, 'title': title,
            'uname': c['uname'], 'like': c['like'],
            'message': c['message'], 'subs_count': len(c.get('subs',[])),
            'type': 'main'
        })
        for s in c.get('subs', []):
            all_comments.append({
                'bvid': bvid, 'title': title,
                'uname': s['uname'], 'like': s['like'],
                'message': s['message'], 'subs_count': 0,
                'type': 'sub'
            })

all_comments.sort(key=lambda x: -x['like'])
print(f"总评论数: {len(all_comments)}")
print("\n=== TOP 60 高赞评论 ===")
for i, c in enumerate(all_comments[:60]):
    msg = c['message'].replace('\n', ' ')[:150]
    print(f"{i+1:2d}. [{c['like']:5d}赞|{c['bvid']}] {c['uname']}: {msg}")
