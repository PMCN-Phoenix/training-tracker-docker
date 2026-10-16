# -*- coding: utf-8 -*-
"""录入 2026-10-16 晨脉 74（经 Node-RED /add-training，时间用当前时刻）"""
import requests
from datetime import datetime, timezone, timedelta

NR = "http://127.0.0.1:1880"
tz8 = timezone(timedelta(hours=8))
ts = datetime.now(tz8).strftime("%Y-%m-%dT%H:%M:%S+08:00")

text = "晨脉 74"
url = f"{NR}/add-training?source=phone&time={ts}"
r = requests.post(url, data=text.encode("utf-8"),
                  headers={"Content-Type": "text/plain; charset=utf-8"}, timeout=30)
try:
    msg = r.json()
except Exception:
    msg = r.text[:120]
print(f"[{r.status_code}] {ts} {text} -> {msg}")
