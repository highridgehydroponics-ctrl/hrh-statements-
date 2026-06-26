"""
square_client.py — Square REST API + AppSheet integration for HRH Statements Dashboard.

Environment variables:
  SQUARE_ACCESS_TOKEN  (required) — Square Bearer token, set as GitHub Secret
  SQUARE_LOCATION_ID   (optional) — defaults to BYZ5P0549Z01F
  LOOKBACK_DAYS        (optional) — how many days back to search invoices (default 365)
"""

import os
import json
import math
import requests
from datetime import datetime, timedelta, timezone

# ──────────────────────────────────────────────────────────────
# Configuration
# ──────────────────────────────────────────────────────────────
SQUARE_BASE_URL     = "https://connect.squareup.com/v2"
SQUARE_API_VERSION  = "2025-01-23"
SQUARE_TOKEN        = os.environ["SQUARE_ACCESS_TOKEN"]
LOCATION_ID         = os.environ.get("SQUARE_LOCATION_ID", "BYZ5P0549Z01F")
LOOKBACK_DAYS       = int(os.environ.get("LOOKBACK_DAYS", "365"))

APPSHEET_APP_ID  = "bea55701-8006-4581-a791-19a75092943f"
APPSHEET_API_KEY = "V2-f4zl4-pDmwB-IZ9zh-t6ari-vPhJu-FmAwJ-WQ46U-LIUqO"
APPSHEET_BASE    = f"https://api.appsheet.com/api/v2/apps/{APPSHEET_APP_ID}/tables/{{table}}/Action"

SQUARE_HEADERS = {
    "Authorization": f"Bearer {SQUARE_TOKEN}",
    "Square-Version": SQUARE_API_VERSION,
    "Content-Type":   "application/json",
}


# ──────────────────────────────────────────────────────────────
# Square helpers
# ──────────────────────────────────────────────────────────────

def _square_get(path, params=None):
    resp = requests.get(f"{SQUARE_BASE_URL}{path}", headers=SQUARE_HEADERS, params=params)
    resp.raise_for_status()
    return resp.json()


def _square_post(path, body):
    resp = requests.post(f"{SQUARE_BASE_URL}{path}", headers=SQUARE_HEADERS, json=body)
    resp.raise_for_status()
    return resp.json()


def _money_to_float(money_dict):
    """Convert Square money object {amount: int, currency: str} to float dollars."""
    if not money_dict:
        return 0.0
    return money_dict.get("amount", 0) / 100.0


def _normalize_invoice(inv):
    """Flatten a raw Square invoice object into a simple dict."""
    pr = inv.get("primary_recipient", {})
    payment_reqs = inv.get("payment_requests", [])

    # Balance remaining = sum of all payment request remaining amounts
    balance = sum(
        _money_to_float(req.get("computed_amount_money"))
        for req in payment_reqs
    )

    # Invoice date: prefer scheduled_at, fall back to created_at
    raw_date = inv.get("scheduled_at") or inv.get("created_at", "")
    try:
        date_str = raw_date[:10]  # YYYY-MM-DD
    except Exception:
        date_str = ""

    return {
        "invoice_id":  inv.get("id", ""),
        "id":          inv.get("invoice_number", ""),   # e.g. "0004765914"
        "date":        date_str,
        "amount":      round(balance, 2),
        "url":         inv.get("public_url", ""),
        "status":      inv.get("status", ""),
        "cust_id":     pr.get("customer_id", ""),
        "email":       pr.get("email_address", ""),
        "order_id":    inv.get("order_id", ""),
        "line_items":  [],          # populated later
        "appsheet_client_id": None, # populated later
    }


def get_all_unpaid_invoices():
    """
    Fetch all UNPAID / PARTIALLY_PAID invoices for the location within LOOKBACK_DAYS.
    Returns a flat list of normalized invoice dicts.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(days=LOOKBACK_DAYS)
    cutoff_str = cutoff.strftime("%Y-%m-%dT%H:%M:%SZ")

    invoices = []
    cursor = None

    while True:
        params = {
            "location_id": LOCATION_ID,
            "limit":       200,
        }
        if cursor:
            params["cursor"] = cursor

        data = _square_get("/invoices", params=params)
        for inv in data.get("invoices", []):
            status = inv.get("status", "")
            if status not in ("UNPAID", "PARTIALLY_PAID"):
                continue
            # Date filter
            raw = inv.get("scheduled_at") or inv.get("created_at", "")
            if raw[:10] < cutoff_str[:10]:
                continue
            invoices.append(_normalize_invoice(inv))

        cursor = data.get("cursor")
        if not cursor:
            break

    return invoices


def get_customer(customer_id):
    """Fetch a single Square customer record."""
    data = _square_get(f"/customers/{customer_id}")
    c = data.get("customer", {})
    address = c.get("address", {})
    addr_line = ", ".join(filter(None, [
        address.get("address_line_1", ""),
        address.get("address_line_2", ""),
        address.get("locality", ""),
        address.get("administrative_district_level_1", ""),
        address.get("postal_code", ""),
    ]))
    return {
        "name":    " ".join(filter(None, [c.get("given_name", ""), c.get("family_name", "")])).strip()
                   or c.get("company_name", ""),
        "company": c.get("company_name", ""),
        "email":   c.get("email_address", ""),
        "phone":   c.get("phone_number", ""),
        "address": addr_line,
    }


def get_line_items_for_orders(order_ids):
    """
    Batch-fetch Square orders and return a dict: {order_id: [line_item_dict, ...]}.
    Square allows up to 100 order IDs per batch call.
    """
    result = {}
    if not order_ids:
        return result

    order_ids = [oid for oid in order_ids if oid]
    batch_size = 100

    for i in range(0, len(order_ids), batch_size):
        batch = order_ids[i : i + batch_size]
        data = _square_post("/orders/batch-retrieve", {
            "order_ids": batch,
            "location_id": LOCATION_ID,
        })
        for order in data.get("orders", []):
            oid = order.get("id", "")
            items = []
            for li in order.get("line_items", []):
                name = li.get("name", "")
                qty  = float(li.get("quantity", "1"))
                base = _money_to_float(li.get("base_price_money"))
                total= _money_to_float(li.get("total_money"))
                items.append({
                    "name":       name,
                    "quantity":   qty,
                    "unit_price": base,
                    "total":      total,
                })
            # Also capture service charges (e.g. delivery fee)
            for sc in order.get("service_charges", []):
                items.append({
                    "name":       sc.get("name", "Service Charge"),
                    "quantity":   1,
                    "unit_price": _money_to_float(sc.get("amount_money")),
                    "total":      _money_to_float(sc.get("total_money") or sc.get("amount_money")),
                })
            result[oid] = items

    return result


# ──────────────────────────────────────────────────────────────
# AppSheet helpers
# ──────────────────────────────────────────────────────────────

def _appsheet_find(table):
    """Fetch all records from an AppSheet table. Returns list of row dicts."""
    url = APPSHEET_BASE.format(table=table)
    resp = requests.post(
        url,
        headers={
            "ApplicationAccessKey": APPSHEET_API_KEY,
            "Content-Type": "application/json",
        },
        json={"Action": "Find", "Properties": {}, "Rows": []},
        timeout=60,
    )
    resp.raise_for_status()
    text = resp.text.strip()
    if not text:
        return []
    return json.loads(text)


def get_appsheet_clients():
    """
    Fetch all AppSheet client records.
    Returns dict: {client_id: {name, address, email, phone, square_cust_id}}
    """
    rows = _appsheet_find("client")
    result = {}
    for r in rows:
        client_id = r.get("id", "")
        if not client_id:
            continue
        name = (r.get("account_name") or r.get("_ComputedName") or "").strip()
        result[client_id] = {
            "name":            name,
            "address":         (r.get("address") or "").strip(),
            "email":           (r.get("email_address") or r.get("_email") or "").strip(),
            "phone":           (r.get("phonenumber") or r.get("_phone_number") or "").strip(),
            "square_cust_id":  (r.get("reserve_3") or "").strip(),
            "archived":        (r.get("archive?") or "N").strip().upper() == "Y",
        }
    return result


def get_appsheet_invoice_client_map():
    """
    Fetch AppSheet orders that have invoice_number set.
    Returns dict: {square_invoice_number: appsheet_client_id}

    This is the critical link: Square invoice → AppSheet order → AppSheet client.
    """
    rows = _appsheet_find("order")
    mapping = {}
    for r in rows:
        inv_num = (r.get("invoice_number") or "").strip()
        client_id = (r.get("client") or "").strip()
        if inv_num and client_id:
            # invoice_number in AppSheet matches the Square invoice's invoice_number field
            mapping[inv_num] = client_id
    return mapping
