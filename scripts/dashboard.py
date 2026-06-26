"""
dashboard.py — Generates docs/index.html for the HRH Statements Dashboard.

Uses plain string concatenation throughout — NOT f-strings — because the
HTML embeds JavaScript with curly braces that confuse Python's f-string parser.
"""

import json
from datetime import date


def _j(val):
    """Serialize value to a JSON literal safe for embedding in HTML."""
    return json.dumps(val, ensure_ascii=False)


def _fmt(amount):
    try:
        return "${:,.2f}".format(float(amount))
    except Exception:
        return "$0.00"


def generate_dashboard(results, output_path):
    """
    Write the HTML dashboard to output_path.

    results: list of customer dicts from generate.py, each containing:
      statement_id, customer_name, customer_email, customer_phone,
      customer_address, appsheet_id, total, buckets, invoices, pdf_filename
    """
    today_str = date.today().strftime("%B %d, %Y")
    total_ar = sum(r["total"] for r in results)
    total_inv = sum(len(r["invoices"]) for r in results)

    # Aging totals across all customers
    ag_0_30  = sum(r["buckets"].get("0_30", 0)   for r in results)
    ag_31_60 = sum(r["buckets"].get("31_60", 0)  for r in results)
    ag_61_90 = sum(r["buckets"].get("61_90", 0)  for r in results)
    ag_over90= sum(r["buckets"].get("over_90", 0) for r in results)

    # Build customer rows data for JS
    customers_json_rows = []
    for r in results:
        invoices_data = []
        for inv in r["invoices"]:
            raw_num = inv.get("id", "")
            display_num = raw_num.lstrip("0") or raw_num
            try:
                d = date.fromisoformat(inv["date"])
                date_display = d.strftime("%m/%d/%Y")
            except Exception:
                date_display = inv.get("date", "")

            line_items = []
            for li in inv.get("line_items", []):
                line_items.append({
                    "name":      li.get("name", ""),
                    "qty":       li.get("quantity", 1),
                    "unitPrice": li.get("unit_price", 0),
                    "total":     li.get("total", 0),
                })

            invoices_data.append({
                "date":       date_display,
                "raw_date":   inv.get("date", ""),
                "num":        display_num,
                "email":      inv.get("email", ""),
                "amount":     inv.get("amount", 0),
                "age":        inv.get("age_days", 0),
                "url":        inv.get("url", ""),
                "status":     inv.get("status", ""),
                "lineItems":  line_items,
            })

        # Collect all invoice numbers for "Copy #s"
        all_nums = [
            (inv.get("id", "").lstrip("0") or inv.get("id", ""))
            for inv in r["invoices"]
        ]

        # Gmail compose body
        subject = "HRH Account Statement - " + r["customer_name"]
        body = (
            "Hi,\n\nPlease find your current account statement attached.\n\n"
            "Total Balance Due: " + _fmt(r["total"]) + "\n\n"
            "You can pay individual invoices online via the Pay Here links on your statement.\n\n"
            "Thank you,\nHigh Ridge Hydroponics\n"
            + "highridgehydroponics@gmail.com | 203-788-5180"
        )
        gmail_url = (
            "https://mail.google.com/mail/?view=cm"
            "&to=" + r.get("customer_email", "")
            + "&su=" + subject.replace(" ", "%20")
            + "&body=" + body.replace(" ", "%20").replace("\n", "%0A")
        )

        customers_json_rows.append({
            "stmtId":    r["statement_id"],
            "appId":     r.get("appsheet_id") or "",
            "name":      r["customer_name"],
            "email":     r.get("customer_email", ""),
            "phone":     r.get("customer_phone", ""),
            "address":   r.get("customer_address", ""),
            "total":     r["total"],
            "b0_30":     r["buckets"].get("0_30", 0),
            "b31_60":    r["buckets"].get("31_60", 0),
            "b61_90":    r["buckets"].get("61_90", 0),
            "bOver90":   r["buckets"].get("over_90", 0),
            "invoices":  invoices_data,
            "invoiceNums": all_nums,
            "pdfFile":   r.get("pdf_filename") or "",
            "gmailUrl":  gmail_url,
        })

    customers_json = json.dumps(customers_json_rows, ensure_ascii=False, indent=2)

    html = (
        "<!DOCTYPE html>\n"
        "<html lang='en'>\n"
        "<head>\n"
        "<meta charset='UTF-8'/>\n"
        "<meta name='viewport' content='width=device-width, initial-scale=1'/>\n"
        "<title>HRH Accounts Receivable Dashboard</title>\n"
        "<style>\n"
        "  * { box-sizing: border-box; margin: 0; padding: 0; }\n"
        "  body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;\n"
        "         background: #f0f4f0; color: #1a1a1a; font-size: 14px; }\n"
        "  header { background: #2d6a4f; color: white; padding: 16px 24px;\n"
        "           display: flex; justify-content: space-between; align-items: center; }\n"
        "  header h1 { font-size: 18px; font-weight: 600; }\n"
        "  header .meta { font-size: 12px; opacity: .8; }\n"
        "  .container { max-width: 1200px; margin: 0 auto; padding: 16px; }\n"
        "  /* Aging cards */\n"
        "  .cards { display: flex; gap: 10px; margin-bottom: 16px; flex-wrap: wrap; }\n"
        "  .card { background: white; border-radius: 8px; padding: 14px 18px;\n"
        "          flex: 1; min-width: 150px; border: 2px solid transparent;\n"
        "          cursor: pointer; transition: border-color .15s; }\n"
        "  .card:hover, .card.active { border-color: #2d6a4f; }\n"
        "  .card .label { font-size: 11px; color: #666; text-transform: uppercase;\n"
        "                 letter-spacing: .4px; margin-bottom: 4px; }\n"
        "  .card .amount { font-size: 20px; font-weight: 600; color: #2d6a4f; }\n"
        "  .card .count  { font-size: 11px; color: #888; margin-top: 2px; }\n"
        "  /* Toolbar */\n"
        "  .toolbar { background: white; border-radius: 8px; padding: 12px 16px;\n"
        "             display: flex; gap: 10px; align-items: center;\n"
        "             flex-wrap: wrap; margin-bottom: 12px; }\n"
        "  .toolbar input { padding: 7px 12px; border: 1px solid #ccc;\n"
        "                   border-radius: 6px; font-size: 13px; flex: 1;\n"
        "                   min-width: 180px; }\n"
        "  .toolbar input:focus { outline: none; border-color: #2d6a4f; }\n"
        "  .toolbar label { font-size: 12px; color: #555; }\n"
        "  .toolbar .date-group { display: flex; gap: 6px; align-items: center; }\n"
        "  .btn { padding: 7px 14px; border-radius: 6px; border: 1px solid #ccc;\n"
        "         background: white; cursor: pointer; font-size: 12px;\n"
        "         white-space: nowrap; }\n"
        "  .btn:hover { background: #f0f4f0; }\n"
        "  .btn-primary { background: #2d6a4f; color: white; border-color: #2d6a4f; }\n"
        "  .btn-primary:hover { background: #245940; }\n"
        "  /* Table */\n"
        "  .tbl-wrap { background: white; border-radius: 8px; overflow: hidden; }\n"
        "  .tbl-header { display: grid;\n"
        "    grid-template-columns: 80px 1fr 160px 90px 90px 90px 90px 100px;\n"
        "    gap: 0; padding: 10px 14px;\n"
        "    background: #2d6a4f; color: white; font-size: 11px;\n"
        "    font-weight: 600; text-transform: uppercase; letter-spacing: .4px; }\n"
        "  .cust-row { border-bottom: 1px solid #e8ede8; }\n"
        "  .cust-main { display: grid;\n"
        "    grid-template-columns: 80px 1fr 160px 90px 90px 90px 90px 100px;\n"
        "    gap: 0; padding: 10px 14px; cursor: pointer;\n"
        "    align-items: center; transition: background .1s; }\n"
        "  .cust-main:hover { background: #f0f4f0; }\n"
        "  .cust-main .name { font-weight: 500; }\n"
        "  .cust-main .email { font-size: 12px; color: #666; }\n"
        "  .ra { text-align: right; }\n"
        "  .ca { text-align: center; }\n"
        "  .actions { display: flex; gap: 5px; justify-content: flex-end; }\n"
        "  .act-btn { padding: 3px 8px; border-radius: 4px; border: 1px solid #ccc;\n"
        "             background: white; cursor: pointer; font-size: 11px; }\n"
        "  .act-btn:hover { background: #f0f4f0; }\n"
        "  /* Invoice sub-table */\n"
        "  .inv-section { display: none; background: #f8fbf8;\n"
        "                 border-top: 1px solid #e0e8e0; padding: 8px 14px 10px 80px; }\n"
        "  .cust-row.open .inv-section { display: block; }\n"
        "  .inv-tbl { width: 100%; border-collapse: collapse; font-size: 12px; }\n"
        "  .inv-tbl th { padding: 5px 8px; text-align: left;\n"
        "                background: #e8f0e8; color: #2d6a4f;\n"
        "                font-size: 11px; font-weight: 600; }\n"
        "  .inv-tbl th.ra { text-align: right; }\n"
        "  .inv-tbl td { padding: 5px 8px; border-bottom: 1px solid #eee; color: #333; }\n"
        "  .inv-tbl td.ra { text-align: right; }\n"
        "  .inv-tbl tr:last-child td { border-bottom: none; }\n"
        "  .inv-tbl tr.inv-row { cursor: pointer; }\n"
        "  .inv-tbl tr.inv-row:hover { background: #f0f5f0; }\n"
        "  .pay-link { color: #2d6a4f; text-decoration: underline;\n"
        "              font-size: 11px; white-space: nowrap; }\n"
        "  /* Line items sub-sub-table */\n"
        "  .li-section { display: none; }\n"
        "  .li-section.open { display: table-row; }\n"
        "  .li-tbl { width: 100%; border-collapse: collapse;\n"
        "            font-size: 11px; margin: 2px 0 4px 16px; }\n"
        "  .li-tbl td { padding: 3px 6px; color: #555; }\n"
        "  .li-tbl td.ra { text-align: right; }\n"
        "  .no-results { text-align: center; padding: 40px; color: #888; }\n"
        "  .badge-90 { color: #b91c1c; font-weight: 600; }\n"
        "  .badge-60 { color: #d97706; font-weight: 600; }\n"
        "  .badge-30 { color: #15803d; }\n"
        "  .appid { font-size: 10px; color: #aaa; margin-top: 1px; }\n"
        "  .copied { color: #2d6a4f !important; }\n"
        "</style>\n"
        "</head>\n"
        "<body>\n"
        "<header>\n"
        "  <div>\n"
        "    <h1>HRH Accounts Receivable</h1>\n"
        "    <div class='meta'>Updated " + today_str + " &nbsp;|&nbsp; "
        + str(len(results)) + " customers &nbsp;|&nbsp; "
        + str(total_inv) + " invoices</div>\n"
        "  </div>\n"
        "  <div style='font-size:22px;font-weight:700;color:#a7f3d0'>"
        + _fmt(total_ar) + " AR</div>\n"
        "</header>\n"
        "<div class='container'>\n"

        # Aging cards
        "  <div class='cards'>\n"
        "    <div class='card active' data-bucket='all' onclick='filterBucket(this,\"all\")'>\n"
        "      <div class='label'>Total AR</div>\n"
        "      <div class='amount'>" + _fmt(total_ar) + "</div>\n"
        "      <div class='count'>" + str(len(results)) + " customers</div>\n"
        "    </div>\n"
        "    <div class='card' data-bucket='0_30' onclick='filterBucket(this,\"0_30\")'>\n"
        "      <div class='label'>0–30 Days</div>\n"
        "      <div class='amount'>" + _fmt(ag_0_30) + "</div>\n"
        "    </div>\n"
        "    <div class='card' data-bucket='31_60' onclick='filterBucket(this,\"31_60\")'>\n"
        "      <div class='label'>31–60 Days</div>\n"
        "      <div class='amount'>" + _fmt(ag_31_60) + "</div>\n"
        "    </div>\n"
        "    <div class='card' data-bucket='61_90' onclick='filterBucket(this,\"61_90\")'>\n"
        "      <div class='label'>61–90 Days</div>\n"
        "      <div class='amount'>" + _fmt(ag_61_90) + "</div>\n"
        "    </div>\n"
        "    <div class='card' data-bucket='over_90' onclick='filterBucket(this,\"over_90\")'>\n"
        "      <div class='label'>Over 90 Days</div>\n"
        "      <div class='amount badge-90'>" + _fmt(ag_over90) + "</div>\n"
        "    </div>\n"
        "  </div>\n"

        # Toolbar
        "  <div class='toolbar'>\n"
        "    <input type='search' id='search' placeholder='Search customer name or email…'\n"
        "           oninput='applyFilters()'/>\n"
        "    <div class='date-group'>\n"
        "      <label>From <input type='date' id='dateFrom' onchange='applyFilters()'/></label>\n"
        "      <label>To <input type='date' id='dateTo' onchange='applyFilters()'/></label>\n"
        "    </div>\n"
        "    <button class='btn' onclick='clearFilters()'>Clear</button>\n"
        "    <button class='btn btn-primary' onclick='draftAllEmails()'>✉ Draft All Emails</button>\n"
        "  </div>\n"

        # Table
        "  <div class='tbl-wrap'>\n"
        "    <div class='tbl-header'>\n"
        "      <div>Stmt #</div><div>Customer</div><div>Email</div>\n"
        "      <div class='ra'>Balance</div>\n"
        "      <div class='ra'>0-30d</div>\n"
        "      <div class='ra'>31-60d</div>\n"
        "      <div class='ra'>61-90d</div>\n"
        "      <div class='ca'>Actions</div>\n"
        "    </div>\n"
        "    <div id='cust-list'></div>\n"
        "    <div id='no-results' class='no-results' style='display:none'>No customers match.</div>\n"
        "  </div>\n"

        "</div>\n"  # end container

        "<script>\n"
        "const CUSTOMERS = " + customers_json + ";\n"
        "\n"
        "let activeBucket = 'all';\n"
        "\n"
        "function fmt(n) {\n"
        "  return '$' + Number(n).toLocaleString('en-US',{minimumFractionDigits:2,maximumFractionDigits:2});\n"
        "}\n"
        "\n"
        "function ageClass(days) {\n"
        "  if (days > 90) return 'badge-90';\n"
        "  if (days > 60) return 'badge-60';\n"
        "  if (days > 30) return 'badge-30';\n"
        "  return '';\n"
        "}\n"
        "\n"
        "function filterBucket(el, bucket) {\n"
        "  activeBucket = bucket;\n"
        "  document.querySelectorAll('.card').forEach(c => c.classList.remove('active'));\n"
        "  el.classList.add('active');\n"
        "  applyFilters();\n"
        "}\n"
        "\n"
        "function applyFilters() {\n"
        "  const q = document.getElementById('search').value.toLowerCase();\n"
        "  const dfrom = document.getElementById('dateFrom').value;\n"
        "  const dto   = document.getElementById('dateTo').value;\n"
        "\n"
        "  let visible = CUSTOMERS.filter(c => {\n"
        "    // Bucket filter\n"
        "    if (activeBucket !== 'all') {\n"
        "      const bmap = {0_30:'b0_30','31_60':'b31_60','61_90':'b61_90','over_90':'bOver90'};\n"
        "      if ((c[bmap[activeBucket]] || 0) <= 0) return false;\n"
        "    }\n"
        "    // Text search\n"
        "    if (q && !(c.name.toLowerCase().includes(q) || c.email.toLowerCase().includes(q))) return false;\n"
        "    // Date range: at least one invoice within range\n"
        "    if (dfrom || dto) {\n"
        "      const anyMatch = c.invoices.some(inv => {\n"
        "        if (dfrom && inv.raw_date < dfrom) return false;\n"
        "        if (dto   && inv.raw_date > dto)   return false;\n"
        "        return true;\n"
        "      });\n"
        "      if (!anyMatch) return false;\n"
        "    }\n"
        "    return true;\n"
        "  });\n"
        "\n"
        "  renderList(visible);\n"
        "}\n"
        "\n"
        "function clearFilters() {\n"
        "  document.getElementById('search').value = '';\n"
        "  document.getElementById('dateFrom').value = '';\n"
        "  document.getElementById('dateTo').value = '';\n"
        "  activeBucket = 'all';\n"
        "  document.querySelectorAll('.card').forEach((c,i) => c.classList.toggle('active', i===0));\n"
        "  renderList(CUSTOMERS);\n"
        "}\n"
        "\n"
        "function renderList(list) {\n"
        "  const el = document.getElementById('cust-list');\n"
        "  const noRes = document.getElementById('no-results');\n"
        "  if (!list.length) {\n"
        "    el.innerHTML = '';\n"
        "    noRes.style.display = 'block';\n"
        "    return;\n"
        "  }\n"
        "  noRes.style.display = 'none';\n"
        "  el.innerHTML = list.map((c, ci) => {\n"
        "    const appIdBadge = c.appId ? '<div class=\"appid\">ID: ' + c.appId + '</div>' : '';\n"
        "    const pdfBtn = c.pdfFile\n"
        "      ? '<button class=\"act-btn\" onclick=\"event.stopPropagation();window.open(\\'pdfs/' + c.pdfFile + '\\',\\'_blank\\')\" title=\"Open PDF\">&#128196; PDF</button>'\n"
        "      : '';\n"
        "    const emailBtn = '<button class=\"act-btn\" onclick=\"event.stopPropagation();window.open(c' + ci + 'gmail,\\'_blank\\')\" title=\"Draft Email\">&#9993; Draft Email</button>';\n"
        "    const copyBtn  = '<button class=\"act-btn\" id=\"cpbtn-' + ci + '\" onclick=\"event.stopPropagation();copyNums(' + ci + ')\" title=\"Copy invoice numbers\">&#128203; Copy #s</button>';\n"
        "    return (\n"
        "      '<div class=\"cust-row\" id=\"cr-' + ci + '\">'\n"
        "      + '<div class=\"cust-main\" onclick=\"toggleCust(' + ci + ')\">'\n"
        "      + '<div style=\"font-size:11px;color:#888\">' + c.stmtId + '</div>'\n"
        "      + '<div><div class=\"name\">' + c.name + '</div>'\n"
        "      +    appIdBadge\n"
        "      + '</div>'\n"
        "      + '<div style=\"font-size:12px;color:#555\">' + (c.email || '—') + '</div>'\n"
        "      + '<div class=\"ra\" style=\"font-weight:600\">' + fmt(c.total) + '</div>'\n"
        "      + '<div class=\"ra\">' + (c.b0_30   > 0 ? fmt(c.b0_30)   : '—') + '</div>'\n"
        "      + '<div class=\"ra\">' + (c.b31_60  > 0 ? fmt(c.b31_60)  : '—') + '</div>'\n"
        "      + '<div class=\"ra\">' + (c.b61_90  > 0 ? fmt(c.b61_90)  : '—') + '</div>'\n"
        "      + '<div class=\"actions\">' + pdfBtn + ' ' + copyBtn + '</div>'\n"
        "      + '</div>'\n"
        "      + '<div class=\"inv-section\">'\n"
        "      + '<div style=\"display:flex;justify-content:space-between;align-items:center;margin-bottom:6px\">'\n"
        "      + '<div style=\"font-size:12px;font-weight:600;color:#2d6a4f\">' + c.invoices.length + ' invoice(s)</div>'\n"
        "      + '<div style=\"display:flex;gap:6px\">'\n"
        "      + pdfBtn + ' '\n"
        "      + '<button class=\"act-btn btn-primary\" style=\"font-size:11px\" onclick=\"window.open(' + JSON.stringify(c.gmailUrl) + ',\\'_blank\\')\">&#9993; Draft Email</button>'\n"
        "      + '</div></div>'\n"
        "      + '<table class=\"inv-tbl\">'\n"
        "      + '<thead><tr>'\n"
        "      + '<th>Invoice Date</th><th>Invoice #</th><th>Email</th>'\n"
        "      + '<th class=\"ra\">Amount</th><th class=\"ra\">Age</th><th>Pay</th>'\n"
        "      + '</tr></thead><tbody>'\n"
        "      + c.invoices.map((inv, ii) => {\n"
        "          const ageCls = ageClass(inv.age);\n"
        "          const payCell = inv.url\n"
        "            ? '<a class=\"pay-link\" href=\"' + inv.url + '\" target=\"_blank\">Pay Here</a>'\n"
        "            : '—';\n"
        "          const hasLI = inv.lineItems && inv.lineItems.length > 0;\n"
        "          const liRows = hasLI\n"
        "            ? inv.lineItems.map(li =>\n"
        "                '<tr><td style=\"padding-left:16px;color:#555\">↳ ' + li.name + '</td>'\n"
        "                + '<td class=\"ra\">' + li.qty + '</td>'\n"
        "                + '<td class=\"ra\">' + fmt(li.unitPrice) + '</td>'\n"
        "                + '<td class=\"ra\">' + fmt(li.total) + '</td>'\n"
        "                + '<td></td><td></td>'\n"
        "                + '</tr>'\n"
        "              ).join('')\n"
        "            : '<tr><td colspan=\"6\" style=\"padding-left:16px;color:#aaa;font-style:italic\">No line item detail</td></tr>';\n"
        "          const liId = 'li-' + ci + '-' + ii;\n"
        "          return (\n"
        "            '<tr class=\"inv-row\" onclick=\"toggleLI(\\'' + liId + '\\')\" style=\"background:white\">'\n"
        "            + '<td>' + inv.date + '</td>'\n"
        "            + '<td>' + inv.num + '</td>'\n"
        "            + '<td style=\"font-size:11px;color:#666\">' + (inv.email || '—') + '</td>'\n"
        "            + '<td class=\"ra\">' + fmt(inv.amount) + '</td>'\n"
        "            + '<td class=\"ra\"><span class=\"' + ageCls + '\">' + inv.age + 'd</span></td>'\n"
        "            + '<td>' + payCell + '</td>'\n"
        "            + '</tr>'\n"
        "            + '<tr id=\"' + liId + '\" style=\"display:none\">'\n"
        "            + '<td colspan=\"6\" style=\"padding:0 8px 6px 8px;background:#f8fbf8\">'\n"
        "            + '<table style=\"width:100%;font-size:11px;border-collapse:collapse\">'\n"
        "            + '<thead><tr style=\"background:#e8f0e8\">'\n"
        "            + '<th style=\"padding:3px 6px;text-align:left\">Item</th>'\n"
        "            + '<th style=\"padding:3px 6px;text-align:right\">Qty</th>'\n"
        "            + '<th style=\"padding:3px 6px;text-align:right\">Unit Price</th>'\n"
        "            + '<th style=\"padding:3px 6px;text-align:right\">Total</th>'\n"
        "            + '<th></th><th></th></tr></thead><tbody>'\n"
        "            + liRows\n"
        "            + '</tbody></table></td></tr>'\n"
        "          );\n"
        "        }).join('')\n"
        "      + '</tbody></table>'\n"
        "      + '</div>'\n"
        "      + '</div>'\n"
        "    );\n"
        "  }).join('');\n"
        "\n"
        "  // Bind gmail URLs after render (avoids string-escaping issues)\n"
        "  list.forEach((c, ci) => {\n"
        "    window['c' + ci + 'gmail'] = c.gmailUrl;\n"
        "  });\n"
        "}\n"
        "\n"
        "function toggleCust(ci) {\n"
        "  const row = document.getElementById('cr-' + ci);\n"
        "  if (row) row.classList.toggle('open');\n"
        "}\n"
        "\n"
        "function toggleLI(id) {\n"
        "  const row = document.getElementById(id);\n"
        "  if (row) row.style.display = (row.style.display === 'none' ? '' : 'none');\n"
        "}\n"
        "\n"
        "function copyNums(ci) {\n"
        "  const list = document.getElementById('cust-list');\n"
        "  // Find the customer in the rendered list by its rendered position\n"
        "  const rows = list.querySelectorAll('.cust-row');\n"
        "  // ci is index in rendered list, get invoice nums from CUSTOMERS via data attr\n"
        "  // We use a closure captured from renderList\n"
        "  const btn = document.getElementById('cpbtn-' + ci);\n"
        "  // The customer object — read from global captured index\n"
        "  const nums = window['cnums' + ci] || [];\n"
        "  if (!nums.length) return;\n"
        "  navigator.clipboard.writeText(nums.join(', ')).then(() => {\n"
        "    if (btn) { btn.textContent = '✓ Copied'; btn.classList.add('copied'); }\n"
        "    setTimeout(() => {\n"
        "      if (btn) { btn.textContent = '\\u{1F4CB} Copy #s'; btn.classList.remove('copied'); }\n"
        "    }, 2000);\n"
        "  });\n"
        "}\n"
        "\n"
        "function draftAllEmails() {\n"
        "  const list = document.getElementById('cust-list');\n"
        "  const rows = list.querySelectorAll('.cust-row');\n"
        "  // Open Gmail compose for every visible customer with an email\n"
        "  rows.forEach((row, ci) => {\n"
        "    const url = window['c' + ci + 'gmail'];\n"
        "    if (url) window.open(url, '_blank');\n"
        "  });\n"
        "}\n"
        "\n"
        "// Initial render\n"
        "renderList(CUSTOMERS);\n"
        "\n"
        "// Bind copy-nums arrays after render\n"
        "CUSTOMERS.forEach((c, ci) => {\n"
        "  window['cnums' + ci] = c.invoiceNums;\n"
        "});\n"
        "</script>\n"
        "</body>\n"
        "</html>\n"
    )

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"  Dashboard written to {output_path}")
