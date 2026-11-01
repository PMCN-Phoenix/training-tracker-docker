# -*- coding: utf-8 -*-
"""11-01 拉日补充字段写入（修复版：epoch ns 时间戳）"""
import time
from datetime import datetime, timezone

import requests

s = requests.Session()
s.trust_env = False
H = {"Authorization": "Token training-super-secret-token-2026",
     "Accept": "application/csv", "Content-Type": "application/vnd.flux"}
URL = "http://127.0.0.1:8086/api/v2/query?org=training-org"


def to_ns(ts):
    """RFC3339(可能不足9位小数) -> epoch 纳秒"""
    ts = ts.strip()
    if ts.endswith("Z"):
        ts = ts[:-1] + "+00:00"
    dt = datetime.fromisoformat(ts)
    return int(dt.timestamp() * 1_000_000_000)


q = '''from(bucket: "training")
  |> range(start: 2026-11-01T00:00:00+08:00)
  |> filter(fn: (r) => r._measurement == "ppl_pull_deadlift" or r._measurement == "ppl_pull_seated_row" or r._measurement == "ppl_pull_tbar_row" or r._measurement == "ppl_pull_lat_pulldown" or r._measurement == "ppl_pull_barbell_curl" or r._measurement == "ppl_pull_back_extension")
  |> filter(fn: (r) => r._field == "reps")
  |> keep(columns: ["_time", "_measurement", "set_index", "session_id", "source"])
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

write_lines = []
for p in points:
    m = p["_measurement"]
    sid = p.get("session_id", "")
    src = p.get("source", "phone")
    si = p.get("set_index", "")
    ns = to_ns(p["_time"])
    if m == "ppl_pull_deadlift":
        write_lines.append(
            f'{m},session_id={sid},source={src} lumbar_status="none" {ns}')
    last = "4" if m != "ppl_pull_back_extension" else "2"
    if si == last:
        write_lines.append(
            f'{m},session_id={sid},source={src} last_set_reps=12,form_break="none" {ns}')

print(f"待补写 {len(write_lines)} 条")
body = "\n".join(write_lines) + "\n"
w = s.post("http://127.0.0.1:8086/api/v2/write?org=training-org&bucket=training",
           headers={"Authorization": "Token training-super-secret-token-2026"},
           data=body.encode("utf-8"), timeout=30)
print("write:", w.status_code, w.text[:200] if w.status_code != 204 else "OK")

# 校验：回读硬拉的 lumbar_status 与 seated_row 末组字段
q2 = '''from(bucket: "training")
  |> range(start: 2026-11-01T00:00:00+08:00)
  |> filter(fn: (r) => r._measurement == "ppl_pull_deadlift" and r._field == "lumbar_status")
  |> count()'''
r2 = s.post(URL, headers=H, data=q2.encode("utf-8"), timeout=30)
for line in r2.text.splitlines():
    if line and not line.startswith("#"):
        v = line.split(",")
        print("硬拉 lumbar_status 点数:", v[5] if len(v) > 5 else line)
q3 = '''from(bucket: "training")
  |> range(start: 2026-11-01T00:00:00+08:00)
  |> filter(fn: (r) => r._field == "last_set_reps" or r._field == "form_break")
  |> group(columns: ["_measurement", "_field"])
  |> count()'''
r3 = s.post(URL, headers=H, data=q3.encode("utf-8"), timeout=30)
for line in r3.text.splitlines():
    if line and not line.startswith("#"):
        v = line.split(",")
        print("末组字段:", v[6] if len(v) > 6 else line, v[5] if len(v) > 5 else "", "=", v[4] if len(v) > 4 else "")
