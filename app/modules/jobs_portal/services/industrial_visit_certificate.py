from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import Optional

from PIL import Image, ImageDraw, ImageFont
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas


ASSETS = Path(__file__).resolve().parent.parent / "assets" / "certificates"

TEMPLATE_PATH = ASSETS / "industrial_visit_template.png"

NAVY = (5, 30, 94)

FONT_PATHS = [
    Path("/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf"),
    Path("/usr/share/fonts/truetype/liberation/LiberationSerif-Regular.ttf"),
    Path(r"C:\Windows\Fonts\times.ttf"),
    Path("/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf"),
    Path(r"C:\Windows\Fonts\timesbd.ttf"),
]


def _ordinal_day(day: int) -> str:
    if 10 <= day % 100 <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(day % 10, "th")

    return f"{day}{suffix}"


def format_visit_date(visit_date: datetime) -> str:
    return (
        f"{visit_date.strftime('%A')}, {_ordinal_day(visit_date.day)} "
        f"{visit_date.strftime('%B')} {visit_date.year}"
    )


def _font(size: int):
    for path in FONT_PATHS:
        if path.exists():
            return ImageFont.truetype(str(path), size)

    return ImageFont.load_default()


def _fit_name_font(text: str, max_width: int):
    size = 48

    while size > 20:
        font = _font(size)

        if font.getlength(text) <= max_width:
            return font

        size -= 2

    return _font(size)


def generate_participation_certificate_pdf(
    *,
    full_name: str,
    college_name: str,
    department: str,
    visit_title: str,
    visit_date: datetime,
    venue: Optional[str],
    certificate_id: str,
    verify_url: str,
    issue_date: Optional[datetime] = None,
) -> bytes:
    """
    Generate industrial visit participation certificate.

    The original certificate template is kept unchanged.
    Only the participant name is dynamically added.
    """

    # These values are currently not rendered dynamically.
    _ = (
        college_name,
        department,
        visit_title,
        visit_date,
        venue,
        certificate_id,
        verify_url,
        issue_date,
    )

    if not TEMPLATE_PATH.exists():
        raise FileNotFoundError(
            f"Certificate template missing: {TEMPLATE_PATH}"
        )

    # Load original certificate template.
    img = Image.open(TEMPLATE_PATH).convert("RGBA")

    draw = ImageDraw.Draw(img)

    w, h = img.size

    # ---------------------------------------------------------
    # Dynamic Participant Name
    # ---------------------------------------------------------

    name = (full_name or "").strip().upper()

    font = _fit_name_font(
        name,
        int(w * 0.58),
    )

    # Vertical position of the participant name.
    name_y = int(h * 0.530)

    # Calculate text width for horizontal centering.
    text_w = font.getlength(name)

    name_x = int((w - text_w) / 2)

    # Draw participant name.
    draw.text(
        (name_x, name_y),
        name,
        font=font,
        fill=NAVY,
    )

    # ---------------------------------------------------------
    # Convert image to RGB for PDF
    # ---------------------------------------------------------

    rgb = img.convert("RGB")

    buf = BytesIO()

    # Landscape A4 PDF.
    page_w, page_h = landscape(A4)

    c = canvas.Canvas(
        buf,
        pagesize=landscape(A4),
    )

    # Place certificate template on the entire A4 page.
    c.drawImage(
        ImageReader(rgb),
        0,
        0,
        width=page_w,
        height=page_h,
        preserveAspectRatio=True,
        anchor="c",
    )

    c.showPage()
    c.save()

    return buf.getvalue()