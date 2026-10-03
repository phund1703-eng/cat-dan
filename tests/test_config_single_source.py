"""
tests/test_config_single_source.py — Task 5.2: một nguồn cấu hình duy nhất.

Nghiệm thu: đổi model trong settings.yaml (file tạm qua CATDAN_SETTINGS_FILE)
→ GeminiClient (dùng bởi cả ScriptGenerator lẫn MetadataGenerator) và
TTSManager đều thấy model/cấu hình mới qua core.config.get_settings();
biến môi trường GEMINI_MODEL/GEMINI_PRO_MODEL là override thắng settings.
"""

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core import config as core_config  # noqa: E402

CUSTOM_SETTINGS = """\
llm:
  provider: gemini
  model: gemini-unit-test-x
  pro_model: gemini-unit-test-pro
tts:
  primary_engine: edge
queue:
  max_concurrent_jobs: 7
"""


@pytest.fixture()
def custom_settings(tmp_path, monkeypatch):
    settings_file = tmp_path / "settings.yaml"
    settings_file.write_text(CUSTOM_SETTINGS, encoding="utf-8")
    monkeypatch.setenv(core_config.SETTINGS_PATH_ENV, str(settings_file))
    # env override Gemini phải trống để không thắng settings trong test này;
    # (để "" thay vì delenv để load_dotenv không nạp lại từ .env)
    monkeypatch.setenv("GEMINI_MODEL", "")
    monkeypatch.setenv("GEMINI_PRO_MODEL", "")
    core_config.clear_settings_cache()
    yield settings_file
    core_config.clear_settings_cache()


def test_get_settings_reads_custom_file(custom_settings):
    settings = core_config.get_settings()
    assert settings["llm"]["model"] == "gemini-unit-test-x"
    assert core_config.get_setting("llm.pro_model") == "gemini-unit-test-pro"
    assert core_config.get_setting("queue.max_concurrent_jobs") == 7
    assert core_config.get_setting("khong.co.key.nay", "mac-dinh") == "mac-dinh"


def test_get_gemini_model_from_settings(custom_settings):
    assert core_config.get_gemini_model() == "gemini-unit-test-x"
    assert core_config.get_gemini_model(pro=True) == "gemini-unit-test-pro"


def test_gemini_client_follows_settings(custom_settings):
    from core.script_engine.gemini_client import GeminiClient

    client = GeminiClient()
    assert client.default_model == "gemini-unit-test-x"
    assert client.pro_model == "gemini-unit-test-pro"
    assert client.fallback_models[0] == "gemini-unit-test-x"


def test_script_and_metadata_generators_share_settings_model(custom_settings):
    from core.script_engine.script_generator import ScriptGenerator
    from publish.metadata_generator import MetadataGenerator

    generator = ScriptGenerator()
    assert generator.client.default_model == "gemini-unit-test-x"
    assert generator.client.pro_model == "gemini-unit-test-pro"

    metadata = MetadataGenerator()
    assert metadata.gemini.default_model == "gemini-unit-test-x"


def test_tts_manager_config_comes_from_get_settings(custom_settings):
    from core.tts_engine.tts_manager import TTSManager

    manager = object.__new__(TTSManager)  # bỏ qua __init__ (client TTS nặng)
    loaded = manager._load_config()
    assert loaded["llm"]["model"] == "gemini-unit-test-x"
    assert loaded["tts"]["primary_engine"] == "edge"


def test_queue_max_concurrent_from_settings(custom_settings):
    from dashboard.worker.runner import load_max_concurrent_jobs

    assert core_config.get_queue_max_concurrent_jobs() == 7
    assert load_max_concurrent_jobs() == 7


def test_env_override_wins_over_settings(custom_settings, monkeypatch):
    monkeypatch.setenv("GEMINI_MODEL", "gemini-env-override")
    assert core_config.get_gemini_model() == "gemini-env-override"

    from core.script_engine.gemini_client import GeminiClient

    assert GeminiClient().default_model == "gemini-env-override"


def test_repo_settings_default_model(monkeypatch):
    """settings.yaml thật của repo phải khớp model mặc định mà
    test_gemini_client_empirical kỳ vọng (gemini-3.8-flash)."""
    monkeypatch.delenv(core_config.SETTINGS_PATH_ENV, raising=False)
    monkeypatch.setenv("GEMINI_MODEL", "")
    monkeypatch.setenv("GEMINI_PRO_MODEL", "")
    core_config.clear_settings_cache()
    try:
        assert core_config.get_gemini_model() == "gemini-3.8-flash"
        assert core_config.get_gemini_model(pro=True) == "gemini-3.8-flash"
    finally:
        core_config.clear_settings_cache()
