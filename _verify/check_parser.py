# -*- coding: utf-8 -*-
"""检查 parse-training 对 lumbar/肩胛前伸的支持，并列出动作表"""
import json
import re

d = json.load(open(r"D:\11.project\iwen-codex\codex-list\training-tracker-docker\nodered_data\flows.json", encoding="utf-8"))
for n in d:
    if n.get("id") == "parse-training":
        src = n["func"]
        print("lumbar 支持:", "lumbar" in src)
        print("肩胛 支持:", "肩胛" in src)
        print("前伸 支持:", "前伸" in src)
        print("技术块 支持:", "tech" in src.lower())
        ids = re.findall(r'id:\s*"([a-z_0-9]+)"', src)
        print("动作数:", len(ids))
        print(" ".join(ids))
        break
