#!/usr/bin/env python3
"""Convert YouTube VTT subtitles to clean timestamped text.
Usage: python vtt2txt.py <input.vtt> <output.txt>
"""
import sys
import re
import os

def parse_vtt(path):
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
    # Split into cue blocks by blank lines
    blocks = re.split(r'\n\n+', content)
    cues = []
    for b in blocks:
        lines = b.strip().split('\n')
        if len(lines) < 2:
            continue
        # Find the timestamp line
        ts_line = None
        ts_idx = None
        for i, l in enumerate(lines):
            m = re.match(r'^(\d{2}:\d{2}:\d{2}\.\d{3})\s*-->', l)
            if m:
                ts_line = l
                ts_idx = i
                break
        if ts_line is None:
            continue
        start = ts_line.split(' -->')[0]
        # Text lines are after ts line
        text_lines = lines[ts_idx+1:]
        # Remove inline timing tags <...>
        text = ' '.join(text_lines)
        text = re.sub(r'<[^>]+>', '', text)
        text = re.sub(r'\s+', ' ', text).strip()
        if not text:
            continue
        # Convert start to mm:ss
        parts = start.split(':')
        h, m, s = int(parts[0]), int(parts[1]), float(parts[2])
        total_min = h*60 + m
        ts_short = f"{total_min:02d}:{int(s):02d}"
        cues.append((ts_short, text))
    return cues

def dedupe(cues):
    """VTT repeats previous caption line. Keep only incremental additions."""
    out = []
    prev_text = ""
    for ts, text in cues:
        # If text starts with prev_text, the new part is what's after
        if prev_text and text.startswith(prev_text):
            new_part = text[len(prev_text):].strip()
            if new_part:
                out.append((ts, new_part))
        else:
            # New sentence/block - emit full
            out.append((ts, text))
        prev_text = text
    return out

def main():
    inp = sys.argv[1]
    outp = sys.argv[2]
    cues = parse_vtt(inp)
    cues = dedupe(cues)
    with open(outp, 'w', encoding='utf-8') as f:
        for ts, text in cues:
            f.write(f"[{ts}] {text}\n")
    print(f"{inp} -> {outp} ({len(cues)} cues)")

if __name__ == '__main__':
    main()
