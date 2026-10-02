import os
import sys
import math
import numpy as np
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter, ImageEnhance, ImageOps

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))
from core.media_engine.cutout_engine import CutoutEngine

BASE_DIR = Path(__file__).parent.parent / "assets" / "collage_assets"
REF_IMG_PATH = Path(r"C:\Users\phund\.gemini\antigravity\brain\cab00e24-2bf5-460a-9ed5-b6d3971602c5\.user_uploaded\media_1789661284592.png")

cutout_engine = CutoutEngine()

def extract_from_reference():
    """Extracts and enhances the pristine assets from the user reference photo."""
    if not REF_IMG_PATH.exists():
        print("Reference image not found at:", REF_IMG_PATH)
        return

    ref = Image.open(REF_IMG_PATH).convert("RGBA")
    rw, rh = ref.size # 461, 820

    # 1. Extract Giant Hand at top
    # Giant hand is roughly top 0 to 35% height, center 25% to 75% width
    hand_box = (int(rw * 0.22), int(rh * 0.02), int(rw * 0.85), int(rh * 0.38))
    hand_crop = ref.crop(hand_box)
    hand_cutout = cutout_engine.remove_background(hand_crop)
    # Enhance resolution
    hand_highres = hand_cutout.resize((int(hand_cutout.width * 2.5), int(hand_cutout.height * 2.5)), Image.Resampling.LANCZOS)
    hand_final = cutout_engine.add_paper_keyline_and_shadow(hand_highres, border_px=8)
    hand_final.save(BASE_DIR / "hands" / "giant_chess_hand.png")
    print("Saved hands/giant_chess_hand.png")

    # 2. Extract Vintage Teal Camera at bottom
    cam_box = (int(rw * 0.30), int(rh * 0.70), int(rw * 0.70), int(rh * 0.94))
    cam_crop = ref.crop(cam_box)
    cam_cutout = cutout_engine.remove_background(cam_crop)
    cam_highres = cam_cutout.resize((int(cam_cutout.width * 2.5), int(cam_cutout.height * 2.5)), Image.Resampling.LANCZOS)
    cam_final = cutout_engine.add_paper_keyline_and_shadow(cam_highres, border_px=8)
    cam_final.save(BASE_DIR / "props" / "vintage_camera.png")
    print("Saved props/vintage_camera.png")

    # 3. Extract Characters on Pedestals
    # Top character
    char_top_box = (int(rw * 0.40), int(rh * 0.19), int(rw * 0.58), int(rh * 0.40))
    c_top = cutout_engine.remove_background(ref.crop(char_top_box))
    c_top = c_top.resize((int(c_top.width * 2.5), int(c_top.height * 2.5)), Image.Resampling.LANCZOS)
    c_top_final = cutout_engine.add_paper_keyline_and_shadow(c_top, border_px=6)
    c_top_final.save(BASE_DIR / "characters" / "man_jacket_chess.png")

    # Left character (Woman in gown)
    char_left_box = (int(rw * 0.26), int(rh * 0.38), int(rw * 0.42), int(rh * 0.58))
    c_left = cutout_engine.remove_background(ref.crop(char_left_box))
    c_left = c_left.resize((int(c_left.width * 2.5), int(c_left.height * 2.5)), Image.Resampling.LANCZOS)
    c_left_final = cutout_engine.add_paper_keyline_and_shadow(c_left, border_px=6)
    c_left_final.save(BASE_DIR / "characters" / "woman_gown_chess.png")

    # Right character (Man in suit)
    char_right_box = (int(rw * 0.56), int(rh * 0.38), int(rw * 0.72), int(rh * 0.58))
    c_right = cutout_engine.remove_background(ref.crop(char_right_box))
    c_right = c_right.resize((int(c_right.width * 2.5), int(c_right.height * 2.5)), Image.Resampling.LANCZOS)
    c_right_final = cutout_engine.add_paper_keyline_and_shadow(c_right, border_px=6)
    c_right_final.save(BASE_DIR / "characters" / "man_suit_chess.png")
    print("Saved 3 character cutouts.")

def build_procedural_chessboard():
    """Builds a high-res editorial perspective chessboard."""
    size = 800
    sq = size // 8
    board = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(board)

    # Cream and tan vintage squares
    c1 = (245, 240, 225, 255) # Warm cream
    c2 = (195, 180, 160, 255) # Tan / Kraft brown

    for r in range(8):
        for c in range(8):
            color = c1 if (r + c) % 2 == 0 else c2
            draw.rectangle([c * sq, r * sq, (c + 1) * sq, (r + 1) * sq], fill=color)

    # Outer cream cardstock border
    bw = 36
    bordered = Image.new("RGBA", (size + bw * 2, size + bw * 2), (248, 245, 238, 255))
    b_draw = ImageDraw.Draw(bordered)
    b_draw.rectangle([bw - 4, bw - 4, size + bw + 4, size + bw + 4], outline=(150, 140, 130, 255), width=2)
    bordered.paste(board, (bw, bw))

    # Add subtle paper fiber texture
    noise = Image.effect_noise(bordered.size, 10).convert("L")
    bordered.paste(Image.new("RGBA", bordered.size, (0, 0, 0, 15)), mask=noise)

    # Perspective warp / tilt for 3D depth (subtle vertical compression + trapezoid)
    # Using quadrilateral transform
    w, h = bordered.size
    # Shrink top edge slightly for perspective
    pad_top = 40
    coeffs = find_perspective_coeffs(
        [(0, 0), (w, 0), (w, h), (0, h)],
        [(pad_top, 0), (w - pad_top, 0), (w, h), (0, h)]
    )
    warped = bordered.transform((w, h), Image.Transform.PERSPECTIVE, coeffs, Image.Resampling.BICUBIC)

    # Add soft drop shadow
    final_board = cutout_engine.add_paper_keyline_and_shadow(warped, border_px=10, shadow_blur=18, shadow_offset=(0, 18))
    final_board.save(BASE_DIR / "props" / "chessboard_perspective.png")
    print("Saved props/chessboard_perspective.png")

def build_lighting_cone():
    """Builds the glowing translucent yellow light cone beam matching reference."""
    w, h = 900, 1200
    cone_img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(cone_img)

    # Beam starts narrow at bottom center (where camera lens is) and expands upward
    bx, by = w // 2, h - 50 # Apex at bottom
    top_w = 780
    top_y = 60
    poly = [
        (bx - 35, by),
        (bx + 35, by),
        (bx + top_w // 2, top_y),
        (bx - top_w // 2, top_y)
    ]
    # Warm amber/yellow translucent fill #EBB534 with ~140 alpha (55% opacity)
    draw.polygon(poly, fill=(238, 185, 52, 145))

    # Soft feather blur along beam edges
    feathered = cone_img.filter(ImageFilter.GaussianBlur(3))
    feathered.save(BASE_DIR / "lighting" / "yellow_light_cone.png")
    print("Saved lighting/yellow_light_cone.png")

def find_perspective_coeffs(src_coords, dst_coords):
    matrix = []
    for (s, t), (u, v) in zip(src_coords, dst_coords):
        matrix.append([u, v, 1, 0, 0, 0, -s * u, -s * v])
        matrix.append([0, 0, 0, u, v, 1, -t * u, -t * v])
    A = np.matrix(matrix, dtype=np.float32)
    B = np.array(src_coords).reshape(8)
    res = np.dot(np.linalg.inv(A.T * A) * A.T, B)
    return np.array(res).reshape(8)

if __name__ == "__main__":
    print("Building asset library...")
    extract_from_reference()
    build_procedural_chessboard()
    build_lighting_cone()
    print("All assets successfully built in:", BASE_DIR)
