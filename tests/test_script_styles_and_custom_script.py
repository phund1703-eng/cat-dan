"""
Unit and Integration tests for Script Styles Presets and Custom Script Input.
"""
import pytest
import tempfile
import os
from pathlib import Path
from fastapi.testclient import TestClient

from core.script_engine.script_style_presets import (
    get_all_script_styles,
    get_script_style_by_id,
    save_script_style,
    delete_script_style
)
from core.script_engine.script_generator import ScriptGenerator
from dashboard.api.main import app
from dashboard.api.database import SessionLocal, get_job, create_tables


@pytest.fixture(scope="module")
def client():
    create_tables()
    return TestClient(app)


def test_script_style_presets_crud():
    # 1. Test get all default presets
    styles = get_all_script_styles()
    assert len(styles) >= 4
    preset_ids = [s["id"] for s in styles]
    assert "storytelling_mystery" in preset_ids
    assert "deep_science" in preset_ids
    assert "humorous_fun" in preset_ids
    assert "quick_viral" in preset_ids

    # 2. Test get by id
    s_mystery = get_script_style_by_id("storytelling_mystery")
    assert s_mystery is not None
    assert "Ly Kỳ" in s_mystery["name"] or "storytelling" in s_mystery["id"]

    # 3. Test saving a new custom style
    custom_style = save_script_style(
        style_id="test_custom_preset",
        name="Giọng Test Đặc Biệt",
        description="Mô tả phong cách thử nghiệm",
        tone_instruction="Nói thật truyền cảm hứng và kịch tính.",
        target_audience="Tester"
    )
    assert custom_style["id"] == "test_custom_preset"
    assert custom_style["name"] == "Giọng Test Đặc Biệt"

    # Verify it exists in list
    fetched = get_script_style_by_id("test_custom_preset")
    assert fetched is not None
    assert fetched["tone_instruction"] == "Nói thật truyền cảm hứng và kịch tính."

    # 4. Test delete custom style
    del_ok = delete_script_style("test_custom_preset")
    assert del_ok is True
    assert get_script_style_by_id("test_custom_preset") is None

    # 5. Cannot delete built-in style
    del_builtin = delete_script_style("storytelling_mystery")
    assert del_builtin is False


def test_parse_custom_script_into_scenes_preserves_text_verbatim():
    generator = ScriptGenerator()
    user_script = (
        "Bạn có biết rằng axit trong dạ dày của bạn mạnh đến mức có thể làm tan chảy cả kim loại? "
        "Tuy nhiên, dạ dày của chính bạn lại không hề bị tiêu hoá bởi lượng axit khủng khiếp này. "
        "Bí mật nằm ở một lớp màng nhầy sinh học đặc biệt, liên tục tái tạo tế bào sau mỗi vài ngày."
    )

    result = generator.parse_custom_script_into_scenes(
        raw_text=user_script,
        topic="Axit dạ dày",
        style="collage_broll",
        language="vi"
    )

    assert result["script_origin"] == "custom_script"
    assert len(result["scenes"]) >= 2

    # Check that words from user script are 100% retained
    reconstructed_text = " ".join([s["voiceover"] for s in result["scenes"]])
    user_words = set(user_script.replace(".", "").replace(",", "").replace("?", "").split())
    reconstructed_words = set(reconstructed_text.replace(".", "").replace(",", "").replace("?", "").split())
    
    assert user_words.issubset(reconstructed_words)

    for scene in result["scenes"]:
        assert scene["duration"] >= 3.0
        assert "image_prompt" in scene
        assert "focal_keyword" in scene
        assert len(scene["focal_keyword"]) > 0


def test_api_script_styles_routes(client):
    # GET /script-styles
    res = client.get("/script-styles")
    assert res.status_code == 200
    styles = res.json()
    assert len(styles) >= 4

    # POST /script-styles
    create_payload = {
        "name": "Phong Cách API Test",
        "description": "API Test",
        "tone_instruction": "Tone hướng dẫn qua API test",
        "target_audience": "Audience"
    }
    res_post = client.post("/script-styles", json=create_payload)
    assert res_post.status_code == 200
    saved = res_post.json()
    assert "tone_instruction" in saved

    style_id = saved["id"]

    # DELETE /script-styles/{style_id}
    res_del = client.delete(f"/script-styles/{style_id}")
    assert res_del.status_code == 200
    assert res_del.json().get("ok") is True


def test_api_create_job_with_custom_script(client):
    custom_text = (
        "Trái đất của chúng ta đang quay quanh mặt trời với vận tốc hơn một trăm nghìn kilômét một giờ. "
        "Nhưng tại sao chúng ta lại không hề cảm nhận thấy sự chuyển động chóng mặt này?"
    )
    payload = {
        "topic": "Vận tốc trái đất",
        "style": "collage_broll",
        "language": "vi",
        "format": "shorts",
        "mode": "step_by_step",
        "script_mode": "custom_script",
        "custom_script_text": custom_text
    }
    res = client.post("/jobs", json=payload)
    assert res.status_code == 200
    data = res.json()
    job_id = data["id"]
    assert data["stage"] == "script_ready"

    # Verify job in DB
    db = SessionLocal()
    try:
        db_job = get_job(db, job_id)
        assert db_job is not None
        assert db_job.pipeline_data["script_origin"] == "custom_script"
        assert len(db_job.pipeline_data["scenes"]) >= 2
    finally:
        db.close()


def test_api_initialize_script_endpoint(client):
    # 1. Create a job without custom script (pending)
    payload = {
        "topic": "Khám phá đại dương",
        "style": "collage_broll",
        "language": "vi",
        "format": "shorts",
        "mode": "step_by_step"
    }
    res = client.post("/jobs", json=payload)
    assert res.status_code == 200
    job_id = res.json()["id"]

    # 2. Call initialize-script with custom script text
    init_payload = {
        "script_mode": "custom_script",
        "custom_script_text": "Dưới đáy đại dương sâu thẳm, có những sinh vật phát quang rực rỡ trong bóng tối vĩnh cửu. Chúng sử dụng ánh sáng để săn mồi và giao tiếp với nhau.",
        "topic": "Sinh vật đáy biển"
    }
    res_init = client.post(f"/jobs/{job_id}/initialize-script", json=init_payload)
    assert res_init.status_code == 200
    data_init = res_init.json()
    assert data_init["stage"] == "script_ready"
    assert data_init["pipeline_data"]["script_origin"] == "custom_script"
    assert len(data_init["pipeline_data"]["scenes"]) >= 1


def test_initialize_script_with_bill_bryson_style(client):
    # Create job in step_by_step mode
    payload = {
        "topic": "Sự thật thú vị về bộ não",
        "style": "collage_broll",
        "language": "vi",
        "format": "shorts",
        "mode": "step_by_step"
    }
    res = client.post("/jobs", json=payload)
    assert res.status_code == 200
    job_id = res.json()["id"]

    # Call initialize-script with bill_bryson style
    init_payload = {
        "script_mode": "ai_generate",
        "topic": "Sự thật thú vị về bộ não",
        "script_style_id": "bill_bryson",
        "duration": 60
    }
    res_init = client.post(f"/jobs/{job_id}/initialize-script", json=init_payload)
    assert res_init.status_code == 200
    data = res_init.json()
    assert data["stage"] == "script_ready"
    assert len(data["pipeline_data"]["scenes"]) >= 1


def test_is_autovideofactory_api_logic():
    from launch_studio import is_autovideofactory_api
    # If a port is not running or doesn't have openapi, returns False
    assert is_autovideofactory_api(59999) is False
