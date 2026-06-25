"""
generate.py — main entrypoint for HRH account statements.

Called by the GitHub Action. Outputs:
  docs/index.html            — aging dashboard
  docs/pdfs/<name>.pdf       — one PDF per customer with outstanding balance

Required environment variable:
  SQUARE_ACCESS_TOKEN        — your Square production access token

Optional environment variables (have sensible defaults):
  SQUARE_LOCATION_ID         — defaults to BYZ5P0549Z01F
  LOOKBACK_DAYS              — how far back to search invoices (default 365)
"""

import os
import sys
from datetime import date

from square_client import get_customer, get_all_unpaid_invoices, get_line_items_for_orders
from pdf_generator import generate_pdf
from dashboard import generate_dashboard

# ── Config ────────────────────────────────────────────────────────────────────
DOCS_DIR    = os.path.join(os.path.dirname(__file__), "..", "docs")
PDF_DIR     = os.path.join(DOCS_DIR, "pdfs")
DASHBOARD   = os.path.join(DOCS_DIR, "index.html")
STMT_PREFIX = "HRH"
MIN_BALANCE = 0.01


# ── Helpers ───────────────────────────────────────────────────────────────────

def _aging(invoices, today):
    b0 = b1 = b2 = b3 = 0.0
    for inv in invoices:
        d   = inv["date"]
        age = (today - date(int(d[:4]), int(d[5:7]), int(d[8:10]))).days
        if   age <= 30: b0 += inv["amount"]
        elif age <= 60: b1 += inv["amount"]
        elif age <= 90: b2 += inv["amount"]
        else:           b3 += inv["amount"]
    return round(b0,2), round(b1,2), round(b2,2), round(b3,2)


def _safe(s):
    for ch in (" ", "/", "'", ",", "&"):
        s = s.replace(ch, "_")
    return s.strip("_")


def _pdf_filename(cust, yyyymm):
    if cust["company_name"]:
        return f"{_safe(cust['name'])}_{_safe(cust['company_name'])}_Statement_{yyyymm}.pdf"
    return f"{_safe(cust['name'])}_Statement_{yyyymm}.pdf"


# ── Main ──────────────────────────────────────────────────────────────────────

def run():
    os.makedirs(PDF_DIR,  exist_ok=True)
    os.makedirs(DOCS_DIR, exist_ok=True)

    today  = date.today()
    yyyymm = today.strftime("%Y%m")

    print("Fetching all unpaid invoices from Square…")
    raw_map = get_all_unpaid_invoices()
    print(f"  Found balances for {len(raw_map)} customer(s)")

    # ── Build result rows ────────────────────────────────────────────────────
    results = []
    for seq, (cid, invoices) in enumerate(raw_map.items(), 1):
        if not invoices:
            continue
        total = round(sum(i["amount"] for i in invoices), 2)
        if total < MIN_BALANCE:
            continue

        print(f"  Looking up customer {cid}…", end=" ", flush=True)
        cust = get_customer(cid)
        display = cust["company_name"] or cust["name"]
        print(display)

        b0, b1, b2, b3 = _aging(invoices, today)
        fname    = _pdf_filename(cust, yyyymm)
        pdf_path = os.path.join(PDF_DIR, fname)
        pdf_url  = f"pdfs/{fname}"

        results.append({
            "cust_id":       cid,
            "name":          cust["name"],
            "company_name":  display,
            "email":         cust["email"],
            "phone":         cust["phone"],
            "stmt_no":       f"{STMT_PREFIX}-{yyyymm}-{seq:03d}",
            "invoices":      invoices,
            "invoice_count": len(invoices),
            "total":         total,
            "b0_30":         b0,
            "b31_60":        b1,
            "b61_90":        b2,
            "b90plus":       b3,
            "pdf_url":       pdf_url,
            "_pdf_path":     pdf_path,
            "_cust":         cust,
        })

    if not results:
        print("No outstanding balances found.")
        generate_dashboard([], DASHBOARD)
        return

    # Sort highest balance first, re-number
    results.sort(key=lambda r: r["total"], reverse=True)
    for i, r in enumerate(results, 1):
        r["stmt_no"] = f"{STMT_PREFIX}-{yyyymm}-{i:03d}"

    # ── Enrich invoices with line items ──────────────────────────────────────
    all_order_ids = [
        inv["order_id"]
        for r in results
        for inv in r["invoices"]
        if inv.get("order_id")
    ]
    if all_order_ids:
        print(f"\nFetching line items for {len(all_order_ids)} invoice(s)…")
        order_items = get_line_items_for_orders(all_order_ids)
        for r in results:
            for inv in r["invoices"]:
                oid = inv.get("order_id", "")
                if oid and oid in order_items:
                    inv["line_items"] = order_items[oid]

    # ── Generate PDFs ────────────────────────────────────────────────────────
    print(f"\nGenerating {len(results)} PDF(s)…")
    for r in results:
        try:
            generate_pdf(r["_pdf_path"], r["_cust"], r["invoices"], r["stmt_no"])
            print(f"  ✓  {r['company_name']:<40} ${r['total']:>9,.2f}")
        except Exception as e:
            print(f"  ✗  {r['company_name']}: {e}", file=sys.stderr)

    # ── Generate dashboard ───────────────────────────────────────────────────
    generate_dashboard(results, DASHBOARD)

    # ── Summary ──────────────────────────────────────────────────────────────
    grand_total = sum(r["total"] for r in results)
    grand_inv   = sum(r["invoice_count"] for r in results)
    print(f"\n{'─' * 55}")
    print(f"  Customers : {len(results)}")
    print(f"  Invoices  : {grand_inv}")
    print(f"  Total AR  : ${grand_total:,.2f}")
    print(f"  Dashboard : {DASHBOARD}")
    print(f"  PDFs      : {PDF_DIR}/")


if __name__ == "__main__":
    run()
