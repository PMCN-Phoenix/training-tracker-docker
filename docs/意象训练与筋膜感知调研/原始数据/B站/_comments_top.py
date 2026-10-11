# -*- coding: utf-8 -*-
"""提取评论区高赞评论，按bvid分组输出"""
import json, os

OUT = r"D:\11.project\iwen-codex\codex-list\training-tracker-docker\docs\意象训练与筋膜感知调研\原始数据\B站"
with open(os.path.join(OUT, '视频评论.json'), encoding='utf-8') as f:
    data = json.load(f)

lines = []
for bv, info in data.items():
    lines.append(f"\n{'='*60}\n### {bv} | {info.get('title','')} | {info.get('comment_count',0)} comments")
    # 按like排序前15
    cs = sorted(info.get('comments',[]), key=lambda x: -x.get('like',0))[:15]
    for c in cs:
        lines.append(f"  [{c.get('like',0):>4}赞] {c.get('message','')[:200]}")
        for s in c.get('subs',[])[:3]:
            lines.append(f"      ↳ [{s.get('like',0)}赞] {s.get('message','')[:150]}")

with open(os.path.join(OUT, '评论Top汇总.txt'), 'w', encoding='utf-8') as f:
    f.write('\n'.join(lines))
print(f"written, {len(lines)} lines")
