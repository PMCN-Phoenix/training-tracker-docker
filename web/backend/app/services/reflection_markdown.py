# -*- coding: utf-8 -*-
"""
训练感悟 - Markdown 按日双向同步服务
对应技术方案 §4.3 / 里程碑 M4
将感悟同步到人类可读的 Markdown 文件（docs/记录/训练感悟/YYYY-MM-DD.md），
写（增/改/删）→ 重写当日 md；读 → 从 md 解析回感悟列表。
字段：id / date / direction / exercise / set_index / session_id / source / content / title / tags
"""
import os
import re
from datetime import datetime
from typing import List, Dict, Any, Optional

# Markdown 文件存储目录（技术方案：docs/记录/训练感悟）
MARKDOWN_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))),
    "docs", "记录", "训练感悟"
)


def ensure_markdown_dir():
    if not os.path.exists(MARKDOWN_DIR):
        os.makedirs(MARKDOWN_DIR, exist_ok=True)


def get_markdown_path(date: str) -> str:
    return os.path.join(MARKDOWN_DIR, f"{date}.md")


def reflection_to_markdown(reflection: Dict[str, Any]) -> str:
    """单条感悟 → Markdown 块（隐藏 reflection_id 供回读）"""
    title = reflection.get("title") or ""
    exercise = reflection.get("exercise") or ""
    set_index = reflection.get("set_index")
    if not title:
        title = f"{exercise} · 第{set_index}组" if set_index else (exercise or "当日随笔")

    lines = [f"### {title}", ""]

    meta = []
    if reflection.get("direction"):
        meta.append(f"**方向**: {reflection['direction']}")
    if exercise:
        meta.append(f"**动作**: {exercise}")
    if set_index:
        meta.append(f"**组号**: {set_index}")
    if reflection.get("session_id"):
        meta.append(f"**会话**: {reflection['session_id']}")
    if reflection.get("source"):
        meta.append(f"**来源**: {reflection['source']}")
    lines.append(" | ".join(meta))
    lines.append("")

    tags = reflection.get("tags") or []
    if tags:
        lines.append(f"**标签**: {' '.join(tags)}")
        lines.append("")

    content = reflection.get("content", "")
    lines.append(content)
    lines.append("")
    lines.append(f"<!-- reflection_id: {reflection.get('id', '')} -->")
    lines.append("")
    lines.append("---")
    lines.append("")

    return "\n".join(lines)


def parse_markdown_reflections(content: str) -> List[Dict[str, Any]]:
    """Markdown 内容 → 感悟列表（反向解析，字段与上面一一对应）"""
    reflections = []
    blocks = re.split(r'^### ', content, flags=re.MULTILINE)

    for block in blocks[1:]:
        r: Dict[str, Any] = {}
        m = re.search(r'<!-- reflection_id: (.+?) -->', block)
        if m:
            r["id"] = m.group(1).strip()

        first_line = block.split("\n")[0].strip()
        title = re.sub(r'^[\U0001F300-\U0001F9FF\U00002600-\U000027BF\U0001F000-\U0001F02F\U0001FA00-\U0001FA6F\s]+', '', first_line).strip()
        r["title"] = title

        def grab(field):
            m2 = re.search(rf'\*\*{field}\*\*: (.+?)(?:\s*\||\n|$)', block)
            return m2.group(1).strip() if m2 else None

        r["direction"] = grab("方向")
        r["exercise"] = grab("动作")
        r["session_id"] = grab("会话")
        r["source"] = grab("来源")
        si = grab("组号")
        r["set_index"] = int(si) if si and si.isdigit() else None

        tm = re.search(r'\*\*标签\*\*: (.+?)(?:\n|$)', block)
        if tm:
            r["tags"] = [t.strip() for t in tm.group(1).split() if t.strip()]

        cm = re.search(r'\*\*标签\*\*:.*?\n\n(.*?)(?:\n<!-- reflection_id)', block, re.DOTALL)
        if not cm:
            cm = re.search(r'\*\*方向\*\*:.*?\n\n(.*?)(?:\n<!-- reflection_id)', block, re.DOTALL)
        if cm:
            r["content"] = cm.group(1).strip()

        if r.get("title") or r.get("content"):
            reflections.append(r)

    return reflections


def read_date_reflections(date: str) -> List[Dict[str, Any]]:
    """读：从 Markdown 文件解析该日感悟"""
    filepath = get_markdown_path(date)
    if not os.path.exists(filepath):
        return []
    with open(filepath, "r", encoding="utf-8") as f:
        return parse_markdown_reflections(f.read())


def write_date_reflections(date: str, reflections: List[Dict[str, Any]]) -> bool:
    """写：整日重写 Markdown（先清后写，保证删除/更新一致）"""
    ensure_markdown_dir()
    filepath = get_markdown_path(date)
    lines = [
        f"# 训练感悟 - {date}",
        "",
        f"> 自动生成于 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        "---",
        "",
    ]
    for r in reflections:
        lines.append(reflection_to_markdown(r))
    with open(filepath, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    return True


def sync_reflection_to_markdown(reflection: Dict[str, Any]) -> bool:
    """写同步：增/改单条后重写当日 md（按 id 覆盖或追加）"""
    date = reflection.get("date", "")
    if not date:
        return False
    existing = read_date_reflections(date)
    ref_id = reflection.get("id", "")
    found = False
    for i, item in enumerate(existing):
        if item.get("id") == ref_id:
            existing[i] = reflection
            found = True
            break
    if not found:
        existing.append(reflection)
    existing.sort(key=lambda x: x.get("id", ""))
    return write_date_reflections(date, existing)


def delete_reflection_from_markdown(date: str, ref_id: str) -> bool:
    """写同步：删除后重写当日 md；无剩余则删文件"""
    existing = read_date_reflections(date)
    remaining = [item for item in existing if item.get("id") != ref_id]
    if len(remaining) == len(existing):
        return True
    if remaining:
        return write_date_reflections(date, remaining)
    filepath = get_markdown_path(date)
    if os.path.exists(filepath):
        os.remove(filepath)
    return True


def list_all_markdown_dates() -> List[str]:
    ensure_markdown_dir()
    dates = []
    for filename in os.listdir(MARKDOWN_DIR):
        if filename.endswith(".md") and re.match(r'\d{4}-\d{2}-\d{2}\.md$', filename):
            dates.append(filename.replace(".md", ""))
    dates.sort(reverse=True)
    return dates


def import_all_from_markdown() -> List[Dict[str, Any]]:
    """读→写回：从所有 md 导入感悟（date 补全）"""
    all_reflections = []
    for date in list_all_markdown_dates():
        for r in read_date_reflections(date):
            r["date"] = date
            all_reflections.append(r)
    return all_reflections
