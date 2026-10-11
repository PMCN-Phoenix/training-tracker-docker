# -*- coding: utf-8 -*-
"""M4 单元测试：Markdown 双向同步往返一致性（纯逻辑，不碰库）"""
import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "web", "backend"))

from app.services import reflection_markdown as md  # noqa: E402

pass_count = 0
fail_count = 0


def check(name, cond, extra=""):
    global pass_count, fail_count
    if cond:
        pass_count += 1
        print(f"  PASS {name} {extra}")
    else:
        fail_count += 1
        print(f"  FAIL {name} {extra}")


# 指向临时目录，避免污染真实 docs/记录/训练感悟
_tmp = tempfile.mkdtemp(prefix="m4md-")
md.MARKDOWN_DIR = os.path.join(_tmp, "训练感悟")


def mk(exercise="平板卧推", set_index=1, **kw):
    base = {
        "id": "rf-test-001",
        "date": "2026-10-11",
        "direction": "push",
        "exercise": exercise,
        "set_index": set_index,
        "session_id": "s1",
        "source": "api",
        "title": "",
        "tags": ["力量", "控制"],
        "content": "起桥稳住，下放慢一点，推起发力感更顺。",
    }
    base.update(kw)
    return base


print("— 单条往返：写 → 读回 —")
r = mk()
block = md.reflection_to_markdown(r)
parsed = md.parse_markdown_reflections(block)
check("解析出 1 条", len(parsed) == 1, f"got {len(parsed)}")
p = parsed[0]
check("id 保真", p.get("id") == "rf-test-001")
check("exercise 保真", p.get("exercise") == "平板卧推")
check("direction 保真", p.get("direction") == "push")
check("set_index 保真", p.get("set_index") == 1)
check("tags 保真", p.get("tags") == ["力量", "控制"])
check("content 保真", p.get("content") == "起桥稳住，下放慢一点，推起发力感更顺。")
check("session_id 保真", p.get("session_id") == "s1")

print("— 日级随笔（set_index=None）—")
r2 = mk(id="rf-test-000", exercise="", set_index=None, title="今天状态不错", tags=None,
        content="推日整体比上周轻松。")
block2 = md.reflection_to_markdown(r2)
p2 = md.parse_markdown_reflections(block2)[0]
check("标题保真", p2.get("title") == "今天状态不错")
check("set_index 为空", p2.get("set_index") is None)
check("无 tags 不报错", p2.get("tags") is None)
check("内容保真", p2.get("content") == "推日整体比上周轻松。")

print("— 写文件 → 读文件 —")
md.write_date_reflections("2026-10-11", [r, r2])
got = md.read_date_reflections("2026-10-11")
check("读回 2 条", len(got) == 2, f"got {len(got)}")
check("内容与输入一致", {x["id"] for x in got} == {"rf-test-000", "rf-test-001"})

print("— 增：sync 追加 —")
r3 = mk(id="rf-test-002", exercise="夹胸", set_index=2, content="夹胸 45 下压感明显。")
md.sync_reflection_to_markdown(r3)
got = md.read_date_reflections("2026-10-11")
check("追加后 3 条", len(got) == 3, f"got {len(got)}")
check("新条目存在", any(x["id"] == "rf-test-002" for x in got))
check("sync 后按 id 升序", got[0]["id"] == "rf-test-000" and got[-1]["id"] == "rf-test-002")

print("— 改：sync 覆盖（按 id）—")
r3b = dict(r3, content="改后：夹胸改 40，找到挤压感。")
md.sync_reflection_to_markdown(r3b)
got = md.read_date_reflections("2026-10-11")
r3got = next(x for x in got if x["id"] == "rf-test-002")
check("覆盖生效", r3got["content"] == "改后：夹胸改 40，找到挤压感。")
check("条数不变", len(got) == 3)

print("— 删：delete 后 2 条 —")
md.delete_reflection_from_markdown("2026-10-11", "rf-test-002")
got = md.read_date_reflections("2026-10-11")
check("删除生效", len(got) == 2 and all(x["id"] != "rf-test-002" for x in got))

print("— 删光 → 文件移除 —")
md.delete_reflection_from_markdown("2026-10-11", "rf-test-001")
md.delete_reflection_from_markdown("2026-10-11", "rf-test-000")
check("文件已移除", not os.path.exists(md.get_markdown_path("2026-10-11")))
check("空日期读回 []", md.read_date_reflections("2026-10-11") == [])

print("— 无日期不写 —")
check("无 date 返回 False", md.sync_reflection_to_markdown({"id": "x"}) is False)

print(f"\n结果：PASS={pass_count} FAIL={fail_count}")
sys.exit(1 if fail_count else 0)
