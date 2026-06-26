"""
dashboard.py — Generates docs/index.html for the HRH Statements Dashboard.

Uses plain string concatenation throughout — NOT f-strings — because the
HTML embeds JavaScript with curly braces that confuse Python's f-string parser.
"""

import json
from datetime import date


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
    today = date.today()
    # Format: "Thursday, 06/26/2026"
    today_str = today.strftime("%A, %m/%d/%Y")

    total_ar  = sum(r["total"] for r in results)
    total_inv = sum(len(r["invoices"]) for r in results)

    ag_0_30   = sum(r["buckets"].get("0_30",   0) for r in results)
    ag_31_60  = sum(r["buckets"].get("31_60",  0) for r in results)
    ag_61_90  = sum(r["buckets"].get("61_90",  0) for r in results)
    ag_over90 = sum(r["buckets"].get("over_90",0) for r in results)

    # Build customer data for JS
    customers_list = []
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
                "date":      date_display,
                "raw_date":  inv.get("date", ""),
                "num":       display_num,
                "email":     inv.get("email", ""),
                "amount":    inv.get("amount", 0),
                "age":       inv.get("age_days", 0),
                "url":       inv.get("url", ""),
                "lineItems": line_items,
            })

        all_nums = [
            (inv.get("id", "").lstrip("0") or inv.get("id", ""))
            for inv in r["invoices"]
        ]

        subject = "HRH Account Statement - " + r["customer_name"]
        body = (
            "Hi,\n\nPlease find your current account statement attached.\n\n"
            "Total Balance Due: " + _fmt(r["total"]) + "\n\n"
            "You can pay individual invoices online via the Pay Here links on your statement.\n\n"
            "Thank you,\nHigh Ridge Hydroponics\n"
            "highridgehydroponics@gmail.com | 203-788-5180"
        )
        import urllib.parse
        gmail_url = (
            "https://mail.google.com/mail/?view=cm"
            "&to=" + urllib.parse.quote(r.get("customer_email", ""))
            + "&su=" + urllib.parse.quote(subject)
            + "&body=" + urllib.parse.quote(body)
        )

        customers_list.append({
            "stmtId":      r["statement_id"],
            "appId":       r.get("appsheet_id") or "",
            "name":        r["customer_name"],
            "email":       r.get("customer_email", ""),
            "total":       r["total"],
            "b0_30":       r["buckets"].get("0_30",   0),
            "b31_60":      r["buckets"].get("31_60",  0),
            "b61_90":      r["buckets"].get("61_90",  0),
            "bOver90":     r["buckets"].get("over_90",0),
            "invoices":    invoices_data,
            "invoiceNums": all_nums,
            "pdfFile":     r.get("pdf_filename") or "",
            "gmailUrl":    gmail_url,
        })

    customers_json = json.dumps(customers_list, ensure_ascii=False, indent=2)

    # GitHub Actions URL — opens the manual trigger page
    gh_actions_url = "https://github.com/highridgehydroponics-ctrl/hrh-statements/actions/workflows/generate.yml"

    html = (
        "<!DOCTYPE html>\n"
        "<html lang='en'>\n"
        "<head>\n"
        "<meta charset='UTF-8'/>\n"
        "<meta name='viewport' content='width=device-width,initial-scale=1'/>\n"
        "<title>HRH Accounts Receivable</title>\n"
        "<style>\n"
        "*{box-sizing:border-box;margin:0;padding:0}\n"
        "body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;background:#f0f4f0;color:#1a1a1a;font-size:14px}\n"
        "header{background:#2d6a4f;color:white;padding:14px 24px;display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px}\n"
        "header h1{font-size:18px;font-weight:600}\n"
        "header .meta{font-size:12px;opacity:.8;margin-top:2px}\n"
        ".header-right{display:flex;align-items:center;gap:14px}\n"
        ".ar-total{font-size:22px;font-weight:700;color:#a7f3d0}\n"
        ".refresh-btn{padding:6px 14px;border-radius:6px;border:1px solid rgba(255,255,255,.4);background:rgba(255,255,255,.15);color:white;cursor:pointer;font-size:12px;font-weight:500;text-decoration:none;display:inline-block;white-space:nowrap}\n"
        ".refresh-btn:hover{background:rgba(255,255,255,.25)}\n"
        ".container{max-width:1200px;margin:0 auto;padding:16px}\n"
        ".cards{display:flex;gap:10px;margin-bottom:16px;flex-wrap:wrap}\n"
        ".card{background:white;border-radius:8px;padding:14px 18px;flex:1;min-width:140px;border:2px solid transparent;cursor:pointer;transition:border-color .15s}\n"
        ".card:hover,.card.active{border-color:#2d6a4f}\n"
        ".card .label{font-size:11px;color:#666;text-transform:uppercase;letter-spacing:.4px;margin-bottom:4px}\n"
        ".card .amount{font-size:20px;font-weight:600;color:#2d6a4f}\n"
        ".card .count{font-size:11px;color:#888;margin-top:2px}\n"
        ".toolbar{background:white;border-radius:8px;padding:10px 14px;display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin-bottom:12px}\n"
        ".toolbar input[type=search]{padding:6px 12px;border:1px solid #ccc;border-radius:6px;font-size:13px;flex:1;min-width:180px}\n"
        ".toolbar input[type=search]:focus{outline:none;border-color:#2d6a4f}\n"
        ".toolbar input[type=date]{padding:5px 8px;border:1px solid #ccc;border-radius:6px;font-size:12px}\n"
        ".toolbar label{font-size:12px;color:#555;display:flex;align-items:center;gap:5px}\n"
        ".btn{padding:6px 13px;border-radius:6px;border:1px solid #ccc;background:white;cursor:pointer;font-size:12px;white-space:nowrap}\n"
        ".btn:hover{background:#f0f4f0}\n"
        ".btn-primary{background:#2d6a4f;color:white;border-color:#2d6a4f}\n"
        ".btn-primary:hover{background:#245940}\n"
        ".tbl-wrap{background:white;border-radius:8px;overflow:hidden}\n"
        ".tbl-header{display:grid;grid-template-columns:80px 1fr 180px 100px 90px 90px 90px 120px;padding:10px 14px;background:#2d6a4f;color:white;font-size:11px;font-weight:600;text-transform:uppercase;letter-spacing:.4px}\n"
        ".cust-row{border-bottom:1px solid #e8ede8}\n"
        ".cust-main{display:grid;grid-template-columns:80px 1fr 180px 100px 90px 90px 90px 120px;padding:10px 14px;cursor:pointer;align-items:center;transition:background .1s}\n"
        ".cust-main:hover{background:#f0f4f0}\n"
        ".cust-main .cname{font-weight:500}\n"
        ".cust-main .appid{font-size:10px;color:#aaa;margin-top:1px}\n"
        ".ra{text-align:right}\n"
        ".ca{text-align:center}\n"
        ".actions{display:flex;gap:4px;justify-content:flex-end}\n"
        ".act-btn{padding:3px 7px;border-radius:4px;border:1px solid #ccc;background:white;cursor:pointer;font-size:11px}\n"
        ".act-btn:hover{background:#f0f4f0}\n"
        ".inv-section{display:none;background:#f8fbf8;border-top:1px solid #e0e8e0;padding:8px 14px 10px 80px}\n"
        ".cust-row.open .inv-section{display:block}\n"
        ".inv-tbl{width:100%;border-collapse:collapse;font-size:12px}\n"
        ".inv-tbl th{padding:5px 8px;text-align:left;background:#e8f0e8;color:#2d6a4f;font-size:11px;font-weight:600}\n"
        ".inv-tbl th.ra{text-align:right}\n"
        ".inv-tbl td{padding:5px 8px;border-bottom:1px solid #eee;color:#333}\n"
        ".inv-tbl td.ra{text-align:right}\n"
        ".inv-tbl tr:last-child td{border-bottom:none}\n"
        ".inv-row{cursor:pointer}\n"
        ".inv-row:hover{background:#f0f5f0}\n"
        ".pay-link{color:#2d6a4f;text-decoration:underline;font-size:11px;white-space:nowrap}\n"
        ".age-90{color:#b91c1c;font-weight:600}\n"
        ".age-60{color:#d97706;font-weight:600}\n"
        ".age-30{color:#15803d}\n"
        ".no-results{text-align:center;padding:40px;color:#888}\n"
        ".copied{color:#2d6a4f!important}\n"
        "</style>\n"
        "</head>\n"
        "<body>\n"

        "<header>\n"
        "  <div>\n"
        "    <h1>HRH Accounts Receivable</h1>\n"
        "    <div class='meta'>" + today_str + " &nbsp;|&nbsp; "
        + str(len(results)) + " customers &nbsp;|&nbsp; "
        + str(total_inv) + " invoices</div>\n"
        "  </div>\n"
        "  <div class='header-right'>\n"
        "    <a class='refresh-btn' href='" + gh_actions_url + "' target='_blank'\n"
        "       title='Opens GitHub Actions — click Run workflow to pull fresh Square data'>\n"
        "      &#x21BB; Refresh Data\n"
        "    </a>\n"
        "    <div class='ar-total'>" + _fmt(total_ar) + " AR</div>\n"
        "  </div>\n"
        "</header>\n"

        "<div class='container'>\n"

        "  <div class='cards'>\n"
        "    <div class='card active' onclick='filterBucket(this,\"all\")'>\n"
        "      <div class='label'>Total AR</div>\n"
        "      <div class='amount'>" + _fmt(total_ar) + "</div>\n"
        "      <div class='count'>" + str(len(results)) + " customers</div>\n"
        "    </div>\n"
        "    <div class='card' onclick='filterBucket(this,\"0_30\")'>\n"
        "      <div class='label'>0–30 Days</div>\n"
        "      <div class='amount'>" + _fmt(ag_0_30) + "</div>\n"
        "    </div>\n"
        "    <div class='card' onclick='filterBucket(this,\"31_60\")'>\n"
        "      <div class='label'>31–60 Days</div>\n"
        "      <div class='amount'>" + _fmt(ag_31_60) + "</div>\n"
        "    </div>\n"
        "    <div class='card' onclick='filterBucket(this,\"61_90\")'>\n"
        "      <div class='label'>61–90 Days</div>\n"
        "      <div class='amount'>" + _fmt(ag_61_90) + "</div>\n"
        "    </div>\n"
        "    <div class='card' onclick='filterBucket(this,\"over_90\")'>\n"
        "      <div class='label'>Over 90 Days</div>\n"
        "      <div class='amount age-90'>" + _fmt(ag_over90) + "</div>\n"
        "    </div>\n"
        "  </div>\n"

        "  <div class='toolbar'>\n"
        "    <input type='search' id='srch' placeholder='Search customer name or email…' oninput='applyFilters()'/>\n"
        "    <label>From <input type='date' id='dfrom' onchange='applyFilters()'/></label>\n"
        "    <label>To <input type='date' id='dto' onchange='applyFilters()'/></label>\n"
        "    <button class='btn' onclick='clearFilters()'>Clear</button>\n"
        "    <button class='btn btn-primary' onclick='draftAll()'>&#9993; Draft All Emails</button>\n"
        "  </div>\n"

        "  <div class='tbl-wrap'>\n"
        "    <div class='tbl-header'>\n"
        "      <div>Stmt #</div><div>Customer</div><div>Email</div>\n"
        "      <div class='ra'>Balance</div>\n"
        "      <div class='ra'>0-30d</div>\n"
        "      <div class='ra'>31-60d</div>\n"
        "      <div class='ra'>61-90d</div>\n"
        "      <div class='ca'>Actions</div>\n"
        "    </div>\n"
        "    <div id='list'></div>\n"
        "    <div id='empty' class='no-results' style='display:none'>No customers match.</div>\n"
        "  </div>\n"
        "</div>\n"

        "<script>\n"
        "const CUSTOMERS = " + customers_json + ";\n"
        "let activeBucket = 'all';\n"
        "let _visibleGmail = [];\n"
        "let _visibleNums  = [];\n"
        "\n"
        "function fmt(n){\n"
        "  return '$'+Number(n).toLocaleString('en-US',{minimumFractionDigits:2,maximumFractionDigits:2});\n"
        "}\n"
        "function ageCls(d){\n"
        "  return d>90?'age-90':d>60?'age-60':d>30?'age-30':'';\n"
        "}\n"
        "function filterBucket(el,b){\n"
        "  activeBucket=b;\n"
        "  document.querySelectorAll('.card').forEach(c=>c.classList.remove('active'));\n"
        "  el.classList.add('active');\n"
        "  applyFilters();\n"
        "}\n"
        "function applyFilters(){\n"
        "  const q=(document.getElementById('srch').value||'').toLowerCase();\n"
        "  const df=document.getElementById('dfrom').value;\n"
        "  const dt=document.getElementById('dto').value;\n"
        "  const BUCKET_KEY={'all':null,'0_30':'b0_30','31_60':'b31_60','61_90':'b61_90','over_90':'bOver90'};\n"
        "  const bk=BUCKET_KEY[activeBucket];\n"
        "  const vis=CUSTOMERS.filter(c=>{\n"
        "    if(bk && (c[bk]||0)<=0) return false;\n"
        "    if(q && !(c.name.toLowerCase().includes(q)||c.email.toLowerCase().includes(q))) return false;\n"
        "    if(df||dt){\n"
        "      if(!c.invoices.some(inv=>(!df||inv.raw_date>=df)&&(!dt||inv.raw_date<=dt))) return false;\n"
        "    }\n"
        "    return true;\n"
        "  });\n"
        "  renderList(vis);\n"
        "}\n"
        "function clearFilters(){\n"
        "  document.getElementById('srch').value='';\n"
        "  document.getElementById('dfrom').value='';\n"
        "  document.getElementById('dto').value='';\n"
        "  activeBucket='all';\n"
        "  document.querySelectorAll('.card').forEach((c,i)=>c.classList.toggle('active',i===0));\n"
        "  renderList(CUSTOMERS);\n"
        "}\n"
        "function draftAll(){\n"
        "  _visibleGmail.forEach(u=>{ if(u) window.open(u,'_blank'); });\n"
        "}\n"
        "function copyNums(ci){\n"
        "  const nums=_visibleNums[ci]||[];\n"
        "  if(!nums.length) return;\n"
        "  navigator.clipboard.writeText(nums.join(', ')).then(()=>{\n"
        "    const btn=document.getElementById('cpbtn-'+ci);\n"
        "    if(btn){btn.textContent='Copied!';btn.classList.add('copied');}\n"
        "    setTimeout(()=>{\n"
        "      if(btn){btn.textContent='Copy #s';btn.classList.remove('copied');}\n"
        "    },2000);\n"
        "  });\n"
        "}\n"
        "function toggleRow(id){\n"
        "  const el=document.getElementById(id);\n"
        "  if(el) el.style.display=el.style.display==='none'?'':'none';\n"
        "}\n"
        "function renderList(list){\n"
        "  _visibleGmail=list.map(c=>c.gmailUrl);\n"
        "  _visibleNums =list.map(c=>c.invoiceNums);\n"
        "  const el=document.getElementById('list');\n"
        "  const em=document.getElementById('empty');\n"
        "  if(!list.length){el.innerHTML='';em.style.display='block';return;}\n"
        "  em.style.display='none';\n"
        "  el.innerHTML=list.map((c,ci)=>{\n"
        "    const appIdLine=c.appId?'<div class=\"appid\">ID: '+c.appId+'</div>':'';\n"
        "    const pdfBtn=c.pdfFile\n"
        "      ?'<button class=\"act-btn\" onclick=\"event.stopPropagation();window.open(\\'pdfs/'+c.pdfFile+'\\',\\'_blank\\')\">&#128196; PDF</button>'\n"
        "      :'';\n"
        "    const cpBtn='<button id=\"cpbtn-'+ci+'\" class=\"act-btn\" onclick=\"event.stopPropagation();copyNums('+ci+')\">Copy #s</button>';\n"
        "    const invRows=c.invoices.map((inv,ii)=>{\n"
        "      const liId='li-'+ci+'-'+ii;\n"
        "      const payCell=inv.url?'<a class=\"pay-link\" href=\"'+inv.url+'\" target=\"_blank\">Pay Here</a>':'—';\n"
        "      const liContent=inv.lineItems&&inv.lineItems.length\n"
        "        ?inv.lineItems.map(li=>\n"
        "            '<tr><td style=\"padding-left:20px;color:#666\">&#8627; '+li.name+'</td>'\n"
        "            +'<td class=\"ra\">'+li.qty+'</td><td class=\"ra\">'+fmt(li.unitPrice)+'</td>'\n"
        "            +'<td class=\"ra\">'+fmt(li.total)+'</td><td></td><td></td></tr>'\n"
        "          ).join('')\n"
        "        :'<tr><td colspan=\"6\" style=\"padding-left:20px;color:#bbb;font-style:italic\">No line item detail</td></tr>';\n"
        "      return '<tr class=\"inv-row\" onclick=\"toggleRow(\\''+liId+'\\')\" style=\"background:white\">'\n"
        "        +'<td>'+inv.date+'</td><td>'+inv.num+'</td>'\n"
        "        +'<td style=\"font-size:11px;color:#666\">'+(inv.email||'—')+'</td>'\n"
        "        +'<td class=\"ra\">'+fmt(inv.amount)+'</td>'\n"
        "        +'<td class=\"ra\"><span class=\"'+ageCls(inv.age)+'\">'+inv.age+'d</span></td>'\n"
        "        +'<td>'+payCell+'</td></tr>'\n"
        "        +'<tr id=\"'+liId+'\" style=\"display:none\"><td colspan=\"6\" style=\"padding:0 8px 6px 8px;background:#f8fbf8\">'\n"
        "        +'<table style=\"width:100%;font-size:11px;border-collapse:collapse\">'\n"
        "        +'<thead><tr style=\"background:#e8f0e8\">'\n"
        "        +'<th style=\"padding:3px 6px\">Item</th>'\n"
        "        +'<th style=\"padding:3px 6px;text-align:right\">Qty</th>'\n"
        "        +'<th style=\"padding:3px 6px;text-align:right\">Unit $</th>'\n"
        "        +'<th style=\"padding:3px 6px;text-align:right\">Total</th>'\n"
        "        +'<th></th><th></th></tr></thead><tbody>'+liContent+'</tbody></table></td></tr>';\n"
        "    }).join('');\n"
        "    const gmailUrl=c.gmailUrl;\n"
        "    return '<div class=\"cust-row\" id=\"cr-'+ci+'\">'\n"
        "      +'<div class=\"cust-main\" onclick=\"document.getElementById(\\'cr-'+ci+'\\').classList.toggle(\\'open\\');\">'\n"
        "      +'<div style=\"font-size:11px;color:#888\">'+c.stmtId+'</div>'\n"
        "      +'<div><div class=\"cname\">'+c.name+'</div>'+appIdLine+'</div>'\n"
        "      +'<div style=\"font-size:12px;color:#555\">'+(c.email||'—')+'</div>'\n"
        "      +'<div class=\"ra\" style=\"font-weight:600\">'+fmt(c.total)+'</div>'\n"
        "      +'<div class=\"ra\">'+(c.b0_30>0?fmt(c.b0_30):'—')+'</div>'\n"
        "      +'<div class=\"ra\">'+(c.b31_60>0?fmt(c.b31_60):'—')+'</div>'\n"
        "      +'<div class=\"ra\">'+(c.b61_90>0?fmt(c.b61_90):'—')+'</div>'\n"
        "      +'<div class=\"actions\">'+pdfBtn+' '+cpBtn+'</div>'\n"
        "      +'</div>'\n"
        "      +'<div class=\"inv-section\">'\n"
        "      +'<div style=\"display:flex;justify-content:space-between;align-items:center;margin-bottom:8px\">'\n"
        "      +'<div style=\"font-size:12px;font-weight:600;color:#2d6a4f\">'+c.invoices.length+' invoice(s)</div>'\n"
        "      +'<div style=\"display:flex;gap:6px\">'\n"
        "      +pdfBtn\n"
        "      +'<button class=\"act-btn btn-primary\" style=\"font-size:11px\" onclick=\"window.open(\\''+gmailUrl+'\\',\\'_blank\\')\">&#9993; Draft Email</button>'\n"
        "      +'</div></div>'\n"
        "      +'<table class=\"inv-tbl\">'\n"
        "      +'<thead><tr><th>Invoice Date</th><th>Invoice #</th><th>Email</th>'\n"
        "      +'<th class=\"ra\">Amount</th><th class=\"ra\">Age</th><th>Pay</th></tr></thead>'\n"
        "      +'<tbody>'+invRows+'</tbody></table>'\n"
        "      +'</div>'\n"
        "      +'</div>';\n"
        "  }).join('');\n"
        "}\n"
        "renderList(CUSTOMERS);\n"
        "</script>\n"
        "</body>\n"
        "</html>\n"
    )

    with open(output_path, "w", encoding="utf-8") as fh:
        fh.write(html)

    print("  Dashboard written to " + output_path)
