# -*- coding: utf-8 -*-
"""训练感悟数据模型（健身版，三级粒度）"""
from pydantic import BaseModel, Field
from typing import Optional, List


class PplReflectionBase(BaseModel):
    """感悟基础模型"""
    content: str = Field(..., description="感悟正文")
    title: Optional[str] = Field(None, description="可选标题")
    tags: List[str] = Field(default_factory=list, description="自由标签")
    direction: Optional[str] = Field(None, description="方向: push/pull/squat/other")
    exercise: Optional[str] = Field(None, description="动作中文名（组级/动作级）")
    set_index: Optional[int] = Field(None, description="组号（仅组级）")
    session_id: Optional[str] = Field(None, description="同消息训练 session")
    source: str = Field(default="web", description="录入通道")


class PplReflectionCreate(PplReflectionBase):
    """创建感悟请求模型"""
    date: str = Field(..., description="日期 YYYY-MM-DD")


class PplReflectionUpdate(BaseModel):
    """更新感悟请求模型（只传需要更新的字段）"""
    content: Optional[str] = None
    title: Optional[str] = None
    tags: Optional[List[str]] = None
    direction: Optional[str] = None
    exercise: Optional[str] = None
    set_index: Optional[int] = None
    date: Optional[str] = None


class PplReflectionStats(BaseModel):
    """感悟统计数据模型"""
    total_count: int = 0
    today_count: int = 0
    consecutive_days: int = 0
    exercise_count: int = 0
