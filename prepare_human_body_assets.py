"""
DEPRECATED shim — logic đã chuyển vào core/media_engine/human_body_assets.py (Task 1.1).
Giữ lại để tương thích ngược với import cũ:
    from prepare_human_body_assets import draw_procedural_golden_scale, prepare_all_assets
"""

import warnings

warnings.warn(
    "prepare_human_body_assets is deprecated: use core.media_engine.human_body_assets instead.",
    DeprecationWarning,
    stacklevel=2,
)

from core.media_engine.human_body_assets import (  # noqa: E402,F401
    ASSET_DIR,
    CUTOUTS_DIR,
    apply_vintage_engraving_filter,
    draw_procedural_golden_scale,
    prepare_all_assets,
)

if __name__ == "__main__":
    prepare_all_assets()
