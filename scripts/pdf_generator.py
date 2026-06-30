"""
pdf_generator.py — ReportLab PDF statement builder for HRH.
Format matches the generate-account-statement skill spec exactly.
"""

from datetime import date as _date
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle,
    Spacer, Paragraph, HRFlowable
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_RIGHT, TA_CENTER

# ── Colors ──────────────────────────────────────────────────────────────────
HRH_BLUE    = colors.HexColor("#1565C0")
LIGHT_BLUE  = colors.HexColor("#E3F2FD")
MID_BLUE    = colors.HexColor("#BBDEFB")
WHITE       = colors.white
BLACK       = colors.black
DARK        = colors.black          # alias — keep name for any leftover refs
GREY        = colors.HexColor("#555555")
LIGHT_GREY  = colors.HexColor("#F5F5F5")

PAGE_W, PAGE_H = letter
MARGIN = 0.55 * inch

SS = getSampleStyleSheet()


def _ps(name, **kw):
    return ParagraphStyle(name, parent=SS["Normal"], **kw)


# ── Shared styles ────────────────────────────────────────────────────────────
sNorm    = _ps("norm",    fontSize=10, textColor=DARK)
sBold    = _ps("bold",    fontSize=10, textColor=DARK,  fontName="Helvetica-Bold")
sBoldR   = _ps("boldR",   fontSize=10, textColor=DARK,  fontName="Helvetica-Bold", alignment=TA_RIGHT)
sWhiteB  = _ps("whiteB",  fontSize=10, textColor=WHITE, fontName="Helvetica-Bold")
sWhiteR  = _ps("whiteR",  fontSize=10, textColor=WHITE, fontName="Helvetica-Bold", alignment=TA_RIGHT)
sLink    = _ps("link",    fontSize=9,  textColor=HRH_BLUE, fontName="Helvetica-Bold", alignment=TA_CENTER)
sSmall   = _ps("small",   fontSize=8,  textColor=GREY)
sAddr    = _ps("addr",    fontSize=8,  textColor=DARK)
sStmtLbl = _ps("stmtLbl", fontSize=10, textColor=DARK,  fontName="Helvetica-Bold", alignment=TA_RIGHT)
sStmtVal = _ps("stmtVal", fontSize=10, textColor=DARK,  alignment=TA_RIGHT)
sPayable = _ps("payable", fontSize=10, textColor=DARK,  fontName="Helvetica-Bold", alignment=TA_CENTER)
sPayAddr = _ps("payaddr", fontSize=9,  textColor=DARK,  alignment=TA_CENTER)
sCompany = _ps("company", fontSize=14, textColor=HRH_BLUE, fontName="Helvetica-Bold")


def _fmt_date(d):
    """YYYY-MM-DD → MM/DD/YYYY"""
    try:
        return f"{d[5:7]}/{d[8:10]}/{d[:4]}"
    except Exception:
        return d or "—"


def _fmt_phone(raw):
    """Normalize any US phone string to (XXX) XXX-XXXX."""
    import re
    if not raw:
        return raw
    digits = re.sub(r"\D", "", raw)
    if digits.startswith("1") and len(digits) == 11:
        digits = digits[1:]
    if len(digits) == 10:
        return f"({digits[:3]}) {digits[3:6]}-{digits[6:]}"
    return raw  # unrecognized format — return as-is


def _fmt_money(val):
    try:
        return "${:,.2f}".format(float(val))
    except Exception:
        return "$0.00"


def _add_border_and_footer(canvas, doc):
    """Page-level callback: draws blue border + footer contact line."""
    canvas.saveState()
    canvas.setStrokeColor(HRH_BLUE)
    canvas.setLineWidth(1.5)
    canvas.rect(0.3 * inch, 0.3 * inch,
                PAGE_W - 0.6 * inch, PAGE_H - 0.6 * inch)
    canvas.setFont("Helvetica-Bold", 9)
    canvas.setFillColor(DARK)
    canvas.drawCentredString(
        PAGE_W / 2, 0.45 * inch,
        "Questions? Contact Joe Alvarez  |  (203) 788-5180  |  highridgehydroponics@gmail.com"
    )
    canvas.restoreState()


def generate_pdf(customer_data, output_path):
    """
    Generate a single account statement PDF for one customer.

    customer_data keys:
      statement_id, customer_name, customer_email, customer_phone,
      customer_address, total, buckets, invoices
    """
    today     = _date.today()
    today_str = today.strftime("%m/%d/%Y")

    total    = customer_data["total"]
    b        = customer_data["buckets"]
    buckets  = [b.get("0_30", 0), b.get("31_60", 0),
                b.get("61_90", 0), b.get("over_90", 0)]
    invoices = customer_data["invoices"]
    stmt_no  = customer_data["statement_id"]

    # Period string
    dates  = [inv["date"] for inv in invoices if inv.get("date")]
    if len(dates) > 1:
        period = f"{_fmt_date(min(dates))} - {_fmt_date(max(dates))}"
    elif dates:
        period = _fmt_date(dates[0])
    else:
        period = today_str

    doc = SimpleDocTemplate(
        output_path,
        pagesize=letter,
        leftMargin=MARGIN,
        rightMargin=MARGIN,
        topMargin=MARGIN,
        bottomMargin=0.6 * inch,
    )
    els = []

    # ── Header ───────────────────────────────────────────────────────────────
    farm_info = Table([
        [Paragraph("High Ridge Hydroponics LLC", sCompany)],
        [Paragraph("1 1/2 Island Brook Ave, BLDG B", sAddr)],
        [Paragraph("Bridgeport, CT 06606", sAddr)],
    ], colWidths=[4.55 * inch])
    farm_info.setStyle(TableStyle([
        ("TOPPADDING",    (0, 0), (-1, -1), 1),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
        ("BOTTOMPADDING", (0, 0), (0, 0),   8),   # extra gap after company name
    ]))

    stmt_info = Table([
        [Paragraph("<b>ACCOUNT STATEMENT</b>", sStmtLbl)],
        [Paragraph(f"Date: {today_str}",       sStmtVal)],
        [Paragraph(f"Statement #: {stmt_no}",  sStmtVal)],
        [Paragraph(f"Period: {period}",        sStmtVal)],
    ], colWidths=[2.65 * inch])
    stmt_info.setStyle(TableStyle([
        ("TOPPADDING",    (0, 0), (-1, -1), 1),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
    ]))

    header = Table([[farm_info, stmt_info]],
                   colWidths=[4.55 * inch, 2.65 * inch])
    header.setStyle(TableStyle([
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        ("BACKGROUND",    (0, 0), (-1, -1), LIGHT_GREY),
        ("TOPPADDING",    (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("LEFTPADDING",   (0, 0), (0, -1),  8),
    ]))
    els += [header,
            HRFlowable(width="100%", thickness=2, color=HRH_BLUE),
            Spacer(1, 0.15 * inch)]

    # ── Bill To + Aging ───────────────────────────────────────────────────────
    name        = customer_data["customer_name"]
    addr_street = customer_data.get("customer_address_street", "")
    addr_csz    = customer_data.get("customer_address_csz", "")
    address     = customer_data.get("customer_address", "")
    phone       = customer_data.get("customer_phone", "")
    email       = customer_data.get("customer_email", "")

    bill_rows = [
        [Paragraph("<b>Bill To:</b>", sBold)],
        [Paragraph(name, sNorm)],
    ]
    # Street address on its own line, then City, State ZIP on the next
    if addr_street:
        bill_rows.append([Paragraph(addr_street, sNorm)])
    if addr_csz:
        bill_rows.append([Paragraph(addr_csz, sNorm)])
    elif address and not addr_street:
        # Fallback: no structured data available
        bill_rows.append([Paragraph(address, sNorm)])
    if phone:
        bill_rows.append([Paragraph(_fmt_phone(phone), sNorm)])
    if email:
        bill_rows.append([Paragraph(email, sNorm)])

    bill_tbl = Table(bill_rows, colWidths=[3.1 * inch])
    bill_tbl.setStyle(TableStyle([
        ("TOPPADDING",    (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    ]))

    aging_tbl = Table([
        [Paragraph("Account Aging Summary", sWhiteB), Paragraph("Balance", sWhiteR)],
        [Paragraph("0 - 30 Days",   sBold), Paragraph(_fmt_money(buckets[0]), sBoldR)],
        [Paragraph("31 - 60 Days",  sBold), Paragraph(_fmt_money(buckets[1]), sBoldR)],
        [Paragraph("61 - 90 Days",  sBold), Paragraph(_fmt_money(buckets[2]), sBoldR)],
        [Paragraph("90+ Days",      sBold), Paragraph(_fmt_money(buckets[3]), sBoldR)],
        [Paragraph("<b>Total Balance Due</b>", sBold),
         Paragraph(f"<b>{_fmt_money(total)}</b>", sBoldR)],
    ], colWidths=[2.0 * inch, 1.2 * inch])
    aging_tbl.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0),  (-1, 0),  HRH_BLUE),
        ("ROWBACKGROUNDS",(0, 1),  (-1, -2), [WHITE, LIGHT_BLUE]),
        ("LINEABOVE",     (0, -1), (-1, -1), 1.2, HRH_BLUE),
        ("BACKGROUND",    (0, -1), (-1, -1), MID_BLUE),
        ("TOPPADDING",    (0, 0),  (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0),  (-1, -1), 5),
        ("LEFTPADDING",   (0, 0),  (-1, -1), 6),
        ("RIGHTPADDING",  (0, 0),  (-1, -1), 6),
        ("GRID",          (0, 1),  (-1, -2), 0.4, colors.lightgrey),
    ]))

    side = Table([[bill_tbl, "", aging_tbl]],
                 colWidths=[3.1 * inch, 0.5 * inch, 3.2 * inch])
    side.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")]))
    els += [side, Spacer(1, 0.2 * inch)]

    # ── Invoice Table ─────────────────────────────────────────────────────────
    inv_rows = [[
        Paragraph("<b>Date</b>",       sWhiteB),
        Paragraph("<b>Invoice #</b>",  sWhiteB),
        Paragraph("<b>Description</b>",sWhiteB),
        Paragraph("<b>Amount</b>",     sWhiteR),
        Paragraph("<b>Pay</b>",        sWhiteB),
    ]]

    for inv in invoices:
        pay_url = inv.get("url", "")
        if pay_url:
            pay_cell = Paragraph(
                f'<link href="{pay_url}"><u>Pay Here</u></link>', sLink
            )
        else:
            pay_cell = Paragraph("--", sNorm)

        raw_num     = inv.get("id", "")
        display_num = raw_num.lstrip("0") or raw_num

        inv_rows.append([
            Paragraph(_fmt_date(inv.get("date", "")), sBold),
            Paragraph(display_num, sBold),
            Paragraph("Microgreens", sBold),
            Paragraph(_fmt_money(inv.get("amount", 0)), sBoldR),
            pay_cell,
        ])

    # Total Due footer row
    inv_rows.append([
        "", "", "",
        Paragraph(f"<b>TOTAL DUE<br/>{_fmt_money(total)}</b>", sBoldR),
        "",
    ])

    inv_tbl = Table(
        inv_rows,
        colWidths=[0.9 * inch, 1.55 * inch, 2.25 * inch, 1.1 * inch, 1.0 * inch],
    )
    inv_tbl.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0),  (-1, 0),  HRH_BLUE),
        ("ROWBACKGROUNDS",(0, 1),  (-1, -2), [WHITE, LIGHT_BLUE]),
        ("GRID",          (0, 0),  (-1, -2), 0.4, colors.lightgrey),
        ("LINEABOVE",     (0, -1), (-1, -1), 1.2, HRH_BLUE),
        ("BACKGROUND",    (0, -1), (-1, -1), MID_BLUE),
        ("TOPPADDING",    (0, 0),  (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0),  (-1, -1), 5),
        ("LEFTPADDING",   (0, 0),  (-1, -1), 6),
        ("RIGHTPADDING",  (0, 0),  (-1, -1), 6),
        ("VALIGN",        (0, 0),  (-1, -1), "MIDDLE"),
    ]))
    els += [inv_tbl, Spacer(1, 0.2 * inch)]

    # ── Checks Payable ────────────────────────────────────────────────────────
    payable_tbl = Table([
        [Paragraph("Please make checks payable to:", sPayable)],
        [Paragraph("<b>High Ridge Hydroponics LLC</b>", sPayable)],
        [Paragraph("1 1/2 Island Brook Ave,", sPayAddr)],
        [Paragraph("BLDG B", sPayAddr)],
        [Paragraph("Bridgeport, CT", sPayAddr)],
        [Paragraph("06606", sPayAddr)],
    ], colWidths=[7.2 * inch])
    payable_tbl.setStyle(TableStyle([
        ("TOPPADDING",    (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ("ALIGN",         (0, 0), (-1, -1), "CENTER"),
    ]))
    els.append(payable_tbl)

    doc.build(
        els,
        onFirstPage=_add_border_and_footer,
        onLaterPages=_add_border_and_footer,
    )
