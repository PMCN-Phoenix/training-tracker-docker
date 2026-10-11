# -*- coding: utf-8 -*-
"""
训练感悟功能 - 数据访问层（InfluxDB）
Measurement: ppl_reflection（三级粒度：组级/动作级/日级）
"""
import time
import uuid
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from .influx_client import db


# ==================== 工具函数 ====================

def _escape_tag_value(value: str) -> str:
    """转义 InfluxDB tag 值中的空格、逗号、等号"""
    return value.replace(" ", "\\ ").replace(",", "\\,").replace("=", "\\=")


def _escape_field_string(value: str) -> str:
    """转义 InfluxDB field 字符串值中的双引号"""
    return value.replace('"', '\\"')


def _generate_reflection_id(date: str) -> str:
    """生成感悟唯一 ID: ref_{YYYYMMDD}_{短UUID}"""
    date_compact = date.replace("-", "")
    short_uuid = uuid.uuid4().hex[:8]
    return f"ref_{date_compact}_{short_uuid}"


def _date_to_timestamp(date_str: str) -> int:
    """日期字符串转时间戳（北京时间 00:00:00）"""
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    return int(dt.timestamp())


def _tag_line(parts: List[str]) -> str:
    return ",".join(parts)


def _field_line(fields: List[str]) -> str:
    """Line Protocol 字段用逗号分隔（空格分隔会被 InfluxDB 拒绝）"""
    return ",".join(fields)


# ==================== 感悟 CRUD ====================

def create_ppl_reflection(
    content: str,
    date: str,
    direction: Optional[str] = None,
    exercise: Optional[str] = None,
    set_index: Optional[int] = None,
    session_id: Optional[str] = None,
    source: str = "web",
    title: Optional[str] = None,
    tags: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    创建一条训练感悟
    返回: {"id": "...", "created_at": "..."}
    """
    ref_id = _generate_reflection_id(date)
    now_ns = int(time.time() * 1e9)
    tags_str = ",".join(tags) if tags else ""

    tag_parts = [
        f"id={_escape_tag_value(ref_id)}",
        f"date={_escape_tag_value(date)}",
    ]
    if direction:
        tag_parts.append(f"direction={_escape_tag_value(direction)}")
    if exercise:
        tag_parts.append(f"exercise={_escape_tag_value(exercise)}")
    if set_index is not None:
        tag_parts.append(f"set_index={str(set_index)}")
    if session_id:
        tag_parts.append(f"session_id={_escape_tag_value(session_id)}")
    tag_parts.append(f"source={_escape_tag_value(source)}")

    field_parts = [f'content="{_escape_field_string(content)}"']
    if title:
        field_parts.append(f'title="{_escape_field_string(title)}"')
    field_parts.append(f'tags="{_escape_field_string(tags_str)}"')

    line = f"ppl_reflection,{_tag_line(tag_parts)} {_field_line(field_parts)} {now_ns}"
    success = db.write(line)
    if not success:
        raise Exception("写入 InfluxDB 失败")

    return {
        "id": ref_id,
        "created_at": datetime.fromtimestamp(now_ns / 1e9).isoformat(),
    }


def get_ppl_reflection_by_id(ref_id: str) -> Optional[Dict[str, Any]]:
    """根据 ID 获取单条感悟"""
    flux = f'''
from(bucket: "{db.bucket}")
  |> range(start: -365d)
  |> filter(fn: (r) => r._measurement == "ppl_reflection")
  |> filter(fn: (r) => r.id == "{ref_id}")
  |> pivot(rowKey: ["_time"], columnKey: ["_field"], valueColumn: "_value")
  |> keep(columns: ["_time", "id", "date", "direction", "exercise", "set_index", "session_id", "source", "content", "title", "tags"])
  |> limit(n: 1)
'''
    rows = db.query(flux)
    if not rows:
        return None
    return _parse_reflection_row(rows[0])


def list_ppl_reflections(
    direction: Optional[str] = None,
    exercise: Optional[str] = None,
    date: Optional[str] = None,
    set_index: Optional[int] = None,
    tag: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
) -> Dict[str, Any]:
    """获取感悟列表（支持筛选）"""
    filters = ['r._measurement == "ppl_reflection"']
    if direction:
        filters.append(f'r.direction == "{direction}"')
    if exercise:
        filters.append(f'r.exercise == "{exercise}"')
    if date:
        filters.append(f'r.date == "{date}"')
    if set_index is not None:
        filters.append(f'r.set_index == "{str(set_index)}"')
    filter_str = " and ".join(filters)

    flux = f'''
from(bucket: "{db.bucket}")
  |> range(start: -365d)
  |> filter(fn: (r) => {filter_str})
  |> pivot(rowKey: ["_time"], columnKey: ["_field"], valueColumn: "_value")
  |> keep(columns: ["_time", "id", "date", "direction", "exercise", "set_index", "session_id", "source", "content", "title", "tags"])
  |> sort(columns: ["_time"], desc: true)
  |> limit(n: {limit}, offset: {offset})
'''
    rows = db.query(flux)
    items = [_parse_reflection_row(row) for row in rows]

    if tag:
        items = [item for item in items if tag in (item.get("tags") or [])]

    return {"items": items, "total": len(items)}


def update_ppl_reflection(ref_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
    """更新感悟（删除旧数据 + 写入新数据，保留原 ID）"""
    old = get_ppl_reflection_by_id(ref_id)
    if not old:
        raise Exception(f"感悟不存在: {ref_id}")

    merged = {**old, **updates}
    for key in ["id", "created_at"]:
        merged.pop(key, None)

    delete_ppl_reflection(ref_id)

    now_ns = int(time.time() * 1e9)
    tags_str = ",".join(merged.get("tags") or [])

    tag_parts = [
        f"id={_escape_tag_value(ref_id)}",
        f"date={_escape_tag_value(merged['date'])}",
    ]
    if merged.get("direction"):
        tag_parts.append(f"direction={_escape_tag_value(merged['direction'])}")
    if merged.get("exercise"):
        tag_parts.append(f"exercise={_escape_tag_value(merged['exercise'])}")
    if merged.get("set_index") is not None:
        tag_parts.append(f"set_index={str(merged['set_index'])}")
    if merged.get("session_id"):
        tag_parts.append(f"session_id={_escape_tag_value(merged['session_id'])}")
    tag_parts.append(f"source={_escape_tag_value(merged.get('source') or 'web')}")

    field_parts = [f'content="{_escape_field_string(merged["content"])}"']
    if merged.get("title"):
        field_parts.append(f'title="{_escape_field_string(merged["title"])}"')
    field_parts.append(f'tags="{_escape_field_string(tags_str)}"')

    line = f"ppl_reflection,{_tag_line(tag_parts)} {_field_line(field_parts)} {now_ns}"
    success = db.write(line)
    if not success:
        raise Exception("写入 InfluxDB 失败")

    return {"id": ref_id, "updated_at": datetime.fromtimestamp(now_ns / 1e9).isoformat()}


def delete_ppl_reflection(ref_id: str) -> Dict[str, Any]:
    """删除感悟"""
    ok = db.delete(f'_measurement="ppl_reflection" AND id="{ref_id}"')
    if not ok:
        raise Exception("删除失败")
    return {"id": ref_id, "deleted": True}


# ==================== 统计 ====================

def get_ppl_reflection_stats() -> Dict[str, Any]:
    """获取感悟统计数据（总数/今日/连续天数/覆盖动作数）"""
    today = datetime.now().strftime("%Y-%m-%d")

    flux = f'''
from(bucket: "{db.bucket}")
  |> range(start: -365d)
  |> filter(fn: (r) => r._measurement == "ppl_reflection")
  |> filter(fn: (r) => r._field == "content")
  |> group(columns: ["id"])
  |> count()
'''
    rows = db.query(flux)
    total_count = len(rows)

    flux = f'''
from(bucket: "{db.bucket}")
  |> range(start: -1d)
  |> filter(fn: (r) => r._measurement == "ppl_reflection")
  |> filter(fn: (r) => r.date == "{today}")
  |> filter(fn: (r) => r._field == "content")
  |> group(columns: ["id"])
  |> count()
'''
    rows = db.query(flux)
    today_count = len(rows)

    flux = f'''
from(bucket: "{db.bucket}")
  |> range(start: -365d)
  |> filter(fn: (r) => r._measurement == "ppl_reflection")
  |> filter(fn: (r) => r._field == "content")
  |> keep(columns: ["date"])
  |> distinct(column: "date")
'''
    rows = db.query(flux)
    recorded_dates = set()
    for row in rows:
        d = row.get("_value", "")
        if d:
            recorded_dates.add(d)

    consecutive_days = 0
    check_date = datetime.now()
    while check_date.strftime("%Y-%m-%d") in recorded_dates:
        consecutive_days += 1
        check_date -= timedelta(days=1)

    flux = f'''
from(bucket: "{db.bucket}")
  |> range(start: -365d)
  |> filter(fn: (r) => r._measurement == "ppl_reflection")
  |> filter(fn: (r) => r._field == "content")
  |> keep(columns: ["exercise"])
  |> distinct(column: "exercise")
'''
    rows = db.query(flux)
    exercise_count = len([r for r in rows if r.get("_value")])

    return {
        "total_count": total_count,
        "today_count": today_count,
        "consecutive_days": consecutive_days,
        "exercise_count": exercise_count,
    }


# ==================== 内部解析函数 ====================

def _parse_reflection_row(row: Dict[str, Any]) -> Dict[str, Any]:
    """解析 InfluxDB 返回的感悟行"""
    tags_str = row.get("tags", "") or ""
    tags = [t.strip() for t in tags_str.split(",") if t.strip()] if tags_str else []

    set_idx = row.get("set_index", "")
    return {
        "id": row.get("id", ""),
        "title": row.get("title", "") or None,
        "content": row.get("content", ""),
        "direction": row.get("direction") or None,
        "exercise": row.get("exercise") or None,
        "set_index": int(set_idx) if set_idx else None,
        "session_id": row.get("session_id") or None,
        "source": row.get("source", "web"),
        "date": row.get("date", ""),
        "tags": tags,
        "created_at": row.get("_time"),
    }
