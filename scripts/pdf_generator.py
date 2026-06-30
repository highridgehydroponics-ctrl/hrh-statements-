"""
pdf_generator.py — ReportLab PDF statement builder for HRH.
Format matches the HRH HTML statement template (blue theme).
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

# ── Color palette — Material Blue (matches HTML template) ──────────────────
PRIMARY_BLUE   = colors.HexColor("#1565C0")   # header, title, amounts
LIGHT_BLUE_BG  = colors.HexColor("#E3F2FD")   # tfoot row, card backgrounds
MED_BLUE_BDR   = colors.HexColor("#BBDEFB")   # borders / separators
DARK_TEXT      = colors.HexColor("#1a1a1a")
MED_GRAY       = colors.HexColor("#666666")
ROW_BORDER     = colors.HexColor("#e8eef4")

# Aging bucket colors (hex strings for Paragraph markup)
_C_0_30   = "#2e7d32"   # green
_C_31_60  = "#f57f17"   # amber
_C_61_90  = "#e65100"   # dark orange
_C_OVER90 = "#b71c1c"   # red
_C_ZERO   = "#cccccc"   # gray for $0 buckets

# ReportLab color objects for card values
_RC_0_30   = colors.HexColor(_C_0_30)
_RC_31_60  = colors.HexColor(_C_31_60)
_RC_61_90  = colors.HexColor(_C_61_90)
_RC_OVER90 = colors.HexColor(_C_OVER90)
_RC_ZERO   = colors.HexColor(_C_ZERO)


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


def _bucket_info(age_days):
    """Return (label_str, hex_color_str) for an age in days."""
    if age_days <= 30:
        return "0-30d",   _C_0_30
    elif age_days <= 60:
        return "31-60d",  _C_31_60
    elif age_days <= 90:
        return "61-90d",  _C_61_90
    else:
        return "90+d",    _C_OVER90


def _bucket_color_obj(val, rc):
    """Return gray color if val is 0, otherwise rc."""
    return _RC_ZERO if (not val or float(val) == 0) else rc


def generate_pdf(customer_data, output_path):
    """
    Generate a single account statement PDF for one customer.
    Matches the HRH HTML statement format exactly.
    """
    margin     = 0.6 * inch
    content_w  = letter[0] - 2 * margin   # ~7.3 inches

    doc = SimpleDocTemplate(
        output_path,
        pagesize=letter,
        leftMargin=margin,
        rightMargin=margin,
        topMargin=0.55 * inch,
        bottomMargin=0.6 * inch,
    )

    # ── Styles ──────────────────────────────────────────────────────────────
    def _ps(name, **kw):
        return ParagraphStyle(name, **kw)

    s_hrh     = _ps("hrh",  fontSize=7.5, textColor=MED_GRAY,  alignment=TA_RIGHT)
    s_title   = _ps("title",fontSize=13,  textColor=PRIMARY_BLUE, fontName="Helvetica-Bold", spaceAfter=3)
    s_sub     = _ps("sub",  fontSize=8.5, textColor=MED_GRAY,  spaceAfter=8)
    s_card_lbl= _ps("clbl", fontSize=6.5, textColor=MED_GRAY,  fontName="Helvetica-Bold",
                    alignment=TA_CENTER, spaceAfter=2)
    s_tbl_hdr = _ps("thdr", fontSize=7.5, textColor=colors.white,
                    fontName="Helvetica-Bold", alignment=TA_CENTER)
    s_cell    = _ps("cell", fontSize=8,   textColor=DARK_TEXT)
    s_cell_r  = _ps("cr",   fontSize=8,   textColor=DARK_TEXT,  alignment=TA_RIGHT)
    s_bold8   = _ps("b8",   fontSize=8,   fontName="Helvetica-Bold")
    s_bold_r9 = _ps("br9",  fontSize=9,   fontName="Helvetica-Bold",
                    textColor=PRIMARY_BLUE, alignment=TA_RIGHT)
    s_foot_l  = _ps("ftl",  fontSize=8.5, fontName="Helvetica-Bold", alignment=TA_RIGHT)
    s_link    = _ps("lnk",  fontSize=8,   textColor=PRIMARY_BLUE)
    s_footer  = _ps("pgft", fontSize=7.5, textColor=MED_GRAY,   alignment=TA_CENTER)

    story = []

    # ── HRH Sender line ─────────────────────────────────────────────────────
    story.append(Table(
        [[Paragraph(HRH_NAME + "  |  " + HRH_EMAIL + "  |  " + HRH_PHONE, s_hrh)]],
        colWidths=[content_w]
    ))
    story.append(Spacer(1, 3))
    story.append(HRFlowable(width="100%", thickness=0.5, color=MED_BLUE_BDR, spaceAfter=5))

    # ── Title ───────────────────────────────────────────────────────────────
    month_year = date.today().strftime("%B %Y")
    story.append(Paragraph(
        "Account Statement — " + customer_data["customer_name"] + " (" + month_year + ")",
        s_title
    ))

    # ── Subtitle (generated date + customer contact) ─────────────────────
    parts = ["Generated " + date.today().strftime("%m/%d/%Y")]
    if customer_data.get("customer_email"):
        parts.append(customer_data["customer_email"])
    if customer_data.get("customer_phone"):
        parts.append(customer_data["customer_phone"])
    story.append(Paragraph(" • ".join(parts), s_sub))

    # ── Summary Cards ───────────────────────────────────────────────────────
    b     = customer_data["buckets"]
    total = customer_data["total"]

    card_gap  = 5
    card_cols = 5
    card_w    = (content_w - (card_cols - 1) * card_gap) / card_cols

    def _card(lbl, val, val_color):
        inner = Table(
            [[Paragraph(lbl,           s_card_lbl)],
             [Paragraph(val,           ParagraphStyle("cv", fontSize=13,
                                       textColor=val_color,
                                       fontName="Helvetica-Bold",
                                       alignment=TA_CENTER))]],
            colWidths=[card_w],
        )
        inner.setStyle(TableStyle([
            ("BACKGROUND",    (0, 0), (-1, -1), colors.white),
            ("TOPPADDING",    (0, 0), (-1, -1), 7),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
            ("LEFTPADDING",   (0, 0), (-1, -1), 3),
            ("RIGHTPADDING",  (0, 0), (-1, -1), 3),
            ("BOX",           (0, 0), (-1, -1), 0.5, MED_BLUE_BDR),
        ]))
        return inner

    b0  = b.get("0_30",  0)
    b31 = b.get("31_60", 0)
    b61 = b.get("61_90", 0)
    b90 = b.get("over_90", 0)

    cards_row = [[
        _card("TOTAL AR",      _fmt_money(total), PRIMARY_BLUE),
        _card("0–30 DAYS",   _fmt_money(b0),    _bucket_color_obj(b0,  _RC_0_30)),
        _card("31–60 DAYS",  _fmt_money(b31),   _bucket_color_obj(b31, _RC_31_60)),
        _card("61–90 DAYS",  _fmt_money(b61),   _bucket_color_obj(b61, _RC_61_90)),
        _card("90+ DAYS",      _fmt_money(b90),   _bucket_color_obj(b90, _RC_OVER90)),
    ]]

    cards_tbl = Table(cards_row,
                      colWidths=[card_w] * card_cols,
                      spaceBefore=2, spaceAfter=10)
    cards_tbl.setStyle(TableStyle([
        ("LEFTPADDING",   (0, 0), (-1, -1), card_gap // 2),
        ("RIGHTPADDING",  (0, 0), (-1, -1), card_gap // 2),
        ("TOPPADDING",    (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
    ]))
    story.append(cards_tbl)

    # ── Invoice Table ────────────────────────────────────────────────────────
    # Columns: # | Date | Invoice # | Description | Amount | Pay
    col_w = [
        0.27 * inch,   # #
        0.87 * inch,   # Date
        0.95 * inch,   # Invoice #
        3.25 * inch,   # Description
        0.97 * inch,   # Amount
        0.89 * inch,   # Pay
    ]
    # Total ≈ 7.2" within 7.3" content width

    inv_rows = [["#", "Date", "Invoice", "Description", "Amount", "Pay"]]

    for i, inv in enumerate(customer_data["invoices"], start=1):
        raw_num     = inv["id"]
        display_num = raw_num.lstrip("0") or raw_num
        date_str    = _fmt_date(inv.get("date", ""))
        age_days    = inv.get("age_days", 0)
        blabel, bcolor = _bucket_info(age_days)

        desc_para = Paragraph(
            "Microgreens <font color='" + bcolor + "'><b>[" + blabel + "]</b></font>",
            s_cell
        )

        pay_url = inv.get("url", "")
        if pay_url:
            pay_cell = Paragraph(
                "<link href='" + pay_url + "'><u>Pay Here</u></link>",
                s_link
            )
        else:
            pay_cell = Paragraph("—", s_cell)

        inv_rows.append([
            str(i),
            date_str,
            Paragraph("<b>" + display_num + "</b>", s_bold8),
            desc_para,
            _fmt_money(inv["amount"]),
            pay_cell,
        ])

    # Footer row — spans columns 0-3 for "TOTAL DUE", amount in col 4
    footer_row_idx = len(inv_rows)
    inv_rows.append([
        Paragraph("<b>TOTAL DUE</b>", s_foot_l),
        "", "", "",
        Paragraph("<b>" + _fmt_money(total) + "</b>", s_bold_r9),
        "",
    ])

    inv_tbl = Table(inv_rows, colWidths=col_w, repeatRows=1)
    inv_tbl.setStyle(TableStyle([
        # ── Header row ──
        ("BACKGROUND",    (0, 0), (-1, 0),               PRIMARY_BLUE),
        ("TEXTCOLOR",     (0, 0), (-1, 0),               colors.white),
        ("FONTNAME",      (0, 0), (-1, 0),               "Helvetica-Bold"),
        ("FONTSIZE",      (0, 0), (-1, 0),               7.5),
        ("ALIGN",         (0, 0), (-1, 0),               "CENTER"),
        # ── Data rows ──
        ("FONTSIZE",      (0, 1), (-1, footer_row_idx - 1), 8),
        ("LINEBELOW",     (0, 1), (-1, footer_row_idx - 1), 0.5, ROW_BORDER),
        # ── Alignment ──
        ("ALIGN",         (0, 1), (0, -1),               "CENTER"),   # #
        ("ALIGN",         (4, 0), (4, -1),               "RIGHT"),    # Amount
        ("ALIGN",         (5, 0), (5, -1),               "CENTER"),   # Pay
        # ── Footer row ──
        ("BACKGROUND",    (0, footer_row_idx), (-1, footer_row_idx), LIGHT_BLUE_BG),
        ("LINEABOVE",     (0, footer_row_idx), (-1, footer_row_idx), 1.5, PRIMARY_BLUE),
        ("SPAN",          (0, footer_row_idx), (3, footer_row_idx)),
        ("FONTNAME",      (0, footer_row_idx), (-1, footer_row_idx), "Helvetica-Bold"),
        ("FONTSIZE",      (0, footer_row_idx), (-1, footer_row_idx), 8.5),
        # ── Global ──
        ("VALIGN",        (0, 0), (-1, -1),              "MIDDLE"),
        ("TOPPADDING",    (0, 0), (-1, -1),              4),
        ("BOTTOMPADDING", (0, 0), (-1, -1),              4),
        ("LEFTPADDING",   (0, 0), (-1, -1),              5),
        ("RIGHTPADDING",  (0, 0), (-1, -1),              5),
    ]))
    story.append(inv_tbl)
    story.append(Spacer(1, 14))

    # ── Page footer ─────────────────────────────────────────────────────────
    story.append(HRFlowable(width="100%", thickness=0.5, color=MED_BLUE_BDR,
                             spaceAfter=5))
    story.append(Paragraph(
        "<b>Please remit payment to:</b> " + HRH_NAME + " • " +
        HRH_EMAIL + " • " + HRH_PHONE,
        s_footer
    ))

    doc.build(story)
