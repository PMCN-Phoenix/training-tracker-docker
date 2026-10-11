# -*- coding: utf-8 -*-
"""B站分组关键词搜索 + wbi签名 + Cookie池轮询"""
import sys, os, json, time, re, hashlib, urllib.parse
sys.path.insert(0, r"D:\11.project\iwen-codex\bilibili-cookies")
from cookie_manager import BiliCookiePool
import requests

OUT = r"D:\11.project\iwen-codex\codex-list\training-tracker-docker\docs\意象训练与筋膜感知调研\原始数据\B站"

MIXIN = [46,47,18,2,53,8,23,32,15,50,10,31,58,3,45,35,27,43,5,49,33,9,42,19,29,28,14,39,12,38,41,13,37,48,7,16,24,55,40,61,26,17,0,1,60,51,30,4,22,25,54,21,56,59,6,63,57,62,11,36,20,34,44,52]

pool = BiliCookiePool()
s = requests.Session()
s.headers.update({'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
                 'Referer': 'https://www.bilibili.com/'})

# 初始化wbi key
def refresh_wbi():
    cookie = pool.get_cookie()
    s.headers['Cookie'] = cookie
    nav = s.get('https://api.bilibili.com/x/web-interface/nav', timeout=20).json()
    if nav.get('code') != 0:
        print("nav fail:", nav.get('code'), nav.get('message'))
        pool.report_412()
        return None
    wbi = nav['data']['wbi_img']
    img = wbi['img_url'].rsplit('/',1)[-1].split('.')[0]
    sub = wbi['sub_url'].rsplit('/',1)[-1].split('.')[0]
    mixin = ''.join((img+sub)[i] for i in MIXIN)[:32]
    uname = nav['data'].get('uname','?')
    print(f"wbi ok, uname={uname}")
    pool.report_success()
    return mixin

mixin = refresh_wbi()
if not mixin:
    sys.exit(1)

def sign(p):
    p = dict(p); p['wts'] = str(int(time.time()))
    q = urllib.parse.urlencode(sorted(p.items()))
    p['w_rid'] = hashlib.md5((q+mixin).encode()).hexdigest()
    return p

def clean_title(t):
    return re.sub(r'<[^>]+>', '', t or '')

def parse_dur(d):
    if not d: return 0
    d = str(d)
    parts = d.split(':')
    try:
        if len(parts) == 2: return int(parts[0])*60+int(parts[1])
        if len(parts) == 3: return int(parts[0])*3600+int(parts[1])*60+int(parts[2])
    except: return 0
    return 0

KEYWORDS = {
    '意象/意念锻炼': ['意念锻炼', '表象训练', '念动一致', '心理演练 运动', '大脑训练 力量 肌肉'],
    '筋膜链/解剖列车': ['肌筋膜链', '解剖列车', '筋膜训练', '筋膜拉伸'],
    '肌腱/张力/本体感觉': ['高尔基腱器', '本体感觉训练', '肌肉张力 力量', '肌腱 力量训练', '本体感觉 健身'],
    '神经肌肉控制': ['神经适应 力量训练', '神经募集 训练', '神经肌肉控制', '运动单位募集'],
    '注意焦点': ['注意力焦点 运动', '内部注意 外部注意 运动', '专注发力 健身', '动作控制 注意力'],
    '运动学习/迁移': ['运动技能学习', '动作学习迁移', '刻意练习 运动', '心理训练 力量训练'],
}

all_results = {}
for direction, kws in KEYWORDS.items():
    for kw in kws:
        try:
            p = sign({'search_type':'video','keyword':kw,'page':1,'page_size':30})
            r = s.get('https://api.bilibili.com/x/web-interface/wbi/search/type', params=p, timeout=25)
            if r.status_code == 412 or '"code":-412' in r.text:
                print(f"  412 on kw={kw}, switching cookie")
                pool.report_412()
                time.sleep(2)
                # refresh cookie and retry once
                s.headers['Cookie'] = pool.get_cookie()
                r = s.get('https://api.bilibili.com/x/web-interface/wbi/search/type', params=p, timeout=25)
            j = r.json()
            pool.report_success()
            results = (j.get('data') or {}).get('result') or []
            cnt = 0
            for v in results:
                bv = v.get('bvid')
                if not bv: continue
                if bv not in all_results:
                    all_results[bv] = {
                        'bvid': bv,
                        'title': clean_title(v.get('title')),
                        'author': v.get('author'),
                        'play': v.get('play', 0),
                        'duration': v.get('duration'),
                        '_dur_s': parse_dur(v.get('duration')),
                        'pubdate': v.get('pubdate'),
                        'desc': clean_title(v.get('description') or '')[:200],
                        'hit_keywords': [],
                        'hit_directions': set(),
                    }
                all_results[bv]['hit_keywords'].append(kw)
                all_results[bv]['hit_directions'].add(direction)
                cnt += 1
            print(f"[{direction}] {kw}: {cnt} results")
            time.sleep(1.5)
        except Exception as e:
            print(f"  ERR kw={kw}: {e}")
            time.sleep(2)

# 转set为list
for bv, v in all_results.items():
    v['hit_directions'] = list(v['hit_directions'])

print(f"\n=== 去重后总视频: {len(all_results)} ===")

# 打分
W = [
    # 方向1 意象
    ('意念锻炼', 12), ('表象训练', 12), ('念动一致', 11), ('心理演练', 10), ('意象', 8),
    # 方向2 筋膜
    ('肌筋膜链', 12), ('解剖列车', 12), ('筋膜链', 10), ('筋膜训练', 9), ('筋膜', 5),
    # 方向3 肌腱/张力/本体感觉
    ('高尔基', 12), ('本体感觉', 11), ('肌梭', 10), ('肌腱', 7), ('肌肉张力', 7), ('肌张力', 6),
    # 方向4 神经
    ('神经适应', 9), ('神经募集', 9), ('神经肌肉', 7), ('运动单位', 8),
    # 方向5 注意焦点
    ('注意焦点', 11), ('内部注意', 10), ('外部注意', 10), ('专注发力', 7),
    # 方向6 运动学习
    ('运动学习', 9), ('动作学习', 8), ('迁移', 5), ('刻意练习', 6),
    # 通用
    ('发力感', 5), ('拉伸感', 4), ('肌肉链', 8), ('牵张反射', 9),
]

def score(v):
    t = (v['title'] + ' ' + v['desc']).lower()
    s = 0
    for k, w in W:
        if k.lower() in t: s += w
    # 命中方向加成
    s += len(v['hit_directions']) * 2
    # 命中关键词数加成
    s += min(len(v['hit_keywords']), 5) * 1.5
    # 播放量弱信号
    p = v.get('play') or 0
    if isinstance(p, str):
        p = int(p.replace('万','0000')) if '万' in p else (int(p) if p.isdigit() else 0)
    s += 4 if p > 500000 else 3 if p > 100000 else 2 if p > 30000 else 1 if p > 5000 else -1
    # 时长
    if v['_dur_s'] < 90: s -= 3
    if v['_dur_s'] > 600: s += 1
    return s

scored = []
for bv, v in all_results.items():
    v['score'] = score(v)
    scored.append(v)
scored.sort(key=lambda x: -x['score'])

# 保存搜索清单
out_file = os.path.join(OUT, '搜索清单.json')
with open(out_file, 'w', encoding='utf-8') as f:
    json.dump(scored, f, ensure_ascii=False, indent=1)
print(f"\n已保存 {out_file}")
print("\n=== Top 40 ===")
for i, v in enumerate(scored[:40]):
    print(f"{i+1:2d}. [{v['score']:5.1f}] {v['bvid']} | {v['title'][:40]} | play={v['play']} | {v['duration']} | kws={v['hit_keywords'][:3]}")
