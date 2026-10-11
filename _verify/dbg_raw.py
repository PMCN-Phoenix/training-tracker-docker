# -*- coding: utf-8 -*-
import sys
sys.path.insert(0, r"D:\11.project\iwen-codex\codex-list\training-tracker-docker\web\backend")
from app.repositories.influx_client import db

flux = f'''
from(bucket: "{db.bucket}")
  |> range(start: -365d)
  |> filter(fn: (r) => r._measurement == "ppl_pr_test")
  |> keep(columns: ["_time", "session_id", "exercise", "direction", "weight_kg", "_field", "_value"])
  |> sort(columns: ["_time"])
'''
import urllib.request
url = f"{db.url}/api/v2/query?org={db.org}"
req = urllib.request.Request(url, data=flux.encode("utf-8"), method="POST")
req.add_header("Authorization", f"Token {db.token}")
req.add_header("Content-Type", "application/vnd.flux")
req.add_header("Accept", "application/csv")
with urllib.request.urlopen(req, timeout=30) as resp:
    raw = resp.read().decode("utf-8")
print("=== 原始 CSV 前 25 行 ===")
for i, ln in enumerate(raw.split("\n")[:25]):
    print(i, repr(ln))
