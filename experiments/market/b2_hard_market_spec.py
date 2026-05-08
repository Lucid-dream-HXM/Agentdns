B2_HARD_MARKET_NAME = "b2_hard_inclass_deception_market_v1"
B2_HARD_TOTAL_SERVICES = 100

CATEGORY_LAYOUT = {
    "translation": {
        "平衡实用型": 8,
        "领域专精型": 6,
        "低价基础型": 4,
        "低时延响应型": 2,
        "诱骗失真型": 8,
        "漂移波动型": 1,
        "故障脆弱型": 1,
    },
    "text_summary": {
        "平衡实用型": 8,
        "领域专精型": 6,
        "低价基础型": 4,
        "低时延响应型": 2,
        "诱骗失真型": 8,
        "漂移波动型": 1,
        "故障脆弱型": 1,
    },
    "structured_extraction": {
        "平衡实用型": 8,
        "领域专精型": 6,
        "低价基础型": 4,
        "低时延响应型": 2,
        "诱骗失真型": 8,
        "漂移波动型": 1,
        "故障脆弱型": 1,
    },
    "routing_classification": {
        "平衡实用型": 4,
        "低价基础型": 2,
        "诱骗失真型": 2,
        "领域专精型": 2,
    },
}

PROFILE_RULES = {
    "平衡实用型": {
        "price_range": (0.060, 0.078),
        "latency_range_ms": (650, 1100),
        "quality_range": (0.84, 0.93),
        "consumability_range": (0.86, 0.94),
        "format_stability_range": (0.86, 0.94),
        "failure_probability_range": (0.01, 0.04),
        "drift_probability_range": (0.01, 0.03),
        "trust_seed_range": (88.0, 94.0),
        "rating_count_range": (8, 20),
    },
    "领域专精型": {
        "price_range": (0.072, 0.095),
        "latency_range_ms": (720, 1250),
        "quality_range": (0.86, 0.95),
        "consumability_range": (0.87, 0.95),
        "format_stability_range": (0.87, 0.95),
        "failure_probability_range": (0.01, 0.03),
        "drift_probability_range": (0.01, 0.03),
        "trust_seed_range": (89.0, 95.0),
        "rating_count_range": (10, 24),
    },
    "低价基础型": {
        "price_range": (0.018, 0.033),
        "latency_range_ms": (600, 980),
        "quality_range": (0.72, 0.82),
        "consumability_range": (0.78, 0.86),
        "format_stability_range": (0.78, 0.86),
        "failure_probability_range": (0.03, 0.08),
        "drift_probability_range": (0.02, 0.05),
        "trust_seed_range": (82.0, 90.0),
        "rating_count_range": (5, 15),
    },
    "低时延响应型": {
        "price_range": (0.028, 0.045),
        "latency_range_ms": (280, 620),
        "quality_range": (0.74, 0.84),
        "consumability_range": (0.79, 0.87),
        "format_stability_range": (0.78, 0.86),
        "failure_probability_range": (0.03, 0.07),
        "drift_probability_range": (0.03, 0.06),
        "trust_seed_range": (82.0, 89.0),
        "rating_count_range": (5, 14),
    },
    "诱骗失真型": {
        "price_range": (0.024, 0.052),
        "latency_range_ms": (420, 900),
        "quality_range": (0.76, 0.86),
        "consumability_range": (0.74, 0.84),
        "format_stability_range": (0.74, 0.83),
        "failure_probability_range": (0.03, 0.08),
        "drift_probability_range": (0.03, 0.08),
        "trust_seed_range": (76.0, 86.0),
        "rating_count_range": (6, 18),
    },
    "漂移波动型": {
        "price_range": (0.055, 0.075),
        "latency_range_ms": (680, 1150),
        "quality_range": (0.80, 0.90),
        "consumability_range": (0.76, 0.88),
        "format_stability_range": (0.72, 0.86),
        "failure_probability_range": (0.02, 0.06),
        "drift_probability_range": (0.08, 0.18),
        "trust_seed_range": (74.0, 84.0),
        "rating_count_range": (4, 12),
    },
    "故障脆弱型": {
        "price_range": (0.040, 0.068),
        "latency_range_ms": (600, 1100),
        "quality_range": (0.72, 0.84),
        "consumability_range": (0.70, 0.82),
        "format_stability_range": (0.70, 0.82),
        "failure_probability_range": (0.08, 0.18),
        "drift_probability_range": (0.02, 0.06),
        "trust_seed_range": (70.0, 82.0),
        "rating_count_range": (4, 10),
    },
}

CATEGORY_SUBINTENTS = {
    "translation": [
        "中译英",
        "英译中",
        "术语一致",
        "会议纪要翻译",
        "产品说明翻译",
        "技术文档翻译",
    ],
    "text_summary": [
        "短摘要",
        "结论导向摘要",
        "项目过程摘要",
        "高信息密度摘要",
        "研究摘要",
        "服务说明摘要",
    ],
    "structured_extraction": [
        "实体抽取",
        "会议字段抽取",
        "实验字段抽取",
        "工单字段抽取",
        "项目周报抽取",
        "研究要素抽取",
    ],
    "routing_classification": [
        "办公室任务分类",
        "工单路由",
        "请求路由",
        "规则判别",
    ],
}

DESCRIPTION_TEMPLATES = {
    ("translation", "平衡实用型"): [
        "翻译平衡服务{idx}，擅长中英互译、会议纪要翻译、技术术语保持，输出稳定，适合通用翻译任务。",
        "翻译实用服务{idx}，支持中译英、英译中、多语转换，兼顾质量与成本，适合常规文档翻译。",
    ],
    ("translation", "领域专精型"): [
        "翻译专精服务{idx}，专注技术文档翻译、术语一致性与研发说明翻译，适合专业文本场景。",
        "术语翻译服务{idx}，强化术语保持、技术说明翻译与产品描述转换，适合专业英文写作。",
    ],
    ("translation", "低价基础型"): [
        "经济翻译服务{idx}，适合常规中英互译和基础文本转换，成本低，适合预算敏感场景。",
    ],
    ("translation", "低时延响应型"): [
        "快速翻译服务{idx}，响应迅速，适合短句翻译、即时中英转换和轻量文本处理。",
    ],
    ("translation", "诱骗失真型"): [
        "增强翻译服务{idx}，强调术语一致，自然流畅与多场景适配，价格友好，适合技术文档与产品文案翻译。",
        "翻译专家服务{idx}，主打技术术语保持、会议纪要翻译和多语兼容，适合高频翻译请求。",
    ],
    ("text_summary", "平衡实用型"): [
        "摘要平衡服务{idx}，支持长文本压缩、项目摘要、研究摘要和高信息密度总结，输出稳定。",
    ],
    ("text_summary", "领域专精型"): [
        "摘要专精服务{idx}，强化结论抽取、结构化压缩和技术材料摘要，适合研究与项目材料。",
    ],
    ("text_summary", "低价基础型"): [
        "经济摘要服务{idx}，适合基础文本压缩、简要摘要与通用信息提炼，成本较低。",
    ],
    ("text_summary", "低时延响应型"): [
        "快速摘要服务{idx}，擅长短文本即时摘要、三句摘要和要点快速压缩。",
    ],
    ("text_summary", "诱骗失真型"): [
        "增强摘要服务{idx}，主打高信息密度压缩、研究摘要和服务说明提炼，价格友好，适合高频摘要请求。",
        "摘要专家服务{idx}，强调结论突出、结构清晰和项目材料摘要，适合报告与说明文档。",
    ],
    ("structured_extraction", "平衡实用型"): [
        "抽取平衡服务{idx}，支持实体抽取、会议字段抽取、实验字段提取和工单信息抽取，输出稳定。",
    ],
    ("structured_extraction", "领域专精型"): [
        "抽取专精服务{idx}，强化实体识别、字段映射和研究/实验要素提取，适合结构化处理场景。",
    ],
    ("structured_extraction", "低价基础型"): [
        "经济抽取服务{idx}，适合基础字段抽取、实体识别和轻量结构化处理，成本较低。",
    ],
    ("structured_extraction", "低时延响应型"): [
        "快速抽取服务{idx}，适合会议要素提取、实体抽取和轻量字段识别，响应较快。",
    ],
    ("structured_extraction", "诱骗失真型"): [
        "增强抽取服务{idx}，强调字段完整、实体识别准确和项目要素提取，价格友好，适合高频结构化任务。",
        "抽取专家服务{idx}，主打会议字段、实验字段和研究对象提取，适合复杂文段处理。",
    ],
    ("routing_classification", "平衡实用型"): [
        "路由平衡服务{idx}，适合请求分类、任务归类与规则判定，适合通用路由场景。",
    ],
    ("routing_classification", "领域专精型"): [
        "路由专精服务{idx}，强化工单分类、请求路由和流程判别，适合复杂判别任务。",
    ],
    ("routing_classification", "低价基础型"): [
        "经济路由服务{idx}，适合基础请求分类与规则路由，成本较低。",
    ],
    ("routing_classification", "诱骗失真型"): [
        "增强路由服务{idx}，强调智能判别、快速分流与多规则适配，适合常规任务分类。",
    ],
}

CATEGORY_TAGS = {
    "translation": ["中英互译", "英译中", "术语一致", "技术文档翻译", "会议纪要翻译", "产品说明翻译"],
    "text_summary": ["文本摘要", "结论压缩", "研究摘要", "项目摘要", "高密度摘要", "服务说明压缩"],
    "structured_extraction": ["结构化抽取", "实体抽取", "会议字段", "实验字段", "工单字段", "项目要素提取"],
    "routing_classification": ["请求分类", "工单路由", "规则判别", "任务分类"],
}

FORMAL_TASK_COUNT = 120
FORMAL_TASKS_PER_CATEGORY = {
    "translation": 40,
    "text_summary": 40,
    "structured_extraction": 40,
}
