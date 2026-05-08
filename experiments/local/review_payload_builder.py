
from __future__ import annotations
import re
from typing import Any, Dict, Optional, Tuple

def _http_outcome(call_data: Dict[str, Any]) -> str:
    status = str(call_data.get("status") or "").lower().strip()
    if status in {"success", "partial", "fail", "failed"}:
        return "fail" if status == "failed" else status
    return "success"

def _profile_and_behavior(selected_service: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
    capabilities = selected_service.get("capabilities") or {}
    profile_name = str(capabilities.get("profile_name") or "")
    mock_behavior = capabilities.get("mock_behavior") or {}
    return profile_name, mock_behavior

def _extract_phase_id(task_id: Optional[str]) -> Optional[int]:
    if not task_id:
        return None
    s = str(task_id).lower()
    for pattern in [r"b3p([123])", r"phase[_-]?([123])", r"b3[_-]?phase[_-]?([123])"]:
        m = re.search(pattern, s)
        if m:
            return int(m.group(1))
    return None

def _phase_value(values: Any, phase_id: Optional[int], default_value: float) -> float:
    if phase_id is None:
        return float(default_value)
    if isinstance(values, list) and len(values) >= phase_id:
        return float(values[phase_id - 1])
    return float(default_value)

def _derive_drift_effective_outcome(mock_behavior: Dict[str, Any], phase_id: Optional[int]) -> Tuple[str, int, int, int, bool]:
    base_quality_range = mock_behavior.get("quality_range") or [0.84, 0.90]
    quality_mean = (float(base_quality_range[0]) + float(base_quality_range[1])) / 2.0 if isinstance(base_quality_range, list) and len(base_quality_range) == 2 else 0.87

    base_consumability = float(mock_behavior.get("consumability") or 0.88)
    base_format = float(mock_behavior.get("format_stability") or 0.88)

    quality = _phase_value(mock_behavior.get("phase_quality"), phase_id, quality_mean)
    consumability = _phase_value(mock_behavior.get("phase_consumability"), phase_id, base_consumability)
    format_stability = _phase_value(mock_behavior.get("phase_format_stability"), phase_id, base_format)

    if quality < 0.72 or consumability < 0.72 or format_stability < 0.72:
        return "fail", 1, 1, 1, False

    if quality < 0.80 or consumability < 0.80 or format_stability < 0.80:
        return "partial", 2, 2, 2, False

    if quality < 0.86 or consumability < 0.86 or format_stability < 0.86:
        return "partial", 3, 3, 3, False

    return "success", 4, 4, 4, True

def _derive_effective_outcome(selected_service: Dict[str, Any], call_data: Dict[str, Any], task_id: Optional[str]) -> Tuple[str, int, int, int, bool]:
    http_outcome = _http_outcome(call_data)
    if http_outcome == "fail":
        return "fail", 1, 1, 1, False
    profile_name, mock_behavior = _profile_and_behavior(selected_service)
    consumability = float(mock_behavior.get("consumability") or 1.0)
    format_stability = float(mock_behavior.get("format_stability") or 1.0)
    quality_range = mock_behavior.get("quality_range") or [0.8, 0.9]
    quality_mean = (float(quality_range[0]) + float(quality_range[1])) / 2.0 if isinstance(quality_range, list) and len(quality_range) == 2 else 0.85
    phase_id = _extract_phase_id(task_id)
    if profile_name == "漂移波动型":
        return _derive_drift_effective_outcome(mock_behavior, phase_id)
    if profile_name == "诱骗失真型":
        if consumability < 0.78 or format_stability < 0.82:
            return "fail", 1, 1, 2, False
        return "partial", 2, 2, 3, False
    if profile_name in {"低价基础型", "低时延响应型"}:
        if consumability < 0.82 or format_stability < 0.85 or quality_mean < 0.78:
            return "partial", 3, 2, 3, False
        return "success", 4, 3, 4, True
    if profile_name in {"平衡实用型", "领域专精型", "旗舰通用型"}:
        if quality_mean >= 0.86 and consumability >= 0.86 and format_stability >= 0.86:
            return "success", 5, 5, 5, True
        if quality_mean >= 0.80 and consumability >= 0.80 and format_stability >= 0.80:
            return "success", 5, 4, 5, True
        return "partial", 4, 3, 4, True
    if profile_name == "故障脆弱型":
        if consumability < 0.8 or format_stability < 0.8:
            return "fail", 1, 1, 2, False
        return "partial", 3, 2, 3, False
    return "success", 4, 4, 4, True

def build_review_payload(*, usage_id: int, selected_service: Dict[str, Any], call_data: Dict[str, Any], group_name: str, task_id: Optional[str] = None, step_id: Optional[int] = None) -> Dict[str, Any]:
    service_id = selected_service.get("id")
    service_name = selected_service.get("name", "unknown_service")
    profile_name, mock_behavior = _profile_and_behavior(selected_service)
    effective_outcome, task_fit, output_quality, protocol_adherence, would_reuse = _derive_effective_outcome(selected_service, call_data, task_id)
    rating = int(round((task_fit + output_quality + protocol_adherence) / 3))
    rating = max(1, min(5, rating))
    phase_id = _extract_phase_id(task_id)
    comment = f"{group_name} 自动评价：{service_name} | profile={profile_name or 'unknown'} | phase={phase_id} | effective_outcome={effective_outcome} | cons={mock_behavior.get('consumability')} | fmt={mock_behavior.get('format_stability')} | drift_mode={mock_behavior.get('drift_mode')}"
    payload = {
        "service_id": service_id,
        "usage_id": usage_id,
        "outcome": effective_outcome,
        "rating": rating,
        "comment": comment,
        "task_fit": task_fit,
        "output_quality": output_quality,
        "protocol_adherence": protocol_adherence,
        "would_reuse": would_reuse,
    }
    if task_id is not None or step_id is not None:
        payload["task_context"] = {"task_id": task_id, "step_id": step_id}
    return payload
