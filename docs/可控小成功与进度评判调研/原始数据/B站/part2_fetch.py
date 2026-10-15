# -*- coding: utf-8 -*-
"""阶段2：对精选 bvid 列表抓 aid/cid/评论/字幕。"""
import sys, os, re, json, time, hashlib, urllib.parse, requests
from pathlib import Path
sys.path.insert(0, r"D:\11.project\iwen-codex\bilibili-cookies")
from cookie_manager import BiliCookiePool

OUT_DIR = Path(r"D:\11.project\iwen-codex\codex-list\training-tracker-docker\docs\可控小成功与进度评判调研\原始数据\B站")
SUB_DIR = OUT_DIR / "字幕"
CMT_DIR = OUT_DIR / "评论"
SUB_DIR.mkdir(exist_ok=True)
CMT_DIR.mkdir(exist_ok=True)

PROXY = {"http": "http://127.0.0.1:7892", "https": "http://127.0.0.1:7892"}

MIXIN = [46,47,18,2,53,8,23,32,15,50,10,31,58,3,45,35,27,43,5,49,33,9,42,19,29,28,14,39,
         12,38,41,13,37,48,7,16,24,55,40,61,26,17,0,1,60,51,30,4,22,25,54,21,56,59,6,63,
         57,62,11,36,20,34,44,52]

def make_session(cookie):
    s = requests.Session()
    s.proxies.update(PROXY)
    s.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36",
        "Referer": "https://www.bilibili.com/",
        "Cookie": cookie,
    })
    return s

def get_wbi_keys(s):
    nav = s.get("https://api.bilibili.com/x/web-interface/nav", timeout=20).json()
    wbi = nav["data"]["wbi_img"]
    img = wbi["img_url"].rsplit("/", 1)[-1].split(".")[0]
    sub = wbi["sub_url"].rsplit("/", 1)[-1].split(".")[0]
    return "".join((img + sub)[i] for i in MIXIN)[:32]

def sign(p, mixin):
    p = dict(p)
    p["wts"] = str(int(time.time()))
    q = urllib.parse.urlencode(sorted(p.items()))
    p["w_rid"] = hashlib.md5((q + mixin).encode()).hexdigest()
    return p

def _extract_initial_state(t):
    """括号匹配提取 window.__INITIAL_STATE__={...}"""
    i = t.find("window.__INITIAL_STATE__=")
    if i < 0:
        return None
    j = t.find("{", i)
    if j < 0:
        return None
    depth = 0; k = j
    in_str = False; esc = False
    while k < len(t):
        c = t[k]
        if in_str:
            if esc:
                esc = False
            elif c == "\\":
                esc = True
            elif c == '"':
                in_str = False
        else:
            if c == '"':
                in_str = True
            elif c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
                if depth == 0:
                    break
        k += 1
    try:
        return json.loads(t[j:k+1])
    except Exception as e:
        print(f"  [parse err] {e}")
        return None

def fetch_video_info(s, bvid):
    """从网页 HTML 拿 aid/cid/title/desc/duration。"""
    r = s.get(f"https://www.bilibili.com/video/{bvid}/", timeout=25)
    t = r.text
    state = _extract_initial_state(t)
    if not state:
        return None
    v = state.get("videoData")
    if not v:
        return None
    return {
        "aid": v["aid"],
        "cid": v["cid"],
        "title": v["title"],
        "owner": v["owner"]["name"],
        "duration": v["duration"],
        "desc": v.get("desc", ""),
        "pages": [{"cid": p["cid"], "part": p.get("part",""), "duration": p.get("duration",0)} for p in v.get("pages",[])],
    }

def fetch_comments(s, bvid, aid, max_pages=15):
    """主评论 + 楼中楼。"""
    out = []
    for pn in range(1, max_pages + 1):
        try:
            d = s.get("https://api.bilibili.com/x/v2/reply",
                      params={"oid": aid, "type": 1, "pn": pn, "ps": 20, "sort": 2},
                      headers={"Referer": f"https://www.bilibili.com/video/{bvid}/"},
                      timeout=25).json()
        except Exception as e:
            print(f"  [cmt p{pn} exc] {e}")
            break
        dd = d.get("data") or {}
        reps = dd.get("replies") or []
        if not reps:
            break
        total = (dd.get("page") or {}).get("count", 0)
        for r in reps:
            item = {
                "uname": r["member"]["uname"],
                "like": r["like"],
                "rcount": r["rcount"],
                "rpid": r["rpid"],
                "message": r["content"]["message"],
                "subs": [],
            }
            # 楼中楼
            if r["rcount"] > 0:
                try:
                    d2 = s.get("https://api.bilibili.com/x/v2/reply/reply",
                               params={"oid": aid, "type": 1, "root": r["rpid"], "pn": 1, "ps": 20},
                               headers={"Referer": f"https://www.bilibili.com/video/{bvid}/"},
                               timeout=25).json()
                    for sub in ((d2.get("data") or {}).get("replies") or []):
                        item["subs"].append({
                            "uname": sub["member"]["uname"],
                            "like": sub["like"],
                            "message": sub["content"]["message"],
                        })
                    time.sleep(0.8)
                except Exception as e:
                    print(f"  [sub cmt exc] {e}")
            out.append(item)
        if len(out) >= total:
            break
        time.sleep(1.3)
    return out

def fetch_subtitle(s, bvid, cid, mixin):
    """wbi 字幕。返回 (body_list, lan, note)。"""
    q = sign({"bvid": bvid, "cid": str(cid), "web_location": "333.1007"}, mixin)
    try:
        d = s.get("https://api.bilibili.com/x/player/wbi/v2", params=q,
                  headers={"Referer": f"https://www.bilibili.com/video/{bvid}/"},
                  timeout=20).json()
    except Exception as e:
        return None, None, f"exc: {e}"
    subs = ((d.get("data") or {}).get("subtitle") or {}).get("subtitles") or []
    if not subs:
        return [], None, "no_subtitle"
    pick = next((x for pref in ["zh-Hans","zh-CN","zh","ai-zh"] for x in subs if x.get("lan") == pref), subs[0])
    u = pick["subtitle_url"]
    if u.startswith("//"):
        u = "https:" + u
    for attempt in range(4):
        try:
            body = s.get(u, headers={"Referer": f"https://www.bilibili.com/video/{bvid}/"}, timeout=25).json()["body"]
            if body:
                return body, pick.get("lan"), "ok"
        except Exception as e:
            time.sleep(3)
    return [], pick.get("lan"), "empty_after_retry"

def sec_to_ts(sec):
    sec = int(sec)
    h = sec // 3600; m = (sec % 3600) // 60; s = sec % 60
    return f"{h:02d}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"

def main():
    bv_file = OUT_DIR / "精选列表.json"
    bv_list = json.loads(bv_file.read_text(encoding="utf-8"))["bvid_list"]
    pool = BiliCookiePool()
    cookie = pool.get_cookie()
    s = make_session(cookie)
    mixin = get_wbi_keys(s)
    print(f"[ok] {len(bv_list)} videos to fetch")

    summary = []
    for i, bv in enumerate(bv_list, 1):
        print(f"\n[{i}/{len(bv_list)}] {bv}")
        try:
            info = fetch_video_info(s, bv)
            if not info:
                print("  [err] no video info")
                summary.append({"bvid": bv, "error": "no_info"})
                continue
            aid = info["aid"]; cid = info["cid"]
            print(f"  title: {info['title']} | dur={info['duration']}s | aid={aid} cid={cid}")

            # 字幕
            sub_body, lan, note = fetch_subtitle(s, bv, cid, mixin)
            sub_txt_path = None
            if sub_body:
                lines = []
                for seg in sub_body:
                    lines.append(f"[{sec_to_ts(seg['from'])}] {seg['content']}")
                txt = "\n".join(lines)
                (SUB_DIR / f"{bv}.txt").write_text(txt, encoding="utf-8")
                sub_txt_path = f"字幕/{bv}.txt"
                print(f"  [sub] {lan} {len(sub_body)} 段 -> {sub_txt_path}")
            else:
                print(f"  [sub] {note}")
            time.sleep(1.0)

            # 评论
            comments = fetch_comments(s, bv, aid, max_pages=10)
            cmt_obj = {
                "bvid": bv, "title": info["title"], "aid": aid, "cid": cid,
                "owner": info["owner"], "duration": info["duration"],
                "desc": info["desc"], "count": len(comments),
                "comments": comments,
            }
            (CMT_DIR / f"{bv}.json").write_text(json.dumps(cmt_obj, ensure_ascii=False, indent=2), encoding="utf-8")
            print(f"  [cmt] {len(comments)} 条")

            summary.append({
                "bvid": bv, "title": info["title"], "owner": info["owner"],
                "duration": info["duration"], "aid": aid, "cid": cid,
                "subtitle": sub_txt_path or note, "n_comments": len(comments),
            })
        except Exception as e:
            print(f"  [exc] {e}")
            summary.append({"bvid": bv, "error": str(e)})
        time.sleep(1.5)

    (OUT_DIR / "抓取摘要.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print("\n[done]")

if __name__ == "__main__":
    main()
