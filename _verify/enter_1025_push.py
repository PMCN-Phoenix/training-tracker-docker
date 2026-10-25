# -*- coding: utf-8 -*-
"""录入 2026-10-25 推日容量做组（用户口述）

处方对照（《做组处方-2026-10-16重算版》Day1 推日，顺序：平板→上斜→推举→窄距→夹胸）：
  平板卧推 3×8+ @47.5kg（肩胛技术块期应为 3×10@37.5）
  上斜卧推 4×12 @12.5kg / 站姿推举 4×12 @10kg / 窄距卧推 4×12 @40kg / 夹胸 4×12 @42.5kg

实际执行（用户口述）：
  平板卧推 2×8+10 @50kg  → 按「2 组 8 次 + 1 组 10 次」录入（3 组，共 26 次）
  上斜卧推 4×12 @12.5kg / 站姿推举 4×12 @10kg
  窄距卧推 4×12 @40kg   / 夹胸 4×12 @42.5kg

两处偏离处方，如实记录、不改写：
  1. 平板 50kg（处方 47.5 试探档，且肩胛技术块期应为 37.5×3×10 慢速）
     用户说明：健身房无 1.25kg 片，47.5 不可达，45 之后只能跳 50。
  2. 平板组数 3 组（8/8/10），未做满处方 3×8+ 的次数判定线语义待复核。
"""
import urllib.request
from datetime import datetime, timezone, timedelta
from urllib.parse import quote

NR = "http://127.0.0.1:1880"
tz8 = timezone(timedelta(hours=8))
ts = datetime.now(tz8).strftime("%Y-%m-%dT%H:%M:%S+08:00")


def block(name, w, reps):
    """reps 为逐组次数列表，允许每组不同。"""
    parts = []
    for i, r in enumerate(reps, 1):
        parts.append(f"{w:g}kg×{r} 第{i}组")
    return name + " " + " ".join(parts) + " "


text = (
    "推日容量："
    + block("平板卧推", 50, [8, 8, 10])
    + block("上斜卧推", 12.5, [12, 12, 12, 12])
    + block("站姿推举", 10, [12, 12, 12, 12])
    + block("窄距卧推", 40, [12, 12, 12, 12])
    + block("夹胸", 42.5, [12, 12, 12, 12])
).strip()

print("=== 发送文本 ===")
print(text)
print()

url = f"{NR}/add-training?source=phone&time={quote(ts)}"
req = urllib.request.Request(
    url, data=text.encode("utf-8"),
    headers={"Content-Type": "text/plain; charset=utf-8"}, method="POST")
try:
    with urllib.request.urlopen(req, timeout=30) as r:
        print(f"[{r.status}]")
        print(r.read().decode("utf-8")[:400])
except Exception as e:
    print("ERR", e)
