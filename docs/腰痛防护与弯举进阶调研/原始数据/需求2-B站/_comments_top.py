# -*- coding: utf-8 -*-
"""提取关键评论：按点赞排序，找与弯举进阶/小片/渐进/二头相关的评论"""
import json, os

OUT_DIR = r"D:\11.project\iwen-codex\codex-list\training-tracker-docker\docs\腰痛防护与弯举进阶调研\原始数据\需求2-B站"
d = json.load(open(os.path.join(OUT_DIR, '新抓视频明细.json'), encoding='utf-8'))

KW = ['弯举', '二头', '肱二', '小片', '配重片', '1.25', '0.5', '磁吸', '可调哑铃',
      '渐进', '加重', '重量上不去', '平台期', '次数', '组次', 'double',
      '绳索', 'EZ', 'ez', '牧师', '锤式', '上斜', '杠铃弯举',
      '借力', '甩', '手腕', '前臂', '肱桡', '长头', '短头',
      '没有小', '自己带', '自带', '买', '换挡', '丝滑',
      '升重', '加重量', '加不上去', '卡住', '停住']

out_lines = []
for v in d:
    if 'error' in v: continue
    comments = v.get('comments', [])
    # 收集相关评论
    rel = []
    for c in comments:
        msg = c.get('message','')
        like = c.get('like',0)
        if any(k in msg for k in KW):
            rel.append((like, msg, c.get('subs',[])))
        for s in c.get('subs',[]):
            smsg = s.get('message','')
            if any(k in smsg for k in KW):
                rel.append((s.get('like',0), '[楼中楼] '+smsg, []))
    rel.sort(key=lambda x: -x[0])
    if rel:
        out_lines.append(f"\n=== {v['bvid']} | {v['title'][:40]} | 评论{len(comments)}条 ===")
        for like, msg, subs in rel[:15]:
            out_lines.append(f"  [{like}赞] {msg[:300]}")
            for s in subs[:3]:
                out_lines.append(f"    └[{s.get('like',0)}赞] {s.get('message','')[:200]}")

with open(os.path.join(OUT_DIR, '评论Top汇总.txt'), 'w', encoding='utf-8') as f:
    f.write('\n'.join(out_lines))
print(f"written {len(out_lines)} lines")
