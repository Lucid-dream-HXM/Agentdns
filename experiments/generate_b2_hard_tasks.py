from __future__ import annotations

import json
from pathlib import Path

ROOT = Path("/home/hxm/projects/AgentDNS")
OUT = ROOT / "experiments" / "outputs" / "b2_hard_120tasks.json"

tasks = []

translation_prompts = [
    "将这段中文翻译成英文，并保持术语一致：人工智能正在改变软件系统的设计方式。",
    "将这段英文翻译成中文：Trust-aware routing can improve service selection quality.",
    "请将下列技术说明翻译为英文，并保持术语一致。",
    "将以下中文会议纪要要点翻译为英文：系统稳定性、服务发现、信任反馈。",
    "请把下面这句产品说明翻译成英文，要求自然流畅。",
    "请把以下英文实验描述翻译成中文，并保留专业术语。",
    "将以下中文研发说明翻译为英文：该系统支持同步、流式与异步调用。",
    "请把这句英文会议结论翻译为中文：The trust signal should not dominate semantic relevance.",
    "将以下中文接口说明翻译为英文，并保留 API 术语。",
    "请将这段英文项目说明翻译为中文，保持技术语气。",
]

summary_prompts = [
    "请对以下长文本进行摘要，保留核心观点与结论。",
    "请生成一段简洁摘要，突出任务目标、方法和结果。",
    "对这段描述生成摘要，要求语言简洁、信息密度高。",
    "请把以下项目说明压缩成三句摘要。",
    "请总结下面这段系统设计说明，突出模块关系。",
    "请把以下研究背景压缩成一段摘要，要求保留问题与贡献。",
    "请对以下的实验记录做摘要，重点突出对比结果。",
    "请将以下服务描述压缩为两句，保留适用场景与限制。",
    "请对以下会议纪要进行摘要，保留决策与待办事项。",
    "请把下面这段产品说明压缩为一段简洁摘要。",
]

extract_prompts = [
    "从文本中抽取时间、地点、人物、事件，输出为结构化字段。",
    "识别文中的组织名、金额、日期和关键动作。",
    "从以下段落抽取会议主题、负责人和截止日期。",
    "请从文本中抽取研究对象、方法、结果和结论。",
    "请抽取工单中的问题类型、优先级、责任人和处理状态。",
    "从通知文本中抽取部门、时间、会议地点和参与对象。",
    "请抽取实验描述中的模型名称、数据集、指标和结论。",
    "从项目周报中抽取里程碑、延期原因、负责人和下一步计划。",
    "从服务说明中抽取功能、输入、输出和限制条件。",
    "请从会议纪要中抽取决议项、负责人、截止日期和风险点。",
]

for i in range(40):
    base = translation_prompts[i % len(translation_prompts)]
    tasks.append({
        "task_id": f"b2h_translation_{i+1:03d}",
        "scenario_family": "b2_hard",
        "complexity_level": "L1",
        "task_goal": "翻译任务",
        "task_prompt": base,
        "required_service_categories": ["translation"],
    })

for i in range(40):
    base = summary_prompts[i % len(summary_prompts)]
    tasks.append({
        "task_id": f"b2h_summary_{i+1:03d}",
        "scenario_family": "b2_hard",
        "complexity_level": "L1",
        "task_goal": "文本摘要",
        "task_prompt": base,
        "required_service_categories": ["text_summary"],
    })

for i in range(40):
    base = extract_prompts[i % len(extract_prompts)]
    tasks.append({
        "task_id": f"b2h_extract_{i+1:03d}",
        "scenario_family": "b2_hard",
        "complexity_level": "L1",
        "task_goal": "结构化抽取",
        "task_prompt": base,
        "required_service_categories": ["structured_extraction"],
    })

OUT.write_text(json.dumps({"tasks": tasks}, ensure_ascii=False, indent=2), encoding="utf-8")
print(OUT)
print(f"task_count={len(tasks)}")
