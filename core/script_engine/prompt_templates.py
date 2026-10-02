from typing import Dict

class PromptTemplates:
    """Provides prompt templates for script generation."""
    
    VIDEO_STYLES = {
        "collage_broll": "Editorial halftone paper collage cutout style, isolated background, bold flat color fields, cream keylines, paper drop shadows, stop-motion assembly.",
        "animation_2d": "Story-driven, using animated characters and scenes. Friendly and approachable.",
        "clip_overlay": "Minimalist, text and graphics overlaid on a single continuous background or slow-moving clip.",
        "whiteboard": "Educational, drawn out step-by-step on a whiteboard. Good for explaining complex topics.",
        "ai_avatar": "A talking head AI avatar presenting the content directly to the viewer. Professional and engaging."
    }

    @staticmethod
    def get_script_prompt(topic: str, style: str, language: str, duration: int = 60) -> str:
        """
        Generates the full prompt string for Gemini to create a video script.

        Args:
            topic (str): The video topic.
            style (str): The video style.
            language (str): 'en' or 'vi'.
            duration (int): Target duration in seconds.

        Returns:
            str: The formatted prompt.
        """
        style_desc = PromptTemplates.VIDEO_STYLES.get(style, "Standard engaging video style.")
        collage_rule_vi = ""
        collage_rule_en = ""
        if style == "collage_broll":
            if language == 'vi':
                return f"""Bạn là một biên kịch và giám đốc nghệ thuật video chuyên nghiệp theo phong cách editorial paper-collage stop-motion chuẩn repo gbro-collage-broll.
Hãy viết một kịch bản video về chủ đề: "{topic}".
Thời lượng dự kiến: khoảng {duration} giây (khoảng {max(3, duration // 7)} đến {max(4, duration // 6)} cảnh, mỗi cảnh 5-8 giây).

QUY TẮC BẮT BUỘC CHO TỪNG CẢNH (SCENE):
1. topic_domain: Xác định 1 trong các lĩnh vực sau: "space", "biology", "geography", "history", "psychology", "technology".
2. QUY TẮC VẬT THỂ HỮU HÌNH 100% (Tangible Object Rule):
   - BẮT BUỘC chuyển đổi mọi khái niệm, câu nói trừu tượng thành VẬT THỂ VẬT LÝ CỤ THỂ cầm nắm, nhìn thấy và bóc tách sticker được bằng tiếng Anh (1-3 từ).
   - Ví dụ:
     * Bạch cầu / Miễn dịch -> "macrophage" / "white blood cell"
     * Vi khuẩn / Mầm bệnh -> "bacterium" / "microbe" / "virus"
     * Biển sâu / Vực thẳm -> "bathyscaphe" / "submarine" / "anglerfish" / "anchor" / "pressure gauge"
     * Xác ướp / Ai Cập -> "pharaoh" / "golden sarcophagus" / "canopic jar" / "pyramid" / "papyrus"
     * Bế tắc / Bảo mật -> "iron padlock" / "chains"
     * Ý tưởng / Khai sáng -> "light bulb"
     * Thời gian / Đo lường -> "hourglass" / "clock" / "compass"
   - NGHIÊM CẤM dùng các từ khóa trừu tượng (như "success", "danger", "mystery", "power", "depth", "fear").
3. layout_type: 1 trong 4 bố cục: "hero_center", "split_contrast", "surreal_interaction", "stage_prop".
4. Cờ ngữ cảnh:
   - has_hand: boolean (chỉ đặt true khi cảnh có ý đồ thao túng, can thiệp hoặc bàn tay người chỉ dẫn).
   - has_camera: boolean (chỉ đặt true khi cảnh liên quan đến góc nhìn quay phim, truyền thông).
5. Gate 2 (Prompt sinh ảnh tĩnh hoàn chỉnh):
   Sử dụng chính xác mẫu chuyên gia:
   "Use case: ads-marketing. Asset type: final still frame for a 9:16 image-to-video B-roll clip. Primary request: Create a finished editorial paper-collage image expressing [visual_metaphor]. Scene/backdrop: perfectly flat [color_field] paper field #[color_hex] with subtle uncoated paper fiber. Style/medium: premium editorial stop-motion paper collage; black-and-white halftone photographic cut-outs mixed with selective colored cardstock. Composition/framing: vertical 9:16 locked poster frame; central subject within the middle 70 percent; generous clean color-field negative space; 3–6 large separable paper groups for later assemble-from-empty animation. Materials/textures: visible printed halftone dots, crisp machine-cut edges, thin warm-cream paper keylines, soft low-opacity physical drop shadows. Avoid: no typography, no readable letters, no numerals, no logos, no watermark, no UI, no subtitles, no glossy 3D, no photoreal environment, no clutter."

YÊU CẦU ĐẦU RA:
Bạn phải trả về DUY NHẤT một chuỗi JSON hợp lệ với cấu trúc sau:
{{
  "title": "Tiêu đề video (ngắn gọn, thu hút)",
  "description": "Mô tả ngắn gọn về video",
  "topic_domain": "biology | geography | history | space | psychology | technology",
  "hashtags": ["#hashtag1", "#hashtag2", "#hashtag3"],
  "scenes": [
    {{
      "narration": "Lời thoại nhân vật hoặc giọng đọc súc tích, hấp dẫn bằng tiếng Việt.",
      "core_meaning": "Ý nghĩa cốt lõi của cảnh",
      "visual_metaphor": "3-6 đồ vật biểu tượng cụ thể hữu hình",
      "topic_domain": "biology",
      "focal_keyword": "white blood cell",
      "secondary_keyword": "bacterium",
      "layout_type": "hero_center",
      "has_hand": false,
      "has_camera": false,
      "color_field": "Deep Cobalt",
      "color_hex": "1D3557",
      "assembly_order": "Thứ tự các đồ vật bay vào/lắp ráp từ nền trống",
      "still_image_prompt": "Use case: ads-marketing. Asset type: final still frame for a 9:16 image-to-video B-roll clip...",
      "visual_description": "Mô tả ngắn gọn cảnh thị giác cắt dán",
      "duration": 5.0
    }}
  ]
}}
"""
            else:
                return f"""You are a professional video scriptwriter and art director in editorial paper-collage stop-motion style (gbro-collage-broll).
Write a video script about the topic: "{topic}".
Target duration: approximately {duration} seconds.

MANDATORY RULES FOR EACH SCENE:
1. topic_domain: One of: "space", "biology", "geography", "history", "psychology", "technology".
2. 100% TANGIBLE OBJECT RULE:
   - Convert all abstract ideas into CONCRETE PHYSICAL TOUCHABLE OBJECTS in English (1-3 words).
   - Never use abstract keywords.
3. layout_type: One of: 'hero_center', 'split_contrast', 'surreal_interaction', 'stage_prop'.
4. Contextual flags:
   - has_hand: bool (true only if human intervention/pointing/manipulation is depicted).
   - has_camera: bool (true only if observation or media perspective is depicted).

OUTPUT REQUIREMENTS:
Return ONLY a valid JSON string:
{{
  "title": "Video title",
  "description": "Short description",
  "topic_domain": "space | biology | geography | history | psychology | technology",
  "hashtags": ["#tag1", "#tag2", "#tag3"],
  "scenes": [
    {{
      "narration": "Concise, punchy voiceover narration.",
      "core_meaning": "Core meaning",
      "visual_metaphor": "3-6 concrete objects metaphor",
      "topic_domain": "space",
      "focal_keyword": "astronaut",
      "secondary_keyword": "hourglass",
      "layout_type": "hero_center",
      "has_hand": false,
      "has_camera": false,
      "color_field": "Deep Cobalt",
      "color_hex": "1D3557",
      "assembly_order": "Assembly order",
      "still_image_prompt": "Use case: ads-marketing. Asset type: final still frame...",
      "visual_description": "Short visual description",
      "duration": 5.0
    }}
  ]
}}
"""

        if language == 'vi':
            return f"""Bạn là một biên kịch video chuyên nghiệp. Hãy viết một kịch bản video về chủ đề: "{topic}".
Phong cách video: {style} ({style_desc})
Thời lượng dự kiến: khoảng {duration} giây.

YÊU CẦU ĐẦU RA:
Bạn phải trả về DUY NHẤT một chuỗi JSON hợp lệ với cấu trúc sau:
{{
  "title": "Tiêu đề video (ngắn gọn, thu hút)",
  "description": "Mô tả ngắn gọn về video",
  "hashtags": ["#hashtag1", "#hashtag2", "#hashtag3"],
  "scenes": [
    {{
      "narration": "Lời thoại nhân vật hoặc giọng đọc (voiceover). Phải tự nhiên, hấp dẫn, súc tích.",
      "visual_description": "Mô tả hình ảnh trực quan của cảnh",
      "duration": 5.0
    }}
  ]
}}

Lưu ý:
- Tổng duration của tất cả các cảnh (scenes) nên xấp xỉ {duration} giây.
- Đảm bảo đầu ra là JSON chuẩn.
- Phải dùng tiếng Việt.
"""
        else:
            return f"""You are a professional video scriptwriter. Write a video script about the topic: "{topic}".
Video style: {style} ({style_desc})
Target duration: approximately {duration} seconds.

OUTPUT REQUIREMENTS:
You must return ONLY a valid JSON string with the following structure:
{{
  "title": "Video title (short, catchy)",
  "description": "Short description of the video",
  "hashtags": ["#hashtag1", "#hashtag2", "#hashtag3"],
  "scenes": [
    {{
      "narration": "The spoken text (voiceover) for this scene. Should be natural, concise and engaging.",
      "visual_description": "Visual description of the scene",
      "duration": 5.0
    }}
  ]
}}

Notes:
- The sum of all scene durations should be approximately {duration} seconds.
- Ensure the output is valid JSON.
- Must be in English.
"""
