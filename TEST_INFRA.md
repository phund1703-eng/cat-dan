# E2E Test Infra: Cinematic Collage Theatre (AutoVideoFactory)

## Test Philosophy
- Requirement-driven, opaque-box verification based on `ORIGINAL_REQUEST.md`.
- No reliance on mock objects or internal module monkey-patching.
- Methodology: Category-Partition, Boundary Value Analysis, Pairwise Combinations, Real-World Application Scenarios.

## Feature Inventory Mapping
| # | Feature | Source | Tier 1 | Tier 2 | Tier 3 | Tier 4 |
|---|---------|--------|:------:|:------:|:------:|:------:|
| 1 | R1: Paper Cutout 9px & 3D Shadow | ORIGINAL_REQUEST §R1 | 5 | 5 | ✓ | ✓ |
| 2 | R2: Torn Paper Backdrop Generator | ORIGINAL_REQUEST §R2 | 5 | 5 | ✓ | ✓ |
| 3 | R3: AI Visual Director Blueprint | ORIGINAL_REQUEST §R3 | 5 | 5 | ✓ | ✓ |
| 4 | R4: Paper FX 12fps & Shock | ORIGINAL_REQUEST §R4 | 5 | 5 | ✓ | ✓ |
| 5 | R5: Kinetic Layout 8 Engines | ORIGINAL_REQUEST §R5 | 5 | 5 | ✓ | ✓ |
| 6 | R6: 7-Layer Compositor & Pipeline V5 | ORIGINAL_REQUEST §R6 | 5 | 5 | ✓ | ✓ |

## Test Architecture
- **Environment**: Windows, CPython 3.11 (`.\venv\Scripts\python.exe`).
- **Target Pipeline**: `run_pipeline_v5.py`.
- **Primary Video Artifact**: `output/video_v5_sever_axe_woodlog.mp4`.
  - Specs: Resolution 1080x1920, 12 fps, Audio present (EdgeTTS vi-VN), Subtitles burned in (ASS TikTok Yellow with black border).
- **Snapshot Artifact**: `output/snapshot_v5_demo_axe_woodlog.jpg` at 2.4s.
  - Verification: 7 layers present simultaneously:
    - Layer 0: Cardstock textured field.
    - Layer 1: Torn Paper archival backdrop with #F5EFEB fiber border and soft shadow.
    - Layer 2: Stage prop (carpenter workbench) beneath objects.
    - Layer 3: Wood log split into 2 drifting halves (260px, 30°).
    - Layer 4: Axe embedded with 9px cream border.
    - Layer 5: Paper debris particles bursting in cone.
    - Layer 6: Director accents (Victorian hand/ruler).

## Test Cases by Tier
- **Tier 1 (Feature Coverage)**: Unit & contract execution for each module (`apply_paper_cutout_styling`, `TornPaperBackdropGenerator`, `AIVisualDirector`, `PaperFXEngine`, `KineticLayoutBridge`).
- **Tier 2 (Boundary & Corner Cases)**: Empty input images, non-existent paths, edge coordinates, extreme shock amplitudes, extreme scale factors.
- **Tier 3 (Cross-Feature Combinations)**: Visual Director -> Bridge -> Paper FX -> GbroAdapter data propagation.
- **Tier 4 (Real-World Application Scenarios)**: Execution of `"Lưỡi rìu bổ đôi khúc gỗ rừng già"` through full Pipeline V5.
- **Tier 5 (Adversarial Coverage Hardening)**: White-box inspection of code branches, frame bounds, memory leaks, and clipping defenses.

## Pass/Fail Criteria
- `.\venv\Scripts\python.exe run_pipeline_v5.py` exits with code 0.
- `output/video_v5_sever_axe_woodlog.mp4` exists, size > 100KB, duration > 3.0s.
- `output/snapshot_v5_demo_axe_woodlog.jpg` exists, dimensions 1080x1920.
