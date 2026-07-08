import math
from pathlib import Path
from django.core.management.base import BaseCommand
from django.conf import settings
from PIL import Image, ImageDraw, ImageFont
from events.models import Event

FONT_BOLD = '/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf'
FONT_REG  = '/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf'
FONT_SANS = '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'

IMG_W, IMG_H = 800, 480

# Per-event scene config: (top_color, bottom_color, accent, scene_key)
EVENT_SCENES = {
    "Children's Story Hour":          ('#1a0533', '#3d0a6e', '#f9c74f', 'kids_reading'),
    'Summer Reading Challenge Kickoff': ('#0a2744', '#1a4a8a', '#ffd166', 'adults_reading'),
    'Digital Literacy Workshop':        ('#0d1b2a', '#1b3a5c', '#06d6a0', 'adults_workshop'),
    'Author Talk: The Future of Fiction': ('#1a0a2e', '#2e1a4e', '#e040fb', 'speaker'),
    'Local History Exhibit Opening':    ('#2c1a0e', '#5a3210', '#f4a261', 'exhibit'),
    'Book Club: Science Fiction Edition': ('#0a1628', '#102040', '#00b4d8', 'book_club'),
    'Teen Creative Writing Workshop':   ('#0d2818', '#1a4a2e', '#b7e4c7', 'teens_writing'),
    'Language Learning Meet-Up':        ('#1a1a0a', '#3a3a10', '#e9c46a', 'group_talk'),
    'Film Screening: Adaptations Night': ('#080808', '#1a1a1a', '#ef233c', 'film'),
    'Annual Library Gala':              ('#1a0a0a', '#3a0a1a', '#ffd700', 'gala'),
}
DEFAULT_SCENE = ('#0a1628', '#1a2e4a', '#90e0ef', 'adults_reading')


def gradient(draw, w, h, top, bot):
    tr, tg, tb = int(top[1:3], 16), int(top[3:5], 16), int(top[5:7], 16)
    br, bg, bb = int(bot[1:3], 16), int(bot[3:5], 16), int(bot[5:7], 16)
    for y in range(h):
        r = int(tr + (br - tr) * y / h)
        g = int(tg + (bg - tg) * y / h)
        b = int(tb + (bb - tb) * y / h)
        draw.line([(0, y), (w, y)], fill=(r, g, b))


def hex_rgb(h, alpha=255):
    return (int(h[1:3], 16), int(h[3:5], 16), int(h[5:7], 16), alpha)


def floor_oval(draw, cx, cy, w, h, fill):
    draw.ellipse([cx - w // 2, cy - h // 2, cx + w // 2, cy + h // 2], fill=fill)


# ── Silhouette drawing helpers ────────────────────────────────────────────────

def draw_person_reading(draw, cx, by, scale, fill):
    """Seated person, book in lap."""
    s = scale
    # body (torso leaning forward)
    draw.ellipse([cx - 14*s, by - 58*s, cx + 14*s, by - 30*s], fill=fill)   # head
    draw.polygon([                                                               # torso
        (cx - 12*s, by - 30*s), (cx + 12*s, by - 30*s),
        (cx + 16*s, by),        (cx - 16*s, by),
    ], fill=fill)
    # legs (bent, sitting)
    draw.polygon([
        (cx - 16*s, by), (cx - 6*s, by), (cx - 10*s, by + 20*s), (cx - 22*s, by + 20*s),
    ], fill=fill)
    draw.polygon([
        (cx + 6*s, by), (cx + 16*s, by), (cx + 22*s, by + 20*s), (cx + 10*s, by + 20*s),
    ], fill=fill)
    # book
    draw.rectangle([cx - 20*s, by - 10*s, cx + 20*s, by + 4*s], fill=(220, 200, 160, 200))
    draw.line([(cx, by - 10*s), (cx, by + 4*s)], fill=(150, 130, 100, 200), width=max(1, int(round(s))))


def draw_child_reading(draw, cx, by, scale, fill):
    """Small child seated cross-legged with a big book."""
    s = scale
    draw.ellipse([cx - 10*s, by - 46*s, cx + 10*s, by - 26*s], fill=fill)
    draw.polygon([
        (cx - 9*s, by - 26*s), (cx + 9*s, by - 26*s),
        (cx + 12*s, by),       (cx - 12*s, by),
    ], fill=fill)
    draw.ellipse([cx - 18*s, by - 6*s, cx + 18*s, by + 8*s], fill=fill)  # cross legs blob
    # open book in lap
    draw.rectangle([cx - 16*s, by - 14*s, cx + 16*s, by + 2*s], fill=(240, 230, 200, 200))
    draw.line([(cx, by - 14*s), (cx, by + 2*s)], fill=(180, 150, 100, 200), width=max(1, int(round(s))))


def draw_painter(draw, cx, by, scale, fill):
    """Standing person in front of a canvas."""
    s = scale
    draw.ellipse([cx - 12*s, by - 80*s, cx + 12*s, by - 56*s], fill=fill)
    draw.polygon([
        (cx - 12*s, by - 56*s), (cx + 12*s, by - 56*s),
        (cx + 14*s, by - 20*s), (cx - 14*s, by - 20*s),
    ], fill=fill)
    # right arm raised (painting)
    draw.polygon([
        (cx + 12*s, by - 52*s), (cx + 18*s, by - 52*s),
        (cx + 30*s, by - 72*s), (cx + 24*s, by - 76*s),
    ], fill=fill)
    # brush tip
    draw.ellipse([cx + 27*s, by - 78*s, cx + 33*s, by - 72*s], fill=(200, 80, 80, 220))
    # legs
    draw.rectangle([cx - 14*s, by - 20*s, cx - 2*s, by + 20*s], fill=fill)
    draw.rectangle([cx + 2*s, by - 20*s, cx + 14*s, by + 20*s], fill=fill)
    # canvas easel
    ex = cx + 48*s
    draw.rectangle([ex - 18*s, by - 75*s, ex + 18*s, by - 20*s], fill=(200, 180, 140, 160))
    draw.line([(ex, by - 20*s), (ex - 10*s, by + 20*s)], fill=(120, 100, 70, 180), width=max(1, int(round(s))))
    draw.line([(ex, by - 20*s), (ex + 10*s, by + 20*s)], fill=(120, 100, 70, 180), width=max(1, int(round(s))))


def draw_musician(draw, cx, by, scale, fill, instrument='violin'):
    """Standing musician holding instrument."""
    s = scale
    draw.ellipse([cx - 11*s, by - 78*s, cx + 11*s, by - 56*s], fill=fill)
    draw.polygon([
        (cx - 11*s, by - 56*s), (cx + 11*s, by - 56*s),
        (cx + 13*s, by - 18*s), (cx - 13*s, by - 18*s),
    ], fill=fill)
    draw.rectangle([cx - 13*s, by - 18*s, cx - 2*s, by + 22*s], fill=fill)
    draw.rectangle([cx + 2*s, by - 18*s, cx + 13*s, by + 22*s], fill=fill)
    if instrument == 'violin':
        # arm holding violin
        draw.polygon([
            (cx - 11*s, by - 52*s), (cx - 6*s, by - 52*s),
            (cx - 28*s, by - 34*s), (cx - 34*s, by - 38*s),
        ], fill=fill)
        # violin body
        vx, vy = cx - 32*s, by - 42*s
        draw.ellipse([vx - 8*s, vy - 14*s, vx + 8*s, vy + 14*s], fill=(140, 80, 40, 220))
        # bow arm raised
        draw.polygon([
            (cx + 11*s, by - 54*s), (cx + 16*s, by - 50*s),
            (cx + 36*s, by - 72*s), (cx + 30*s, by - 76*s),
        ], fill=fill)
        draw.line([(cx + 33*s, by - 74*s), (cx + 20*s, by - 54*s)],
                  fill=(220, 200, 160, 200), width=max(1, int(round(s))))
    elif instrument == 'guitar':
        draw.polygon([
            (cx + 11*s, by - 50*s), (cx + 6*s, by - 50*s),
            (cx + 14*s, by - 14*s), (cx + 20*s, by - 18*s),
        ], fill=fill)
        gx, gy = cx + 18*s, by - 30*s
        draw.ellipse([gx - 9*s, gy - 16*s, gx + 9*s, gy + 16*s], fill=(120, 70, 30, 220))
        draw.line([(gx, gy - 16*s), (gx, gy - 36*s)], fill=(80, 50, 20, 220), width=max(2, int(round(2*s))))
    elif instrument == 'piano_keys':
        # pianist seated at keyboard
        kx, ky = cx + 20*s, by - 10*s
        draw.rectangle([kx - 30*s, ky - 6*s, kx + 30*s, ky + 6*s], fill=(230, 225, 215, 220))
        for i in range(7):
            draw.line([(kx - 28*s + i * 8*s, ky - 6*s),
                       (kx - 28*s + i * 8*s, ky + 6*s)], fill=(150, 140, 130, 180), width=max(1, int(round(s))))


def draw_dancer(draw, cx, by, scale, fill):
    """Dancing figure with arm and leg raised."""
    s = scale
    draw.ellipse([cx - 11*s, by - 80*s, cx + 11*s, by - 58*s], fill=fill)
    draw.polygon([
        (cx - 10*s, by - 58*s), (cx + 10*s, by - 58*s),
        (cx + 18*s, by - 22*s), (cx - 8*s, by - 22*s),
    ], fill=fill)
    # left arm raised
    draw.polygon([
        (cx - 10*s, by - 54*s), (cx - 4*s, by - 54*s),
        (cx - 22*s, by - 76*s), (cx - 28*s, by - 70*s),
    ], fill=fill)
    # right arm out
    draw.polygon([
        (cx + 10*s, by - 50*s), (cx + 14*s, by - 46*s),
        (cx + 34*s, by - 38*s), (cx + 30*s, by - 32*s),
    ], fill=fill)
    # standing leg
    draw.rectangle([cx - 6*s, by - 22*s, cx + 4*s, by + 22*s], fill=fill)
    # raised leg
    draw.polygon([
        (cx + 8*s, by - 22*s), (cx + 16*s, by - 22*s),
        (cx + 32*s, by - 2*s),  (cx + 24*s, by + 2*s),
    ], fill=fill)


def draw_speaker(draw, cx, by, scale, fill):
    """Standing person at a podium, one arm gesturing."""
    s = scale
    draw.ellipse([cx - 11*s, by - 80*s, cx + 11*s, by - 58*s], fill=fill)
    draw.polygon([
        (cx - 11*s, by - 58*s), (cx + 11*s, by - 58*s),
        (cx + 12*s, by - 18*s), (cx - 12*s, by - 18*s),
    ], fill=fill)
    draw.polygon([
        (cx + 10*s, by - 52*s), (cx + 15*s, by - 50*s),
        (cx + 30*s, by - 36*s), (cx + 25*s, by - 30*s),
    ], fill=fill)
    draw.rectangle([cx - 12*s, by - 18*s, cx - 2*s, by + 22*s], fill=fill)
    draw.rectangle([cx + 2*s, by - 18*s, cx + 12*s, by + 22*s], fill=fill)
    # podium
    px = cx - 30*s
    draw.polygon([
        (px - 20*s, by - 30*s), (px + 20*s, by - 30*s),
        (px + 16*s, by + 22*s), (px - 16*s, by + 22*s),
    ], fill=(80, 60, 40, 180))
    draw.rectangle([px - 22*s, by - 32*s, px + 22*s, by - 28*s], fill=(100, 80, 50, 200))


def draw_bookshelf(draw, x, y, w, h, fill):
    shelf_fill = (fill[0], fill[1], fill[2], 100)
    draw.rectangle([x, y, x + w, y + h], fill=shelf_fill)
    num_shelves = 3
    for i in range(num_shelves):
        sy = y + (i + 1) * h // (num_shelves + 1)
        draw.line([(x, sy), (x + w, sy)], fill=(fill[0], fill[1], fill[2], 140), width=2)


def draw_stars(draw, w, h, accent, count=40):
    import random
    random.seed(42)
    ar, ag, ab = int(accent[1:3], 16), int(accent[3:5], 16), int(accent[5:7], 16)
    for _ in range(count):
        sx, sy = random.randint(0, w), random.randint(0, h // 2)
        alpha = random.randint(60, 180)
        r = random.choice([1, 1, 1, 2])
        draw.ellipse([sx - r, sy - r, sx + r, sy + r], fill=(ar, ag, ab, alpha))


def draw_lights(draw, w, h, accent):
    ar, ag, ab = int(accent[1:3], 16), int(accent[3:5], 16), int(accent[5:7], 16)
    for i in range(6):
        lx = int(w * (i + 0.5) / 6)
        ly = 30
        draw.ellipse([lx - 14, ly - 14, lx + 14, ly + 14], fill=(ar, ag, ab, 60))
        draw.ellipse([lx - 8, ly - 8, lx + 8, ly + 8], fill=(ar, ag, ab, 120))
        draw.line([(lx, 0), (lx, ly - 14)], fill=(ar, ag, ab, 80), width=1)


def draw_music_notes(draw, accent, positions):
    ar, ag, ab = int(accent[1:3], 16), int(accent[3:5], 16), int(accent[5:7], 16)
    for (nx, ny, sz) in positions:
        draw.ellipse([nx - sz, ny, nx + sz, ny + sz], fill=(ar, ag, ab, 160))
        draw.line([(nx + sz, ny + sz), (nx + sz, ny - sz * 2)],
                  fill=(ar, ag, ab, 160), width=max(1, sz // 3))


# ── Scene composers ───────────────────────────────────────────────────────────

def compose_kids_reading(img, draw, w, h, accent):
    sil = (175, 135, 65, 255)
    ground_y = int(h * 0.82)
    draw.rectangle([0, ground_y, w, h], fill=(20, 12, 4, 200))
    draw_bookshelf(draw, 20, h // 4, 60, h // 2, (210, 170, 100))
    draw_bookshelf(draw, w - 80, h // 4, 60, h // 2, (210, 170, 100))
    positions = [
        (int(w * 0.22), ground_y, 1.6, 'child'),
        (int(w * 0.40), ground_y, 1.8, 'child'),
        (int(w * 0.58), ground_y, 1.6, 'child'),
        (int(w * 0.75), ground_y, 1.5, 'adult'),
    ]
    for cx, by, sc, kind in positions:
        if kind == 'child':
            draw_child_reading(draw, cx, by, sc, sil)
        else:
            draw_person_reading(draw, cx, by, sc, sil)
    ar, ag, ab = int(accent[1:3], 16), int(accent[3:5], 16), int(accent[5:7], 16)
    for _ in range(8):
        import random; random.seed(7)
        for _ in range(8):
            sx = random.randint(100, w - 100)
            sy = random.randint(h // 3, ground_y - 20)
            draw.ellipse([sx - 3, sy - 3, sx + 3, sy + 3], fill=(ar, ag, ab, 80))


def compose_adults_reading(img, draw, w, h, accent):
    sil = (165, 120, 55, 255)
    ground_y = int(h * 0.83)
    draw.rectangle([0, ground_y, w, h], fill=(15, 10, 4, 200))
    draw_bookshelf(draw, 0, h // 5, 55, int(h * 0.6), (200, 155, 80))
    positions = [
        (int(w * 0.25), ground_y, 1.8),
        (int(w * 0.45), ground_y, 1.9),
        (int(w * 0.65), ground_y, 1.7),
        (int(w * 0.82), ground_y, 1.8),
    ]
    for cx, by, sc in positions:
        draw_person_reading(draw, cx, by, sc, sil)
    draw_stars(draw, w, h, accent, 25)


def compose_adults_workshop(img, draw, w, h, accent):
    sil = (130, 155, 175, 255)
    ground_y = int(h * 0.82)
    draw.rectangle([0, ground_y, w, h], fill=(10, 10, 10, 210))
    ar, ag, ab = int(accent[1:3], 16), int(accent[3:5], 16), int(accent[5:7], 16)
    # laptop glow rectangles on table
    for i in range(4):
        lx = int(w * (0.18 + i * 0.2))
        draw.rectangle([lx - 20, ground_y - 28, lx + 20, ground_y - 4],
                       fill=(ar, ag, ab, 60))
    positions = [
        (int(w * 0.18), ground_y, 1.6),
        (int(w * 0.36), ground_y, 1.8),
        (int(w * 0.54), ground_y, 1.7),
        (int(w * 0.72), ground_y, 1.6),
        (int(w * 0.88), ground_y, 1.7),
    ]
    for cx, by, sc in positions:
        draw_person_reading(draw, cx, by, sc, sil)


def compose_speaker(img, draw, w, h, accent):
    sil = (170, 125, 60, 255)
    ground_y = int(h * 0.82)
    draw.rectangle([0, ground_y, w, h], fill=(10, 5, 5, 200))
    ar, ag, ab = int(accent[1:3], 16), int(accent[3:5], 16), int(accent[5:7], 16)
    # spotlight cone
    draw.polygon([(w // 2, 0), (w // 2 - 90, ground_y), (w // 2 + 90, ground_y)],
                 fill=(ar, ag, ab, 35))
    draw_speaker(draw, w // 2, ground_y, 2.2, sil)
    # audience — slightly darker than speaker
    audience_sil = (100, 75, 35, 220)
    for i in range(6):
        ax = int(w * (0.08 + i * 0.15))
        draw_person_reading(draw, ax, ground_y, 1.3, audience_sil)


def compose_exhibit(img, draw, w, h, accent):
    sil = (160, 115, 50, 255)
    ground_y = int(h * 0.82)
    draw.rectangle([0, ground_y, w, h], fill=(20, 12, 4, 200))
    ar, ag, ab = int(accent[1:3], 16), int(accent[3:5], 16), int(accent[5:7], 16)
    # framed pictures on wall
    for i in range(3):
        fx = int(w * (0.22 + i * 0.28))
        fy = int(h * 0.12)
        fw, fh = 100, 125
        draw.rectangle([fx, fy, fx + fw, fy + fh], fill=(70, 52, 28, 220))
        draw.rectangle([fx + 8, fy + 8, fx + fw - 8, fy + fh - 8],
                       fill=(ar, ag, ab, 70))
        draw.rectangle([fx - 3, fy - 3, fx + fw + 3, fy + fh + 3],
                       outline=(ar, ag, ab, 180), width=3)
        draw.line([(fx + fw // 2, fy + fh), (fx + fw // 2, ground_y)],
                  fill=(80, 55, 25, 140), width=1)
    positions = [(int(w * 0.25), ground_y, 1.7),
                 (int(w * 0.50), ground_y, 1.8),
                 (int(w * 0.75), ground_y, 1.7)]
    for cx, by, sc in positions:
        draw_person_reading(draw, cx, by, sc, sil)


def compose_book_club(img, draw, w, h, accent):
    sil = (155, 110, 48, 255)
    ground_y = int(h * 0.82)
    draw.rectangle([0, ground_y, w, h], fill=(12, 10, 4, 200))
    cx_table = w // 2
    cy_table = int(ground_y - 15)
    draw.ellipse([cx_table - 160, cy_table - 30, cx_table + 160, cy_table + 30],
                 fill=(90, 68, 35, 200))
    angles = [0, 52, 104, 156, 208, 260, 312]
    for angle in angles:
        rad = math.radians(angle)
        px = int(cx_table + 130 * math.sin(rad))
        py = int(ground_y - 16 * math.cos(rad))
        draw_person_reading(draw, px, py, 1.5, sil)
    draw_stars(draw, w, h, accent, 20)


def compose_teens_writing(img, draw, w, h, accent):
    sil = (145, 185, 130, 255)
    ground_y = int(h * 0.82)
    draw.rectangle([0, ground_y, w, h], fill=(8, 18, 8, 200))
    ar, ag, ab = int(accent[1:3], 16), int(accent[3:5], 16), int(accent[5:7], 16)
    for i in range(4):
        tx = int(w * (0.15 + i * 0.23))
        draw.rectangle([tx - 24, ground_y - 14, tx + 24, ground_y - 2],
                       fill=(ar, ag, ab, 50))
    positions = [(int(w * 0.15), ground_y, 1.5),
                 (int(w * 0.38), ground_y, 1.6),
                 (int(w * 0.61), ground_y, 1.5),
                 (int(w * 0.82), ground_y, 1.6)]
    for cx, by, sc in positions:
        draw_person_reading(draw, cx, by, sc, sil)


def compose_group_talk(img, draw, w, h, accent):
    sil = (165, 150, 60, 255)
    ground_y = int(h * 0.82)
    draw.rectangle([0, ground_y, w, h], fill=(14, 12, 4, 200))
    positions = [
        (int(w * 0.20), ground_y, 1.7, 'speaker'),
        (int(w * 0.40), ground_y, 1.8, 'listen'),
        (int(w * 0.57), ground_y, 1.7, 'listen'),
        (int(w * 0.74), ground_y, 1.6, 'listen'),
    ]
    for cx, by, sc, role in positions:
        if role == 'speaker':
            draw_speaker(draw, cx, by, sc * 0.8, sil)
        else:
            draw_person_reading(draw, cx, by, sc, sil)
    draw_stars(draw, w, h, accent, 15)


def compose_film(img, draw, w, h, accent):
    # audience is silhouetted dark against bright screen — intentionally dark
    sil = (35, 28, 22, 240)
    ground_y = int(h * 0.82)
    draw.rectangle([0, ground_y, w, h], fill=(5, 5, 5, 210))
    ar, ag, ab = int(accent[1:3], 16), int(accent[3:5], 16), int(accent[5:7], 16)
    # bright screen fill
    draw.rectangle([int(w * 0.08), int(h * 0.06), int(w * 0.92), int(h * 0.54)],
                   fill=(ar, ag, ab, 90))
    draw.rectangle([int(w * 0.08), int(h * 0.06), int(w * 0.92), int(h * 0.54)],
                   outline=(ar, ag, ab, 200), width=4)
    # film strip top
    for i in range(8):
        fx = int(w * 0.1) + i * int(w * 0.1)
        draw.rectangle([fx, 4, fx + int(w * 0.07), 18], fill=(ar, ag, ab, 60))
    # audience silhouettes
    for i in range(7):
        ax = int(w * (0.08 + i * 0.13))
        draw_person_reading(draw, ax, ground_y, 1.3, sil)


def compose_gala(img, draw, w, h, accent):
    sil = (180, 140, 55, 255)
    ground_y = int(h * 0.82)
    draw.rectangle([0, ground_y, w, h], fill=(20, 4, 4, 200))
    draw_lights(draw, w, h, accent)
    ar, ag, ab = int(accent[1:3], 16), int(accent[3:5], 16), int(accent[5:7], 16)
    draw.polygon([(w // 2, 0), (w // 2 - 130, ground_y), (w // 2 + 130, ground_y)],
                 fill=(ar, ag, ab, 25))
    draw_dancer(draw, int(w * 0.30), ground_y, 2.0, sil)
    draw_dancer(draw, int(w * 0.55), ground_y, 2.2, sil)
    draw_musician(draw, int(w * 0.78), ground_y, 1.8, sil, 'violin')
    draw_music_notes(draw, accent, [
        (int(w * 0.18), int(h * 0.3), 8),
        (int(w * 0.44), int(h * 0.25), 6),
        (int(w * 0.65), int(h * 0.35), 7),
        (int(w * 0.88), int(h * 0.28), 6),
    ])


SCENE_COMPOSERS = {
    'kids_reading':   compose_kids_reading,
    'adults_reading': compose_adults_reading,
    'adults_workshop': compose_adults_workshop,
    'speaker':        compose_speaker,
    'exhibit':        compose_exhibit,
    'book_club':      compose_book_club,
    'teens_writing':  compose_teens_writing,
    'group_talk':     compose_group_talk,
    'film':           compose_film,
    'gala':           compose_gala,
}


def wrap_text(text, font, max_width, draw):
    words = text.split()
    lines, current = [], ''
    for word in words:
        test = f'{current} {word}'.strip()
        if draw.textbbox((0, 0), test, font=font)[2] > max_width and current:
            lines.append(current)
            current = word
        else:
            current = test
    if current:
        lines.append(current)
    return lines


def make_event_image(title, scene_key, top_col, bot_col, accent, dest_path):
    img = Image.new('RGBA', (IMG_W, IMG_H), (0, 0, 0, 255))
    draw = ImageDraw.Draw(img, 'RGBA')

    gradient(draw, IMG_W, IMG_H, top_col, bot_col)

    composer = SCENE_COMPOSERS.get(scene_key)
    if composer:
        composer(img, draw, IMG_W, IMG_H, accent)

    # Build bottom-darkening overlay as a separate RGBA image so alpha_composite
    # is used rather than direct pixel replacement (Pillow's ImageDraw replaces
    # alpha in place, which would make semi-transparent blacks opaque-black).
    overlay = Image.new('RGBA', (IMG_W, IMG_H), (0, 0, 0, 0))
    ov_draw = ImageDraw.Draw(overlay)
    for y in range(IMG_H // 2, IMG_H):
        alpha = int(180 * (y - IMG_H // 2) / (IMG_H // 2))
        ov_draw.line([(0, y), (IMG_W, y)], fill=(0, 0, 0, alpha))
    img = Image.alpha_composite(img, overlay)
    draw = ImageDraw.Draw(img, 'RGBA')

    # Accent bottom bar
    ar, ag, ab = int(accent[1:3], 16), int(accent[3:5], 16), int(accent[5:7], 16)
    draw.rectangle([0, IMG_H - 6, IMG_W, IMG_H], fill=(ar, ag, ab, 255))

    # Title text
    try:
        font_lg = ImageFont.truetype(FONT_BOLD, 30)
        font_md = ImageFont.truetype(FONT_BOLD, 24)
    except Exception:
        font_lg = font_md = ImageFont.load_default()

    padding = 32
    max_w = IMG_W - padding * 2
    for font in [font_lg, font_md]:
        lines = wrap_text(title, font, max_w, draw)
        total_h = sum(draw.textbbox((0, 0), l, font=font)[3] + 4 for l in lines)
        if total_h < 100:
            break

    ty = IMG_H - 20 - sum(draw.textbbox((0, 0), l, font=font)[3] + 4 for l in lines) - 14
    for line in lines:
        lb = draw.textbbox((0, 0), line, font=font)
        draw.text((padding + 2, ty + 2), line, font=font, fill=(0, 0, 0, 180))
        draw.text((padding, ty), line, font=font, fill=(255, 255, 255, 255))
        ty += lb[3] - lb[1] + 4

    # Accent rule above title
    rule_y = IMG_H - 20 - sum(draw.textbbox((0, 0), l, font=font)[3] + 4 for l in lines) - 20
    draw.line([(padding, rule_y), (padding + 60, rule_y)], fill=(ar, ag, ab, 255), width=2)

    img.convert('RGB').save(dest_path, 'JPEG', quality=92)


class Command(BaseCommand):
    help = 'Generate cover images for all events'

    def add_arguments(self, parser):
        parser.add_argument('--all', action='store_true', help='Regenerate even if image exists')

    def handle(self, *args, **options):
        img_dir = Path(settings.MEDIA_ROOT) / 'event_images'
        img_dir.mkdir(parents=True, exist_ok=True)

        events = Event.objects.all()
        if not options['all']:
            events = events.filter(image='')

        total = events.count()
        self.stdout.write(f'Generating images for {total} events...')

        for event in events:
            cfg = EVENT_SCENES.get(event.title, DEFAULT_SCENE)
            top_col, bot_col, accent, scene_key = cfg

            filename = f'event_{event.id}.jpg'
            dest = img_dir / filename
            make_event_image(event.title, scene_key, top_col, bot_col, accent, str(dest))

            event.image = f'event_images/{filename}'
            event.save(update_fields=['image'])
            self.stdout.write(f'  {event.title}')

        self.stdout.write(self.style.SUCCESS(f'Done! Generated {total} event images.'))
