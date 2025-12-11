"""题目管理服务"""
import json
from typing import List, Optional, Dict
from pathlib import Path

from config import settings
from schemas.problem import (
    ProblemResponse, ProblemCreate, ProblemUpdate,
    ProblemQueryParams, ProblemStatsResponse
)


class ProblemService:
    """题目管理服务类"""

    def __init__(self):
        """初始化服务，加载题目数据"""
        self.problems: Dict[str, Dict] = {}
        self.tags: Dict[str, Dict] = {}
        self._load_data()

    def _load_data(self):
        """从JSON文件加载题目和标签数据"""
        # 加载题目
        try:
            with open(settings.problems_json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                problems_list = data.get('problems', [])
                self.problems = {p['id']: p for p in problems_list}
        except FileNotFoundError:
            print(f"警告: 题目文件未找到 {settings.problems_json_path}")
            self.problems = {}

        # 加载标签
        try:
            with open(settings.tags_json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                tags_list = data.get('tags', [])
                self.tags = {t['id']: t for t in tags_list}
        except FileNotFoundError:
            print(f"警告: 标签文件未找到 {settings.tags_json_path}")
            self.tags = {}

    def get_all_problems(
        self,
        skip: int = 0,
        limit: int = 100
    ) -> List[Dict]:
        """
        获取所有题目（分页）

        Args:
            skip: 跳过的数量
            limit: 返回的数量

        Returns:
            题目列表
        """
        problems_list = list(self.problems.values())
        return problems_list[skip:skip + limit]

    def get_problem_by_id(self, problem_id: str) -> Optional[Dict]:
        """
        根据ID获取题目

        Args:
            problem_id: 题目ID

        Returns:
            题目数据或None
        """
        return self.problems.get(problem_id)

    def search_problems(self, params: ProblemQueryParams) -> tuple[List[Dict], int]:
        """
        搜索题目

        Args:
            params: 查询参数

        Returns:
            (题目列表, 总数)
        """
        filtered_problems = list(self.problems.values())

        # 难度过滤
        if params.difficulty:
            filtered_problems = [
                p for p in filtered_problems
                if p['difficulty'] in params.difficulty
            ]

        # 标签过滤
        if params.tags:
            filtered_problems = [
                p for p in filtered_problems
                if any(tag in p.get('tags', []) for tag in params.tags)
            ]

        # 公司过滤
        if params.companies:
            filtered_problems = [
                p for p in filtered_problems
                if any(company in p.get('companies', []) for company in params.companies)
            ]

        # 搜索关键词
        if params.search:
            keyword = params.search.lower()
            filtered_problems = [
                p for p in filtered_problems
                if (keyword in p.get('title', '').lower() or
                    keyword in p.get('title_cn', '').lower())
            ]

        # 频率过滤
        if params.min_frequency is not None:
            filtered_problems = [
                p for p in filtered_problems
                if p.get('frequency', 0) >= params.min_frequency
            ]

        total = len(filtered_problems)

        # 分页
        start = params.offset
        end = start + params.limit
        filtered_problems = filtered_problems[start:end]

        return filtered_problems, total

    def get_problems_by_tags(self, tags: List[str]) -> List[Dict]:
        """
        根据标签获取题目

        Args:
            tags: 标签列表

        Returns:
            题目列表
        """
        return [
            p for p in self.problems.values()
            if any(tag in p.get('tags', []) for tag in tags)
        ]

    def get_problems_by_difficulty(self, difficulty: str) -> List[Dict]:
        """
        根据难度获取题目

        Args:
            difficulty: 难度 (easy, medium, hard)

        Returns:
            题目列表
        """
        return [
            p for p in self.problems.values()
            if p['difficulty'] == difficulty
        ]

    def get_statistics(self) -> ProblemStatsResponse:
        """
        获取题目统计信息

        Returns:
            统计信息
        """
        problems_list = list(self.problems.values())

        # 按难度统计
        by_difficulty = {'easy': 0, 'medium': 0, 'hard': 0}
        for p in problems_list:
            by_difficulty[p['difficulty']] += 1

        # 按标签统计
        by_tag: Dict[str, int] = {}
        for p in problems_list:
            for tag in p.get('tags', []):
                by_tag[tag] = by_tag.get(tag, 0) + 1

        # 按平台统计
        by_platform: Dict[str, int] = {}
        for p in problems_list:
            platform = p.get('platform', 'unknown')
            by_platform[platform] = by_platform.get(platform, 0) + 1

        # 平均时间
        times = [p.get('estimated_time', 0) for p in problems_list]
        avg_time = sum(times) / len(times) if times else 0

        return ProblemStatsResponse(
            total_problems=len(problems_list),
            by_difficulty=by_difficulty,
            by_tag=by_tag,
            by_platform=by_platform,
            avg_estimated_time=avg_time
        )

    def add_problem(self, problem_data: ProblemCreate) -> Dict:
        """
        添加新题目（保存到内存，实际应该保存到文件）

        Args:
            problem_data: 题目数据

        Returns:
            添加的题目
        """
        # 生成新ID
        max_id = max([int(pid) for pid in self.problems.keys() if pid.isdigit()] + [0])
        new_id = str(max_id + 1)

        problem_dict = problem_data.model_dump()
        problem_dict['id'] = new_id

        self.problems[new_id] = problem_dict

        # TODO: 保存到文件
        # self._save_to_file()

        return problem_dict

    def update_problem(
        self,
        problem_id: str,
        problem_data: ProblemUpdate
    ) -> Optional[Dict]:
        """
        更新题目

        Args:
            problem_id: 题目ID
            problem_data: 更新数据

        Returns:
            更新后的题目或None
        """
        if problem_id not in self.problems:
            return None

        # 更新非None的字段
        update_data = problem_data.model_dump(exclude_unset=True)
        self.problems[problem_id].update(update_data)

        # TODO: 保存到文件
        # self._save_to_file()

        return self.problems[problem_id]

    def delete_problem(self, problem_id: str) -> bool:
        """
        删除题目

        Args:
            problem_id: 题目ID

        Returns:
            是否成功删除
        """
        if problem_id in self.problems:
            del self.problems[problem_id]
            # TODO: 保存到文件
            # self._save_to_file()
            return True
        return False

    def get_tag_info(self, tag_id: str) -> Optional[Dict]:
        """
        获取标签信息

        Args:
            tag_id: 标签ID

        Returns:
            标签信息或None
        """
        return self.tags.get(tag_id)

    def get_all_tags(self) -> List[Dict]:
        """
        获取所有标签

        Returns:
            标签列表
        """
        return list(self.tags.values())


# 全局服务实例
_problem_service: Optional[ProblemService] = None


def get_problem_service() -> ProblemService:
    """获取题目服务单例"""
    global _problem_service
    if _problem_service is None:
        _problem_service = ProblemService()
    return _problem_service
