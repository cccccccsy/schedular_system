"""
动态规划 - 顺序优化器

优化题目刷题顺序，目标：
1. 尊重题目依赖关系（前置题目先做）
2. 同类题目聚合（减少上下文切换）
3. 难度渐进（easy → medium → hard）

算法：拓扑排序 + 启发式搜索 + 聚类分析
"""
from typing import List, Dict, Set, Optional, Tuple
from dataclasses import dataclass
from collections import defaultdict, deque
import math


@dataclass
class Problem:
    """题目数据"""
    id: str
    title: str
    difficulty: str
    tags: List[str]
    priority: float
    prerequisites: List[str]  # 前置题目ID列表
    follow_ups: List[str]  # 后续题目ID列表


@dataclass
class OptimizedSequence:
    """优化后的序列"""
    problems: List[Problem]
    optimization_score: float  # 优化得分
    dependency_layers: List[List[str]]  # 依赖层级
    tag_clusters: Dict[str, List[str]]  # 标签聚类
    difficulty_progression: List[float]  # 难度进度曲线
    metadata: Dict


class SequenceOptimizer:
    """顺序优化器"""

    # 难度数值映射
    DIFFICULTY_VALUES = {
        "easy": 1.0,
        "medium": 2.0,
        "hard": 3.0
    }

    def __init__(
        self,
        tag_switch_penalty: float = 0.2,
        difficulty_jump_penalty: float = 0.3
    ):
        """
        初始化顺序优化器

        Args:
            tag_switch_penalty: 标签切换惩罚（0-1）
            difficulty_jump_penalty: 难度跳跃惩罚（0-1）
        """
        self.tag_switch_penalty = tag_switch_penalty
        self.difficulty_jump_penalty = difficulty_jump_penalty

    def optimize_order(
        self,
        problems: List[Problem],
        preferred_tags: Optional[List[str]] = None
    ) -> OptimizedSequence:
        """
        优化题目顺序

        步骤：
        1. 构建依赖图
        2. 拓扑排序（DAG）
        3. 同层内按标签聚类
        4. 同簇内按难度排序

        Args:
            problems: 题目列表
            preferred_tags: 优先标签（这些标签的题目优先排列）

        Returns:
            优化后的序列
        """
        if not problems:
            return OptimizedSequence(
                problems=[],
                optimization_score=0.0,
                dependency_layers=[],
                tag_clusters={},
                difficulty_progression=[],
                metadata={}
            )

        # Step 1: 构建依赖图和入度表
        dependency_graph, in_degree = self._build_dependency_graph(problems)

        # Step 2: 拓扑排序，得到依赖层级
        dependency_layers = self._topological_sort_with_layers(
            problems,
            dependency_graph,
            in_degree
        )

        # Step 3: 在每一层内按标签聚类
        optimized_problems = []
        tag_clusters = {}

        for layer_idx, layer_problem_ids in enumerate(dependency_layers):
            layer_problems = [p for p in problems if p.id in layer_problem_ids]

            # 按标签聚类
            clustered = self._cluster_by_tags(layer_problems, preferred_tags)

            # 每个簇内按难度排序
            for cluster_tag, cluster_problems in clustered.items():
                sorted_cluster = self._sort_by_difficulty_progressive(cluster_problems)
                optimized_problems.extend(sorted_cluster)

                # 记录聚类
                if cluster_tag not in tag_clusters:
                    tag_clusters[cluster_tag] = []
                tag_clusters[cluster_tag].extend([p.id for p in sorted_cluster])

        # Step 4: 计算难度进度曲线
        difficulty_progression = [
            self.DIFFICULTY_VALUES[p.difficulty]
            for p in optimized_problems
        ]

        # Step 5: 计算优化得分
        optimization_score = self._calculate_optimization_score(
            optimized_problems,
            dependency_layers
        )

        return OptimizedSequence(
            problems=optimized_problems,
            optimization_score=optimization_score,
            dependency_layers=dependency_layers,
            tag_clusters=tag_clusters,
            difficulty_progression=difficulty_progression,
            metadata={
                "algorithm": "topological_sort_with_clustering",
                "total_problems": len(optimized_problems),
                "total_layers": len(dependency_layers),
                "avg_layer_size": sum(len(layer) for layer in dependency_layers) / len(dependency_layers)
                    if dependency_layers else 0
            }
        )

    def _build_dependency_graph(
        self,
        problems: List[Problem]
    ) -> Tuple[Dict[str, List[str]], Dict[str, int]]:
        """
        构建依赖图和入度表

        Returns:
            (邻接表, 入度表)
        """
        graph = defaultdict(list)  # graph[A] = [B, C] 表示 A 是 B 和 C 的前置
        in_degree = defaultdict(int)  # in_degree[B] 表示 B 的前置题目数量

        # 初始化所有节点的入度为0
        for problem in problems:
            if problem.id not in in_degree:
                in_degree[problem.id] = 0

        # 构建图
        for problem in problems:
            if problem.prerequisites:
                for prereq_id in problem.prerequisites:
                    # prereq_id -> problem.id
                    graph[prereq_id].append(problem.id)
                    in_degree[problem.id] += 1

        return dict(graph), dict(in_degree)

    def _topological_sort_with_layers(
        self,
        problems: List[Problem],
        graph: Dict[str, List[str]],
        in_degree: Dict[str, int]
    ) -> List[List[str]]:
        """
        拓扑排序并生成层级结构

        使用 BFS 的 Kahn 算法，同时记录每个节点所在的层级

        Args:
            problems: 题目列表
            graph: 依赖图
            in_degree: 入度表

        Returns:
            依赖层级列表 [[layer0_ids], [layer1_ids], ...]
        """
        # 找到所有入度为0的节点（起始节点）
        queue = deque([p.id for p in problems if in_degree.get(p.id, 0) == 0])

        layers = []
        in_degree_copy = in_degree.copy()

        while queue:
            # 当前层的所有节点
            current_layer = []
            layer_size = len(queue)

            for _ in range(layer_size):
                node_id = queue.popleft()
                current_layer.append(node_id)

                # 处理该节点的所有后继节点
                for neighbor in graph.get(node_id, []):
                    in_degree_copy[neighbor] -= 1
                    if in_degree_copy[neighbor] == 0:
                        queue.append(neighbor)

            layers.append(current_layer)

        return layers

    def _cluster_by_tags(
        self,
        problems: List[Problem],
        preferred_tags: Optional[List[str]] = None
    ) -> Dict[str, List[Problem]]:
        """
        按标签聚类题目

        策略：
        - 优先聚类 preferred_tags 中的标签
        - 其他题目按主标签（第一个标签）聚类
        - 无标签的题目归为 "uncategorized"

        Args:
            problems: 题目列表
            preferred_tags: 优先标签

        Returns:
            标签聚类字典 {tag: [problems]}
        """
        clusters = defaultdict(list)
        preferred_set = set(preferred_tags) if preferred_tags else set()

        for problem in problems:
            if not problem.tags:
                clusters["uncategorized"].append(problem)
                continue

            # 找到第一个匹配的优先标签
            matched_tag = None
            for tag in problem.tags:
                if tag in preferred_set:
                    matched_tag = tag
                    break

            # 如果没有匹配优先标签，使用第一个标签
            if not matched_tag:
                matched_tag = problem.tags[0]

            clusters[matched_tag].append(problem)

        # 按优先标签顺序排列聚类
        if preferred_tags:
            ordered_clusters = {}
            for tag in preferred_tags:
                if tag in clusters:
                    ordered_clusters[tag] = clusters[tag]
            # 添加其他聚类
            for tag, probs in clusters.items():
                if tag not in ordered_clusters:
                    ordered_clusters[tag] = probs
            return ordered_clusters

        return dict(clusters)

    def _sort_by_difficulty_progressive(
        self,
        problems: List[Problem]
    ) -> List[Problem]:
        """
        按难度渐进排序

        策略：easy → medium → hard，但同时考虑优先级

        Args:
            problems: 题目列表

        Returns:
            排序后的题目列表
        """
        # 先按难度分组
        by_difficulty = {
            "easy": [],
            "medium": [],
            "hard": []
        }

        for problem in problems:
            by_difficulty[problem.difficulty].append(problem)

        # 每个难度组内按优先级排序
        for difficulty in by_difficulty:
            by_difficulty[difficulty].sort(key=lambda p: p.priority, reverse=True)

        # 组合：easy -> medium -> hard
        result = []
        result.extend(by_difficulty["easy"])
        result.extend(by_difficulty["medium"])
        result.extend(by_difficulty["hard"])

        return result

    def _calculate_optimization_score(
        self,
        problems: List[Problem],
        dependency_layers: List[List[str]]
    ) -> float:
        """
        计算优化得分

        评估标准：
        1. 依赖关系满足度（必须100%）
        2. 标签切换频率（越低越好）
        3. 难度平滑度（越平滑越好）

        Returns:
            优化得分 (0-1)
        """
        if not problems or len(problems) < 2:
            return 1.0

        # 1. 依赖关系满足度（必须满足，这里假设拓扑排序已经保证）
        dependency_score = 1.0

        # 2. 标签切换频率
        tag_switches = 0
        for i in range(1, len(problems)):
            prev_tags = set(problems[i-1].tags)
            curr_tags = set(problems[i].tags)
            if not (prev_tags & curr_tags):  # 无交集，表示完全切换
                tag_switches += 1

        tag_switch_rate = tag_switches / (len(problems) - 1)
        tag_score = 1.0 - tag_switch_rate * self.tag_switch_penalty

        # 3. 难度平滑度
        difficulty_jumps = 0
        for i in range(1, len(problems)):
            prev_diff = self.DIFFICULTY_VALUES[problems[i-1].difficulty]
            curr_diff = self.DIFFICULTY_VALUES[problems[i].difficulty]
            jump = abs(curr_diff - prev_diff)
            if jump > 1.0:  # 跳跃超过1个级别
                difficulty_jumps += 1

        difficulty_jump_rate = difficulty_jumps / (len(problems) - 1)
        difficulty_score = 1.0 - difficulty_jump_rate * self.difficulty_jump_penalty

        # 综合得分
        optimization_score = (
            0.5 * dependency_score +
            0.3 * tag_score +
            0.2 * difficulty_score
        )

        return optimization_score

    def optimize_with_constraints(
        self,
        problems: List[Problem],
        max_consecutive_same_tag: int = 5,
        max_difficulty_variance_per_segment: float = 1.0,
        preferred_tags: Optional[List[str]] = None
    ) -> OptimizedSequence:
        """
        带约束的顺序优化

        额外约束：
        - 同一标签连续出现不超过 max_consecutive_same_tag 次
        - 每个片段（5题）的难度方差不超过阈值

        Args:
            problems: 题目列表
            max_consecutive_same_tag: 同标签最大连续次数
            max_difficulty_variance_per_segment: 片段难度方差阈值
            preferred_tags: 优先标签

        Returns:
            优化后的序列
        """
        # 首先进行基础优化
        base_sequence = self.optimize_order(problems, preferred_tags)

        # TODO: 在此基础上应用额外约束（留作扩展）
        # 这里简化实现，直接返回基础序列

        return base_sequence


def create_problem_from_dict(problem_dict: Dict) -> Problem:
    """
    从字典创建 Problem 对象

    Args:
        problem_dict: 题目字典

    Returns:
        Problem 对象
    """
    metadata = problem_dict.get("metadata", {})

    return Problem(
        id=problem_dict["id"],
        title=problem_dict.get("title", ""),
        difficulty=problem_dict["difficulty"],
        tags=problem_dict.get("tags", []),
        priority=problem_dict.get("priority", 0.5),
        prerequisites=metadata.get("prerequisites", []),
        follow_ups=metadata.get("follow_ups", [])
    )


# 便捷函数
def optimize_problem_sequence(
    problems: List[Dict],
    preferred_tags: Optional[List[str]] = None
) -> OptimizedSequence:
    """
    优化题目顺序的便捷函数

    Args:
        problems: 题目字典列表
        preferred_tags: 优先标签

    Returns:
        优化后的序列
    """
    # 转换为 Problem 对象
    problem_objects = [create_problem_from_dict(p) for p in problems]

    # 优化
    optimizer = SequenceOptimizer()
    return optimizer.optimize_order(problem_objects, preferred_tags)
