# -*- coding: utf-8 -*-
"""EZ杆 vs 哑铃弯举换算 · 评论主题分析"""
import json, os, re, glob, collections

RAW = r"D:\11.project\iwen-codex\codex-list\EZ杆哑铃换算-B站原始数据\raw"

allc = []
for d in sorted(glob.glob(os.path.join(RAW, "BV*"))):
    cf = os.path.join(d, "comments.json")
    mf = os.path.join(d, "meta.json")
    if not os.path.exists(cf):
        continue
    meta = json.load(open(mf, encoding="utf-8")) if os.path.exists(mf) else {}
    j = json.load(open(cf, encoding="utf-8"))
    for c in j.get("main", []):
        allc.append({**c, "src": meta.get("title", "")[:26], "bvid": os.path.basename(d), "kind": "main"})
    for c in j.get("sub", []):
        allc.append({**c, "src": meta.get("title", "")[:26], "bvid": os.path.basename(d), "kind": "sub"})

print("评论总数:", len(allc))

# ---- 1) 提到具体重量数字 + 换算语义的评论 ----
kw_conv = re.compile(r"等于|换算|换成|换到|相当于|换算成|一半|除以2|除以 2|两个手|双手|单手|一边|每边|每只|一只|两边")
kw_num = re.compile(r"\d+(\.\d+)?\s*(kg|KG|Kg|公斤|千克|斤|lb|磅)")
hits = []
for c in allc:
    m = c["msg"]
    if kw_conv.search(m) and kw_num.search(m) or ("ez" in m.lower() and kw_num.search(m)):
        if 8 <= len(m) <= 400:
            hits.append(c)
hits.sort(key=lambda x: -x["like"])
print("\n" + "=" * 100)
print("【A】含『换算语义 + 具体重量』的评论  %d 条  (按赞排序 TOP 40)" % len(hits))
print("=" * 100)
for c in hits[:40]:
    print(f"[{c['like']:>4}赞] {c['src']}")
    print(f"      {c['msg'][:300]}")
    print()

# ---- 2) 只提到 EZ / 曲杆 且带数字的 ----
print("\n" + "=" * 100)
print("【B】提到 EZ/曲杆 且含重量数字  (TOP 25)")
print("=" * 100)
h2 = [c for c in allc if re.search(r"ez|曲杆|曲杠|弯杆", c["msg"], re.I) and kw_num.search(c["msg"])]
h2.sort(key=lambda x: -x["like"])
for c in h2[:25]:
    print(f"[{c['like']:>4}赞] {c['src']}")
    print(f"      {c['msg'][:280]}")
    print()

# ---- 3) 器械选择倾向：谁推荐哪个 ----
print("\n" + "=" * 100)
print("【C】明确表达『选哑铃』或『选杠铃/EZ』的评论")
print("=" * 100)
pat_db = re.compile(r"(用|选|推荐|更喜欢|还是).{0,6}哑铃|哑铃.{0,4}(更好|更舒服|更推荐|自由)")
pat_bb = re.compile(r"(用|选|推荐|更喜欢|还是).{0,6}(杠铃|ez|曲杆)|(杠铃|ez|曲杆).{0,4}(更好|更舒服|更推荐)")
db = sorted([c for c in allc if pat_db.search(c["msg"]) and 10 <= len(c["msg"]) <= 300], key=lambda x: -x["like"])
bb = sorted([c for c in allc if pat_bb.search(c["msg"]) and 10 <= len(c["msg"]) <= 300], key=lambda x: -x["like"])
print(f"-- 倾向哑铃 {len(db)} 条 --")
for c in db[:15]:
    print(f"[{c['like']:>4}] {c['msg'][:200]}")
print(f"\n-- 倾向杠铃/EZ {len(bb)} 条 --")
for c in bb[:15]:
    print(f"[{c['like']:>4}] {c['msg'][:200]}")

# ---- 4) 痛苦/不适/受伤 主题（器械切换的动因）----
print("\n" + "=" * 100)
print("【D】手腕/肘 疼痛与不适（换器械的核心动因）")
print("=" * 100)
kw_pain = re.compile(r"手腕|腕|肘|疼|痛|伤|不舒服|难受")
p = sorted([c for c in allc if kw_pain.search(c["msg"]) and 10 <= len(c["msg"]) <= 300], key=lambda x: -x["like"])
print(f"共 {len(p)} 条，TOP 18：")
for c in p[:18]:
    print(f"[{c['like']:>4}] {c['msg'][:220]}")

# ---- 5) 具体数字统计：评论里出现的『哑铃 X kg 做 N 次』----
print("\n" + "=" * 100)
print("【E】评论中出现的哑铃弯举重量自述")
print("=" * 100)
pat = re.compile(r"(\d+(?:\.\d+)?)\s*(?:kg|KG|Kg|公斤)\s*.{0,8}?(?:做|×|x|X)?\s*(\d+)?\s*(?:个|次)?")
cnt = collections.Counter()
for c in allc:
    m = c["msg"]
    if "哑铃" not in m and "弯举" not in m:
        continue
    for g in re.finditer(r"(\d+(?:\.\d+)?)\s*(?:kg|KG|Kg|公斤)", m):
        v = float(g.group(1))
        if 2 <= v <= 60:
            cnt[v] += 1
for v, n in cnt.most_common(20):
    print(f"  {v:>5g}kg 出现 {n:>3} 次")
