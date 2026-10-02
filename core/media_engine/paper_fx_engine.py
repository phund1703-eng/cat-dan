"""
PaperFXEngine: Stop-motion 12fps Paper Debris & Environmental Shock Engine.
Part of Cinematic Collage Theatre upgrade (AutoVideoFactory Milestone M4 - R4).

Features:
1. Procedural slicing of 3-5 sharp polygonal shards directly from secondary target's texture.
2. 1.5px cream border (#FFFDF7, (255, 253, 247, 255)) around each shard.
3. Stop-motion 12fps cone dispersion trajectory (angles -30° to -150°, burst 60-120px, apex spin ±30° to ±60°, gravity fall).
4. Environmental mechanical shock offsets (±8px) on Layer 2 (stage prop/workbench) across 4 stop-motion frames.
5. Pure Pillow and NumPy implementation (no OpenCV dependency).
"""

import math
import random
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional, Any
from PIL import Image, ImageDraw, ImageFilter, ImageChops
import numpy as np

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)


@dataclass
class DebrisParticle:
    """
    Represents a single paper debris fragment with real texture & kinematics.
    """
    image: Image.Image
    origin_pos: Tuple[float, float]
    cone_angle_rad: float
    burst_speed_px: float
    spin_step1: float
    spin_step2: float
    gravity_drop_px: float
    spin_step0: float = 0.0
    spin_step3: float = 0.0
    cluster_offset: Tuple[float, float] = (0.0, 0.0)
    polygon_points: List[Tuple[float, float]] = field(default_factory=list)


class PaperFXEngine:
    """
    Stop-motion 12fps Paper Debris & Environmental Shock Engine.
    Handles shard generation, stop-motion cone dispersion kinematics, and mechanical shock.
    """

    # Exact environmental shock offsets for shock_amplitude = 8.0 across 4 stop-motion frames:
    # Frame 0: (0.0, +8.0)
    # Frame 1: (-8.0, -6.0)
    # Frame 2: (+6.0, +4.0)
    # Frame 3: (-3.0, -2.0)
    BASE_SHOCK_PATTERN: Dict[int, Tuple[float, float]] = {
        0: (0.0, 8.0),
        1: (-8.0, -6.0),
        2: (6.0, 4.0),
        3: (-3.0, -2.0),
    }

    def __init__(self, fps: int = 12):
        self.fps = fps
        self.particles: List[DebrisParticle] = []
        self._impact_center: Tuple[int, int] = (540, 1300)

    def generate_debris_particles(
        self,
        source_image: Optional[Image.Image],
        num_particles: int = 4,
        impact_center_px: Tuple[int, int] = (540, 1300),
        outline_width: float = 1.5,
        outline_color: Tuple[int, int, int, int] = (255, 253, 247, 255)
    ) -> List[DebrisParticle]:
        """
        Slices 3-5 sharp polygonal fragments directly from source_image's texture,
        applies 1.5px cream border (#FFFDF7), and configures cone dispersion trajectory vectors.

        Args:
            source_image: PIL Image of the secondary target (e.g. wood log cutout).
            num_particles: Number of shards to slice (typically 3 to 5).
            impact_center_px: Impact point in canvas coordinates (cx, cy).
            outline_width: Cream paper outline thickness in pixels (default 1.5px).
            outline_color: RGBA color of the paper border (default #FFFDF7).

        Returns:
            List of initialized DebrisParticle objects.
        """
        num_particles = int(num_particles)
        if num_particles <= 0:
            self.particles = []
            return []

        self._impact_center = (int(impact_center_px[0]), int(impact_center_px[1]))
        outline_width = float(outline_width)

        # Validate and prepare source image
        img = self._prepare_source_texture(source_image)
        img_w, img_h = img.size

        # Identify opaque regions in the source image
        alpha = img.split()[3]
        alpha_np = np.array(alpha)
        ys, xs = np.where(alpha_np > 48)

        # Cone dispersion angle boundaries: -150° to -30° (pointing upward and sideways)
        # Note: in screen space (Y-down), negative angles point upward.
        min_rad = -5.0 * math.pi / 6.0  # -150 degrees
        max_rad = -math.pi / 6.0        # -30 degrees
        angle_span = max_rad - min_rad  # 120 degrees (2pi/3)

        particles: List[DebrisParticle] = []

        for i in range(num_particles):
            # 1. Select seed position for shard in texture
            if len(ys) > 50:
                # Sample from upper/middle region where physical impact occurs
                upper_mask = ys < np.median(ys) + (img_h * 0.15)
                up_ys = ys[upper_mask]
                up_xs = xs[upper_mask]
                if len(up_ys) > 10:
                    idx = random.randint(0, len(up_ys) - 1)
                    sx, sy = int(up_xs[idx]), int(up_ys[idx])
                else:
                    idx = random.randint(0, len(ys) - 1)
                    sx, sy = int(xs[idx]), int(ys[idx])
            else:
                sx = random.randint(img_w // 4, max(img_w // 4 + 1, 3 * img_w // 4))
                sy = random.randint(img_h // 4, max(img_h // 4 + 1, 3 * img_h // 4))

            # 2. Generate sharp polygonal vertices (3 to 5 vertices)
            num_verts = random.choice([3, 3, 4, 4, 5])
            elongation_angle = random.uniform(0.0, 2.0 * math.pi)
            shard_radius = random.uniform(16.0, 32.0)

            world_verts: List[Tuple[float, float]] = []

            for v in range(num_verts):
                # Distribute angles around circle with sharp asymmetry
                base_vert_angle = (2.0 * math.pi / num_verts) * v
                vert_angle = base_vert_angle + random.uniform(-0.35, 0.35)

                # Anisotropic stretching along elongation axis for dagger/shard sharpness
                proj = math.cos(vert_angle - elongation_angle)
                rad = shard_radius * (0.45 + 0.95 * abs(proj) + random.uniform(-0.15, 0.25))
                rad = max(6.0, rad)

                vx = sx + rad * math.cos(vert_angle)
                vy = sy + rad * math.sin(vert_angle)
                # Clamp within source texture bounds
                vx = max(0.0, min(float(img_w - 1), vx))
                vy = max(0.0, min(float(img_h - 1), vy))
                world_verts.append((vx, vy))

            # 3. Crop patch containing the polygon
            min_vx = max(0, int(math.floor(min(p[0] for p in world_verts))) - 2)
            min_vy = max(0, int(math.floor(min(p[1] for p in world_verts))) - 2)
            max_vx = min(img_w, int(math.ceil(max(p[0] for p in world_verts))) + 3)
            max_vy = min(img_h, int(math.ceil(max(p[1] for p in world_verts))) + 3)

            # Ensure minimum patch dimensions
            if max_vx - min_vx < 10:
                max_vx = min(img_w, min_vx + 10)
                min_vx = max(0, max_vx - 10)
            if max_vy - min_vy < 10:
                max_vy = min(img_h, min_vy + 10)
                min_vy = max(0, max_vy - 10)

            patch = img.crop((min_vx, min_vy, max_vx, max_vy))

            # Relative polygon coordinates inside the cropped patch
            poly_local = [(p[0] - min_vx, p[1] - min_vy) for p in world_verts]

            # 4. Mask the patch with polygon shape
            poly_mask = Image.new("L", patch.size, 0)
            ImageDraw.Draw(poly_mask).polygon(poly_local, fill=255)
            combined_alpha = ImageChops.multiply(patch.split()[3], poly_mask)

            shard_raw = patch.copy()
            shard_raw.putalpha(combined_alpha)

            # 5. Apply 1.5px cream paper border (#FFFDF7)
            shard_with_border = self._apply_cream_outline(
                shard_raw,
                outline_width=outline_width,
                outline_color=outline_color
            )

            # 6. Configure cone dispersion trajectory vectors
            if num_particles == 1:
                base_angle = -math.pi / 2.0  # straight up (-90°)
            else:
                frac = float(i) / float(num_particles - 1)
                base_angle = min_rad + frac * angle_span

            # Small random jitter while strictly keeping within [-150°, -30°]
            jitter = random.uniform(-0.10, 0.10)
            cone_angle = max(min_rad, min(max_rad, base_angle + jitter))

            # Burst speed: distance 60-120px at step 1
            burst_speed = random.uniform(65.0, 115.0)

            # Kinematic rotations
            spin_step0 = random.uniform(-6.0, 6.0)
            spin_step1 = random.uniform(-25.0, 25.0)
            spin_sign = random.choice([-1.0, 1.0])
            # Step 2: random rotation in ±30° to ±60°
            spin_step2 = spin_sign * random.uniform(30.0, 60.0)
            spin_step3 = spin_step2 + spin_sign * random.uniform(20.0, 40.0)

            # Gravity drop: 45-75px downward
            gravity_drop = random.uniform(45.0, 75.0)

            # Cluster offset at Step 0
            cluster_dx = random.uniform(-8.0, 8.0)
            cluster_dy = random.uniform(-8.0, 8.0)

            particle = DebrisParticle(
                image=shard_with_border,
                origin_pos=(float(self._impact_center[0]), float(self._impact_center[1])),
                cone_angle_rad=float(cone_angle),
                burst_speed_px=float(burst_speed),
                spin_step1=float(spin_step1),
                spin_step2=float(spin_step2),
                gravity_drop_px=float(gravity_drop),
                spin_step0=float(spin_step0),
                spin_step3=float(spin_step3),
                cluster_offset=(float(cluster_dx), float(cluster_dy)),
                polygon_points=poly_local
            )
            particles.append(particle)

        self.particles = particles
        return particles

    def get_particles_state(self, t: float, impact_time: float) -> List[Dict[str, Any]]:
        """
        Calculates render states for all particles at time t relative to impact_time.
        Evaluates stop-motion positions, rotations, and opacities across 4 frames:
        - Step 0 (t = impact_time): clustered near impact point.
        - Step 1 (t = impact_time + 1/12s): burst upward and sideways (60-120px, angles -30° to -150°).
        - Step 2 (t = impact_time + 2/12s): apex & free fall with random rotation (±30° to ±60°).
        - Step 3 (t = impact_time + 3/12s): falling downward with fading opacity.
        - Step >= 4 (t >= impact_time + 4/12s): particles vanish (empty list returned).

        Args:
            t: Current playback timestamp in seconds.
            impact_time: Timestamp of impact collision in seconds.

        Returns:
            List of dictionaries:
            [
                {
                    "image": Image.Image,
                    "position": (float, float),
                    "rotation_deg": float,
                    "opacity": float
                }
            ]
        """
        if not self.particles:
            return []

        if t < impact_time - 1e-5:
            return []

        # Calculate discrete stop-motion step index at self.fps
        dt = t - impact_time
        step = int(math.floor(dt * self.fps + 1e-4))

        if step < 0 or step >= 4:
            return []

        states: List[Dict[str, Any]] = []

        for p in self.particles:
            cx, cy = p.origin_pos

            if step == 0:
                # Step 0: Clustered near impact center
                x = cx + p.cluster_offset[0]
                y = cy + p.cluster_offset[1]
                rot = p.spin_step0
                opacity = 1.0

            elif step == 1:
                # Step 1: Burst upward and sideways along cone angle
                dx = p.burst_speed_px * math.cos(p.cone_angle_rad)
                dy = p.burst_speed_px * math.sin(p.cone_angle_rad)
                x = cx + dx
                y = cy + dy
                rot = p.spin_step1
                opacity = 1.0

            elif step == 2:
                # Step 2: Apex & free fall onset with random rotation (±30° to ±60°)
                dx = p.burst_speed_px * math.cos(p.cone_angle_rad) * 1.35
                dy = p.burst_speed_px * math.sin(p.cone_angle_rad) * 1.15 + p.gravity_drop_px * 0.25
                x = cx + dx
                y = cy + dy
                rot = p.spin_step2
                opacity = 0.90

            else:  # step == 3
                # Step 3: Falling downward with fading opacity
                dx = p.burst_speed_px * math.cos(p.cone_angle_rad) * 1.45
                dy = p.burst_speed_px * math.sin(p.cone_angle_rad) * 0.95 + p.gravity_drop_px
                x = cx + dx
                y = cy + dy
                rot = p.spin_step3
                opacity = 0.40

            states.append({
                "image": p.image,
                "position": (round(x, 1), round(y, 1)),
                "rotation_deg": round(rot, 1),
                "opacity": round(opacity, 2)
            })

        return states

    def get_environmental_shock(
        self,
        t: float,
        impact_time: float,
        shock_amplitude: float = 8.0
    ) -> Tuple[float, float]:
        """
        Calculates Layer 2 (stage prop / workbench) mechanical jitter offset (dx, dy).

        For t in [impact_time, impact_time + 4/12s]:
          Frame 0: (0.0, +8.0)
          Frame 1: (-8.0, -6.0)
          Frame 2: (+6.0, +4.0)
          Frame 3: (-3.0, -2.0)
          Otherwise: (0.0, 0.0)

        Args:
            t: Current playback timestamp in seconds.
            impact_time: Timestamp of impact collision in seconds.
            shock_amplitude: Shock amplitude scaling factor (default 8.0).

        Returns:
            Tuple (dx, dy) offset in pixels.
        """
        if t < impact_time - 1e-5:
            return (0.0, 0.0)

        dt = t - impact_time
        step = int(math.floor(dt * self.fps + 1e-4))

        if step not in self.BASE_SHOCK_PATTERN:
            return (0.0, 0.0)

        scale = float(shock_amplitude) / 8.0
        base_x, base_y = self.BASE_SHOCK_PATTERN[step]
        return (round(float(base_x * scale), 2), round(float(base_y * scale), 2))

    def reset(self) -> None:
        """Clears current active particles."""
        self.particles = []

    def __len__(self) -> int:
        return len(self.particles)

    def _prepare_source_texture(self, source_image: Optional[Image.Image]) -> Image.Image:
        """
        Ensures a valid RGBA source texture is available.
        Provides realistic procedural wood grain fallback if source_image is None or empty.
        """
        if source_image is not None:
            img = source_image.convert("RGBA") if source_image.mode != "RGBA" else source_image.copy()
            bbox = img.split()[3].getbbox()
            if bbox and (bbox[2] - bbox[0] >= 16) and (bbox[3] - bbox[1] >= 16):
                return img

        # Procedural fallback wood texture
        w, h = 240, 240
        tex = Image.new("RGBA", (w, h), (139, 90, 43, 255))
        draw = ImageDraw.Draw(tex)

        # Procedural timber bands
        for y in range(0, h, 6):
            c_jitter = random.randint(-15, 15)
            band_color = (
                max(0, min(255, 115 + c_jitter)),
                max(0, min(255, 75 + c_jitter)),
                max(0, min(255, 35 + c_jitter)),
                255
            )
            draw.line([(0, y), (w, y)], fill=band_color, width=2)

        # Cellulose noise grain
        noise_arr = np.random.randint(-20, 20, (h, w), dtype=np.int16)
        tex_arr = np.array(tex, dtype=np.int16)
        for c in range(3):
            tex_arr[:, :, c] = np.clip(tex_arr[:, :, c] + noise_arr, 0, 255)
        return Image.fromarray(tex_arr.astype(np.uint8), mode="RGBA")

    def _apply_cream_outline(
        self,
        shard_img: Image.Image,
        outline_width: float = 1.5,
        outline_color: Tuple[int, int, int, int] = (255, 253, 247, 255)
    ) -> Image.Image:
        """
        Applies precise 1.5px cream border (#FFFDF7) around shard alpha contour using pure PIL.
        Pads canvas, expands alpha contour via morphological dilation with sub-pixel sampling,
        composites cream border behind shard texture, and crops to tight bounding box.
        """
        if shard_img.mode != "RGBA":
            shard_img = shard_img.convert("RGBA")

        w, h = shard_img.size
        pad = int(math.ceil(outline_width)) + 6
        padded_w, padded_h = w + pad * 2, h + pad * 2

        padded_shard = Image.new("RGBA", (padded_w, padded_h), (0, 0, 0, 0))
        padded_shard.paste(shard_img, (pad, pad), mask=shard_img)

        alpha = padded_shard.split()[3]

        # Supersample 2x to achieve precise sub-pixel outline width (1.5px -> 3px filter radius)
        scale_factor = 2
        alpha_2x = alpha.resize((padded_w * scale_factor, padded_h * scale_factor), Image.Resampling.BILINEAR)

        # MaxFilter radius in 2x space
        filter_size = max(3, int(round(outline_width * scale_factor * 2)) + 1)
        if filter_size % 2 == 0:
            filter_size += 1

        dilated_alpha_2x = alpha_2x.filter(ImageFilter.MaxFilter(filter_size))
        dilated_alpha = dilated_alpha_2x.resize((padded_w, padded_h), Image.Resampling.LANCZOS)
        dilated_alpha = dilated_alpha.point(lambda p: 255 if p > 60 else (p * 4 if p > 10 else 0))

        # Cream outline layer
        outline_layer = Image.new("RGBA", (padded_w, padded_h), (0, 0, 0, 0))
        cream_fill = Image.new("RGBA", (padded_w, padded_h), outline_color)
        outline_layer.paste(cream_fill, (0, 0), mask=dilated_alpha)

        # Composite original shard on top of cream outline
        outline_layer.paste(padded_shard, (0, 0), mask=padded_shard)

        # Tight crop
        bbox = outline_layer.getbbox()
        if bbox:
            outline_layer = outline_layer.crop(bbox)

        return outline_layer
