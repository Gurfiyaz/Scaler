"""Production Configuration & Deployment Readiness Unit Tests."""

import os
from pathlib import Path
import pytest
from app.core.config import Settings


def test_production_environment_debug_flag_default():
    # Production env should default debug to False
    os.environ["APP_ENV"] = "production"
    if "APP_DEBUG" in os.environ:
        del os.environ["APP_DEBUG"]
    
    prod_settings = Settings()
    assert prod_settings.app_env == "production"
    assert prod_settings.debug is False
    
    # Restore dev env
    os.environ["APP_ENV"] = "development"


def test_port_environment_variable_override():
    os.environ["PORT"] = "10000"
    custom_settings = Settings()
    assert custom_settings.port == 10000
    del os.environ["PORT"]


def test_deployment_manifest_files_exist():
    repo_root = Path(__file__).parent.parent.parent
    render_yaml = repo_root / "render.yaml"
    procfile = repo_root / "Procfile"
    env_example = repo_root / ".env.example"

    assert render_yaml.exists()
    assert procfile.exists()
    assert env_example.exists()

    render_content = render_yaml.read_text()
    assert "healthCheckPath: /health" in render_content
    assert "python -m spacy download en_core_web_sm" in render_content
    assert "startCommand: uvicorn app.main:app --host 0.0.0.0 --port $PORT" in render_content
