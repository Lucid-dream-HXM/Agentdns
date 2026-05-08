from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class ServiceReviewCreate(BaseModel):
    """
    Service review create/update request.

    The core review fields are used by the backend trust model. The optional
    service_id, rating, comment, and task_context fields keep compatibility
    with the experiment runner payload.
    """
    usage_id: int
    service_id: Optional[int] = None

    outcome: str = Field(..., description="success / partial / fail")
    rating: Optional[int] = Field(None, ge=1, le=5)
    task_fit: int = Field(..., ge=1, le=5)
    output_quality: int = Field(..., ge=1, le=5)
    protocol_adherence: int = Field(..., ge=1, le=5)
    would_reuse: bool
    cost_satisfaction: Optional[int] = Field(None, ge=1, le=5)

    feedback_text: Optional[str] = None
    comment: Optional[str] = None
    evidence: Optional[Dict[str, Any]] = None
    task_context: Optional[Dict[str, Any]] = None


class ServiceReviewResponse(BaseModel):
    """
    Service review response.
    """
    id: int
    usage_id: int
    service_id: int
    reviewer_user_id: int
    reviewer_agent_id: Optional[int] = None

    outcome: str
    task_fit: int
    output_quality: int
    protocol_adherence: int
    would_reuse: bool
    cost_satisfaction: Optional[int] = None

    feedback_text: Optional[str] = None
    evidence: Optional[Dict[str, Any]] = None

    is_locked: bool
    is_public_aggregate: bool

    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ServiceTrustSummary(BaseModel):
    """
    Aggregated trust summary for one service.
    """
    service_id: int
    trust_score: float
    objective_score: float
    subjective_score: float

    success_rate: float
    avg_response_time_ms: float

    rating_count: int
    usage_count: int

    last_reviewed_at: Optional[datetime] = None
    last_calculated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
