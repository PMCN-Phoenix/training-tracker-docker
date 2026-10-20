# -*- coding: utf-8 -*-
"""录入晨脉（经 Node-RED /add-training，时间用当前时刻）
用法: python enter_hr.py 73
"""
import sys
import requests
from datetime import datetime, timezone, timedelta

NR = "http://127.0.0.1:1880"
val = sys.argv[1] if len(sys.argv) > 1 else "73"
tz8 = timezone(timedelta(hours=8))
ts = datetime.now(tz8).strftime("%Y-%m-%dT%H:%M:%S+08:00")

text = f"晨脉 {val}"
url = f"{NR}/add-training?source=phone&time={ts}"
r = requests.post(url, data=text.encode("utf-8"),
                  headers={"Content-Type": "text/plain; charset=utf-8"}, timeout=30)
try:
    msg = r.json()
except Exception:
    msg = r.text[:120]
print(f"[{r.status_code}] {ts} {text} -> {msg}")
