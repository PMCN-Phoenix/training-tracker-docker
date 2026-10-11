# -*- coding: utf-8 -*-
import requests

def flux(q):
    r = requests.post("http://127.0.0.1:8086/api/v2/query?org=training-org", data=q.encode("utf-8"),
                      headers={"Authorization": "Token training-super-secret-token-2026",
                               "Content-Type": "application/vnd.flux", "Accept": "application/csv"}, timeout=30)
    return r.text

print("===== PR narrow 查询原始 CSV =====")
print(flux('''from(bucket:"training") |> range(start: -365d)
  |> filter(fn: (r) => r._measurement == "ppl_pr_test")
  |> keep(columns: ["_time", "session_id", "exercise", "direction", "weight_kg", "_field", "_value"])
  |> sort(columns: ["_time"])''')[:1500])
