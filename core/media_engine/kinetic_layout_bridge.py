import os
import math
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple
from PIL import Image
from loguru import logger


class KineticLayoutBridge:
    """
    Universal Kinetic Layout Bridge (1080x1920).
    Tự động hóa 100% việc tính toán hình học stop-motion trên khung hình dọc:
    1. Đo kích thước thật và Bounding Box Alpha của hero_asset và secondary_asset.
    2. Tự tính tỷ lệ Scale tối ưu để vừa vặn khung dọc mà không bị che lấp hoặc tràn biên.
    3. Tự động tính tọa độ va chạm (Collision Detection) dựa trên chiều cao/rộng thật.
    4. Trả về cấu trúc scene_layout hoàn chỉnh tương thích 100% với MotionTimelineEngine & GbroAdapter.
    """

    FRAME_WIDTH = 1080
    FRAME_HEIGHT = 1920

    # Bảng màu cardstock chuẩn gbro theo từng động cơ / phong cách
    ENGINE_THEMES = {
        "ENGINE_COMPRESS_SQUASH": {
            "archetype": "industrial_social",
            "color_field": "Burnt Terracotta",
            "color_hex": "D44D22",
            "environment_graphic": "ruler_scale"
        },
        "ENGINE_SEVER_SHATTER": {
            "archetype": "conceptual_duel",
            "color_field": "Plum & Gold",
            "color_hex": "4A235A",
            "environment_graphic": "coordinate_grid"
        },
        "ENGINE_EMIT_SLIDE": {
            "archetype": "specimen_scientific",
            "color_field": "Deep Cobalt",
            "color_hex": "1D3557",
            "environment_graphic": "depth_contours"
        },
        "ENGINE_CONVERGE_WRAP": {
            "archetype": "ancient_archival",
            "color_field": "Warm Ochre",
            "color_hex": "E9C46A",
            "environment_graphic": "concentric_circles"
        },
        "ENGINE_ABSORB_DISSOLVE": {
            "archetype": "specimen_scientific",
            "color_field": "Forest Sage",
            "color_hex": "2D6A4F",
            "environment_graphic": "depth_contours"
        },
        "ENGINE_TRANSLATE_NAV": {
            "archetype": "ancient_archival",
            "color_field": "Prussian Blue",
            "color_hex": "1D3557",
            "environment_graphic": "depth_contours"
        },
        "ENGINE_SWEEP_OSCILLATE": {
            "archetype": "specimen_scientific",
            "color_field": "Teal & Coral",
            "color_hex": "2A9D8F",
            "environment_graphic": "microscope_reticle"
        },
        "ENGINE_REVOLVE_VORTEX": {
            "archetype": "conceptual_duel",
            "color_field": "Plum & Gold",
            "color_hex": "4A235A",
            "environment_graphic": "coordinate_grid"
        }
    }

    @classmethod
    def measure_asset(cls, asset_path: Optional[str]) -> Tuple[int, int, Tuple[int, int, int, int]]:
        """
        Đo đạc kích thước thật và Bounding Box Alpha của asset PNG RGBA.
        Returns: (width, height, bbox)
        """
        if not asset_path or not os.path.exists(asset_path):
            return 500, 500, (0, 0, 500, 500)
        try:
            with Image.open(asset_path) as img:
                img = img.convert("RGBA")
                w, h = img.size
                bbox = img.getchannel("A").getbbox()
                if not bbox:
                    bbox = (0, 0, w, h)
                return w, h, bbox
        except Exception as e:
            logger.warning(f"Không thể đo đạc asset {asset_path}: {e}")
            return 500, 500, (0, 0, 500, 500)

    @classmethod
    def build_scene_layout(
        cls,
        engine_name: str,
        hero_asset_path: str,
        secondary_asset_path: Optional[str] = None,
        action_assets_paths: Optional[List[str]] = None,
        custom_params: Optional[Dict[str, Any]] = None,
        director_blueprint: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Tự động hóa 100% việc tính toán hình học stop-motion trên khung hình 1080x1920:
        1. Đo kích thước thật và Bounding Box Alpha của hero_asset và secondary_asset.
        2. Tự tính tỷ lệ Scale tối ưu để vừa vặn khung dọc mà không bị che lấp hoặc tràn biên.
        3. Tự động tính tọa độ va chạm (Collision Detection) dựa trên chiều cao/rộng thật.
        4. Trả về Dictionary đầy đủ cấu trúc {archetype, color_field, color_hex, environment_graphic, hero_element, secondary_element, action_assets, timeline}.
        """
        params = dict(custom_params or {})
        bp = director_blueprint or params.get("director_blueprint") or {}
        if bp and isinstance(bp, dict):
            fx_cfg = bp.get("cause_and_effect_fx", {})
            if isinstance(fx_cfg, dict):
                for k, v in fx_cfg.items():
                    if k not in params:
                        params[k] = v

        eng = engine_name.upper().strip()
        theme = cls.ENGINE_THEMES.get(eng, {
            "archetype": "specimen_scientific",
            "color_field": "Deep Cobalt",
            "color_hex": "1D3557",
            "environment_graphic": "coordinate_grid"
        })

        spatial_ctx = params.get("spatial_context") or (bp.get("spatial_context") if isinstance(bp, dict) else None)
        archetype = (spatial_ctx.get("archetype") if isinstance(spatial_ctx, dict) else None) or theme["archetype"]
        color_field = (spatial_ctx.get("color_field") if isinstance(spatial_ctx, dict) else None) or theme["color_field"]
        color_hex = (spatial_ctx.get("color_hex") if isinstance(spatial_ctx, dict) else None) or theme["color_hex"]
        env_graphic = (spatial_ctx.get("environment_graphic") if isinstance(spatial_ctx, dict) else None) or theme["environment_graphic"]

        W, H = cls.FRAME_WIDTH, cls.FRAME_HEIGHT

        # 1. Đo đạc hình học asset
        hw_raw, hh_raw, h_bbox = cls.measure_asset(hero_asset_path)
        sw_raw, sh_raw, s_bbox = cls.measure_asset(secondary_asset_path) if secondary_asset_path else (500, 500, (0, 0, 500, 500))

        # Tỷ lệ co dãn thực tế của vùng nội dung (Alpha content)
        h_content_ratio_h = (h_bbox[3] - h_bbox[1]) / max(1, hh_raw)
        s_content_ratio_h = (s_bbox[3] - s_bbox[1]) / max(1, sh_raw)

        # 2. Tự tính tỷ lệ Scale tối ưu
        hero_scale = params.get("hero_scale")
        if hero_scale is None:
            # Tối ưu cho khung hình dọc 1080px
            hero_scale = 0.46 if eng in ["ENGINE_SEVER_SHATTER", "ENGINE_COMPRESS_SQUASH"] else 0.48

        sec_scale = params.get("sec_scale")
        if sec_scale is None:
            sec_scale = 0.36 if eng in ["ENGINE_SEVER_SHATTER", "ENGINE_COMPRESS_SQUASH"] else 0.32

        # Chiều cao pixel sau khi scale
        scaled_hero_w = W * hero_scale
        scaled_hero_h = hh_raw * (scaled_hero_w / max(1, hw_raw))

        scaled_sec_w = W * sec_scale
        scaled_sec_h = sh_raw * (scaled_sec_w / max(1, sw_raw))

        timeline = []
        action_assets_cfg = []

        # =====================================================================
        # ĐỘNG CƠ 1: ENGINE_COMPRESS_SQUASH (Nén, Dập, Ép bẹp)
        # =====================================================================
        if eng == "ENGINE_COMPRESS_SQUASH":
            sec_pos_y = params.get("secondary_y", 0.68)
            sec_pos_x = params.get("secondary_x", 0.50)

            # Mặt sàn neo giữ (Bottom Ground Anchor): chân giữ nguyên trên sàn khi dẹp Y
            target_sy = params.get("scale_y", 0.32)
            target_sx = params.get("scale_x", 1.70)

            # Điểm va chạm: Hero hạ xuống chạm sát đỉnh mới của Secondary khi bị nén dẹp lép
            sec_bottom_y = (sec_pos_y * H) + (scaled_sec_h / 2.0)
            sec_squashed_top_y = sec_bottom_y - (scaled_sec_h * target_sy)
            hero_impact_y = sec_squashed_top_y - (scaled_hero_h * h_content_ratio_h / 2.0) + 16.0
            hero_impact_norm_y = round(hero_impact_y / H, 3)

            hero_start_norm_y = round(params.get("hero_start_y", 0.16), 3)

            hero_elem = {
                "name": Path(hero_asset_path).stem,
                "position": [0.50, hero_start_norm_y],
                "scale": hero_scale,
                "visible": True
            }
            sec_elem = {
                "name": Path(secondary_asset_path).stem if secondary_asset_path else "target_element",
                "position": [sec_pos_x, sec_pos_y],
                "scale": sec_scale,
                "visible": True,
                "bottom_anchor": True
            }

            impact_t = params.get("impact_time", 1.8)
            hero_start_t = params.get("hero_start_time", 1.2)

            timeline = [
                {
                    "target": "hero",
                    "action": "DISCRETE_TRANSLATE",
                    "time_range": [hero_start_t, impact_t],
                    "start_pos": [0.50, hero_start_norm_y],
                    "end_pos": [0.50, hero_impact_norm_y],
                    "steps": 3
                },
                {
                    "target": "secondary",
                    "action": "ENGINE_COMPRESS_SQUASH",
                    "time_range": [impact_t, round(impact_t + 0.75, 2)],
                    "scale_x": target_sx,
                    "scale_y": target_sy,
                    "steps": 3,
                    "screen_shake": True
                }
            ]

        # =====================================================================
        # ĐỘNG CƠ 2: ENGINE_SEVER_SHATTER (Bổ, Chặt, Chém, Cắt)
        # =====================================================================
        elif eng == "ENGINE_SEVER_SHATTER":
            sec_pos_y = params.get("secondary_y", 0.68)
            sec_pos_x = params.get("secondary_x", 0.50)

            # 1. Định hướng Lưỡi cắt (Working-End Orientation):
            hero_name = Path(hero_asset_path).stem.lower()
            is_cutting_tool = any(k in hero_name for k in [
                "axe", "knife", "blade", "sword", "cleaver", "chopper",
                "riu", "dao", "kiem", "bổ", "chém", "chặt", "cắt"
            ])
            flip_v = params.get("flip_vertical", is_cutting_tool)

            # 2. Tọa độ va chạm Cắm ngập tâm (Deep Center Penetration):
            hero_impact_norm_y = round(params.get("hero_impact_y", sec_pos_y - 0.02), 3)
            hero_start_norm_y = round(params.get("hero_start_y", 0.16), 3)

            hero_elem = {
                "name": Path(hero_asset_path).stem,
                "position": [0.50, hero_start_norm_y],
                "scale": hero_scale,
                "visible": True,
                "flip_vertical": flip_v
            }
            sec_elem = {
                "name": Path(secondary_asset_path).stem if secondary_asset_path else "target_element",
                "position": [sec_pos_x, sec_pos_y],
                "scale": sec_scale,
                "visible": True
            }

            impact_t = params.get("impact_time", 1.8)
            tilt = params.get("tilt_deg", 30.0)
            split_axis = params.get("split_axis", "vertical")
            angle_deg = params.get("angle_deg")

            # 3. Quỹ đạo Vung Bổ cực mạnh (Wind-up -35°, Strike +6°, Recoil 8px):
            recoil_px = params.get("recoil_px", 8.0)
            recoil_norm_y = round(recoil_px / H, 4)

            timeline = [
                {
                    "target": "hero",
                    "action": "DISCRETE_TRANSLATE",
                    "time_range": [1.0, 1.5],
                    "start_pos": [0.50, hero_start_norm_y],
                    "end_pos": [0.50, hero_start_norm_y],
                    "max_tilt_deg": params.get("windup_tilt_deg", -35.0),
                    "steps": 2
                },
                {
                    "target": "hero",
                    "action": "DISCRETE_TRANSLATE",
                    "time_range": [1.5, impact_t],
                    "start_pos": [0.50, hero_start_norm_y],
                    "end_pos": [0.50, hero_impact_norm_y],
                    "max_tilt_deg": params.get("strike_tilt_deg", 6.0),
                    "steps": 3
                },
                {
                    "target": "hero",
                    "action": "DISCRETE_TRANSLATE",
                    "time_range": [round(impact_t + 0.05, 2), round(impact_t + 0.55, 2)],
                    "start_pos": [0.50, hero_impact_norm_y],
                    "end_pos": [0.50, round(hero_impact_norm_y - recoil_norm_y, 4)],
                    "max_tilt_deg": 0.0,
                    "steps": 2
                },
                {
                    "target": "secondary",
                    "action": "ENGINE_SEVER_SHATTER",
                    "impact_time": impact_t,
                    "split_axis": split_axis,
                    "angle_deg": angle_deg,
                    "drift_direction": params.get("drift_direction", [1.0, 0.2]),
                    "max_drift_px": params.get("max_drift_px", 260.0),
                    "tilt_deg": tilt,
                    "duration": 0.85,
                    "steps": 3
                }
            ]

        # =====================================================================
        # ĐỘNG CƠ 3: ENGINE_EMIT_SLIDE (Phóng, Bắn, Đùn, In)
        # =====================================================================
        elif eng == "ENGINE_EMIT_SLIDE":
            hero_pos_y = params.get("hero_y", 0.36)
            hero_elem = {
                "name": Path(hero_asset_path).stem,
                "position": [0.50, hero_pos_y],
                "scale": hero_scale,
                "visible": True
            }
            sec_elem = {
                "name": "hidden_secondary",
                "position": [0.50, 0.90],
                "scale": 0.05,
                "visible": False
            }

            action_desc = params.get("verb_desc", "").lower()
            if any(w in action_desc for w in ["phóng", "bay", "lên", "launch", "rocket"]):
                slide_dir = [0.0, -1.0]
                slot_pos = [0.50, round(hero_pos_y - (scaled_hero_h / (2.0 * H)) * 0.4, 3)]
            elif any(w in action_desc for w in ["bắn", "phun", "tiết", "shoot"]):
                slide_dir = [1.0, 0.0]
                slot_pos = [round(0.50 + (scaled_hero_w / (2.0 * W)) * 0.4, 3), hero_pos_y]
            else:
                slide_dir = params.get("slide_direction", [0.0, 1.0])
                slot_pos = [0.50, round(hero_pos_y + (scaled_hero_h / (2.0 * H)) * 0.4, 3)]

            assets_list = action_assets_paths or []
            spawn_t = 1.4
            for idx, a_path in enumerate(assets_list):
                act_id = f"emit_asset_{idx + 1}"
                action_assets_cfg.append({
                    "id": act_id,
                    "path": str(a_path),
                    "scale": params.get("emit_asset_scale", 0.28),
                    "layer_order": "below_hero"
                })
                timeline.append({
                    "target": act_id,
                    "action": "ENGINE_EMIT_SLIDE",
                    "spawn_time": spawn_t,
                    "slide_direction": slide_dir,
                    "distance": params.get("distance", 580.0 + idx * 160.0),
                    "duration": 0.85,
                    "steps": 4 + idx,
                    "base_pos": slot_pos
                })
                spawn_t += 0.8

        # =====================================================================
        # ĐỘNG CƠ 4: ENGINE_CONVERGE_WRAP (Quấn, Bao bọc, Siết chặt)
        # =====================================================================
        elif eng == "ENGINE_CONVERGE_WRAP":
            hero_pos_y = params.get("hero_y", 0.50)
            hero_elem = {
                "name": Path(hero_asset_path).stem,
                "position": [0.50, hero_pos_y],
                "scale": hero_scale,
                "visible": True
            }
            sec_elem = {
                "name": "hidden_holder",
                "position": [0.50, 0.90],
                "scale": 0.05,
                "visible": False
            }

            # Phân tầng tọa độ quấn Y dọc thân thể (Cổ, Ngực, Bụng, Chân)
            tiered_y = [
                round(hero_pos_y - 0.14, 3),  # Cổ y=0.36
                round(hero_pos_y - 0.05, 3),  # Ngực y=0.45
                round(hero_pos_y + 0.05, 3),  # Bụng y=0.55
                round(hero_pos_y + 0.15, 3)   # Chân y=0.65
            ]
            alternating_tilts = [-20.0, 30.0, -15.0, 25.0]
            # Xuất phát hoàn toàn bên ngoài màn hình dọc 1080p (+-750px -> 850px)
            corner_offsets = [
                (-750.0, -450.0),
                (750.0, -350.0),
                (-750.0, 350.0),
                (750.0, 450.0)
            ]

            assets_list = action_assets_paths or []
            start_t = 1.4
            for idx, a_path in enumerate(assets_list):
                act_id = f"wrap_strip_{idx + 1}"
                off = corner_offsets[idx % len(corner_offsets)]
                target_y = tiered_y[idx % len(tiered_y)]
                action_assets_cfg.append({
                    "id": act_id,
                    "path": str(a_path),
                    "scale": params.get("wrap_strip_scale", 0.35),
                    "layer_order": "above_hero"
                })
                timeline.append({
                    "target": act_id,
                    "action": "ENGINE_CONVERGE_WRAP",
                    "start_time": start_t,
                    "start_offset": off,
                    "duration": 0.85,
                    "steps": 4,
                    "target_pos": [0.50, target_y]
                })
                start_t += 0.6

        # =====================================================================
        # ĐỘNG CƠ 5: ENGINE_ABSORB_DISSOLVE (Nuốt chửng, Thực bào, Tiêu biến)
        # =====================================================================
        elif eng == "ENGINE_ABSORB_DISSOLVE":
            hero_pos_y = params.get("hero_y", 0.48)
            sec_pos_y = params.get("secondary_y", 0.85)
            hero_elem = {
                "name": Path(hero_asset_path).stem,
                "position": [0.50, hero_pos_y],
                "scale": hero_scale,
                "visible": True
            }
            sec_elem = {
                "name": Path(secondary_asset_path).stem if secondary_asset_path else "bacterium",
                "position": [0.50, sec_pos_y],
                "scale": sec_scale,
                "visible": True
            }
            # Con mồi từ đáy màn hình y=0.85 hút xoáy vào tâm kẻ săn mồi y=0.48
            timeline = [
                {
                    "target": "secondary",
                    "action": "DISCRETE_TRANSLATE",
                    "time_range": [1.0, 1.8],
                    "start_pos": [0.50, sec_pos_y],
                    "end_pos": [0.50, hero_pos_y],
                    "steps": 4
                },
                {
                    "target": "secondary",
                    "action": "ENGINE_ABSORB_DISSOLVE",
                    "absorb_time": 1.8,
                    "duration": 0.5,
                    "steps": 3
                },
                {
                    "target": "hero",
                    "action": "SQUASH_AND_STRETCH",
                    "time_range": [1.85, 2.15],
                    "scale_x": 1.30,
                    "scale_y": 1.30,
                    "steps": 2
                },
                {
                    "target": "hero",
                    "action": "SQUASH_AND_STRETCH",
                    "time_range": [2.15, 2.45],
                    "scale_x": 1.0,
                    "scale_y": 1.0,
                    "steps": 2
                }
            ]

        # =====================================================================
        # ĐỘNG CƠ 6: ENGINE_TRANSLATE_NAV (Lướt, Lặn, Bay)
        # =====================================================================
        elif eng == "ENGINE_TRANSLATE_NAV":
            s_pos = params.get("start_pos", [0.12, 0.22])
            e_pos = params.get("end_pos", [0.88, 0.78])

            delta_x = e_pos[0] - s_pos[0]
            default_faces_left = any(k in Path(hero_asset_path).stem.lower() for k in ["sub", "tau", "fish", "shark", "ship"])
            flip_h = params.get("flip_horizontal", (delta_x > 0 and default_faces_left))

            hero_elem = {
                "name": Path(hero_asset_path).stem,
                "position": s_pos,
                "scale": hero_scale,
                "visible": True,
                "flip_horizontal": flip_h
            }
            sec_elem = {
                "name": Path(secondary_asset_path).stem if secondary_asset_path else "anchor",
                "position": [0.50, 0.85],
                "scale": sec_scale,
                "visible": True
            }
            timeline = [
                {
                    "target": "hero",
                    "action": "ENGINE_TRANSLATE_NAV",
                    "time_range": params.get("time_range", [1.0, 3.2]),
                    "start_pos": s_pos,
                    "end_pos": e_pos,
                    "max_tilt_deg": params.get("max_tilt_deg", 22.0),
                    "wave_amplitude": params.get("wave_amplitude", 45.0),
                    "steps": params.get("steps", 5)
                }
            ]

        # =====================================================================
        # ĐỘNG CƠ 7: ENGINE_SWEEP_OSCILLATE (Soi, Quét, Lắc lư)
        # =====================================================================
        elif eng == "ENGINE_SWEEP_OSCILLATE":
            hero_elem = {
                "name": Path(hero_asset_path).stem,
                "position": [0.50, 0.48],
                "scale": hero_scale,
                "visible": True,
                "pivot_point": [0.5, 1.0]
            }
            sec_elem = {
                "name": Path(secondary_asset_path).stem if secondary_asset_path else "petri_dish",
                "position": [0.50, 0.74],
                "scale": sec_scale,
                "visible": True
            }
            timeline = [
                {
                    "target": "hero",
                    "action": "ENGINE_SWEEP_OSCILLATE",
                    "time_range": params.get("time_range", [1.0, 3.4]),
                    "sweep_angle": params.get("sweep_angle", 45.0),
                    "cycles": 2,
                    "steps_per_cycle": 4
                }
            ]

        # =====================================================================
        # ĐỘNG CƠ 8: ENGINE_REVOLVE_VORTEX (Quay quanh, Quỹ đạo 2.5D)
        # =====================================================================
        elif eng == "ENGINE_REVOLVE_VORTEX":
            hero_elem = {
                "name": Path(hero_asset_path).stem,
                "position": [0.50, 0.50],
                "scale": hero_scale,
                "visible": True
            }
            sec_elem = {
                "name": Path(secondary_asset_path).stem if secondary_asset_path else "satellite",
                "position": [0.50, 0.26],
                "scale": sec_scale,
                "visible": True
            }
            timeline = [
                {
                    "target": "secondary",
                    "action": "ENGINE_REVOLVE_VORTEX",
                    "center_pos": [0.50, 0.50],
                    "radius": params.get("radius", 420.0),
                    "time_range": params.get("time_range", [1.0, 3.4]),
                    "total_revolutions": params.get("total_revolutions", 1.0),
                    "steps": params.get("steps", 8)
                }
            ]

        else:
            hero_elem = {
                "name": Path(hero_asset_path).stem,
                "position": [0.50, 0.42],
                "scale": hero_scale,
                "visible": True
            }
            sec_elem = {
                "name": Path(secondary_asset_path).stem if secondary_asset_path else "sec",
                "position": [0.50, 0.70],
                "scale": sec_scale,
                "visible": bool(secondary_asset_path)
            }

        # Trả về Scene Layout Dictionary hoàn chỉnh
        scene_layout = {
            "archetype": archetype,
            "color_field": color_field,
            "color_hex": color_hex,
            "environment_graphic": env_graphic,
            "hero_element": hero_elem,
            "secondary_element": sec_elem,
            "action_assets": action_assets_cfg,
            "timeline": timeline
        }

        # Pass-through support for 7-layer scene blueprint components
        archival_backdrop = (
            params.get("archival_backdrop")
            or (bp.get("archival_backdrop") if isinstance(bp, dict) else None)
        )
        if archival_backdrop is not None:
            scene_layout["archival_backdrop"] = archival_backdrop

        stage_prop = (
            params.get("stage_prop")
            or (bp.get("stage_prop") if isinstance(bp, dict) else None)
        )
        if stage_prop is not None:
            scene_layout["stage_prop"] = stage_prop

        paper_debris_fx = (
            params.get("paper_debris_fx")
            or (bp.get("paper_debris_fx") if isinstance(bp, dict) else None)
            or (bp.get("cause_and_effect_fx", {}).get("paper_debris_fx") if isinstance(bp, dict) else None)
            or params.get("cause_and_effect_fx", {}).get("paper_debris_fx")
        )
        if paper_debris_fx is not None:
            scene_layout["paper_debris_fx"] = paper_debris_fx

        director_accents = (
            params.get("director_accents")
            or (bp.get("director_accents") if isinstance(bp, dict) else None)
        )
        if director_accents is not None:
            scene_layout["director_accents"] = director_accents

        if bp:
            scene_layout["director_blueprint"] = bp

        return scene_layout
