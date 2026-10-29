# -*- coding: utf-8 -*-
"""生成《外部对话交接包》的数据段（自动段）

用法: python gen_handoff.py
- 目标文件: codex-list/外部对话交接包.md
- 仅重写 <!-- AUTO:BEGIN --> ... <!-- AUTO:END --> 之间的内容，其余段落保留
- 数据源: InfluxDB（晨脉 / 底座习惯 / 做组记录 / PR 梯队）
- 镜像: 同步复制一份到 docs/简报/交接包-全量快照.md，随规则 1 的 git push 上 Gitee
- 约定: 每次录入数据或重大文档更新后跑一次，保持快照新鲜
"""
import re
import shutil
import sys
from datetime import datetime, timedelta, timezone

import requests

TARGET = r"D:\11.project\iwen-codex\codex-list\外部对话交接包.md"
MIRROR = r"D:\11.project\iwen-codex\codex-list\training-tracker-docker\docs\简报\交接包-全量快照.md"
INFLUX = "http://127.0.0.1:8086"
ORG, TOKEN = "training-org", "training-super-secret-token-2026"
TZ8 = timezone(timedelta(hours=8))


def flux(q):
    s = requests.Session()
    s.trust_env = False  # 绕过系统代理拦截 localhost
    r = s.post(f"{INFLUX}/api/v2/query?org={ORG}", data=q.encode("utf-8"),
               headers={"Authorization": f"Token {TOKEN}",
                        "Content-Type": "application/vnd.flux",
                        "Accept": "application/csv"}, timeout=30)
    if r.status_code != 200:
        print(f"[flux 400] {q[:200]}\n -> {r.text[:300]}")
    r.raise_for_status()
    return r.text


def parse_csv(txt):
    header, rows = None, []
    for ln in txt.strip().splitlines():
        ln = ln.replace("\r", "")
        if ln.startswith("#") or not ln.strip():
            continue
        if ln.startswith(",result"):
            header = ln.split(",")
            continue
        if header:
            row = ln.split(",")
            if len(row) == len(header):
                rows.append(dict(zip(header, row)))
    return rows


def t8(iso):
    """UTC ISO -> 北京时间字符串"""
    dt = datetime.fromisoformat(iso.replace("Z", "+00:00")).astimezone(TZ8)
    return dt


# ---------- ① 晨脉近 14 天 ----------
def sec_morning_hr():
    q = '''from(bucket:"training") |> range(start: -14d)
      |> filter(fn:(r) => r._measurement == "ppl_morning_hr" and r._field == "bpm")
      |> keep(columns:["_time","_value"]) |> sort(columns:["_time"])'''
    rows = parse_csv(flux(q))
    if not rows:
        return "_（近 14 天无晨脉记录）_"
    lines = ["| 日期 | 晨脉 bpm |", "|---|---|"]
    vals = []
    for r in rows:
        d = t8(r["_time"]).strftime("%m-%d")
        v = float(r["_value"])
        vals.append(v)
        lines.append(f"| {d} | {v:g} |")
    base = "64~68"
    abnormal = [v for v in vals if v >= 72]
    note = f"\n\n基线 {base}；14 天内 ≥72 的天数：{len(abnormal)}。规则：≥72 当天不追加负荷，≥75 触发四查（睡眠/酒精烟/前日负荷/疾病压力）。"
    return "\n".join(lines) + note


# ---------- ② 底座习惯近 7 天 ----------
def sec_habits():
    meas = [("ppl_habit_sleep", "hours", "睡眠h"),
            ("ppl_habit_cardio", "minutes", "有氧min"),
            ("ppl_habit_alcohol", "drinks", "酒"),
            ("ppl_habit_smoke", "cigarettes", "烟"),
            ("ppl_habit_sitting", "ok", "久坐✓")]
    days = {}
    for m, f, label in meas:
        q = f'''from(bucket:"training") |> range(start: -8d)
          |> filter(fn:(r) => r._measurement == "{m}" and r._field == "{f}")
          |> keep(columns:["_time","_value"])'''
        for r in parse_csv(flux(q)):
            d = t8(r["_time"]).strftime("%Y-%m-%d")
            days.setdefault(d, {})[label] = r["_value"]
    if not days:
        return "_（近 8 天无习惯记录）_"
    hdr = ["| 日期 | 睡眠h | 有氧min | 酒 | 烟 | 久坐 |", "|---|---|---|---|---|---|"]
    lines = list(hdr)
    sleeps, cardio, sit_ok, n = [], 0.0, 0, 0
    for d in sorted(days):
        c = days[d]
        sh = c.get("睡眠h", "")
        if sh != "":
            sleeps.append(float(sh))
        if c.get("有氧min", "") != "":
            cardio += float(c["有氧min"])
        if c.get("久坐✓", "") != "":
            n += 1
            if float(c["久坐✓"]) >= 1:
                sit_ok += 1
        lines.append(f"| {d[5:]} | {sh} | {c.get('有氧min','')} | {c.get('酒','')} "
                     f"| {c.get('烟','')} | {'✓' if c.get('久坐✓','')!='' and float(c['久坐✓'])>=1 else '✗'} |")
    savg = f"{sum(sleeps)/len(sleeps):.1f}" if sleeps else "—"
    lines.append(f"\n\n近 8 天汇总：睡眠均值 **{savg}h**（目标 7~8）· 有氧合计 **{cardio:g}min**（目标 ≥150/周）"
                 f"· 酒/烟见上表 · 久坐达标 {sit_ok}/{n} 天（目标 ≥5/7）。")
    return "\n".join(lines)


# ---------- ③ 做组记录（最近 21 天，按训练日汇总）----------
def sec_workouts():
    q = '''from(bucket:"training") |> range(start: -21d)
      |> filter(fn:(r) => r._measurement =~ /^ppl_(push|pull|squat)_/)
      |> filter(fn:(r) => r.source == "phone")
      |> filter(fn:(r) => r._field == "weight_kg" or r._field == "reps")
      |> pivot(rowKey:["_time","_measurement","exercise","set_index","session_id"], columnKey:["_field"], valueColumn:"_value")
      |> keep(columns:["_time","direction","exercise","weight_kg","reps"])
      |> sort(columns:["_time"])'''
    rows = parse_csv(flux(q))
    if not rows:
        return "_（近 21 天无做组记录）_"
    sessions = {}
    for r in rows:
        d = t8(r["_time"]).strftime("%Y-%m-%d")
        key = (d, r["direction"])
        s = sessions.setdefault(key, {"ex": {}, "vol": 0.0, "sets": 0})
        ex = r["exercise"]
        w = float(r.get("weight_kg") or 0)
        rp = float(r.get("reps") or 0)
        e = s["ex"].setdefault(ex, {"w": w, "reps": [], "dir": r["direction"]})
        e["reps"].append(rp)
        s["vol"] += w * rp
        s["sets"] += 1
    lines = ["| 日期 | 方向 | 动作明细 | 组数 | 容量(kg·次) |", "|---|---|---|---|---|"]
    for (d, direction) in sorted(sessions, reverse=True):
        s = sessions[(d, direction)]
        det = " / ".join(
            f"{ex}{e['w']:g}×{'_'.join(f'{r:g}' for r in e['reps'])}"
            for ex, e in s["ex"].items())
        lines.append(f"| {d} | {direction} | {det} | {s['sets']} | {s['vol']:g} |")
    lines.append("\n\n注：容量为 Σ重量×次数。**EZ杠弯举为单边口径（7.5=每手）**，拉日容量被系统性低估约 6.5%，"
                 "对比拉日容量阶梯时必须先对弯举 ×2 修正。次数均为「连续口径」（10-27 起，顶点静态维持不算次数）。")
    return "\n".join(lines)


# ---------- ④ PR 梯队（近 90 天最新测试）----------
def sec_pr():
    q = '''from(bucket:"training") |> range(start: -90d)
      |> filter(fn:(r) => r._measurement == "ppl_pr_test")
      |> filter(fn:(r) => r._field == "weight_kg" or r._field == "max_reps")
      |> drop(columns: ["weight_kg"])
      |> pivot(rowKey:["_time","exercise","set_index","session_id"], columnKey:["_field"], valueColumn:"_value")
      |> keep(columns:["_time","direction","exercise","weight_kg","max_reps"])
      |> sort(columns:["_time"])'''
    rows = parse_csv(flux(q))
    if not rows:
        return "_（近 90 天无 PR 测试记录）_"
    prs = {}
    for r in rows:
        d = t8(r["_time"]).strftime("%Y-%m-%d")
        ex = r["exercise"]
        prs.setdefault(ex, {"dir": r["direction"], "ladder": {}, "last": d})
        w = float(r["weight_kg"])
        rp = int(float(r["max_reps"]))
        cur = prs[ex]["ladder"].get(w)
        if cur is None or rp > cur[0]:
            prs[ex]["ladder"][w] = (rp, d)
    lines = ["| 动作 | 方向 | 档位→最大连续次数 | 最近测试 |", "|---|---|---|---|"]
    for ex in sorted(prs, key=lambda x: (prs[x]["dir"], x)):
        p = prs[ex]
        lad = " / ".join(f"{w:g}kg→{p['ladder'][w][0]}" for w in sorted(p["ladder"], reverse=True))
        lines.append(f"| {ex} | {p['dir']} | {lad} | {p['last']} |")
    return "\n".join(lines)


def main():
    auto = (
        "### 2.1 晨脉（近 14 天）\n\n" + sec_morning_hr() +
        "\n\n### 2.2 底座习惯（近 8 天）\n\n" + sec_habits() +
        "\n\n### 2.3 训练做组记录（近 21 天）\n\n" + sec_workouts() +
        "\n\n### 2.4 PR 梯队（近 90 天）\n\n" + sec_pr()
    )
    try:
        with open(TARGET, encoding="utf-8") as f:
            content = f.read()
        new = re.sub(r"(<!-- AUTO:BEGIN -->\n).*?(\n<!-- AUTO:END -->)",
                     lambda m: m.group(1) + auto + m.group(2), content, flags=re.S)
        if new == content:
            print("未找到 AUTO 标记或内容无变化，未写入")
            return 1
    except FileNotFoundError:
        print(f"目标文件不存在：{TARGET}（请先建手工骨架）")
        return 1
    with open(TARGET, "w", encoding="utf-8") as f:
        f.write(new)
    shutil.copyfile(TARGET, MIRROR)  # 镜像进仓库，随规则 1 推上 Gitee
    stamp = datetime.now(TZ8).strftime("%Y-%m-%d %H:%M")
    print(f"[OK] 数据段已更新 -> {TARGET}（{stamp}），镜像 -> docs/简报/交接包-全量快照.md")
    return 0


if __name__ == "__main__":
    sys.exit(main())
