# -*- coding: utf-8 -*-
"""对精选视频批量抓 aid/cid + wbi AI字幕 + 评论"""
import sys, os, json, time, re, hashlib, urllib.parse
sys.path.insert(0, r"D:\11.project\iwen-codex\bilibili-cookies")
from cookie_manager import BiliCookiePool
import requests

OUT = r"D:\11.project\iwen-codex\codex-list\training-tracker-docker\docs\意象训练与筋膜感知调研\原始数据\B站"
SUB_DIR = os.path.join(OUT, '字幕')
os.makedirs(SUB_DIR, exist_ok=True)

MIXIN = [46,47,18,2,53,8,23,32,15,50,10,31,58,3,45,35,27,43,5,49,33,9,42,19,29,28,14,39,12,38,41,13,37,48,7,16,24,55,40,61,26,17,0,1,60,51,30,4,22,25,54,21,56,59,6,63,57,62,11,36,20,34,44,52]

SELECTED = [
    'BV1Yv411k7PQ',  # 本体觉及本体感受器
    'BV15b4y1W7Gf',  # NSCA 肌梭高尔基腱器
    'BV1LGp46bE2p',  # 神经训练重建本体感觉
    'BV1jjmoYLEaN',  # 训练中枢神经系统
    'BV1Qo4y1Z7jQ',  # 割韭菜念动一致（反面）
    'BV1hM4y1t7Np',  # 精英运动员想象力训练
    'BV1Nv4y1H7jE',  # 筋膜健身教程
    'BV1Jt421K7pi',  # 费登奎斯方法
    'BV1Mq4y1S7sQ',  # 神经运动学
    'BV1oVSoBCECd',  # 神经募集训练方法
    'BV1RVb1zGEoc',  # 脑内电影心理演练
    'BV1xsqTY8Ei9',  # 筋膜释放术解剖列车
]

pool = BiliCookiePool()
s = requests.Session()
s.headers.update({'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36'})

# wbi init
cookie = pool.get_cookie()
s.headers['Cookie'] = cookie
nav = s.get('https://api.bilibili.com/x/web-interface/nav', timeout=20).json()
wbi = nav['data']['wbi_img']
img = wbi['img_url'].rsplit('/',1)[-1].split('.')[0]
sub = wbi['sub_url'].rsplit('/',1)[-1].split('.')[0]
mixin = ''.join((img+sub)[i] for i in MIXIN)[:32]
print(f"wbi init ok, uname={nav['data'].get('uname')}")

def sign(p):
    p = dict(p); p['wts'] = str(int(time.time()))
    q = urllib.parse.urlencode(sorted(p.items()))
    p['w_rid'] = hashlib.md5((q+mixin).encode()).hexdigest()
    return p

def safe_get(url, **kw):
    for attempt in range(3):
        s.headers['Cookie'] = pool.get_cookie()
        try:
            r = s.get(url, timeout=25, **kw)
            if r.status_code == 412 or '"code":-412' in r.text[:200]:
                pool.report_412()
                time.sleep(2)
                continue
            pool.report_success()
            return r
        except Exception as e:
            print(f"  req err: {e}")
            time.sleep(2)
    return None

def get_video_info(bvid):
    r = safe_get(f'https://www.bilibili.com/video/{bvid}/')
    if not r: return None
    t = r.text
    m = re.search(r'window\.__INITIAL_STATE__=(.*?);\(function', t, re.S)
    if not m:
        m = re.search(r'window\.__INITIAL_STATE__=(.*?);\s*</script>', t, re.S)
    if not m: return None
    d = json.loads(m.group(1))
    v = d.get('videoData') or {}
    return {
        'aid': v.get('aid'),
        'cid': v.get('cid'),
        'title': v.get('title'),
        'owner': (v.get('owner') or {}).get('name'),
        'duration': v.get('duration'),
        'desc': (v.get('desc') or '')[:500],
        'pages': v.get('pages', []),
    }

def get_subtitle(bvid, cid):
    q = sign({'bvid': bvid, 'cid': str(cid), 'web_location': '333.1007'})
    r = safe_get('https://api.bilibili.com/x/player/wbi/v2',
                 params=q, headers={'Referer': f'https://www.bilibili.com/video/{bvid}/'})
    if not r: return None, 'req_fail'
    j = r.json()
    subs = ((j.get('data') or {}).get('subtitle') or {}).get('subtitles') or []
    if not subs:
        return None, 'no_ai_subtitle'
    # 选中文
    pick = None
    for pref in ['zh-Hans','zh-CN','zh','ai-zh']:
        for x in subs:
            if x.get('lan') == pref:
                pick = x; break
        if pick: break
    if not pick: pick = subs[0]
    u = pick.get('subtitle_url') or ''
    if not u: return None, 'empty_url'
    if u.startswith('//'): u = 'https:' + u
    r2 = safe_get(u, headers={'Referer': f'https://www.bilibili.com/video/{bvid}/'})
    if not r2: return None, 'sub_dl_fail'
    try:
        body = r2.json().get('body') or []
        return body, pick.get('lan','')
    except: return None, 'sub_parse_fail'

def get_comments(aid, bvid, max_pages=8):
    comments = []
    for pn in range(1, max_pages+1):
        r = safe_get('https://api.bilibili.com/x/v2/reply/wbi/main',
                     params=sign({'oid': aid, 'type': 1, 'pn': pn, 'ps': 20, 'sort': 2}),
                     headers={'Referer': f'https://www.bilibili.com/video/{bvid}/'})
        if not r: break
        j = r.json()
        dd = j.get('data') or {}
        reps = dd.get('replies') or []
        if not reps: break
        for c in reps:
            item = {
                'uname': (c.get('member') or {}).get('uname'),
                'like': c.get('like', 0),
                'rcount': c.get('rcount', 0),
                'rpid': c.get('rpid'),
                'message': c.get('content',{}).get('message',''),
                'subs': [],
            }
            # 内联楼中楼
            for s in (c.get('replies') or []):
                item['subs'].append({
                    'uname': (s.get('member') or {}).get('uname'),
                    'like': s.get('like',0),
                    'message': s.get('content',{}).get('message',''),
                })
            comments.append(item)
        cursor = dd.get('cursor') or {}
        if cursor.get('is_end'): break
        time.sleep(1.3)
    return comments

results = {}
coverage = []
for bv in SELECTED:
    print(f"\n=== {bv} ===")
    info = get_video_info(bv)
    if not info:
        print("  FAIL info")
        coverage.append({'bvid': bv, 'status': 'info_fail'})
        continue
    print(f"  title: {info['title'][:40]} | aid={info['aid']} cid={info['cid']} dur={info['duration']}s")
    # 字幕（多P取P1，单P直接cid）
    body, status = get_subtitle(bv, info['cid'])
    sub_note = status
    if body:
        to_max = max(x['to'] for x in body)
        cov = to_max / info['duration'] if info['duration'] else 0
        sub_note = f"ok,{len(body)}seg,cov={cov:.2f}"
        # 保存
        with open(os.path.join(SUB_DIR, f'{bv}.json'), 'w', encoding='utf-8') as f:
            json.dump({'title': info['title'], 'owner': info['owner'], 'duration': info['duration'],
                       'body': body}, f, ensure_ascii=False, indent=1)
        print(f"  subtitle: {len(body)} seg, coverage={cov:.2f}")
    else:
        print(f"  subtitle: {status}")
    # 评论
    comments = get_comments(info['aid'], bv)
    print(f"  comments: {len(comments)}")
    results[bv] = {**info, 'subtitle_status': sub_note, 'comment_count': len(comments), 'comments': comments}
    time.sleep(1.5)
    coverage.append({'bvid': bv, 'title': info['title'], 'aid': info['aid'], 'cid': info['cid'],
                     'duration': info['duration'], 'subtitle': sub_note, 'comments': len(comments)})

# 保存评论
with open(os.path.join(OUT, '视频评论.json'), 'w', encoding='utf-8') as f:
    json.dump(results, f, ensure_ascii=False, indent=1)

# 保存覆盖率
with open(os.path.join(OUT, '覆盖率与评论概览.txt'), 'w', encoding='utf-8') as f:
    f.write(f"抓取日期: 2026-10-11\n")
    f.write(f"精选视频数: {len(SELECTED)}\n\n")
    sub_ok = sum(1 for c in coverage if str(c.get('subtitle','')).startswith('ok'))
    f.write(f"有AI字幕: {sub_ok} / {len(coverage)}\n\n")
    for c in coverage:
        f.write(f"{c['bvid']} | {c.get('title','')[:40]} | dur={c.get('duration')}s | sub={c.get('subtitle')} | comments={c.get('comments')}\n")

print("\n=== DONE ===")
print(f"有字幕: {sum(1 for c in coverage if str(c.get('subtitle','')).startswith('ok'))}/{len(coverage)}")
