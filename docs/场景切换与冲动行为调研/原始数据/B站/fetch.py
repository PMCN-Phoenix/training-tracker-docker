# -*- coding: utf-8 -*-
"""场景切换与冲动行为 - 主抓取脚本
1. 从网页HTML拿 aid/cid (__INITIAL_STATE__)
2. 抓评论（主评论分页 + 楼中楼）
3. 抓 AI 字幕（wbi /x/player/wbi/v2）
"""
import sys, os, time, json, re, hashlib, urllib.parse, html
import requests
from pathlib import Path

sys.path.insert(0, r"D:\11.project\iwen-codex\bilibili-cookies")
from cookie_manager import BiliCookiePool

OUT_DIR = Path(r"D:\11.project\iwen-codex\codex-list\training-tracker-docker\docs\场景切换与冲动行为调研\原始数据\B站")
SUB_DIR = OUT_DIR / "字幕"
SUB_DIR.mkdir(parents=True, exist_ok=True)

MIXIN = [46,47,18,2,53,8,23,32,15,50,10,31,58,3,45,35,27,43,5,49,33,9,42,19,29,28,14,39,
         12,38,41,13,37,48,7,16,24,55,40,61,26,17,0,1,60,51,30,4,22,25,54,21,56,59,6,63,
         57,62,11,36,20,34,44,52]
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"

# 精选30个视频
TARGETS = [
    "BV1FUuy6DE6G",  # 核心：你不是手机成瘾是情绪成瘾
    "BV1SN41117oY",  # 多巴胺自律 4M
    "BV1YLBtB8EHh",  # 多巴胺陷阱刷手机
    "BV1MBp964EDy",  # 多巴胺戒断适应无聊
    "BV1MhLS6FEAg",  # 成瘾真相多巴胺 1M
    "BV1NkhU6oEJJ",  # 最容易上瘾
    "BV1rmEKzJETu",  # 抖音上瘾数据科学
    "BV1xYpS6VEbk",  # 刷短剧脑子变钝
    "BV1UpXzBsE3Z",  # 注意力残留效应
    "BV15Etz6rE5j",  # 注意力残留与规划谬误
    "BV1Dbi9BfEUy",  # 对抗注意力残留
    "BV12Aao6JEMq",  # Stroop任务切换
    "BV16otezJEJm",  # 微习惯
    "BV1cbpu6RER7",  # 原子习惯深度
    "BV1qNtAz9EJL",  # 原子习惯微小改变
    "BV1bLuw6VEVZ",  # 微习惯改变生活
    "BV1LvUSBpEFa",  # DMN操控情绪
    "BV11hM36FEpv",  # DMN空闲审判你
    "BV1QLEC6dE6D",  # 走神后台运算心智游移
    "BV1GvaB61EeZ",  # DMN什么都没做却累
    "BV1b4qcB5EhJ",  # DMN高度激活
    "BV1pv4y1d7ZJ",  # TED拖延症
    "BV1YWWA6oEcL",  # 拖延是逃避感觉
    "BV132TM6bEAa",  # 意志力不是差
    "BV14K2pYcEwY",  # 自我损耗
    "BV1s54y1x75L",  # 提升自制力 1.3M
    "BV1b5rMBgETi",  # 意志力消耗品
    "BV1GF4m1576d",  # 上课走神3秒 1.5M
    "BV1UQ4y1c7S1",  # 3招拯救拖延 1.5M
    "BV1EuVUzUEMR",  # 放下手机自我约束
]

pool = BiliCookiePool()
session = requests.Session()
session.headers.update({"User-Agent": UA, "Referer": "https://www.bilibili.com/"})

def refresh_cookie():
    ck = pool.get_cookie()
    session.headers.update({"Cookie": ck})
    return ck

refresh_cookie()

# wbi keys
nav = session.get('https://api.bilibili.com/x/web-interface/nav', timeout=20).json()
wbi = nav['data']['wbi_img']
img = wbi['img_url'].rsplit('/',1)[-1].split('.')[0]
sub = wbi['sub_url'].rsplit('/',1)[-1].split('.')[0]
MIXIN_KEY = ''.join((img+sub)[i] for i in MIXIN)[:32]
print(f"[wbi] key={MIXIN_KEY[:8]}...")

def sign(p):
    p = dict(p); p['wts'] = str(int(time.time()))
    q = urllib.parse.urlencode(sorted(p.items()))
    p['w_rid'] = hashlib.md5((q+MIXIN_KEY).encode()).hexdigest()
    return p

def req_get(url, params=None, headers=None, tries=4):
    """带412自动切换的请求"""
    for i in range(tries):
        try:
            r = session.get(url, params=params, headers=headers, timeout=25)
            if r.status_code == 412:
                print(f"    [412] {url[:60]}, switching...")
                pool.report_412()
                refresh_cookie()
                time.sleep(2)
                continue
            return r
        except Exception as e:
            print(f"    [err] {e}, retry {i+1}")
            time.sleep(2)
    return None

# ============ Step 1: 拿 aid/cid ============
print(f"\n=== Step 1: 拿 aid/cid for {len(TARGETS)} videos ===")
videos = {}
for bvid in TARGETS:
    r = req_get(f'https://www.bilibili.com/video/{bvid}/')
    if not r:
        print(f"  [FAIL] {bvid}: no response")
        continue
    t = r.text
    m = (re.search(r'window\.__INITIAL_STATE__=(.*?);\(function', t, re.S)
         or re.search(r'window\.__INITIAL_STATE__=(.*?);\s*</script>', t, re.S))
    if not m:
        print(f"  [FAIL] {bvid}: no __INITIAL_STATE__")
        continue
    try:
        v = json.loads(m.group(1))['videoData']
    except Exception as e:
        print(f"  [FAIL] {bvid}: json {e}")
        continue
    aid = v.get('aid')
    cid = v.get('cid')
    title = v.get('title','')
    owner = v.get('owner',{}).get('name','')
    duration = v.get('duration',0)
    desc = (v.get('desc') or '')[:800]
    pages = v.get('pages') or []
    videos[bvid] = {
        'bvid': bvid, 'aid': aid, 'cid': cid, 'title': title,
        'owner': owner, 'duration': duration, 'desc': desc,
        'pages': [{'cid': p.get('cid'), 'part': p.get('part'), 'duration': p.get('duration')} for p in pages],
    }
    print(f"  OK {bvid} aid={aid} cid={cid} dur={duration}s | {title[:40]}")
    time.sleep(0.8)

print(f"\n[done] 拿到 {len(videos)}/{len(TARGETS)} 个视频的aid/cid")

# ============ Step 2: 评论 ============
print(f"\n=== Step 2: 抓评论 ===")
comments_data = {}
for bvid, info in videos.items():
    aid = info['aid']
    bv = bvid
    print(f"\n  [{bv}] aid={aid}")
    vdata = {'title': info['title'], 'aid': aid, 'cid': info['cid'],
             'owner': info['owner'], 'duration': info['duration'], 'desc': info['desc'],
             'count': 0, 'comments': []}
    # 主评论
    main_comments = []
    total = 0
    for pn in range(1, 12):
        r = req_get('https://api.bilibili.com/x/v2/reply',
                    params={'oid': aid, 'type': 1, 'pn': pn, 'ps': 20, 'sort': 2},
                    headers={'Referer': f'https://www.bilibili.com/video/{bv}/'})
        if not r: break
        try:
            d = r.json()
        except: break
        if d.get('code') != 0:
            print(f"    reply page{pn} code={d.get('code')}")
            break
        dd = d.get('data') or {}
        reps = dd.get('replies') or []
        if not reps: break
        total = (dd.get('page') or {}).get('count', 0)
        for rep in reps:
            main_comments.append(rep)
        if len(main_comments) >= total: break
        time.sleep(1.2)
    vdata['count'] = total
    print(f"    主评论 {len(main_comments)} / 总{total}")
    # 楼中楼
    for rep in main_comments:
        rpid = rep.get('rpid')
        rcount = rep.get('rcount', 0)
        msg = rep.get('content',{}).get('message','')
        like = rep.get('like',0)
        uname = rep.get('member',{}).get('uname','')
        entry = {'uname': uname, 'like': like, 'rcount': rcount, 'rpid': rpid,
                 'message': msg, 'subs': []}
        if rcount and rcount > 0:
            for pn in range(1, 6):
                r2 = req_get('https://api.bilibili.com/x/v2/reply/reply',
                            params={'oid': aid, 'type': 1, 'root': rpid, 'pn': pn, 'ps': 20},
                            headers={'Referer': f'https://www.bilibili.com/video/{bv}/'})
                if not r2: break
                try:
                    d2 = r2.json()
                except: break
                if d2.get('code') != 0: break
                dd2 = d2.get('data') or {}
                subs = dd2.get('replies') or []
                if not subs: break
                for s in subs:
                    entry['subs'].append({
                        'uname': s.get('member',{}).get('uname',''),
                        'like': s.get('like',0),
                        'message': s.get('content',{}).get('message',''),
                    })
                # 楼中楼总数判断
                sub_count = (dd2.get('page') or {}).get('count',0)
                if len(entry['subs']) >= sub_count: break
                time.sleep(0.9)
        vdata['comments'].append(entry)
        time.sleep(0.3)
    comments_data[bvid] = vdata
    print(f"    完成: {len(vdata['comments'])}条主评论, 楼中楼已抓")

# 保存评论
out_c = OUT_DIR / "视频评论.json"
out_c.write_text(json.dumps(comments_data, ensure_ascii=False, indent=2), encoding='utf-8')
print(f"\n[save] 评论 -> {out_c}")

# ============ Step 3: AI字幕 ============
print(f"\n=== Step 3: 抓AI字幕 (wbi) ===")
sub_report = []
for bvid, info in videos.items():
    cid = info['cid']
    aid = info['aid']
    print(f"\n  [{bvid}] cid={cid}")
    sub_entry = {'bvid': bvid, 'title': info['title'], 'duration': info['duration'],
                 'has_subtitle': False, 'segments': 0, 'coverage': 0.0, 'lan': ''}
    # 对多P视频，只抓P1的cid（多数情况）；如果多P且时长分配，可抓所有P
    cids_to_fetch = [(cid, info['duration'])]
    pages = info.get('pages') or []
    if len(pages) > 1:
        cids_to_fetch = [(p['cid'], p.get('duration',0)) for p in pages]
    all_body = []
    for pcid, pdur in cids_to_fetch:
        got = False
        for attempt in range(4):
            q = sign({'bvid': bvid, 'cid': str(pcid), 'web_location': '333.1007'})
            r = req_get('https://api.bilibili.com/x/player/wbi/v2', params=q,
                       headers={'Referer': f'https://www.bilibili.com/video/{bvid}/'})
            if not r: break
            try:
                d = r.json()
            except: break
            if d.get('code') != 0:
                print(f"    player code={d.get('code')}")
                time.sleep(2); continue
            subs = ((d.get('data') or {}).get('subtitle') or {}).get('subtitles') or []
            if not subs:
                print(f"    P{pcid}: no subtitles list, attempt {attempt+1}")
                time.sleep(3); continue
            pick = None
            for pref in ['zh-Hans','zh-CN','zh','ai-zh','en-US','en']:
                for x in subs:
                    if x.get('lan') == pref:
                        pick = x; break
                if pick: break
            if not pick:
                pick = subs[0]
            u = pick.get('subtitle_url','')
            if not u:
                print(f"    subtitle_url empty, retry {attempt+1}")
                time.sleep(4); continue
            if u.startswith('//'): u = 'https:'+u
            r2 = req_get(u, headers={'Referer': f'https://www.bilibili.com/video/{bvid}/'})
            if not r2: continue
            try:
                body = r2.json().get('body', [])
            except:
                time.sleep(2); continue
            if not body:
                time.sleep(3); continue
            all_body.extend(body)
            sub_entry['lan'] = pick.get('lan','')
            got = True
            break
        time.sleep(0.8)
    if all_body:
        sub_entry['has_subtitle'] = True
        sub_entry['segments'] = len(all_body)
        total_dur = info['duration']
        if total_dur > 0:
            last_to = max((seg.get('to',0) for seg in all_body), default=0)
            sub_entry['coverage'] = round(last_to / total_dur, 3)
        # 保存字幕JSON
        (SUB_DIR / f"{bvid}.json").write_text(
            json.dumps(all_body, ensure_ascii=False, indent=2), encoding='utf-8')
        print(f"    ✅ {len(all_body)}段, 覆盖率{sub_entry['coverage']*100:.1f}%, lan={sub_entry['lan']}")
    else:
        print(f"    ❌ 无AI字幕（需FunASR兜底或硬字幕）")
    sub_report.append(sub_entry)

# 保存字幕报告
out_s = OUT_DIR / "字幕清单.json"
out_s.write_text(json.dumps(sub_report, ensure_ascii=False, indent=2), encoding='utf-8')
print(f"\n[save] 字幕清单 -> {out_s}")

# 总结
has_sub = sum(1 for x in sub_report if x['has_subtitle'])
print(f"\n=== 总结 ===")
print(f"视频总数: {len(videos)}")
print(f"有AI字幕: {has_sub}")
print(f"无AI字幕: {len(videos)-has_sub}")
for x in sub_report:
    flag = "✅" if x['has_subtitle'] else "❌"
    print(f"  {flag} {x['bvid']} | seg={x['segments']:4d} | cov={x['coverage']*100:5.1f}% | {x['title'][:35]}")
