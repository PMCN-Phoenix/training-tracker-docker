# -*- coding: utf-8 -*-
"""查看底座习惯：近 14 天每日明细 + 近 7 天汇总

用法: python q_habit.py [天数]
"""
import collections
import datetime
import sys

import requests

INFLUX = "http://127.0.0.1:8086"
ORG = "training-org"
TOKEN = "training-super-secret-token-2026"

MEAS = {
    "ppl_habit_sleep": ("hours", "睡眠h"),
    "ppl_habit_cardio": ("minutes", "有氧min"),
    "ppl_habit_alcohol": ("drinks", "酒"),
    "ppl_habit_smoke": ("cigarettes", "烟"),
    "ppl_habit_sitting": ("ok", "久坐"),
}


def flux(q):
    r = requests.post(f"{INFLUX}/api/v2/query", params={"org": ORG},
                      headers={"Authorization": f"Token {TOKEN}",
                               "Accept": "application/csv",
                               "Content-Type": "application/vnd.flux"},
                      data=q.encode(), timeout=60)
    r.raise_for_status()
    lines = [l for l in r.text.split("\r\n") if l and not l.startswith("#")]
    if len(lines) < 2:
        return []
    hdr = lines[0].split(",")
    return [dict(zip(hdr, l.split(","))) for l in lines[1:]]


def bj_date(ts):
    t = datetime.datetime.fromisoformat(ts.replace("Z", "+00:00"))
    return (t + datetime.timedelta(hours=8)).strftime("%Y-%m-%d")


def main():
    days = int(sys.argv[1]) if len(sys.argv) > 1 else 14
    q = f'''from(bucket: "training")
  |> range(start: -{days}d)
  |> filter(fn: (r) => r._measurement =~ /^ppl_habit_/)
  |> keep(columns: ["_time", "_field", "_value", "_measurement"])
  |> sort(columns: ["_time"])'''
    rows = flux(q)
    if not rows:
        print(f"近 {days} 天没有任何底座习惯记录。")
        return

    daily = collections.defaultdict(dict)
    for r in rows:
        m = r["_measurement"]
        if m not in MEAS:
            continue
        field = MEAS[m][0]
        if r["_field"] != field:
            continue
        # 同一天多次写入时取最后一条（事件式：酒/烟取当天合计）
        d = bj_date(r["_time"])
        val = float(r["_value"])
        if m in ("ppl_habit_alcohol", "ppl_habit_smoke") and field in daily[d]:
            daily[d][m] = daily[d][m] + val
        else:
            daily[d][m] = val

    cols = list(MEAS.keys())
    print(f"{'日期':<12}" + "".join(f"{MEAS[m][1]:>9}" for m in cols))
    for d in sorted(daily):
        cells = []
        for m in cols:
            v = daily[d].get(m)
            if m == "ppl_habit_sitting":
                cells.append("  ✓" if v == 1 else ("  ✗" if v == 0 else "  -"))
            elif v is None:
                cells.append("  -")
            else:
                cells.append(f"{v:g}")
        print(f"{d:<12}" + "".join(f"{c:>9}" for c in cells))

    # 近 7 天汇总
    cutoff = (datetime.date.today() - datetime.timedelta(days=7)).isoformat()
    recent = {d: v for d, v in daily.items() if d >= cutoff}
    sleep_vals = [v["ppl_habit_sleep"] for v in recent.values() if "ppl_habit_sleep" in v]
    cardio_vals = [v["ppl_habit_cardio"] for v in recent.values() if "ppl_habit_cardio" in v]
    alc = sum(v.get("ppl_habit_alcohol", 0) for v in recent.values())
    smoke = sum(v.get("ppl_habit_smoke", 0) for v in recent.values())
    sit = [v["ppl_habit_sitting"] for v in recent.values() if "ppl_habit_sitting" in v]

    print("\n近 7 天汇总（目标）")
    if sleep_vals:
        avg = sum(sleep_vals) / len(sleep_vals)
        print(f"  睡眠均值  {avg:.1f} h      （目标 7~8）  {len(sleep_vals)} 天有记录")
    if cardio_vals:
        total = sum(cardio_vals)
        print(f"  有氧合计  {total:.0f} min   （目标 ≥150） {len(cardio_vals)} 天有记录")
    print(f"  酒精      {alc:.0f} 次      （目标 ≤2）")
    print(f"  吸烟      {smoke:.0f} 支      （目标 0）")
    if sit:
        print(f"  久坐达标  {sum(sit):.0f}/{len(sit)} 天（目标 ≥5/7）")


if __name__ == "__main__":
    main()
