from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..database import get_db
from ..models.organization import Organization
from ..models.review import ServiceReview
from ..models.service import Service
from ..models.usage import Usage
from ..schemas.review import ServiceReviewCreate, ServiceReviewResponse, ServiceTrustSummary
from ..services.trust_service import TrustService
from .deps import get_current_principal

router = APIRouter()

REVIEW_EDIT_HOURS = 24
VALID_OUTCOMES = {"success", "partial", "fail"}
ALLOWED_OUTCOMES_BY_USAGE_STATE = {
    "success": {"success", "partial", "fail"},
    "partial": {"partial", "fail"},
    "fail": {"fail"},
}


def _review_feedback_text(review_data: ServiceReviewCreate):
    return review_data.feedback_text if review_data.feedback_text is not None else review_data.comment


def _review_evidence(review_data: ServiceReviewCreate):
    evidence = dict(review_data.evidence or {})
    if review_data.rating is not None:
        evidence.setdefault("rating", review_data.rating)
    if review_data.task_context is not None:
        evidence.setdefault("task_context", review_data.task_context)
    return evidence or None


def _ensure_review_allowed(review_data: ServiceReviewCreate, usage: Usage, service: Service):
    if review_data.service_id is not None and review_data.service_id != usage.service_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="service_id does not match usage record"
        )

    if not usage.is_meaningful:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This usage record did not enter service execution and cannot be reviewed"
        )

    if usage.final_state not in VALID_OUTCOMES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current usage state is not reviewable"
        )

    if not service.is_public:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only public services can be reviewed at this stage"
        )

    if review_data.outcome not in VALID_OUTCOMES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="outcome only supports success / partial / fail"
        )

    allowed_outcomes = ALLOWED_OUTCOMES_BY_USAGE_STATE.get(usage.final_state, {"fail"})
    if review_data.outcome not in allowed_outcomes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Usage state is {usage.final_state}; outcome={review_data.outcome} is not allowed"
        )


@router.post("/", response_model=ServiceReviewResponse)
def create_or_update_review(
    review_data: ServiceReviewCreate,
    principal=Depends(get_current_principal),
    db: Session = Depends(get_db)
):
    current_user = principal["user"]
    current_agent = principal["agent"]

    usage = db.query(Usage).filter(
        Usage.id == review_data.usage_id,
        Usage.user_id == current_user.id
    ).first()
    if not usage:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usage record not found"
        )

    service = db.query(Service).filter(Service.id == usage.service_id).first()
    if not service:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Service not found"
        )

    _ensure_review_allowed(review_data, usage, service)

    organization = db.query(Organization).filter(
        Organization.id == service.organization_id
    ).first()
    if organization and organization.owner_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Service provider cannot review its own service"
        )

    existing_review = db.query(ServiceReview).filter(
        ServiceReview.usage_id == usage.id
    ).first()

    feedback_text = _review_feedback_text(review_data)
    evidence = _review_evidence(review_data)

    if existing_review:
        if existing_review.is_locked:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Review is locked and cannot be modified"
            )

        if existing_review.created_at:
            cutoff = datetime.now(timezone.utc) - timedelta(hours=REVIEW_EDIT_HOURS)
            created_at = existing_review.created_at
            if created_at.tzinfo is None:
                created_at = created_at.replace(tzinfo=timezone.utc)
            if created_at < cutoff:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Review edit window has expired"
                )

        existing_review.outcome = review_data.outcome
        existing_review.task_fit = review_data.task_fit
        existing_review.output_quality = review_data.output_quality
        existing_review.protocol_adherence = review_data.protocol_adherence
        existing_review.would_reuse = review_data.would_reuse
        existing_review.cost_satisfaction = review_data.cost_satisfaction
        existing_review.feedback_text = feedback_text
        existing_review.evidence = evidence
        existing_review.reviewer_agent_id = current_agent.id if current_agent else None

        db.commit()
        db.refresh(existing_review)
        TrustService(db).recompute_service_trust(service.id)
        return existing_review

    review = ServiceReview(
        usage_id=usage.id,
        service_id=service.id,
        reviewer_user_id=current_user.id,
        reviewer_agent_id=current_agent.id if current_agent else None,
        outcome=review_data.outcome,
        task_fit=review_data.task_fit,
        output_quality=review_data.output_quality,
        protocol_adherence=review_data.protocol_adherence,
        would_reuse=review_data.would_reuse,
        cost_satisfaction=review_data.cost_satisfaction,
        feedback_text=feedback_text,
        evidence=evidence
    )

    db.add(review)
    db.commit()
    db.refresh(review)

    TrustService(db).recompute_service_trust(service.id)
    return review


@router.get("/services/{service_id}/summary", response_model=ServiceTrustSummary)
def get_service_trust_summary(
    service_id: int,
    principal=Depends(get_current_principal),
    db: Session = Depends(get_db)
):
    current_user = principal["user"]

    service = db.query(Service).filter(
        Service.id == service_id,
        Service.is_active == True
    ).first()
    if not service:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Service not found"
        )

    if not service.is_public:
        organization = db.query(Organization).filter(
            Organization.id == service.organization_id
        ).first()
        if not organization or organization.owner_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No permission to view this service trust summary"
            )

    trust_stats = TrustService(db).get_service_trust_summary(service_id)
    if not trust_stats:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Service has no trust summary"
        )

    return trust_stats


@router.get("/my-usage/{usage_id}", response_model=ServiceReviewResponse)
def get_my_review_by_usage(
    usage_id: int,
    principal=Depends(get_current_principal),
    db: Session = Depends(get_db)
):
    current_user = principal["user"]

    usage = db.query(Usage).filter(
        Usage.id == usage_id,
        Usage.user_id == current_user.id
    ).first()
    if not usage:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usage record not found"
        )

    review = db.query(ServiceReview).filter(
        ServiceReview.usage_id == usage.id
    ).first()
    if not review:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Review not found"
        )

    return review
