# -*- coding: utf-8 -*-
import re, glob, os

folder = r"D:\11.project\iwen-codex\codex-list\training-tracker-docker\docs\意象训练与筋膜感知调研\原始数据\YouTube"

def ts_to_mmss(ts):
    # ts like 00:00:12.345 or 00:12.345
    ts = ts.split('.')[0]
    parts = ts.split(':')
    parts = [int(p) for p in parts]
    if len(parts) == 3:
        h, m, s = parts
    else:
        h, m, s = 0, parts[0], parts[1]
    return h*60 + m, s

def parse(path):
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
    lines = content.split('\n')
    out = []
    i = 0
    last_text = ""
    while i < len(lines):
        line = lines[i].strip()
        m = re.match(r'(\d{1,2}:\d{2}:\d{2}[.,]\d{3})\s*-->', line)
        if not m:
            i += 1
            continue
        start = m.group(1)
        # collect cue text until blank
        i += 1
        text_lines = []
        while i < len(lines) and lines[i].strip() != '':
            tl = lines[i].strip()
            if '-->' in tl:
                break
            text_lines.append(tl)
            i += 1
        text = ' '.join(text_lines)
        text = re.sub(r'<[^>]+>', '', text)  # remove <c> tags
        text = re.sub(r'&nbsp;', ' ', text)
        text = re.sub(r'\s+', ' ', text).strip()
        if not text:
            continue
        if text == last_text:
            continue
        mm, ss = ts_to_mmss(start)
        out.append((mm*60+ss, f"{mm:02d}:{ss:02d}", text))
        last_text = text
    return out

for vtt in sorted(glob.glob(os.path.join(folder, "*.en.vtt"))):
    if vtt.endswith(".en-orig.vtt"):
        continue
    cues = parse(vtt)
    txt_path = vtt.replace(".en.vtt", ".txt")
    with open(txt_path, 'w', encoding='utf-8') as f:
        for total, tlabel, text in cues:
            f.write(f"[{tlabel}] {text}\n")
    print(os.path.basename(vtt), "->", len(cues), "cues")
print("ALL DONE")
