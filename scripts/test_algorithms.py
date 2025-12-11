"""
算法模块功能测试脚本

演示所有核心算法的使用方法
"""
import sys
import json
from pathlib import Path
from datetime import date

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from algorithms.greedy.priority_calculator import (
    PriorityCalculator, Problem, UserProfile
)
from algorithms.greedy.quick_scheduler import QuickScheduler
from algorithms.scheduler.time_allocator import TimeAllocator, quick_allocate
from algorithms.scheduler.task_scheduler import TaskScheduler, ScheduleConstraints
from algorithms.scheduler.multi_day_planner import MultiDayPlanner, PlanConfig
from algorithms.optimizer.sequence_optimizer import (
    SequenceOptimizer, create_problem_from_dict
)
from algorithms.optimizer.dp_optimizer import DPOptimizer, LearningGoals


def load_test_problems():
    """加载测试题目数据"""
    with open('data/problems/problems.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
        return data.get('problems', [])


def test_priority_calculator():
    """测试优先级计算器"""
    print("\n" + "=" * 60)
    print("测试 1: 优先级计算器")
    print("=" * 60)

    # 创建用户画像
    user_profile = UserProfile(
        skill_level='intermediate',
        completed_problems=set(),
        weak_tags=['dynamic-programming', 'tree'],
        strong_tags=['array', 'string'],
        focus_tags=['hash-table', 'two-pointers'],
        target_difficulty=['medium', 'easy']
    )

    # 创建测试题目
    test_problems = [
        Problem(
            id='1', title='Two Sum', difficulty='easy',
            tags=['array', 'hash-table'], estimated_time=15,
            frequency=0.95, acceptance_rate=0.49, companies=['amazon']
        ),
        Problem(
            id='53', title='Maximum Subarray', difficulty='medium',
            tags=['array', 'dynamic-programming'], estimated_time=25,
            frequency=0.86, acceptance_rate=0.49, companies=['amazon']
        ),
        Problem(
            id='300', title='Longest Increasing Subsequence', difficulty='medium',
            tags=['array', 'dynamic-programming', 'binary-search'], estimated_time=35,
            frequency=0.82, acceptance_rate=0.51, companies=['google']
        )
    ]

    calculator = PriorityCalculator()

    print("\n用户画像:")
    print(f"  - 技能水平: {user_profile.skill_level}")
    print(f"  - 薄弱标签: {user_profile.weak_tags}")
    print(f"  - 关注标签: {user_profile.focus_tags}")

    print("\n题目优先级排序:")
    ranked = calculator.rank_problems(test_problems, user_profile, ['amazon'])

    for i, (problem, score) in enumerate(ranked, 1):
        print(f"  {i}. {problem.title:40} | 优先级: {score:.3f}")

    print("\n✅ 优先级计算器测试完成")


def test_quick_scheduler():
    """测试快速调度器"""
    print("\n" + "=" * 60)
    print("测试 2: 快速调度器")
    print("=" * 60)

    problems = load_test_problems()[:10]  # 取前10道题

    user_profile = UserProfile(
        skill_level='intermediate',
        completed_problems=set(),
        weak_tags=[],
        strong_tags=[],
        focus_tags=['array', 'dynamic-programming'],
        target_difficulty=['medium']
    )

    # 转换为Problem对象
    problem_objects = [
        Problem(
            id=p['id'], title=p['title'], difficulty=p['difficulty'],
            tags=p['tags'], estimated_time=p['estimated_time'],
            frequency=p['frequency'], acceptance_rate=p['acceptance_rate'],
            companies=p['companies']
        )
        for p in problems
    ]

    scheduler = QuickScheduler()
    result = scheduler.schedule(
        problems=problem_objects,
        user_profile=user_profile,
        daily_time_budget=60,
        total_days=5,
        start_date=date.today()
    )

    print(f"\n生成计划:")
    print(f"  - 总天数: {result.total_days}")
    print(f"  - 总题数: {result.total_problems}")
    print(f"  - 总时间: {result.total_time} 分钟")

    print(f"\n每日安排:")
    for day_schedule in result.daily_schedules[:3]:  # 显示前3天
        print(f"  Day {day_schedule.day_index + 1} ({day_schedule.date}):")
        print(f"    题目数: {len(day_schedule.problems)}, 总时间: {day_schedule.total_time}分钟")
        for prob, time, priority in day_schedule.problems[:2]:  # 显示前2题
            print(f"      - {prob.title} ({prob.difficulty}, {time}分钟)")

    print("\n✅ 快速调度器测试完成")


def test_time_allocator():
    """测试时间分配器"""
    print("\n" + "=" * 60)
    print("测试 3: 时间分配器")
    print("=" * 60)

    allocator = TimeAllocator()

    test_cases = [
        ("Two Sum", "easy", ["array", "hash-table"], 15),
        ("Maximum Subarray", "medium", ["array", "dynamic-programming"], 25),
        ("Coin Change", "medium", ["dynamic-programming"], 35),
    ]

    print("\n时间估算 (用户水平: intermediate):")
    for title, difficulty, tags, base_time in test_cases:
        estimated = allocator.allocate_time(
            base_time, difficulty, tags, "intermediate", None
        )
        print(f"  {title:40} | 基础: {base_time}分钟 → 估算: {estimated}分钟")

    print("\n✅ 时间分配器测试完成")


def test_sequence_optimizer():
    """测试顺序优化器"""
    print("\n" + "=" * 60)
    print("测试 4: 顺序优化器")
    print("=" * 60)

    problems = load_test_problems()[:10]

    # 为题目添加优先级
    for i, p in enumerate(problems):
        p['priority'] = 1.0 - (i * 0.05)

    problem_objects = [create_problem_from_dict(p) for p in problems]

    optimizer = SequenceOptimizer()
    result = optimizer.optimize_order(
        problem_objects,
        preferred_tags=['array', 'dynamic-programming', 'tree']
    )

    print(f"\n优化结果:")
    print(f"  - 优化得分: {result.optimization_score:.3f}")
    print(f"  - 依赖层级数: {len(result.dependency_layers)}")
    print(f"  - 标签聚类数: {len(result.tag_clusters)}")

    print(f"\n优化后的顺序 (前5题):")
    for i, problem in enumerate(result.problems[:5], 1):
        print(f"  {i}. {problem.title:40} | {problem.difficulty:6} | {problem.tags[:2]}")

    print("\n✅ 顺序优化器测试完成")


def test_dp_optimizer():
    """测试DP优化器"""
    print("\n" + "=" * 60)
    print("测试 5: DP优化器")
    print("=" * 60)

    problems_data = load_test_problems()[:15]

    # 创建Problem对象
    from algorithms.optimizer.dp_optimizer import create_problem_from_dict
    problems = [create_problem_from_dict(p) for p in problems_data]

    # 设置学习目标
    learning_goals = LearningGoals(
        target_tags=['array', 'dynamic-programming', 'tree'],
        target_companies=['amazon', 'google'],
        min_tag_coverage=0.7
    )

    optimizer = DPOptimizer()

    # 测试贪心+局部优化
    result_greedy = optimizer.optimize_selection(
        problems, time_budget=180, learning_goals=learning_goals
    )

    print(f"\n优化结果 (贪心+局部优化):")
    print(f"  - 选中题数: {len(result_greedy.selected_problems)}")
    print(f"  - 总价值: {result_greedy.total_value:.2f}")
    print(f"  - 总时间: {result_greedy.total_time} / 180 分钟")
    print(f"  - 时间利用率: {result_greedy.metadata['time_utilization']:.1%}")

    print(f"\n  标签覆盖率:")
    for tag, coverage in list(result_greedy.tag_coverage.items())[:3]:
        print(f"    - {tag}: {coverage:.1%}")

    print(f"\n  难度分布:")
    for difficulty, count in result_greedy.difficulty_distribution.items():
        print(f"    - {difficulty}: {count}道")

    # 测试DP算法（小规模）
    result_dp = optimizer.optimize_with_dp(
        problems[:10], time_budget=120, learning_goals=learning_goals
    )

    print(f"\n优化结果 (动态规划):")
    print(f"  - 选中题数: {len(result_dp.selected_problems)}")
    print(f"  - 总价值: {result_dp.total_value:.2f}")
    print(f"  - 总时间: {result_dp.total_time} / 120 分钟")

    print("\n✅ DP优化器测试完成")


def main():
    """主函数"""
    print("\n" + "=" * 60)
    print("智能刷题计划调度系统 - 算法模块测试")
    print("=" * 60)

    try:
        # 运行所有测试
        test_priority_calculator()
        test_quick_scheduler()
        test_time_allocator()
        test_sequence_optimizer()
        test_dp_optimizer()

        print("\n" + "=" * 60)
        print("✅ 所有算法模块测试通过！")
        print("=" * 60)

    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
