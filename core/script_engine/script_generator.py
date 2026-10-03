import uuid
import json
from pathlib import Path
from typing import Dict, Any
from loguru import logger
from dotenv import load_dotenv
from .gemini_client import GeminiClient
from .scene_schema import normalize_script_scenes

load_dotenv()

class ScriptGenerator:
    """High-level script generation orchestrator."""

    def __init__(self):
        """Initializes the ScriptGenerator."""
        self.client = GeminiClient()

    async def generate(self, topic: str, style: str, language: str = 'vi', duration: int = 60, quality: str = 'standard') -> Dict[str, Any]:
        """
        Generates a complete video script.

        Args:
            topic (str): Video topic.
            style (str): Video style.
            language (str, optional): Language ('en' or 'vi'). Defaults to 'vi'.
            duration (int, optional): Duration in seconds. Defaults to 60.
            quality (str, optional): 'premium' uses pro_model (gemini-3.8-flash), 'standard' uses default_model (gemini-3.8-flash).

        Returns:
            dict: The generated script structure.
        """
        model = self.client.pro_model if quality == 'premium' else self.client.default_model
        
        logger.info(f"Generating script '{topic}' | Style: {style} | Lang: {language} | Quality: {quality}")
        
        if not self.client.api_keys:
            logger.warning("No valid Gemini API key found. Using high-quality collage template script...")
            script = self._generate_fallback_script(topic, style, language, duration)
            normalize_script_scenes(script)
            job_id = str(uuid.uuid4())[:8]
            script["job_id"] = job_id
            self._save_script(script, job_id)
            return script
            
        try:
            script = await self.client.generate_script(
                topic=topic,
                style=style,
                language=language,
                duration=duration,
                model=model
            )
        except Exception as e_gemini:
            logger.warning(f"ScriptGenerator: Gemini API unavailable or quota limit reached ({e_gemini}). Using dynamic topic-aware fallback script...")
            script = self._generate_fallback_script(topic, style, language, duration)

        script.setdefault("script_origin", "gemini")
        normalize_script_scenes(script)
        job_id = str(uuid.uuid4())[:8]
        script["job_id"] = job_id
        script["estimated_duration"] = self.estimate_duration(script)
        
        self._save_script(script, job_id)
        
        return script

    @staticmethod
    def _create_still_image_prompt(visual_metaphor: str, color_field: str, color_hex: str) -> str:
        """Creates an editorial paper-collage stop-motion still prompt adhering to gbro-collage-broll standards."""
        return (
            f"Use case: ads-marketing. Asset type: final still frame for a 9:16 image-to-video B-roll clip. "
            f"Primary request: Create a finished editorial paper-collage image expressing {visual_metaphor}. "
            f"Scene/backdrop: perfectly flat {color_field} paper field #{color_hex} with subtle uncoated paper fiber. "
            f"Style/medium: premium editorial stop-motion paper collage; black-and-white halftone photographic cut-outs "
            f"mixed with selective colored cardstock. Composition/framing: vertical 9:16 locked poster frame; "
            f"central subject within the middle 70 percent; generous clean color-field negative space; "
            f"3–6 large separable paper groups for later assemble-from-empty animation. Materials/textures: visible printed "
            f"halftone dots, crisp machine-cut edges, thin warm-cream paper keylines, soft low-opacity physical drop shadows. "
            f"Avoid: no typography, no readable letters, no numerals, no logos, no watermark, no UI, no subtitles, "
            f"no glossy 3D, no photoreal environment, no clutter."
        )

    def _generate_fallback_script(self, topic: str, style: str, language: str = 'vi', duration: int = 30) -> Dict[str, Any]:
        """
        Generates dynamic scene scripts closely tied to topic keywords and theme.
        Completely eliminates static chess board fallbacks and supports topic-aware generation
        across multiple domains (biology, space, technology, history, nature/geography, and generic science/life).
        """
        topic_clean = topic.strip()
        topic_lower = topic_clean.lower()
        scene_dur = round(float(duration) / 3.0, 1) if duration else 5.0
        scene_dur = max(4.0, scene_dur)
        is_en = language == 'en'

        bio_keywords = [
            "tế bào", "cell", "sinh học", "biology", "dna", "adn", "vi khuẩn",
            "bacteria", "virus", "não", "brain", "tim", "heart", "máu", "blood",
            "cơ thể", "body", "miễn dịch", "immune", "y học", "medicine", "sức khỏe",
            "health", "gen", "gene", "di truyền", "bạch cầu"
        ]
        space_keywords = [
            "vũ trụ", "universe", "space", "hố đen", "black hole", "sao hỏa", "mars",
            "thiên văn", "astronomy", "galaxy", "hành tinh", "planet", "ngân hà",
            "phi hành gia", "astronaut", "mặt trăng", "moon", "sao kim", "venus", "solar system"
        ]
        tech_keywords = [
            "công nghệ", "technology", "tech", "ai", "trí tuệ nhân tạo", "robot",
            "máy tính", "computer", "lập trình", "code", "coding", "dữ liệu", "data",
            "thuật toán", "algorithm", "internet", "software", "phần mềm", "bán dẫn", "chip"
        ]
        hist_keywords = [
            "lịch sử", "history", "cổ đại", "ancient", "ai cập", "egypt", "vương triều",
            "dynasty", "chiến tranh", "war", "di tích", "relic", "khảo cổ", "archaeology",
            "pharaoh", "đế chế", "empire", "văn minh", "civilization", "la mã", "rome"
        ]
        nature_keywords = [
            "đại dương", "ocean", "biển", "sea", "rừng", "forest", "núi", "mountain",
            "động vật", "animal", "môi trường", "environment", "thiên nhiên", "nature",
            "trái đất", "earth", "khí hậu", "climate", "san hô", "coral"
        ]

        if any(k in topic_lower for k in bio_keywords):
            domain = "biology"
            title = f"{topic_clean}: 3 Bí Ẩn Kỳ Diệu Của Sự Sống" if not is_en else f"{topic_clean}: 3 Wonders of Cellular Biology"
            desc = f"Khám phá các bí mật khoa học sinh học phi thường về {topic_clean}." if not is_en else f"Fascinating biological insights and facts about {topic_clean}."
            hashtags = ["#shorts", "#sinhhoc", "#tebao", "#suckhoe", "#khoahoc", "#kienthuc"] if not is_en else ["#shorts", "#biology", "#cells", "#science", "#health"]
            scenes_data = [
                {
                    "narration": "Cơ thể con người không ngừng sản sinh tế bào mới để thay thế và duy trì sự sống kỳ diệu." if not is_en else "The human body constantly produces new cells to replace old ones and sustain life.",
                    "core_meaning": "Sự tái sinh liên tục và quy mô kỳ vĩ của tế bào người",
                    "visual_metaphor": "Tế bào sinh học hình cầu phát sáng, kính hiển vi kim loại cổ điển, lam kính phòng thí nghiệm",
                    "focal_keyword": "human cell",
                    "secondary_keyword": "microscope",
                    "layout_type": "hero_center",
                    "has_hand": False,
                    "has_camera": False,
                    "color_field": "Emerald Teal",
                    "color_hex": "0E7C7B",
                    "assembly_order": "kính hiển vi -> tế bào cầu phát sáng -> lam kính phòng thí nghiệm hạ xuống",
                    "visual_description": "halftone paper collage cutout style, isolated background, emerald teal paper field, glowing cell sphere and microscope cutout with cream keyline, paper drop shadow",
                },
                {
                    "narration": "Chuỗi xoắn kép DNA nằm gọn trong nhân tế bào, mang theo mật mã di truyền hướng dẫn mọi hoạt động của sự sống." if not is_en else "The double-helix DNA strand sits inside the cell nucleus, carrying the genetic code that guides all life processes.",
                    "core_meaning": "Mật độ thông tin di truyền khổng lồ chứa trong nhân tế bào",
                    "visual_metaphor": "Chuỗi xoắn kép DNA phát sáng, ty thể tế bào, thước đo cuộn cổ điển",
                    "focal_keyword": "dna strand",
                    "secondary_keyword": "mitochondria",
                    "layout_type": "split_contrast",
                    "has_hand": False,
                    "has_camera": False,
                    "color_field": "Deep Cobalt Blue",
                    "color_hex": "1D3557",
                    "assembly_order": "chuỗi xoắn kép DNA -> ty thể năng lượng -> thước đo cuộn xoay tròn",
                    "visual_description": "halftone paper collage cutout style, isolated background, deep cobalt blue paper field, glowing dna helix cutout with cream keyline, paper drop shadow",
                },
                {
                    "narration": "Bạch cầu và đại thực bào đóng vai trò như những chiến binh dũng cảm, liên tục tuần tra và tiêu diệt các vi khuẩn xâm nhập." if not is_en else "White blood cells act as tireless microscopic warriors, continuously hunting and destroying foreign pathogens.",
                    "core_meaning": "Cơ chế miễn dịch tự vệ tinh vi bảo vệ cơ thể",
                    "visual_metaphor": "Tế bào bạch cầu dũng mãnh, lá chắn kháng thể bảo vệ, vi khuẩn tí hon",
                    "focal_keyword": "white blood cell",
                    "secondary_keyword": "antibody shield",
                    "layout_type": "surreal_interaction",
                    "has_hand": False,
                    "has_camera": False,
                    "color_field": "Crimson Coral",
                    "color_hex": "E63946",
                    "assembly_order": "bạch cầu macrophage -> tấm khiên kháng thể -> cụm vi khuẩn bị bao vây",
                    "visual_description": "halftone paper collage cutout style, isolated background, crimson coral paper field, white blood cell and antibody shield cutout with cream keyline, paper drop shadow",
                }
            ]

        elif any(k in topic_lower for k in space_keywords):
            domain = "space"
            title = f"{topic_clean}: 3 Sự Thật Thú Vị Về Vũ Trụ" if not is_en else f"{topic_clean}: 3 Fascinating Facts About Space"
            desc = f"Khám phá những bí ẩn kinh ngạc về vũ trụ qua chủ đề {topic_clean}." if not is_en else f"Mind-blowing cosmic facts and wonders about {topic_clean}."
            hashtags = ["#shorts", "#vutru", "#kienthuc", "#thienvan", "#khoahoc"] if not is_en else ["#shorts", "#space", "#astronomy", "#cosmos", "#universe"]
            scenes_data = [
                {
                    "narration": "Vũ trụ rộng lớn chứa đựng vô vàn những điều kỳ diệu vượt xa trí tưởng tượng của con người." if not is_en else "The vast universe contains countless cosmic wonders far beyond human imagination.",
                    "core_meaning": "Sự vô tận và bí ẩn của không gian",
                    "visual_metaphor": "Dải ngân hà xoắn ốc, kính viễn vọng cổ, quả địa cầu nhỏ",
                    "focal_keyword": "galaxy",
                    "secondary_keyword": "telescope",
                    "layout_type": "hero_center",
                    "has_hand": False,
                    "has_camera": False,
                    "color_field": "Deep Cobalt Blue",
                    "color_hex": "0C2340",
                    "assembly_order": "dải ngân hà -> kính viễn vọng -> quả địa cầu hạ xuống trung tâm",
                    "visual_description": "halftone paper collage cutout style, isolated background, deep cobalt blue paper field, glowing galaxy cutout with cream keyline, paper drop shadow",
                },
                {
                    "narration": "Sao Kim tự quay quanh trục vô cùng chậm chạp, khiến nhịp ngày đêm nơi đây khác hẳn Trái Đất." if not is_en else "Venus rotates extraordinarily slowly on its axis, giving it a day-night rhythm unlike anywhere else.",
                    "core_meaning": "Thời gian tương đối và sự chuyển động ngược ngạo",
                    "visual_metaphor": "Sao Kim màu đất nung, mặt đồng hồ tan chảy, lịch số xoay tròn",
                    "focal_keyword": "planet",
                    "secondary_keyword": "hourglass",
                    "layout_type": "split_contrast",
                    "has_hand": False,
                    "has_camera": False,
                    "color_field": "Burnt Terracotta",
                    "color_hex": "C84B31",
                    "assembly_order": "hành tinh sao kim -> mặt đồng hồ cong -> trang lịch bay vào",
                    "visual_description": "halftone paper collage cutout style, isolated background, burnt orange paper field, rotating venus planet cutout with cream keyline, paper drop shadow",
                },
                {
                    "narration": "Âm thanh trong không gian vũ trụ là sự im lặng tuyệt đối vì hoàn toàn không có bầu khí quyển để truyền dẫn." if not is_en else "Space is entirely silent because there is no atmosphere to carry sound waves.",
                    "core_meaning": "Sự im lặng tuyệt đối và chân không",
                    "visual_metaphor": "Nhà du hành vũ trụ trôi nổi, sóng âm bị gạch chéo, loa phóng thanh cổ",
                    "focal_keyword": "astronaut",
                    "secondary_keyword": "none",
                    "layout_type": "surreal_interaction",
                    "has_hand": False,
                    "has_camera": False,
                    "color_field": "Mustard Cardstock",
                    "color_hex": "E8A838",
                    "assembly_order": "phi hành gia trôi -> sóng âm gạch chéo -> loa phát thanh cổ",
                    "visual_description": "halftone paper collage cutout style, isolated background, mustard yellow paper field, astronaut silhouette cutout with cream keyline, paper drop shadow",
                }
            ]

        elif any(k in topic_lower for k in tech_keywords):
            domain = "technology"
            title = f"{topic_clean}: 3 Đột Phá Công Nghệ Tương Lai" if not is_en else f"{topic_clean}: 3 Tech Breakthroughs"
            desc = f"Khám phá những bước tiến công nghệ đột phá về {topic_clean}." if not is_en else f"Exploring transformative technology insights about {topic_clean}."
            hashtags = ["#shorts", "#congnghe", "#ai", "#tuonglai", "#kienthuc"] if not is_en else ["#shorts", "#tech", "#ai", "#innovation", "#future"]
            scenes_data = [
                {
                    "narration": "Trí tuệ nhân tạo và vi xử lý thế hệ mới đang tái định hình toàn bộ cách nhân loại xử lý thông tin." if not is_en else "Artificial intelligence and next-generation microchips are reshaping how humanity computes and communicates.",
                    "core_meaning": "Sức mạnh tính toán đột phá của công nghệ tương lai",
                    "visual_metaphor": "Chip vi xử lý lượng tử, bảng mạch bán dẫn phát sáng, bàn tay robot chính xác",
                    "focal_keyword": "microchip",
                    "secondary_keyword": "circuit board",
                    "layout_type": "hero_center",
                    "has_hand": False,
                    "has_camera": False,
                    "color_field": "Electric Indigo",
                    "color_hex": "1A1B4B",
                    "assembly_order": "chip vi xử lý trung tâm -> mạch bán dẫn phát sáng -> bàn tay robot thao tác",
                    "visual_description": "halftone paper collage cutout style, isolated background, dark indigo paper field, microchip and glowing circuit cutout with cream keyline, paper drop shadow",
                },
                {
                    "narration": "Các mô hình học sâu với vô vàn kết nối cho phép máy tính hiểu ngôn ngữ và sáng tạo tự nhiên như con người." if not is_en else "Vast webs of neural connections empower modern algorithms to process complex knowledge almost instantly.",
                    "core_meaning": "Mạng nơ-ron nhân tạo và khả năng suy luận số",
                    "visual_metaphor": "Mạng nơ-ron phát sáng, sợi quang học truyền dữ liệu, lăng kính pha lê quang học",
                    "focal_keyword": "neural network",
                    "secondary_keyword": "fiber optic",
                    "layout_type": "split_contrast",
                    "has_hand": False,
                    "has_camera": False,
                    "color_field": "Cyber Cyan",
                    "color_hex": "005F73",
                    "assembly_order": "mạng nơ-ron kết nối -> luồng sợi quang -> lăng kính pha lê khúc xạ",
                    "visual_description": "halftone paper collage cutout style, isolated background, cyan paper field, neural network graph cutout with cream keyline, paper drop shadow",
                },
                {
                    "narration": "Làm chủ công nghệ và thuật toán thông minh sẽ mở ra kỷ nguyên mới với tiềm năng phát triển vô hạn." if not is_en else "Mastering technological innovations unlocks boundless potential for human advancement.",
                    "core_meaning": "Sự hòa hợp giữa con người và công nghệ tương lai",
                    "visual_metaphor": "Cổng dữ liệu số tương lai, bóng đèn ý tưởng phát sáng, chìa khóa vàng mã hóa",
                    "focal_keyword": "digital portal",
                    "secondary_keyword": "light bulb",
                    "layout_type": "surreal_interaction",
                    "has_hand": False,
                    "has_camera": False,
                    "color_field": "Amber Gold",
                    "color_hex": "E9D8A6",
                    "assembly_order": "cổng dữ liệu số -> bóng đèn phát sáng -> chìa khóa mã hóa hạ xuống",
                    "visual_description": "halftone paper collage cutout style, isolated background, amber gold paper field, digital portal and light bulb cutout with cream keyline, paper drop shadow",
                }
            ]

        elif any(k in topic_lower for k in hist_keywords):
            domain = "history"
            title = f"{topic_clean}: 3 Bí Mật Lịch Sử Vượt Thời Gian" if not is_en else f"{topic_clean}: 3 Timeless Historical Secrets"
            desc = f"Hành trình khám phá những câu chuyện lịch sử kỳ vĩ về {topic_clean}." if not is_en else f"Exploring epic historical stories and secrets about {topic_clean}."
            hashtags = ["#shorts", "#lichsu", "#codai", "#khampha", "#kienthuc"] if not is_en else ["#shorts", "#history", "#ancient", "#discovery", "#knowledge"]
            scenes_data = [
                {
                    "narration": "Những trang sử lâu đời của các nền văn minh cổ đại luôn lưu giữ những bài học vô giá cho nhân loại." if not is_en else "Ancient civilizational scrolls preserve timeless lessons that continue to enlighten humanity.",
                    "core_meaning": "Dấu ấn trường tồn của di sản lịch sử",
                    "visual_metaphor": "Cuộn giấy cói cổ đại, la bàn hàng hải bằng đồng, bút lông ngỗng và bình mực",
                    "focal_keyword": "papyrus scroll",
                    "secondary_keyword": "compass",
                    "layout_type": "hero_center",
                    "has_hand": False,
                    "has_camera": False,
                    "color_field": "Vintage Ochre",
                    "color_hex": "D4A373",
                    "assembly_order": "cuộn giấy cói mở ra -> la bàn đồng cổ -> bút lông ngỗng ghi chép",
                    "visual_description": "halftone paper collage cutout style, isolated background, vintage ochre paper field, papyrus scroll and brass compass cutout with cream keyline, paper drop shadow",
                },
                {
                    "narration": "Những công trình kỳ vĩ như kim tự tháp hay đền đài cổ xưa vẫn là thách thức lớn đối với khoa học hiện đại." if not is_en else "Monumental architecture like pyramids continues to astound modern science with ancient engineering mastery.",
                    "core_meaning": "Trí tuệ kiến trúc và kỹ thuật vượt thời đại",
                    "visual_metaphor": "Kim tự tháp đá sa thạch, mặt trời vàng Ai Cập cổ, đồng hồ cát đo thế kỷ",
                    "focal_keyword": "pyramid",
                    "secondary_keyword": "hourglass",
                    "layout_type": "split_contrast",
                    "has_hand": False,
                    "has_camera": False,
                    "color_field": "Burnt Terracotta",
                    "color_hex": "C84B31",
                    "assembly_order": "kim tự tháp đá -> mặt trời vàng treo cao -> đồng hồ cát cát chảy",
                    "visual_description": "halftone paper collage cutout style, isolated background, terracotta paper field, ancient pyramid and hourglass cutout with cream keyline, paper drop shadow",
                },
                {
                    "narration": "Hiểu sâu sắc cội nguồn lịch sử giúp chúng ta nhìn nhận hiện tại sáng suốt và định hình tương lai vững bền." if not is_en else "Gaining deep insight into historical roots guides our understanding of the present and future.",
                    "core_meaning": "Sự thức tỉnh và tiếp nối dòng chảy lịch sử",
                    "visual_metaphor": "Cột đá cẩm thạch La Mã, con dấu sáp hoàng gia, cánh cổng thành cổ mở rộng",
                    "focal_keyword": "marble column",
                    "secondary_keyword": "wax seal",
                    "layout_type": "stage_prop",
                    "has_hand": False,
                    "has_camera": False,
                    "color_field": "Deep Olive",
                    "color_hex": "283618",
                    "assembly_order": "cột cẩm thạch dựng đứng -> con dấu sáp đỏ -> cánh cổng thành hé mở",
                    "visual_description": "halftone paper collage cutout style, isolated background, deep olive paper field, marble column and royal seal cutout with cream keyline, paper drop shadow",
                }
            ]

        elif any(k in topic_lower for k in nature_keywords):
            domain = "geography"
            title = f"{topic_clean}: 3 Kỳ Quan Thiên Nhiên Bí Ẩn" if not is_en else f"{topic_clean}: 3 Natural Wonders"
            desc = f"Khám phá những vẻ đẹp hoang sơ và kỳ vĩ của thiên nhiên về {topic_clean}." if not is_en else f"Discovering pristine natural wonders about {topic_clean}."
            hashtags = ["#shorts", "#thiennhien", "#daiduong", "#khampha", "#traidat"] if not is_en else ["#shorts", "#nature", "#ocean", "#wildlife", "#earth"]
            scenes_data = [
                {
                    "narration": "Dưới đáy đại dương sâu thẳm, thế giới sinh vật phát quang tồn tại trong điều kiện áp suất và bóng tối nghẹt thở." if not is_en else "In the abyss of deep oceans, bioluminescent life thrives in intense pressure and total darkness.",
                    "core_meaning": "Sự sống phi thường nơi đáy biển sâu",
                    "visual_metaphor": "Tàu ngầm thám hiểm biển sâu, sứa biển phát quang sinh học, đồng hồ áp suất hàng hải",
                    "focal_keyword": "submarine",
                    "secondary_keyword": "jellyfish",
                    "layout_type": "hero_center",
                    "has_hand": False,
                    "has_camera": False,
                    "color_field": "Ocean Abyss Navy",
                    "color_hex": "03045E",
                    "assembly_order": "tàu ngầm lặn xuống -> sứa phát quang trôi -> đồng hồ áp suất hiển thị",
                    "visual_description": "halftone paper collage cutout style, isolated background, dark ocean navy paper field, research submarine and glowing jellyfish cutout with cream keyline, paper drop shadow",
                },
                {
                    "narration": "Những rạn san hô rực rỡ là chiếc nôi nuôi dưỡng vô vàn sinh vật biển dù chỉ chiếm một phần nhỏ diện tích đại dương." if not is_en else "Vibrant coral reefs shelter a vast share of marine life while covering only a small fraction of the sea floor.",
                    "core_meaning": "Chiếc nôi đa dạng sinh học của hành tinh xanh",
                    "visual_metaphor": "Rạn san hô nhiệt đới rực rỡ, vỏ ốc hóa thạch cổ xưa, la bàn định hướng biển",
                    "focal_keyword": "coral reef",
                    "secondary_keyword": "seashell",
                    "layout_type": "split_contrast",
                    "has_hand": False,
                    "has_camera": False,
                    "color_field": "Teal Marine",
                    "color_hex": "0077B6",
                    "assembly_order": "rạn san hô mọc lên -> vỏ ốc hóa thạch -> la bàn định hướng nổi bật",
                    "visual_description": "halftone paper collage cutout style, isolated background, marine teal paper field, colorful coral reef cutout with cream keyline, paper drop shadow",
                },
                {
                    "narration": "Mỗi hệ sinh thái trên Trái Đất đều gắn kết chặt chẽ, tạo nên sự cân bằng hoàn mỹ cho sự sống muôn loài." if not is_en else "Every ecosystem on Earth connects dynamically, sustaining an intricate balance of life.",
                    "core_meaning": "Bản hòa ca cân bằng sinh thái của Mẹ Thiên Nhiên",
                    "visual_metaphor": "Đỉnh núi tuyết phủ hùng vĩ, cây đại thụ cổ thụ ngàn năm, ống nhòm dã ngoại",
                    "focal_keyword": "mountain peak",
                    "secondary_keyword": "binoculars",
                    "layout_type": "stage_prop",
                    "has_hand": False,
                    "has_camera": False,
                    "color_field": "Forest Moss Green",
                    "color_hex": "2D6A4F",
                    "assembly_order": "dãy núi tuyết nhô lên -> cây đại thụ cắm rễ -> ống nhòm dã ngoại hướng xa",
                    "visual_description": "halftone paper collage cutout style, isolated background, moss green paper field, mountain peak and ancient tree cutout with cream keyline, paper drop shadow",
                }
            ]

        else:
            domain = "science"
            title = f"{topic_clean}: 3 Điều Cốt Lõi Bạn Cần Biết" if not is_en else f"{topic_clean}: 3 Core Essentials You Must Know"
            desc = f"Phân tích trực quan và sinh động về những nguyên lý quan trọng của {topic_clean}." if not is_en else f"Clear and engaging visual exploration of key principles regarding {topic_clean}."
            clean_tag = "".join(ch for ch in topic_clean.lower() if ch.isalnum())[:12]
            hashtags = ["#shorts", "#kienthuc", "#khampha", "#phattrien", "#khoahoc"]
            if clean_tag:
                hashtags.append(f"#{clean_tag}")
            scenes_data = [
                {
                    "narration": f"Chào mừng bạn đến với góc nhìn sâu sắc và những khám phá bất ngờ nhất về {topic_clean}." if not is_en else f"Welcome to an insightful exploration uncovering the most compelling aspects of {topic_clean}.",
                    "core_meaning": f"Khởi đầu hành trình tiếp cận và giải mã {topic_clean}",
                    "visual_metaphor": "Sổ tay ghi chép bằng da cổ điển, bút mực kim loại, kính lúp quang học soi tiêu điểm",
                    "focal_keyword": "leather notebook",
                    "secondary_keyword": "magnifying glass",
                    "layout_type": "hero_center",
                    "has_hand": False,
                    "has_camera": False,
                    "color_field": "Warm Ivory",
                    "color_hex": "FAEDCD",
                    "assembly_order": "sổ tay da mở ra -> bút mực kim loại -> kính lúp soi rọi trung tâm",
                    "visual_description": "halftone paper collage cutout style, isolated background, warm ivory paper field, leather notebook and magnifying glass cutout with cream keyline, paper drop shadow",
                },
                {
                    "narration": f"Bản chất cốt lõi của {topic_clean} nằm ở những nguyên lý vận hành độc đáo mà ít người chú ý." if not is_en else f"The foundational core of {topic_clean} relies on intricate dynamics that often go unnoticed.",
                    "core_meaning": f"Phân tích các cơ chế và nguyên tắc trọng tâm của {topic_clean}",
                    "visual_metaphor": "Đồng hồ cát bằng đồng, bánh răng cơ học bằng đồng thau, thước đo độ chính xác",
                    "focal_keyword": "hourglass",
                    "secondary_keyword": "brass gear",
                    "layout_type": "split_contrast",
                    "has_hand": False,
                    "has_camera": False,
                    "color_field": "Sage Green",
                    "color_hex": "CCD5AE",
                    "assembly_order": "đồng hồ cát đồng -> bánh răng cơ học khớp nhau -> thước đo trượt vào",
                    "visual_description": "halftone paper collage cutout style, isolated background, sage green paper field, hourglass and precision gears cutout with cream keyline, paper drop shadow",
                },
                {
                    "narration": f"Hiểu rõ và vận dụng linh hoạt {topic_clean} sẽ giúp bạn làm chủ tri thức và mở ra tiềm năng mới." if not is_en else f"Mastering and applying {topic_clean} empowers informed decisions and unlocks your true potential.",
                    "core_meaning": f"Làm chủ ứng dụng thực tiễn của {topic_clean}",
                    "visual_metaphor": "Bóng đèn ý tưởng phát sáng, chiếc chìa khóa đồng cổ điển, cánh cửa ánh sáng hé mở",
                    "focal_keyword": "light bulb",
                    "secondary_keyword": "brass key",
                    "layout_type": "surreal_interaction",
                    "has_hand": False,
                    "has_camera": False,
                    "color_field": "Mustard Cardstock",
                    "color_hex": "E8A838",
                    "assembly_order": "bóng đèn phát sáng -> chìa khóa đồng -> cánh cửa hé mở luồng sáng",
                    "visual_description": "halftone paper collage cutout style, isolated background, mustard paper field, glowing light bulb and brass key cutout with cream keyline, paper drop shadow",
                }
            ]

        scenes = []
        for s in scenes_data:
            scene_dict = {
                "narration": s["narration"],
                "fact": s.get("fact") or s["core_meaning"],
                "sources": s.get("sources") or [],
                "core_meaning": s["core_meaning"],
                "visual_metaphor": s["visual_metaphor"],
                "topic_domain": domain,
                "focal_keyword": s["focal_keyword"],
                "secondary_keyword": s["secondary_keyword"],
                "layout_type": s["layout_type"],
                "has_hand": s.get("has_hand", False),
                "has_camera": s.get("has_camera", False),
                "color_field": s["color_field"],
                "color_hex": s["color_hex"],
                "assembly_order": s["assembly_order"],
                "still_image_prompt": self._create_still_image_prompt(s["visual_metaphor"], s["color_field"], s["color_hex"]),
                "visual_description": s["visual_description"],
                "duration": scene_dur
            }
            scenes.append(scene_dict)

        return {
            "title": title,
            "description": desc,
            "topic_domain": domain,
            "script_origin": "fallback",
            "hashtags": hashtags,
            "scenes": scenes,
            "estimated_duration": sum(s["duration"] for s in scenes)
        }

    async def generate_bilingual(self, topic: str, style: str, duration: int = 60) -> Dict[str, Dict[str, Any]]:
        """
        Generates scripts in both Vietnamese and English.

        Args:
            topic (str): Video topic.
            style (str): Video style.
            duration (int, optional): Target duration. Defaults to 60.

        Returns:
            dict: Dictionary with 'vi' and 'en' script dicts.
        """
        logger.info(f"Generating bilingual scripts for topic: {topic}")
        
        vi_script = await self.generate(topic, style, 'vi', duration)
        en_script = await self.generate(topic, style, 'en', duration)
        
        return {
            "vi": vi_script,
            "en": en_script
        }

    def estimate_duration(self, script: Dict[str, Any]) -> float:
        """
        Estimates the total video duration based on scene durations.

        Args:
            script (dict): The script dictionary.

        Returns:
            float: Total estimated duration in seconds.
        """
        try:
            return sum(scene.get("duration", 0) for scene in script.get("scenes", []))
        except Exception as e:
            logger.warning(f"Failed to estimate duration: {e}")
            return 0.0

    def _save_script(self, script: Dict[str, Any], job_id: str) -> None:
        """Saves the generated script to a JSON file."""
        try:
            base_dir = Path("data/scripts")
            base_dir.mkdir(parents=True, exist_ok=True)
            
            filepath = base_dir / f"{job_id}.json"
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(script, f, ensure_ascii=False, indent=4)
            logger.info(f"Saved script to {filepath}")
        except Exception as e:
            logger.error(f"Failed to save script {job_id}: {e}")
