# -*- coding: utf-8 -*-
"""分析字幕和评论：提取关键观点+时间戳+高赞评论"""
import json, re
from pathlib import Path

BASE = Path(r"D:\11.project\iwen-codex\codex-list\training-tracker-docker\docs\场景切换与冲动行为调研\原始数据\B站")
SUB_DIR = BASE / "字幕"

def fmt_ts(sec):
    m, s = divmod(int(sec), 60)
    h, m = divmod(m, 60)
    if h: return f"{h:02d}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"

def dump_sub(bvid, max_chars=None):
    """输出字幕为可读文本，带时间戳"""
    p = SUB_DIR / f"{bvid}.json"
    if not p.exists():
        return f"[无字幕] {bvid}"
    segs = json.loads(p.read_text(encoding='utf-8'))
    lines = []
    for s in segs:
        ts = fmt_ts(s['from'])
        lines.append(f"[{ts}] {s['content']}")
    text = '\n'.join(lines)
    if max_chars:
        text = text[:max_chars]
    return text

# 核心视频1: 不可打扰 - 你不是手机成瘾是情绪成瘾
print("="*80)
print("【核心视频】BV1FUuy6DE6G 《不可打扰》：你不是手机成瘾，你是情绪成瘾")
print("="*80)
print(dump_sub("BV1FUuy6DE6G"))
