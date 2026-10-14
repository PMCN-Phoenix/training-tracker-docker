# -*- coding: utf-8 -*-
"""把 B 站字幕 JSON 合并成可 grep 的纯文本"""
import json, pathlib

ROOT = pathlib.Path(r"D:\11.project\iwen-codex\codex-list\training-tracker-docker\docs\扣篮弹跳调研\原始数据\B站")

summary = json.loads((ROOT / "_summary.json").read_text(encoding="utf-8"))

out_lines = []
for bv, r in summary.items():
    title = r["info"]["title"]
    dur = r["info"]["duration"]
    out_lines.append(f"\n\n========== {bv} | {title} | dur={dur}s ==========")
    for sub in r["subs"]:
        out_lines.append(f"\n--- P: {sub.get('part','?')} ({sub.get('lang','?')}) ---")
        for seg in sub["segments"]:
            t = seg.get("from", 0)
            mm = int(t // 60); ss = int(t % 60)
            content = seg.get("content", "").strip()
            out_lines.append(f"[{mm:02d}:{ss:02d}] {content}")

text = "\n".join(out_lines)
(ROOT / "_all_subtitles.txt").write_text(text, encoding="utf-8")
print(f"合并完成: {len(text)} chars, {len(summary)} videos")
