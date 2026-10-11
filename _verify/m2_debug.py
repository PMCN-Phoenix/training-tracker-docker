# -*- coding: utf-8 -*-
"""M2 失败点诊断：PR weight_kg / GET单条 / 删除404 / 晨脉 / stats"""
import requests, json, io, sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
API = "http://127.0.0.1:8001"
INFLUX = "http://127.0.0.1:8086"
ORG, BUCKET, TOKEN = "training-org", "training", "training-super-secret-token-2026"

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
            header = [h.rstrip('\r') for h in ln.split(',')]; continue
        if header:
            row = [v.rstrip('\r') for v in ln.split(',')]
            if len(row) == len(header):
                rows.append(dict(zip(header, row)))
    return rows

print("=== 1) PR 原始 CSV（平板卧推，最近2条测试）===")
q = f'''from(bucket:"{BUCKET}") |> range(start: -400d)
  |> filter(fn: (r) => r._measurement == "ppl_pr_test" and r.exercise == "平板卧推")
  |> sort(columns: ["_time"]) |> limit(n: 8)'''
rows = parse_csv(flux(q))
for r in rows:
    print(f"  _time={r.get('_time')} _field={r.get('_field')} _value={r.get('_value')} weight_kg_col={r.get('weight_kg')!r}")

print("=== 2) API /api/pr/tests 平板卧推最近一次 ===")
r = requests.get(f"{API}/api/pr/tests", timeout=30)
exs = {e["exercise"]: e for e in r.json()["data"]["exercises"]}
t = exs["平板卧推"]["tests"][-1]
print("  最近测试:", json.dumps(t, ensure_ascii=False)[:300])

print("=== 3) 感悟 CRUD 诊断 ===")
r = requests.post(f"{API}/api/reflections", json={"date": "2026-10-11", "content": "诊断补录",
                   "exercise": "平板卧推", "direction": "push", "set_index": 2, "tags": ["测试"], "source": "web"}, timeout=30)
print("  POST:", r.status_code, r.json())
rid = r.json()["data"]["id"]
r = requests.get(f"{API}/api/reflections/{rid}", timeout=30)
print("  GET:", r.status_code, json.dumps(r.json(), ensure_ascii=False)[:300])
r = requests.delete(f"{API}/api/reflections/{rid}", timeout=30)
print("  DELETE:", r.status_code, r.json())
r = requests.get(f"{API}/api/reflections/{rid}", timeout=30)
print("  删除后 GET:", r.status_code, r.text[:100])

print("=== 4) 晨脉原始查询（10-08 窗口）===")
q = f'''from(bucket:"{BUCKET}") |> range(start: 2026-10-07T16:00:00Z, stop: 2026-10-08T16:00:00Z)
  |> filter(fn: (r) => r._measurement == "ppl_morning_hr")'''
rows = parse_csv(flux(q))
print("  行数:", len(rows))
for r in rows[:5]:
    print(f"  _time={r.get('_time')} _field={r.get('_field')} _value={r.get('_value')}")

print("=== 5) stats 原始查询（distinct exercise）===")
q = f'''from(bucket:"{BUCKET}") |> range(start: -365d)
  |> filter(fn: (r) => r._measurement == "ppl_reflection" and r._field == "content")
  |> keep(columns: ["exercise"]) |> distinct(column: "exercise")'''
rows = parse_csv(flux(q))
print("  distinct 行数:", len(rows))
for r in rows[:6]:
    print(" ", json.dumps(r, ensure_ascii=False))

print("=== 6) 感悟原始 CSV（date=2026-10-08 全部）===")
q = f'''from(bucket:"{BUCKET}") |> range(start: -400d)
  |> filter(fn: (r) => r._measurement == "ppl_reflection" and r.date == "2026-10-08")
  |> keep(columns: ["_time", "_field", "_value", "id", "date", "direction", "exercise", "set_index", "session_id", "source", "content", "title", "tags"])'''
rows = parse_csv(flux(q))
print("  行数:", len(rows))
for r in rows[:12]:
    print(" ", json.dumps(r, ensure_ascii=False))
