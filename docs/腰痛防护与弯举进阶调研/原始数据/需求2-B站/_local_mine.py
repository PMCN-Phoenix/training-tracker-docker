# -*- coding: utf-8 -*-
"""本地语料挖掘：扫已有 B站 原始数据，捞弯举/二头/渐进/绳索/EZ/锤式相关评论和字幕"""
import os, re, json, glob, sys

LOCAL_DIRS = [
    r"D:\11.project\iwen-codex\codex-list\力量训练平台期突破-B站原始数据",
    r"D:\11.project\iwen-codex\codex-list\training-tracker-docker\docs\健身日常进步与TOC调研\健身日常进步+TOC瓶颈-B站原始数据",
    r"D:\11.project\iwen-codex\codex-list\training-tracker-docker\docs\意象训练与筋膜感知调研\原始数据\B站",
]

OUT_DIR = r"D:\11.project\iwen-codex\codex-list\training-tracker-docker\docs\腰痛防护与弯举进阶调研\原始数据\需求2-B站"

# 关键词（命中即捞）
KW = ['弯举', '二头', '肱二', '臂弯', '绳索弯举', 'EZ杠', 'ez杠', '杠铃弯举',
      '锤式', '牧师', '上斜哑铃弯举', '小重量片', '磁吸', '配重片', '小片',
      '渐进超负荷', '渐进', 'double progression', '次数递增', '次数先行',
      '重量上不去', '平台期', '可调哑铃', '哑铃进阶']

def has_kw(text):
    if not text: return None
    for k in KW:
        if k.lower() in text.lower():
            return k
    return None

def extract_bvid(path):
    m = re.search(r'(BV[0-9A-Za-z]{10})', os.path.basename(path))
    return m.group(1) if m else None

# 收集评论
hits_comments = []  # (bvid, source_file, keyword, like, text)
hits_subs = []      # (bvid, source_file, keyword, from, to, text)
local_bvids = set()

def collect_comments(o, src, bvid):
    if isinstance(o, dict):
        # 结构1: {comments:[{message, like, subs}]}
        if isinstance(o.get('comments'), list):
            for c in o['comments']:
                msg = c.get('message') or c.get('content') or ''
                like = c.get('like', 0)
                k = has_kw(msg)
                if k:
                    hits_comments.append((bvid, src, k, like, msg))
                for s in (c.get('subs') or []):
                    smsg = s.get('message') or s.get('content') or ''
                    sk = has_kw(smsg)
                    if sk:
                        hits_comments.append((bvid, src, sk, s.get('like', 0), smsg))
        # 结构2: {replies:[{content:{message}, like, replies:[...]}]}
        if isinstance(o.get('replies'), list):
            for c in o['replies']:
                content = c.get('content', {})
                msg = content.get('message', '') if isinstance(content, dict) else str(content)
                like = c.get('like', 0)
                k = has_kw(msg)
                if k:
                    hits_comments.append((bvid, src, k, like, msg))
                for s in (c.get('replies') or []):
                    sc = s.get('content', {})
                    smsg = sc.get('message', '') if isinstance(sc, dict) else str(sc)
                    sk = has_kw(smsg)
                    if sk:
                        hits_comments.append((bvid, src, sk, s.get('like', 0), smsg))
        for v in o.values():
            collect_comments(v, src, bvid)
    elif isinstance(o, list):
        for v in o:
            collect_comments(v, src, bvid)

def collect_subs(o, src, bvid):
    """字幕 JSON: {body:[{from,to,content}]} 或 {title, owner, body:[...]}"""
    if isinstance(o, dict):
        if isinstance(o.get('body'), list) and o['body'] and isinstance(o['body'][0], dict):
            for seg in o['body']:
                content = seg.get('content', '') if isinstance(seg, dict) else ''
                fr = seg.get('from', 0) if isinstance(seg, dict) else 0
                to = seg.get('to', 0) if isinstance(seg, dict) else 0
                k = has_kw(content)
                if k:
                    hits_subs.append((bvid, src, k, fr, to, content))
        for v in o.values():
            collect_subs(v, src, bvid)
    elif isinstance(o, list):
        for v in o:
            collect_subs(v, src, bvid)

# 扫所有 json
for d in LOCAL_DIRS:
    if not os.path.exists(d):
        print(f"[MISS] {d}")
        continue
    for root, dirs, files in os.walk(d):
        for f in files:
            if not f.endswith('.json'): continue
            fp = os.path.join(root, f)
            bvid = extract_bvid(fp)
            if bvid: local_bvids.add(bvid)
            try:
                with open(fp, encoding='utf-8') as fh:
                    data = json.load(fh)
            except Exception as e:
                continue
            # 判断是评论还是字幕：看文件名
            low = f.lower()
            if '评论' in f or 'comment' in low:
                collect_comments(data, fp, bvid)
            elif '字幕' in f or 'sub' in low or f.endswith('.json') and 'body' in json.dumps(data)[:200]:
                # 也尝试字幕
                collect_subs(data, fp, bvid)
                collect_comments(data, fp, bvid)
            else:
                collect_comments(data, fp, bvid)
                collect_subs(data, fp, bvid)

# 扫字幕目录下的 .txt（纯中文提取）
for d in LOCAL_DIRS:
    if not os.path.exists(d): continue
    for root, dirs, files in os.walk(d):
        for f in files:
            if not (f.endswith('.txt') or f.endswith('.md')): continue
            fp = os.path.join(root, f)
            bvid = extract_bvid(fp)
            try:
                with open(fp, encoding='utf-8') as fh:
                    txt = fh.read()
            except: continue
            for line in txt.split('\n'):
                k = has_kw(line)
                if k:
                    hits_subs.append((bvid, fp, k, 0, 0, line[:300]))

# 输出
with open(os.path.join(OUT_DIR, '本地语料命中清单.json'), 'w', encoding='utf-8') as f:
    json.dump({
        'local_bvids_count': len(local_bvids),
        'local_bvids': sorted(local_bvids),
        'hits_comments': [{'bvid':b,'src':s,'kw':k,'like':l,'text':t} for b,s,k,l,t in hits_comments],
        'hits_subs': [{'bvid':b,'src':s,'kw':k,'from':fr,'to':to,'text':t} for b,s,k,fr,to,t in hits_subs],
    }, f, ensure_ascii=False, indent=2)

# 同时写一份可读 txt
with open(os.path.join(OUT_DIR, '本地语料命中-关键上下文.txt'), 'w', encoding='utf-8') as f:
    f.write(f"本地 bvid 总数: {len(local_bvids)}\n")
    f.write(f"评论命中: {len(hits_comments)}\n")
    f.write(f"字幕命中: {len(hits_subs)}\n\n")
    f.write("=== 评论命中（按点赞排序）===\n")
    for b,s,k,l,t in sorted(hits_comments, key=lambda x: -(x[3] or 0))[:200]:
        f.write(f"\n[{b}|{k}|{l}赞] {t[:400]}\n")
    f.write("\n\n=== 字幕命中 ===\n")
    for b,s,k,fr,to,t in hits_subs[:300]:
        f.write(f"\n[{b}|{k}|{fr:.0f}-{to:.0f}] {t[:300]}\n")

print(f"local_bvids={len(local_bvids)} comments={len(hits_comments)} subs={len(hits_subs)}")
