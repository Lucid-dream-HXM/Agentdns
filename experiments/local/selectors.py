from __future__ import annotations

from typing import Any, Dict, List


def choose_direct_general_service(candidates: List[Dict[str, Any]]) -> Dict[str, Any]:
    if not candidates:
        raise RuntimeError('候选服务为空')
    ranked = sorted(candidates, key=lambda svc: float(svc.get('price_per_unit') or 0.0) - float(svc.get('trust_score') or 0.0) * 0.05)
    return ranked[0]


def choose_simple_rule_service(candidates: List[Dict[str, Any]]) -> Dict[str, Any]:
    if not candidates:
        raise RuntimeError('候选服务为空')
    ranked = sorted(
        candidates,
        key=lambda svc: (
            float(svc.get('price_per_unit') or 0.0),
            float(svc.get('trust_score') or 0.0) * -1,
        ),
    )
    return ranked[0]


def choose_basic_resolution_service(candidates: List[Dict[str, Any]]) -> Dict[str, Any]:
    if not candidates:
        raise RuntimeError('候选服务为空')
    return candidates[0]


def choose_vector_enhanced_service(candidates: List[Dict[str, Any]]) -> Dict[str, Any]:
    if not candidates:
        raise RuntimeError('候选服务为空')
    return candidates[0]


def choose_trust_feedback_service(candidates: List[Dict[str, Any]]) -> Dict[str, Any]:
    if not candidates:
        raise RuntimeError('候选服务为空')
    ranked = sorted(candidates, key=lambda svc: float(svc.get('trust_score') or 0.0), reverse=True)
    return ranked[0]


def choose_full_multi_step_service(candidates: List[Dict[str, Any]]) -> Dict[str, Any]:
    if not candidates:
        raise RuntimeError('候选服务为空')
    def score(svc: Dict[str, Any]) -> float:
        trust = float(svc.get('trust_score') or 0.0)
        price = float(svc.get('price_per_unit') or 0.0)
        return trust - price * 15.0
    return sorted(candidates, key=score, reverse=True)[0]
