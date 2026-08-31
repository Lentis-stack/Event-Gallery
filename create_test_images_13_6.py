"""Generate distinct colored test images for Phase 13.6 browser verification."""
from PIL import Image, ImageDraw, ImageFont
import os

OUTPUT_DIR = r"C:\Users\Person\Desktop\GALL\test_images_13_6"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Define all test images with distinct colors and labels
IMAGES = [
    # Hero images (3)
    ("hero_1.png", "#FF6B6B", "HERO 1"),
    ("hero_2.png", "#FF4444", "HERO 2"),
    ("hero_3.png", "#CC3333", "HERO 3"),
    # Landing slideshow (3)
    ("slide_l_1.png", "#4ECDC4", "LANDING 1"),
    ("slide_l_2.png", "#45B7AA", "LANDING 2"),
    ("slide_l_3.png", "#36A89C", "LANDING 3"),
    # Guest slideshow (3)
    ("slide_g_1.png", "#45B7D1", "GUEST 1"),
    ("slide_g_2.png", "#3AA0C0", "GUEST 2"),
    ("slide_g_3.png", "#2E8BAF", "GUEST 3"),
    # Host slideshow (3)
    ("slide_h_1.png", "#96CEB4", "HOST 1"),
    ("slide_h_2.png", "#80B89E", "HOST 2"),
    ("slide_h_3.png", "#6AA088", "HOST 3"),
    # Gallery (2)
    ("gallery_1.png", "#FFEAA7", "GALLERY 1"),
    ("gallery_2.png", "#F0D890", "GALLERY 2"),
]

WIDTH, HEIGHT = 1280, 720

for filename, color, label in IMAGES:
    img = Image.new("RGB", (WIDTH, HEIGHT), color)
    draw = ImageDraw.Draw(img)
    
    # Draw large centered label
    try:
        font = ImageFont.truetype("arial.ttf", 72)
    except:
        font = ImageFont.load_default()
    
    bbox = draw.textbbox((0, 0), label, font=font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    x = (WIDTH - tw) // 2
    y = (HEIGHT - th) // 2
    
    # Draw text with shadow
    draw.text((x + 3, y + 3), label, fill="#000000", font=font)
    draw.text((x, y), label, fill="#FFFFFF", font=font)
    
    img.save(os.path.join(OUTPUT_DIR, filename))
    print(f"Created {filename}")

print(f"\nAll {len(IMAGES)} images created in {OUTPUT_DIR}")
