"""
AutoVideoFactory — Asset Content Validation Module
core/media_engine/asset_content_validator.py

Requirement R4:
Pre-render validation of cutout assets for the multi-layer collage engine.
Enforces:
1. File existence and readability in RGBA format.
2. Valid dimensions: between 60x60 and 4096x4096 pixels.
3. Transparent alpha channel ratio: minimum 8% (confirming cutout, not solid background)
   and maximum 95% (not empty / nearly empty image).
4. Methods: validate_cutout() and validate_and_reject_if_invalid().
"""

import os
from pathlib import Path
from typing import Optional, Union, Tuple
from PIL import Image
import numpy as np
from loguru import logger

PROJECT_ROOT = Path(__file__).resolve().parents[2]


class ValidationResult(tuple):
    """
    Result object that is both a (is_valid: bool, reason: str) 2-tuple
    and evaluates directly as a boolean in conditional expressions:
        res = validator.validate_cutout(path)
        if res: ...
        is_valid, reason = validator.validate_cutout(path)
        assert res.is_valid
    """
    def __new__(cls, is_valid: bool, reason: str, transparent_ratio: float = 0.0):
        instance = super(ValidationResult, cls).__new__(cls, (bool(is_valid), str(reason)))
        instance._transparent_ratio = float(transparent_ratio)
        return instance

    @property
    def is_valid(self) -> bool:
        return self[0]

    @property
    def reason(self) -> str:
        return self[1]

    @property
    def transparent_ratio(self) -> float:
        return getattr(self, "_transparent_ratio", 0.0)

    def __bool__(self) -> bool:
        return self[0]

    def __repr__(self) -> str:
        return f"ValidationResult(is_valid={self.is_valid}, reason='{self.reason}', transparent_ratio={self.transparent_ratio:.3f})"



class AssetContentValidator:
    """
    Validates cutout asset suitability before rendering into collage scenes.
    Prevents corrupt, non-cutout, solid-background, or empty images from entering the pipeline.
    """
    MIN_DIMENSION: int = 60
    MAX_DIMENSION: int = 4096
    MIN_ALPHA_RATIO: float = 0.08
    MAX_ALPHA_RATIO: float = 0.95

    REJECTED_ASSET_NAMES: set = {
        "scale.png",
        "scale",
        "test_art_cutout",
        "test_art_cutout.png",
        "temp_raw_real_kitchen_knife",
        "temp_raw_real_kitchen_knife.png",
        "test_axe_flip_v",
        "test_axe_flip_v.png",
        "test_axe_rot_180",
        "test_axe_rot_180.png",
        "test_knife_dl",
        "test_knife_dl.png",
        "test_knife_flip_v",
        "test_knife_flip_v.png",
    }

    def __init__(
        self,
        min_dimension: int = MIN_DIMENSION,
        max_dimension: int = MAX_DIMENSION,
        min_alpha_ratio: float = MIN_ALPHA_RATIO,
        max_alpha_ratio: float = MAX_ALPHA_RATIO
    ):
        self.min_dimension = min_dimension
        self.max_dimension = max_dimension
        self.min_alpha_ratio = min_alpha_ratio
        self.max_alpha_ratio = max_alpha_ratio

    def validate_cutout(self, asset_path: Union[str, Path]) -> ValidationResult:
        """
        Check cutout asset validity before rendering:
        1. File exists and is readable in RGBA format.
        2. Valid dimensions: between min_dimension (60x60) and max_dimension (4096x4096).
        3. Transparent alpha channel ratio: between min_alpha_ratio (8%) and max_alpha_ratio (95%).
        """
        if not isinstance(asset_path, (str, Path)):
            return ValidationResult(False, f"Invalid asset path type: {type(asset_path).__name__}")

        if not asset_path:
            return ValidationResult(False, "Empty or None asset path provided")

        path = Path(asset_path)
        name_lower = path.name.lower()
        stem_lower = path.stem.lower()

        # Check against blacklist and intermediate junk
        if name_lower in self.REJECTED_ASSET_NAMES or stem_lower in self.REJECTED_ASSET_NAMES:
            return ValidationResult(False, f"Asset '{path.name}' is in REJECTED_ASSET_NAMES blacklist")

        if stem_lower.startswith("test_") or stem_lower.startswith("temp_") or "_raw_try" in stem_lower:
            return ValidationResult(False, f"Asset '{path.name}' is temporary/intermediate junk")

        # Resolve path if relative or not found directly
        if not path.exists():
            candidates = [
                PROJECT_ROOT / path,
                PROJECT_ROOT / "data" / "asset_library" / "global_cutouts" / path.name,
                PROJECT_ROOT / "data" / "cache" / "cutouts" / path.name,
                PROJECT_ROOT / "data" / "cache" / "human_body_assets" / path.name,
                PROJECT_ROOT / "data" / "cache" / "quarantine" / path.name,
            ]
            for cand in candidates:
                if cand.exists():
                    path = cand
                    break

        if not path.exists():
            return ValidationResult(False, f"File does not exist: {path}")
        if not path.is_file():
            return ValidationResult(False, f"Path is not a regular file: {path}")

        try:
            with Image.open(path) as raw_img:
                # 1. Format check: readable in RGBA format
                bands = raw_img.getbands()
                if "A" not in bands:
                    return ValidationResult(
                        False,
                        f"Asset is not in RGBA format (bands: {bands}, missing alpha channel)"
                    )

                # 2. Dimensions check: between 60x60 and 4096x4096
                w, h = raw_img.size
                if w < self.min_dimension or h < self.min_dimension:
                    return ValidationResult(
                        False,
                        f"Asset dimensions {w}x{h} are below minimum {self.min_dimension}x{self.min_dimension}"
                    )
                if w > self.max_dimension or h > self.max_dimension:
                    return ValidationResult(
                        False,
                        f"Asset dimensions {w}x{h} exceed maximum {self.max_dimension}x{self.max_dimension}"
                    )

                # 3. Transparent alpha channel ratio: minimum 8% and maximum 95%
                alpha_chan = raw_img.getchannel("A")
                alpha_arr = np.array(alpha_chan)
                total_pixels = alpha_arr.size
                # A pixel is considered transparent if alpha < 128
                transparent_pixels = np.sum(alpha_arr < 128)
                transparent_ratio = float(transparent_pixels) / float(total_pixels)

                if transparent_ratio < self.min_alpha_ratio:
                    return ValidationResult(
                        False,
                        f"Transparent alpha channel ratio {transparent_ratio:.1%} is below minimum {self.min_alpha_ratio:.1%} "
                        f"(solid background, not a cutout)",
                        transparent_ratio=transparent_ratio
                    )
                if transparent_ratio > self.max_alpha_ratio:
                    return ValidationResult(
                        False,
                        f"Transparent alpha channel ratio {transparent_ratio:.1%} exceeds maximum {self.max_alpha_ratio:.1%} "
                        f"(empty or nearly empty image)",
                        transparent_ratio=transparent_ratio
                    )

                return ValidationResult(
                    True,
                    f"Valid cutout asset ({w}x{h}, alpha transparent ratio {transparent_ratio:.1%})",
                    transparent_ratio=transparent_ratio
                )

        except Exception as e:
            return ValidationResult(False, f"Failed to read/validate asset '{path.name}': {e}")

    def validate_and_reject_if_invalid(self, asset_path: Optional[Union[str, Path]]) -> str:
        """
        Validates cutout asset.
        Returns:
            Resolved absolute file path string if valid.
            Empty string "" if invalid (preventing rendering junk).
        """
        if not isinstance(asset_path, (str, Path)) or not asset_path:
            return ""

        res = self.validate_cutout(asset_path)
        if res.is_valid:
            p = Path(asset_path)
            if p.exists():
                return str(p.resolve())
            candidates = [
                PROJECT_ROOT / p,
                PROJECT_ROOT / "data" / "asset_library" / "global_cutouts" / p.name,
                PROJECT_ROOT / "data" / "cache" / "cutouts" / p.name,
                PROJECT_ROOT / "data" / "cache" / "human_body_assets" / p.name,
            ]
            for cand in candidates:
                if cand.exists():
                    return str(cand.resolve())
            return str(p.resolve())
        else:
            logger.warning(f"⚠️ [AssetContentValidator] Rejected invalid asset '{asset_path}': {res.reason}")
            return ""

