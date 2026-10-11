# -*- coding: utf-8 -*-
"""M1 端到端：写 4 条测试消息文件（utf-8 无 BOM）+ Flux 查询脚本"""
import io, sys, os

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
BASE = r"D:\11.project\iwen-codex\codex-list\training-tracker-docker\_verify\m1_e2e"
os.makedirs(BASE, exist_ok=True)

cases = [
    ("msg1_group.txt", "平板卧推 第2组 感悟：肩胛锁死更稳"),
    ("msg2_action.txt", "平板卧推 感悟：今天上胸感觉好"),
    ("msg3_day.txt", "推日 感悟：整体状态一般"),
    ("msg4_mix.txt", "平板卧推 47.5kg×8 第1组 感悟：这组最顺"),
]
for name, text in cases:
    with open(os.path.join(BASE, name), "w", encoding="utf-8", newline="") as f:
        f.write(text)
    print("写出:", name)

# Flux 查询：全部 ppl_reflection（测试用，按 source=test 过滤）
flux = '''
from(bucket: "training")
  |> range(start: -1h)
  |> filter(fn: (r) => r._measurement == "ppl_reflection" and r.source == "test")
  |> keep(columns: ["_time", "_field", "_value", "id", "date", "direction", "exercise", "set_index", "session_id", "source"])
  |> sort(columns: ["_time"])
'''
with open(os.path.join(BASE, "query_refs.flux"), "w", encoding="utf-8", newline="") as f:
    f.write(flux)
print("写出: query_refs.flux")

# Flux 查询：检查测试训练组是否也落库（混录消息）
flux2 = '''
from(bucket: "training")
  |> range(start: -1h)
  |> filter(fn: (r) => r._measurement == "ppl_push_bench_flat" and r.source == "test")
  |> keep(columns: ["_time", "_field", "_value", "exercise", "set_index", "session_id", "source"])
'''
with open(os.path.join(BASE, "query_train.flux"), "w", encoding="utf-8", newline="") as f:
    f.write(flux2)
print("写出: query_train.flux")
