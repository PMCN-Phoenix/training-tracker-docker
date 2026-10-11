# -*- coding: utf-8 -*-
"""M5 清理：删除 2026-10-11 的 e2e 测试训练数据（仅 ppl_push_bench_flat）"""
import json
import urllib.request

INFLUX = "http://127.0.0.1:8086"
TOKEN = "training-super-secret-token-2026"
ORG = "training-org"
BUCKET = "training"

body = json.dumps({
    "start": "2026-10-11T00:00:00+08:00",
    "stop": "2026-10-11T23:59:59+08:00",
    "predicate": '_measurement="ppl_push_bench_flat"',
}).encode("utf-8")
req = urllib.request.Request(
    f"{INFLUX}/api/v2/delete?org={ORG}&bucket={BUCKET}",
    data=body, method="POST",
    headers={"Authorization": f"Token {TOKEN}",
             "Content-Type": "application/json"},
)
with urllib.request.urlopen(req, timeout=30) as r:
    print("delete status:", r.status)

# 复核
data = json.dumps({"query": f'''
from(bucket: "{BUCKET}")
  |> range(start: 2026-10-11T00:00:00+08:00, stop: 2026-10-11T23:59:59+08:00)
  |> filter(fn: (r) => r._measurement == "ppl_push_bench_flat")
  |> count(column: "_value")
'''}).encode("utf-8")
req2 = urllib.request.Request(
    f"{INFLUX}/api/v2/query?org={ORG}", data=data,
    headers={"Authorization": f"Token {TOKEN}",
             "Content-Type": "application/json", "Accept": "application/csv"},
)
with urllib.request.urlopen(req2, timeout=30) as r:
    print("remaining:")
    print(r.read().decode("utf-8").strip())
