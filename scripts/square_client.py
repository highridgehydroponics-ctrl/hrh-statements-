"""
square_client.py — Square REST API calls.
Reads SQUARE_ACCESS_TOKEN and SQUARE_LOCATION_ID from environment variables.
"""

import os
import requests
from datetime import date, timedelta

SQUARE_BASE_URL     = "https://connect.squareup.com/v2"
SQUARE_ACCESS_TOKEN = os.environ["SQUARE_ACCESS_TOKEN"]
SQUARE_LOCATION_ID  = os.environ.get("SQUARE_LOCATION_ID", "BYZ5P0549Z01F")
LOOKBACK_DAYS       = int(os.environ.get("LOOKBACK_DAYS", "365"))


def _headers() -> dict:
    return {
        "Authorization":  f"Bearer {SQUARE_ACCESS_TOKEN}",
        "Content-Type":   "application/json",
        "Square-Version": "2025-01-23",
    }


def _get(path: str, params: dict = None) -> dict:
    r = requests.get(f"{SQUARE_BASE_URL}{path}", headers=_headers(), params=params)
    r.raise_for_status()
    return r.json()


def _post(path: str, body: dict) -> dict:
    r = requests.post(f"{SQUARE_BASE_URL}{path}", headers=_headers(), json=body)
    r.raise_for_status()
    return r.json()


def _normalize_invoice(inv: dict) -> dict | None:
    cutoff = (date.today() - timedelta(days=LOOKBACK_DAYS)).isoformat()
    status = inv.get("status", "")
    if status not in ("UNPAID", "PARTIALLY_PAID"):
        return None
    created = inv.get("created_at", "")[:10]
    if created < cutoff:
        return None
    payment = inv.get("payment_requests", [{}])[0]
    total   = payment.get("computed_amount_money",        {}).get("amount", 0) / 100
    paid    = payment.get("total_completed_amount_money", {}).get("amount", 0) / 100
    amount  = round(total - paid, 2)
    if amount <= 0:
        return None
    recipient = inv.get("primary_recipient", {})
    cust_id   = recipient.get("customer_id")
    email     = recipient.get("email_address", "")
    return {
        "invoice_id": inv["id"],
        "id":         inv.get("invoice_number", ""),
        "date":       created,
        "amount":     amount,
        "url":        inv.get("public_url", ""),
        "status":     status,
        "cust_id":    cust_id,
        "email":      email,
        "order_id":   inv.get("order_id", ""),
        "line_items": [],
    }


def get_customer(customer_id: str) -> dict:
    raw  = _get(f"/customers/{customer_id}")["customer"]
    addr = raw.get("address", {})
    city  = addr.get("locality", "")
    state = addr.get("administrative_district_level_1", "")
    zip_  = addr.get("postal_code", "")
    return {
        "cust_id":        raw["id"],
        "name":           f"{raw.get('given_name', '')} {raw.get('family_name', '')}".strip(),
        "company_name":   raw.get("company_name", "").strip(),
        "email":          raw.get("email_address", ""),
        "phone":          raw.get("phone_number", ""),
        "street":         addr.get("address_line_1", "").strip(),
        "city_state_zip": f"{city}, {state} {zip_}".strip(", "),
    }


def get_all_unpaid_invoices() -> dict[str, list[dict]]:
    """
    Page through ALL location invoices.
    Returns { customer_id: [normalized invoice, ...] }.
    """
    cutoff      = (date.today() - timedelta(days=LOOKBACK_DAYS)).isoformat()
    params      = {"location_id": SQUARE_LOCATION_ID, "limit": 200}
    by_customer: dict[str, list] = {}
    seen: set[str] = set()

    while True:
        data = _get("/invoices", params)
        oldest_on_page = None

        for inv in data.get("invoices", []):
            created = inv.get("created_at", "")[:10]
            if oldest_on_page is None or created < oldest_on_page:
                oldest_on_page = created
            if inv["id"] in seen:
                continue
            seen.add(inv["id"])
            normalized = _normalize_invoice(inv)
            if normalized and normalized["cust_id"]:
                by_customer.setdefault(normalized["cust_id"], []).append(normalized)

        cursor = data.get("cursor")
        if not cursor or (oldest_on_page and oldest_on_page < cutoff):
            break
        params["cursor"] = cursor

    for cid in by_customer:
        by_customer[cid].sort(key=lambda x: x["date"])

    return by_customer


def get_line_items_for_orders(order_ids: list[str]) -> dict[str, list[dict]]:
    """Batch-fetch Square orders and return their line items. Chunks at 100."""
    result = {}
    for i in range(0, len(order_ids), 100):
        chunk = order_ids[i:i + 100]
        data  = _post("/orders/batch-retrieve", {"order_ids": chunk})
        for order in data.get("orders", []):
            oid   = order.get("id", "")
            items = []
            for li in order.get("line_items", []):
                items.append({
                    "name":       li.get("name", "Microgreens"),
                    "quantity":   li.get("quantity", "1"),
                    "unit_price": li.get("base_price_money", {}).get("amount", 0) / 100,
                    "total":      li.get("total_money", {}).get("amount", 0) / 100,
                })
            result[oid] = items
    return result
