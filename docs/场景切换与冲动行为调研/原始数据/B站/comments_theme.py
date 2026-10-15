# -*- coding: utf-8 -*-
"""按主题筛评论：间隙/切换/无聊/触发/反面意见"""
import json
from pathlib import Path

BASE = Path(r"D:\11.project\iwen-codex\codex-list\training-tracker-docker\docs\场景切换与冲动行为调研\原始数据\B站")
data = json.loads((BASE / "视频评论.json").read_text(encoding='utf-8'))

all_c = []
for bvid, v in data.items():
    title = v.get('title','')
    for c in v.get('comments', []):
        all_c.append((bvid, title, c['uname'], c['like'], c['message'], c.get('subs',[])))

themes = {
    "间隙/切换/下课/碎片": ["间隙", "切换", "下课", "碎片", "休息", "课间", "换教室", "路上", "等", "排队", "电梯"],
    "无聊/触发/ cue": ["无聊", "没事干", "触发", "手", "不自觉", "自动", "习惯", "下意识", "顺手", "拿起"],
    "情绪/逃避/焦虑": ["焦虑", "情绪", "逃避", "烦", "压力", "emo", "抑郁", "空虚", "孤独"],
    "反面/质疑/没用": ["没用", "假的", "不信", "扯淡", "割韭菜", "骗", "悖论", "反例", "没用过", "做不到", "失败"],
    "环境/摩擦/物理隔离": ["物理", "隔离", "藏", "放远", "另一个房间", "摩擦", "阻力", "卸载", "通知", "灰度"],
    "运动/替代/内啡肽": ["运动", "跑步", "健身", "内啡肽", "替代", "散步", "散步"],
}

for theme, kws in themes.items():
    print(f"\n=== {theme} ===")
    hits = []
    for bvid, title, uname, like, msg, subs in all_c:
        if any(k in msg for k in kws):
            hits.append((like, bvid, uname, msg))
    hits.sort(key=lambda x: -x[0])
    for like, bvid, uname, msg in hits[:8]:
        m = msg.replace('\n',' ')[:130]
        print(f"  [{like:5d}|{bvid}] {uname}: {m}")
