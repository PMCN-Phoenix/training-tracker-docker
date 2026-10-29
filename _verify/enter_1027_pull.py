# -*- coding: utf-8 -*-
"""录入 2026-10-27 拉日容量做组（用户口述，次日 10-28 补录）

- 6 动作：坐姿划船 / T杆划船 / 硬拉 / 高位下拉 / EZ杠弯举 / 山羊挺身
- 硬拉 30→35kg（+16.7%，相对 10-18 拉日加重）
- EZ 杠弯举：单边口径 7.5（与历史 19 组一致）
- 山羊挺身：口述 3x12~15，按下限 12 保守录入
- 归属时间：2026-10-27 20:00（用户未报具体训练时刻，按晚间默认值补录）
"""
import requests
from urllib.parse import quote

NR = "http://127.0.0.1:1880"
ts = "2026-10-27T20:00:00+08:00"  # 用户未报具体时刻，按晚间默认补录


def block(name, w, r, sets=4):
    return name + " " + " ".join(
        f"{w:g}kg×{r} 第{i}组" for i in range(1, sets + 1)
    ) + " "


text = (
    "拉日容量："
    + block("坐姿划船", 35, 12)
    + block("T杆划船", 30, 12)
    + block("硬拉", 35, 12)
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
