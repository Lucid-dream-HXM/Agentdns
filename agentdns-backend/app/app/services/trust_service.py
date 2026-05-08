from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from ..models.usage import Usage
from ..models.review import ServiceReview, ServiceTrustStats


class TrustService:
    """
    服务信任计算服务

    负责基于Usage客观数据和ServiceReview主观数据，
    计算并维护服务级别的信任摘要信息
    """

    def __init__(self, db: Session):
        self.db = db

    def _clamp_score(self, value: float) -> float:
        """
        将分值限制在0~100区间
        """
        if value < 0:
            return 0.0
        if value > 100:
            return 100.0
        return round(value, 2)

    def _calc_latency_score(self, avg_response_time_ms: float) -> float:
        """
        根据平均响应时间计算延迟分

        第一阶段使用简单分段规则，后续可进一步优化
        """
        if avg_response_time_ms <= 0:
            return 50.0
        if avg_response_time_ms <= 1000:
            return 100.0
        if avg_response_time_ms <= 3000:
            return 80.0
        if avg_response_time_ms <= 5000:
            return 60.0
        if avg_response_time_ms <= 10000:
            return 40.0
        return 20.0

    def _calc_objective_score(self, service_id: int) -> dict:
        """
        计算服务的客观分

        基于真实Usage记录，计算成功率、平均响应时间、调用量等指标
        """
        usage_records = self.db.query(Usage).filter(
            Usage.service_id == service_id,
            Usage.is_meaningful == True
        ).all()

        usage_count = len(usage_records)
        if usage_count == 0:
            return {
                "objective_score": 0.0,
                "success_rate": 0.0,
                "avg_response_time_ms": 0.0,
                "usage_count": 0
            }

        success_count = 0.0
        response_times = []

        for usage in usage_records:
            # 成功/部分成功加权
            if usage.final_state == "success":
                success_count += 1.0
            elif usage.final_state == "partial":
                success_count += 0.5

            if usage.execution_time_ms is not None and usage.execution_time_ms >= 0:
                response_times.append(float(usage.execution_time_ms))

        success_rate = (success_count / usage_count) * 100.0
        avg_response_time_ms = sum(response_times) / len(response_times) if response_times else 0.0

        latency_score = self._calc_latency_score(avg_response_time_ms)
        volume_confidence = min((usage_count / 20.0) * 100.0, 100.0)

        # 第一阶段加入轻量样本保护：
        # 样本越少，客观分越向中性区间收缩，避免极少量调用把分数拉得过高或过低
        raw_objective_score = (
            0.50 * success_rate +
            0.30 * latency_score +
            0.20 * volume_confidence
        )

        if usage_count < 5:
            shrink_ratio = usage_count / 5.0
            objective_score = 50.0 * (1 - shrink_ratio) + raw_objective_score * shrink_ratio
        else:
            objective_score = raw_objective_score

        return {
            "objective_score": self._clamp_score(objective_score),
            "success_rate": round(success_rate, 2),
            "avg_response_time_ms": round(avg_response_time_ms, 2),
            "usage_count": usage_count
        }

    def _calc_subjective_score(self, service_id: int) -> dict:
        """
        计算服务的主观分

        基于结构化评价记录，计算平均主观质量分
        """
        reviews = self.db.query(ServiceReview).filter(
            ServiceReview.service_id == service_id,
            ServiceReview.is_public_aggregate == True
        ).all()

        rating_count = len(reviews)
        if rating_count == 0:
            return {
                "subjective_score": 0.0,
                "rating_count": 0,
                "last_reviewed_at": None
            }

        review_scores = []
        last_reviewed_at = None

        for review in reviews:
            cost_score = review.cost_satisfaction if review.cost_satisfaction is not None else 3

            # 先按1~5评分计算组合分，再映射到0~100
            base_score = (
                0.35 * review.task_fit +
                0.30 * review.output_quality +
                0.20 * review.protocol_adherence +
                0.15 * cost_score
            ) * 20.0

            # 是否愿意再次使用作为轻量修正项
            if review.would_reuse:
                base_score += 5.0
            else:
                base_score -= 5.0

            # 将最终结果 outcome 纳入主观分修正
            # 第一阶段采用轻量规则：
            # - success：小幅加分
            # - partial：不加不减
            # - fail：明显扣分
            outcome_adjust_map = {
                "success": 5.0,
                "partial": 0.0,
                "fail": -15.0
            }
            base_score += outcome_adjust_map.get(review.outcome, 0.0)

            review_scores.append(self._clamp_score(base_score))

            if review.created_at and (last_reviewed_at is None or review.created_at > last_reviewed_at):
                last_reviewed_at = review.created_at

        subjective_score = sum(review_scores) / len(review_scores)

        return {
            "subjective_score": self._clamp_score(subjective_score),
            "rating_count": rating_count,
            "last_reviewed_at": last_reviewed_at
        }

    def recompute_service_trust(self, service_id: int) -> ServiceTrustStats:
        """
        重算指定服务的信任摘要

        这是第一阶段的核心入口：评价提交后或需要展示时调用
        """
        objective_data = self._calc_objective_score(service_id)
        subjective_data = self._calc_subjective_score(service_id)

        # 没有主观评价时，先用客观分作为信任分
        if subjective_data["rating_count"] == 0:
            trust_score = objective_data["objective_score"]
        else:
            trust_score = (
                0.65 * objective_data["objective_score"] +
                0.35 * subjective_data["subjective_score"]
            )

        trust_score = self._clamp_score(trust_score)

        trust_stats = self.db.query(ServiceTrustStats).filter(
            ServiceTrustStats.service_id == service_id
        ).first()

        if not trust_stats:
            trust_stats = ServiceTrustStats(service_id=service_id)
            self.db.add(trust_stats)

        trust_stats.trust_score = trust_score
        trust_stats.objective_score = objective_data["objective_score"]
        trust_stats.subjective_score = subjective_data["subjective_score"]
        trust_stats.success_rate = objective_data["success_rate"]
        trust_stats.avg_response_time_ms = objective_data["avg_response_time_ms"]
        trust_stats.rating_count = subjective_data["rating_count"]
        trust_stats.usage_count = objective_data["usage_count"]
        trust_stats.last_reviewed_at = subjective_data["last_reviewed_at"]
        trust_stats.last_calculated_at = datetime.utcnow()

        self.db.commit()
        self.db.refresh(trust_stats)
        return trust_stats

    def get_service_trust_summary(self, service_id: int) -> Optional[ServiceTrustStats]:
        """
        获取指定服务的信任摘要

        如果当前不存在摘要，则现场计算一次
        """
        trust_stats = self.db.query(ServiceTrustStats).filter(
            ServiceTrustStats.service_id == service_id
        ).first()

        if trust_stats:
            return trust_stats

        return self.recompute_service_trust(service_id)