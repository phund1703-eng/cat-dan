import sys
from pathlib import Path
from PIL import Image
from rembg import remove

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

art_dir = Path(r"C:\Users\phund\.gemini\antigravity\brain\863fafe5-673d-4b9c-87b0-b632bf64b3e7")
out_dir = Path("data/cache/cutouts")
out_dir.mkdir(parents=True, exist_ok=True)

pairs = [
    ("real_kitchen_knife", "real_kitchen_knife.png"),
    ("real_baguette", "real_baguette.png"),
    ("real_axe", "real_axe.png"),
    ("real_wood_log", "real_wood_log.png"),
    ("real_white_blood_cell", "biology_white_blood_cell.png"),
]

for prefix, target_name in pairs:
    matches = sorted(list(art_dir.glob(f"{prefix}_*.jpg")), key=lambda p: p.stat().st_mtime, reverse=True)
    if not matches:
        print(f"Not found: {prefix}")
        continue
    src_file = matches[0]
    print(f"Processing {src_file.name} -> {target_name}...")
    with Image.open(src_file) as img:
        img_rgb = img.convert("RGB")
        cutout = remove(img_rgb)
        # Tight crop to alpha bounding box then place centered in 512x512
        bbox = cutout.getchannel("A").getbbox()
        if bbox:
            cropped = cutout.crop(bbox)
            # scale cropped to fit 440x440
            scale = min(440 / cropped.width, 440 / cropped.height)
            cw, ch = int(cropped.width * scale), int(cropped.height * scale)
            resized = cropped.resize((cw, ch), Image.Resampling.LANCZOS)
            canvas = Image.new("RGBA", (512, 512), (0, 0, 0, 0))
            canvas.paste(resized, ((512 - cw) // 2, (512 - ch) // 2), mask=resized)
            cutout = canvas
        else:
            cutout = cutout.resize((512, 512), Image.Resampling.LANCZOS)

        dest_path = out_dir / target_name
        cutout.save(dest_path, format="PNG")
        alpha_pixels = sum(1 for p in cutout.getdata() if p[3] > 20)
        ratio = alpha_pixels / (512 * 512)
        print(f"  Saved {target_name} (alpha ratio = {ratio*100:.1f}%)")

print("All 5 assets processed successfully!")
