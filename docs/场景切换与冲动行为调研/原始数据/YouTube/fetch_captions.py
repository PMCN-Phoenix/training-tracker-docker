"""Directly fetch YouTube video page and extract caption tracks."""
import requests, re, json, sys

proxies = {'http':'http://127.0.0.1:7897','https':'http://127.0.0.1:7897'}
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept-Language': 'en-US,en;q=0.9',
}

# Load cookies
cookies = {}
ck_path = r'D:\11.project\iwen-codex\codex-list\training-tracker-docker\docs\场景切换与冲动行为调研\原始数据\YouTube\cookies.txt'
for line in open(ck_path, encoding='utf-8'):
    if line.startswith('#') or not line.strip():
        continue
    p = line.strip().split('\t')
    if len(p) >= 7:
        cookies[p[5]] = p[6]

vid = sys.argv[1] if len(sys.argv) > 1 else '7Ey_vTTgJGc'
r = requests.get(f'https://www.youtube.com/watch?v={vid}', headers=headers, cookies=cookies, proxies=proxies, timeout=25)
print('status:', r.status_code, 'len:', len(r.text))

m = re.search(r'"captionTracks":(\[.*?\])', r.text)
if m:
    tracks = json.loads(m.group(1))
    print(f'Found {len(tracks)} caption tracks:')
    for t in tracks[:8]:
        print(' ', t.get('languageCode'), t.get('kind',''), t.get('baseUrl','')[:250])
else:
    print('no captionTracks found')
    if 'Sign in to confirm' in r.text or 'not a bot' in r.text:
        print('BOT CHECK detected')
    # Save for debugging
    out = r'D:\11.project\iwen-codex\codex-list\training-tracker-docker\docs\场景切换与冲动行为调研\原始数据\YouTube\_page_debug.html'
    open(out, 'w', encoding='utf-8').write(r.text)
    print('saved debug page')
