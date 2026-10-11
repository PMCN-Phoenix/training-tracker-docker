# -*- coding: utf-8 -*-
"""把字幕json转成可读的时间戳文本，方便读"""
import json, os, glob

SUB_DIR = r"D:\11.project\iwen-codex\codex-list\training-tracker-docker\docs\意象训练与筋膜感知调研\原始数据\B站\字幕"

def ts(sec):
    m = int(sec)//60; s = int(sec)%60
    return f"{m:02d}:{s:02d}"

for f in sorted(glob.glob(os.path.join(SUB_DIR, '*.json'))):
    bv = os.path.basename(f).replace('.json','')
    with open(f, encoding='utf-8') as fp:
        d = json.load(fp)
    lines = [f"# {bv} | {d.get('title','')} | dur={d.get('duration')}s", ""]
    for seg in d.get('body', []):
        lines.append(f"[{ts(seg['from'])}] {seg['content']}")
    out = os.path.join(SUB_DIR, f'{bv}-全文.txt')
    with open(out, 'w', encoding='utf-8') as fp:
        fp.write('\n'.join(lines))
    print(f"{bv}: {len(d.get('body',[]))} segs -> {out}")
