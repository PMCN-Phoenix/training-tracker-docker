# -*- coding: utf-8 -*-
"""11-13 推日补充字段写入（平板卧推末组：崩点 rep6）

- last_set_reps=8, form_break="rep6"（末组第 6 次起把持不住 = B1 崩点数据）
- 时间戳取实际入库点（epoch ns），字段级覆盖
"""
from datetime import datetime

import requests

s = requests.Session()
s.trust_env = False
H = {"Authorization": "Token training-super-secret-token-2026",
     "Accept": "application/csv", "Content-Type": "application/vnd.flux"}
URL = "http://127.0.0.1:8086/api/v2/query?org=training-org"


def to_ns(ts):
    ts = ts.strip()
    if ts.endswith("Z"):
        ts = ts[:-1] + "+00:00"
    return int(datetime.fromisoformat(ts).timestamp() * 1_000_000_000)


q = '''from(bucket: "training")
  |> range(start: 2026-11-13T00:00:00+08:00)
  |> filter(fn: (r) => r._measurement == "ppl_push_bench_flat" and r._field == "reps")
  |> keep(columns: ["_time", "set_index", "session_id", "source"])
  |> sort(columns: ["_time"])'''
r = s.post(URL, headers=H, data=q.encode("utf-8"), timeout=30)
r.raise_for_status()

cols = None
points = []
for line in r.text.splitlines():
    if line.startswith("#") or not line.strip():
        continue
    v = line.split(",")
    if cols is None:
        cols = v
        continue
    points.append(dict(zip(cols, v)))
print(f"平板卧推今日 {len(points)} 组")

write_lines = []
for p in points:
    sid = p.get("session_id", "")
    src = p.get("source", "phone")
    ns = to_ns(p["_time"])
    if p.get("set_index") == "4":
        write_lines.append(
            f'ppl_push_bench_flat,session_id={sid},source={src} last_set_reps=8,form_break="rep6" {ns}')

body = "\n".join(write_lines) + "\n"
w = s.post("http://127.0.0.1:8086/api/v2/write?org=training-org&bucket=training",
           headers={"Authorization": "Token training-super-secret-token-2026"},
           data=body.encode("utf-8"), timeout=30)
print("write:", w.status_code, w.text[:200] if w.status_code != 204 else "OK")

q2 = '''from(bucket: "training")
  |> range(start: 2026-11-13T00:00:00+08:00)
  |> filter(fn: (r) => r._measurement == "ppl_push_bench_flat" and (r._field == "last_set_reps" or r._field == "form_break"))
  |> keep(columns: ["_time", "_field", "_value"])'''
r2 = s.post(URL, headers=H, data=q2.encode("utf-8"), timeout=30)
for line in r2.text.splitlines():
    if line and not line.startswith("#"):
        print(line)
