from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Dict, List, Optional


@dataclass(slots=True)
class TaskOracleRecord:
    task_id: str
    group_name: str
    scenario_family: str
    task_success: bool
    oracle_final_quality_score: float
    oracle_total_latency_ms: int
    oracle_total_cost: float
    oracle_final_utility: float
    failure_type: Optional[str] = None

    def to_dict(self) -> Dict[str, object]:
        return asdict(self)


@dataclass(slots=True)
class StepOracleRecord:
    task_id: str
    step_id: str
    step_type: str
    selected_service_id: str
    step_success: bool
    oracle_step_quality_score: float
    oracle_step_consumability_score: float
    oracle_step_latency_ms: int
    oracle_step_cost: float
    step_failure_type: Optional[str] = None

    def to_dict(self) -> Dict[str, object]:
        return asdict(self)


@dataclass(slots=True)
class SelectionOracleRecord:
    task_id: str
    step_id: str
    candidate_pool_size: int
    selected_service_id: str
    service_type_match: bool
    oracle_best_service_id: str
    selection_regret: float

    def to_dict(self) -> Dict[str, object]:
        return asdict(self)


def serialize_task_records(records: List[TaskOracleRecord]) -> List[Dict[str, object]]:
    return [record.to_dict() for record in records]


def serialize_step_records(records: List[StepOracleRecord]) -> List[Dict[str, object]]:
    return [record.to_dict() for record in records]


def serialize_selection_records(records: List[SelectionOracleRecord]) -> List[Dict[str, object]]:
    return [record.to_dict() for record in records]
