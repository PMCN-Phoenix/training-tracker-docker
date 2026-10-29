# -*- coding: utf-8 -*-
"""录入底座习惯（经 Node-RED /add-training 写入 InfluxDB）

用法：
    python enter_habit.py "睡眠7.5 有氧30 酒0 烟0 久坐达标"
    python enter_habit.py "睡眠7小时30分 有氧45 没喝酒 没抽烟 久坐未达标"
    python enter_habit.py --day 2026-10-18 "睡眠7.5 久坐达标"   # 精确补录某天
    python enter_habit.py --dry-run "睡眠7.5 有氧30"

归属规则：默认记「前一天 20:00」（早上录昨天）。消息含「今天」则记当天。
"""
import argparse
import sys
from datetime import datetime, timedelta, timezone

import requests

NR = "http://127.0.0.1:1880"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("text", nargs="+", help="习惯文本，例如 睡眠7.5 有氧30 酒0 烟0 久坐达标")
    ap.add_argument("--day", help="归属日期 YYYY-MM-DD（补录用），不填则按默认规则")
    ap.add_argument("--source", default="phone")
    ap.add_argument("--dry-run", action="store_true", help="只打印请求，不写入")
    args = ap.parse_args()

    text = " ".join(args.text).strip()
    tz8 = timezone(timedelta(hours=8))
    now = datetime.now(tz8)
    params = f"source={args.source}&time={now.strftime('%Y-%m-%dT%H:%M:%S+08:00')}"
    if args.day:
        datetime.strptime(args.day, "%Y-%m-%d")  # 校验格式
        params += f"&day={args.day}"
    url = f"{NR}/add-training?{params}"

    if args.dry_run:
        print(f"[dry-run] POST {url}")
        print(f"[dry-run] body: {text}")
        return 0

    s = requests.Session()
    s.trust_env = False  # 绕过系统代理拦截 localhost
    r = s.post(url, data=text.encode("utf-8"),
               headers={"Content-Type": "text/plain; charset=utf-8"}, timeout=30)
    try:
        body = r.json()
    except Exception:
        body = r.text[:200]
    print(f"[{r.status_code}] {text} -> {body}")
    return 0 if r.status_code == 200 else 1


if __name__ == "__main__":
    sys.exit(main())
