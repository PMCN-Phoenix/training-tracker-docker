# -*- coding: utf-8 -*-
"""录入 2026-10-18 拉日容量做组（用户口述）
- 6 动作：坐姿划船 / T杆划船 / 硬拉 / 高位下拉 / EZ杠弯举 / 山羊挺身
- EZ 杠弯举：用户口述「总15kg」，但 ppl_pull_barbell_curl 历史 18 组全部为**单边负荷口径**
  （7.5 / 5 / 10），故按 7.5 录入以保持口径一致（总重 15 = 单边 7.5）
- 山羊挺身：Node-RED 原无别名，本次已补 ppl_pull_back_extension（2026-10-18）
  自重动作，weight_kg 记 0；用户口述 3x12~15，按下限 12 保守录入
"""
import requests
from datetime import datetime, timezone, timedelta
from urllib.parse import quote

NR = "http://127.0.0.1:1880"
tz8 = timezone(timedelta(hours=8))
ts = datetime.now(tz8).strftime("%Y-%m-%dT%H:%M:%S+08:00")


def block(name, w, r, sets=4):
    return name + " " + " ".join(
        f"{w:g}kg×{r} 第{i}组" for i in range(1, sets + 1)
    ) + " "


text = (
    "拉日容量："
    + block("坐姿划船", 35, 12)
    + block("T杆划船", 30, 12)
    + block("硬拉", 30, 12)
    + block("高位下拉", 40, 12)
    + block("EZ杠弯举", 7.5, 12)
    + block("山羊挺身", 0, 12, sets=3)
).strip()

print("=== 发送文本 ===")
print(text)
print()

url = f"{NR}/add-training?source=phone&time={quote(ts)}"
r = requests.post(url, data=text.encode("utf-8"),
                  headers={"Content-Type": "text/plain; charset=utf-8"}, timeout=30)
print(f"[{r.status_code}]")
try:
    print(r.json())
except Exception:
    print(r.text[:400])
