"""
推荐系统 - 历史数据分析器

分析用户的刷题历史，提取有价值的洞察：
1. 学习曲线分析（进步趋势）
2. 薄弱领域识别
3. 最佳学习时间段
4. 题目类型偏好

这些洞察用于个性化推荐和计划调整。
"""
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field
from collections import defaultdict
from datetime import datetime, timedelta
import math
import statistics


@dataclass
class AttemptRecord:
    """尝试记录"""
    problem_id: str
    difficulty: str
    tags: List[str]
    success: bool
    time_spent: int  # 分钟
    attempts: int  # 尝试次数
    timestamp: datetime
    hints_used: int = 0


@dataclass
class LearningCurve:
    """学习曲线"""
    time_points: List[datetime]  # 时间点
    success_rates: List[float]  # 各时间点的成功率
    avg_times: List[float]  # 各时间点的平均用时
    trend: str  # "improving", "stable", "declining"
    improvement_rate: float  # 进步率 (-1 to 1)


@dataclass
class WeakAreaAnalysis:
    """薄弱领域分析"""
    weak_tags: List[Tuple[str, float]]  # [(标签, 薄弱程度), ...]
    weak_difficulties: List[Tuple[str, float]]  # [(难度, 薄弱程度), ...]
    recommended_focus: List[str]  # 建议重点关注的领域
    improvement_suggestions: List[str]  # 改进建议


@dataclass
class StudyPatternAnalysis:
    """学习模式分析"""
    best_hours: List[int]  # 最佳学习时段（小时）
    best_days: List[str]  # 最佳学习日
    avg_session_duration: float  # 平均学习时长
    consistency_score: float  # 学习一致性分数
    streak_stats: Dict  # 连续学习统计


@dataclass
class HistoryAnalysisResult:
    """历史分析结果"""
    total_problems: int
    total_time: int  # 总学习时间（分钟）
    success_rate: float  # 总体成功率
    learning_curve: LearningCurve
    weak_areas: WeakAreaAnalysis
    study_patterns: StudyPatternAnalysis
    tag_proficiency: Dict[str, float]  # 各标签熟练度
    difficulty_stats: Dict[str, Dict]  # 各难度统计
    recommendations: List[str]  # 综合建议


class HistoryAnalyzer:
    """历史数据分析器"""

    # 难度数值映射
    DIFFICULTY_VALUES = {
        "easy": 1.0,
        "medium": 2.0,
        "hard": 3.0
    }

    def __init__(
        self,
        min_samples_for_analysis: int = 5,
        window_size_days: int = 7
    ):
        """
        初始化历史分析器

        Args:
            min_samples_for_analysis: 进行分析所需的最小样本数
            window_size_days: 时间窗口大小（天）
        """
        self.min_samples_for_analysis = min_samples_for_analysis
        self.window_size_days = window_size_days

    def analyze(
        self,
        records: List[AttemptRecord]
    ) -> HistoryAnalysisResult:
        """
        分析用户历史数据

        Args:
            records: 尝试记录列表

        Returns:
            历史分析结果
        """
        if not records:
            return self._empty_result()

        # 按时间排序
        sorted_records = sorted(records, key=lambda x: x.timestamp)

        # 基础统计
        total_problems = len(set(r.problem_id for r in records))
        total_time = sum(r.time_spent for r in records)
        success_count = sum(1 for r in records if r.success)
        success_rate = success_count / len(records)

        # 分析学习曲线
        learning_curve = self._analyze_learning_curve(sorted_records)

        # 分析薄弱领域
        weak_areas = self._analyze_weak_areas(records)

        # 分析学习模式
        study_patterns = self._analyze_study_patterns(sorted_records)

        # 计算标签熟练度
        tag_proficiency = self._calculate_tag_proficiency(records)

        # 计算难度统计
        difficulty_stats = self._calculate_difficulty_stats(records)

        # 生成综合建议
        recommendations = self._generate_recommendations(
            learning_curve,
            weak_areas,
            study_patterns,
            difficulty_stats
        )

        return HistoryAnalysisResult(
            total_problems=total_problems,
            total_time=total_time,
            success_rate=success_rate,
            learning_curve=learning_curve,
            weak_areas=weak_areas,
            study_patterns=study_patterns,
            tag_proficiency=tag_proficiency,
            difficulty_stats=difficulty_stats,
            recommendations=recommendations
        )

    def _empty_result(self) -> HistoryAnalysisResult:
        """返回空结果"""
        return HistoryAnalysisResult(
            total_problems=0,
            total_time=0,
            success_rate=0.0,
            learning_curve=LearningCurve(
                time_points=[],
                success_rates=[],
                avg_times=[],
                trend="stable",
                improvement_rate=0.0
            ),
            weak_areas=WeakAreaAnalysis(
                weak_tags=[],
                weak_difficulties=[],
                recommended_focus=[],
                improvement_suggestions=["开始刷题以获取分析数据"]
            ),
            study_patterns=StudyPatternAnalysis(
                best_hours=[],
                best_days=[],
                avg_session_duration=0.0,
                consistency_score=0.0,
                streak_stats={}
            ),
            tag_proficiency={},
            difficulty_stats={},
            recommendations=["开始刷题以获取个性化建议"]
        )

    def _analyze_learning_curve(
        self,
        records: List[AttemptRecord]
    ) -> LearningCurve:
        """
        分析学习曲线

        策略：将记录分成时间窗口，计算每个窗口的成功率和平均用时

        Args:
            records: 按时间排序的记录

        Returns:
            学习曲线
        """
        if len(records) < self.min_samples_for_analysis:
            return LearningCurve(
                time_points=[],
                success_rates=[],
                avg_times=[],
                trend="stable",
                improvement_rate=0.0
            )

        # 按时间窗口分组
        windows = self._group_by_time_window(records)

        time_points = []
        success_rates = []
        avg_times = []

        for window_start, window_records in windows:
            time_points.append(window_start)

            # 计算窗口内的成功率
            window_success = sum(1 for r in window_records if r.success)
            success_rate = window_success / len(window_records)
            success_rates.append(success_rate)

            # 计算窗口内的平均用时
            avg_time = statistics.mean(r.time_spent for r in window_records)
            avg_times.append(avg_time)

        # 计算趋势
        trend, improvement_rate = self._calculate_trend(success_rates)

        return LearningCurve(
            time_points=time_points,
            success_rates=success_rates,
            avg_times=avg_times,
            trend=trend,
            improvement_rate=improvement_rate
        )

    def _group_by_time_window(
        self,
        records: List[AttemptRecord]
    ) -> List[Tuple[datetime, List[AttemptRecord]]]:
        """
        按时间窗口分组记录

        Args:
            records: 按时间排序的记录

        Returns:
            [(窗口开始时间, 记录列表), ...]
        """
        if not records:
            return []

        windows = []
        window_start = records[0].timestamp
        current_window = []

        for record in records:
            # 检查是否在当前窗口内
            if (record.timestamp - window_start).days < self.window_size_days:
                current_window.append(record)
            else:
                # 保存当前窗口，开始新窗口
                if current_window:
                    windows.append((window_start, current_window))
                window_start = record.timestamp
                current_window = [record]

        # 添加最后一个窗口
        if current_window:
            windows.append((window_start, current_window))

        return windows

    def _calculate_trend(
        self,
        values: List[float]
    ) -> Tuple[str, float]:
        """
        计算趋势

        使用简单线性回归

        Args:
            values: 数值序列

        Returns:
            (趋势描述, 改进率)
        """
        if len(values) < 2:
            return "stable", 0.0

        n = len(values)
        x_mean = (n - 1) / 2
        y_mean = statistics.mean(values)

        # 计算斜率
        numerator = sum((i - x_mean) * (v - y_mean) for i, v in enumerate(values))
        denominator = sum((i - x_mean) ** 2 for i in range(n))

        if denominator == 0:
            return "stable", 0.0

        slope = numerator / denominator

        # 归一化改进率
        improvement_rate = slope / max(y_mean, 0.01)
        improvement_rate = max(-1, min(1, improvement_rate))

        # 判断趋势
        if improvement_rate > 0.1:
            trend = "improving"
        elif improvement_rate < -0.1:
            trend = "declining"
        else:
            trend = "stable"

        return trend, improvement_rate

    def _analyze_weak_areas(
        self,
        records: List[AttemptRecord]
    ) -> WeakAreaAnalysis:
        """
        分析薄弱领域

        策略：
        - 成功率低的标签和难度
        - 平均用时长的标签和难度
        - 尝试次数多的标签和难度

        Args:
            records: 尝试记录

        Returns:
            薄弱领域分析
        """
        # 按标签统计
        tag_stats = defaultdict(lambda: {"attempts": 0, "success": 0, "time": 0})
        for record in records:
            for tag in record.tags:
                tag_stats[tag]["attempts"] += 1
                tag_stats[tag]["success"] += 1 if record.success else 0
                tag_stats[tag]["time"] += record.time_spent

        # 计算标签薄弱程度
        weak_tags = []
        for tag, stats in tag_stats.items():
            if stats["attempts"] >= self.min_samples_for_analysis:
                success_rate = stats["success"] / stats["attempts"]
                avg_time = stats["time"] / stats["attempts"]

                # 薄弱程度 = (1 - 成功率) + 时间因子
                weakness = (1 - success_rate) * 0.7 + (avg_time / 60) * 0.3
                weak_tags.append((tag, weakness))

        weak_tags.sort(key=lambda x: x[1], reverse=True)

        # 按难度统计
        difficulty_stats = defaultdict(lambda: {"attempts": 0, "success": 0, "time": 0})
        for record in records:
            difficulty_stats[record.difficulty]["attempts"] += 1
            difficulty_stats[record.difficulty]["success"] += 1 if record.success else 0
            difficulty_stats[record.difficulty]["time"] += record.time_spent

        # 计算难度薄弱程度
        weak_difficulties = []
        for difficulty, stats in difficulty_stats.items():
            if stats["attempts"] >= self.min_samples_for_analysis:
                success_rate = stats["success"] / stats["attempts"]
                weakness = 1 - success_rate
                weak_difficulties.append((difficulty, weakness))

        weak_difficulties.sort(key=lambda x: x[1], reverse=True)

        # 建议重点关注的领域
        recommended_focus = [tag for tag, _ in weak_tags[:3]]

        # 改进建议
        improvement_suggestions = self._generate_improvement_suggestions(
            weak_tags,
            weak_difficulties
        )

        return WeakAreaAnalysis(
            weak_tags=weak_tags[:10],
            weak_difficulties=weak_difficulties,
            recommended_focus=recommended_focus,
            improvement_suggestions=improvement_suggestions
        )

    def _generate_improvement_suggestions(
        self,
        weak_tags: List[Tuple[str, float]],
        weak_difficulties: List[Tuple[str, float]]
    ) -> List[str]:
        """
        生成改进建议

        Args:
            weak_tags: 薄弱标签
            weak_difficulties: 薄弱难度

        Returns:
            建议列表
        """
        suggestions = []

        # 标签建议
        if weak_tags:
            top_weak_tag = weak_tags[0][0]
            suggestions.append(f"建议重点练习 {top_weak_tag} 类型的题目")

        # 难度建议
        if weak_difficulties:
            for difficulty, weakness in weak_difficulties:
                if weakness > 0.5:  # 成功率低于50%
                    if difficulty == "hard":
                        suggestions.append("Hard 题目成功率较低，建议先巩固 Medium 难度")
                    elif difficulty == "medium":
                        suggestions.append("Medium 题目需要加强，可以多练习同类型的 Easy 题目热身")

        # 通用建议
        if not suggestions:
            suggestions.append("保持当前学习节奏，逐步提升难度")

        return suggestions

    def _analyze_study_patterns(
        self,
        records: List[AttemptRecord]
    ) -> StudyPatternAnalysis:
        """
        分析学习模式

        包括最佳时间段、学习一致性等

        Args:
            records: 按时间排序的记录

        Returns:
            学习模式分析
        """
        if not records:
            return StudyPatternAnalysis(
                best_hours=[],
                best_days=[],
                avg_session_duration=0.0,
                consistency_score=0.0,
                streak_stats={}
            )

        # 按小时统计成功率
        hour_stats = defaultdict(lambda: {"attempts": 0, "success": 0})
        for record in records:
            hour = record.timestamp.hour
            hour_stats[hour]["attempts"] += 1
            hour_stats[hour]["success"] += 1 if record.success else 0

        # 找出最佳时段
        best_hours = []
        for hour, stats in hour_stats.items():
            if stats["attempts"] >= 3:
                success_rate = stats["success"] / stats["attempts"]
                if success_rate >= 0.6:
                    best_hours.append((hour, success_rate))

        best_hours.sort(key=lambda x: x[1], reverse=True)
        best_hours = [h for h, _ in best_hours[:5]]

        # 按星期统计
        day_names = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
        day_stats = defaultdict(lambda: {"attempts": 0, "success": 0})
        for record in records:
            day = record.timestamp.weekday()
            day_stats[day]["attempts"] += 1
            day_stats[day]["success"] += 1 if record.success else 0

        best_days = []
        for day, stats in day_stats.items():
            if stats["attempts"] >= 3:
                success_rate = stats["success"] / stats["attempts"]
                if success_rate >= 0.6:
                    best_days.append((day_names[day], success_rate))

        best_days.sort(key=lambda x: x[1], reverse=True)
        best_days = [d for d, _ in best_days[:3]]

        # 计算平均学习时长
        avg_session_duration = statistics.mean(r.time_spent for r in records)

        # 计算学习一致性
        consistency_score = self._calculate_consistency(records)

        # 连续学习统计
        streak_stats = self._calculate_streak_stats(records)

        return StudyPatternAnalysis(
            best_hours=best_hours,
            best_days=best_days,
            avg_session_duration=avg_session_duration,
            consistency_score=consistency_score,
            streak_stats=streak_stats
        )

    def _calculate_consistency(
        self,
        records: List[AttemptRecord]
    ) -> float:
        """
        计算学习一致性

        基于学习日期的分布均匀程度

        Returns:
            一致性分数 (0-1)
        """
        if len(records) < 2:
            return 0.0

        # 获取所有学习日期
        study_dates = set(r.timestamp.date() for r in records)

        if len(study_dates) < 2:
            return 0.0

        # 计算日期间隔
        sorted_dates = sorted(study_dates)
        gaps = []
        for i in range(1, len(sorted_dates)):
            gap = (sorted_dates[i] - sorted_dates[i - 1]).days
            gaps.append(gap)

        if not gaps:
            return 0.0

        # 间隔越均匀，一致性越高
        avg_gap = statistics.mean(gaps)
        if avg_gap == 0:
            return 1.0

        # 使用变异系数的倒数作为一致性分数
        std_gap = statistics.stdev(gaps) if len(gaps) > 1 else 0
        cv = std_gap / avg_gap if avg_gap > 0 else 0

        # 转换为 0-1 分数
        consistency = 1 / (1 + cv)

        return min(1.0, consistency)

    def _calculate_streak_stats(
        self,
        records: List[AttemptRecord]
    ) -> Dict:
        """
        计算连续学习统计

        Returns:
            连续学习统计信息
        """
        if not records:
            return {"current_streak": 0, "max_streak": 0, "total_active_days": 0}

        # 获取所有学习日期
        study_dates = sorted(set(r.timestamp.date() for r in records))

        if not study_dates:
            return {"current_streak": 0, "max_streak": 0, "total_active_days": 0}

        # 计算连续天数
        max_streak = 1
        current_streak = 1

        for i in range(1, len(study_dates)):
            if (study_dates[i] - study_dates[i - 1]).days == 1:
                current_streak += 1
                max_streak = max(max_streak, current_streak)
            else:
                current_streak = 1

        # 检查当前连续天数是否延续到今天
        today = datetime.now().date()
        if study_dates[-1] != today and (today - study_dates[-1]).days > 1:
            current_streak = 0

        return {
            "current_streak": current_streak,
            "max_streak": max_streak,
            "total_active_days": len(study_dates)
        }

    def _calculate_tag_proficiency(
        self,
        records: List[AttemptRecord]
    ) -> Dict[str, float]:
        """
        计算各标签熟练度

        Args:
            records: 尝试记录

        Returns:
            {标签: 熟练度} 字典
        """
        tag_stats = defaultdict(lambda: {"attempts": 0, "success": 0, "total_time": 0})

        for record in records:
            for tag in record.tags:
                tag_stats[tag]["attempts"] += 1
                tag_stats[tag]["success"] += 1 if record.success else 0
                tag_stats[tag]["total_time"] += record.time_spent

        proficiency = {}
        for tag, stats in tag_stats.items():
            if stats["attempts"] >= self.min_samples_for_analysis:
                success_rate = stats["success"] / stats["attempts"]
                avg_time = stats["total_time"] / stats["attempts"]

                # 熟练度 = 成功率 * 时间效率因子
                time_factor = 1 / (1 + avg_time / 30)  # 30分钟为基准
                proficiency[tag] = success_rate * 0.7 + time_factor * 0.3

        return proficiency

    def _calculate_difficulty_stats(
        self,
        records: List[AttemptRecord]
    ) -> Dict[str, Dict]:
        """
        计算各难度统计

        Args:
            records: 尝试记录

        Returns:
            各难度的统计信息
        """
        stats = {
            "easy": {"attempts": 0, "success": 0, "total_time": 0, "avg_attempts": []},
            "medium": {"attempts": 0, "success": 0, "total_time": 0, "avg_attempts": []},
            "hard": {"attempts": 0, "success": 0, "total_time": 0, "avg_attempts": []}
        }

        for record in records:
            difficulty = record.difficulty
            if difficulty in stats:
                stats[difficulty]["attempts"] += 1
                stats[difficulty]["success"] += 1 if record.success else 0
                stats[difficulty]["total_time"] += record.time_spent
                stats[difficulty]["avg_attempts"].append(record.attempts)

        # 计算汇总统计
        result = {}
        for difficulty, data in stats.items():
            if data["attempts"] > 0:
                result[difficulty] = {
                    "total_attempts": data["attempts"],
                    "success_count": data["success"],
                    "success_rate": data["success"] / data["attempts"],
                    "avg_time": data["total_time"] / data["attempts"],
                    "avg_attempts_per_problem": statistics.mean(data["avg_attempts"])
                        if data["avg_attempts"] else 0
                }
            else:
                result[difficulty] = {
                    "total_attempts": 0,
                    "success_count": 0,
                    "success_rate": 0.0,
                    "avg_time": 0.0,
                    "avg_attempts_per_problem": 0.0
                }

        return result

    def _generate_recommendations(
        self,
        learning_curve: LearningCurve,
        weak_areas: WeakAreaAnalysis,
        study_patterns: StudyPatternAnalysis,
        difficulty_stats: Dict[str, Dict]
    ) -> List[str]:
        """
        生成综合建议

        Args:
            learning_curve: 学习曲线
            weak_areas: 薄弱领域
            study_patterns: 学习模式
            difficulty_stats: 难度统计

        Returns:
            建议列表
        """
        recommendations = []

        # 基于学习曲线
        if learning_curve.trend == "improving":
            recommendations.append("🎉 学习曲线呈上升趋势，保持良好势头！")
        elif learning_curve.trend == "declining":
            recommendations.append("📉 近期表现有所下降，建议适当降低难度，巩固基础")

        # 基于薄弱领域
        recommendations.extend(weak_areas.improvement_suggestions)

        # 基于学习模式
        if study_patterns.best_hours:
            hours_str = ", ".join(f"{h}点" for h in study_patterns.best_hours[:3])
            recommendations.append(f"⏰ 你在 {hours_str} 学习效果最好")

        if study_patterns.consistency_score < 0.5:
            recommendations.append("📅 建议保持更规律的学习节奏")

        if study_patterns.streak_stats.get("current_streak", 0) >= 7:
            recommendations.append("🔥 连续学习超过一周，太棒了！")

        # 基于难度分布
        easy_rate = difficulty_stats.get("easy", {}).get("success_rate", 0)
        medium_rate = difficulty_stats.get("medium", {}).get("success_rate", 0)

        if easy_rate > 0.9 and medium_rate < 0.6:
            recommendations.append("💪 Easy 题目已经很熟练，建议增加 Medium 练习")

        return recommendations


def create_attempt_record(
    problem_id: str,
    difficulty: str,
    tags: List[str],
    success: bool,
    time_spent: int,
    attempts: int = 1,
    hints_used: int = 0,
    timestamp: datetime = None
) -> AttemptRecord:
    """
    创建尝试记录

    Args:
        problem_id: 题目ID
        difficulty: 难度
        tags: 标签
        success: 是否成功
        time_spent: 花费时间
        attempts: 尝试次数
        hints_used: 提示使用次数
        timestamp: 时间戳

    Returns:
        AttemptRecord 对象
    """
    return AttemptRecord(
        problem_id=problem_id,
        difficulty=difficulty,
        tags=tags,
        success=success,
        time_spent=time_spent,
        attempts=attempts,
        hints_used=hints_used,
        timestamp=timestamp or datetime.now()
    )


# 便捷函数
def analyze_user_history(
    attempt_history: List[Dict]
) -> Dict:
    """
    分析用户历史的便捷函数

    Args:
        attempt_history: 尝试历史（字典列表）

    Returns:
        分析结果字典
    """
    # 转换记录
    records = []
    for h in attempt_history:
        timestamp = h.get("timestamp")
        if isinstance(timestamp, str):
            timestamp = datetime.fromisoformat(timestamp)
        elif isinstance(timestamp, (int, float)):
            timestamp = datetime.fromtimestamp(timestamp)
        elif timestamp is None:
            timestamp = datetime.now()

        records.append(AttemptRecord(
            problem_id=h["problem_id"],
            difficulty=h["difficulty"],
            tags=h.get("tags", []),
            success=h["success"],
            time_spent=h.get("time_spent", 30),
            attempts=h.get("attempts", 1),
            hints_used=h.get("hints_used", 0),
            timestamp=timestamp
        ))

    # 分析
    analyzer = HistoryAnalyzer()
    result = analyzer.analyze(records)

    # 转换为可序列化的字典
    return {
        "total_problems": result.total_problems,
        "total_time": result.total_time,
        "success_rate": result.success_rate,
        "learning_curve": {
            "trend": result.learning_curve.trend,
            "improvement_rate": result.learning_curve.improvement_rate,
            "data_points": len(result.learning_curve.time_points)
        },
        "weak_areas": {
            "weak_tags": result.weak_areas.weak_tags,
            "weak_difficulties": result.weak_areas.weak_difficulties,
            "recommended_focus": result.weak_areas.recommended_focus,
            "suggestions": result.weak_areas.improvement_suggestions
        },
        "study_patterns": {
            "best_hours": result.study_patterns.best_hours,
            "best_days": result.study_patterns.best_days,
            "avg_session_duration": result.study_patterns.avg_session_duration,
            "consistency_score": result.study_patterns.consistency_score,
            "streak_stats": result.study_patterns.streak_stats
        },
        "tag_proficiency": result.tag_proficiency,
        "difficulty_stats": result.difficulty_stats,
        "recommendations": result.recommendations
    }

