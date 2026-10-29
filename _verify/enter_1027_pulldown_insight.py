# -*- coding: utf-8 -*-
"""录入 2026-10-27 高位下拉 第4组 感悟（用户口述，次日 10-28 补录）

- 感悟挂到动作级/组级：消息格式 = 动作名 + [第N组] + 感悟词 + 内容
- parse-training 的感悟解析：取「感悟」识别词前最近的动作 + 「第N组」→ 组级
- 归属时间：2026-10-27 20:30（回挂到昨天拉日）
"""
import requests
from urllib.parse import quote

NR = "http://127.0.0.1:1880"
ts = "2026-10-27T20:30:00+08:00"

text = (
    "高位下拉 第4组 感悟 "
    "最后一组特别有感觉：拉下来再往上起时背阔肌仍持续发力，"
    "不是卸力后再重新拉，而是像有弹性的过程（张力不断）。"
    "发力感从肩胛骨下面往上走——左肩胛向左上、右肩胛向右上旋转（上回旋）。"
    "要点：顶部不完全卸死，肘微屈不耸肩，离心 2~3 秒主动送回，"
    "想着「把杆推上去」而不是「被杆拉上去」。目标是把这种感觉常态化到每一组。"
)

print("=== 发送文本 ===")
print(text)
print()

url = f"{NR}/add-training?source=phone&time={quote(ts)}"
r = requests.post(url, data=text.encode("utf-8"),
                  headers={"Content-Type": "text/plain; charset=utf-8"}, timeout=30)
print(f"[{r.status_code}]")
try:
    print(r.json())
except Exception:
    print(r.text[:400])
