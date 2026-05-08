
B3_DRIFT_MARKET_NAME = "b3_drift_inclass_market_v1"
B3_DRIFT_TOTAL_SERVICES = 100

CATEGORY_LAYOUT = {
    "translation": {
        "平衡实用型": 10,
        "领域专精型": 10,
        "漂移波动型": 10,
    },
    "text_summary": {
        "平衡实用型": 10,
        "领域专精型": 10,
        "漂移波动型": 10,
    },
    "structured_extraction": {
        "平衡实用型": 10,
        "领域专精型": 10,
        "漂移波动型": 10,
    },
    "routing_classification": {
        "平衡实用型": 5,
        "领域专精型": 5,
    },
}

PROFILE_RULES = {
    "平衡实用型": {
        "price_range": (0.062, 0.078),
        "latency_range_ms": (650, 980),
        "quality_range": (0.84, 0.91),
        "consumability_range": (0.86, 0.92),
        "format_stability_range": (0.86, 0.92),
        "failure_probability_range": (0.01, 0.03),
        "drift_probability_range": (0.01, 0.02),
        "trust_seed_range": (84.0, 86.0),
        "rating_count_range": (5, 8),
    },
    "领域专精型": {
        "price_range": (0.074, 0.090),
        "latency_range_ms": (700, 1050),
        "quality_range": (0.86, 0.94),
        "consumability_range": (0.88, 0.94),
        "format_stability_range": (0.88, 0.94),
        "failure_probability_range": (0.01, 0.03),
        "drift_probability_range": (0.01, 0.02),
        "trust_seed_range": (86.0, 88.0),
        "rating_count_range": (5, 8),
    },
    "低价基础型": {
        "price_range": (0.018, 0.034),
        "latency_range_ms": (600, 980),
        "quality_range": (0.72, 0.82),
        "consumability_range": (0.78, 0.86),
        "format_stability_range": (0.78, 0.86),
        "failure_probability_range": (0.03, 0.08),
        "drift_probability_range": (0.02, 0.05),
        "trust_seed_range": (80.0, 88.0),
        "rating_count_range": (5, 15),
    },
    "低时延响应型": {
        "price_range": (0.026, 0.046),
        "latency_range_ms": (280, 620),
        "quality_range": (0.74, 0.84),
        "consumability_range": (0.79, 0.87),
        "format_stability_range": (0.78, 0.86),
        "failure_probability_range": (0.03, 0.07),
        "drift_probability_range": (0.03, 0.06),
        "trust_seed_range": (80.0, 88.0),
        "rating_count_range": (5, 14),
    },
    "诱骗失真型": {
        "price_range": (0.024, 0.050),
        "latency_range_ms": (420, 900),
        "quality_range": (0.76, 0.86),
        "consumability_range": (0.74, 0.84),
        "format_stability_range": (0.74, 0.83),
        "failure_probability_range": (0.03, 0.08),
        "drift_probability_range": (0.03, 0.08),
        "trust_seed_range": (78.0, 86.0),
        "rating_count_range": (6, 18),
    },
    "漂移波动型": {
        "price_range": (0.062, 0.076),
        "latency_range_ms": (620, 960),
        "quality_range": (0.84, 0.92),
        "consumability_range": (0.84, 0.92),
        "format_stability_range": (0.84, 0.92),
        "failure_probability_range": (0.02, 0.05),
        "drift_probability_range": (0.10, 0.18),
        "trust_seed_range": (86.0, 88.0),
        "rating_count_range": (1, 2),
    },
    "故障脆弱型": {
        "price_range": (0.040, 0.068),
        "latency_range_ms": (620, 1100),
        "quality_range": (0.72, 0.84),
        "consumability_range": (0.70, 0.82),
        "format_stability_range": (0.70, 0.82),
        "failure_probability_range": (0.08, 0.18),
        "drift_probability_range": (0.02, 0.06),
        "trust_seed_range": (72.0, 82.0),
        "rating_count_range": (4, 10),
    },
}

DRIFT_MODES = ["phase_down", "slow_decay"]

DRIFT_PHASE_RULES = {
    "phase_down": {
        "phase_quality": [0.92, 0.80, 0.64],
        "phase_consumability": [0.91, 0.79, 0.62],
        "phase_format_stability": [0.91, 0.78, 0.60],
    },
    "slow_decay": {
        "phase_quality": [0.90, 0.84, 0.76],
        "phase_consumability": [0.89, 0.83, 0.75],
        "phase_format_stability": [0.89, 0.82, 0.74],
    },
}

CATEGORY_SUBINTENTS = {
    "translation": ["中译英","英译中","术语一致","会议纪要翻译","产品说明翻译","技术文档翻译"],
    "text_summary": ["结论导向摘要","项目过程摘要","高密度压缩摘要","研究摘要","服务说明摘要","会议纪要摘要"],
    "structured_extraction": ["实体抽取","会议字段抽取","实验字段抽取","工单字段抽取","项目周报抽取","研究要素抽取"],
    "routing_classification": ["办公室任务分类","工单路由","请求路由","规则判别"],
}

CATEGORY_TAGS = {
    "translation": ["中英互译","英译中","术语一致","技术文档翻译","会议纪要翻译","产品说明翻译"],
    "text_summary": ["文本摘要","结论压缩","研究摘要","项目摘要","高密度摘要","服务说明压缩"],
    "structured_extraction": ["结构化抽取","实体抽取","会议字段","实验字段","工单字段","项目要素提取"],
    "routing_classification": ["请求分类","工单路由","规则判别","任务分类"],
}

DESCRIPTION_TEMPLATES = {
    ("translation", "平衡实用型"): ["翻译平衡服务{idx}，擅长中英互译、会议纪要翻译、技术术语保持，适合通用翻译任务。","翻译实用服务{idx}，支持中译英、英译中与多语转换，兼顾质量与成本。"],
    ("translation", "领域专精型"): ["翻译专精服务{idx}，专注技术文档翻译、术语一致性与研发说明翻译。","术语翻译服务{idx}，强化专业术语保持与技术材料翻译。"],
    ("translation", "低价基础型"): ["经济翻译服务{idx}，适合常规中英互译与基础文本转换，成本较低。"],
    ("translation", "低时延响应型"): ["快速翻译服务{idx}，适合短句翻译和即时文本处理。"],
    ("translation", "诱骗失真型"): ["增强翻译服务{idx}，强调术语一致、自然流畅与多场景适配，价格友好，适合技术文档与产品文案翻译。","翻译专家服务{idx}，主打术语保持、会议纪要翻译和多语兼容，适合高频翻译请求。"],
    ("translation", "漂移波动型"): ["翻译增强服务{idx}，擅长将中文翻译成英文、将英文翻译成中文、保持术语一致，适合技术说明、会议纪要和产品说明翻译。","翻译专业服务{idx}，适合中译英、英译中、API 术语保持、技术文档翻译与项目说明翻译。"],
    ("translation", "故障脆弱型"): ["翻译脆弱服务{idx}，适合轻量翻译请求，但在复杂场景下稳定性一般。"],
    ("text_summary", "平衡实用型"): ["摘要平衡服务{idx}，支持长文本压缩、项目摘要、研究摘要和高信息密度总结。"],
    ("text_summary", "领域专精型"): ["摘要专精服务{idx}，强化结论抽取、结构压缩和技术材料摘要。"],
    ("text_summary", "低价基础型"): ["经济摘要服务{idx}，适合基础文本压缩、简要摘要与通用信息提炼。"],
    ("text_summary", "低时延响应型"): ["快速摘要服务{idx}，适合短文本即时摘要和要点快速压缩。"],
    ("text_summary", "诱骗失真型"): ["增强摘要服务{idx}，主打高信息密度压缩、研究摘要和服务说明提炼，价格友好。","摘要专家服务{idx}，强调结论突出、结构清晰和项目材料摘要。"],
    ("text_summary", "漂移波动型"): ["摘要增强服务{idx}，适合长文本摘要、项目说明压缩、研究背景摘要、会议纪要摘要和结果总结。","摘要专业服务{idx}，擅长生成简洁摘要、压缩成三句摘要、突出目标方法结果和高信息密度总结。"],
    ("text_summary", "故障脆弱型"): ["摘要脆弱服务{idx}，适合基础压缩任务，但复杂摘要时稳定性一般。"],
    ("structured_extraction", "平衡实用型"): ["抽取平衡服务{idx}，支持实体抽取、会议字段抽取、实验字段提取和工单信息抽取。"],
    ("structured_extraction", "领域专精型"): ["抽取专精服务{idx}，强化实体识别、字段映射和研究/实验要素提取。"],
    ("structured_extraction", "低价基础型"): ["经济抽取服务{idx}，适合基础字段抽取、实体识别和轻量结构化处理。"],
    ("structured_extraction", "低时延响应型"): ["快速抽取服务{idx}，适合会议要素提取、实体抽取和轻量字段识别。"],
    ("structured_extraction", "诱骗失真型"): ["增强抽取服务{idx}，强调字段完整、实体识别准确和项目要素提取，价格友好。","抽取专家服务{idx}，主打会议字段、实验字段和研究对象提取。"],
    ("structured_extraction", "漂移波动型"): ["抽取增强服务{idx}，适合抽取时间地点人物事件、会议主题负责人截止日期、模型数据集指标和工单字段。","抽取专业服务{idx}，擅长实体抽取、会议字段抽取、实验字段提取、项目周报抽取和服务说明结构化。"],
    ("structured_extraction", "故障脆弱型"): ["抽取脆弱服务{idx}，适合基础字段抽取，但复杂结构化任务下稳定性一般。"],
    ("routing_classification", "平衡实用型"): ["路由平衡服务{idx}，适合请求分类、任务归类与规则判定，适合通用路由场景。"],
    ("routing_classification", "领域专精型"): ["路由专精服务{idx}，强化工单分类、请求路由和流程判别。"],
    ("routing_classification", "低价基础型"): ["经济路由服务{idx}，适合基础请求分类与规则路由，成本较低。"],
    ("routing_classification", "漂移波动型"): ["路由增强服务{idx}，初始适合请求分类、规则判别与工单分流场景。"],
}
