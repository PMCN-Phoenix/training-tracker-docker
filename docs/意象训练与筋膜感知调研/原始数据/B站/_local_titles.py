# -*- coding: utf-8 -*-
"""提取本地命中视频的标题和关键上下文片段"""
import json, re, os

OUT_DIR = r"D:\11.project\iwen-codex\codex-list\training-tracker-docker\docs\意象训练与筋膜感知调研\原始数据\B站"

with open(os.path.join(OUT_DIR, '本地语料命中清单.json'), encoding='utf-8') as f:
    data = json.load(f)

# 按bvid分组，输出关键上下文
by_bv = {}
for h in data['hits']:
    by_bv.setdefault(h['bv'], []).append(h)

# 找本地语料里的标题映射
LOCAL_DIRS = [
    r"D:\11.project\iwen-codex\codex-list\力量训练平台期突破-B站原始数据",
    r"D:\11.project\iwen-codex\codex-list\training-tracker-docker\docs\健身日常进步与TOC调研\健身日常进步+TOC瓶颈-B站原始数据",
]
import glob
title_map = {}
for d in LOCAL_DIRS:
    for f in glob.glob(os.path.join(d, '**', '*.json'), recursive=True):
        try:
            with open(f, encoding='utf-8') as fp:
                obj = json.load(fp)
        except: continue
        # 搜索清单结构
        if isinstance(obj, list):
            for v in obj:
                if isinstance(v, dict) and v.get('bvid'):
                    title_map[v['bvid']] = v.get('title','')
        elif isinstance(obj, dict):
            for bv, v in obj.items():
                if isinstance(v, dict) and v.get('title'):
                    title_map[bv] = v['title']

# 输出
lines = []
lines.append("=== 本地命中视频标题 ===")
for bv in sorted(by_bv.keys()):
    t = title_map.get(bv, '(未知)')
    lines.append(f"\n### {bv} | {t} | hits={len(by_bv[bv])}")
    # 去重上下文
    seen = set()
    for h in by_bv[bv]:
        key = h['ctx'][:50]
        if key in seen: continue
        seen.add(key)
        lines.append(f"  [{h['kw']}] {h['ctx']}")

out_txt = os.path.join(OUT_DIR, '本地语料命中-关键上下文.txt')
with open(out_txt, 'w', encoding='utf-8') as fp:
    fp.write('\n'.join(lines))
print(f"已写入 {out_txt}")
print(f"标题映射数: {len(title_map)}")
