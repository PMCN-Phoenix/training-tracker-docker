import os, re, glob

d = r"D:\11.project\iwen-codex\codex-list\training-tracker-docker\docs\腰痛防护与弯举进阶调研\原始数据\需求2-YouTube"

# Rename RP en-orig to en.vtt
rp_orig = os.path.join(d, "RP_5RulesOfBicepTraining__q8jjwZbhBas.en-orig.vtt")
rp_dest = os.path.join(d, "RP_5RulesOfBicepTraining__q8jjwZbhBas.en.vtt")
if os.path.exists(rp_orig) and not os.path.exists(rp_dest):
    os.rename(rp_orig, rp_dest)

def vtt_to_ts_txt(vtt_path, txt_path):
    with open(vtt_path, "r", encoding="utf-8") as f:
        content = f.read()
    # Split into cues
    cues = []
    blocks = re.split(r"\n\n+", content)
    for b in blocks:
        lines = b.strip().split("\n")
        if len(lines) < 2:
            continue
        # find time line
        time_line = None
        text_lines = []
        for ln in lines:
            if "-->" in ln:
                time_line = ln
            elif ln.startswith(("WEBVTT", "Kind:", "Language:", "NOTE")):
                continue
            else:
                text_lines.append(ln)
        if not time_line or not text_lines:
            continue
        start = time_line.split("-->")[0].strip()
        # start is HH:MM:SS.mmm or MM:SS.mmm
        parts = start.split(":")
        if len(parts) == 3:
            h, m, s = parts
            mm = int(h)*60 + int(m)
            ss = float(s)
        elif len(parts) == 2:
            m, s = parts
            mm = int(m)
            ss = float(s)
        else:
            continue
        ts = f"{mm:02d}:{int(ss):02d}"
        text = " ".join(text_lines).strip()
        # remove VTT tags
        text = re.sub(r"<[^>]+>", "", text)
        text = re.sub(r"\s+", " ", text).strip()
        if text:
            cues.append((ts, text))
    # Dedupe consecutive identical (auto-caption repeats)
    out = []
    prev = None
    for ts, t in cues:
        if t == prev:
            continue
        out.append((ts, t))
        prev = t
    with open(txt_path, "w", encoding="utf-8") as f:
        for ts, t in out:
            f.write(f"[{ts}] {t}\n")
    return len(out)

for vtt in sorted(glob.glob(os.path.join(d, "*.en.vtt"))):
    base = os.path.basename(vtt).replace(".en.vtt", "")
    txt = os.path.join(d, base + ".txt")
    n = vtt_to_ts_txt(vtt, txt)
    print(f"{base}: {n} cues")
