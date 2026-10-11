# -*- coding: utf-8 -*-
"""M1 端到端 + 集成验证：HTTP POST 消息 -> Node-RED -> InfluxDB -> 查询断言 -> 清理测试数据。
用法: python m1_e2e.py
"""
import requests, json, sys, datetime

BASE = "http://127.0.0.1:1880"
INFLUX = "http://127.0.0.1:8086"
ORG = "training-org"
BUCKET = "training"
TOKEN = "training-super-secret-token-2026"

# 固定时间（UTC），便于窄窗口清理
T1 = "2026-10-11T03:00:00Z"   # 组级纯感悟
T2 = "2026-10-11T05:00:00Z"   # 日级推日
T3 = "2026-10-11T11:00:00Z"   # 混录（训练+感悟）
T4 = "2026-10-11T13:00:00Z"   # 纯训练（对照：无感悟）

MSGS = [
    ("平板卧推 第2组 感悟：肩胛锁死更稳", T1),
    ("推日 感悟：整体状态一般", T2),
    ("平板卧推 47.5kg×8 第1组 感悟：这组最顺", T3),
    ("杠铃深蹲 100kg×5 3组", T4),
]

def post(text, ts):
    r = requests.post(f"{BASE}/add-training?time={ts}", data=text.encode("utf-8"),
                      headers={"Content-Type": "text/plain; charset=utf-8"}, timeout=30)
    return r

def flux(query):
    r = requests.post(f"{INFLUX}/api/v2/query?org={ORG}", data=query.encode("utf-8"),
                      headers={"Authorization": f"Token {TOKEN}",
                               "Content-Type": "application/vnd.flux",
                               "Accept": "application/csv"}, timeout=30)
    r.raise_for_status()
    return r.text

def influx_delete(predicate, start, stop):
    r = requests.post(f"{INFLUX}/api/v2/delete?org={ORG}&bucket={BUCKET}",
                      json={"start": start, "stop": stop, "predicate": predicate},
                      headers={"Authorization": f"Token {TOKEN}"}, timeout=30)
    return r.status_code

def parse_csv(csv_text):
    """跟随每组 table 的 header 行解析（InfluxDB 按 field 分行，各自 header）"""
    header = None
    rows = []
    for ln in csv_text.strip().splitlines():
        if ln.startswith('#') or not ln:
            continue
        if ln.startswith(',result'):
            header = ln.split(',')
            continue
        if header:
            row = ln.split(',')
            if len(row) == len(header):
                rows.append(dict(zip(header, row)))
    return rows

pass_n = 0
fail_n = 0
def check(name, cond, extra=""):
    global pass_n, fail_n
    if cond:
        pass_n += 1
        print(f"  PASS {name}")
    else:
        fail_n += 1
        print(f"  FAIL {name} {extra}")

print("== 1) POST 4 条消息 ==")
for text, ts in MSGS:
    r = post(text, ts)
    print(f"  [{r.status_code}] {text[:28]} -> {r.json().get('message') if r.ok else r.text[:80]}")

print("== 2) 查询 ppl_reflection（窗口 10-11 全天）==")
csv = flux(f'''from(bucket:"{BUCKET}")
  |> range(start: 2026-10-10T00:00:00Z, stop: 2026-10-12T00:00:00Z)
  |> filter(fn: (r) => r._measurement == "ppl_reflection")''')
data_rows = parse_csv(csv)
refs = [r for r in data_rows if r.get('_field') == 'content']
check('感悟总数=3', len(refs) == 3, f"got {len(refs)}")
ref_map = {}
for r in refs:
    key = (r.get('date'), r.get('exercise'), r.get('set_index'))
    ref_map[key] = r
check('组级感悟存在(date/exercise/set_index)', ('2026-10-11', '平板卧推', '2') in ref_map)
g = ref_map.get(('2026-10-11', '平板卧推', '2'))
if g:
    check('组级-content字段', g.get('_value') == '肩胛锁死更稳', g.get('_value'))
    check('组级-id', str(g.get('id', '')).startswith('ref_20261011_'), g.get('id'))
    check('组级-direction', g.get('direction') == 'push')
check('日级感悟存在(无exercise)', any(not k[1] for k in ref_map.keys()))
day_key = [k for k in ref_map if not k[1]][0]
check('日级-direction=push', ref_map[day_key].get('direction') == 'push')
check('混录感悟存在(set_index=1)', ('2026-10-11', '平板卧推', '1') in ref_map)
m = ref_map.get(('2026-10-11', '平板卧推', '1'))
if m:
    check('混录-有session_id', bool(m.get('session_id')), m.get('session_id'))

print("== 3) 混录训练数据也写入 ==")
train_csv = flux(f'''from(bucket:"{BUCKET}")
  |> range(start: 2026-10-11T10:00:00Z, stop: 2026-10-11T12:00:00Z)
  |> filter(fn: (r) => r._measurement == "ppl_push_bench_flat")''')
train_rows = [r for r in parse_csv(train_csv) if r.get('_field') == 'reps']
check('混录-平板卧推组写入', len(train_rows) >= 1, f"got {len(train_rows)}")

print("== 4) 纯训练消息无感悟写入（对照）==")
all_refs = parse_csv(flux(f'''from(bucket:"{BUCKET}")
  |> range(start: 2026-10-10T00:00:00Z, stop: 2026-10-12T00:00:00Z)
  |> filter(fn: (r) => r._measurement == "ppl_reflection")'''))
content_refs = [r for r in all_refs if r.get('_field') == 'content']
check('纯训练不新增感悟(仍=3)', len(content_refs) == 3, f"got {len(content_refs)}")

print("== 5) 清理测试数据（窄窗口 10-11 全天，仅本次测试 measurement）==")
for meas in ["ppl_reflection", "ppl_push_bench_flat", "ppl_squat_back_squat"]:
    sc = influx_delete(f'_measurement="{meas}"', "2026-10-10T00:00:00Z", "2026-10-12T00:00:00Z")
    print(f"  delete {meas} -> {sc}")
after = parse_csv(flux(f'''from(bucket:"{BUCKET}")
  |> range(start: 2026-10-10T00:00:00Z, stop: 2026-10-12T00:00:00Z)
  |> filter(fn: (r) => r._measurement == "ppl_reflection")'''))
check('清理后感悟=0', len(after) == 0, f"got {len(after)}")

print(f"\nM1 端到端: {pass_n} PASS / {fail_n} FAIL")
sys.exit(0 if fail_n == 0 else 1)
