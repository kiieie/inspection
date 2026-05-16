"""config/ 패키지 로드 및 기본값 검증"""
import pytest
from pathlib import Path


def test_env_imports():
    from config.env import BASE_DIR, RESULT_BASE_DIR, DB_PATH, VLM_BACKEND
    assert isinstance(BASE_DIR, Path)
    assert isinstance(RESULT_BASE_DIR, Path)
    assert isinstance(DB_PATH, Path)
    assert VLM_BACKEND in ("ollama", "trtllm")


def test_model_imports():
    from config.model import MODEL_CONFIG, VLM_CONFIG, DG_VLM_CONFIG
    assert "classifier" in MODEL_CONFIG
    assert "ag_pose" in MODEL_CONFIG
    assert "use_backend" in VLM_CONFIG
    assert "use_backend" in DG_VLM_CONFIG


def test_domain_imports():
    from config.domain import LABEL_MAP, VLM_PROMPTS, COLORS, STATUS_MAPPING
    assert isinstance(LABEL_MAP, dict)
    assert len(LABEL_MAP) > 0
    assert "DEFAULT" in VLM_PROMPTS
    assert "PASS" in COLORS


def test_db_models_dir_in_env():
    from config.env import DB_MODELS_DIR, DB_MODELS_FILE
    assert DB_MODELS_FILE == "models.py"
    assert DB_MODELS_DIR.name == "robot-control-system-db"
