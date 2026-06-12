from __future__ import annotations

from io import BytesIO
from typing import Optional

import qrcode
from PIL import Image, ImageDraw, ImageFont


def _load_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "C:/Windows/Fonts/segoeuib.ttf" if bold else "C:/Windows/Fonts/segoeui.ttf",
        "C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf",
    ]
    for path in candidates:
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    return ImageFont.load_default()


def _wrap_text(text: str, max_width: int, font: ImageFont.ImageFont, draw: ImageDraw.ImageDraw) -> list[str]:
    words = text.split(" ")
    lines: list[str] = []
    current = ""

    for word in words:
        candidate = f"{current} {word}".strip()
        bbox = draw.textbbox((0, 0), candidate, font=font)
        if bbox[2] - bbox[0] <= max_width:
            current = candidate
            continue
        if current:
            lines.append(current)
        current = word

    if current:
        lines.append(current)

    if not lines:
        lines = [text]
    return lines


def _wrap_url(url: str, max_width: int, font: ImageFont.ImageFont, draw: ImageDraw.ImageDraw) -> list[str]:
    lines: list[str] = []
    current = ""

    for char in url:
        candidate = current + char
        bbox = draw.textbbox((0, 0), candidate, font=font)
        if bbox[2] - bbox[0] <= max_width:
            current = candidate
            continue
        if current:
            lines.append(current)
        current = char

    if current:
        lines.append(current)

    return lines or [url]


def generate_job_fair_qr_poster(url: str, headline: Optional[str] = None) -> bytes:
    """QR poster with visible URL text for sharing (e.g. WhatsApp screenshots)."""
    qr = qrcode.QRCode(version=None, box_size=8, border=3)
    qr.add_data(url)
    qr.make(fit=True)
    qr_img = qr.make_image(fill_color="black", back_color="white").convert("RGB")
    qr_w, qr_h = qr_img.size

    padding = 24
    canvas_w = max(qr_w + padding * 2, 380)
    text_max_w = canvas_w - padding * 2

    headline_font = _load_font(16, bold=True)
    label_font = _load_font(12)
    url_font = _load_font(13)

    measure = ImageDraw.Draw(Image.new("RGB", (canvas_w, 1)))
    headline_lines = _wrap_text(headline, text_max_w, headline_font, measure) if headline else []
    url_lines = _wrap_url(url, text_max_w, url_font, measure)

    line_h = 18
    label = "Scan QR or visit:"
    text_block_h = 22 + len(url_lines) * line_h
    headline_h = len(headline_lines) * 22 + (8 if headline_lines else 0)
    canvas_h = padding + qr_h + padding + headline_h + text_block_h + padding

    canvas = Image.new("RGB", (canvas_w, canvas_h), "white")
    canvas.paste(qr_img, ((canvas_w - qr_w) // 2, padding))

    draw = ImageDraw.Draw(canvas)
    y = padding + qr_h + padding

    for line in headline_lines:
        bbox = draw.textbbox((0, 0), line, font=headline_font)
        tw = bbox[2] - bbox[0]
        draw.text(((canvas_w - tw) // 2, y), line, fill="#1e293b", font=headline_font)
        y += 22

    if headline_lines:
        y += 8

    bbox = draw.textbbox((0, 0), label, font=label_font)
    tw = bbox[2] - bbox[0]
    draw.text(((canvas_w - tw) // 2, y), label, fill="#64748b", font=label_font)
    y += 22

    for line in url_lines:
        bbox = draw.textbbox((0, 0), line, font=url_font)
        tw = bbox[2] - bbox[0]
        draw.text(((canvas_w - tw) // 2, y), line, fill="#2563eb", font=url_font)
        y += line_h

    buf = BytesIO()
    canvas.save(buf, format="PNG")
    return buf.getvalue()
