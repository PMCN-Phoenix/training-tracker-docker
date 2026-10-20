# -*- coding: utf-8 -*-
import json, os, re, glob, collections

BASE = r"D:\11.project\iwen-codex\codex-list\EZ杆弯举-B站原始数据\raw"

allc = []
for f in glob.glob(os.path.join(BASE, "*", "comments.json")):
    bvid = os.path.basename(os.path.dirname(f))
    d = json.load(open(f, encoding="utf-8"))
    for c in d.get("main", []):
        allc.append({"bv": bvid, "like": c["like"], "msg": c["msg"], "kind": "主评"})
    for c in d.get("sub", []):
        allc.append({"bv": bvid, "like": c["like"], "msg": c["msg"], "kind": "楼中楼"})

print("总评论条数：", len(allc))

THEMES = {
    "手腕不适/疼痛": r"手腕|腕|腱鞘|tfcc",
    "肘部不适/疼痛": r"肘|肘关节|网球肘|高尔夫球肘",
    "曲杆/EZ 相关": r"曲杆|曲杠|ez|w杆|w杠",
    "直杆对比": r"直杆|直杠|直棍",
    "握距": r"握距|握宽|握窄|间距",
    "手肘位置": r"手肘|肘部位置|肘夹|夹肘",
    "重量/配重": r"重量|配重|多少kg|多少公斤|多重",
    "酸痛/发力感": r"酸痛|发力|泵感|充血|没感觉",
    "杆重/器械": r"杆重|空杆|杆子多少|健身房没有",
}
cnt = collections.Counter()
for c in allc:
    for k, p in THEMES.items():
        if re.search(p, c["msg"], re.I):
            cnt[k] += 1
print("\n=== 主题命中数 ===")
for k, v in cnt.most_common():
    print(f"{k:<14} {v:>4}")

print("\n=== 高赞评论 TOP 45 ===")
for c in sorted(allc, key=lambda x: -x["like"])[:45]:
    m = re.sub(r"\s+", " ", c["msg"]).strip()
    if len(m) < 4:
        continue
    print(f"[{c['like']:>4}赞] {c['bv']} {c['kind']} | {m[:110]}")

print("\n=== 提到手腕的评论（按赞）===")
hw = [c for c in allc if re.search(r"手腕|腕", c["msg"])]
for c in sorted(hw, key=lambda x: -x["like"])[:18]:
    m = re.sub(r"\s+", " ", c["msg"]).strip()
    print(f"[{c['like']:>4}] {m[:120]}")

print("\n=== 提到曲杆/EZ（按赞）===")
hz = [c for c in allc if re.search(r"曲杆|曲杠|ez|w杆|w杠", c["msg"], re.I)]
for c in sorted(hz, key=lambda x: -x["like"])[:18]:
    m = re.sub(r"\s+", " ", c["msg"]).strip()
    print(f"[{c['like']:>4}] {m[:120]}")
