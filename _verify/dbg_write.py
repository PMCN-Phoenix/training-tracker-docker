# -*- coding: utf-8 -*-
import requests
line = 'ppl_reflection,id=ref_20261008_test,date=2026-10-08,direction=push,exercise=平板卧推,set_index=2,source=web content="补录测试",tags="发力感" 1700000000000000000'
r = requests.post('http://127.0.0.1:8086/api/v2/write?org=training-org&bucket=training',
                  data=line.encode('utf-8'),
                  headers={'Authorization': 'Token training-super-secret-token-2026',
                           'Content-Type': 'text/plain'}, timeout=10)
print(r.status_code)
print(r.text[:500])
