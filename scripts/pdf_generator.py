"""
pdf_generator.py — ReportLab PDF statement builder for HRH.
"""

import os
from datetime import date
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph,
    Spacer, HRFlowable
)
from reportlab.lib.enums import TA_LEFT, TA_RIGHT, TA_CENTER

# ── HRH Constants ──────────────────────────────────────────────────────────
HRH_NAME  = "High Ridge Hydroponics LLC"
HRH_ADDR1 = "1 1/2 Island Brook Avenue, Building B"
HRH_CITY  = "Bridgeport, CT 06606"
HRH_PHONE = "203-788-5180"
HRH_EMAIL = "highridgehydroponics@gmail.com"

# Brand colors — blue theme
HRH_BLUE    = colors.HexColor("#1e40af")   # deep blue (header/accents)
LIGHT_BLUE  = colors.HexColor("#eff6ff")   # very light blue (row backgrounds)
MED_BLUE    = colors.HexColor("#bfdbfe")   # medium blue (borders)
LIGHT_GRAY  = colors.HexColor("#f5f5f5")   # fallback row bg
MED_GRAY    = colors.HexColor("#cccccc")   # neutral borders
DARK_GRAY   = colors.HexColor("#444444")


def _fmt_money(val):
    try:
        return "$" + "{:,.2f}".format(float(val))
    except Exception:
        return "$0.00"


def _fmt_date(date_str):
    """Convert YYYY-MM-DD to MM/DD/YYYY."""
    try:
        d = date.fromisoformat(date_str)
        return d.strftime("%m/%d/%Y")
    except Exception:
        return date_str or "—"


def generate_pdf(customer_data, output_path):
    """
    Generate a single account statement PDF for one customer.

    customer_data keys:
      statement_id, customer_name, customer_email, customer_phone,
      customer_address, total, buckets, invoices, pdf_filename
    """
    doc = SimpleDocTemplate(
        output_path,
        pagesize=letter,
        leftMargin=0.6 * inch,
        rightMargin=0.6 * inch,
        topMargin=0.6 * inch,
        bottomMargin=0.7 * inch,
    )

    styles = getSampleStyleSheet()
    normal   = styles["Normal"]
    h1_style = ParagraphStyle("h1", fontSize=16, textColor=HRH_BLUE,
                               spaceAfter=2, fontName="Helvetica-Bold")
    h2_style = ParagraphStyle("h2", fontSize=10, textColor=HRH_BLUE,
                               spaceAfter=2, fontName="Helvetica-Bold",
                               spaceBefore=8)
    small    = ParagraphStyle("small", fontSize=8, textColor=DARK_GRAY,
                               spaceAfter=1)
    right_sm = ParagraphStyle("rsm", fontSize=8, alignment=TA_RIGHT,
                               textColor=DARK_GRAY)
    bold_sm  = ParagraphStyle("bsm", fontSize=8, fontName="Helvetica-Bold")
    center_sm= ParagraphStyle("csm", fontSize=8, alignment=TA_CENTER,
                               textColor=DARK_GRAY)

    story = []

    # ── Header ──────────────────────────────────────────────────────────────
    header_data = [[
        Paragraph(HRH_NAME, h1_style),
        Paragraph(
            "<b>ACCOUNT STATEMENT</b><br/>"
            "Statement #: " + customer_data["statement_id"] + "<br/>"
            "Date: " + date.today().strftime("%B %d, %Y"),
            right_sm
        ),
    ]]
    header_tbl = Table(header_data, colWidths=["60%", "40%"])
    header_tbl.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ALIGN",  (1, 0), (1, 0),  "RIGHT"),
    ]))
    story.append(header_tbl)

    contact_data = [[
        Paragraph(
            HRH_ADDR1 + "<br/>" + HRH_CITY + "<br/>"
            "Phone: " + HRH_PHONE + "<br/>Email: " + HRH_EMAIL,
            small
        ),
        Paragraph("", small),
    ]]
    contact_tbl = Table(contact_data, colWidths=["60%", "40%"])
    contact_tbl.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")]))
    story.append(contact_tbl)

    story.append(HRFlowable(width="100%", thickness=1, color=HRH_BLUE,
                             spaceAfter=8, spaceBefore=6))

    # ── Bill To ─────────────────────────────────────────────────────────────
    story.append(Paragraph("BILL TO", h2_style))
    bill_lines = [customer_data["customer_name"]]
    if customer_data.get("customer_address"):
        bill_lines.append(customer_data["customer_address"])
    if customer_data.get("customer_email"):
        bill_lines.append(customer_data["customer_email"])
    if customer_data.get("customer_phone"):
        bill_lines.append(customer_data["customer_phone"])
    story.append(Paragraph("<br/>".join(bill_lines), small))
    story.append(Spacer(1, 10))

    # ── Aging Summary ────────────────────────────────────────────────────────
    story.append(Paragraph("ACCOUNT SUMMARY", h2_style))
    b = customer_data["buckets"]
    aging_data = [
        ["Total Balance", "0-30 Days", "31-60 Days", "61-90 Days", "Over 90 Days"],
        [
            _fmt_money(customer_data["total"]),
            _fmt_money(b.get("0_30", 0)),
            _fmt_money(b.get("31_60", 0)),
            _fmt_money(b.get("61_90", 0)),
            _fmt_money(b.get("over_90", 0)),
        ],
    ]
    aging_tbl = Table(aging_data, colWidths=["20%", "20%", "20%", "20%", "20%"])
    aging_tbl.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, 0),  HRH_BLUE),
        ("TEXTCOLOR",     (0, 0), (-1, 0),  colors.white),
        ("FONTNAME",      (0, 0), (-1, 0),  "Helvetica-Bold"),
        ("FONTSIZE",      (0, 0), (-1, -1), 8),
        ("ALIGN",         (0, 0), (-1, -1), "CENTER"),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        ("ROWBACKGROUNDS",(0, 1), (-1, -1), [LIGHT_BLUE, colors.white]),
        ("GRID",          (0, 0), (-1, -1), 0.5, MED_BLUE),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING",    (0, 0), (-1, -1), 5),
    ]))
    story.append(aging_tbl)
    story.append(Spacer(1, 12))

    # ── Invoice Detail ───────────────────────────────────────────────────────
    story.append(Paragraph("INVOICE DETAIL", h2_style))

    # Columns: Invoice Date | Invoice # | Bill Due | Amount Due | Pay Here
    inv_header = ["Invoice Date", "Invoice #", "Bill Due", "Amount Due", "Pay Here"]
    inv_rows = [inv_header]

    for inv in customer_data["invoices"]:
        raw_num = inv["id"]
        display_num = raw_num.lstrip("0") or raw_num

        date_display = _fmt_date(inv.get("date", ""))
        due_display  = _fmt_date(inv.get("due_date", ""))

        pay_url = inv.get("url", "")
        if pay_url:
            pay_cell = Paragraph(
                '<link href="' + pay_url + '"><u>Pay Here</u></link>',
                ParagraphStyle("link", fontSize=7, textColor=HRH_BLUE)
            )
        else:
            pay_cell = Paragraph("—", center_sm)

        inv_rows.append([
            date_display,
            display_num,
            due_display,
            _fmt_money(inv["amount"]),
            pay_cell,
        ])

    # Column widths: Date | Inv# | Due | Amount | Pay
    col_w = [
        1.1 * inch,   # Invoice Date
        1.0 * inch,   # Invoice #
        1.1 * inch,   # Bill Due
        1.1 * inch,   # Amount Due
        1.0 * inch,   # Pay Here
    ]

    inv_tbl = Table(inv_rows, colWidths=col_w, repeatRows=1)
    inv_style = [
        # Header row
        ("BACKGROUND",    (0, 0), (-1, 0),  HRH_BLUE),
        ("TEXTCOLOR",     (0, 0), (-1, 0),  colors.white),
        ("FONTNAME",      (0, 0), (-1, 0),  "Helvetica-Bold"),
        ("FONTSIZE",      (0, 0), (-1, -1), 8),
        ("ALIGN",         (0, 0), (-1, -1), "LEFT"),
        ("ALIGN",         (3, 0), (3, -1),  "RIGHT"),   # Amount Due right-aligned
        ("ALIGN",         (4, 0), (4, -1),  "CENTER"),  # Pay Here centered
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        ("ROWBACKGROUNDS",(0, 1), (-1, -1), [LIGHT_BLUE, colors.white]),
        ("GRID",          (0, 0), (-1, -1), 0.25, MED_BLUE),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING",    (0, 0), (-1, -1), 4),
    ]

    inv_tbl.setStyle(TableStyle(inv_style))
    story.append(inv_tbl)
    story.append(Spacer(1, 14))

    # ── Remittance Footer ────────────────────────────────────────────────────
    story.append(HRFlowable(width="100%", thickness=0.5, color=MED_BLUE,
                             spaceAfter=6, spaceBefore=4))
    story.append(Paragraph(
        "<b>Please remit payment to:</b> " + HRH_NAME + " | " + HRH_EMAIL + " | " + HRH_PHONE + "<br/>"
        "Thank you for your business!",
        center_sm
    ))

    doc.build(story)
