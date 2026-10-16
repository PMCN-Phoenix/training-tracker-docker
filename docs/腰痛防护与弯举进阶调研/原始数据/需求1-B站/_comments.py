# -*- coding: utf-8 -*-
import json, io, os
OUT = r"D:\11.project\iwen-codex\codex-list\training-tracker-docker\docs\腰痛防护与弯举进阶调研\原始数据\需求1-B站"
data = json.load(io.open(OUT+r'\新抓视频明细.json', encoding='utf-8'))
lines=[]
for v in data:
    lines.append(f"\n===== {v['bvid']} {v['title'][:50]} | {v['owner']} | dur {v['duration']} | sub {v['subtitles']} | comments {v['n_comments']} =====")
    cs = sorted(v.get('comments') or [], key=lambda x:-(x.get('like') or 0))
    for c in cs[:12]:
        tag = '[楼中楼]' if c.get('sub') else ''
        msg = (c.get('message') or '').replace('\n',' ')[:260]
        lines.append(f"  [{c.get('like')}赞]{tag} {msg}")
io.open(OUT+r'\评论区高赞摘录.txt','w',encoding='utf-8').write('\n'.join(lines))
print('done', len(data))
