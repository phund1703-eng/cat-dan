"""
AutoVideoFactory — AlphaQAGate (Phase 1)
Cổng kiểm soát chất lượng kênh Alpha sau khi tách nền rembg:
- Ngăn chặn hoàn toàn lỗi màn hình rỗng trơn hoặc vật thể bị teo tóp thành chấm đen.
- Kiểm duyệt tỷ lệ pixel không trong suốt so với diện tích khung hình.
"""

from pathlib import Path
from typing import Dict, Any, Union
from PIL import Image
from loguru import logger


class AlphaQAGate:
    """
    Kiểm duyệt chất lượng kênh Alpha của sticker cắt dán (Cutout Sticker QA Gate):
    - alpha_ratio: Tỷ lệ pixel có alpha > 20 trên tổng số pixel.
    - Tiêu chuẩn:
      * 0.08 <= alpha_ratio <= 0.85: PASS (Vật thể hiển thị đẹp, rõ ràng).
      * alpha_ratio < 0.08: FAIL_TOO_EMPTY (Vật thể bị xóa mất hoặc teo tóp thành chấm đen).
      * alpha_ratio > 0.85: FAIL_NOT_REMOVED (Nền chưa được bóc tách).
    """

    MIN_PASS_RATIO = 0.08
    MAX_PASS_RATIO = 0.85

    @classmethod
    def verify(cls, image_path: Union[str, Path]) -> Dict[str, Any]:
        """
        Kiểm tra file ảnh PNG đã tách nền.
        """
        p = Path(image_path).resolve()
        if not p.exists():
            return {
                "passed": False,
                "ratio": 0.0,
                "status": "FAIL_NOT_FOUND",
                "message": f"File không tồn tại: {p.name}"
            }

        try:
            with Image.open(p) as img:
                rgba = img.convert("RGBA")
                alpha = rgba.split()[-1]
                total_pixels = alpha.width * alpha.height

                if total_pixels == 0:
                    return {
                        "passed": False,
                        "ratio": 0.0,
                        "status": "FAIL_ZERO_DIM",
                        "message": "Ảnh có kích thước 0"
                    }

                # Đếm số pixel có alpha > 20
                # Sử dụng point/histogram hoặc numpy/getdata
                alpha_data = alpha.getdata()
                non_transparent = sum(1 for a in alpha_data if a > 20)
                alpha_ratio = non_transparent / total_pixels

            # Đánh giá quy chuẩn
            if alpha_ratio < cls.MIN_PASS_RATIO:
                status = "FAIL_TOO_EMPTY"
                passed = False
                msg = f"Vật thể bị rỗng hoặc teo tóp (tỷ lệ {alpha_ratio*100:.1f}% < {cls.MIN_PASS_RATIO*100}%)"
            elif alpha_ratio > cls.MAX_PASS_RATIO:
                status = "FAIL_NOT_REMOVED"
                passed = False
                msg = f"Nền chưa được bóc tách (tỷ lệ {alpha_ratio*100:.1f}% > {cls.MAX_PASS_RATIO*100}%)"
            else:
                status = "PASS"
                passed = True
                msg = f"Vật thể hiển thị sắc nét, tỷ lệ chuẩn ({alpha_ratio*100:.1f}%)"

            res = {
                "passed": passed,
                "ratio": round(alpha_ratio, 4),
                "status": status,
                "message": msg,
                "file": p.name
            }

            if passed:
                logger.success(f"✅ [AlphaQA] {p.name}: {msg}")
            else:
                logger.warning(f"⚠️ [AlphaQA] {p.name}: {msg}")

            return res

        except Exception as e:
            logger.error(f"Lỗi đọc kiểm duyệt Alpha cho {p.name}: {e}")
            return {
                "passed": False,
                "ratio": 0.0,
                "status": "FAIL_ERROR",
                "message": str(e),
                "file": p.name
            }
