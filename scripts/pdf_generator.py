"""
pdf_generator.py — ReportLab PDF statement builder.

Entry point: generate_pdf(output_path, customer, invoices, stmt_no)
"""

from datetime import date
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle,
    Spacer, Paragraph, HRFlowable,
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_RIGHT, TA_CENTER

# ── HRH constants ─────────────────────────────────────────────────────────────
HRH_NAME  = "High Ridge Hydroponics LLC"
HRH_ADDR1 = "1 1/2 Island Brook Avenue, Building B"
HRH_CITY  = "Bridgeport, CT 06606"
HRH_PHONE = "203-788-5180"
HRH_EMAIL = "highridgehydroponics@gmail.com"

# ── Design tokens ─────────────────────────────────────────────────────────────
HRH_BLUE   = colors.HexColor("#1565C0")
LIGHT_BLUE = colors.HexColor("#E3F2FD")
MID_BLUE   = colors.HexColor("#BBDEFB")
WHITE      = colors.white
DARK       = colors.HexColor("#1A1A1A")
GREY       = colors.HexColor("#555555")
LIGHT_GREY = colors.HexColor("#F5F5F5")
PAGE_W, PAGE_H = letter
MARGIN = 0.55 * inch
_SS = getSampleStyleSheet()


def _ps(name: str, **kw) -> ParagraphStyle:
    return ParagraphStyle(name, parent=_SS["Normal"], **kw)


def _aging(invoices: list[dict], today: date) -> tuple[float, float, float, float]:
    b0 = b1 = b2 = b3 = 0.0
    for inv in invoices:
        d   = inv["date"]
        age = (today - date(int(d[:4]), int(d[5:7]), int(d[8:10]))).days
        if   age <= 30: b0 += inv["amount"]
        elif age <= 60: b1 += inv["amount"]
        elif age <= 90: b2 += inv["amount"]
        else:           b3 += inv["amount"]
    return round(b0, 2), round(b1, 2), round(b2, 2), round(b3, 2)


def _fmt(d: str) -> str:
    return f"{d[5:7]}/{d[8:10]}/{d[:4]}"


def _border_footer(canvas, doc):
    canvas.saveState()
    canvas.setStrokeColor(HRH_BLUE)
    canvas.setLineWidth(1.5)
    canvas.rect(0.3 * inch, 0.3 * inch, PAGE_W - 0.6 * inch, PAGE_H - 0.6 * inch)
    canvas.setFont("Helvetica-Bold", 9)
    canvas.setFillColor(DARK)
    canvas.drawCentredString(
        PAGE_W / 2, 0.45 * inch,
        f"Questions? Contact Joe Alvarez  |  {HRH_PHONE}  |  {HRH_EMAIL}",
    )
    canvas.restoreState()


def generate_pdf(
    output_path: str,
    customer:    dict,
    invoices:    list[dict],
    stmt_no:     str,
) -> None:
    today     = date.today()
    today_str = today.strftime("%m/%d/%Y")
    total     = round(sum(i["amount"] for i in invoices), 2)
    b0, b1, b2, b3 = _aging(invoices, today)
    dates  = [i["date"] for i in invoices]
    period = (
        f"{_fmt(min(dates))} - {_fmt(max(dates))}"
        if len(dates) > 1 else _fmt(dates[0])
    )

    sNorm    = _ps("norm",    fontSize=10, textColor=DARK)
    sBold    = _ps("bold",    fontSize=10, textColor=DARK,  fontName="Helvetica-Bold")
    sBoldR   = _ps("boldR",   fontSize=10, textColor=DARK,  fontName="Helvetica-Bold", alignment=TA_RIGHT)
    sWhiteB  = _ps("whiteB",  fontSize=10, textColor=WHITE, fontName="Helvetica-Bold")
    sWhiteR  = _ps("whiteR",  fontSize=10, textColor=WHITE, fontName="Helvetica-Bold", alignment=TA_RIGHT)
    sLink    = _ps("link",    fontSize=9,  textColor=HRH_BLUE, fontName="Helvetica-Bold", alignment=TA_CENTER)
    sSmall   = _ps("small",   fontSize=8,  textColor=GREY)
    sStmtLbl = _ps("sLbl",    fontSize=10, textColor=DARK,  fontName="Helvetica-Bold", alignment=TA_RIGHT)
    sStmtVal = _ps("sVal",    fontSize=10, textColor=DARK,  alignment=TA_RIGHT)
    sPayable = _ps("pay",     fontSize=10, textColor=DARK,  fontName="Helvetica-Bold", alignment=TA_CENTER)
    sPayAddr = _ps("paddr",   fontSize=9,  textColor=DARK,  alignment=TA_CENTER)
    sCompany = _ps("co",      fontSize=14, textColor=HRH_BLUE, fontName="Helvetica-Bold")

    doc = SimpleDocTemplate(
        output_path, pagesize=letter,
        leftMargin=MARGIN, rightMargin=MARGIN,
        topMargin=MARGIN,  bottomMargin=0.6 * inch,
    )
    els = []

    # ── Header ────────────────────────────────────────────────────────────────
    farm_tbl = Table([
        [Paragraph(HRH_NAME,  sCompany)],
        [Paragraph(HRH_ADDR1, sSmall)],
        [Paragraph(HRH_CITY,  sSmall)],
    ], colWidths=[4.55 * inch])
    farm_tbl.setStyle(TableStyle([
        ("TOPPADDING",    (0, 0), (-1, -1), 1),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
    ]))

    stmt_tbl = Table([
        [Paragraph("<b>ACCOUNT STATEMENT</b>", sStmtLbl)],
        [Paragraph(f"Date: {today_str}",        sStmtVal)],
        [Paragraph(f"Statement #: {stmt_no}",   sStmtVal)],
        [Paragraph(f"Period: {period}",          sStmtVal)],
    ], colWidths=[2.65 * inch])
    stmt_tbl.setStyle(TableStyle([
        ("TOPPADDING",    (0, 0), (-1, -1), 1),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
    ]))

    header = Table([[farm_tbl, stmt_tbl]], colWidths=[4.55 * inch, 2.65 * inch])
    header.setStyle(TableStyle([
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        ("BACKGROUND",    (0, 0), (-1, -1), LIGHT_GREY),
        ("TOPPADDING",    (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("LEFTPADDING",   (0, 0), (0,  -1), 8),
    ]))
    els += [header, HRFlowable(width="100%", thickness=2, color=HRH_BLUE), Spacer(1, 0.15 * inch)]

    # ── Bill To + Aging Summary ───────────────────────────────────────────────
    bill_rows = [
        [Paragraph("<b>Bill To:</b>",                  sBold)],
        [Paragraph(customer.get("name", ""),           sNorm)],
        [Paragraph(customer.get("company_name", ""),   sNorm)],
        [Paragraph(customer.get("street", ""),         sNorm)],
        [Paragraph(customer.get("city_state_zip", ""), sNorm)],
    ]
    if customer.get("phone"):
        bill_rows.append([Paragraph(customer["phone"], sNorm)])
    bill_tbl = Table(bill_rows, colWidths=[3.1 * inch])
    bill_tbl.setStyle(TableStyle([
        ("TOPPADDING",    (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    ]))

    aging_tbl = Table([
        [Paragraph("Account Aging Summary",      sWhiteB), Paragraph("Balance",            sWhiteR)],
        [Paragraph("0 - 30 Days",  sBold),                 Paragraph(f"${b0:,.2f}",  sBoldR)],
        [Paragraph("31 - 60 Days", sBold),                 Paragraph(f"${b1:,.2f}",  sBoldR)],
        [Paragraph("61 - 90 Days", sBold),                 Paragraph(f"${b2:,.2f}",  sBoldR)],
        [Paragraph("90+ Days",     sBold),                 Paragraph(f"${b3:,.2f}",  sBoldR)],
        [Paragraph("<b>Total Balance Due</b>",   sBold),   Paragraph(f"<b>${total:,.2f}</b>", sBoldR)],
    ], colWidths=[2.0 * inch, 1.2 * inch])
    aging_tbl.setStyle(TableStyle([
        ("BACKGROUND",    (0,  0), (-1,  0), HRH_BLUE),
        ("ROWBACKGROUNDS",(0,  1), (-1, -2), [WHITE, LIGHT_BLUE]),
        ("LINEABOVE",     (0, -1), (-1, -1), 1.2, HRH_BLUE),
        ("BACKGROUND",    (0, -1), (-1, -1), MID_BLUE),
        ("TOPPADDING",    (0,  0), (-1, -1), 5),
        ("BOTTOMPADDING", (0,  0), (-1, -1), 5),
        ("LEFTPADDING",   (0,  0), (-1, -1), 6),
        ("RIGHTPADDING",  (0,  0), (-1, -1), 6),
        ("GRID",          (0,  1), (-1, -2), 0.4, colors.lightgrey),
    ]))

    side = Table([[bill_tbl, "", aging_tbl]], colWidths=[3.1 * inch, 0.5 * inch, 3.2 * inch])
    side.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")]))
    els += [side, Spacer(1, 0.2 * inch)]

    # ── Invoice table ─────────────────────────────────────────────────────────
    rows = [[
        Paragraph("<b>Date</b>",        sWhiteB),
        Paragraph("<b>Invoice #</b>",   sWhiteB),
        Paragraph("<b>Description</b>", sWhiteB),
        Paragraph("<b>Amount</b>",      sWhiteR),
        Paragraph("<b>Pay</b>",         sWhiteB),
    ]]
    for inv in invoices:
        pay = (
            Paragraph(f'<link href="{inv["url"]}"><u>Pay Here</u></link>', sLink)
            if inv.get("url") else Paragraph("—", sNorm)
        )
        rows.append([
            Paragraph(_fmt(inv["date"]),          sBold),
            Paragraph(inv["id"],                  sBold),
            Paragraph("Microgreens",              sBold),
            Paragraph(f"${inv['amount']:,.2f}",   sBoldR),
            pay,
        ])
    rows.append(["", "", "", Paragraph(f"<b>TOTAL DUE<br/>${total:,.2f}</b>", sBoldR), ""])

    inv_tbl = Table(rows, colWidths=[0.9*inch, 1.55*inch, 2.25*inch, 1.1*inch, 1.0*inch])
    inv_tbl.setStyle(TableStyle([
        ("BACKGROUND",    (0,  0), (-1,  0), HRH_BLUE),
        ("ROWBACKGROUNDS",(0,  1), (-1, -2), [WHITE, LIGHT_BLUE]),
        ("GRID",          (0,  0), (-1, -2), 0.4, colors.lightgrey),
        ("LINEABOVE",     (0, -1), (-1, -1), 1.2, HRH_BLUE),
        ("BACKGROUND",    (0, -1), (-1, -1), MID_BLUE),
        ("TOPPADDING",    (0,  0), (-1, -1), 5),
        ("BOTTOMPADDING", (0,  0), (-1, -1), 5),
        ("LEFTPADDING",   (0,  0), (-1, -1), 6),
        ("RIGHTPADDING",  (0,  0), (-1, -1), 6),
        ("VALIGN",        (0,  0), (-1, -1), "MIDDLE"),
    ]))
    els += [inv_tbl, Spacer(1, 0.2 * inch)]

    # ── Remittance footer ─────────────────────────────────────────────────────
    payable_tbl = Table([
        [Paragraph("Please make checks payable to:",     sPayable)],
        [Paragraph(f"<b>{HRH_NAME}</b>",                sPayable)],
        [Paragraph(f"{HRH_ADDR1}  —  {HRH_CITY}",      sPayAddr)],
    ], colWidths=[7.2 * inch])
    payable_tbl.setStyle(TableStyle([
        ("TOPPADDING",    (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ("ALIGN",         (0, 0), (-1, -1), "CENTER"),
    ]))
    els.append(payable_tbl)

    doc.build(els, onFirstPage=_border_footer, onLaterPages=_border_footer)
