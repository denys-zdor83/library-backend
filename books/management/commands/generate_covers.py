import os
import textwrap
from pathlib import Path
from django.core.management.base import BaseCommand
from django.conf import settings
from PIL import Image, ImageDraw, ImageFont
from books.models import Book

FONT_BOLD = '/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf'
FONT_REG  = '/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf'
FONT_SANS = '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'

# Two-color gradient pairs per genre
GENRE_PALETTES = {
    'Fiction':           ('#1a1a2e', '#16213e', '#e0c97f'),
    'Science Fiction':   ('#0d0d2b', '#1a1a4e', '#7ec8e3'),
    'Fantasy':           ('#1b0033', '#3d0066', '#d4af37'),
    'Mystery & Thriller':('#0a0a0a', '#1c1c1c', '#c0392b'),
    'Biography':         ('#1a2a1a', '#2d4a2d', '#f5f0e8'),
    'History':           ('#2c1a0e', '#4a2f1a', '#d4af37'),
    'Science':           ('#002b36', '#004d5c', '#2ecc71'),
    'Technology':        ('#0a0f1e', '#0d1b35', '#00d4ff'),
    'Romance':           ('#2d0025', '#5a0050', '#ff85b3'),
    'Self-Help':         ('#1a2744', '#2e4070', '#f4c542'),
}
DEFAULT_PALETTE = ('#1a1a2e', '#2d2d4e', '#ffffff')

COVER_W, COVER_H = 400, 600


def draw_gradient(draw, width, height, top_color, bottom_color):
    tr, tg, tb = int(top_color[1:3], 16), int(top_color[3:5], 16), int(top_color[5:7], 16)
    br, bg, bb = int(bottom_color[1:3], 16), int(bottom_color[3:5], 16), int(bottom_color[5:7], 16)
    for y in range(height):
        ratio = y / height
        r = int(tr + (br - tr) * ratio)
        g = int(tg + (bg - tg) * ratio)
        b = int(tb + (bb - tb) * ratio)
        draw.line([(0, y), (width, y)], fill=(r, g, b))


def draw_decorative_lines(draw, width, height, accent_hex):
    r, g, b = int(accent_hex[1:3], 16), int(accent_hex[3:5], 16), int(accent_hex[5:7], 16)
    accent = (r, g, b, 60)
    # Top and bottom border lines
    for offset in [0, 3, 6]:
        draw.line([(20 + offset, 30 + offset), (width - 20 - offset, 30 + offset)], fill=accent, width=1)
        draw.line([(20 + offset, height - 30 - offset), (width - 20 - offset, height - 30 - offset)], fill=accent, width=1)
    # Corner ornaments
    size = 18
    for cx, cy in [(25, 35), (width - 25, 35), (25, height - 35), (width - 25, height - 35)]:
        draw.rectangle([cx - size // 2, cy - size // 2, cx + size // 2, cy + size // 2],
                       outline=(r, g, b, 80), width=1)


def wrap_text(text, font, max_width, draw):
    """Wrap text to fit within max_width pixels."""
    words = text.split()
    lines = []
    current = ''
    for word in words:
        test = f'{current} {word}'.strip()
        bbox = draw.textbbox((0, 0), test, font=font)
        if bbox[2] > max_width and current:
            lines.append(current)
            current = word
        else:
            current = test
    if current:
        lines.append(current)
    return lines


def make_cover(title, author, genre_name, dest_path):
    palette = GENRE_PALETTES.get(genre_name, DEFAULT_PALETTE)
    top_col, bot_col, accent_hex = palette

    img = Image.new('RGB', (COVER_W, COVER_H))
    draw = ImageDraw.Draw(img, 'RGBA')

    draw_gradient(draw, COVER_W, COVER_H, top_col, bot_col)
    draw_decorative_lines(draw, COVER_W, COVER_H, accent_hex)

    # Parse accent color
    ar, ag, ab = int(accent_hex[1:3], 16), int(accent_hex[3:5], 16), int(accent_hex[5:7], 16)
    accent_solid = (ar, ag, ab)
    accent_dim   = (ar, ag, ab, 180)
    white        = (255, 255, 255)
    white_dim    = (220, 220, 220)

    padding = 30
    max_text_w = COVER_W - padding * 2

    # Genre label at top
    try:
        font_genre = ImageFont.truetype(FONT_SANS, 13)
    except Exception:
        font_genre = ImageFont.load_default()
    genre_text = genre_name.upper()
    gb = draw.textbbox((0, 0), genre_text, font=font_genre)
    gw = gb[2] - gb[0]
    draw.text(((COVER_W - gw) // 2, 55), genre_text, font=font_genre, fill=accent_dim)

    # Accent divider under genre
    draw.line([(COVER_W // 2 - 30, 75), (COVER_W // 2 + 30, 75)], fill=accent_solid, width=2)

    # Title — large, centered, wrapped
    title_y = 110
    try:
        font_title_lg = ImageFont.truetype(FONT_BOLD, 32)
        font_title_md = ImageFont.truetype(FONT_BOLD, 26)
        font_title_sm = ImageFont.truetype(FONT_BOLD, 21)
    except Exception:
        font_title_lg = font_title_md = font_title_sm = ImageFont.load_default()

    for font_title in [font_title_lg, font_title_md, font_title_sm]:
        lines = wrap_text(title, font_title, max_text_w, draw)
        total_h = sum(draw.textbbox((0, 0), l, font=font_title)[3] + 6 for l in lines)
        if total_h < 280:
            break

    for line in lines:
        lb = draw.textbbox((0, 0), line, font=font_title)
        lw = lb[2] - lb[0]
        draw.text(((COVER_W - lw) // 2, title_y), line, font=font_title, fill=white)
        title_y += lb[3] - lb[1] + 8

    # Accent rule between title and author
    rule_y = title_y + 20
    draw.line([(padding, rule_y), (COVER_W - padding, rule_y)], fill=accent_solid, width=1)

    # Author name
    try:
        font_author = ImageFont.truetype(FONT_REG, 18)
    except Exception:
        font_author = ImageFont.load_default()

    author_lines = wrap_text(author, font_author, max_text_w, draw)
    author_y = rule_y + 16
    for line in author_lines:
        ab2 = draw.textbbox((0, 0), line, font=font_author)
        aw = ab2[2] - ab2[0]
        draw.text(((COVER_W - aw) // 2, author_y), line, font=font_author, fill=accent_dim)
        author_y += ab2[3] - ab2[1] + 5

    # Bottom: "City Library" watermark
    try:
        font_wm = ImageFont.truetype(FONT_SANS, 11)
    except Exception:
        font_wm = ImageFont.load_default()
    wm = 'CITY LIBRARY'
    wmb = draw.textbbox((0, 0), wm, font=font_wm)
    draw.text(((COVER_W - (wmb[2] - wmb[0])) // 2, COVER_H - 50),
              wm, font=font_wm, fill=(ar, ag, ab, 100))

    img.save(dest_path, 'JPEG', quality=90)


class Command(BaseCommand):
    help = 'Generate book cover images for all books that have no cover'

    def add_arguments(self, parser):
        parser.add_argument('--all', action='store_true', help='Regenerate covers even if they already exist')

    def handle(self, *args, **options):
        covers_dir = Path(settings.MEDIA_ROOT) / 'covers'
        covers_dir.mkdir(parents=True, exist_ok=True)

        books = Book.objects.select_related('genre').all()
        if not options['all']:
            books = books.filter(cover='')

        total = books.count()
        self.stdout.write(f'Generating covers for {total} books...')

        for i, book in enumerate(books, 1):
            filename = f'cover_{book.id}.jpg'
            dest = covers_dir / filename
            genre_name = book.genre.name if book.genre else 'Fiction'

            make_cover(book.title, book.author, genre_name, str(dest))

            book.cover = f'covers/{filename}'
            book.save(update_fields=['cover'])

            if i % 50 == 0 or i == total:
                self.stdout.write(f'  {i}/{total}')

        self.stdout.write(self.style.SUCCESS(f'Done! Generated {total} covers.'))
