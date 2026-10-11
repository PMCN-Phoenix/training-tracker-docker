# -*- coding: utf-8 -*-
"""M5 清理：查看并删除 2026-10-11 的 e2e 测试训练数据（47.5kg×8 平板卧推）"""
import json
import urllib.request

INFLUX = "http://127.0.0.1:8086"
TOKEN = "training-super-secret-token-2026"
ORG = "training-org"
BUCKET = "training"


def q(flux):
    data = json.dumps({"query": flux}).encode("utf-8")
    req = urllib.request.Request(
        f"{INFLUX}/api/v2/query?org={ORG}",
        data=data,
        headers={"Authorization": f"Token {TOKEN}",
                 "Content-Type": "application/json", "Accept": "application/csv"},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8")


# 查 2026-10-11 有哪些 measurement 及行数
out = q(f'''
from(bucket: "{BUCKET}")
  |> range(start: 2026-10-11T00:00:00+08:00, stop: 2026-10-11T23:59:59+08:00)
  |> filter(fn: (r) => r._measurement == "ppl_push_bench_flat")
  |> group(columns: ["_measurement"])
  |> count(column: "_value")
''')
print("=== bench_flat 2026-10-11 ===")
print(out.strip())
