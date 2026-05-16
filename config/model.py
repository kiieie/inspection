"""AI 모델 경로 및 VLM 백엔드 연결 설정"""
import os
from pathlib import Path
from config.env import VLM_BACKEND

_ROOT = Path(__file__).parent.parent

MODEL_CONFIG = {
    "classifier": _ROOT / "models" / "classifier" / "weights" / "best.pt",
    "ag_pose": _ROOT / "models" / "ag_inspector" / "weights" / "best.pt",
}

VLM_CONFIG = {
    "use_backend": VLM_BACKEND,
    "ollama": {
        "api_url": os.getenv("OLLAMA_API_URL", "http://localhost:11434/api/generate"),
        "model": os.getenv("OLLAMA_MODEL", "qwen3-vl:8b"),
        "stream": False,
    },
    "trtllm": {
        "model_urls": {
            "4b": os.getenv("TRTLLM_URL_4B", "http://10.52.194.208:18080/qwen3_vl/4b/infer"),
            "8b": os.getenv("TRTLLM_URL_8B", "http://10.52.194.208:18080/qwen3_vl/8b/infer"),
        },
        "default_model": os.getenv("TRTLLM_DEFAULT_MODEL", "8b"),
    },
}

DG_VLM_CONFIG = {
    "use_backend": VLM_BACKEND,
    "ollama": {
        "api_url": os.getenv("OLLAMA_API_URL", "http://localhost:11434/api/generate"),
        "model": os.getenv("OLLAMA_MODEL", "qwen3-vl:8b"),
        "stream": False,
        "temperature": 0.0,
    },
    "trtllm": {
        "model_urls": {
            "8b": os.getenv("TRTLLM_URL_8B", "http://10.52.194.208:18080/qwen3_vl/8b/infer"),
        },
        "default_model": "8b",
    },
}
