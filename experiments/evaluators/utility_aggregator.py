from __future__ import annotations

from typing import Iterable


def compute_step_utility(
    quality: float,
    consumability: float,
    latency_ms: int,
    cost: float,
    *,
    latency_budget_ms: int = 2500,
    cost_budget: float = 0.12,
) -> float:
    latency_score = max(0.0, 1 - latency_ms / max(latency_budget_ms, 1))
    cost_score = max(0.0, 1 - cost / max(cost_budget, 1e-8))
    utility = quality * 0.45 + consumability * 0.30 + latency_score * 0.15 + cost_score * 0.10
    return round(max(0.0, min(1.0, utility)), 4)


def compute_task_utility(
    step_utilities: Iterable[float],
    task_success: bool,
    *,
    success_bonus: float = 0.08,
) -> float:
    values = list(step_utilities)
    if not values:
        return 0.0
    base = sum(values) / len(values)
    if task_success:
        base += success_bonus
    return round(max(0.0, min(1.0, base)), 4)
