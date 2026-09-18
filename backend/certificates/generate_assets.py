import math
import os
from PIL import Image, ImageDraw, ImageFont, ImageFilter

ASSETS_DIR = os.path.dirname(os.path.abspath(__file__)) + "/assets"
os.makedirs(ASSETS_DIR, exist_ok=True)

def create_fxec_logo():
    """
    Official Francis Xavier Engineering College header logo.
    """
    width, height = 1500, 380
    img = Image.new("RGBA", (width, height), (255, 255, 255, 0))
    draw = ImageDraw.Draw(img)

    cx, cy = 150, 180

    # Green bottom bowl
    draw.arc([cx - 110, cy - 90, cx + 110, cy + 120], start=25, end=155, fill=(101, 163, 13, 255), width=20)
    
    bowl_poly = [
        (cx - 100, cy + 38),
        (cx - 75, cy + 95),
        (cx, cy + 118),
        (cx + 75, cy + 95),
        (cx + 100, cy + 38),
        (cx + 65, cy + 70),
        (cx, cy + 82),
        (cx - 65, cy + 70),
    ]
    draw.polygon(bowl_poly, fill=(132, 204, 22, 255))

    # Leaf 1: Purple
    leaf1 = [
        (cx - 12, cy + 28),
        (cx - 50, cy + 12),
        (cx - 82, cy - 25),
        (cx - 70, cy - 56),
        (cx - 38, cy - 38),
        (cx - 15, cy - 10),
    ]
    draw.polygon(leaf1, fill=(107, 33, 168, 255))

    # Leaf 2: Dark Green
    leaf2 = [
        (cx - 12, cy + 28),
        (cx - 20, cy - 18),
        (cx - 10, cy - 72),
        (cx + 10, cy - 72),
        (cx + 20, cy - 18),
        (cx + 12, cy + 28),
    ]
    draw.polygon(leaf2, fill=(4, 120, 87, 255))

    # Leaf 3: Lime Green
    leaf3 = [
        (cx + 12, cy + 28),
        (cx + 38, cy - 10),
        (cx + 70, cy - 38),
        (cx + 82, cy - 25),
        (cx + 50, cy + 12),
    ]
    draw.polygon(leaf3, fill=(132, 204, 22, 255))

    # Top arc
    draw.arc([cx - 110, cy - 110, cx + 110, cy + 110], start=180, end=360, fill=(101, 163, 13, 180), width=7)

    # Typography
    font_bold_path = "C:/Windows/Fonts/arialbd.ttf"
    font_reg_path = "C:/Windows/Fonts/arial.ttf"

    def get_font(path, size):
        if path and os.path.exists(path):
            return ImageFont.truetype(path, size)
        return ImageFont.load_default()

    font_main = get_font(font_bold_path, 72)
    font_box = get_font(font_bold_path, 42)
    font_sub = get_font(font_bold_path, 34)
    font_addr = get_font(font_reg_path, 30)

    navy = (15, 38, 85, 255)
    tx = 310

    # "FRANCIS XAVIER®"
    draw.text((tx, 38), "FRANCIS XAVIER", font=font_main, fill=navy)
    draw.text((tx + 645, 38), "®", font=get_font(font_bold_path, 38), fill=navy)

    # Filled Navy Box with "ENGINEERING COLLEGE"
    box_x = tx
    box_y = 135
    box_w = 640
    box_h = 58
    draw.rectangle([box_x, box_y, box_x + box_w, box_y + box_h], fill=navy)
    draw.text((box_x + 18, box_y + 6), "ENGINEERING COLLEGE", font=font_box, fill=(255, 255, 255, 255))

    # "AN AUTONOMOUS INSTITUTION"
    draw.text((tx + 2, 212), "AN AUTONOMOUS INSTITUTION", font=font_sub, fill=navy)

    # "Vannarpettai, Tirunelveli - 627 003."
    draw.text((tx + 2, 264), "Vannarpettai, Tirunelveli - 627 003.", font=font_addr, fill=(30, 58, 138, 255))

    out_path = os.path.join(ASSETS_DIR, "fxec_logo.png")
    img.save(out_path, "PNG")
    print(f"Saved {out_path}")


def create_fxec_crest():
    """
    FXEC Department Crest Shield (Gold & Navy).
    """
    size = 500
    img = Image.new("RGBA", (size, size), (255, 255, 255, 0))
    draw = ImageDraw.Draw(img)

    cx, cy = size // 2, size // 2 - 20

    shield_pts = [
        (cx - 170, cy - 170),
        (cx + 170, cy - 170),
        (cx + 170, cy + 35),
        (cx + 125, cy + 130),
        (cx, cy + 195),
        (cx - 125, cy + 130),
        (cx - 170, cy + 35),
    ]

    gold_dark = (180, 115, 15, 255)
    gold = (235, 175, 45, 255)
    gold_light = (254, 230, 130, 255)
    navy = (11, 28, 65, 255)

    draw.polygon(shield_pts, fill=gold, outline=gold_dark, width=4)

    inner_pts = [
        (cx - 152, cy - 152),
        (cx + 152, cy - 152),
        (cx + 152, cy + 28),
        (cx + 112, cy + 118),
        (cx, cy + 176),
        (cx - 112, cy + 118),
        (cx - 152, cy + 28),
    ]
    draw.polygon(inner_pts, fill=navy)

    trim_pts = [
        (cx - 138, cy - 138),
        (cx + 138, cy - 138),
        (cx + 138, cy + 22),
        (cx + 102, cy + 105),
        (cx, cy + 160),
        (cx - 102, cy + 105),
        (cx - 138, cy + 22),
    ]
    draw.polygon(trim_pts, outline=gold_light, width=3)

    # Insignia: Stylized Lightning / Gear
    lightning = [
        (cx + 12, cy - 105),
        (cx - 30, cy - 20),
        (cx + 2, cy - 20),
        (cx - 18, cy + 50),
        (cx + 36, cy - 10),
        (cx + 6, cy - 10),
    ]
    draw.polygon(lightning, fill=gold_light, outline=gold, width=2)

    font_path = "C:/Windows/Fonts/arialbd.ttf"
    if os.path.exists(font_path):
        f_crest = ImageFont.truetype(font_path, 36)
        f_sub = ImageFont.truetype(font_path, 24)
        f_banner = ImageFont.truetype(font_path, 20)
    else:
        f_crest = ImageFont.load_default()
        f_sub = ImageFont.load_default()
        f_banner = ImageFont.load_default()

    draw.text((cx - 52, cy + 60), "FXEC", font=f_crest, fill=(255, 255, 255, 255))
    draw.text((cx - 30, cy + 105), "EEE", font=f_sub, fill=gold_light)

    ribbon_pts = [
        (cx - 155, cy + 185),
        (cx - 180, cy + 170),
        (cx - 180, cy + 220),
        (cx - 155, cy + 208),
        (cx + 155, cy + 208),
        (cx + 180, cy + 220),
        (cx + 180, cy + 170),
        (cx + 155, cy + 185),
    ]
    draw.polygon(ribbon_pts, fill=gold, outline=navy, width=3)
    draw.text((cx - 86, cy + 182), "EXCELLENCE", font=f_banner, fill=navy)

    out_path = os.path.join(ASSETS_DIR, "fxec_crest.png")
    img.save(out_path, "PNG")
    print(f"Saved {out_path}")


def create_achievement_seal():
    """
    Photorealistic embossed silver Achievement seal badge with correctly rotated arc text.
    """
    size = 600
    img = Image.new("RGBA", (size, size), (255, 255, 255, 0))
    draw = ImageDraw.Draw(img)

    cx, cy = size // 2, size // 2
    r_outer = 270

    # 1. Beaded outer coin edge
    num_teeth = 56
    for i in range(num_teeth):
        angle = (2 * math.pi / num_teeth) * i
        x1 = cx + (r_outer - 15) * math.cos(angle)
        y1 = cy + (r_outer - 15) * math.sin(angle)
        draw.ellipse([x1 - 10, y1 - 10, x1 + 10, y1 + 10], fill=(195, 205, 220, 255), outline=(245, 250, 255, 255), width=2)

    # 2. Concentric silver rings
    draw.ellipse([cx - 245, cy - 245, cx + 245, cy + 245], fill=(215, 225, 235, 255), outline=(130, 145, 165, 255), width=7)
    draw.ellipse([cx - 232, cy - 232, cx + 232, cy + 232], fill=(245, 248, 252, 255), outline=(255, 255, 255, 255), width=6)
    draw.ellipse([cx - 195, cy - 195, cx + 195, cy + 195], fill=(225, 232, 240, 255), outline=(148, 163, 184, 255), width=5)
    draw.ellipse([cx - 175, cy - 175, cx + 175, cy + 175], fill=(250, 252, 255, 255), outline=(203, 213, 225, 255), width=4)

    # 3. Rotated Arc Text: "★ ACHIEVEMENT ★"
    font_path = "C:/Windows/Fonts/arialbd.ttf"
    if os.path.exists(font_path):
        f_arc = ImageFont.truetype(font_path, 34)
    else:
        f_arc = ImageFont.load_default()

    word = "★ ACHIEVEMENT ★"
    arc_radius = 142
    start_angle = 205
    end_angle = 335
    angle_step = (end_angle - start_angle) / (len(word) - 1)

    for i, ch in enumerate(word):
        ang_deg = start_angle + i * angle_step
        ang_rad = math.radians(ang_deg)

        # Character center
        tx = cx + arc_radius * math.cos(ang_rad)
        ty = cy + arc_radius * math.sin(ang_rad)

        # Create character sub-image
        char_box = 80
        char_img = Image.new("RGBA", (char_box, char_box), (255, 255, 255, 0))
        c_draw = ImageDraw.Draw(char_img)

        # Draw character in center of char_img with 3D relief
        c_draw.text((char_box // 2 - 12, char_box // 2 - 16), ch, font=f_arc, fill=(71, 85, 105, 255))

        # Rotate character so upright follows normal to circle
        # normal angle = ang_deg - 90
        rot_angle = -(ang_deg + 90)
        rotated_char = char_img.rotate(rot_angle, resample=Image.BICUBIC)

        # Paste onto main image
        img.paste(rotated_char, (int(tx - char_box // 2), int(ty - char_box // 2)), rotated_char)

    # 4. Central 5-pointed star
    star_pts = []
    r_outer_star = 80
    r_inner_star = 35
    for i in range(10):
        r = r_outer_star if i % 2 == 0 else r_inner_star
        ang = math.radians(i * 36 - 90)
        star_pts.append((cx + r * math.cos(ang), cy + 28 + r * math.sin(ang)))

    draw.polygon(star_pts, fill=(220, 230, 240, 255), outline=(110, 125, 145, 255), width=4)

    # 5. Laurel branches at bottom
    draw.arc([cx - 130, cy - 30, cx + 130, cy + 155], start=30, end=150, fill=(140, 155, 175, 255), width=7)

    out_path = os.path.join(ASSETS_DIR, "achievement_seal.png")
    img.save(out_path, "PNG")
    print(f"Saved {out_path}")

if __name__ == "__main__":
    create_fxec_logo()
    create_fxec_crest()
    create_achievement_seal()
