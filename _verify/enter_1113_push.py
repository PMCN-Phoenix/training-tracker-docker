# -*- coding: utf-8 -*-
"""录入 2026-11-13 推日容量做组（M1 第 3 场，用户口述，当晚录入）

- 平板卧推 50kg×8×4（处方 3×8@50，实际做 4 组；末组第 6~8 次把持不住 → 崩点 rep6，由 fields 脚本补写）
- 上斜卧推 12.5kg（哑铃）×12×4
- 站姿推举 10kg×12×4
- 窄距卧推 40kg×12×4
- 夹胸 42.5kg×6×1（没劲了，提前收）
- 时间归属 2026-11-13 20:00（用户未报具体时刻）
"""
import time

import requests
from urllib.parse import quote

NR = "http://127.0.0.1:1880"
TS = "2026-11-13T20:00:00+08:00"


def post(text):
    s = requests.Session()
    s.trust_env = False  # 规则 3：绕过系统代理
    url = f"{NR}/add-training?source=phone&time={quote(TS)}"
    r = s.post(url, data=text.encode("utf-8"),
               headers={"Content-Type": "text/plain; charset=utf-8"}, timeout=30)
    print(f"[{r.status_code}] {text[:60]}")
    try:
        print("  ", r.json())
    except Exception:
        print("  ", r.text[:200])
    return r.status_code == 200


def block(name, w, r, sets=4):
    return " ".join(f"{name} {w:g}kg×{r} 第{i}组" for i in range(1, sets + 1))


ok = True
ok &= post(
    block("平板卧推", 50, 8) + " "
    + block("上斜卧推", 12.5, 12) + " "
    + block("站姿推举", 10, 12) + " "
    + block("窄距卧推", 40, 12)
)
ok &= post("夹胸 42.5kg×6 第1组")
time.sleep(1)
print("ALL OK" if ok else "SOME FAILED")
