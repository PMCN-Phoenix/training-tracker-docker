# -*- coding: utf-8 -*-
"""M1 端到端清理：删除 source=test 的测试数据（ppl_reflection + ppl_push_bench_flat）"""
import json, io, sys, urllib.request

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

URL = "http://127.0.0.1:8086/api/v2/delete?org=training-org&bucket=training"
TOKEN = "training-super-secret-token-2026"
HEADERS = {
    "Authorization": f"Token {TOKEN}",
    "Content-Type": "application/json",
}

for m in ["ppl_reflection", "ppl_push_bench_flat"]:
    body = json.dumps({
        "start": "2026-10-11T00:00:00Z",
        "stop": "2026-10-12T00:00:00Z",
        "predicate": f'_measurement="{m}" AND source="test"',
    }).encode("utf-8")
    req = urllib.request.Request(URL, data=body, method="POST", headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            print(f"{m}: HTTP {resp.status} (204=已删除)")
    except urllib.error.HTTPError as e:
        print(f"{m}: HTTP {e.code} {e.read().decode('utf-8', errors='replace')}")
