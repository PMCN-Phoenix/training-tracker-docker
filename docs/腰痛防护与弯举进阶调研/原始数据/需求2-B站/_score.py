# -*- coding: utf-8 -*-
"""加权打分筛选候选视频"""
import json, os, re

OUT_DIR = r"D:\11.project\iwen-codex\codex-list\training-tracker-docker\docs\腰痛防护与弯举进阶调研\原始数据\需求2-B站"
d = json.load(open(os.path.join(OUT_DIR, '搜索清单.json'), encoding='utf-8'))
videos = d['videos']

# 关键词权重（相关度主导）
WEIGHTS = [
    # 核心词 12-14
    ('绳索弯举', 14), ('绳索臂弯举', 14),
    ('ez杠弯举', 13), ('ez 杠弯举', 13), ('曲杆弯举', 13), ('曲杠弯举', 13),
    ('牧师凳弯举', 13), ('牧师椅弯举', 13), ('斜托弯举', 13),
    ('锤式弯举', 13), ('锤击弯举', 12),
    ('上斜哑铃弯举', 12),
    ('磁吸配重片', 14), ('磁吸片', 13), ('配重片 1.25', 12), ('小重量片', 12), ('小片', 10),
    ('double progression', 14), ('双重渐进', 12), ('双渐进', 12),
    ('哑铃弯举', 11), ('杠铃弯举', 10),
    ('弯举 重量', 9), ('弯举 加重', 9), ('弯举 上不去', 10),
    ('二头 渐进', 9), ('肱二头 渐进', 9),
    ('小肌群 升重', 11), ('小肌群 渐进', 10),
    ('波浪式渐进', 10), ('波浪渐进', 10),
    ('次数递增', 9), ('次数先行', 11),
    # 边缘词 5-7
    ('渐进超负荷', 6), ('渐进', 5), ('平台期', 5), ('增肌', 4),
]

# 主题命中加成
THEME_HIT = ['弯举', '二头', '肱二', '臂弯', '小片', '配重片', '绳索', 'ez', '牧师', '锤式', '上斜']

# 排除词（明显无关）
EXCLUDE = ['女生', '女性', '女神', '细臂', '女团', '马甲线', '减脂', '减肥', '瘦',
           '比赛', '健美比赛', '奥赛', '阿诺德', '药', '科技', '类固醇',
           '残疾人', '手术', '康复', '伤病恢复', '腰痛', '腰椎',
           '俯卧撑', '引体向上', '深蹲', '硬拉', '卧推', '腿', '跑步',
           '青少年', '儿童', '老年']

def score(v):
    t = (v['title'] + ' ' + v.get('description','')).lower()
    s = 0
    matched_kw = []
    for k, w in WEIGHTS:
        if k.lower() in t:
            s += w
            matched_kw.append(k)
    # 主题命中加成
    if any(x in t for x in THEME_HIT):
        s += 4
    # 播放量弱信号
    p = v.get('play', 0)
    if p > 500000: s += 4
    elif p > 150000: s += 3
    elif p > 40000: s += 2
    elif p > 10000: s += 1
    else: s -= 1  # 低播放轻微扣，但不重扣
    # 时长
    dur = v.get('dur_sec', 0)
    if dur < 150: s -= 3   # <2.5分钟装不下
    elif dur > 600: s += 1  # 长视频
    elif dur < 60: s -= 5   # 短视频
    # 本地已有加分（质量已筛过）
    if v.get('_local'): s += 5
    # 排除
    for ex in EXCLUDE:
        if ex in t:
            s -= 20
            break
    return s, matched_kw

scored = []
for v in videos:
    s, kws = score(v)
    v['_score'] = s
    v['_matched_kw'] = kws
    scored.append(v)

scored.sort(key=lambda x: -x['_score'])

# 输出 top 60
print(f"=== TOP 60 ===")
for i, v in enumerate(scored[:60]):
    local = '★本地' if v.get('_local') else ''
    print(f"{i+1:2d}. [{v['_score']:3d}] {local} {v['bvid']} | {v['title'][:50]} | {v['author'][:15]} | play={v['play']} | dur={v['duration']}")

# 保存精选（top 50 + 所有本地相关）
picked = [v for v in scored if v.get('_local') and v['_score'] > 5] + scored[:50]
# 去重
seen = set()
final = []
for v in picked:
    if v['bvid'] in seen: continue
    seen.add(v['bvid'])
    final.append(v)

with open(os.path.join(OUT_DIR, '精选视频明细.json'), 'w', encoding='utf-8') as f:
    json.dump({'total_scored': len(scored), 'picked': final}, f, ensure_ascii=False, indent=2)

print(f"\n=== 精选: {len(final)} ===")
