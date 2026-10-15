# -*- coding: utf-8 -*-
"""场景切换与冲动行为 - B站搜索脚本
按SOP: wbi签名搜索, 多关键词去重, 相关度打分
"""
import sys, os, time, json, re, hashlib, urllib.parse
import requests
from pathlib import Path

# 引入cookie池
sys.path.insert(0, r"D:\11.project\iwen-codex\bilibili-cookies")
from cookie_manager import BiliCookiePool

OUT_DIR = Path(r"D:\11.project\iwen-codex\codex-list\training-tracker-docker\docs\场景切换与冲动行为调研\原始数据\B站")
OUT_DIR.mkdir(parents=True, exist_ok=True)

MIXIN = [46,47,18,2,53,8,23,32,15,50,10,31,58,3,45,35,27,43,5,49,33,9,42,19,29,28,14,39,
         12,38,41,13,37,48,7,16,24,55,40,61,26,17,0,1,60,51,30,4,22,25,54,21,56,59,6,63,
         57,62,11,36,20,34,44,52]

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"

pool = BiliCookiePool()
session = requests.Session()
session.headers.update({"User-Agent": UA, "Referer": "https://www.bilibili.com/"})

def refresh_cookie():
    ck = pool.get_cookie()
    session.headers.update({"Cookie": ck})
    return ck

# 初始化wbi keys
def get_wbi_keys():
    refresh_cookie()
    nav = session.get('https://api.bilibili.com/x/web-interface/nav', timeout=20).json()
    wbi = nav['data']['wbi_img']
    img = wbi['img_url'].rsplit('/', 1)[-1].split('.')[0]
    sub = wbi['sub_url'].rsplit('/', 1)[-1].split('.')[0]
    mixin = ''.join((img + sub)[i] for i in MIXIN)[:32]
    return mixin

MIXIN_KEY = get_wbi_keys()
print(f"[wbi] mixin key acquired: {MIXIN_KEY[:8]}...")

def sign(p):
    p = dict(p); p['wts'] = str(int(time.time()))
    q = urllib.parse.urlencode(sorted(p.items()))
    p['w_rid'] = hashlib.md5((q + MIXIN_KEY).encode()).hexdigest()
    return p

def search_one(kw, page=1):
    for attempt in range(3):
        try:
            p = sign({'search_type': 'video', 'keyword': kw, 'page': page, 'page_size': 30})
            r = session.get('https://api.bilibili.com/x/web-interface/wbi/search/type',
                           params=p, timeout=25)
            d = r.json()
            if d.get('code') == 0:
                pool.report_success()
                return d.get('data', {}).get('result') or []
            elif d.get('code') == -412 or 'banned' in str(d.get('message','')):
                print(f"  [412] {kw}, switching cookie...")
                pool.report_412()
                refresh_cookie()
                time.sleep(2)
            else:
                print(f"  [warn] {kw}: code={d.get('code')} msg={d.get('message')}")
                return []
        except Exception as e:
            print(f"  [err] {kw}: {e}")
            time.sleep(2)
    return []

# 关键词组（覆盖6个子主题 + 场景词）
KEYWORDS = [
    # 1. 注意力残留/任务切换
    "注意力残留",
    "attention residue 注意力",
    "任务切换成本 心理学",
    "context switching 认知",
    # 2. 习惯回路
    "习惯回路 cue routine reward",
    "原子习惯 习惯养成",
    "微习惯 微小改变",
    # 3. 手机成瘾/多巴胺
    "手机成瘾 多巴胺",
    "短视频成瘾 机制",
    "多巴胺脱敏 刷手机",
    "不由自主看手机",
    # 4. 过渡仪式/环境设计
    "过渡仪式 transition ritual",
    "增加摩擦 专注 手机",
    "环境设计 习惯 自控",
    # 5. 拖延/执行功能/自我损耗
    "拖延症 心理学 机制",
    "自我损耗 ego depletion",
    "意志力 执行功能",
    # 6. 默认模式网络/走神
    "默认模式网络 DMN",
    "心智游移 走神",
    # 场景词
    "下课 刷手机 间隙",
    "工作间隙 看手机 停不下来",
    "切换场景 分心",
]

print(f"[search] 共 {len(KEYWORDS)} 组关键词")
all_videos = {}  # bvid -> info

for i, kw in enumerate(KEYWORDS):
    print(f"[{i+1}/{len(KEYWORDS)}] {kw}")
    results = search_one(kw, page=1)
    new_count = 0
    for v in results:
        bvid = v.get('bvid')
        if not bvid:
            continue
        title = re.sub(r'<[^>]+>', '', v.get('title') or '')
        dur = v.get('duration') or '0:0'
        # 解析duration秒数
        try:
            parts = str(dur).split(':')
            if len(parts) == 2:
                dur_s = int(parts[0])*60 + int(parts[1])
            elif len(parts) == 3:
                dur_s = int(parts[0])*3600 + int(parts[1])*60 + int(parts[2])
            else:
                dur_s = 0
        except:
            dur_s = 0
        if bvid not in all_videos:
            all_videos[bvid] = {
                'bvid': bvid,
                'title': title,
                'author': v.get('author', ''),
                'play': v.get('play', 0),
                'duration': str(dur),
                'dur_s': dur_s,
                'description': re.sub(r'<[^>]+>', '', v.get('description') or ''),
                'pubdate': v.get('pubdate', 0),
                'search_kws': [kw],
            }
            new_count += 1
        else:
            all_videos[bvid]['search_kws'].append(kw)
    print(f"    命中 {len(results)} 条, 新增 {new_count} 条, 累计去重 {len(all_videos)}")
    time.sleep(1.5)

print(f"\n[done] 去重后共 {len(all_videos)} 个视频")

# 相关度打分
def score(v):
    t = (v['title'] or '') + ' ' + (v.get('description') or '')
    tl = t.lower()
    s = 0.0
    # 核心概念权重
    weight_map = [
        # 注意力残留/任务切换
        ('注意力残留', 10), ('attention residue', 10), ('任务切换', 6), ('切换成本', 6),
        ('context switching', 6), ('认知切换', 5),
        # 习惯回路
        ('习惯回路', 8), ('cue', 3), ('routine', 3), ('原子习惯', 7), ('微习惯', 6),
        ('习惯养成', 5), ('习惯的力量', 5),
        # 手机成瘾/多巴胺
        ('手机成瘾', 8), ('多巴胺', 6), ('刷手机', 7), ('短视频成瘾', 8),
        ('手机依赖', 7), ('上瘾', 5), ('成瘾', 5), ('脱敏', 5),
        ('不由自主', 6), ('控制不住', 5), ('停不下来', 5),
        # 过渡仪式/环境设计
        ('过渡仪式', 8), ('transition', 3), ('摩擦', 6), ('环境设计', 5),
        ('专注力', 3), ('专注', 2),
        # 拖延/自我损耗
        ('拖延', 5), ('自我损耗', 8), ('ego depletion', 8), ('意志力', 5),
        ('执行功能', 5), ('自控', 3),
        # DMN/走神
        ('默认模式', 8), ('DMN', 8), ('心智游移', 7), ('走神', 6), ('白日梦', 3),
        # 场景词
        ('下课', 3), ('间隙', 4), ('碎片时间', 4), ('休息时间', 2),
        ('切换', 2), ('场景', 2),
        # 心理学/认知科学正向
        ('心理学', 2), ('认知', 2), ('神经科学', 3), ('脑科学', 3),
        # 反相关（营销/卖课）
        ('课程', -3), ('报名', -4), ('加微信', -5), ('私域', -4),
        ('带货', -3), ('广告', -3), ('购买', -3),
    ]
    for k, w in weight_map:
        if k.lower() in tl:
            s += w
    # 播放量加权
    p = v.get('play') or 0
    if p > 500000: s += 3
    elif p > 100000: s += 2
    elif p > 30000: s += 1
    elif p > 5000: s += 0.5
    else: s -= 0.5
    # 时长：3-30分钟信息量最好
    d = v.get('dur_s', 0)
    if d < 60: s -= 2
    elif d > 7200: s -= 1  # 超长直播回放
    elif d >= 180: s += 1
    # 被多组关键词命中加分
    s += min(len(v.get('search_kws', [])), 5) * 0.5
    return s

scored = []
for bvid, v in all_videos.items():
    v['score'] = score(v)
    scored.append(v)

scored.sort(key=lambda x: -x['score'])

# 保存全量搜索清单
out_all = OUT_DIR / "搜索清单.json"
out_all.write_text(json.dumps(scored, ensure_ascii=False, indent=2), encoding='utf-8')
print(f"\n[save] 全量搜索清单 -> {out_all} ({len(scored)}条)")

# 打印 top 40 供人工过
print("\n=== TOP 40 候选 ===")
for i, v in enumerate(scored[:40]):
    print(f"{i+1:2d}. [{v['score']:5.1f}] {v['bvid']} | {v['title'][:42]} | {v['author']} | play={v['play']} | {v['duration']}")
