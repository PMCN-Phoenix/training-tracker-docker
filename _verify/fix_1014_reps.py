# -*- coding: utf-8 -*-
"""修正 10-14 蹲日 4 条做组记录的 reps（按用户提供的当日 PR 最大值）。

矛盾记录（做组次数 > 当日同重量 PR 最大值，且错值恰为更低重量档 PR 值，判定串行录错）：
  杠铃深蹲 80kg x 17  -> 6   （PR: 80kg 最多 6 个）
  倒蹬/哈克 150kg x 19 -> 7   （PR: 150kg 最多 7 个）
  腿弯举   80kg x 20  -> 15  （PR: 80kg 最多 15 个）
  站姿提踵 100kg x 19 -> 5   （PR: 100kg 最大 5 个）

覆盖方式：同 measurement + 同标签集 + 同时间戳写 reps 字段（InfluxDB 字段级覆盖，
weight_kg 等其他字段原样保留）。已执行过一次，本脚本幂等可重跑。
"""
import requests

INFLUX = "http://127.0.0.1:8086"
ORG, TOKEN = "training-org", "training-super-secret-token-2026"
BUCKET = "training"
TS_NS = 1791941400000000000  # 2026-10-14T01:30:00Z

# (measurement, exercise_label, set_index, session_id, new_reps, old_reps)
FIXES = [
    ("ppl_squat_back_squat",    "杠铃深蹲",  "1", "s1791941400000", 6,  17),
    ("ppl_squat_leg_press_hack", "倒蹬/哈克", "1", "s1791941400000", 7,  19),
    ("ppl_squat_leg_curl",      "腿弯举",    "1", "s1791941400000", 15, 20),
    ("ppl_squat_calf_raise",    "站姿提踵",  "1", "s1791941400000", 5,  19),
]

HEADERS = {"Authorization": f"Token {TOKEN}"}


def write_lp(lines, precision="ns"):
    url = f"{INFLUX}/api/v2/write?org={ORG}&bucket={BUCKET}&precision={precision}"
    r = requests.post(url, data="\n".join(lines).encode("utf-8"),
                      headers={**HEADERS, "Content-Type": "text/plain"}, timeout=30)
    return r


def read_reps(measurement, exercise, session_id):
    q = f"""
from(bucket:"{BUCKET}")
  |> range(start: 2026-10-14T00:00:00Z, stop: 2026-10-14T23:59:59Z)
  |> filter(fn: (r) => r._measurement == "{measurement}")
  |> filter(fn: (r) => r.exercise == "{exercise}")
  |> filter(fn: (r) => r.session_id == "{session_id}")
  |> filter(fn: (r) => r._field == "reps")
"""
    r = requests.post(f"{INFLUX}/api/v2/query?org={ORG}", data=q.encode("utf-8"),
                      headers={**HEADERS, "Content-Type": "application/vnd.flux",
                               "Accept": "application/csv"}, timeout=30)
    r.raise_for_status()
    header = None
    for ln in r.text.splitlines():
        ln = ln.replace("\r", "")
        if ln.startswith("#") or not ln.strip():
            continue
        if ln.startswith(",result"):
            header = ln.split(",")
            continue
        if header:
            parts = ln.split(",")
            if len(parts) == len(header):
                return dict(zip(header, parts)).get("_value")
    return None


print("=== 写入前当前值 ===")
for m, ex, si, sid, new, old in FIXES:
    cur = read_reps(m, ex, sid)
    print(f"  {ex} {m}: reps={cur} (期望修正为 {new}, 原错值 {old})")

# 先按整数写；若字段实为浮点（类型冲突）则回退浮点写
lines_int = [
    f"{m},direction=squat,exercise={ex},set_index={si},source=phone,session_id={sid} reps={new}i {TS_NS}"
    for m, ex, si, sid, new, old in FIXES
]
r = write_lp(lines_int)
if r.status_code in (204, 200):
    print("\n整数写入成功（ reps=N i ）")
else:
    print(f"\n整数写入被拒（{r.status_code}）: {r.text[:200]}")
    print("回退为浮点写入（ reps=N ）...")
    lines_float = [
        f"{m},direction=squat,exercise={ex},set_index={si},source=phone,session_id={sid} reps={new} {TS_NS}"
        for m, ex, si, sid, new, old in FIXES
    ]
    r2 = write_lp(lines_float)
    if r2.status_code in (204, 200):
        print("浮点写入成功")
    else:
        print(f"浮点写入也失败（{r2.status_code}）: {r2.text[:300]}")
        raise SystemExit(1)

print("\n=== 写入后验证 ===")
ok = True
for m, ex, si, sid, new, old in FIXES:
    cur = read_reps(m, ex, sid)
    good = cur is not None and float(cur) == float(new)
    ok = ok and good
    print(f"  {ex}: reps={cur} {'OK' if good else 'FAIL(期望 ' + str(new) + ')'}")
print("\n结论:", "全部修正成功" if ok else "存在失败项")
