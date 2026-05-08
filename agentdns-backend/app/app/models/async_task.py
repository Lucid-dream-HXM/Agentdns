"""
异步任务ORM模型
定义异步任务的数据模型，用于处理长时间运行的服务请求
"""

from sqlalchemy import Column, String, Integer, Text, DateTime, ForeignKey, Float, JSON, Boolean  # SQLAlchemy ORM核心组件，用于定义数据库模型字段
from sqlalchemy.sql import func  # SQLAlchemy SQL函数，用于处理数据库时间戳等
from sqlalchemy.orm import relationship  # SQLAlchemy ORM关系映射，用于定义模型间关联
from ..database import Base  # 数据库基础模型类，所有模型都需要继承此类


class AsyncTask(Base):
    """
    异步任务模型 - 存储系统中的异步任务信息
    
    该模型定义了异步任务的基本属性，包括任务状态、输入输出数据、计费信息等
    与用户、服务模型存在关联关系
    """
    __tablename__ = "async_tasks"  # 定义数据库表名
    
    # 主键和关联字段
    id = Column(String(36), primary_key=True)  # UUID任务ID，主键
    service_id = Column(Integer, ForeignKey("services.id"), nullable=False)  # 服务ID，外键，不允许为空
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)  # 用户ID，外键，不允许为空
    agent_id = Column(Integer, ForeignKey("agents.id"), nullable=True)  # 创建该异步任务的Agent ID，可空
    usage_id = Column(Integer, ForeignKey("usage_records.id"), nullable=True)  # 与该异步任务关联的Usage锚点ID

    # 任务状态和数据字段
    state = Column(String(20), default="pending", nullable=False)  # 任务状态：pending（待处理）、running（运行中）、succeeded（成功）、failed（失败），默认为pending，不允许为空
    input_data = Column(JSON, nullable=False)  # 原始输入数据，JSON格式，不允许为空
    result_data = Column(JSON)  # 最终结果数据，JSON格式
    error_message = Column(Text)  # 错误信息
    progress = Column(Float, default=0.0)  # 任务进度（0.0-1.0），默认为0.0
    
    # 外部任务信息字段
    external_task_id = Column(String(200))  # 外部任务ID
    external_status = Column(String(50))  # 外部状态
    
    # 计费信息字段
    estimated_cost = Column(Float, default=0.0)  # 预估成本，默认为0.0
    actual_cost = Column(Float, default=0.0)  # 实际成本，默认为0.0
    is_billed = Column(Boolean, default=False)  # 是否已计费，默认为False
    
    # 时间戳字段
    created_at = Column(DateTime(timezone=True), server_default=func.now())  # 创建时间，服务器自动生成当前时间
    started_at = Column(DateTime(timezone=True))  # 任务开始时间
    completed_at = Column(DateTime(timezone=True))  # 任务完成时间
    last_updated = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())  # 最后更新时间，服务器自动生成当前时间，更新记录时自动更新
    
    # 模型关联关系
    service = relationship("Service", back_populates="async_tasks")  # 与服务模型的反向关联（一个服务有多个异步任务）
    user = relationship("User", back_populates="async_tasks")  # 与用户模型的反向关联（一个用户有多个异步任务）
    agent = relationship("Agent", back_populates="async_tasks")
    usage = relationship("Usage", back_populates="async_tasks")
    
    def __repr__(self):
        """对象的字符串表示"""
        return f"<AsyncTask(id={self.id}, state={self.state}, service_id={self.service_id})>"
    
    def to_dict(self, include_sensitive=False):
        """
        转换为字典
        将任务对象转换为字典格式，便于序列化和API返回
        
        Args:
            include_sensitive: 是否包含敏感字段
        
        Returns:
            包含任务信息的字典
        """
        result = {
            "task_id": self.id,  # 任务ID
            "state": self.state,  # 任务状态
            "progress": self.progress,  # 任务进度
            "created_at": self.created_at.isoformat() if self.created_at else None,  # 创建时间
            "started_at": self.started_at.isoformat() if self.started_at else None,  # 开始时间
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,  # 完成时间
            "last_updated": self.last_updated.isoformat() if self.last_updated else None,  # 最后更新时间
        }
        
        # 根据状态添加字段
        if self.state == "succeeded":
            result["results"] = self.result_data  # 结果数据
            result["cost"] = self.actual_cost  # 实际成本
        elif self.state == "failed":
            result["error"] = self.error_message  # 错误信息
        
        # 仅在请求时包含敏感字段
        if include_sensitive:
            result.update({
                "external_task_id": self.external_task_id,  # 外部任务ID
                "external_status": self.external_status,  # 外部状态
                "input_data": self.input_data,  # 输入数据
                "estimated_cost": self.estimated_cost,  # 预估成本
                "is_billed": self.is_billed  # 是否已计费
            })
        
        return result
    
    @property
    def is_completed(self):
        """
        检查任务是否已完成
        判断任务是否处于成功或失败状态
        
        Returns:
            如果任务已完成返回True，否则返回False
        """
        return self.state in ["succeeded", "failed"]
    
    @property
    def is_active(self):
        """
        检查任务是否仍在活动
        判断任务是否处于待处理或运行中状态
        
        Returns:
            如果任务仍在活动返回True，否则返回False
        """
        return self.state in ["pending", "running"]
