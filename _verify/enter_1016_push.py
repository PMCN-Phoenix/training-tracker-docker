# -*- coding: utf-8 -*-
"""录入 2026-10-16 推日容量做组（用户口述）
- 站姿卧推 → 规范化为「站姿推举」（流别名表无"站姿卧推"，原文会被"卧推"别名误吞进平板）
- 平板降序 4 组：47.5×10 / 45×10 / 42.5×10 / 40×10
- 时间用当前时刻
"""
import requests
from datetime import datetime, timezone, timedelta
from urllib.parse import quote

NR = "http://127.0.0.1:1880"
tz8 = timezone(timedelta(hours=8))
ts = datetime.now(tz8).strftime("%Y-%m-%dT%H:%M:%S+08:00")

text = (
    "推日容量："
    "夹胸 42.5kg×12 第1组 42.5kg×12 第2组 42.5kg×12 第3组 42.5kg×12 第4组 "
    "上斜卧推 12.5kg×12 第1组 12.5kg×12 第2组 12.5kg×12 第3组 12.5kg×12 第4组 "
    "平板卧推 47.5kg×10 第1组 45kg×10 第2组 42.5kg×10 第3组 40kg×10 第4组 "
    "窄距卧推 40kg×12 第1组 40kg×12 第2组 40kg×12 第3组 40kg×12 第4组 "
    "站姿推举 10kg×12 第1组 10kg×12 第2组 10kg×12 第3组 10kg×12 第4组"
)

url = f"{NR}/add-training?source=phone&time={quote(ts)}"
r = requests.post(url, data=text.encode("utf-8"),
                  headers={"Content-Type": "text/plain; charset=utf-8"}, timeout=30)
try:
    print(f"[{r.status_code}]", r.json())
except Exception:
    print(f"[{r.status_code}]", r.text[:200])
