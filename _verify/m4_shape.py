# -*- coding: utf-8 -*-
"""M4 交叉测试：真实 API 创建/更新/删除感悟 → 当日 Markdown 同步一致性"""
import json
import os
import sys
import urllib.request

BASE = "http://127.0.0.1:8001/api"
TEST_DATE = "2026-10-11"   # 用测试专属日期，避免污染真实记录
pass_count = 0
fail_count = 0


def check(name, cond, extra=""):
    global pass_count, fail_count
    if cond:
        pass_count += 1
        print(f"  PASS {name} {extra}")
    else:
        fail_count += 1
        print(f"  FAIL {name} {extra}")


def req(method, path, body=None):
    data = json.dumps(body).encode("utf-8") if body else None
    r = urllib.request.Request(BASE + path, data=data, method=method,
                               headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(r, timeout=20) as resp:
        return json.loads(resp.read().decode("utf-8"))


def md_path():
    repo = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(repo, "docs", "记录", "训练感悟", f"{TEST_DATE}.md")


# 0. 清理测试日全部数据（幂等，TEST_DATE 为测试专属日期）
def clean_date():
    d = req("GET", f"/reflections?date={TEST_DATE}&limit=200")
    for item in d["data"].get("items", []):
        req("DELETE", f"/reflections/{item['id']}")


clean_date()

print("— 交叉：创建 → md 生成 —")
created = req("POST", "/reflections", {
    "content": "M4TEST 交叉测试感悟：平板第一组起桥要再稳。",
    "date": TEST_DATE, "direction": "push", "exercise": "平板卧推",
    "set_index": 1, "session_id": "s-m4test", "source": "api-test",
    "title": "", "tags": ["测试"],
})
rid = created["data"]["id"]
check("创建成功", created["code"] == 0 and rid)
check("md 文件已生成", os.path.exists(md_path()))
with open(md_path(), "r", encoding="utf-8") as f:
    md_text = f.read()
check("md 含该感悟 id", f"reflection_id: {rid}" in md_text)
check("md 含动作", "平板卧推" in md_text)
check("md 含内容", "起桥要再稳" in md_text)

print("— 交叉：GET markdown 接口读回一致 —")
g = req("GET", f"/reflections/markdown/{TEST_DATE}")
check("接口 code==0", g["code"] == 0)
check("接口 count==1", g["data"]["count"] == 1, f"got {g['data']['count']}")
rp = g["data"]["reflections"][0]
check("读回 id 一致", rp["id"] == rid)
check("读回 exercise 一致", rp.get("exercise") == "平板卧推")
check("读回 set_index 一致", rp.get("set_index") == 1)
check("读回 content 一致", "起桥要再稳" in (rp.get("content") or ""))

print("— 交叉：更新 → md 覆盖 —")
upd = req("PUT", f"/reflections/{rid}", {"content": "M4TEST 更新后：组间拉长到 3 分钟试试。"})
check("更新成功", upd["code"] == 0)
with open(md_path(), "r", encoding="utf-8") as f:
    md_text2 = f.read()
check("md 已覆盖新内容", "更新后" in md_text2)
check("md 无旧内容残留", "起桥要再稳" not in md_text2)
check("md 仍含同一 id", f"reflection_id: {rid}" in md_text2)

print("— 交叉：删除 → md 移除 —")
d = req("DELETE", f"/reflections/{rid}")
check("删除成功", d["code"] == 0)
check("md 文件已移除", not os.path.exists(md_path()))
g2 = req("GET", f"/reflections/markdown/{TEST_DATE}")
check("读回 count==0", g2["data"]["count"] == 0)

clean_date()  # 收尾清理
print(f"\n结果：PASS={pass_count} FAIL={fail_count}")
sys.exit(1 if fail_count else 0)
