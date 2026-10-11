# -*- coding: utf-8 -*-
"""M3 交叉测试：真实 API 响应形状 vs 前端 normalize 期望（跑在 3.11 python）"""
import json
import sys
import urllib.request

BASE = "http://127.0.0.1:8001/api"
pass_count = 0
fail_count = 0


def check(name, cond, extra=""):
    global pass_count, fail_count
    if cond:
        pass_count += 1
        print(f"  PASS {name} {extra}")
    else:
        fail_count += 1
        print(f"  FAIL {name} {extra}")


def get(path):
    with urllib.request.urlopen(BASE + path, timeout=20) as r:
        return json.loads(r.read().decode("utf-8"))


print("— 交叉：训练记录 exercise —")
d = get("/training/exercise/%E5%B9%B3%E6%9D%BF%E5%8D%A7%E6%8E%A8")  # 平板卧推
data = d["data"]
check("code==0", d["code"] == 0)
check("有 sessions 字段", isinstance(data.get("sessions"), list))
if data["sessions"]:
    s = data["sessions"][0]
    check("session 含 session_id/date/direction/sets",
          all(k in s for k in ("session_id", "date", "direction", "sets")))
    check("session 含 exercise 字段", bool(s.get("exercise")))
    st = s["sets"][0]
    check("组行含 set_index/weight_kg/reps",
          all(k in st for k in ("set_index", "weight_kg", "reps")))
    print(f"  样本: {s['date']} {len(s['sets'])}组 首组 {st['weight_kg']}kg×{st['reps']}")

print("— 交叉：PR tests —")
d = get("/pr/tests")
data = d["data"]
check("code==0", d["code"] == 0)
check("有 exercises 列表", isinstance(data.get("exercises"), list))
has_bench = False
for e in data["exercises"]:
    if e["exercise"] == "平板卧推":
        has_bench = True
        check("PR 含 exercise/direction/tests", all(k in e for k in ("exercise", "direction", "tests")))
        for t in e["tests"]:
            check("测试含 test_no/date/points", all(k in t for k in ("test_no", "date", "points")))
            if t["points"]:
                p = t["points"][0]
                check("档位含 weight_kg/max_reps", all(k in p for k in ("weight_kg", "max_reps")))
                break
        check("测试按日期升序编号", all(
            e["tests"][i]["test_no"] == i + 1 and e["tests"][i]["date"] >= e["tests"][i - 1]["date"]
            for i in range(1, len(e["tests"]))
        ))
        print(f"  平板卧推测试轮数={len(e['tests'])} 最近={e['tests'][-1]['date']}")
        break
check("平板卧推存在 PR 数据", has_bench)

print("— 交叉：reflections —")
d = get("/reflections?limit=50")
data = d["data"]
check("code==0", d["code"] == 0)
check("分页结构含 items/total", isinstance(data.get("items"), list) and "total" in data)
if data["items"]:
    r = data["items"][0]
    check("感悟含 id/date/content/exercise/set_index/tags",
          all(k in r for k in ("id", "date", "content", "exercise", "set_index", "tags")))
else:
    check("感悟字段结构（空库跳过）", True)

print("— 交叉：stats —")
d = get("/reflections/stats")
data = d["data"]
check("stats 含 total_count/today_count/consecutive_days/exercise_count",
      all(k in data for k in ("total_count", "today_count", "consecutive_days", "exercise_count")))

print("— 交叉：calendar —")
d = get("/training/calendar")
data = d["data"]
check("code==0", d["code"] == 0)
check("training_dates 升序", data["training_dates"] == sorted(data["training_dates"]))
check("pr_dates 是列表", isinstance(data["pr_dates"], list))

print("— 交叉：day 全貌 —")
if data["training_dates"]:
    day = data["training_dates"][-1]
    d = get(f"/day/{day}")
    data2 = d["data"]
    check("code==0", d["code"] == 0)
    check("day 含 sessions/day_reflections/morning_hr/imagery_count",
          all(k in data2 for k in ("sessions", "day_reflections", "morning_hr", "imagery_count")))
    print(f"  样本日 {day}: sessions={len(data2['sessions'])} 日级感悟={len(data2['day_reflections'])} 晨脉={len(data2['morning_hr'])} 意象={data2['imagery_count']}")

print(f"\n结果：PASS={pass_count} FAIL={fail_count}")
sys.exit(1 if fail_count else 0)
