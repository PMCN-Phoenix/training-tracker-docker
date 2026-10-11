# -*- coding: utf-8 -*-
import sys, json
sys.path.insert(0, r"D:\11.project\iwen-codex\codex-list\training-tracker-docker\web\backend")
from app.repositories import training_queries as tq
from app.repositories.influx_client import db

# 1. 先看 PR 原始查询行（debug：直接打前几行原始 CSV 的 weight_kg 列）
flux = f'''
from(bucket: "{db.bucket}")
  |> range(start: -365d)
  |> filter(fn: (r) => r._measurement == "ppl_pr_test")
  |> keep(columns: ["_time", "session_id", "exercise", "direction", "weight_kg", "_field", "_value"])
  |> sort(columns: ["_time"])
'''
rows = db.query(flux)
print("总行数:", len(rows))
for row in rows[:6]:
    print("  weight_kg=", repr(row.get("weight_kg")), "| max_reps=", row.get("_value"), "| ex=", row.get("exercise"), "| sid=", row.get("session_id"))

print()
data = tq.get_pr_tests()
for e in data["exercises"]:
    if e["exercise"] == "平板卧推":
        print(json.dumps(e, ensure_ascii=False, indent=1))
