# -*- coding: utf-8 -*-
import urllib.request, sys
line = 'ppl_reflection,id=ref_20261008_test2,date=2026-10-08,direction=push,exercise=平板卧推,set_index=2,source=web content="补录测试",tags="发力感" 1700000000000000000'
url = "http://127.0.0.1:8086/api/v2/write?org=training-org&bucket=training"
req = urllib.request.Request(url, data=line.encode("utf-8"), method="POST")
req.add_header("Authorization", "Token training-super-secret-token-2026")
req.add_header("Content-Type", "text/plain")
try:
    with urllib.request.urlopen(req, timeout=10) as resp:
        print("urllib OK", resp.status)
except urllib.error.HTTPError as e:
    print("urllib HTTPError", e.code)
    print(e.read().decode("utf-8", "ignore")[:500])
