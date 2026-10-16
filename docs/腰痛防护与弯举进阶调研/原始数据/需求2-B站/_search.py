# -*- coding: utf-8 -*-
"""B站搜索：按 4 方向分组关键词搜索弯举进阶相关视频"""
import sys, os, re, json, time, hashlib, urllib.parse
import requests
sys.path.insert(0, r"D:\11.project\iwen-codex\bilibili-cookies")
from cookie_manager import BiliCookiePool

OUT_DIR = r"D:\11.project\iwen-codex\codex-list\training-tracker-docker\docs\腰痛防护与弯举进阶调研\原始数据\需求2-B站"

MIXIN = [46,47,18,2,53,8,23,32,15,50,10,31,58,3,45,35,27,43,5,49,33,9,42,19,29,28,14,39,12,38,41,13,37,48,7,16,24,55,40,61,26,17,0,1,60,51,30,4,22,25,54,21,56,59,6,63,57,62,11,36,20,34,44,52]

pool = BiliCookiePool()

def make_session():
    s = requests.Session()
    s.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
        'Referer': 'https://search.bilibili.com/',
    })
    s.headers['Cookie'] = pool.get_cookie()
    return s

def get_wbi_keys(s):
    r = s.get('https://api.bilibili.com/x/web-interface/nav', timeout=20)
    data = r.json()
    wbi = data['data']['wbi_img']
    img = wbi['img_url'].rsplit('/',1)[-1].split('.')[0]
    sub = wbi['sub_url'].rsplit('/',1)[-1].split('.')[0]
    return ''.join((img+sub)[i] for i in MIXIN)[:32]

def sign(params, mixin):
    p = dict(params)
    p['wts'] = str(int(time.time()))
    q = urllib.parse.urlencode(sorted(p.items()))
    p['w_rid'] = hashlib.md5((q+mixin).encode()).hexdigest()
    return p

# 4 方向 × 5 组关键词
GROUPS = {
    'A_动作进阶': ['哑铃弯举 进阶', '弯举 重量上不去', '二头 渐进超负荷', '肱二头肌 平台期', '弯举 加重'],
    'B_器械手段': ['绳索弯举', 'EZ杠弯举', '牧师凳弯举', '锤式弯举', '上斜哑铃弯举'],
    'C_微调手段': ['磁吸配重片', '哑铃 小重量片', '1.25kg 小片', '可调哑铃 渐进', '健身房 没有小片'],
    'D_方案设计': ['double progression', '次数递增 渐进', '次数先行 加重', '波浪式渐进', '小肌群 渐进 升重幅度'],
}

def dur_to_sec(d):
    if not d: return 0
    parts = d.split(':')
    try:
        if len(parts) == 2: return int(parts[0])*60 + int(parts[1])
        if len(parts) == 3: return int(parts[0])*3600 + int(parts[1])*60 + int(parts[2])
    except: pass
    return 0

def clean(t):
    return re.sub(r'<[^>]+>', '', t or '')

def search_kw(s, mixin, kw, page=1):
    p = sign({'search_type':'video','keyword':kw,'page':page,'page_size':30,'order':'totalrating'}, mixin)
    r = s.get('https://api.bilibili.com/x/web-interface/wbi/search/type', params=p, timeout=25)
    if r.status_code == 412 or '"code":-412' in r.text:
        pool.report_412()
        return None
    pool.report_success()
    j = r.json()
    return j.get('data', {}).get('result', []) or []

all_videos = {}  # bvid -> info
kw_hits = {}     # bvid -> [kws]

s = make_session()
mixin = get_wbi_keys(s)
print(f"mixin={mixin[:8]}...")

for group, kws in GROUPS.items():
    for kw in kws:
        for attempt in range(3):
            try:
                results = search_kw(s, mixin, kw)
                break
            except Exception as e:
                print(f"  err {kw}: {e}")
                time.sleep(2)
                s = make_session()
                mixin = get_wbi_keys(s)
        else:
            results = []
        print(f"[{group}] {kw}: {len(results)} hits")
        for v in results:
            bvid = v.get('bvid')
            if not bvid: continue
            if bvid not in all_videos:
                all_videos[bvid] = {
                    'bvid': bvid,
                    'title': clean(v.get('title','')),
                    'author': v.get('author',''),
                    'play': v.get('play',0),
                    'duration': v.get('duration',''),
                    'dur_sec': dur_to_sec(v.get('duration','')),
                    'pubdate': v.get('pubdate',0),
                    'description': clean(v.get('description','')),
                    'group': group,
                    'kws': [],
                }
            all_videos[bvid]['kws'].append(kw)
        time.sleep(1.5)

# 本地已有 bvid（不重复抓）
LOCAL_BV = set()
local_path = os.path.join(OUT_DIR, '本地语料命中清单.json')
if os.path.exists(local_path):
    d = json.load(open(local_path, encoding='utf-8'))
    LOCAL_BV = set(d.get('local_bvids', []))
for bv in all_videos:
    all_videos[bv]['_local'] = bv in LOCAL_BV

# 保存
out = {
    'groups': GROUPS,
    'total_unique': len(all_videos),
    'local_count': len(LOCAL_BV),
    'videos': list(all_videos.values()),
}
with open(os.path.join(OUT_DIR, '搜索清单.json'), 'w', encoding='utf-8') as f:
    json.dump(out, f, ensure_ascii=False, indent=2)

print(f"\n=== 总去重: {len(all_videos)} (本地已抓过: {sum(1 for v in all_videos.values() if v['_local'])}) ===")
