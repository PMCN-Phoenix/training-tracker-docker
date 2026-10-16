# -*- coding: utf-8 -*-
"""M2 后端 API 验证：种子数据 + 全接口断言（原子/单元/交叉/集成/端到端）+ 精确清理
前置：Node-RED(1880) 已含 M1 感悟解析；后端 uvicorn 已起 8001。
用法: python m2_e2e.py
"""
import requests, json, sys

NR = "http://127.0.0.1:1880"
API = "http://127.0.0.1:8001"
INFLUX = "http://127.0.0.1:8086"
ORG, BUCKET, TOKEN = "training-org", "training", "training-super-secret-token-2026"

pass_n = fail_n = 0
def check(name, cond, extra=""):
    global pass_n, fail_n
    if cond:
        pass_n += 1
        print(f"  PASS {name}")
    else:
        fail_n += 1
        print(f"  FAIL {name} {extra}")

def nr_post(text, ts):
    r = requests.post(f"{NR}/add-training?time={ts}", data=text.encode("utf-8"),
                      headers={"Content-Type": "text/plain; charset=utf-8"}, timeout=30)
    return r

def api(method, path, **kw):
    r = requests.request(method, API + path, timeout=30, **kw)
    return r

def flux(q):
    r = requests.post(f"{INFLUX}/api/v2/query?org={ORG}", data=q.encode("utf-8"),
                      headers={"Authorization": f"Token {TOKEN}", "Content-Type": "application/vnd.flux",
                               "Accept": "application/csv"}, timeout=30)
    r.raise_for_status()
    return r.text

def parse_csv(txt):
    header = None; rows = []
    for ln in txt.strip().splitlines():
        if ln.startswith('#') or not ln.strip():
            continue
        if ln.startswith(',result'):
            header = ln.split(','); continue
        if header:
            row = ln.split(',')
            if len(row) == len(header):
                rows.append(dict(zip(header, row)))
    return rows

def influx_delete(predicate):
    r = requests.post(f"{INFLUX}/api/v2/delete?org={ORG}&bucket={BUCKET}",
                      json={"start": "2016-01-01T00:00:00Z", "stop": "2036-01-01T00:00:00Z",
                            "predicate": predicate},
                      headers={"Authorization": f"Token {TOKEN}"}, timeout=30)
    return r.status_code

print("== 0) 种子数据（消息录入，固定时间窗 10-08~10-09）==")
seed = [
    ("PR 平板卧推 60kg×5 55kg×8 50kg×10", "2026-10-08T09:00:00Z"),   # PR #1
    ("测试 平板卧推 62.5kg×3 57.5kg×6", "2026-10-09T09:00:00Z"),      # PR #2
    ("平板卧推 47.5kg×8 第1组 47.5kg×8 第2组 47.5kg×7 第3组 感悟：肩胛锁死更稳", "2026-10-08T12:00:00Z"),  # 训练3组+组级感悟
    ("晨脉 65 推日 感悟：整体状态一般", "2026-10-08T05:00:00Z"),         # 晨脉+日级感悟
    ("意象训练 50个意念卧推", "2026-10-08T12:30:00Z"),                   # 意象
]
for text, ts in seed:
    r = nr_post(text, ts)
    print(f"  [{r.status_code}] {text[:30]} -> {r.json().get('message') if r.ok else r.text[:80]}")

# ★ 种子 session / 感悟 id 推导（与 Node-RED 逻辑一致）：
#   session_id = "s"+毫秒戳；ref_id = "ref_YYYYMMDD(UTC+8)_"+毫秒戳hex末8位。
#   清理段只删这些 id，绝不枚举窗口内全部数据（防止误删真实数据 —— 10-16 曾因此误删 10-09 推日 PR）。
from datetime import datetime, timedelta

def _ms(ts):
    return int(datetime.fromisoformat(ts.replace("Z", "+00:00")).timestamp() * 1000)

SEED_SIDS = {"s" + str(_ms(ts)) for _, ts in seed}
SEED_REF_IDS = set()
for text, ts in seed:
    if any(k in text for k in ("感悟", "心得", "笔记")):
        ms = _ms(ts)
        d8 = (datetime.fromisoformat(ts.replace("Z", "+00:00")) + timedelta(hours=8)).strftime("%Y%m%d")
        SEED_REF_IDS.add(f"ref_{d8}_{ms:08x}")
SEED_IMAGERY_SID = "s" + str(_ms("2026-10-08T12:30:00Z"))

print("== 1) 感悟 CRUD 循环（原子）==")
r = api("POST", "/api/reflections", json={
    "date": "2026-10-08", "content": "补录：第2组发力感好", "exercise": "平板卧推",
    "direction": "push", "set_index": 2, "tags": ["发力感"], "source": "web"})
check("POST 创建", r.status_code == 200 and r.json()["data"]["id"], r.text[:100])
rid = r.json()["data"]["id"]
r = api("GET", f"/api/reflections/{rid}")
d = r.json()["data"]
check("GET 单条", d["content"] == "补录：第2组发力感好" and d["set_index"] == 2 and d["tags"] == ["发力感"])
r = api("PUT", f"/api/reflections/{rid}", json={"content": "补录：改成第2组更稳"})
check("PUT 更新", r.status_code == 200)
r = api("GET", f"/api/reflections/{rid}")
check("PUT 生效", r.json()["data"]["content"] == "补录：改成第2组更稳")
r = api("DELETE", f"/api/reflections/{rid}")
check("DELETE 删除", r.status_code == 200 and r.json()["data"]["deleted"] is True)
r = api("GET", f"/api/reflections/{rid}")
check("删除后 404", r.status_code == 404)

print("== 2) 感悟列表筛选（单元）==")
r = api("GET", "/api/reflections", params={"date": "2026-10-08"})
items = r.json()["data"]["items"]
check("按日筛-2条", len(items) == 2, f"got {len(items)}")
r = api("GET", "/api/reflections", params={"exercise": "平板卧推"})
check("按动作筛-1条", len(r.json()["data"]["items"]) == 1)
r = api("GET", "/api/reflections", params={"set_index": 1})
items = r.json()["data"]["items"]
check("按组号筛-1条", len(items) == 1 and items[0]["set_index"] == 1)
r = api("GET", "/api/reflections", params={"direction": "push"})
check("按方向筛", len(r.json()["data"]["items"]) >= 2)

print("== 3) 训练历史（交叉：与 InfluxDB 实查对账）==")
r = api("GET", "/api/training/exercise/平板卧推?start_date=2026-10-08&end_date=2026-10-09")
data = r.json()["data"]
check("exercise接口-窗口内仅训练session(不含PR/感悟)", data["total"] == 1, f"got {data['total']}")
s = data["sessions"][0]
check("session-3组", len(s["sets"]) == 3, f"got {len(s['sets'])}")
check("session-组顺序1-2-3", [x["set_index"] for x in s["sets"]] == [1, 2, 3])
check("session-重量", [x["weight_kg"] for x in s["sets"]] == [47.5, 47.5, 47.5])
check("session-次数", [x["reps"] for x in s["sets"]] == [8, 8, 7])
check("session-date(UTC+8)", s["date"] == "2026-10-08", s["date"])
check("session-direction", s["direction"] == "push")
# 与 InfluxDB 实查对账：训练组数
cnt = parse_csv(flux(f'''from(bucket:"{BUCKET}") |> range(start: 2026-10-08T00:00:00Z, stop: 2026-10-10T00:00:00Z)
  |> filter(fn: (r) => r._measurement == "ppl_push_bench_flat") |> filter(fn: (r) => r._field == "reps")'''))
check("交叉-实查训练组数一致", len(cnt) == 3, f"got {len(cnt)}")

print("== 4) PR 测试（集成）==")
r = api("GET", "/api/pr/tests?start_date=2026-10-08&end_date=2026-10-09")
exs = {e["exercise"]: e for e in r.json()["data"]["exercises"]}
check("PR-含平板卧推", "平板卧推" in exs)
t = exs["平板卧推"]["tests"]
# ★ 2026-10-16：断言改为容忍窗口内真实数据并存（共享库不假设独占；
#   真实 10-09 推日 PR 恢复后平板在该窗口有第 3 次测试，旧断言 len==2 会误报）
check("PR-至少2次测试(真实PR可并存)", len(t) >= 2, f"got {len(t)}")
check("PR-日期升序且编号递增",
      [x["date"] for x in t] == sorted(x["date"] for x in t)
      and all(t[i]["test_no"] < t[i + 1]["test_no"] for i in range(len(t) - 1)))
check("PR-#1 三档", [(p["weight_kg"], p["max_reps"]) for p in t[0]["points"]] == [(60, 5), (55, 8), (50, 10)],
      str(t[0]["points"]))
check("PR-#2 两档", [(p["weight_kg"], p["max_reps"]) for p in t[1]["points"]] == [(62.5, 3), (57.5, 6)],
      str(t[1]["points"]))

print("== 5) 按日全貌（端到端）==")
r = api("GET", "/api/day/2026-10-08")
d = r.json()["data"]
check("day-日期", d["date"] == "2026-10-08")
check("day-训练session 1个", len(d["sessions"]) == 1, f"got {len(d['sessions'])}")
check("day-session动作", d["sessions"][0]["exercise"] == "平板卧推")
check("day-日级感悟1条", len(d["day_reflections"]) == 1, f"got {len(d['day_reflections'])}")
check("day-日级无动作", d["day_reflections"][0].get("exercise") is None)
check("day-晨脉65", d["morning_hr"] and d["morning_hr"][0]["bpm"] == 65, str(d["morning_hr"]))
check("day-意象1次", d["imagery_count"] == 1, f"got {d['imagery_count']}")

print("== 6) 统计（交叉）==")
r = api("GET", "/api/reflections/stats")
st = r.json()["data"]
check("stats-总数≥2(种子2条)", st["total_count"] >= 2, str(st))
check("stats-覆盖动作≥1", st["exercise_count"] >= 1, str(st))

print("== 7) 精确清理（只删本测试种子的 session / id，不枚举窗口）==")
# ★ 2026-10-16 修复：旧逻辑枚举 10-08~10-10 窗口内全部 session 并全删，
#   曾误删真实数据（10-09 推日 PR 第三轮 23 档）。现只删种子推导出的 id。
for meas in ["ppl_pr_test", "ppl_push_bench_flat", "ppl_morning_hr", "ppl_reflection", "ppl_imagery"]:
    for sid in SEED_SIDS:
        influx_delete(f'_measurement="{meas}" AND session_id="{sid}"')
for rid in SEED_REF_IDS:
    influx_delete(f'_measurement="ppl_reflection" AND id="{rid}"')
# 验证清理：种子 session 无残留（窗口内真实数据不受影响、不做断言）
or_sids = " or ".join(f'r.session_id == "{sid}"' for sid in sorted(SEED_SIDS))
csv = flux(f'''from(bucket:"{BUCKET}") |> range(start: 2026-10-01T00:00:00Z, stop: 2026-10-20T00:00:00Z)
  |> filter(fn: (r) => r._measurement =~ /^ppl_(pr_test|push_bench_flat|morning_hr|reflection|imagery)$/)
  |> filter(fn: (r) => {or_sids})''')
check("清理后种子 session 无残留", len(parse_csv(csv)) == 0, f"got {len(parse_csv(csv))}")

print(f"\nM2 验证: {pass_n} PASS / {fail_n} FAIL")
sys.exit(0 if fail_n == 0 else 1)
