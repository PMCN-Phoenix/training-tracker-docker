# -*- coding: utf-8 -*-
"""本地语料增量挖掘：在两个健身语料目录里搜意象/筋膜/张力/本体感觉等关键词"""
import json, re, os, glob, sys

KEYWORDS = ['意象','意念','念动','念动一致','发力感','发力感知','筋膜','肌筋膜','解剖列车','腱','肌腱',
            '张力','拉伸感','本体感觉','本体感','神经募集','神经适应','神经肌肉','注意力焦点','内部注意',
            '外部注意','专注','大脑训练','心理训练','运动学习','动作学习','迁移','刻意练习','肌肉链',
            '筋膜链','高尔基','肌梭','牵张反射','拉伸','意念锻炼','脑内回放','心理演练','表象训练']

LOCAL_DIRS = [
    r"D:\11.project\iwen-codex\codex-list\力量训练平台期突破-B站原始数据",
    r"D:\11.project\iwen-codex\codex-list\training-tracker-docker\docs\健身日常进步与TOC调研\健身日常进步+TOC瓶颈-B站原始数据",
]

def find_bv(path):
    m = re.search(r'(BV[0-9A-Za-z]{10})', os.path.basename(path))
    return m.group(1) if m else None

def scan_text(text, source, hits, bv):
    low = text
    for kw in KEYWORDS:
        if kw in low:
            # 提取上下文片段
            for m in re.finditer(re.escape(kw), low):
                s = max(0, m.start()-40); e = min(len(low), m.end()+60)
                ctx = low[s:e].replace('\n',' ').replace('\r',' ')
                hits.append({'kw': kw, 'bv': bv, 'src': source, 'ctx': ctx})

def walk(o, source, hits, bv):
    if isinstance(o, dict):
        # 提取title/owner
        title = o.get('title') or ''
        owner = o.get('owner') or o.get('author') or ''
        if title:
            scan_text(title, source, hits, bv)
        # 字幕body
        if isinstance(o.get('body'), list) and o['body'] and isinstance(o['body'][0], dict) and 'content' in o['body'][0]:
            for seg in o['body']:
                scan_text(seg.get('content',''), source, hits, bv)
        # 评论
        if isinstance(o.get('comments'), list):
            for c in o['comments']:
                scan_text(c.get('message',''), source, hits, bv)
                for s in (c.get('subs') or []):
                    scan_text(s.get('message',''), source, hits, bv)
        for v in o.values():
            walk(v, source, hits, bv)
    elif isinstance(o, list):
        for v in o:
            walk(v, source, hits, bv)

all_hits = []
for d in LOCAL_DIRS:
    if not os.path.isdir(d):
        continue
    for f in glob.glob(os.path.join(d, '**', '*.json'), recursive=True):
        bv = find_bv(f) or os.path.basename(f).replace('.json','')[:40]
        try:
            with open(f, encoding='utf-8') as fp:
                data = json.load(fp)
        except Exception as e:
            continue
        walk(data, f, all_hits, bv)

# 按bvid分组
by_bv = {}
for h in all_hits:
    by_bv.setdefault(h['bv'], []).append(h)

# 输出
out = r"D:\11.project\iwen-codex\codex-list\training-tracker-docker\docs\意象训练与筋膜感知调研\原始数据\B站\本地语料命中清单.json"
with open(out, 'w', encoding='utf-8') as fp:
    json.dump({'total_hits': len(all_hits), 'by_bv_count': {k: len(v) for k,v in by_bv.items()}, 'hits': all_hits}, fp, ensure_ascii=False, indent=1)

print(f"总命中: {len(all_hits)} 条")
print(f"涉及视频: {len(by_bv)} 个")
for bv, hs in sorted(by_bv.items(), key=lambda x: -len(x[1])):
    kws = set(h['kw'] for h in hs)
    print(f"  {bv}: {len(hs)} hits, kws={list(kws)[:8]}")
