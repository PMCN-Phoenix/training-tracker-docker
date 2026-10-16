# -*- coding: utf-8 -*-
"""精抓视频：网页取 aid/cid + wbi 字幕 + 登录评论限速"""
import sys, os, re, json, time, hashlib, urllib.parse
import requests
sys.path.insert(0, r"D:\11.project\iwen-codex\bilibili-cookies")
from cookie_manager import BiliCookiePool

OUT_DIR = r"D:\11.project\iwen-codex\codex-list\training-tracker-docker\docs\腰痛防护与弯举进阶调研\原始数据\需求2-B站"
SUB_DIR = os.path.join(OUT_DIR, '字幕')
os.makedirs(SUB_DIR, exist_ok=True)

MIXIN = [46,47,18,2,53,8,23,32,15,50,10,31,58,3,45,35,27,43,5,49,33,9,42,19,29,28,14,39,12,38,41,13,37,48,7,16,24,55,40,61,26,17,0,1,60,51,30,4,22,25,54,21,56,59,6,63,57,62,11,36,20,34,44,52]

# 精选要抓的 bvid（20个）
PICKS = [
    # 微调手段
    'BV11V4y1E7Em', 'BV1tg4y1o7jo', 'BV1Bg411y79Y', 'BV1VCbG6YEMh',
    # 方案设计
    'BV1Gp69BBEbK', 'BV1BgB8BrEm3', 'BV17561YaEzh', 'BV1rFRpYCEB5',
    'BV1Trhj6MEpG', 'BV113411Q7VW',
    # 动作类
    'BV1Fp4y1d73D', 'BV1bCMZzmEBV', 'BV1ro9oYzE5u', 'BV1Cf421q7Ks',
    'BV1GN4y1Q75g', 'BV1iJ411U72E', 'BV1subYz4E4t', 'BV1Vn2iBBEGG',
    'BV1cSVN6HEfm', 'BV1b9ad6xEzv',
]

pool = BiliCookiePool()

def make_session():
    s = requests.Session()
    s.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
        'Referer': 'https://www.bilibili.com/',
    })
    s.headers['Cookie'] = pool.get_cookie()
    return s

def get_wbi_keys(s):
    r = s.get('https://api.bilibili.com/x/web-interface/nav', timeout=20)
    wbi = r.json()['data']['wbi_img']
    img = wbi['img_url'].rsplit('/',1)[-1].split('.')[0]
    sub = wbi['sub_url'].rsplit('/',1)[-1].split('.')[0]
    return ''.join((img+sub)[i] for i in MIXIN)[:32]

def sign(params, mixin):
    p = dict(params)
    p['wts'] = str(int(time.time()))
    q = urllib.parse.urlencode(sorted(p.items()))
    p['w_rid'] = hashlib.md5((q+mixin).encode()).hexdigest()
    return p

def fetch_video_page(s, bvid):
    """从网页 HTML 取 aid/cid/title/duration"""
    r = s.get(f'https://www.bilibili.com/video/{bvid}/', timeout=25)
    if r.status_code == 412:
        pool.report_412()
        return None
    t = r.text
    m = re.search(r'window\.__INITIAL_STATE__=(.*?);\(function', t, re.S)
    if not m:
        m = re.search(r'window\.__INITIAL_STATE__=(.*?);\s*</script>', t, re.S)
    if not m: return None
    d = json.loads(m.group(1))
    v = d['videoData']
    return {
        'aid': v['aid'],
        'cid': v['cid'],
        'title': v['title'],
        'owner': v['owner']['name'],
        'duration': v['duration'],
        'desc': v.get('desc',''),
        'view': v.get('stat',{}).get('view',0),
        'reply': v.get('stat',{}).get('reply',0),
    }

def fetch_subtitle(s, bvid, cid, mixin):
    """wbi 签名字幕"""
    p = sign({'bvid': bvid, 'cid': cid}, mixin)
    r = s.get('https://api.bilibili.com/x/player/wbi/v2', params=p, timeout=20)
    j = r.json()
    subs = j.get('data',{}).get('subtitle',{}).get('subtitles',[])
    if not subs: return None
    # 取中文
    sub_url = None
    for sub in subs:
        if 'zh' in sub.get('lan','') or sub.get('lan') == 'ai-zh':
            sub_url = sub['subtitle_url']
            break
    if not sub_url:
        sub_url = subs[0]['subtitle_url']
    if sub_url.startswith('//'): sub_url = 'https:' + sub_url
    r2 = s.get(sub_url, timeout=20)
    return r2.json()

def fetch_comments(s, aid, max_pages=10):
    """登录评论抓取"""
    comments = []
    for pn in range(1, max_pages+1):
        try:
            r = s.get('https://api.bilibili.com/x/v2/reply',
                      params={'oid': aid, 'type':1, 'pn':pn, 'ps':20, 'sort':2},
                      timeout=20)
            if r.status_code == 412:
                pool.report_412()
                break
            j = r.json()
            if j.get('code') != 0: break
            replies = j.get('data',{}).get('replies') or []
            if not replies: break
            for c in replies:
                msg = c.get('content',{}).get('message','')
                like = c.get('like',0)
                rcount = c.get('rcount',0)
                # 楼中楼
                subs = []
                if rcount > 0:
                    time.sleep(1.0)
                    r2 = s.get('https://api.bilibili.com/x/v2/reply/reply',
                               params={'oid':aid,'type':1,'root':c['rpid'],'pn':1,'ps':20},
                               timeout=20)
                    if r2.status_code == 200 and r2.json().get('code')==0:
                        for sc in (r2.json().get('data',{}).get('replies') or []):
                            subs.append({
                                'message': sc.get('content',{}).get('message',''),
                                'like': sc.get('like',0),
                            })
                comments.append({'message':msg,'like':like,'subs':subs})
            time.sleep(1.2)
        except Exception as e:
            print(f"    comment err p{pn}: {e}")
            break
    return comments

# 主流程
results = []
s = make_session()
mixin = get_wbi_keys(s)
print(f"mixin ok")

for i, bvid in enumerate(PICKS):
    print(f"\n[{i+1}/{len(PICKS)}] {bvid}")
    info = None
    for attempt in range(3):
        try:
            info = fetch_video_page(s, bvid)
            if info: break
        except Exception as e:
            print(f"  page err: {e}")
            time.sleep(2)
            s = make_session()
            mixin = get_wbi_keys(s)
    if not info:
        print(f"  !! 无法获取视频页")
        results.append({'bvid':bvid,'error':'page_fetch_failed'})
        continue
    pool.report_success()
    print(f"  {info['title'][:40]} | {info['owner']} | dur={info['duration']}s | reply={info['reply']}")

    # 字幕
    sub = None
    try:
        sub = fetch_subtitle(s, bvid, info['cid'], mixin)
    except Exception as e:
        print(f"  sub err: {e}")
    if sub:
        body = sub.get('body',[])
        total_to = max((x.get('to',0) for x in body), default=0)
        cov = total_to / info['duration'] if info['duration'] else 0
        print(f"  字幕: {len(body)}段, 覆盖率={cov:.3f}")
        with open(os.path.join(SUB_DIR, f'{bvid}.json'), 'w', encoding='utf-8') as f:
            json.dump(sub, f, ensure_ascii=False, indent=2)
        # 纯文本
        txt = '\n'.join(f"[{x.get('from',0):.1f}-{x.get('to',0):.1f}] {x.get('content','')}" for x in body)
        with open(os.path.join(SUB_DIR, f'{bvid}.txt'), 'w', encoding='utf-8') as f:
            f.write(txt)
    else:
        print(f"  字幕: 无AI字幕（需FunASR兜底或靠评论）")

    # 评论
    comments = fetch_comments(s, info['aid'])
    print(f"  评论: {len(comments)}条主评论")

    results.append({
        'bvid': bvid,
        'aid': info['aid'],
        'cid': info['cid'],
        'title': info['title'],
        'owner': info['owner'],
        'duration': info['duration'],
        'desc': info['desc'],
        'view': info['view'],
        'reply_total': info['reply'],
        'subtitle': 'yes' if sub else 'no',
        'comment_count': len(comments),
        'comments': comments,
    })
    time.sleep(1.5)

# 保存
with open(os.path.join(OUT_DIR, '新抓视频明细.json'), 'w', encoding='utf-8') as f:
    json.dump(results, f, ensure_ascii=False, indent=2)

# 覆盖率概览
lines = [f"抓取日期: 2026-10-12", f"精选视频数: {len(PICKS)}", ""]
has_sub = sum(1 for r in results if r.get('subtitle')=='yes')
no_sub = sum(1 for r in results if r.get('subtitle')=='no')
total_comments = sum(r.get('comment_count',0) for r in results)
lines.append(f"有AI字幕: {has_sub}/{len(PICKS)}")
lines.append(f"无AI字幕: {no_sub}/{len(PICKS)}")
lines.append(f"评论总数（主评论）: {total_comments}")
lines.append("")
lines.append("=== 逐条 ===")
for r in results:
    if 'error' in r:
        lines.append(f"{r['bvid']}: ERROR {r['error']}")
    else:
        lines.append(f"{r['bvid']} | {r['title'][:40]} | sub={r['subtitle']} | comments={r['comment_count']}/{r['reply_total']} | dur={r['duration']}s")
with open(os.path.join(OUT_DIR, '覆盖率与评论概览.txt'), 'w', encoding='utf-8') as f:
    f.write('\n'.join(lines))

print(f"\n=== 完成: {has_sub}字幕 / {no_sub}无字幕 / {total_comments}评论 ===")
