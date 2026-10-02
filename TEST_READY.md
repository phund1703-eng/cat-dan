# Test Suite Readiness: VieNeu-TTS & Dynamic Pop-up Subtitles (R5)

**Status**: READY FOR IMPLEMENTATION & VERIFICATION  
**Author**: teamwork_preview_test_writer (test_writer_1)  
**Suite Path**: `test_voice_and_subtitles.py`  
**Infrastructure Spec**: `.agents/teamwork/orchestrator_2/TEST_INFRA.md`  

## 1. Test Suite Summary
The automated test suite `test_voice_and_subtitles.py` has been authored and established at the repository root. It covers all 4 requirements specified under R5:

1. `test_01_vieneu_tts_synthesis`:
   - Validates `VieNeuClient` initialization on-device CPU (`precision="int8"`).
   - Validates voice cloning reference detection in `assets/voices/` and preset voice fallback (`"Minh Quân"`).
   - Validates async synthesis, output file presence, size > 5KB, and duration > 1.0s.
   - Provides deterministic offline execution guarantee to prevent test hanging if ONNX weights are not cached.
2. `test_02_dynamic_subtitles_chunking`:
   - Validates `SubtitleGenerator.generate_dynamic_chunked_ass(sentence, duration, output_path, chunk_words=3, font_size=44, margin_v=180)`.
   - Asserts header resolution `PlayResX: 1080`, `PlayResY: 1920`.
   - Asserts style definitions for `TikTokYellow` (&H0000FFFF) and `TikTokWhite` (&H00FFFFFF) with `Fontsize: 44` and `MarginV: 180`.
   - Asserts each dialogue chunk contains between 2 and 4 words, with single-word remainder merged into the previous chunk.
   - Asserts alternating yellow/white style sequence across dialogue lines.
   - Asserts uniform duration distribution without gaps or overlaps.
3. `test_03_edge_tts_fallback_modulation`:
   - Validates `EdgeTTSClient.default_voices["vi"] == "vi-VN-NamMinhNeural"`.
   - Validates acoustic modulation arguments `rate="-5%"` and `pitch="-2Hz"`.
   - Validates `TTSManager` priority routing for Vietnamese via `VieNeuClient`.
   - Validates seamless, automatic failover to `EdgeTTSClient` when `VieNeuClient` raises an exception.
   - Validates non-Vietnamese requests bypass `VieNeuClient`.
4. `test_04_render_scene_1_snapshot_verification`:
   - Renders Scene 1 12fps stop-motion test video (1.0s) using real cache assets.
   - Extracts midpoint snapshot ($t = 0.5s$) with dynamic ASS subtitles overlay.
   - Uses Pillow programmatic pixel scanning to assert:
     - Pedestal ROI ($y \in [1350, 1640], x \in [200, 880]$) has zero subtitle text yellow/white pixels.
     - Subtitle Safe Zone ROI ($y \in [1680, 1750], x \in [200, 880]$) contains subtitle text pixels.
     - Clearance gap between pedestal bottom ($y=1653$) and subtitle top ($y=1685$) is $\ge 30$px.
     - Clearance gap between balance scales ($y \le 1470$) and subtitle top is $\ge 200$px.

## 2. Test Execution Commands

### Via Pytest:
```powershell
.\venv\Scripts\python.exe -m pytest -v test_voice_and_subtitles.py
```

### Via Direct Python:
```powershell
.\venv\Scripts\python.exe test_voice_and_subtitles.py
```

## 3. Implementation Checklist for Implementing Agent
- [ ] **Milestone M1**:
  - Install dependencies `vieneu` and `soundfile` in `.\venv`.
  - Create `core/tts_engine/vieneu_client.py` (`VieNeuClient`).
  - Update `core/tts_engine/edge_tts_client.py` (voice `vi-VN-NamMinhNeural`, `rate="-5%"`, `pitch="-2Hz"`).
  - Update `core/tts_engine/tts_manager.py` (integrate `VieNeuClient`, Vietnamese priority routing & failover).
- [ ] **Milestone M2**:
  - Implement `generate_dynamic_chunked_ass()` in `core/render_engine/subtitle_generator.py`.
  - Integrate dynamic chunked subtitles and modulated TTS in `produce_human_body_v2.py`.
- [ ] **Milestone M3**:
  - Run `.\venv\Scripts\python.exe test_voice_and_subtitles.py` and confirm all 4 tests pass (Exit code 0).
