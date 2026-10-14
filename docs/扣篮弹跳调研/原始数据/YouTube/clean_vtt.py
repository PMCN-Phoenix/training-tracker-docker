# -*- coding: utf-8 -*-
"""清洗 YouTube VTT 字幕为纯文本，便于后续 grep"""
import re, pathlib

ROOT = pathlib.Path(r"D:\11.project\iwen-codex\codex-list\training-tracker-docker\docs\扣篮弹跳调研\原始数据\YouTube")

def vtt_to_text(vtt_path):
    raw = vtt_path.read_text(encoding="utf-8", errors="ignore")
    lines = raw.split("\n")
    out = []
    seen = set()
    for l in lines:
        l = l.strip()
        if not l: continue
        if l.startswith("WEBVTT") or l.startswith("Kind:") or l.startswith("Language:") or l.startswith("NOTE"): continue
        # 时间戳行
        if re.match(r"^\d{2}:\d{2}:\d{2}", l): continue
        # 去掉 VTT 标签
        l = re.sub(r"<[^>]+>", "", l)
        l = l.replace("&amp;", "&").replace("&lt;","<").replace("&gt;",">")
        if l and l not in seen:
            seen.add(l)
            out.append(l)
    return " ".join(out)

for f in ROOT.glob("*.vtt"):
    txt = vtt_to_text(f)
    txt_path = ROOT / (f.stem + ".txt")
    txt_path.write_text(txt, encoding="utf-8")
    print(f"{f.name}: {len(txt)} chars")
