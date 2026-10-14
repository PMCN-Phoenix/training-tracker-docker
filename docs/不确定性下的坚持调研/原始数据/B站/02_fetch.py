# -*- coding: utf-8 -*-
"""深抓17个精选B站视频：HTML拿aid/cid -> wbi评论 -> wbi字幕。"""
import sys, re, json, time, hashlib, urllib.parse, pathlib
import requests

sys.path.insert(0, r"D:\11.project\iwen-codex\bilibili-cookies")
from cookie_manager import BiliCookiePool

OUT = pathlib.Path(r"D:\11.project\iwen-codex\codex-list\training-tracker-docker\docs\不确定性下的坚持调研\原始数据\B站")
SUB_DIR = OUT / "字幕"
SUB_DIR.mkdir(parents=True, exist_ok=True)

MIXIN = [46,47,18,2,53,8,23,32,15,50,10,31,58,3,45,35,27,43,5,49,33,9,42,19,29,28,14,39,
         12,38,41,13,37,48,7,16,24,55,40,61,26,17,0,1,60,51,30,4,22,25,54,21,56,59,6,63,
         57,62,11,36,20,34,44,52]

pool = BiliCookiePool()
s = requests.Session()
s.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36",
})
s.headers["Cookie"] = pool.get_cookie()

nav = s.get("https://api.bilibili.com/x/web-interface/nav", timeout=20).json()
wbi = nav["data"]["wbi_img"]
img = wbi["img_url"].rsplit("/",1)[-1].split(".")[0]
sub = wbi["sub_url"].rsplit("/",1)[-1].split(".")[0]
MIXIN_KEY = "".join((img+sub)[i] for i in MIXIN)[:32]

def sign(p):
    p = dict(p); p["wts"] = str(int(time.time()))
    q = urllib.parse.urlencode(sorted(p.items()))
    p["w_rid"] = hashlib.md5((q + MIXIN_KEY).encode()).hexdigest()
    return p

def get(url, **kw):
    for attempt in range(4):
        try:
            r = s.get(url, timeout=25, **kw)
            if r.status_code == 412 or '"code":-412' in r.text or '"code":-352' in r.text:
                pool.report_412()
                s.headers["Cookie"] = pool.get_cookie()
                time.sleep(2.0*(attempt+1))
                continue
            pool.report_success()
            return r
        except Exception as e:
            print("  retry", e); time.sleep(2)
    return None

BVIDS = [
    "BV1DpNb6mEkp",  # 长期主义的终极版本（闲聊）
    "BV13duhzUEWa",  # 为何总是中途放弃？不累积对努力的感知
    "BV1HPhU6XEic",  # 毛选：长期主义不能熬，靠短期赢出来
    "BV1df5wzDESa",  # 被固定型思维PUA了《终身成长》
    "BV1nS4y1C7Ri",  # 教育心理学 自我效能感理论
    "BV1iE9MBDE4b",  # 一个人最稀缺的能力：深度复盘（方法论）
    "BV1r44y1i75h",  # 备考学习如何复盘？五步骤
    "BV1uS4y1K7A4",  # 日均14h二战失败 考研复盘（失败案例）
    "BV1K94y127Xg",  # 追求结果vs享受过程（泰勒本沙哈尔）
    "BV1xN411g7CL",  # 可能没结果的事要享受过程
    "BV16otezJEJm",  # 读完《微习惯》跟懒惰做朋友
    "BV1gbEB6kESt",  # 建立系统而非追求目标（纳瓦尔）
    "BV1ms411V7zB",  # 李永乐 沉没成本（放弃智慧）
    "BV1YDcpz6E2v",  # 为什么越努力失败得越快（反方）
    "BV1Cm421779A",  # 用力过猛本身就是内耗（反方）
    "BV1u94y1q7AA",  # 低不确定性容忍度：焦虑困兽
    "BV1YkyUYyEgE",  # 焦虑的本质：想跳过过程直接获得结果
]

result = {}
# 断点续抓：已抓过的跳过
done_file = OUT / "深抓结果.json"
if done_file.exists():
    try:
        result = json.loads(done_file.read_text(encoding="utf-8"))
    except Exception:
        result = {}

for bvid in BVIDS:
    if bvid in result and result[bvid].get("aid"):
        print(f"=== {bvid} already done, skip ===")
        continue
    print(f"\n=== {bvid} ===")
    # 1) HTML -> aid/cid
    r = get(f"https://www.bilibili.com/video/{bvid}/", headers={"Referer":"https://www.bilibili.com/"})
    if not r:
        print("  FAIL html"); continue
    m = (re.search(r'window\.__INITIAL_STATE__=(.*?);\(function', r.text, re.S)
         or re.search(r'window\.__INITIAL_STATE__=(.*?);\s*</script>', r.text, re.S))
    if not m:
        print("  no __INITIAL_STATE__"); continue
    try:
        vdata = json.loads(m.group(1))["videoData"]
    except Exception as e:
        print("  json fail", e); continue
    aid = vdata["aid"]
    cid = vdata["cid"]
    title = vdata.get("title")
    owner = vdata.get("owner",{}).get("name")
    duration = vdata.get("duration")
    desc = (vdata.get("desc") or "")[:1000]
    pages = vdata.get("pages") or []
    print(f"  title={title[:40]} | aid={aid} cid={cid} dur={duration}s")
    entry = {"bvid":bvid,"aid":aid,"cid":cid,"title":title,"owner":owner,
             "duration":duration,"desc":desc,"pages":[{"cid":p.get("cid"),"part":p.get("part")} for p in pages]}

    # 2) 评论（wbi main）
    comments = []
    for pn in range(1, 6):
        p = sign({"oid":aid,"type":1,"next":str((pn-1)*20+1),"ps":20,"sort":2})
        rr = get("https://api.bilibili.com/x/v2/reply/wbi/main",
                 params=p, headers={"Referer":f"https://www.bilibili.com/video/{bvid}/"})
        if not rr: break
        d = rr.json()
        dd = d.get("data") or {}
        reps = dd.get("replies") or []
        if not reps: break
        for rep in reps:
            msg = rep.get("content",{}).get("message","")
            subs = []
            for sub_r in (rep.get("replies") or [])[:5]:
                subs.append({"uname":sub_r.get("member",{}).get("uname"),
                            "like":sub_r.get("like",0),
                            "message":sub_r.get("content",{}).get("message","")})
            comments.append({"uname":rep.get("member",{}).get("uname"),
                             "like":rep.get("like",0),
                             "rcount":rep.get("rcount",0),
                             "message":msg,
                             "subs":subs})
        cursor = dd.get("cursor") or {}
        if cursor.get("is_end"): break
        time.sleep(1.3)
    entry["comments"] = comments
    entry["comment_count"] = len(comments)
    print(f"  comments={len(comments)}")

    # 3) 字幕（wbi player）
    sub_text = None
    for page in pages or [{"cid":cid,"part":"P1"}]:
        pcid = page.get("cid") or cid
        q = sign({"bvid":bvid,"cid":str(pcid),"web_location":"333.1007"})
        rr = get("https://api.bilibili.com/x/player/wbi/v2",
                 params=q, headers={"Referer":f"https://www.bilibili.com/video/{bvid}/"})
        if not rr: continue
        try:
            sub_list = ((rr.json().get("data") or {}).get("subtitle") or {}).get("subtitles") or []
        except Exception:
            sub_list = []
        pick = next((x for pref in ["zh-Hans","zh-CN","zh","ai-zh","en-US","en"]
                     for x in sub_list if x.get("lan")==pref), None)
        if not pick: continue
        u = pick.get("subtitle_url") or ""
        if u.startswith("//"): u = "https:"+u
        if not u: continue
        body = get(u, headers={"Referer":f"https://www.bilibili.com/video/{bvid}/"})
        if not body: continue
        try:
            segs = body.json().get("body") or []
        except Exception:
            continue
        pno = pages.index(page)+1 if pages else 1
        (SUB_DIR / f"{bvid}_P{pno}.json").write_text(
            json.dumps(segs, ensure_ascii=False, indent=1), encoding="utf-8")
        if sub_text is None: sub_text = ""
        for seg in segs:
            sub_text += f"[{int(seg['from']//60):02d}:{int(seg['from']%60):02d}] {seg['content']}\n"
        time.sleep(1.0)
    entry["subtitle_chars"] = len(sub_text or "")
    entry["subtitle_file"] = f"{bvid}.txt"
    if sub_text:
        (SUB_DIR / f"{bvid}.txt").write_text(sub_text, encoding="utf-8")
    print(f"  subtitle_chars={entry['subtitle_chars']}")

    result[bvid] = entry
    # 每抓一个就落盘，防中断
    (OUT / "深抓结果.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    time.sleep(1.0)

(OUT / "深抓结果.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
print("\n\nDONE. saved to", OUT / "深抓结果.json")
