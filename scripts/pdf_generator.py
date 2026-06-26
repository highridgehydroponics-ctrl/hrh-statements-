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

# Brand color
HRH_GREEN  = colors.HexColor("#2d6a4f")
LIGHT_GRAY = colors.HexColor("#f5f5f5")
MED_GRAY   = colors.HexColor("#cccccc")
DARK_GRAY  = colors.HexColor("#444444")


def _fmt_money(val):
    try:
        return f"${float(val):,.2f}"
    except Exception:
        return "$0.00"


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
    h1_style = ParagraphStyle("h1", fontSize=16, textColor=HRH_GREEN,
                               spaceAfter=2, fontName="Helvetica-Bold")
    h2_style = ParagraphStyle("h2", fontSize=10, textColor=HRH_GREEN,
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
            f"<b>ACCOUNT STATEMENT</b><br/>"
            f"Statement #: {customer_data['statement_id']}<br/>"
            f"Date: {date.today().strftime('%B %d, %Y')}",
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
            f"{HRH_ADDR1}<br/>{HRH_CITY}<br/>"
            f"Phone: {HRH_PHONE}<br/>Email: {HRH_EMAIL}",
            small
        ),
        Paragraph("", small),
    ]]
    contact_tbl = Table(contact_data, colWidths=["60%", "40%"])
    contact_tbl.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")]))
    story.append(contact_tbl)

    story.append(HRFlowable(width="100%", thickness=1, color=HRH_GREEN,
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
        ("BACKGROUND",   (0, 0), (-1, 0),  HRH_GREEN),
        ("TEXTCOLOR",    (0, 0), (-1, 0),  colors.white),
        ("FONTNAME",     (0, 0), (-1, 0),  "Helvetica-Bold"),
        ("FONTSIZE",     (0, 0), (-1, -1), 8),
        ("ALIGN",        (0, 0), (-1, -1), "CENTER"),
        ("VALIGN",       (0, 0), (-1, -1), "MIDDLE"),
        ("ROWBACKGROUNDS",(0, 1), (-1, -1), [LIGHT_GRAY, colors.white]),
        ("GRID",         (0, 0), (-1, -1), 0.5, MED_GRAY),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 5),
        ("TOPPADDING",   (0, 0), (-1, -1), 5),
    ]))
    story.append(aging_tbl)
    story.append(Spacer(1, 12))

    # ── Invoice Detail ───────────────────────────────────────────────────────
    story.append(Paragraph("INVOICE DETAIL", h2_style))

    inv_header = ["Invoice Date", "Invoice #", "Billed To", "Amount Due", "Age", "Pay Here"]
    inv_rows = [inv_header]

    for inv in customer_data["invoices"]:
        raw_num = inv["id"]
        display_num = raw_num.lstrip("0") or raw_num

        try:
            d = date.fromisoformat(inv["date"])
            date_display = d.strftime("%m/%d/%Y")
        except Exception:
            date_display = inv["date"]

        days = inv.get("age_days", 0)
        age_label = f"{days}d"

        pay_url = inv.get("url", "")
        if pay_url:
            pay_cell = Paragraph(
                f'<link href="{pay_url}"><u>Pay Here</u></link>',
                ParagraphStyle("link", fontSize=7, textColor=colors.blue)
            )
        else:
            pay_cell = Paragraph("—", center_sm)

        inv_rows.append([
            date_display,
            display_num,
            inv.get("email", ""),
            _fmt_money(inv["amount"]),
            age_label,
            pay_cell,
        ])

        # Line items sub-rows (indented)
        line_items = inv.get("line_items", [])
        if line_items:
            for li in line_items:
                inv_rows.append([
                    "",
                    Paragraph(f'&nbsp;&nbsp;&nbsp;↳ {li["name"]}', small),
                    f'Qty: {li["quantity"]}',
                    _fmt_money(li["unit_price"]),
                    _fmt_money(li["total"]),
                    "",
                ])
        else:
            inv_rows.append([
                "",
                Paragraph("&nbsp;&nbsp;&nbsp;<i>No line item detail available</i>",
                           ParagraphStyle("gray", fontSize=7, textColor=colors.gray)),
                "", "", "", "",
            ])

    # Column widths: Date | Inv# | Email | Amount | Age | Pay
    col_w = [
        0.9 * inch,
        0.9 * inch,
        2.2 * inch,
        0.9 * inch,
        0.45 * inch,
        0.75 * inch,
    ]

    inv_tbl = Table(inv_rows, colWidths=col_w, repeatRows=1)
    inv_style = [
        # Header row
        ("BACKGROUND",  (0, 0), (-1, 0),  HRH_GREEN),
        ("TEXTCOLOR",   (0, 0), (-1, 0),  colors.white),
        ("FONTNAME",    (0, 0), (-1, 0),  "Helvetica-Bold"),
        ("FONTSIZE",    (0, 0), (-1, -1), 7),
        ("ALIGN",       (0, 0), (-1, -1), "LEFT"),
        ("ALIGN",       (3, 0), (3, -1),  "RIGHT"),
        ("ALIGN",       (4, 0), (4, -1),  "CENTER"),
        ("ALIGN",       (5, 0), (5, -1),  "CENTER"),
        ("VALIGN",      (0, 0), (-1, -1), "MIDDLE"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [LIGHT_GRAY, colors.white]),
        ("GRID",        (0, 0), (-1, -1), 0.25, MED_GRAY),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("TOPPADDING",  (0, 0), (-1, -1), 3),
    ]

    # Zebra-stripe but keep line-item rows slightly different
    inv_tbl.setStyle(TableStyle(inv_style))
    story.append(inv_tbl)
    story.append(Spacer(1, 14))

    # ── Remittance Footer ────────────────────────────────────────────────────
    story.append(HRFlowable(width="100%", thickness=0.5, color=MED_GRAY,
                             spaceAfter=6, spaceBefore=4))
    story.append(Paragraph(
        f"<b>Please remit payment to:</b> {HRH_NAME} | {HRH_EMAIL} | {HRH_PHONE}<br/>"
        f"Thank you for your business!",
        center_sm
    ))

    doc.build(story)
