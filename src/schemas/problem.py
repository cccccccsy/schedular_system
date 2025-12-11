"""题目相关的 Pydantic Schemas"""
from typing import List, Optional, Dict
from pydantic import BaseModel, Field


class ProblemMetadata(BaseModel):
    """题目元数据"""
    time_complexity: Optional[str] = None
    space_complexity: Optional[str] = None
    patterns: List[str] = []
    prerequisites: List[str] = []
    follow_ups: List[str] = []


class ProblemBase(BaseModel):
    """题目基础模型"""
    platform: str = Field(..., description="平台名称，如 leetcode")
    number: int = Field(..., description="题目编号")
    title: str = Field(..., description="题目标题")
    title_cn: Optional[str] = Field(None, description="中文标题")
    difficulty: str = Field(..., description="难度: easy, medium, hard")
    tags: List[str] = Field(default=[], description="题目标签")
    estimated_time: int = Field(..., description="预估完成时间（分钟）")
    acceptance_rate: Optional[float] = Field(None, ge=0, le=1, description="通过率")
    frequency: Optional[float] = Field(None, ge=0, le=1, description="出题频率")
    companies: List[str] = Field(default=[], description="相关公司")
    url: Optional[str] = Field(None, description="题目链接")
    metadata: Optional[ProblemMetadata] = None


class ProblemCreate(ProblemBase):
    """创建题目的请求模型"""
    pass


class ProblemUpdate(BaseModel):
    """更新题目的请求模型"""
    title: Optional[str] = None
    title_cn: Optional[str] = None
    difficulty: Optional[str] = None
    tags: Optional[List[str]] = None
    estimated_time: Optional[int] = None
    acceptance_rate: Optional[float] = None
    frequency: Optional[float] = None
    companies: Optional[List[str]] = None
    url: Optional[str] = None
    metadata: Optional[ProblemMetadata] = None


class ProblemResponse(ProblemBase):
    """题目响应模型"""
    id: str = Field(..., description="题目唯一标识")
    priority: Optional[float] = Field(None, description="优先级分数（由算法计算）")

    class Config:
        from_attributes = True


class ProblemListResponse(BaseModel):
    """题目列表响应"""
    problems: List[ProblemResponse]
    total: int
    page: int = 1
    page_size: int = 20


class ProblemQueryParams(BaseModel):
    """题目查询参数"""
    difficulty: Optional[List[str]] = Field(None, description="难度过滤")
    tags: Optional[List[str]] = Field(None, description="标签过滤")
    companies: Optional[List[str]] = Field(None, description="公司过滤")
    search: Optional[str] = Field(None, description="搜索关键词")
    min_frequency: Optional[float] = Field(None, ge=0, le=1, description="最小频率")
    limit: int = Field(20, ge=1, le=100, description="返回数量")
    offset: int = Field(0, ge=0, description="偏移量")


class ProblemStatsResponse(BaseModel):
    """题目统计响应"""
    total_problems: int
    by_difficulty: Dict[str, int]
    by_tag: Dict[str, int]
    by_platform: Dict[str, int]
    avg_estimated_time: float
