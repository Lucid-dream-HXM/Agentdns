from __future__ import annotations

from typing import Dict, Tuple

from experiments.evaluators.oracle_schema import StepOracleRecord
from experiments.evaluators.utility_aggregator import compute_step_utility


def evaluate_step(task_id: str, step_id: str, step_type: str, service: Dict[str, object], *, step_success: bool) -> Tuple[StepOracleRecord, float]:
    quality = float(service['observed_quality'])
    consumability = float(service['observed_consumability'])
    latency_ms = int(service['observed_latency_ms'])
    cost = float(service['observed_cost'])
    utility = compute_step_utility(quality, consumability, latency_ms, cost)
    record = StepOracleRecord(
        task_id=task_id,
        step_id=step_id,
        step_type=step_type,
        selected_service_id=str(service['service_key']),
        step_success=step_success,
        oracle_step_quality_score=quality,
        oracle_step_consumability_score=consumability,
        oracle_step_latency_ms=latency_ms,
        oracle_step_cost=cost,
        step_failure_type=None if step_success else 'step_failed',
    )
    return record, utility
