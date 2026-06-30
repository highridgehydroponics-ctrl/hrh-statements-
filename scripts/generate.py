"""
generate.py — Main entrypoint for HRH Statements Dashboard.

Pipeline:
  1. Fetch all unpaid Square invoices (flat list)
  2. Fetch AppSheet invoice→client mapping (invoice_number → appsheet_client_id)
  3. Fetch AppSheet client details (client_id → name/address/email/phone)
  4. Enrich each invoice with its AppSheet client_id
  5. Group invoices by AppSheet client_id
     - Fallback: group by Square customer_id if no AppSheet match
  6. Compute aging buckets per customer group
  6b. Merge groups that share the same Square customer ID (handles split AppSheet records)
  7. Sort by total balance descending, assign statement numbers
  8. Batch-fetch Square order line items
  9. Generate PDFs
 10. Generate HTML dashboard
"""

import os
import re
from datetime import date, datetime
from collections import defaultdict

from square_client import (
    get_all_unpaid_invoices,
    get_customer,
    get_line_items_for_orders,
    get_appsheet_clients,
    get_appsheet_invoice_client_map,
)
from pdf_generator import generate_pdf
from dashboard import generate_dashboard

DOCS_DIR = os.path.join(os.path.dirname(__file__), "..", "docs")
PDFS_DIR = os.path.join(DOCS_DIR, "pdfs")


def safe_filename(name):
    """Convert a name to a safe filename slug."""
    s = re.sub(r"[^\w\s-]", "", name)
    s = re.sub(r"[\s]+", "_", s.strip())
    return s[:80]


def age_bucket(invoice_date_str):
    """Return number of days since invoice date."""
    try:
        inv_date = datetime.strptime(invoice_date_str, "%Y-%m-%d").date()
        return (date.today() - inv_date).days
    except Exception:
        return 0


def main():
    os.makedirs(PDFS_DIR, exist_ok=True)

    print("Fetching unpaid Square invoices...")
    all_invoices = get_all_unpaid_invoices()
    print(f"  Found {len(all_invoices)} unpaid/partially-paid invoices")

    # ── Step 2: AppSheet invoice→client mapping ──────────────────────────────
    print("Fetching AppSheet invoice→client mapping...")
    try:
        inv_client_map = get_appsheet_invoice_client_map()
        print(f"  Mapped {len(inv_client_map)} invoices to AppSheet clients")
    except Exception as e:
        print(f"  WARNING: Could not fetch AppSheet order mapping: {e}")
        inv_client_map = {}

    # ── Step 3: AppSheet client details ─────────────────────────────────────
    print("Fetching AppSheet client details...")
    try:
        appsheet_clients = get_appsheet_clients()
        print(f"  Found {len(appsheet_clients)} AppSheet clients")
    except Exception as e:
        print(f"  WARNING: Could not fetch AppSheet clients: {e}")
        appsheet_clients = {}

    # ── Step 4: Enrich each invoice with AppSheet client_id + sent_at ──────────
    for inv in all_invoices:
        inv_num = inv["id"].lstrip("0") or inv["id"]  # strip leading zeros for lookup
        # Try exact match first, then zero-stripped match
        map_entry = (
            inv_client_map.get(inv["id"])
            or inv_client_map.get(inv_num)
        )
        if isinstance(map_entry, dict):
            inv["appsheet_client_id"] = map_entry.get("client_id")
            inv["sent_at"]            = map_entry.get("sent_at", "")
        else:
            # Fallback for older mapping format (plain string)
            inv["appsheet_client_id"] = map_entry if isinstance(map_entry, str) else None
            inv["sent_at"]            = ""

    # ── Step 5: Group by AppSheet client_id (with fallback) ──────────────────
    # Primary key: appsheet_client_id
    # Fallback key: "sq_<cust_id>" (Square customer ID) when no AppSheet match
    groups = defaultdict(list)  # key → [invoice, ...]

    for inv in all_invoices:
        if inv["appsheet_client_id"]:
            key = inv["appsheet_client_id"]
        else:
            key = f"sq_{inv['cust_id']}"
        groups[key].append(inv)

    print(f"  Grouped into {len(groups)} customer statements")

    # ── Step 6: Build customer result objects ────────────────────────────────
    today = date.today()
    results = []

    # Cache Square customer lookups to avoid repeated API calls
    _square_customer_cache = {}

    def get_square_customer_cached(cust_id):
        if cust_id not in _square_customer_cache:
            try:
                _square_customer_cache[cust_id] = get_customer(cust_id)
            except Exception as e:
                print(f"  WARNING: Could not fetch Square customer {cust_id}: {e}")
                _square_customer_cache[cust_id] = {
                    "name": cust_id, "company": "", "email": "", "phone": "", "address": ""
                }
        return _square_customer_cache[cust_id]

    for key, invoices in groups.items():
        total = round(sum(inv["amount"] for inv in invoices), 2)
        if total <= 0:
            continue  # skip zero-balance groups

        # ── Resolve customer info ────────────────────────────────────────────
        is_appsheet_key = not key.startswith("sq_")

        if is_appsheet_key and key in appsheet_clients:
            ac = appsheet_clients[key]
            customer_name    = ac["name"] or key
            customer_email   = ac["email"]
            customer_phone   = ac["phone"]
            customer_address = ac["address"]
        else:
            # Fallback: pull from Square customer record
            sq_cust_id = invoices[0]["cust_id"] if invoices else ""
            sq_info = get_square_customer_cached(sq_cust_id) if sq_cust_id else {}
            customer_name    = sq_info.get("company") or sq_info.get("name") or sq_cust_id
            customer_email   = sq_info.get("email", "")
            customer_phone   = sq_info.get("phone", "")
            customer_address = sq_info.get("address", "")

        if not customer_name:
            customer_name = key  # last-resort label

        # ── Aging buckets ────────────────────────────────────────────────────
        buckets = {"0_30": 0.0, "31_60": 0.0, "61_90": 0.0, "over_90": 0.0}
        for inv in invoices:
            days = age_bucket(inv["date"])
            inv["age_days"] = days
            if days <= 30:
                buckets["0_30"] += inv["amount"]
            elif days <= 60:
                buckets["31_60"] += inv["amount"]
            elif days <= 90:
                buckets["61_90"] += inv["amount"]
            else:
                buckets["over_90"] += inv["amount"]

        # Sort invoices oldest → newest
        invoices_sorted = sorted(invoices, key=lambda x: x["date"])

        results.append({
            "key":             key,
            "appsheet_id":     key if is_appsheet_key else None,
            "customer_name":   customer_name,
            "customer_email":  customer_email,
            "customer_phone":  customer_phone,
            "customer_address":customer_address,
            "total":           total,
            "buckets":         {k: round(v, 2) for k, v in buckets.items()},
            "invoices":        invoices_sorted,
        })

    # ── Step 6b: Merge groups sharing the same Square customer ID ───────────
    # Happens when a customer has two AppSheet client records (e.g. data entry duplicate).
    # Group results by Square cust_id, then consolidate any multi-group customers.
    sq_cust_buckets = defaultdict(list)
    for r in results:
        # Collect the set of Square customer IDs used by this group's invoices
        sq_ids = set(inv["cust_id"] for inv in r["invoices"] if inv.get("cust_id"))
        if len(sq_ids) == 1:
            sq_cust_buckets[next(iter(sq_ids))].append(r)
        else:
            # Mixed Square customers within one group — don't merge, keep as-is
            sq_cust_buckets[f"__mixed_{r['key']}"].append(r)

    merged_results = []
    for sq_id, group_list in sq_cust_buckets.items():
        if len(group_list) == 1:
            merged_results.append(group_list[0])
            continue

        # Merge: pick the record with the most contact info as primary
        primary = max(
            group_list,
            key=lambda r: len(
                (r.get("customer_email") or "")
                + (r.get("customer_phone") or "")
                + (r.get("customer_address") or "")
            ),
        )
        print(
            f"  Merging {len(group_list)} statements for Square customer "
            f"{sq_id} → '{primary['customer_name']}'"
        )

        # Combine all invoices, deduplicate by invoice_id
        all_invs = [inv for r in group_list for inv in r["invoices"]]
        seen = set()
        unique_invs = []
        for inv in all_invs:
            if inv["invoice_id"] not in seen:
                seen.add(inv["invoice_id"])
                unique_invs.append(inv)
        unique_invs.sort(key=lambda x: x["date"])

        # Recompute total and aging buckets
        merged_total = round(sum(inv["amount"] for inv in unique_invs), 2)
        merged_buckets = {"0_30": 0.0, "31_60": 0.0, "61_90": 0.0, "over_90": 0.0}
        for inv in unique_invs:
            days = inv.get("age_days", 0)
            if days <= 30:
                merged_buckets["0_30"] += inv["amount"]
            elif days <= 60:
                merged_buckets["31_60"] += inv["amount"]
            elif days <= 90:
                merged_buckets["61_90"] += inv["amount"]
            else:
                merged_buckets["over_90"] += inv["amount"]

        primary["invoices"] = unique_invs
        primary["total"] = merged_total
        primary["buckets"] = {k: round(v, 2) for k, v in merged_buckets.items()}
        merged_results.append(primary)

    if len(merged_results) < len(results):
        print(
            f"  Merged {len(results)} groups → {len(merged_results)} statements "
            f"(collapsed {len(results) - len(merged_results)} duplicate(s))"
        )
    results = merged_results

    # ── Step 7: Sort by total descending, assign statement numbers ────────────
    results.sort(key=lambda x: x["total"], reverse=True)
    for i, r in enumerate(results, start=1):
        r["statement_id"] = f"STMT-{i:03d}"

    print(f"  {len(results)} non-zero statements to generate")

    # ── Step 8: Batch-fetch Square line items ────────────────────────────────
    print("Fetching Square order line items...")
    all_order_ids = [
        inv["order_id"]
        for r in results
        for inv in r["invoices"]
        if inv.get("order_id")
    ]
    line_items_map = get_line_items_for_orders(list(set(all_order_ids)))

    for r in results:
        for inv in r["invoices"]:
            oid = inv.get("order_id", "")
            inv["line_items"] = line_items_map.get(oid, [])

    # ── Step 9: Generate PDFs ────────────────────────────────────────────────
    print("Generating PDFs...")
    for r in results:
        # Use AppSheet client_id in filename to guarantee uniqueness
        # even if two customers share the same display name
        name_slug = safe_filename(r["customer_name"])
        unique_slug = r["appsheet_id"] or safe_filename(r["key"])
        filename = f"{name_slug}__{unique_slug}.pdf"
        pdf_path = os.path.join(PDFS_DIR, filename)
        r["pdf_filename"] = filename

        try:
            generate_pdf(r, pdf_path)
        except Exception as e:
            print(f"  ERROR generating PDF for {r['customer_name']}: {e}")
            r["pdf_filename"] = None

    # ── Step 10: Generate HTML dashboard ────────────────────────────────────
    print("Generating dashboard...")
    dashboard_path = os.path.join(DOCS_DIR, "index.html")
    generate_dashboard(results, dashboard_path)

    total_ar = sum(r["total"] for r in results)
    total_invoices = sum(len(r["invoices"]) for r in results)
    print(
        f"\nDone — {len(results)} statements, "
        f"{total_invoices} invoices, "
        f"${total_ar:,.2f} total AR"
    )


if __name__ == "__main__":
    main()
