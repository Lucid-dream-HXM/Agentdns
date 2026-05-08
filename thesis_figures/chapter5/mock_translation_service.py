from datetime import datetime
from typing import Any, Dict

from fastapi import FastAPI
from pydantic import BaseModel


app = FastAPI(title="AgentDNS Mock Translation Service")


class TranslateRequest(BaseModel):
    text: str
    source_lang: str = "zh"
    target_lang: str = "en"
    task_id: str = "demo"


@app.post("/translate")
async def translate(payload: TranslateRequest) -> Dict[str, Any]:
    dictionary = {
        "面向LLM多智能体的根域名解析系统": "Root domain resolution system for LLM multi-agent services",
        "查找可用于文本翻译的服务": "Find services for text translation",
    }
    translated = dictionary.get(payload.text, f"[{payload.target_lang}] {payload.text}")
    return {
        "status": "success",
        "provider": "mock-translation-upstream",
        "task_id": payload.task_id,
        "input": {
            "text": payload.text,
            "source_lang": payload.source_lang,
            "target_lang": payload.target_lang,
        },
        "result": {
            "translated_text": translated,
            "quality": "demo",
        },
        "completed_at": datetime.utcnow().isoformat(timespec="seconds") + "Z",
    }


@app.get("/health")
async def health() -> Dict[str, str]:
    return {"status": "healthy"}
