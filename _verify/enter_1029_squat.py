# -*- coding: utf-8 -*-
"""录入 2026-10-29 蹲日容量做组（用户口述，当晚录入）

- 深蹲 60kg：12/12/12/15（末组 15 = AMRAP 性质）
- 哈克 100kg×15×4 / 腿屈伸 65kg×15×4 / 提踵 60kg×15×4
- 附加：深蹲第 3 组脉搏 124（动作级笔记）
- 归属时间：默认当前（当晚）
"""
import requests

NR = "http://127.0.0.1:1880"


def post(text):
    s = requests.Session()
    s.trust_env = False  # 规则 3：绕过系统代理拦截 localhost
    url = f"{NR}/add-training?source=phone"
    r = s.post(url, data=text.encode("utf-8"),
               headers={"Content-Type": "text/plain; charset=utf-8"}, timeout=30)
    print(f"[{r.status_code}] {text[:60]}...")
    try:
        print("  ", r.json())
    except Exception:
        print("  ", r.text[:200])
    return r.status_code == 200


def block(name, w, r, sets=4):
    return " ".join(f"{name} {w:g}kg×{r} 第{i}组" for i in range(1, sets + 1))


ok = True
# 深蹲末组 15 次，不能整块生成，单独拼
squat = " ".join(["深蹲 60kg×12 第1组", "深蹲 60kg×12 第2组",
                  "深蹲 60kg×12 第3组", "深蹲 60kg×15 第4组"])
ok &= post(squat)
ok &= post(block("哈克深蹲", 100, 15))
ok &= post(block("腿屈伸", 65, 15))
ok &= post(block("提踵", 60, 15))
ok &= post("深蹲 第3组 笔记 做组中第三组脉搏124")
print("ALL OK" if ok else "SOME FAILED")
