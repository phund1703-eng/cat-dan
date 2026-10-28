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
    def get_script_prompt(topic: str, style: str, language: str, duration: int = 60, tone_instruction: str = None) -> str:
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
        tone_section = f"\nYÊU CẦU ĐẶC BIỆT VỀ PHONG CÁCH VÀ GIỌNG ĐIỆU HÀNH VĂN (TONE OF VOICE):\n{tone_instruction.strip()}\n- Hãy đảm bảo toàn bộ lời thoại (narration) của các cảnh thể hiện triệt để phong cách này!\n" if tone_instruction and tone_instruction.strip() else ""
        if style == "collage_broll":
            if language == 'vi':
                return f"""Bạn là một biên kịch và giám đốc nghệ thuật video chuyên nghiệp theo phong cách editorial paper-collage stop-motion chuẩn repo gbro-collage-broll.
Hãy viết một kịch bản video về chủ đề: "{topic}".
Thời lượng dự kiến: khoảng {duration} giây (khoảng {max(3, duration // 7)} đến {max(4, duration // 6)} cảnh, mỗi cảnh 5-8 giây).
{tone_section}

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
6. NHỊP KỂ CHUYỆN (STORY BEATS — BẮT BUỘC):
   - Mỗi scene PHẢI có 2-4 beats trong trường "beats": các mảnh cắt dán diễn thành câu chuyện theo nhịp lời thoại, KHÔNG phải một hình minh họa đứng yên.
   - "narration_part" phải trích NGUYÊN VĂN từ "narration"; các beat nối tiếp nhau theo đúng thứ tự và phủ toàn bộ narration.
   - Mỗi beat có 1-3 elements. "role": "focal" (nhân vật chính), "secondary" (đối tượng tương tác), "prop" (đạo cụ), "label" (chữ vẽ tay).
   - "action": "enter" (bay vào từ phía "from": left/right/top/bottom), "exit" (trượt ra theo phía "to"), "emphasize" (nảy nhấn mạnh), "swap_pose" (đổi tư thế nhân vật, kèm "pose": tên tư thế như "alt"), "approach" (tiến lại gần nhân vật khác, kèm "target": keyword của nhân vật bị tiếp cận — dùng cho cảnh rượt đuổi/săn mồi), "absorb" (bị nuốt chửng: teo dần rồi biến mất — dùng cho cảnh bị ăn/bị bắt), "attack" (tấn công: lao tới + va chạm khiến đối phương rung, kèm "target"), "pulse" (đập/co bóp theo nhịp lặp — DÙNG CHO TIM ĐẬP, mạch đập, kèm "rate": số nhịp/giây), "flow" (chảy thành dòng từ phía "from" sang phía "to" — DÙNG CHO MÁU CHẢY, oxy), "divide" (phân chia: tách đôi — DÙNG CHO PHÂN BÀO), "block" (tụ lại chặn một điểm — DÙNG CHO ĐÔNG MÁU, TẮC MẠCH, kèm "target": vị trí bị chặn).
   - "keyword" tuân thủ quy tắc vật thể cụ thể 1-3 từ tiếng Anh như focal_keyword.
   - "emphasis_words": tối đa 3 từ trích NGUYÊN VĂN từ narration_part để hiện chữ nhấn theo nhịp nói.
7. QUY TẮC NGUỒN TRÍCH DẪN (BẮT BUỘC):
   - Mỗi cảnh phải có trường "fact": một câu khẳng định khoa học cốt lõi mà lời thoại của cảnh dựa vào.
   - Nếu cảnh chứa con số, năm, tỉ lệ, đơn vị đo hoặc khẳng định khoa học cụ thể, trường "sources" PHẢI có tối thiểu 1 nguồn dạng {{"title", "url", "publisher", "accessed_date"}}.
   - CHỈ ghi URL có thật mà bạn chắc chắn tồn tại của tổ chức uy tín (WHO, NASA, NOAA, Britannica, PubMed, Wikipedia, cơ quan nhà nước, trường đại học...). TUYỆT ĐỐI KHÔNG bịa URL: nếu không chắc chắn về một URL cụ thể, hãy để "sources": [] trống — hệ thống sẽ yêu cầu bổ sung sau.
   - Cảnh thuần định tính (không số liệu, không khẳng định khoa học) được phép để "sources": [].

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
      "fact": "Khẳng định khoa học cốt lõi của cảnh (một câu ngắn).",
      "sources": [{{"title": "Tiêu đề nguồn", "url": "https://...", "publisher": "Tổ chức xuất bản", "accessed_date": "YYYY-MM-DD"}}],
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
      "beats": [
        {{
          "narration_part": "trích nguyên văn một cụm lời thoại của beat này",
          "elements": [
            {{"role": "focal", "keyword": "white blood cell", "action": "enter", "from": "left", "to": "right", "pose": ""}},
            {{"role": "secondary", "keyword": "bacterium", "action": "enter", "from": "right", "to": "left", "pose": ""}}
          ],
          "emphasis_words": ["kẻ lạ mặt"]
        }}
      ],
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
5. STORY BEATS (MANDATORY):
   - Every scene MUST include 2-4 beats in the "beats" field: paper cutouts must act out
     a story following the narration rhythm, NOT a single static illustration.
   - "narration_part" must be a VERBATIM excerpt of "narration"; beats follow narration
     order and together cover the whole narration.
   - Each beat has 1-3 elements. "role": "focal" (main character), "secondary" (interacting
     object), "prop", "label" (hand-drawn text).
   - "action": "enter" (flies in from "from": left/right/top/bottom), "exit" (slides out
     toward "to"), "emphasize" (pop emphasis), "swap_pose" (character changes pose,
     with "pose": pose name like "alt").
   - "keyword" follows the concrete physical object rule (1-3 English words).
   - "emphasis_words": up to 3 words quoted VERBATIM from narration_part, shown as kinetic
     type on the narration beat.
6. SOURCE CITATION RULES (MANDATORY):
   - Every scene must include a "fact" field: one short sentence stating the core scientific claim behind the narration.
   - If a scene contains numbers, years, ratios, measurement units, or any specific scientific claim, its "sources" list MUST contain at least 1 entry: {{"title", "url", "publisher", "accessed_date"}}.
   - ONLY provide URLs you are confident actually exist from reputable organizations (WHO, NASA, NOAA, Britannica, PubMed, Wikipedia, government agencies, universities...). NEVER invent a URL: if you are not sure of an exact URL, leave "sources": [] empty — the system will request it later.
   - Purely qualitative scenes (no figures, no specific scientific claim) may leave "sources": [].

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
      "fact": "Core scientific claim of the scene (one short sentence).",
      "sources": [{{"title": "Source title", "url": "https://...", "publisher": "Publisher", "accessed_date": "YYYY-MM-DD"}}],
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
      "beats": [
        {{
          "narration_part": "verbatim excerpt of this beat's narration",
          "elements": [
            {{"role": "focal", "keyword": "astronaut", "action": "enter", "from": "left", "to": "right", "pose": ""}},
            {{"role": "secondary", "keyword": "hourglass", "action": "enter", "from": "right", "to": "left", "pose": ""}}
          ],
          "emphasis_words": ["time"]
        }}
      ],
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
      "fact": "Khẳng định khoa học cốt lõi của cảnh (một câu ngắn).",
      "sources": [{{"title": "Tiêu đề nguồn", "url": "https://...", "publisher": "Tổ chức xuất bản", "accessed_date": "YYYY-MM-DD"}}],
      "visual_description": "Mô tả hình ảnh trực quan của cảnh",
      "duration": 5.0
    }}
  ]
}}

Lưu ý:
- Tổng duration của tất cả các cảnh (scenes) nên xấp xỉ {duration} giây.
- Đảm bảo đầu ra là JSON chuẩn.
- Phải dùng tiếng Việt.
- QUY TẮC NGUỒN: cảnh có con số/năm/đơn vị đo/khẳng định khoa học thì "sources" phải có tối thiểu 1 nguồn thật (WHO, NASA, Britannica, PubMed...). KHÔNG bịa URL — không chắc thì để "sources": [] trống.
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
      "fact": "Core scientific claim of the scene (one short sentence).",
      "sources": [{{"title": "Source title", "url": "https://...", "publisher": "Publisher", "accessed_date": "YYYY-MM-DD"}}],
      "visual_description": "Visual description of the scene",
      "duration": 5.0
    }}
  ]
}}

Notes:
- The sum of all scene durations should be approximately {duration} seconds.
- Ensure the output is valid JSON.
- Must be in English.
- SOURCE RULE: scenes with numbers/years/units/scientific claims need at least 1 real source in "sources" (WHO, NASA, Britannica, PubMed...). NEVER invent a URL — leave "sources": [] empty when unsure.
"""
