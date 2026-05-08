from __future__ import annotations

from typing import Iterable

from experiments.evaluators.oracle_schema import TaskOracleRecord
from experiments.evaluators.utility_aggregator import compute_task_utility


def evaluate_task(
    *,
    task_id: str,
    group_name: str,
    scenario_family: str,
    task_success: bool,
    step_qualities: Iterable[float],
    step_latencies_ms: Iterable[int],
    step_costs: Iterable[float],
    step_utilities: Iterable[float],
    failure_type: str | None,
) -> TaskOracleRecord:
    qualities = list(step_qualities)
    latencies = list(step_latencies_ms)
    costs = list(step_costs)
    utilities = list(step_utilities)
    final_quality = round(sum(qualities) / len(qualities), 4) if qualities else 0.0
    task_utility = compute_task_utility(utilities, task_success)
    return TaskOracleRecord(
        task_id=task_id,
        group_name=group_name,
        scenario_family=scenario_family,
        task_success=task_success,
        oracle_final_quality_score=final_quality,
        oracle_total_latency_ms=sum(latencies),
        oracle_total_cost=round(sum(costs), 4),
        oracle_final_utility=task_utility,
        failure_type=failure_type,
    )
