# -*- coding: utf-8 -*-
"""录入 2026-10-20 蹲日容量做组（用户口述）

处方对照（《做组处方-2026-10-16重算版》Day3 蹲日）：
  杠铃深蹲 4×12 @60kg  / 哈克 4×15 @100kg / 腿屈伸 4×15 @65kg
  站姿提踵 4×15 @50kg  / 腿弯举 4×15 @70kg

实际执行：前四项与处方一致，全满组；腿弯举按用户口述 20kg 录入（与 10-14 PR
65×20~80×15 差 3 倍以上，异常待用户确认：单腿口径 / 换机器 / 记错）。
按「记录事实优先」原则照录 20kg，不做推断改写。
"""
import urllib.request
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
    "蹲日容量："
    + block("杠铃深蹲", 60, 12)
    + block("哈克", 100, 15)
    + block("腿屈伸", 65, 15)
    + block("站姿提踵", 50, 15)
    + block("腿弯举", 20, 15)
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
