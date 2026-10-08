"""
AutoVideoFactory — MotionTimelineEngine (The 11 Universal Kinetic Engines)
Bộ 11 động cơ chuyển động vật lý hoàn chỉnh ở nhịp stop-motion 12fps thô mộc:
1. ENGINE_COMPRESS_SQUASH : Nén ép & Nghiền dẹp (Hero dập xuống, Target dẹp Y, phình X theo nấc giật)
2. ENGINE_SEVER_SHATTER   : Cắt xẻ & Tách đôi / Vỡ vụn (Hero chém xuống, Target tách 2 mảnh dạt sang hai bên)
3. ENGINE_EMIT_SLIDE      : Đùn trượt liên tiếp từ trong ra ngoài (Hero giữ vị trí, Action assets trượt ra liên tiếp)
4. ENGINE_CONVERGE_WRAP   : Hội tụ & Bao bọc từ ngoài vào trong (Action assets từ ngoài biên bay vào bao bọc Target)
5. ENGINE_ABSORB_DISSOLVE : Nuốt chửng & Tiêu biến (Hero nở rộng đè lên Target, Target thu nhỏ và mờ dần biến mất)
6. ENGINE_TRANSLATE_NAV   : Tịnh tiến & Hành trình (Di chuyển A -> B có góc nghiêng lượn sóng tilt_angle 12fps)
7. ENGINE_SWEEP_OSCILLATE : Soi quét dao động (Hero xoay góc qua lại quanh trục +/- 15 đến +/- 25 độ)
8. ENGINE_REVOLVE_VORTEX  : Quay quanh tâm & Lốc xoáy (Tọa độ tròn/elip [cx + R*cos, cy + R*sin] theo góc giật)
9. ENGINE_SWAP_ASSET      : Đổi tư thế / Đổi asset giữa chừng (nhân vật đổi pose theo beat, Step 6 Stage 6)
10. ENGINE_EXIT_SLIDE     : Trượt ra khỏi khung & Ẩn (element trượt theo hướng rồi visible=False)
11. ENGINE_POP_IN         : Nảy vào (pop-in overshoot 0 -> 1 theo nấc stop-motion)
12. ENGINE_PULSE          : Nhịp đập lặp (tim đập / mạch đập: phồng-xẹp theo nhịp, nấc stop-motion)
"""

import math
from typing import Dict, List, Any, Optional, Tuple
from loguru import logger


class MotionTimelineEngine:
    """
    Bộ điều phối chuyển động vật lý 12fps cho 12 động cơ chuyển động phổ quát.
    """

    # Danh mục tên 12 động cơ chuẩn
    ENGINE_COMPRESS_SQUASH = "ENGINE_COMPRESS_SQUASH"
    ENGINE_SEVER_SHATTER = "ENGINE_SEVER_SHATTER"
    ENGINE_EMIT_SLIDE = "ENGINE_EMIT_SLIDE"
    ENGINE_CONVERGE_WRAP = "ENGINE_CONVERGE_WRAP"
    ENGINE_ABSORB_DISSOLVE = "ENGINE_ABSORB_DISSOLVE"
    ENGINE_TRANSLATE_NAV = "ENGINE_TRANSLATE_NAV"
    ENGINE_SWEEP_OSCILLATE = "ENGINE_SWEEP_OSCILLATE"
    ENGINE_REVOLVE_VORTEX = "ENGINE_REVOLVE_VORTEX"
    ENGINE_SWAP_ASSET = "ENGINE_SWAP_ASSET"
    ENGINE_EXIT_SLIDE = "ENGINE_EXIT_SLIDE"
    ENGINE_POP_IN = "ENGINE_POP_IN"
    ENGINE_PULSE = "ENGINE_PULSE"

    # Hướng trượt cho EXIT_SLIDE (đơn vị: bội số kích thước khung hình)
    EXIT_DIRECTIONS = {
        "left": (-1.25, 0.0),
        "right": (1.25, 0.0),
        "top": (0.0, -1.25),
        "bottom": (0.0, 1.25),
    }

    def __init__(self, timeline: Optional[List[Dict[str, Any]]] = None, base_configs: Optional[Dict[str, Dict[str, Any]]] = None,
                 tactile_jitter_from: float = 3.8, tactile_jitter_amplitude: float = 1.2):
        self.timeline = timeline or []
        self.base_configs = base_configs or {}
        self.tactile_jitter_from = tactile_jitter_from
        self.tactile_jitter_amplitude = tactile_jitter_amplitude

    def set_timeline(self, timeline: List[Dict[str, Any]]):
        self.timeline = timeline

    def set_base_config(self, target: str, config: Dict[str, Any]):
        self.base_configs[target] = config

    # =========================================================================
    # HÀM BƯỚC NHẢY RỜI RẠC (DISCRETE STEP CALCULATION) 12FPS
    # =========================================================================
    @staticmethod
    def calc_step_ratio(t: float, t_start: float, t_end: float, steps: int = 3) -> float:
        """Tính hệ số hoàn thành theo từng nấc gián đoạn (discrete step)."""
        if t <= t_start:
            return 0.0
        if t >= t_end:
            return 1.0
        num_steps = max(1, steps)
        progress = (t - t_start) / (t_end - t_start)
        step_idx = min(num_steps, int(progress * num_steps) + 1)
        return step_idx / num_steps

    # =========================================================================
    # =========================================================================
    # ĐỘNG CƠ 1: COMPRESS & SQUASH (Nén ép & Nghiền dẹp)
    # =========================================================================
    @classmethod
    def apply_compress_squash(
        cls,
        t: float,
        time_range: Tuple[float, float],
        target_scale_x: float = 1.70,
        target_scale_y: float = 0.32,
        steps: int = 3,
        base_scale_x: float = 1.0,
        base_scale_y: float = 1.0
    ) -> Tuple[float, float]:
        ratio = cls.calc_step_ratio(t, time_range[0], time_range[1], steps)
        sx = base_scale_x + (target_scale_x - base_scale_x) * ratio
        sy = base_scale_y + (target_scale_y - base_scale_y) * ratio
        return float(sx), float(sy)

    # =========================================================================
    # ĐỘNG CƠ 2: SEVER & SHATTER (Cắt xẻ, Tách đôi & Vỡ dạt)
    # =========================================================================
    @classmethod
    def apply_sever_shatter(
        cls,
        t: float,
        impact_time: float,
        drift_direction: Tuple[float, float] = (1.0, 0.2),
        max_drift_px: float = 260.0,
        tilt_deg: float = 30.0,
        duration: float = 0.8,
        steps: int = 3
    ) -> Tuple[float, float, float]:
        """
        Returns: (offset_x, offset_y, rotation_deg)
        """
        if t < impact_time:
            return 0.0, 0.0, 0.0
        ratio = cls.calc_step_ratio(t, impact_time, impact_time + duration, steps)
        ox = drift_direction[0] * max_drift_px * ratio
        oy = drift_direction[1] * max_drift_px * ratio
        rot = tilt_deg * ratio
        return float(ox), float(oy), float(rot)

    # =========================================================================
    # ĐỘNG CƠ 3: EMIT & SLIDE (Đùn trượt liên tiếp từ trong ra ngoài)
    # =========================================================================
    @classmethod
    def apply_emit_slide(
        cls,
        t: float,
        spawn_time: float,
        slide_direction: Tuple[float, float] = (0.0, 1.0),
        distance: float = 580.0,
        duration: float = 0.85,
        steps: int = 4
    ) -> Tuple[bool, float, float, float]:
        """
        Returns: (visible, offset_x, offset_y, wobble_tilt_deg)
        """
        if t < spawn_time:
            return False, 0.0, 0.0, 0.0
        ratio = cls.calc_step_ratio(t, spawn_time, spawn_time + duration, steps)
        ox = slide_direction[0] * distance * ratio
        oy = slide_direction[1] * distance * ratio
        wobble = math.sin(ratio * math.pi * 3) * 10.0 if (0.0 < ratio < 1.0) else 0.0
        return True, float(ox), float(oy), float(wobble)

    # =========================================================================
    # ĐỘNG CƠ 4: CONVERGE & WRAP (Hội tụ & Bao bọc từ ngoài vào trong)
    # =========================================================================
    @classmethod
    def apply_converge_wrap(
        cls,
        t: float,
        start_time: float,
        start_offset: Tuple[float, float] = (750.0, -350.0),
        duration: float = 0.85,
        steps: int = 4
    ) -> Tuple[bool, float, float, float]:
        """
        Returns: (visible, offset_x, offset_y, scale)
        Từ ngoài biên hoàn toàn (start_offset 750px+) bay vào hội tụ về offset (0, 0).
        """
        if t < start_time:
            return False, float(start_offset[0]), float(start_offset[1]), 0.8
        ratio = cls.calc_step_ratio(t, start_time, start_time + duration, steps)
        ox = start_offset[0] * (1.0 - ratio)
        oy = start_offset[1] * (1.0 - ratio)
        scale = 0.8 + 0.2 * ratio
        return True, float(ox), float(oy), float(scale)

    # =========================================================================
    # ĐỘNG CƠ 5: ABSORB & DISSOLVE (Nuốt chửng, Thực bào & Tiêu biến)
    # =========================================================================
    @classmethod
    def apply_absorb_dissolve(
        cls,
        t: float,
        absorb_time: float,
        duration: float = 0.6,
        steps: int = 4
    ) -> Tuple[float, float, bool]:
        """
        Target thu nhỏ và giảm opacity biến mất hoàn toàn.
        Returns: (scale, opacity, visible)
        """
        if t < absorb_time:
            return 1.0, 1.0, True
        t_end = absorb_time + duration
        if t >= t_end:
            return 0.0, 0.0, False
        ratio = cls.calc_step_ratio(t, absorb_time, t_end, steps)
        scale = max(0.0, 1.0 - ratio)
        opacity = max(0.0, 1.0 - ratio * 0.95)
        return float(scale), float(opacity), (scale > 0.02)

    # =========================================================================
    # ĐỘNG CƠ 6: TRANSLATE & NAV (Tịnh tiến & Hành trình có góc lượn sóng)
    # =========================================================================
    @classmethod
    def apply_translate_nav(
        cls,
        t: float,
        start_pos: Tuple[float, float],
        end_pos: Tuple[float, float],
        time_range: Tuple[float, float],
        max_tilt_deg: float = 22.0,
        wave_amplitude: float = 45.0,
        steps: int = 5
    ) -> Tuple[float, float, float]:
        """
        Returns: (pos_x, pos_y, tilt_deg)
        """
        ratio = cls.calc_step_ratio(t, time_range[0], time_range[1], steps)
        curr_x = start_pos[0] + (end_pos[0] - start_pos[0]) * ratio
        curr_y = start_pos[1] + (end_pos[1] - start_pos[1]) * ratio

        # Thêm dập dềnh sóng nước wave_heave (+-45px)
        if 0.0 < ratio < 1.0:
            wave_y = math.sin(ratio * math.pi * 4) * wave_amplitude
            curr_y += wave_y

        # Tính góc nghiêng nhấp nhô theo nhịp gián đoạn
        wave_cycle = math.sin(ratio * math.pi * 3)
        tilt = max_tilt_deg * wave_cycle if (0.0 < ratio < 1.0) else 0.0
        return float(curr_x), float(curr_y), float(tilt)

    # =========================================================================
    # ĐỘNG CƠ 7: SWEEP & OSCILLATE (Soi quét dao động qua lại)
    # =========================================================================
    @classmethod
    def apply_sweep_oscillate(
        cls,
        t: float,
        time_range: Tuple[float, float],
        sweep_angle: float = 45.0,
        cycles: int = 2,
        steps_per_cycle: int = 4
    ) -> float:
        """
        Returns: rotation_deg (dao động qua lại quanh trục +/- sweep_angle)
        """
        t_start, t_end = time_range
        if t <= t_start:
            return 0.0
        if t >= t_end:
            return 0.0

        dur = t_end - t_start
        total_steps = cycles * steps_per_cycle
        ratio = cls.calc_step_ratio(t, t_start, t_end, total_steps)

        # Tính góc dao động gián đoạn
        angle = sweep_angle * math.sin(ratio * 2 * math.pi * cycles)
        return float(angle)

    # =========================================================================
    # ĐỘNG CƠ 8: REVOLVE & VORTEX (Quay quanh tâm & Lốc xoáy)
    # =========================================================================
    @classmethod
    def apply_revolve_vortex(
        cls,
        t: float,
        center_pos: Tuple[float, float],
        radius: float = 420.0,
        time_range: Tuple[float, float] = (1.2, 4.2),
        total_revolutions: float = 1.0,
        start_angle_deg: float = 0.0,
        steps: int = 8,
        spiral_in: bool = False
    ) -> Tuple[float, float, float]:
        """
        Returns: (pos_x, pos_y, rotation_deg)
        """
        t_start, t_end = time_range
        ratio = cls.calc_step_ratio(t, t_start, t_end, steps)
        curr_rev = ratio * total_revolutions
        theta = math.radians(start_angle_deg + curr_rev * 360.0)

        curr_r = radius
        if spiral_in:
            curr_r = radius * (1.0 - ratio * 0.6)

        px = center_pos[0] + curr_r * math.cos(theta)
        py = center_pos[1] + curr_r * math.sin(theta)
        rot = math.degrees(theta) + 90.0
        return float(px), float(py), float(rot)

    # =========================================================================
    # TACTILE JITTER (Rung giật xúc giác 12fps khi giữ tĩnh)
    # =========================================================================
    @staticmethod
    def apply_tactile_jitter(
        frame_idx: int,
        base_pos: Tuple[float, float],
        amplitude: float = 1.5
    ) -> Tuple[float, float]:
        pattern_x = [0.0, 1.0, -1.0, 0.5, -0.5, 1.2, -1.0, 0.0]
        pattern_y = [0.0, -1.0, 0.8, -1.2, 0.0, 1.0, -0.8, 0.5]
        jx = pattern_x[frame_idx % len(pattern_x)] * amplitude
        jy = pattern_y[(frame_idx + 3) % len(pattern_y)] * amplitude
        return float(base_pos[0] + jx), float(base_pos[1] + jy)

    # Backward compatibility
    apply_discrete_translate = apply_translate_nav

    # =========================================================================
    # ĐỘNG CƠ 12: PULSE (Nhịp đập lặp: tim đập / mạch đập / co bóp)
    # =========================================================================
    @classmethod
    def apply_pulse(
        cls,
        t: float,
        time_range: Tuple[float, float],
        pulses_per_sec: float = 1.1,
        scale_min: float = 1.0,
        scale_max: float = 1.18,
        steps_per_pulse: int = 2,
        base_scale_x: float = 1.0,
        base_scale_y: float = 1.0,
    ) -> Tuple[float, float]:
        """
        Returns: (scale_x, scale_y) — phồng-xẹp theo nhịp, lượng tử hoá theo
        nấc stop-motion. Ngoài time_range: giữ nguyên scale gốc.
        """
        t0, t1 = time_range
        if t < t0 or t >= t1:
            return float(base_scale_x), float(base_scale_y)
        cyc = ((t - t0) * pulses_per_sec) % 1.0
        q = math.floor(cyc * steps_per_pulse) / max(1, steps_per_pulse)
        thump = math.sin(math.pi * min(1.0, q)) ** 2
        amp = max(0.0, scale_max - scale_min)
        sx = base_scale_x * (1.0 + amp * thump)
        sy = base_scale_y * (1.0 + amp * thump)
        return float(sx), float(sy)

    # =========================================================================
    # Helper: nảy overshoot (dùng cho POP_IN)
    # =========================================================================
    @staticmethod
    def ease_out_back(x: float, overshoot: float = 1.70158) -> float:
        """Nảy overshoot 0 -> 1 (dùng cho POP_IN)."""
        x = min(max(x, 0.0), 1.0)
        c = overshoot
        return 1.0 + (c + 1.0) * (x - 1.0) ** 3 + c * (x - 1.0) ** 2

    # =========================================================================
    # ĐỘNG CƠ 10: EXIT SLIDE (Trượt ra khỏi khung rồi ẩn hẳn)
    # =========================================================================
    @classmethod
    def apply_exit_slide(
        cls,
        t: float,
        time_range: Tuple[float, float],
        start_pos: Tuple[float, float],
        end_pos: Tuple[float, float],
        steps: int = 4
    ) -> Tuple[float, float, bool]:
        """
        Returns: (pos_x, pos_y, visible)
        Trước t0: giữ nguyên (visible=True). Trong [t0, t1]: trượt theo nấc.
        Từ t1 trở đi: visible=False.
        """
        t0, t1 = time_range
        if t < t0:
            return float(start_pos[0]), float(start_pos[1]), True
        if t >= t1:
            return float(end_pos[0]), float(end_pos[1]), False
        ratio = cls.calc_step_ratio(t, t0, t1, steps)
        px = start_pos[0] + (end_pos[0] - start_pos[0]) * ratio
        py = start_pos[1] + (end_pos[1] - start_pos[1]) * ratio
        return float(px), float(py), True

    # =========================================================================
    # ĐỘNG CƠ 11: POP IN (Nảy vào với overshoot theo nấc stop-motion)
    # =========================================================================
    @classmethod
    def apply_pop_in(
        cls,
        t: float,
        start_time: float,
        duration: float = 0.5,
        steps: int = 3
    ) -> Tuple[bool, float]:
        """
        Returns: (visible, scale)
        Trước start_time: ẩn. Trong duration: scale nảy 0 -> overshoot -> 1.
        Sau đó: scale = 1.
        """
        if t < start_time:
            return False, 0.01
        if t >= start_time + duration:
            return True, 1.0
        ratio = (t - start_time) / max(duration, 1e-6)
        q = min(steps, int(ratio * steps) + 1) / max(steps, 1)
        return True, max(0.01, cls.ease_out_back(q))
    apply_squash_and_stretch = apply_compress_squash
    apply_sequential_spawn = apply_emit_slide

    # =========================================================================
    # TÍNH TOÁN TRẠNG THÁI KHUNG HÌNH (GET FRAME STATE)
    # =========================================================================
    def get_frame_state(self, t: float, frame_idx: int = 0, width: int = 1080, height: int = 1920) -> Dict[str, Any]:
        """
        Tính toán trạng thái tất cả các đối tượng (hero, secondary, action assets...)
        cho frame hiện tại theo đúng chỉ định của 12 Động Cơ Chuyển Động.
        """
        states: Dict[str, Dict[str, Any]] = {}

        # 1. Khởi tạo trạng thái gốc từ base_configs
        for target, cfg in self.base_configs.items():
            raw_pos = cfg.get("position", [0.5, 0.5])
            if isinstance(raw_pos, dict):
                cx = raw_pos.get("x", 0.5)
                cy = raw_pos.get("y", 0.5)
                pos_px = [cx if cx > 1.0 else cx * width, cy if cy > 1.0 else cy * height]
            else:
                pos_px = [raw_pos[0] if raw_pos[0] > 1.0 else raw_pos[0] * width,
                          raw_pos[1] if raw_pos[1] > 1.0 else raw_pos[1] * height]

            states[target] = {
                "position": [float(pos_px[0]), float(pos_px[1])],
                "scale_x": float(cfg.get("scale_x", 1.0)),
                "scale_y": float(cfg.get("scale_y", 1.0)),
                "rotation_deg": float(cfg.get("rotation_deg", 0.0)),
                "visible": bool(cfg.get("visible", True)),
                "opacity": float(cfg.get("opacity", 1.0)),
                "asset_variant": str(cfg.get("asset_variant") or "")
            }

        # 2. Duyệt qua timeline để cập nhật theo 12 Động Cơ
        for act in self.timeline:
            target = act.get("target")
            action_type = act.get("action", "").upper()
            if not target:
                continue

            if target not in states:
                states[target] = {
                    "position": [width * 0.5, height * 0.5],
                    "scale_x": 1.0,
                    "scale_y": 1.0,
                    "rotation_deg": 0.0,
                    "visible": True,
                    "opacity": 1.0,
                    "asset_variant": ""
                }

            st = states[target]

            # -----------------------------------------------------------------
            # 1. ENGINE_COMPRESS_SQUASH & SQUASH_AND_STRETCH
            # -----------------------------------------------------------------
            if action_type in [self.ENGINE_COMPRESS_SQUASH, "COMPRESS_SQUASH", "SQUASH_AND_STRETCH"]:
                time_range = act.get("time_range", [2.0, 2.8])
                target_sx = act.get("scale_x", 1.70)
                target_sy = act.get("scale_y", 0.32)
                steps = act.get("steps", 3)
                curr_sx, curr_sy = self.apply_compress_squash(
                    t, time_range, target_scale_x=target_sx, target_scale_y=target_sy,
                    steps=steps, base_scale_x=st["scale_x"], base_scale_y=st["scale_y"]
                )
                st["scale_x"] = curr_sx
                st["scale_y"] = curr_sy
                if act.get("screen_shake", False) and time_range[0] <= t <= time_range[0] + 0.35:
                    states["__screen_shake__"] = True

            # -----------------------------------------------------------------
            # 2. ENGINE_SEVER_SHATTER (Cắt xẻ & Tách đôi dạt sang hai bên)
            # -----------------------------------------------------------------
            elif action_type in [self.ENGINE_SEVER_SHATTER, "SEVER_SHATTER"]:
                impact_t = act.get("impact_time", act.get("time_range", [1.8, 2.6])[0])
                drift_dir = act.get("drift_direction", (1.0, 0.2))
                max_drift = act.get("max_drift_px", 260.0)
                tilt = act.get("tilt_deg", 30.0)
                dur = act.get("duration", 0.8)
                steps = act.get("steps", 3)

                is_severed = (t >= impact_t)
                ox, oy, rot = self.apply_sever_shatter(
                    t, impact_t, drift_direction=drift_dir,
                    max_drift_px=max_drift, tilt_deg=tilt, duration=dur, steps=steps
                )
                base_p = act.get("base_pos", st["position"])
                base_px = (base_p[0] if base_p[0] > 1.0 else base_p[0] * width,
                           base_p[1] if base_p[1] > 1.0 else base_p[1] * height)

                st["is_severed"] = is_severed
                st["position"] = [base_px[0], base_px[1]]
                st["sever_offset"] = [float(ox), float(oy)]
                st["sever_rotation"] = float(rot)
                st["sever_part_1"] = {
                    "offset_x": -ox,
                    "offset_y": oy,
                    "rotation_deg": -rot,
                    "visible": is_severed
                }
                st["sever_part_2"] = {
                    "offset_x": ox,
                    "offset_y": oy,
                    "rotation_deg": rot,
                    "visible": is_severed
                }
                if is_severed:
                    st["scale_x"] = 1.0
                    st["scale_y"] = 1.0

            # -----------------------------------------------------------------
            # 3. ENGINE_EMIT_SLIDE & SEQUENTIAL_SPAWN
            # -----------------------------------------------------------------
            elif action_type in [self.ENGINE_EMIT_SLIDE, "EMIT_SLIDE", "SEQUENTIAL_SPAWN"]:
                spawn_time = act.get("spawn_time", 1.5)
                slide_dir = act.get("slide_direction", (0.0, 1.0))
                distance = act.get("distance", 580.0)
                duration = act.get("duration", 0.85)
                steps = act.get("steps", 4)

                visible, off_x, off_y, wobble = self.apply_emit_slide(
                    t, spawn_time, slide_dir, distance, duration=duration, steps=steps
                )
                st["visible"] = visible
                if visible:
                    base_p = act.get("base_pos", st["position"])
                    base_px = (base_p[0] if base_p[0] > 1.0 else base_p[0] * width,
                               base_p[1] if base_p[1] > 1.0 else base_p[1] * height)
                    st["position"] = [base_px[0] + off_x, base_px[1] + off_y]
                    st["rotation_deg"] = wobble

            # -----------------------------------------------------------------
            # 4. ENGINE_CONVERGE_WRAP (Hội tụ bao bọc từ ngoài vào)
            # -----------------------------------------------------------------
            elif action_type in [self.ENGINE_CONVERGE_WRAP, "CONVERGE_WRAP"]:
                start_t = act.get("start_time", 1.6)
                start_off = act.get("start_offset", (750.0, -350.0))
                dur = act.get("duration", 0.85)
                steps = act.get("steps", 4)

                visible, ox, oy, sc = self.apply_converge_wrap(
                    t, start_t, start_offset=start_off, duration=dur, steps=steps
                )
                st["visible"] = visible
                if visible:
                    target_p = act.get("target_pos", st["position"])
                    target_px = (target_p[0] if target_p[0] > 1.0 else target_p[0] * width,
                                 target_p[1] if target_p[1] > 1.0 else target_p[1] * height)
                    st["position"] = [target_px[0] + ox, target_px[1] + oy]
                    st["scale_x"] = sc
                    st["scale_y"] = sc

            # -----------------------------------------------------------------
            # 5. ENGINE_ABSORB_DISSOLVE (Nuốt chửng & Tiêu biến)
            # -----------------------------------------------------------------
            elif action_type in [self.ENGINE_ABSORB_DISSOLVE, "ABSORB_DISSOLVE"]:
                absorb_t = act.get("absorb_time", 1.8)
                dur = act.get("duration", 0.6)
                steps = act.get("steps", 4)

                sc, opac, vis = self.apply_absorb_dissolve(t, absorb_t, duration=dur, steps=steps)
                st["scale_x"] = sc
                st["scale_y"] = sc
                st["opacity"] = opac
                st["visible"] = vis

            # -----------------------------------------------------------------
            # 6. ENGINE_TRANSLATE_NAV & DISCRETE_TRANSLATE
            # -----------------------------------------------------------------
            elif action_type in [self.ENGINE_TRANSLATE_NAV, "TRANSLATE_NAV", "DISCRETE_TRANSLATE"]:
                time_range = act.get("time_range", [1.0, 2.5])
                s_pos = act.get("start_pos", [0.5, 0.4])
                e_pos = act.get("end_pos", [0.5, 0.6])
                steps = act.get("steps", 4)
                tilt = act.get("max_tilt_deg", 22.0)
                wave_amp = act.get("wave_amplitude", 45.0)

                s_px = (s_pos[0] if s_pos[0] > 1.0 else s_pos[0] * width,
                        s_pos[1] if s_pos[1] > 1.0 else s_pos[1] * height)
                e_px = (e_pos[0] if e_pos[0] > 1.0 else e_pos[0] * width,
                        e_pos[1] if e_pos[1] > 1.0 else e_pos[1] * height)

                curr_x, curr_y, curr_tilt = self.apply_translate_nav(
                    t, s_px, e_px, time_range, max_tilt_deg=tilt, wave_amplitude=wave_amp, steps=steps
                )
                st["position"] = [curr_x, curr_y]
                if curr_tilt != 0.0:
                    st["rotation_deg"] = curr_tilt

            # -----------------------------------------------------------------
            # 7. ENGINE_SWEEP_OSCILLATE (Soi quét dao động)
            # -----------------------------------------------------------------
            elif action_type in [self.ENGINE_SWEEP_OSCILLATE, "SWEEP_OSCILLATE"]:
                time_range = act.get("time_range", [1.2, 3.8])
                sweep_ang = act.get("sweep_angle", 45.0)
                cycles = act.get("cycles", 2)
                steps_cyc = act.get("steps_per_cycle", 4)

                rot = self.apply_sweep_oscillate(
                    t, time_range, sweep_angle=sweep_ang, cycles=cycles, steps_per_cycle=steps_cyc
                )
                st["rotation_deg"] = rot

            # -----------------------------------------------------------------
            # 8. ENGINE_REVOLVE_VORTEX (Quay quanh tâm & Lốc xoáy)
            # -----------------------------------------------------------------
            elif action_type in [self.ENGINE_REVOLVE_VORTEX, "REVOLVE_VORTEX"]:
                center_p = act.get("center_pos", [width * 0.5, height * 0.5])
                center_px = (center_p[0] if center_p[0] > 1.0 else center_p[0] * width,
                             center_p[1] if center_p[1] > 1.0 else center_p[1] * height)
                radius = act.get("radius", 420.0)
                time_range = act.get("time_range", [1.2, 4.2])
                revs = act.get("total_revolutions", 1.0)
                start_ang = act.get("start_angle_deg", 0.0)
                steps = act.get("steps", 8)
                spiral = act.get("spiral_in", False)

                px, py, rot = self.apply_revolve_vortex(
                    t, center_px, radius=radius, time_range=time_range,
                    total_revolutions=revs, start_angle_deg=start_ang,
                    steps=steps, spiral_in=spiral
                )
                st["position"] = [px, py]
                st["rotation_deg"] = rot

                # 2.5D Depth ordering & scaling
                t_start, t_end = time_range
                ratio = self.calc_step_ratio(t, t_start, t_end, steps)
                curr_rev = ratio * revs
                theta = math.radians(start_ang + curr_rev * 360.0)
                sin_val = math.sin(theta)
                # sin_val < 0 -> behind hero; sin_val >= 0 -> in front of hero
                st["layer_order"] = "above_hero" if sin_val >= 0 else "below_hero"
                depth_scale = 1.40 if sin_val >= 0 else 0.60
                st["scale_x"] = depth_scale
                st["scale_y"] = depth_scale
                st["opacity"] = 1.0 if sin_val >= 0 else 0.85

            # -----------------------------------------------------------------
            # 9. ENGINE_SWAP_ASSET (Đổi tư thế / asset giữa chừng theo beat)
            # -----------------------------------------------------------------
            elif action_type in [self.ENGINE_SWAP_ASSET, "SWAP_ASSET"]:
                swap_time = float(act.get("swap_time", 1.0))
                pose = str(act.get("pose") or "alt")
                if t >= swap_time:
                    st["asset_variant"] = pose

            # -----------------------------------------------------------------
            # 10. ENGINE_EXIT_SLIDE (Trượt ra khỏi khung rồi ẩn hẳn)
            # -----------------------------------------------------------------
            elif action_type in [self.ENGINE_EXIT_SLIDE, "EXIT_SLIDE"]:
                time_range = act.get("time_range", [2.0, 2.8])
                steps = int(act.get("steps", 4))
                raw_end = act.get("end_pos")
                if (isinstance(raw_end, (list, tuple)) and len(raw_end) == 2):
                    end_pos = (float(raw_end[0]), float(raw_end[1]))
                else:
                    direction = str(act.get("direction") or "right").lower()
                    dx, dy = self.EXIT_DIRECTIONS.get(direction, self.EXIT_DIRECTIONS["right"])
                    end_pos = (st["position"][0] + dx * width,
                               st["position"][1] + dy * height)
                start_pos = act.get("start_pos", st["position"])
                px, py, vis = self.apply_exit_slide(
                    t, (float(time_range[0]), float(time_range[1])),
                    (float(start_pos[0]), float(start_pos[1])), end_pos,
                    steps=steps
                )
                st["position"] = [px, py]
                st["visible"] = bool(vis)

            # -----------------------------------------------------------------
            # 11. ENGINE_POP_IN (Nảy vào với overshoot)
            # -----------------------------------------------------------------
            elif action_type in [self.ENGINE_POP_IN, "POP_IN"]:
                start_t = float(act.get("start_time", 1.0))
                dur = float(act.get("duration", 0.5))
                steps = int(act.get("steps", 3))
                vis, sc = self.apply_pop_in(t, start_t, duration=dur, steps=steps)
                st["visible"] = bool(vis)
                st["scale_x"] = float(sc)
                st["scale_y"] = float(sc)

            # -----------------------------------------------------------------
            # 12. ENGINE_PULSE (Nhịp đập lặp: tim đập / mạch đập / co bóp)
            # -----------------------------------------------------------------
            elif action_type in [self.ENGINE_PULSE, "PULSE"]:
                time_range = act.get("time_range", [1.0, 3.0])
                pps = float(act.get("pulses_per_sec", 1.1))
                smax = float(act.get("scale_max", 1.18))
                steps = int(act.get("steps", 2))
                sx, sy = self.apply_pulse(
                    t, (float(time_range[0]), float(time_range[1])),
                    pulses_per_sec=pps, scale_max=smax,
                    base_scale_x=st["scale_x"], base_scale_y=st["scale_y"],
                    steps_per_pulse=steps,
                )
                st["scale_x"] = float(sx)
                st["scale_y"] = float(sy)

            # -----------------------------------------------------------------
            # ROTATE_STEP (Legacy)
            # -----------------------------------------------------------------
            elif action_type == "ROTATE_STEP":
                time_range = act.get("time_range", [1.0, 2.5])
                start_rot = act.get("start_rot", 0.0)
                end_rot = act.get("end_rot", 45.0)
                steps = act.get("steps", 3)
                ratio = self.calc_step_ratio(t, time_range[0], time_range[1], steps)
                st["rotation_deg"] = start_rot + (end_rot - start_rot) * ratio

        # 3. Áp dụng tactile jitter nếu ở giai đoạn giữ tĩnh cuối (mặc định t >= 3.8s,
        #    cấu hình được qua tactile_jitter_from / tactile_jitter_amplitude)
        if t >= self.tactile_jitter_from:
            for target, st in states.items():
                if not isinstance(st, dict):
                    continue
                if st["visible"] and st.get("opacity", 1.0) > 0.05:
                    j_pos = self.apply_tactile_jitter(frame_idx, (st["position"][0], st["position"][1]), amplitude=self.tactile_jitter_amplitude)
                    st["position"] = [j_pos[0], j_pos[1]]

        return states
