"""
Script Style Presets Manager
Manages built-in and user-defined script writing styles with custom prompt tone instructions.
"""
import os
import json
import re
from pathlib import Path
from typing import List, Dict, Any, Optional
from loguru import logger

CONFIG_FILE = Path(__file__).resolve().parents[2] / "config" / "script_styles.json"

DEFAULT_STYLES: List[Dict[str, Any]] = [
    {
        "id": "storytelling_mystery",
        "name": "🎭 Kể chuyện Ly Kỳ & Giật Gân (Cuốn hút, hook mạnh)",
        "description": "Mở đầu bằng câu hỏi hoặc sự thật gây sốc, dồn dập kịch tính, đẩy mâu thuẫn lên cao trào và giải mã bất ngờ ở đoạn kết.",
        "tone_instruction": "Phong cách kể chuyện ly kỳ, giật gân (Storytelling / Mystery). 3 giây đầu tiên PHẢI là một câu Hook cực mạnh gây tò mò tột đỉnh hoặc phủ định một niềm tin thông thường. Nhịp điệu dồn dập, dùng từ ngữ giàu hình ảnh và kịch tính. Đẩy sự tò mò lên cao trào và kết thúc bằng một sự thật bất ngờ hoặc bài học sâu sắc.",
        "target_audience": "Khán giả tò mò, thích khám phá bí ẩn, Shorts/Reels viral",
        "is_builtin": True
    },
    {
        "id": "deep_science",
        "name": "🔬 Khoa Học & Phân Tích Cơ Chế (Chính xác, logic, dễ hiểu)",
        "description": "Tập trung vào cơ chế sinh học, vật lý, giải thích bản chất vì sao bằng hình tượng trực quan đời thường.",
        "tone_instruction": "Phong cách khoa học đại chúng (Infotainment / Deep Science). Giọng điệu chuyên gia đáng tin cậy nhưng diễn đạt bằng ngôn ngữ đời thường, hóm hỉnh và dễ hiểu. Nêu rõ các số liệu thực tế, cơ chế sinh học/vật lý cụ thể, giải thích cặn kẽ câu hỏi 'Tại sao cơ thể/vũ trụ lại hoạt động như vậy'.",
        "target_audience": "Người yêu khoa học, học sinh sinh viên, khán giả thích kiến thức thực tế",
        "is_builtin": True
    },
    {
        "id": "humorous_fun",
        "name": "😂 Hài Hước & Ví Von Đời Thường (Gen Z, dí dỏm, châm biếm)",
        "description": "Ngôn từ dí dỏm, châm biếm đời thường, ví von bất ngờ, tạo cảm giác như bạn thân đang trò chuyện.",
        "tone_instruction": "Phong cách hài hước, dí dỏm, châm biếm nhẹ nhàng (Casual / Humorous). Sử dụng ngôn ngữ gần gũi, các phép so sánh ví von bất ngờ giữa khoa học và cuộc sống hằng ngày (ví dụ: so sánh tế bào với công nhân tăng ca, dạ dày với lò phản ứng). Tránh tuyệt đối lối nói khô khan như sách giáo khoa.",
        "target_audience": "Khán giả trẻ, Gen Z, giải trí kết hợp kiến thức",
        "is_builtin": True
    },
    {
        "id": "quick_viral",
        "name": "⚡ Nhanh, Gọn, Thực Chiến (Thông tin dồn dập, dưới 12 từ/câu)",
        "description": "Nhịp độ cực nhanh, mỗi câu thoại ngắn gọn súc tích, đi thẳng vào các điểm mấu chốt gây choáng ngợp.",
        "tone_instruction": "Phong cách nhanh, gọn, dồn dập (Fast-paced Viral). Mỗi câu thoại không quá 12-15 từ. Loại bỏ hoàn toàn các từ thừa, đi thẳng vào sự thật chấn động tiếp theo. Tạo cảm giác năng lượng cao, giữ chân người xem từ đầu đến giây cuối cùng.",
        "target_audience": "Người xem TikTok lướt nhanh, thích thông tin 'mì ăn liền' chất lượng cao",
        "is_builtin": True
    }
]


def _ensure_config_exists() -> None:
    """Ensures the config file exists with default styles."""
    if not CONFIG_FILE.exists():
        CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(DEFAULT_STYLES, f, ensure_ascii=False, indent=2)


def get_all_script_styles() -> List[Dict[str, Any]]:
    """Loads and returns all script style presets."""
    _ensure_config_exists()
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            styles = json.load(f)
            if isinstance(styles, list) and len(styles) > 0:
                return styles
    except Exception as e:
        logger.warning(f"Could not read {CONFIG_FILE} ({e}), using default styles")
    return DEFAULT_STYLES


def get_script_style_by_id(style_id: str) -> Optional[Dict[str, Any]]:
    """Gets a specific script style preset by ID."""
    styles = get_all_script_styles()
    for s in styles:
        if s.get("id") == style_id:
            return s
    return None


def save_script_style(
    style_id: str,
    name: str,
    description: str,
    tone_instruction: str,
    target_audience: str = ""
) -> Dict[str, Any]:
    """Saves a new custom script style preset or updates an existing one."""
    styles = get_all_script_styles()
    clean_id = re.sub(r"[^a-zA-Z0-9_\-]", "_", style_id.strip().lower())
    if not clean_id:
        clean_id = "custom_style"

    existing_idx = None
    for i, s in enumerate(styles):
        if s.get("id") == clean_id:
            existing_idx = i
            break

    new_item = {
        "id": clean_id,
        "name": name.strip(),
        "description": description.strip(),
        "tone_instruction": tone_instruction.strip(),
        "target_audience": target_audience.strip(),
        "is_builtin": False
    }

    if existing_idx is not None:
        # Preserve is_builtin if it was builtin, or override tone
        was_builtin = styles[existing_idx].get("is_builtin", False)
        new_item["is_builtin"] = was_builtin
        styles[existing_idx] = new_item
    else:
        styles.append(new_item)

    try:
        CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(styles, f, ensure_ascii=False, indent=2)
        logger.success(f"Saved script style preset '{clean_id}' successfully.")
    except Exception as e:
        logger.error(f"Failed to save script style preset to {CONFIG_FILE}: {e}")
        raise

    return new_item


def delete_script_style(style_id: str) -> bool:
    """Deletes a custom script style preset (built-ins cannot be deleted)."""
    styles = get_all_script_styles()
    initial_len = len(styles)
    filtered = [s for s in styles if not (s.get("id") == style_id and not s.get("is_builtin"))]
    if len(filtered) == initial_len:
        return False

    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(filtered, f, ensure_ascii=False, indent=2)
        logger.success(f"Deleted custom script style preset '{style_id}'.")
        return True
    except Exception as e:
        logger.error(f"Failed to delete script style: {e}")
        return False
