# -*- coding: utf-8 -*-
"""FastAPI 后端主程序（健身版训练感悟系统）"""
import os
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from typing import Optional
from pydantic import BaseModel

from app.repositories import ppl_reflection_repo as ref_repo
from app.repositories import training_queries as tq
from app.models.ppl_reflection import (
    PplReflectionCreate, PplReflectionUpdate
)
from app.services import reflection_markdown

app = FastAPI(title="训练感悟系统 API", version="0.1.0")

# CORS：允许前端开发服务器跨域访问
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5174", "http://127.0.0.1:5174"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ApiResponse(BaseModel):
    code: int = 0
    message: str = ""
    data: Optional[dict | list] = None


# ==================== 感悟接口 ====================

@app.get("/api/reflections", response_model=ApiResponse)
async def list_reflections(
    date: Optional[str] = Query(None),
    exercise: Optional[str] = Query(None),
    direction: Optional[str] = Query(None),
    set_index: Optional[int] = Query(None),
    tag: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    """感悟列表（筛选）"""
    try:
        data = ref_repo.list_ppl_reflections(
            direction=direction, exercise=exercise, date=date,
            set_index=set_index, tag=tag, limit=limit, offset=offset
        )
        return ApiResponse(code=0, data=data)
    except Exception as e:
        return ApiResponse(code=500, message=str(e))


@app.get("/api/reflections/stats", response_model=ApiResponse)
async def get_reflection_stats():
    """感悟统计（总数/今日/连续天数/覆盖动作数）"""
    try:
        data = ref_repo.get_ppl_reflection_stats()
        return ApiResponse(code=0, data=data)
    except Exception as e:
        return ApiResponse(code=500, message=str(e))


@app.post("/api/reflections", response_model=ApiResponse)
async def create_reflection(reflection: PplReflectionCreate):
    """新建感悟（自动同步当日 Markdown）"""
    try:
        data = ref_repo.create_ppl_reflection(
            content=reflection.content,
            date=reflection.date,
            direction=reflection.direction,
            exercise=reflection.exercise,
            set_index=reflection.set_index,
            session_id=reflection.session_id,
            source=reflection.source,
            title=reflection.title,
            tags=reflection.tags,
        )
        if data and reflection.date:
            # 补全字段后同步 Markdown（repo 返回仅 id/created_at）
            data.update({
                "date": reflection.date,
                "content": reflection.content,
                "direction": reflection.direction,
                "exercise": reflection.exercise,
                "set_index": reflection.set_index,
                "session_id": reflection.session_id,
                "source": reflection.source,
                "title": reflection.title,
                "tags": reflection.tags,
            })
            reflection_markdown.sync_reflection_to_markdown(data)
        return ApiResponse(code=0, data=data)
    except Exception as e:
        return ApiResponse(code=500, message=str(e))


@app.get("/api/reflections/{ref_id}", response_model=ApiResponse)
async def get_reflection(ref_id: str):
    """单条感悟"""
    try:
        data = ref_repo.get_ppl_reflection_by_id(ref_id)
        if not data:
            return JSONResponse(status_code=404, content={"code": 404, "message": "感悟不存在", "data": None})
        return ApiResponse(code=0, data=data)
    except Exception as e:
        return ApiResponse(code=500, message=str(e))


@app.put("/api/reflections/{ref_id}", response_model=ApiResponse)
async def update_reflection(ref_id: str, reflection: PplReflectionUpdate):
    """更新感悟（删除+重写保留 id；自动同步 Markdown）"""
    try:
        old = ref_repo.get_ppl_reflection_by_id(ref_id) or {}
        updates = reflection.dict(exclude_unset=True)
        data = ref_repo.update_ppl_reflection(ref_id, updates)
        # Markdown 同步：合并 old+updates 拿完整字段；旧日期移除，新日期写入
        merged = {**old, **updates}
        old_date = old.get("date", "")
        new_date = merged.get("date", "")
        if old_date and old_date != new_date:
            reflection_markdown.delete_reflection_from_markdown(old_date, ref_id)
        if new_date:
            merged["id"] = ref_id
            reflection_markdown.sync_reflection_to_markdown(merged)
        return ApiResponse(code=0, data=data)
    except Exception as e:
        return ApiResponse(code=500, message=str(e))


@app.delete("/api/reflections/{ref_id}", response_model=ApiResponse)
async def delete_reflection(ref_id: str):
    """删除感悟（自动同步 Markdown）"""
    try:
        old = ref_repo.get_ppl_reflection_by_id(ref_id)
        data = ref_repo.delete_ppl_reflection(ref_id)
        if old and old.get("date"):
            reflection_markdown.delete_reflection_from_markdown(old["date"], ref_id)
        return ApiResponse(code=0, data=data)
    except Exception as e:
        return ApiResponse(code=500, message=str(e))


@app.post("/api/reflections/markdown-sync", response_model=ApiResponse)
async def sync_reflection_markdown():
    """从库全量重写按日 Markdown（消息录入链路不经 CRUD，需此端点补同步）"""
    try:
        all_items = []
        offset = 0
        while True:
            page = ref_repo.list_ppl_reflections(limit=500, offset=offset)
            items = page.get("items", [])
            all_items.extend(items)
            if len(items) < 500:
                break
            offset += 500
        by_date: dict = {}
        for r in all_items:
            d = r.get("date", "")
            if d:
                by_date.setdefault(d, []).append(r)
        for date, items in by_date.items():
            reflection_markdown.write_date_reflections(date, items)
        md_dates = set(reflection_markdown.list_all_markdown_dates())
        lib_dates = set(by_date.keys())
        removed = 0
        for stale in md_dates - lib_dates:
            p = reflection_markdown.get_markdown_path(stale)
            if os.path.exists(p):
                os.remove(p)
                removed += 1
        return ApiResponse(code=0, data={
            "dates": len(by_date), "items": len(all_items), "stale_removed": removed
        })
    except Exception as e:
        return ApiResponse(code=500, message=str(e))


@app.get("/api/reflections/markdown/{date}", response_model=ApiResponse)
async def get_reflection_markdown(date: str):
    """读：返回指定日期的 Markdown 原文（按日 md 双向同步的读路径）"""
    try:
        path = reflection_markdown.get_markdown_path(date)
        if not os.path.exists(path):
            return ApiResponse(code=0, data={"date": date, "markdown": "", "count": 0})
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        parsed = reflection_markdown.parse_markdown_reflections(content)
        return ApiResponse(code=0, data={"date": date, "markdown": content, "count": len(parsed), "reflections": parsed})
    except Exception as e:
        return ApiResponse(code=500, message=str(e))


# ==================== 训练历史接口 ====================

@app.get("/api/training/exercise/{exercise}", response_model=ApiResponse)
async def get_exercise_history(
    exercise: str,
    days: int = Query(365, ge=1, le=3650),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
):
    """某动作历史训练（按 session 分组，时间倒序；可选 start_date/end_date 圈定窗口）"""
    try:
        data = tq.get_exercise_history(exercise, days, start_date, end_date)
        return ApiResponse(code=0, data=data)
    except Exception as e:
        return ApiResponse(code=500, message=str(e))


# ==================== PR 接口 ====================

@app.get("/api/pr/tests", response_model=ApiResponse)
async def get_pr_tests(
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
):
    """全部动作 PR 测试（按动作分组，测试编号；可选 start_date/end_date 圈定窗口）"""
    try:
        data = tq.get_pr_tests(start_date, end_date)
        return ApiResponse(code=0, data=data)
    except Exception as e:
        return ApiResponse(code=500, message=str(e))


# ==================== 训练日历接口 ====================

@app.get("/api/training/calendar", response_model=ApiResponse)
async def get_training_calendar(days: int = Query(365, ge=1, le=3650)):
    """训练日历：有训练的日期 + 有 PR 测试的日期（日历打点数据源）"""
    try:
        data = tq.get_training_calendar(days)
        return ApiResponse(code=0, data=data)
    except Exception as e:
        return ApiResponse(code=500, message=str(e))


# ==================== 按日全貌接口 ====================

@app.get("/api/day/{date}", response_model=ApiResponse)
async def get_day_all(date: str):
    """某天全貌（训练组行 + 日级感悟 + 晨脉 + 意象）"""
    try:
        data = tq.get_day_all(date)
        return ApiResponse(code=0, data=data)
    except Exception as e:
        return ApiResponse(code=500, message=str(e))


# ==================== 健康检查 ====================

@app.get("/api/health")
async def health_check():
    return {"status": "ok"}


# ==================== 生产模式：前端静态文件服务 ====================

frontend_dist = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    "frontend", "dist"
)

if os.path.exists(frontend_dist):
    assets_dir = os.path.join(frontend_dist, "assets")
    if os.path.exists(assets_dir):
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    @app.get("/{full_path:path}")
    async def serve_frontend(full_path: str):
        if full_path.startswith("api/"):
            return {"detail": "Not Found"}
        index_path = os.path.join(frontend_dist, "index.html")
        if os.path.exists(index_path):
            return FileResponse(index_path)
        return {"detail": "Frontend not built"}
