# -*- coding: utf-8 -*-
import sys, re, json, time, hashlib, urllib.parse, io, os
sys.path.insert(0, r"D:\11.project\iwen-codex\bilibili-cookies")
import requests
from cookie_manager import BiliCookiePool

OUT = r"D:\11.project\iwen-codex\codex-list\training-tracker-docker\docs\腰痛防护与弯举进阶调研\原始数据\需求1-B站"
SUBDIR = os.path.join(OUT, '字幕')
os.makedirs(SUBDIR, exist_ok=True)

MIXIN = [46,47,18,2,53,8,23,32,15,50,10,31,58,3,45,35,27,43,5,49,33,9,42,19,29,28,14,39,12,38,41,13,37,48,7,16,24,55,40,61,26,17,0,1,60,51,30,4,22,25,54,21,56,59,6,63,57,62,11,36,20,34,44,52]

pool = BiliCookiePool()
s = requests.Session()
s.headers.update({'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36'})

def new_cookie():
    c = pool.get_cookie()
    s.headers['Cookie'] = c
    return c

def wbi_mixin():
    new_cookie()
    nav = s.get('https://api.bilibili.com/x/web-interface/nav', timeout=20).json()
    w = nav['data']['wbi_img']
    img = w['img_url'].rsplit('/',1)[-1].split('.')[0]
    sub = w['sub_url'].rsplit('/',1)[-1].split('.')[0]
    return ''.join((img+sub)[i] for i in MIXIN)[:32]

mixin = wbi_mixin()
def sign(params):
    p = dict(params); p['wts']=str(int(time.time()))
    q = urllib.parse.urlencode(sorted(p.items()))
    p['w_rid']=hashlib.md5((q+mixin).encode()).hexdigest()
    return p

def get_html(bv):
    for attempt in range(3):
        try:
            new_cookie()
            r = s.get(f'https://www.bilibili.com/video/{bv}/', timeout=25)
            if r.status_code==412 or '"code":-412' in r.text[:200]:
                pool.report_412(); time.sleep(2); continue
            m = re.search(r'window\.__INITIAL_STATE__=(.*?);\(function', r.text, re.S) or re.search(r'window\.__INITIAL_STATE__=(.*?);\s*</script>', r.text, re.S)
            if not m: return None
            return json.loads(m.group(1))
        except Exception as e:
            print('  html err', repr(e)[:80]); time.sleep(2)
    return None

def get_subtitle(bv, cid):
    for attempt in range(3):
        try:
            new_cookie()
            p = sign({'bvid':bv,'cid':cid})
            r = s.get('https://api.bilibili.com/x/player/wbi/v2', params=p, timeout=20)
            if r.status_code==412 or '"code":-412' in r.text[:200]:
                pool.report_412(); time.sleep(2); continue
            subs = r.json()['data']['subtitle']['subtitles']
            if not subs: return []
            out=[]
            for su in subs:
                url = su['subtitle_url']
                if url.startswith('//'): url='https:'+url
                rr = s.get(url, timeout=20)
                body = rr.json().get('body',[])
                out.append({'lan':su.get('lan'),'lan_doc':su.get('lan_doc'),'body':body})
                time.sleep(1)
            return out
        except Exception as e:
            print('  sub err', repr(e)[:80]); time.sleep(2)
    return None

def get_comments(aid):
    comments=[]
    for pn in range(1,12):
        try:
            new_cookie()
            r = s.get('https://api.bilibili.com/x/v2/reply', params={'oid':aid,'type':1,'pn':pn,'ps':20,'sort':2}, timeout=20)
            if r.status_code==412 or '"code":-412' in r.text[:200]:
                pool.report_412(); time.sleep(2); continue
            j = r.json().get('data') or {}
            repl = j.get('replies') or []
            if not repl: break
            for rp in repl:
                comments.append({'message':rp['content']['message'],'like':rp['like'],'rcount':rp.get('rcount',0),'root':rp['rpid']})
            if j.get('cursor',{}).get('is_end'): break
            time.sleep(1.5)
        except Exception as e:
            print('  c err', repr(e)[:80]); break
    # 楼中楼
    roots = [c['root'] for c in comments if c['rcount']>0][:15]
    for root in roots:
        try:
            new_cookie()
            r = s.get('https://api.bilibili.com/x/v2/reply/reply', params={'oid':aid,'type':1,'root':root,'pn':1,'ps':20}, timeout=20)
            if r.status_code==412 or '"code":-412' in r.text[:200]:
                pool.report_412(); time.sleep(2); continue
            reps = (r.json().get('data') or {}).get('replies') or []
            for rp in reps:
                comments.append({'message':rp['content']['message'],'like':rp['like'],'rcount':0,'root':root,'sub':True})
            time.sleep(1.2)
        except Exception as e:
            pass
    return comments

BVS = ['BV1UG411k7ZM','BV1y14y1X7by','BV1ZyCAYQEVv','BV133kxBFEA6','BV1as4y157pd',
       'BV1VTGR6gENz','BV19u411S7Ni','BV1DSTk6sEwJ','BV1994y1N7ea','BV1BJ411R7fV',
       'BV1Q2pE6AE3p','BV1P3zYBaEtP','BV1hf4y177bz','BV1T3Pxz1Epm','BV1gA411B7kK']

results=[]
for bv in BVS:
    d = get_html(bv)
    if not d:
        print('FAIL html', bv); results.append({'bvid':bv,'_fail':'html'}); continue
    vd = d.get('videoData') or {}
    aid = vd.get('aid'); cid = vd.get('cid')
    title = vd.get('title'); owner=(vd.get('owner') or {}).get('name')
    dur = vd.get('duration')
    print('==', bv, title, 'aid',aid,'cid',cid,'dur',dur)
    subs = get_subtitle(bv, cid)
    cov = None
    if subs:
        body = subs[0]['body']
        to_max = max((x['to'] for x in body), default=0)
        cov = round(to_max/dur,3) if dur else None
        # save full text
        txt='\n'.join(f"[{int(x['from']//60):02d}:{int(x['from']%60):02d}] {x['content']}" for x in body)
        io.open(os.path.join(SUBDIR, f'字幕-{bv}.txt'),'w',encoding='utf-8').write(txt)
        json.dump(subs[0], io.open(os.path.join(SUBDIR, f'字幕-{bv}.json'),'w',encoding='utf-8'), ensure_ascii=False, indent=1)
    comments = get_comments(aid)
    results.append({'bvid':bv,'aid':aid,'cid':cid,'title':title,'owner':owner,'duration':dur,
                    'subtitles': 'yes' if subs else 'none','cov':cov,'sub_lan':subs[0]['lan_doc'] if subs else None,
                    'comments':comments,'n_comments':len(comments)})
    print('   sub:', 'yes' if subs else 'NONE', 'cov', cov, 'comments', len(comments))
    time.sleep(2)

json.dump(results, io.open(OUT+r'\新抓视频明细.json','w',encoding='utf-8'), ensure_ascii=False, indent=1)
print('DONE', len(results))
