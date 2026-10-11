# -*- coding: utf-8 -*-
"""
训练数据查询层（健身版）
- get_exercise_history: 动作历史训练（按 session 分组）— 中栏数据源
- get_pr_tests: 全部动作 PR 测试（按动作+测试日期分组编号）— PR 总览/曲线/红标
- get_day_all: 某天全貌（训练组行 + 日级感悟 + 晨脉 + 意象）— 按日模式数据源
"""
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from .influx_client import db

# 15 个训练动作 measurement（与 flows.json parse-training 一致）
EX_MEASUREMENTS = [
    "ppl_push_bench_flat", "ppl_push_bench_incline", "ppl_push_bench_close",
    "ppl_push_overhead_press", "ppl_push_pec_deck",
    "ppl_pull_deadlift", "ppl_pull_seated_row", "ppl_pull_tbar_row",
    "ppl_pull_lat_pulldown", "ppl_pull_barbell_curl",
    "ppl_squat_back_squat", "ppl_squat_leg_press_hack", "ppl_squat_leg_extension",
    "ppl_squat_leg_curl", "ppl_squat_calf_raise",
]


def _ex_measurement_filter() -> str:
    conds = " or ".join(f'r._measurement == "{m}"' for m in EX_MEASUREMENTS)
    return f"({conds})"


def _utc_range_for_date(date_str: str) -> tuple:
    """北京时间日期 → UTC 时间窗 [start, stop)"""
    d = datetime.strptime(date_str, "%Y-%m-%d")
    start = d - timedelta(hours=8)                 # 北京 00:00 = UTC 前日 16:00
    stop = start + timedelta(days=1)
    return (start.strftime("%Y-%m-%dT%H:%M:%SZ"),
            stop.strftime("%Y-%m-%dT%H:%M:%SZ"))


def _date_from_utc(ts_str: str) -> str:
    """UTC 时间戳字符串 → 北京时间日期 YYYY-MM-DD"""
    dt = datetime.strptime(ts_str[:19], "%Y-%m-%dT%H:%M:%S")
    return (dt + timedelta(hours=8)).strftime("%Y-%m-%d")


def _flux_range(days: int, start_date: Optional[str] = None,
                end_date: Optional[str] = None) -> str:
    """构造 Flux range 子句：给出日期窗用 [start_utc, stop_utc)，否则按 days 回看"""
    if start_date and end_date:
        start_utc, _ = _utc_range_for_date(start_date)
        _, stop_utc = _utc_range_for_date(end_date)
        return f"range(start: {start_utc}, stop: {stop_utc})"
    return f"range(start: -{days}d)"


def _to_num(v) -> Optional[float]:
    if v is None or v == "":
        return None
    try:
        return float(v)
    except (ValueError, TypeError):
        return None


def get_exercise_history(exercise: str, days: int = 365,
                         start_date: Optional[str] = None,
                         end_date: Optional[str] = None) -> Dict[str, Any]:
    """某个动作的历史训练（按 session 分组，时间倒序；支持日期窗过滤）"""
    flux = f'''
from(bucket: "{db.bucket}")
  |> {_flux_range(days, start_date, end_date)}
  |> filter(fn: (r) => {_ex_measurement_filter()})
  |> filter(fn: (r) => r.exercise == "{exercise}")
  |> pivot(rowKey: ["_time"], columnKey: ["_field"], valueColumn: "_value")
  |> keep(columns: ["_time", "session_id", "direction", "exercise", "set_index", "weight_kg", "reps"])
  |> sort(columns: ["_time"])
'''
    rows = db.query(flux)

    # 按 session_id 分组（保持时间顺序）
    sessions = {}
    order = []
    for row in rows:
        sid = row.get("session_id", "")
        if not sid:
            continue
        if sid not in sessions:
            sessions[sid] = {
                "session_id": sid,
                "date": _date_from_utc(row.get("_time", "")),
                "direction": row.get("direction", ""),
                "exercise": exercise,
                "time": row.get("_time", ""),
                "sets": [],
            }
            order.append(sid)
        w = _to_num(row.get("weight_kg"))
        r = _to_num(row.get("reps"))
        si = row.get("set_index", "")
        sessions[sid]["sets"].append({
            "set_index": int(si) if si else None,
            "weight_kg": w,
            "reps": int(r) if r is not None else None,
        })

    # 每组内按 set_index 排序
    items = []
    for sid in order:
        s = sessions[sid]
        s["sets"] = sorted(s["sets"], key=lambda x: (x["set_index"] or 0))
        items.append(s)

    # 时间倒序（最新在前）
    items.sort(key=lambda x: x["time"], reverse=True)
    return {"exercise": exercise, "sessions": items, "total": len(items)}


def get_pr_tests(start_date: Optional[str] = None,
                 end_date: Optional[str] = None) -> Dict[str, Any]:
    """全部动作 PR 测试（按动作分组，测试按日期升序编号；支持日期窗过滤）"""
    flux = f'''
from(bucket: "{db.bucket}")
  |> {_flux_range(365, start_date, end_date)}
  |> filter(fn: (r) => r._measurement == "ppl_pr_test")
  |> keep(columns: ["_time", "session_id", "exercise", "direction", "weight_kg", "_field", "_value"])
  |> sort(columns: ["_time"])
'''
    rows = db.query(flux)

    # 按 (exercise, session_id) 分组
    sessions = {}
    order = []
    for row in rows:
        ex = row.get("exercise", "")
        sid = row.get("session_id", "")
        if not ex or not sid:
            continue
        key = (ex, sid)
        if key not in sessions:
            sessions[key] = {
                "exercise": ex,
                "direction": row.get("direction", ""),
                "session_id": sid,
                "date": _date_from_utc(row.get("_time", "")),
                "time": row.get("_time", ""),
                "points": [],
            }
            order.append(key)
        f = row.get("_field", "")
        v = row.get("_value", "")
        if f == "max_reps":
            w = _to_num(row.get("weight_kg"))
            sessions[key]["points"].append({
                "weight_kg": w,
                "max_reps": int(v) if v and _to_num(v) is not None else None,
            })

    # 组内档位按重量降序（PR 阶梯：重→轻，如 60kg→3 / 55kg→6）
    for key in order:
        sessions[key]["points"].sort(key=lambda p: (p["weight_kg"] or 0), reverse=True)

    # 按动作分组 + 测试按日期升序编号
    by_ex = {}
    for key in order:
        s = sessions[key]
        ex = s["exercise"]
        if ex not in by_ex:
            by_ex[ex] = {"exercise": ex, "direction": s["direction"], "tests": []}
        by_ex[ex]["tests"].append({
            "test_no": len(by_ex[ex]["tests"]) + 1,
            "date": s["date"],
            "session_id": s["session_id"],
            "points": s["points"],
        })

    items = list(by_ex.values())
    # 测试按日期升序（第1次=最早）
    for item in items:
        item["tests"].sort(key=lambda t: t["date"])
        for i, t in enumerate(item["tests"], 1):
            t["test_no"] = i
    # 动作按方向+名称排序
    items.sort(key=lambda x: (x["direction"], x["exercise"]))
    return {"exercises": items}


def get_training_calendar(days: int = 365) -> Dict[str, Any]:
    """训练日历：有训练的日期集合 + 有 PR 测试的日期集合（按天去重，升序）"""
    def _dates_for(flux: str) -> List[str]:
        seen = set()
        for row in db.query(flux):
            d = _date_from_utc(row.get("_time", ""))
            if d:
                seen.add(d)
        return sorted(seen)

    train_flux = f'''
from(bucket: "{db.bucket}")
  |> range(start: -{days}d)
  |> filter(fn: (r) => {_ex_measurement_filter()})
  |> keep(columns: ["_time"])
'''
    pr_flux = f'''
from(bucket: "{db.bucket}")
  |> range(start: -{days}d)
  |> filter(fn: (r) => r._measurement == "ppl_pr_test")
  |> keep(columns: ["_time"])
'''
    return {
        "training_dates": _dates_for(train_flux),
        "pr_dates": _dates_for(pr_flux),
    }


def get_day_all(date: str) -> Dict[str, Any]:
    """某天全貌：训练组行 + 日级感悟 + 晨脉 + 意象"""
    start_utc, stop_utc = _utc_range_for_date(date)

    # 训练组行（当天全部动作，按 session 分组）
    flux = f'''
from(bucket: "{db.bucket}")
  |> range(start: {start_utc}, stop: {stop_utc})
  |> filter(fn: (r) => {_ex_measurement_filter()})
  |> pivot(rowKey: ["_time"], columnKey: ["_field"], valueColumn: "_value")
  |> keep(columns: ["_time", "session_id", "direction", "exercise", "set_index", "weight_kg", "reps"])
  |> sort(columns: ["_time"])
'''
    rows = db.query(flux)
    sessions = {}
    order = []
    for row in rows:
        sid = row.get("session_id", "")
        if not sid:
            continue
        if sid not in sessions:
            sessions[sid] = {
                "session_id": sid,
                "exercise": row.get("exercise", ""),
                "direction": row.get("direction", ""),
                "time": row.get("_time", ""),
                "sets": [],
            }
            order.append(sid)
        w = _to_num(row.get("weight_kg"))
        r = _to_num(row.get("reps"))
        si = row.get("set_index", "")
        sessions[sid]["sets"].append({
            "set_index": int(si) if si else None,
            "weight_kg": w,
            "reps": int(r) if r is not None else None,
        })
    day_sessions = []
    for sid in order:
        s = sessions[sid]
        s["sets"] = sorted(s["sets"], key=lambda x: (x["set_index"] or 0))
        day_sessions.append(s)
    day_sessions.sort(key=lambda x: x["time"])

    # 日级感悟（date tag 匹配，内存筛无 exercise）
    flux = f'''
from(bucket: "{db.bucket}")
  |> range(start: -365d)
  |> filter(fn: (r) => r._measurement == "ppl_reflection")
  |> filter(fn: (r) => r.date == "{date}")
  |> pivot(rowKey: ["_time"], columnKey: ["_field"], valueColumn: "_value")
  |> keep(columns: ["_time", "id", "date", "direction", "exercise", "set_index", "session_id", "source", "content", "title", "tags"])
  |> sort(columns: ["_time"])
'''
    from .ppl_reflection_repo import _parse_reflection_row
    day_reflections = []
    for row in db.query(flux):
        parsed = _parse_reflection_row(row)
        if not parsed.get("exercise"):
            day_reflections.append(parsed)

    # 晨脉
    flux = f'''
from(bucket: "{db.bucket}")
  |> range(start: {start_utc}, stop: {stop_utc})
  |> filter(fn: (r) => r._measurement == "ppl_morning_hr")
  |> keep(columns: ["_time", "_value"])
'''
    morning_hr = []
    for row in db.query(flux):
        v = _to_num(row.get("_value"))
        if v is not None:
            morning_hr.append({"bpm": v, "time": row.get("_time", "")})

    # 意象
    flux = f'''
from(bucket: "{db.bucket}")
  |> range(start: {start_utc}, stop: {stop_utc})
  |> filter(fn: (r) => r._measurement == "ppl_imagery")
  |> keep(columns: ["_time"])
'''
    imagery_rows = db.query(flux)

    return {
        "date": date,
        "sessions": day_sessions,
        "day_reflections": day_reflections,
        "morning_hr": morning_hr,
        "imagery_count": len(imagery_rows),
    }
