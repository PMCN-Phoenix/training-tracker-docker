# -*- coding: utf-8 -*-
"""补录推日 10-09 PR 第三轮到 InfluxDB（经 Node-RED /add-training，回填时间）
用户 10-16 提供的精确数值；首条时间戳与处方文档记载的 session s1791539043000 一致，
其余按库里既有 PR 数据的 30 分钟间隔 pattern。
"""
import requests
from urllib.parse import quote

NR = "http://127.0.0.1:1880"

# (动作消息, 北京时间) —— 间隔 30 分钟，对齐 10-11 拉日 PR 的录入 pattern
entries = [
    ("PR 推日 夹胸 35kg×18 40kg×16 45kg×13 50kg×10 55kg×9 60kg×5", "2026-10-09T17:44:03+08:00"),
    ("PR 推日 平板卧推 40kg×15 45kg×12 50kg×11 55kg×6 60kg×3", "2026-10-09T18:14:03+08:00"),
    ("PR 推日 上斜卧推 10kg×16 12.5kg×14 15kg×10 17.5kg×6", "2026-10-09T18:44:03+08:00"),
    ("PR 推日 窄距卧推 40kg×16 45kg×11 50kg×8 55kg×7 60kg×5", "2026-10-09T19:14:03+08:00"),
    ("PR 推日 站姿推举 10kg×13 12.5kg×8 15kg×6", "2026-10-09T19:44:03+08:00"),
]

for text, ts in entries:
    url = f"{NR}/add-training?source=phone&time={quote(ts)}"
    r = requests.post(url, data=text.encode("utf-8"),
                      headers={"Content-Type": "text/plain; charset=utf-8"}, timeout=30)
    msg = r.json().get("message") if r.headers.get("content-type", "").startswith("application/json") else r.text[:80]
    print(f"[{r.status_code}] {ts[11:19]} {text[:28]}... -> {msg}")

print("\n补录完成，下一步：查询验证")
