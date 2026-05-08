from __future__ import annotations

from typing import Dict

from experiments.evaluators.oracle_schema import SelectionOracleRecord


def evaluate_selection(task_id: str, step_id: str, *, candidate_pool_size: int, selected_service: Dict[str, object], best_service: Dict[str, object], required_category: str) -> SelectionOracleRecord:
    selected_quality = float(selected_service.get('observed_quality', 0.0))
    best_quality = float(best_service.get('observed_quality', selected_quality))
    regret = max(0.0, best_quality - selected_quality)
    return SelectionOracleRecord(
        task_id=task_id,
        step_id=step_id,
        candidate_pool_size=candidate_pool_size,
        selected_service_id=str(selected_service['service_key']),
        service_type_match=str(selected_service['category']) == required_category,
        oracle_best_service_id=str(best_service['service_key']),
        selection_regret=round(regret, 4),
    )
