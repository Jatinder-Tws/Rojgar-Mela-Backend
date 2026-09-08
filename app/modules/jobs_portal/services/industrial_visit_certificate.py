from datetime import datetime
from io import BytesIO
from typing import Optional

from reportlab.lib.colors import HexColor, white
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas


NAVY = HexColor("#0f2d52")
GOLD = HexColor("#c9a227")
SLATE = HexColor("#334155")
MUTED = HexColor("#64748b")
LIGHT = HexColor("#eef4f9")


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
) -> bytes:
    """Generate a landscape A4 participation certificate PDF."""
    buffer = BytesIO()
    width, height = landscape(A4)
    c = canvas.Canvas(buffer, pagesize=landscape(A4))

    c.setFillColor(LIGHT)
    c.rect(0, 0, width, height, fill=1, stroke=0)

    c.setStrokeColor(NAVY)
    c.setLineWidth(3.2)
    c.rect(12 * mm, 12 * mm, width - 24 * mm, height - 24 * mm, fill=0, stroke=1)
    c.setStrokeColor(GOLD)
    c.setLineWidth(1.2)
    c.rect(14.5 * mm, 14.5 * mm, width - 29 * mm, height - 29 * mm, fill=0, stroke=1)

    c.setFillColor(NAVY)
    c.rect(12 * mm, height - 38 * mm, width - 24 * mm, 26 * mm, fill=1, stroke=0)
    c.setFillColor(GOLD)
    c.rect(12 * mm, height - 40 * mm, width - 24 * mm, 2.2 * mm, fill=1, stroke=0)

    c.setFillColor(white)
    c.setFont("Times-Bold", 14)
    c.drawCentredString(width / 2, height - 24 * mm, "ROJGARMELA.AI")
    c.setFont("Times-Bold", 22)
    c.drawCentredString(width / 2, height - 34 * mm, "Certificate of Participation")

    c.setFillColor(MUTED)
    c.setFont("Times-Italic", 13)
    c.drawCentredString(width / 2, height - 54 * mm, "This is to certify that")

    c.setFillColor(NAVY)
    c.setFont("Times-Bold", 26)
    c.drawCentredString(width / 2, height - 68 * mm, full_name.strip())

    c.setStrokeColor(GOLD)
    c.setLineWidth(0.8)
    name_width = min(c.stringWidth(full_name.strip(), "Times-Bold", 26) + 24, width - 80 * mm)
    c.line((width - name_width) / 2, height - 71 * mm, (width + name_width) / 2, height - 71 * mm)

    c.setFillColor(SLATE)
    c.setFont("Times-Roman", 13)
    date_display = format_visit_date(visit_date)
    venue_text = (venue or "").strip()
    body_lines = [
        f"a student of {college_name.strip()} ({department.strip()})",
        f"has successfully participated in {visit_title.strip()}",
        f"held on {date_display}" + (f" at {venue_text}." if venue_text else "."),
    ]
    y = height - 86 * mm
    for line in body_lines:
        c.drawCentredString(width / 2, y, line)
        y -= 7.5 * mm

    c.setFillColor(MUTED)
    c.setFont("Times-Italic", 11)
    c.drawCentredString(
        width / 2,
        38 * mm,
        "Issued in recognition of attendance and active participation during the industrial visit.",
    )

    c.setFillColor(NAVY)
    c.setFont("Times-Bold", 10)
    c.drawString(28 * mm, 26 * mm, f"Certificate ID: {certificate_id}")
    c.setFont("Times-Roman", 8)
    c.setFillColor(MUTED)
    c.drawString(28 * mm, 21 * mm, f"Verify at: {verify_url}")

    c.setFillColor(NAVY)
    c.setFont("Times-Bold", 11)
    c.drawRightString(width - 28 * mm, 26 * mm, "Rojgar Mela")
    c.setFont("Times-Italic", 9)
    c.setFillColor(MUTED)
    c.drawRightString(width - 28 * mm, 21 * mm, "Authorised Signature")

    c.showPage()
    c.save()
    return buffer.getvalue()
