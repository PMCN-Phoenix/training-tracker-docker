# -*- coding: utf-8 -*-
"""录入 2026-11-01 拉日容量做组（用户口述，当晚录入）

- 6 动作：坐姿划船 35 / T杆 30 / 硬拉 35 / 高位下拉 40 / EZ弯举 7.5(单边) / 山羊挺身 2×12(原3组)
- 另有：仰卧肩胛前伸 2×10（技术块，Node-RED 未建别名 → 由 separate 脚本直写 ppl_tech_scapula_protraction）
- lumbar_status=none / 末组字段 → 覆盖补写（见 enter_1101_pull_fields.py）
- 晨脉 64 由 enter_hr.py 另行录入
"""
import requests
from urllib.parse import quote

NR = "http://127.0.0.1:1880"


def post(text):
    s = requests.Session()
    s.trust_env = False  # 规则 3：绕过系统代理
    url = f"{NR}/add-training?source=phone"
    r = s.post(url, data=text.encode("utf-8"),
               headers={"Content-Type": "text/plain; charset=utf-8"}, timeout=30)
    print(f"[{r.status_code}] {text[:50]}...")
    try:
        print("  ", r.json())
    except Exception:
        print("  ", r.text[:200])
    return r.status_code == 200


def block(name, w, r, sets=4):
    return " ".join(f"{name} {w:g}kg×{r} 第{i}组" for i in range(1, sets + 1))


ok = True
ok &= post(
    block("坐姿划船", 35, 12) + " "
    + block("T杆划船", 30, 12) + " "
    + block("硬拉", 35, 12) + " "
    + block("高位下拉", 40, 12) + " "
    + block("EZ杠弯举", 7.5, 12)
)
# 山羊挺身只做了 2 组（原处方 3 组）
ok &= post(block("山羊挺身", 0, 12, sets=2))
print("ALL OK" if ok else "SOME FAILED")
