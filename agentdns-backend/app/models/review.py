from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Float, Boolean, Text, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from ..database import Base


class ServiceReview(Base):
    """
    服务评价模型 - 存储一次真实服务调用后的结构化评价

    该模型用于记录用户或Agent在真实调用完成后提交的可选评价，
    每条评价必须绑定到一条真实的Usage记录，用于后续服务信任分计算
    """
    __tablename__ = "service_reviews"

    # 主键字段
    id = Column(Integer, primary_key=True, index=True)

    # 关联字段
    usage_id = Column(Integer, ForeignKey("usage_records.id"), nullable=False, unique=True)  # 一次调用只允许一条有效评价
    service_id = Column(Integer, ForeignKey("services.id"), nullable=False)  # 被评价的服务ID
    reviewer_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)  # 评价者用户ID
    reviewer_agent_id = Column(Integer, ForeignKey("agents.id"), nullable=True)  # 评价者Agent ID，可空

    # 评价核心字段
    outcome = Column(String(20), nullable=False)  # success / partial / fail
    task_fit = Column(Integer, nullable=False)  # 任务匹配度 1~5
    output_quality = Column(Integer, nullable=False)  # 输出质量 1~5
    protocol_adherence = Column(Integer, nullable=False)  # 协议/格式符合度 1~5
    would_reuse = Column(Boolean, nullable=False)  # 是否愿意再次使用
    cost_satisfaction = Column(Integer, nullable=True)  # 性价比满意度 1~5，可空

    # 辅助信息字段
    feedback_text = Column(Text, nullable=True)  # 可选文本反馈
    evidence = Column(JSON, nullable=True)  # 可选结构化证据，如schema_valid/downstream_success等

    # 状态字段
    is_locked = Column(Boolean, default=False)  # 评价是否已锁定，第一阶段先预留
    is_public_aggregate = Column(Boolean, default=True)  # 是否可用于公开聚合统计

    # 时间戳字段
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # 模型关联关系
    usage = relationship("Usage", back_populates="review")
    service = relationship("Service", back_populates="reviews")
    reviewer_user = relationship("User", foreign_keys=[reviewer_user_id])
    reviewer_agent = relationship("Agent", foreign_keys=[reviewer_agent_id], back_populates="reviews")


class ServiceTrustStats(Base):
    """
    服务信任摘要模型 - 存储服务级别的聚合信任统计信息

    该模型用于存储公开服务的客观分、主观分和综合信任分，
    供服务发现重排和服务详情展示直接读取，避免每次临时聚合计算
    """
    __tablename__ = "service_trust_stats"

    # 服务ID作为主键，一条服务对应一条聚合摘要
    service_id = Column(Integer, ForeignKey("services.id"), primary_key=True)

    # 信任分字段
    trust_score = Column(Float, default=0.0)  # 综合信任分
    objective_score = Column(Float, default=0.0)  # 客观分
    subjective_score = Column(Float, default=0.0)  # 主观分

    # 聚合统计字段
    success_rate = Column(Float, default=0.0)  # 成功率
    avg_response_time_ms = Column(Float, default=0.0)  # 平均响应时间
    rating_count = Column(Integer, default=0)  # 评价数量
    usage_count = Column(Integer, default=0)  # 有效调用数量

    # 时间字段
    last_reviewed_at = Column(DateTime(timezone=True), nullable=True)  # 最近一次评价时间
    last_calculated_at = Column(DateTime(timezone=True), nullable=True)  # 最近一次计算时间

    # 模型关联关系
    service = relationship("Service", back_populates="trust_stats")