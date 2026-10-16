# -*- coding: utf-8 -*-
import sys, re, json, time, hashlib, urllib.parse, io
sys.path.insert(0, r"D:\11.project\iwen-codex\bilibili-cookies")
import requests
from cookie_manager import BiliCookiePool

OUT = r"D:\11.project\iwen-codex\codex-list\training-tracker-docker\docs\腰痛防护与弯举进阶调研\原始数据\需求1-B站"

MIXIN = [46,47,18,2,53,8,23,32,15,50,10,31,58,3,45,35,27,43,5,49,33,9,42,19,29,28,14,39,12,38,41,13,37,48,7,16,24,55,40,61,26,17,0,1,60,51,30,4,22,25,54,21,56,59,6,63,57,62,11,36,20,34,44,52]

pool = BiliCookiePool()
s = requests.Session()
s.headers.update({'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36'})

# init wbi
def refresh_wbi():
    cookie = pool.get_cookie()
    s.headers['Cookie'] = cookie
    nav = s.get('https://api.bilibili.com/x/web-interface/nav', timeout=20).json()
    w = nav['data']['wbi_img']
    img = w['img_url'].rsplit('/',1)[-1].split('.')[0]
    sub = w['sub_url'].rsplit('/',1)[-1].split('.')[0]
    mixin = ''.join((img+sub)[i] for i in MIXIN)[:32]
    return mixin

def sign(params, mixin):
    p = dict(params)
    p['wts'] = str(int(time.time()))
    q = urllib.parse.urlencode(sorted(p.items()))
    p['w_rid'] = hashlib.md5((q+mixin).encode()).hexdigest()
    return p

mixin = refresh_wbi()

GROUPS = {
 'A动作症状': ['坐姿划船腰痛','划船腰疼','划船下背痛','坐姿划船腰酸'],
 'B姿势教学': ['绳索划船教学','坐姿划船正确姿势','坐姿划船发力','绳索划船 姿势'],
 'C核心稳定': ['核心稳定训练 腰','竖脊肌强化','下背力量训练','抗旋转核心'],
 'D顺序疲劳': ['硬拉后划船','硬拉腰痛','硬拉后练背','腰部疲劳 训练'],
}

def dur_sec(d):
    if not d: return 0
    d=str(d)
    if ':' in d:
        parts=[int(x) for x in d.split(':')]
        t=0
        for x in parts: t=t*60+x
        return t
    try: return int(d)
    except: return 0

allv = {}
for g, kws in GROUPS.items():
    for kw in kws:
        for page in (1,2):
            try:
                p = sign({'search_type':'video','keyword':kw,'page':page,'page_size':30}, mixin)
                r = s.get('https://api.bilibili.com/x/web-interface/wbi/search/type', params=p, timeout=25)
                if r.status_code==412 or '"code":-412' in r.text:
                    pool.report_412(); time.sleep(2); mixin=refresh_wbi(); continue
                j = r.json()
                res = (j.get('data') or {}).get('result') or []
                for v in res:
                    bv = v.get('bvid')
                    if not bv: continue
                    title = re.sub(r'<[^>]+>','', v.get('title') or '')
                    item = allv.get(bv)
                    tags = item['_tags'] if item else []
                    tags.append(g+'/'+kw)
                    allv[bv] = {
                        'bvid': bv, 'title': title, 'author': v.get('author'),
                        'play': v.get('play'), 'duration': v.get('duration'),
                        'pubdate': v.get('pubdate'), 'desc': v.get('description') or '',
                        '_tags': tags, '_dur': dur_sec(v.get('duration')),
                    }
                pool.report_success()
            except Exception as e:
                print('ERR', kw, page, repr(e)[:100])
            time.sleep(1.5)
        print('done', g, kw, 'total', len(allv))

# local pool
local = set(json.load(io.open(OUT+r'\本地bvid池.json',encoding='utf-8')))
for bv,v in allv.items():
    v['_new'] = bv not in local

# scoring
W = [('坐姿划船',12),('坐姿划',11),('绳索划',10),('划船',7),('腰痛',10),('腰疼',10),('下背',9),('腰',4),
     ('核心稳定',9),('竖脊肌',10),('下背力量',9),('硬拉',7),('疲劳',6),('髋铰链',8),('骨盆',7),('脊柱',6)]
POS = ['腰痛','腰疼','下背痛','坐姿划船','绳索划','竖脊肌','核心稳定']
def score(v):
    t = ((v['title'] or '')+' '+(v.get('desc') or '')).lower()
    s = sum(w for k,w in W if k in t)
    if any(x in t for x in POS): s += 4
    p = v.get('play') or 0
    s += 4 if p>500000 else 3 if p>150000 else 2 if p>40000 else 1 if p>10000 else -2
    if v['_dur']<150: s-=3
    if v['_dur']>600: s+=1
    return s
for v in allv.values(): v['_score']=score(v)

ranked = sorted(allv.values(), key=lambda x:(-x['_score'], -(x.get('play') or 0)))
json.dump(ranked, io.open(OUT+r'\搜索清单.json','w',encoding='utf-8'), ensure_ascii=False, indent=1)
print('TOTAL UNIQUE', len(allv), 'NEW', sum(1 for v in allv.values() if v['_new']))
print('--- TOP 40 ---')
for v in ranked[:40]:
    print(v['_score'], v['_dur'], v.get('play'), ('NEW' if v['_new'] else 'OLD'), v['bvid'], v['title'][:40], '|', v['author'])
