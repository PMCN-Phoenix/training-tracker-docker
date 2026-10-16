# -*- coding: utf-8 -*-
"""查已有 PR 记录的完整字段结构（session_id/source/set_index），供补录对齐"""
import requests

INFLUX = "http://127.0.0.1:8086"
ORG, TOKEN = "training-org", "training-super-secret-token-2026"


def flux(q):
    r = requests.post(f"{INFLUX}/api/v2/query?org={ORG}", data=q.encode("utf-8"),
                      headers={"Authorization": f"Token {TOKEN}",
                               "Content-Type": "application/vnd.flux",
                               "Accept": "application/csv"}, timeout=30)
    r.raise_for_status()
    return r.text


def parse_csv(txt):
    header = None
    rows = []
    for ln in txt.strip().splitlines():
        ln = ln.replace("\r", "")
        if ln.startswith("#") or not ln.strip():
            continue
        if ln.startswith(",result"):
            header = ln.split(",")
            continue
        if header:
            row = ln.split(",")
            if len(row) == len(header):
                rows.append(dict(zip(header, row)))
    return rows


q = """
from(bucket:"training")
  |> range(start: -10d)
  |> filter(fn: (r) => r._measurement == "ppl_pr_test")
  |> filter(fn: (r) => r._field == "weight_kg" or r._field == "max_reps")
  |> drop(columns: ["weight_kg"])
  |> pivot(rowKey:["_time","exercise","set_index","session_id","source","direction"], columnKey:["_field"], valueColumn:"_value")
  |> group()
  |> keep(columns:["_time","direction","exercise","weight_kg","max_reps","session_id","source"])
  |> sort(columns:["_time"])
"""
rows = parse_csv(flux(q))
print("=== 已有 PR 记录结构（-10d，含 10-11 拉日 / 10-14 蹲日）===")
for r in rows[:20]:
    print(f"  {r['_time'][:19]} | {r['direction']:5s} | {r['exercise']:6s} | "
          f"{r['weight_kg']}kg x {r['max_reps']} | session={r.get('session_id')} | source={r.get('source')}")
print(f"\n共 {len(rows)} 条")

# 提取 session_id 与 _time 的对应关系（看 session_id 是否由消息时间生成）
print("\n=== session_id vs _time ===")
seen = set()
for r in rows:
    key = (r.get("session_id"), r["_time"][:16])
    if key not in seen:
        seen.add(key)
        print(f"  session={r.get('session_id')}  _time={r['_time'][:19]}")
