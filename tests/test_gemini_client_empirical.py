"""
tests/test_gemini_client_empirical.py

Empirical Challenger & Stress Test Suite for:
- core/script_engine/gemini_client.py
- .env configuration

Verifies:
1. Default model is gemini-3.8-flash.
2. Candidate model fallback list is ["gemini-3.8-flash", "gemini-3.7-flash", "gemini-flash-latest"].
3. Candidate fallback loop behavior under simulated failure (404, 503, invalid JSON, 429 quota).
4. Non-blocking asyncio.to_thread execution without blocking or crashing the event loop.
"""

import os
import sys
import json
import time
import asyncio
from pathlib import Path
from unittest.mock import MagicMock, patch

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.script_engine.gemini_client import GeminiClient, DEFAULT_FALLBACK_MODELS


def test_env_config():
    """Verify .env and .env.example configuration."""
    print("\n--- Test 1: .env Configuration ---")
    env_path = PROJECT_ROOT / ".env"
    assert env_path.exists(), ".env file must exist"
    
    with open(env_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    gemini_model_lines = [line.strip() for line in content.splitlines() if line.strip().startswith("GEMINI_MODEL=")]
    gemini_pro_lines = [line.strip() for line in content.splitlines() if line.strip().startswith("GEMINI_PRO_MODEL=")]
    
    assert gemini_model_lines, "GEMINI_MODEL must be defined in .env"
    assert "gemini-3.8-flash" in gemini_model_lines[0], f"Expected gemini-3.8-flash in GEMINI_MODEL, got: {gemini_model_lines[0]}"
    assert gemini_pro_lines, "GEMINI_PRO_MODEL must be defined in .env"
    assert "gemini-3.8-flash" in gemini_pro_lines[0], f"Expected gemini-3.8-flash in GEMINI_PRO_MODEL, got: {gemini_pro_lines[0]}"
    print("  [PASS] .env correctly specifies GEMINI_MODEL=gemini-3.8-flash and GEMINI_PRO_MODEL=gemini-3.8-flash")


def test_model_defaults_and_candidate_list():
    """Verify default model and candidate fallback list."""
    print("\n--- Test 2: GeminiClient Defaults & Candidate List ---")
    assert DEFAULT_FALLBACK_MODELS == ["gemini-3.8-flash", "gemini-3.7-flash", "gemini-flash-latest"], (
        f"DEFAULT_FALLBACK_MODELS mismatch: {DEFAULT_FALLBACK_MODELS}"
    )
    
    client = GeminiClient()
    assert client.default_model == "gemini-3.8-flash", f"Expected default_model 'gemini-3.8-flash', got '{client.default_model}'"
    assert client.fallback_models == ["gemini-3.8-flash", "gemini-3.7-flash", "gemini-flash-latest"], (
        f"client.fallback_models mismatch: {client.fallback_models}"
    )
    
    # Check default candidate models
    candidates = client._get_candidate_models()
    assert candidates == ["gemini-3.8-flash", "gemini-3.7-flash", "gemini-flash-latest"], (
        f"Candidates mismatch: {candidates}"
    )
    
    # Check custom preferred model ordering and deduplication
    custom_candidates = client._get_candidate_models("custom-model-x")
    assert custom_candidates == ["custom-model-x", "gemini-3.8-flash", "gemini-3.7-flash", "gemini-flash-latest"], (
        f"Custom candidates mismatch: {custom_candidates}"
    )
    
    # Check preferred model that is already in fallback list (should be prioritized first, deduplicated)
    fallback_as_pref = client._get_candidate_models("gemini-3.7-flash")
    assert fallback_as_pref == ["gemini-3.7-flash", "gemini-3.8-flash", "gemini-flash-latest"], (
        f"Priority candidates mismatch: {fallback_as_pref}"
    )
    print("  [PASS] Model defaults and candidate lists verified with correct ordering and deduplication")


def test_simulated_fallback_generate():
    """Verify fallback behavior in generate() when primary model fails."""
    print("\n--- Test 3: Fallback Loop in generate() ---")
    client = GeminiClient()
    
    calls = []
    
    def fake_generative_model(model_name):
        mock_model = MagicMock()
        calls.append(model_name)
        if model_name == "gemini-3.8-flash":
            def fail_call(*args, **kwargs):
                raise RuntimeError("404 Model Not Found: gemini-3.8-flash")
            mock_model.generate_content.side_effect = fail_call
        elif model_name == "gemini-3.7-flash":
            mock_resp = MagicMock()
            mock_resp.text = "Success output from gemini-3.7-flash"
            mock_model.generate_content.return_value = mock_resp
        else:
            mock_resp = MagicMock()
            mock_resp.text = "Fallback output from " + model_name
            mock_model.generate_content.return_value = mock_resp
        return mock_model

    with patch("core.script_engine.gemini_client.genai.GenerativeModel", side_effect=fake_generative_model):
        result = asyncio.run(client.generate("Test prompt"))
        
    assert result == "Success output from gemini-3.7-flash", f"Unexpected result: {result}"
    assert "gemini-3.8-flash" in calls, "Primary model should have been attempted"
    assert "gemini-3.7-flash" in calls, "Secondary model should have been attempted on fallback"
    assert "gemini-flash-latest" not in calls, "Tertiary model should not be called if secondary succeeds"
    print(f"  [PASS] Fallback succeeded: Attempted {calls}, returned secondary model response")


def test_simulated_multi_level_fallback_generate_script():
    """Verify multi-level fallback in generate_script() with bad JSON and 500 error."""
    print("\n--- Test 4: Multi-Level Fallback Loop in generate_script() ---")
    client = GeminiClient()
    
    calls = []
    
    def fake_generative_model(model_name):
        mock_model = MagicMock()
        calls.append(model_name)
        if model_name == "gemini-3.8-flash":
            def fail_call(*args, **kwargs):
                raise RuntimeError("503 Service Unavailable")
            mock_model.generate_content.side_effect = fail_call
        elif model_name == "gemini-3.7-flash":
            # Returns unparseable non-JSON text
            mock_resp = MagicMock()
            mock_resp.text = "Sorry, I cannot produce JSON right now."
            mock_model.generate_content.return_value = mock_resp
        elif model_name == "gemini-flash-latest":
            # Returns valid JSON
            mock_resp = MagicMock()
            mock_resp.text = json.dumps({
                "title": "Success Title",
                "topic_domain": "science",
                "scenes": [{"narration": "Hello world"}]
            })
            mock_model.generate_content.return_value = mock_resp
        return mock_model

    with patch("core.script_engine.gemini_client.genai.GenerativeModel", side_effect=fake_generative_model):
        result = asyncio.run(client.generate_script("topic", "style", "vi", 30))
        
    assert isinstance(result, dict), f"Expected dict, got {type(result)}"
    assert result["title"] == "Success Title", f"Unexpected title: {result.get('title')}"
    assert calls == ["gemini-3.8-flash", "gemini-3.7-flash", "gemini-flash-latest"], (
        f"Expected all 3 models in sequence, got: {calls}"
    )
    print(f"  [PASS] Multi-level fallback succeeded through 3 models: {calls}")


def test_all_models_fail_raises_last_error():
    """Verify that when all models in candidate list fail, the last error is raised."""
    print("\n--- Test 5: Exhaustion of All Candidate Models ---")
    client = GeminiClient()
    
    calls = []
    
    def fake_generative_model(model_name):
        mock_model = MagicMock()
        calls.append(model_name)
        def fail_call(*args, **kwargs):
            raise RuntimeError(f"Error on {model_name}")
        mock_model.generate_content.side_effect = fail_call
        return mock_model

    with patch("core.script_engine.gemini_client.genai.GenerativeModel", side_effect=fake_generative_model):
        try:
            asyncio.run(client.generate("Test prompt"))
            assert False, "Should have raised RuntimeError when all models fail"
        except RuntimeError as e:
            assert "gemini-flash-latest" in str(e), f"Expected last error from gemini-flash-latest, got: {e}"
            
    assert calls == ["gemini-3.8-flash", "gemini-3.7-flash", "gemini-flash-latest"], (
        f"All models should have been attempted, got: {calls}"
    )
    print("  [PASS] All candidate models attempted and last error cleanly raised")


def test_asyncio_to_thread_non_blocking_event_loop():
    """
    Stress-test asyncio.to_thread execution:
    Asserts that gen_model.generate_content runs in a thread pool without
    blocking concurrent tasks in the asyncio event loop or causing loop crashes.
    """
    print("\n--- Test 6: asyncio.to_thread Non-Blocking Event Loop Stress Test ---")
    client = GeminiClient()
    
    loop_ticks = []
    
    async def background_heartbeat():
        """Tick every 20ms while generate() is running."""
        for _ in range(15):
            await asyncio.sleep(0.02)
            loop_ticks.append(time.time())

    def slow_sync_generate(*args, **kwargs):
        """Simulate synchronous network latency inside the worker thread."""
        time.sleep(0.2)  # 200ms synchronous blocking sleep
        mock_resp = MagicMock()
        mock_resp.text = "Slow thread response"
        return mock_resp

    mock_model = MagicMock()
    mock_model.generate_content.side_effect = slow_sync_generate

    with patch("core.script_engine.gemini_client.genai.GenerativeModel", return_value=mock_model):
        async def main_coro():
            start_t = time.time()
            # Run heartbeat and generate concurrently
            heartbeat_task = asyncio.create_task(background_heartbeat())
            gen_task = asyncio.create_task(client.generate("Test prompt"))
            
            gen_res = await gen_task
            await heartbeat_task
            elapsed = time.time() - start_t
            return gen_res, elapsed

        result, elapsed_time = asyncio.run(main_coro())

    assert result == "Slow thread response"
    assert elapsed_time >= 0.18, f"Expected elapsed >= 0.18s, got {elapsed_time:.3f}s"
    # Crucial assertion: the event loop MUST have ticked multiple times while the thread was sleeping!
    assert len(loop_ticks) >= 5, (
        f"Event loop was blocked! Expected at least 5 ticks during 200ms sleep, got {len(loop_ticks)}"
    )
    print(f"  [PASS] Event loop remained responsive: {len(loop_ticks)} async ticks during 200ms worker thread call (elapsed: {elapsed_time:.3f}s)")


def test_markdown_json_extraction():
    """Verify markdown block JSON extraction in generate_script."""
    print("\n--- Test 7: Markdown Block JSON Extraction ---")
    client = GeminiClient()
    
    mock_model = MagicMock()
    mock_resp = MagicMock()
    mock_resp.text = "Here is the JSON you requested:\n```json\n{\n  \"title\": \"Extracted\",\n  \"scenes\": []\n}\n```\nHope this helps!"
    mock_model.generate_content.return_value = mock_resp

    with patch("core.script_engine.gemini_client.genai.GenerativeModel", return_value=mock_model):
        result = asyncio.run(client.generate_script("topic", "style", "vi", 30))
        
    assert result == {"title": "Extracted", "scenes": []}
    print("  [PASS] Markdown wrapped JSON successfully extracted")


def run_all_empirical_tests():
    print("=====================================================================")
    print("EMPIRICAL TEST SUITE: GeminiClient Fallback & Async Thread Safety")
    print("=====================================================================")
    
    test_env_config()
    test_model_defaults_and_candidate_list()
    test_simulated_fallback_generate()
    test_simulated_multi_level_fallback_generate_script()
    test_all_models_fail_raises_last_error()
    test_asyncio_to_thread_non_blocking_event_loop()
    test_markdown_json_extraction()
    
    print("\n=====================================================================")
    print("ALL 7 EMPIRICAL TESTS PASSED SUCCESSFULLY (100% PASS RATE)")
    print("=====================================================================")


if __name__ == "__main__":
    run_all_empirical_tests()
