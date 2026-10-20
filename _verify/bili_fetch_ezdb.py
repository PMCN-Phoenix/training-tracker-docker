# -*- coding: utf-8 -*-
"""EZ杆 vs 哑铃弯举换算 · 评论 + 字幕抓取"""
import requests, time, json, re, hashlib, urllib.parse, sys, os

sys.path.insert(0, r"D:\11.project\iwen-codex\bilibili-cookies")
from cookie_manager import BiliCookiePool

MIXIN = [46,47,18,2,53,8,23,32,15,50,10,31,58,3,45,35,27,43,5,49,33,9,42,19,29,28,14,39,
         12,38,41,13,37,48,7,16,24,55,40,61,26,17,0,1,60,51,30,4,22,25,54,21,56,59,6,63,
         57,62,11,36,20,34,44,52]

OUT = r"D:\11.project\iwen-codex\codex-list\EZ杆哑铃换算-B站原始数据\raw"
os.makedirs(OUT, exist_ok=True)

TARGETS = [
    ("BV19H4y1k7Vs", "哑铃卧推20kg等于杠铃多少"),
    ("BV1DoL36oEKp", "二头弯举哑铃和杠铃区别"),
    ("BV1Jt411Q7jB", "杠铃or哑铃弯举-生理学"),
    ("BV1YanizfE6h", "哑铃弯举多少算及格"),
    ("BV1494y1N7hR", "哑铃弯举10kg什么水平"),
    ("BV14MeFz2EXr", "卧推80哑铃只能用25"),
    ("BV1am7WzJEQf", "唯一推荐哑铃弯举-小珂"),
    ("BV1Fp4y1d73D", "哑铃弯举详解-凯圣王"),
    ("BV1bRDgYCEgm", "哑铃弯举动作模式-卓叔"),
    ("BV1nPKUziEJz", "杠铃杆的区别"),
    ("BV14h4y187me", "各种杠铃杠多少公斤"),
    ("BV1zJ411T7UJ", "杠铃VS哑铃增肌-Jeremy"),
    ("BV1yt41167as", "你真的适合杠铃弯举吗"),
    ("BV1su4y177Fv", "杠铃弯举哑铃弯矩"),
    ("BV1BJ411y7HJ", "哑铃弯举VS锤式弯举"),
    ("BV1Ex41137H4", "Jeff-不要这样做哑铃弯举"),
    ("BV1GD4y1v7J1", "Jeremy-科学弯举指南"),
    ("BV1np421S7Qn", "哑铃弯举毁手腕"),
]

pool = BiliCookiePool()
s = requests.Session()
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")
s.headers.update({"User-Agent": UA, "Referer": "https://www.bilibili.com/"})

def refresh_mixin():
    s.headers["Cookie"] = pool.get_cookie()
    nav = s.get("https://api.bilibili.com/x/web-interface/nav", timeout=20).json()
    w = nav["data"]["wbi_img"]
    img = w["img_url"].rsplit("/", 1)[-1].split(".")[0]
    sub = w["sub_url"].rsplit("/", 1)[-1].split(".")[0]
    return "".join((img + sub)[i] for i in MIXIN)[:32]

MIX = refresh_mixin()

def sign(p):
    p = dict(p); p["wts"] = str(int(time.time()))
    q = urllib.parse.urlencode(sorted(p.items()))
    p["w_rid"] = hashlib.md5((q + MIX).encode()).hexdigest()
    return p

def get_meta(bvid):
    r = s.get(f"https://www.bilibili.com/video/{bvid}/", timeout=25)
    t = r.text
    m = (re.search(r"window\.__INITIAL_STATE__=(.*?);\(function", t, re.S)
         or re.search(r"window\.__INITIAL_STATE__=(.*?);\s*</script>", t, re.S))
    if not m:
        return None
    v = json.loads(m.group(1))["videoData"]
    return {
        "bvid": bvid, "aid": v["aid"], "cid": v["cid"], "title": v["title"],
        "owner": v["owner"]["name"], "desc": v.get("desc", "")[:800],
        "dur": v.get("duration"), "view": (v.get("stat") or {}).get("view"),
    }

def get_comments(aid, bvid, max_pages=8):
    items = []
    for pn in range(1, max_pages + 1):
        try:
            d = s.get("https://api.bilibili.com/x/v2/reply",
                      params={"oid": aid, "type": 1, "pn": pn, "ps": 20, "sort": 2},
                      headers={"Referer": f"https://www.bilibili.com/video/{bvid}/"},
                      timeout=25).json()
        except Exception:
            break
        if d.get("code") != 0:
            break
        dd = d.get("data") or {}
        reps = dd.get("replies") or []
        if not reps:
            break
        for r in reps:
            items.append({"user": (r.get("member") or {}).get("uname", ""),
                          "like": r.get("like", 0), "msg": r.get("content", {}).get("message", ""),
                          "rc": r.get("rcount", 0), "rpid": r.get("rpid")})
        total = (dd.get("page") or {}).get("count") or 0
        if len(items) >= total:
            break
        time.sleep(1.3)
    subs = []
    for it in [x for x in items if x["rc"] > 0][:8]:
        try:
            d2 = s.get("https://api.bilibili.com/x/v2/reply/reply",
                       params={"oid": aid, "type": 1, "root": it["rpid"], "pn": 1, "ps": 20},
                       headers={"Referer": f"https://www.bilibili.com/video/{bvid}/"},
                       timeout=25).json()
            for r in ((d2.get("data") or {}).get("replies") or []):
                subs.append({"user": (r.get("member") or {}).get("uname", ""),
                             "like": r.get("like", 0),
                             "msg": r.get("content", {}).get("message", "")})
            time.sleep(1.1)
        except Exception:
            continue
    return items, subs

def get_subtitle(bvid, cid):
    try:
        p = sign({"bvid": bvid, "cid": cid})
        d = s.get("https://api.bilibili.com/x/player/wbi/v2", params=p,
                  headers={"Referer": f"https://www.bilibili.com/video/{bvid}/"},
                  timeout=25).json()
        subs = (((d.get("data") or {}).get("subtitle") or {}).get("subtitles")) or []
        if not subs:
            return ""
        url = subs[0].get("subtitle_url", "")
        if url.startswith("//"):
            url = "https:" + url
        if not url:
            return ""
        j = requests.get(url, headers={"User-Agent": UA}, timeout=25).json()
        return "\n".join(x.get("content", "") for x in j.get("body", []))
    except Exception as e:
        print("   subtitle ERR", type(e).__name__)
        return ""

summary = []
for i, (bvid, tag) in enumerate(TARGETS, 1):
    d = os.path.join(OUT, bvid)
    os.makedirs(d, exist_ok=True)
    try:
        meta = get_meta(bvid)
        if not meta:
            print(f"[{i}/{len(TARGETS)}] {bvid} META FAIL")
            continue
        json.dump(meta, open(os.path.join(d, "meta.json"), "w", encoding="utf-8"),
                  ensure_ascii=False, indent=1)
        cm, subs = get_comments(meta["aid"], bvid)
        json.dump({"main": cm, "sub": subs},
                  open(os.path.join(d, "comments.json"), "w", encoding="utf-8"),
                  ensure_ascii=False, indent=1)
        sub = get_subtitle(bvid, meta["cid"])
        if sub:
            open(os.path.join(d, "subtitle.txt"), "w", encoding="utf-8").write(sub)
        summary.append({"bvid": bvid, "tag": tag, "title": meta["title"],
                        "comments": len(cm), "subs": len(subs),
                        "sub_chars": len(sub)})
        print(f"[{i}/{len(TARGETS)}] {bvid} {tag:<20} 评论{len(cm):>4}+{len(subs):>3} 字幕{len(sub):>6}字 | {meta['title'][:30]}")
    except Exception as e:
        print(f"[{i}/{len(TARGETS)}] {bvid} ERR {type(e).__name__}: {e}")
    time.sleep(1.6)

json.dump(summary, open(os.path.join(OUT, "_summary.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
print("\n完成。总评论:", sum(x["comments"] + x["subs"] for x in summary),
      "总字幕字数:", sum(x["sub_chars"] for x in summary))
