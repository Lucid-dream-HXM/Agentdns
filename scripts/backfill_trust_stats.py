#!/usr/bin/env python3
"""
历史信任摘要回填脚本

用途：
1. 基于现有的Usage历史，为公开服务初始化 ServiceTrustStats
2. 不伪造历史主观评价，仅回填客观分与已有评价汇总结果
"""

import sys
import os
from pathlib import Path
from datetime import datetime

project_root = Path(__file__).parent / "agentdns-backend"
sys.path.insert(0, str(project_root))

from app.database import SessionLocal
from app.models.service import Service
from app.services.trust_service import TrustService


def main():
    """
    主执行入口
    """
    db = SessionLocal()

    try:
        trust_service = TrustService(db)

        services = db.query(Service).filter(
            Service.is_active == True,
            Service.is_public == True
        ).all()

        print(f"[INFO] 开始回填公开服务信任摘要，共 {len(services)} 个服务")

        success_count = 0
        failed_count = 0

        for service in services:
            try:
                trust_stats = trust_service.recompute_service_trust(service.id)
                print(
                    f"[OK] service_id={service.id}, "
                    f"name={service.name}, "
                    f"trust_score={trust_stats.trust_score}, "
                    f"usage_count={trust_stats.usage_count}, "
                    f"rating_count={trust_stats.rating_count}"
                )
                success_count += 1

            except Exception as e:
                print(f"[ERROR] service_id={service.id}, name={service.name}, error={e}")
                failed_count += 1

        print("\n========== 回填完成 ==========")
        print(f"成功: {success_count}")
        print(f"失败: {failed_count}")
        print(f"完成时间: {datetime.utcnow().isoformat()}")

    finally:
        db.close()


if __name__ == "__main__":
    main()