# -*- coding: utf-8 -*-
import os, re, json, glob, io, sys

OUT = r"D:\11.project\iwen-codex\codex-list\training-tracker-docker\docs\腰痛防护与弯举进阶调研\原始数据\需求1-B站"
DIRS = [
    r"D:\11.project\iwen-codex\codex-list\力量训练平台期突破-B站原始数据",
    r"D:\11.project\iwen-codex\codex-list\training-tracker-docker\docs\健身日常进步与TOC调研\健身日常进步+TOC瓶颈-B站原始数据",
    r"D:\11.project\iwen-codex\codex-list\training-tracker-docker\docs\意象训练与筋膜感知调研\原始数据\B站",
]

# 主题关键词
KW = ['划船','坐姿划','绳索划','拉背','引体','腰痛','腰疼','下背','腰背','竖脊','核心','硬拉','疲劳','髋铰链','骨盆','中立位','剪切','腰椎','腰悬空','靠垫','胸垫','拉伸','脊柱','稳定','腹压','瓦式','瓦式呼吸','背痛','刺痛','锐痛']

def bvid_from_name(fn):
    m = re.search(r'(BV[0-9A-Za-z]{10})', os.path.basename(fn))
    return m.group(1) if m else None

# 收集所有 json 文件
files = []
for d in DIRS:
    files += glob.glob(os.path.join(d, '**', '*.json'), recursive=True)

comments = []   # (bvid, from, message, like, srcfile)
subs = []       # (bvid, title, from_sec, content, srcfile)
local_bvids = set()

def add_comment(bv, message, like, src):
    if not message: return
    comments.append((bv, message, like or 0, src))

def collect_comments(o, bv, src):
    if isinstance(o, dict):
        if isinstance(o.get('comments'), list):
            for c in o['comments']:
                if isinstance(c, dict):
                    add_comment(bv, c.get('message'), c.get('like'), src)
                    for s in (c.get('subs') or []):
                        if isinstance(s, dict):
                            add_comment(bv, s.get('message'), s.get('like'), src)
        # 评论明细结构 {bvid: {title, owner, body:[{from,content,like}]}}
        if 'bvid' in o and isinstance(o['bvid'], str):
            local_bvids.add(o['bvid'])
        for k, v in o.items():
            if isinstance(v, dict) and 'bvid' in v and isinstance(v['bvid'], str):
                local_bvids.add(v['bvid'])
            collect_comments(v, bv, src)
    elif isinstance(o, list):
        for v in o: collect_comments(v, bv, src)

def collect_subs(o, bv, title, src):
    # 字幕结构: {title, owner, body:[{from, content}]}
    if isinstance(o, dict):
        if isinstance(o.get('body'), list) and o['body'] and isinstance(o['body'][0], dict) and ('content' in o['body'][0] or 'from' in o['body'][0]):
            t = title or o.get('title') or ''
            for seg in o['body']:
                fr = seg.get('from'); ct = seg.get('content')
                if ct:
                    subs.append((bv, t, fr, ct, src))
            return
        for k, v in o.items():
            collect_subs(v, bv, title or o.get('title'), src)
    elif isinstance(o, list):
        for v in o: collect_subs(v, bv, title, src)

n_files = 0
for f in files:
    bv = bvid_from_name(f)
    try:
        d = json.load(open(f, encoding='utf-8'))
    except Exception as e:
        continue
    n_files += 1
    if bv: local_bvids.add(bv)
    collect_comments(d, bv, f)
    collect_subs(d, bv, None, f)

# 过滤命中
def hit(text):
    return [k for k in KW if k in text]

hit_comments = []
for bv, msg, like, src in comments:
    ks = hit(msg)
    if ks:
        hit_comments.append((bv, msg, like, ks, os.path.basename(src)))

hit_subs = []
for bv, t, fr, ct, src in subs:
    ks = hit(ct)
    if ks:
        hit_subs.append((bv, t, fr, ct, ks, os.path.basename(src)))

# 输出
with io.open(os.path.join(OUT, '本地语料命中.txt'), 'w', encoding='utf-8') as w:
    w.write(f"扫描 json 文件数: {n_files}\n")
    w.write(f"本地 bvid 池大小: {len(local_bvids)}\n")
    w.write(f"评论总数: {len(comments)}  命中: {len(hit_comments)}\n")
    w.write(f"字幕段总数: {len(subs)}  命中: {len(hit_subs)}\n\n")
    w.write("="*40 + " 命中评论 " + "="*40 + "\n\n")
    for bv, msg, like, ks, src in sorted(hit_comments, key=lambda x:-x[2]):
        w.write(f"[{bv}|{like}赞|{','.join(ks)}] {msg[:300]}\n  <- {src}\n\n")
    w.write("\n" + "="*40 + " 命中字幕段 " + "="*40 + "\n\n")
    for bv, t, fr, ct, ks, src in hit_subs:
        mm = int(fr//60) if isinstance(fr,(int,float)) else 0
        ss = int(fr%60) if isinstance(fr,(int,float)) else 0
        w.write(f"[{bv}|{t[:30]}|{mm:02d}:{ss:02d}|{','.join(ks)}] {ct[:200]}\n")

# 保存本地 bvid 池供搜索去重
json.dump(sorted(local_bvids), io.open(os.path.join(OUT,'本地bvid池.json'),'w',encoding='utf-8'), ensure_ascii=False, indent=1)

print(f"files={n_files} bvids={len(local_bvids)} comments={len(comments)} hit_comments={len(hit_comments)} subs={len(subs)} hit_subs={len(hit_subs)}")
