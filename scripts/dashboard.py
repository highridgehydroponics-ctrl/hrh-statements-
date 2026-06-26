"""
dashboard.py — generates the static HTML aging dashboard for GitHub Pages.
Clicking a customer row expands to invoices.
Clicking an invoice row expands to show line items (qty, unit price, total).
"""

import json
from datetime import date
from urllib.parse import quote

HRH_PHONE = "203-788-5180"
HRH_EMAIL = "highridgehydroponics@gmail.com"


def _gmail_url(r: dict, month_year: str) -> str:
    if not r.get("email"):
        return ""
    subj = quote(f"{month_year} Account Statement — {r['company_name'] or r['name']}")
    body = quote(
        f"Hello {r['name']},\n\n"
        f"Please find attached your account statement for {month_year}.\n"
        f"Total balance due: ${r['total']:,.2f}\n\n"
        f"You can pay individual invoices via the Pay Here links in the attached PDF.\n\n"
        f"Let me know if you have any questions.\n\n"
        f"Regards,\nJoe Alvarez\nHigh Ridge Hydroponics LLC\n{HRH_PHONE}"
    )
    return f"https://mail.google.com/mail/?view=cm&to={quote(r['email'])}&su={subj}&body={body}"


def generate_dashboard(results: list[dict], output_path: str) -> None:
    today      = date.today()
    month_year = today.strftime("%B %Y")
    gen_date   = today.strftime("%m/%d/%Y")
    today_iso  = today.strftime("%Y-%m-%d")
    all_dates  = [inv["date"] for r in results for inv in r["invoices"]]
    min_date   = min(all_dates) if all_dates else today_iso

    grand_total = sum(r["total"]   for r in results)
    grand_b0    = sum(r["b0_30"]   for r in results)
    grand_b1    = sum(r["b31_60"]  for r in results)
    grand_b2    = sum(r["b61_90"]  for r in results)
    grand_b3    = sum(r["b90plus"] for r in results)
    total_inv   = sum(r["invoice_count"] for r in results)

    for r in results:
        r["gmail_url"] = _gmail_url(r, month_year)

    data_json = json.dumps(results)

    html = (
        '<!DOCTYPE html>\n<html lang="en">\n<head>\n'
        '<meta charset="UTF-8">\n'
        '<meta name="viewport" content="width=device-width,initial-scale=1">\n'
        f'<title>HRH Statements {month_year}</title>\n'
        '<style>\n'
        '*{box-sizing:border-box;margin:0;padding:0}\n'
        'body{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;background:#f0f4f8;color:#1a1a1a;padding:2rem}\n'
        'h1{font-size:1.35rem;color:#1565C0;margin-bottom:.2rem}\n'
        '.sub{font-size:.85rem;color:#666;margin-bottom:1.25rem}\n'
        '.summary-bar{display:flex;gap:1rem;margin-bottom:1.25rem;flex-wrap:wrap}\n'
        '.scard{background:#fff;border-radius:10px;padding:.85rem 1.1rem;flex:1;min-width:130px;box-shadow:0 1px 4px rgba(0,0,0,.08);cursor:pointer;border:2px solid transparent;transition:border-color .15s,transform .1s;user-select:none}\n'
        '.scard:hover{transform:translateY(-1px)}\n'
        '.scard.active{border-color:#1565C0}\n'
        '.scard .lbl{font-size:.72rem;color:#888;font-weight:600;text-transform:uppercase;letter-spacing:.04em}\n'
        '.scard .val{font-size:1.25rem;font-weight:700;color:#1565C0;margin-top:.2rem}\n'
        '.scard .hint{font-size:.68rem;color:#bbb;margin-top:.25rem}\n'
        '.controls{display:flex;align-items:center;gap:.75rem;margin-bottom:1rem;flex-wrap:wrap;background:#fff;border-radius:10px;padding:.85rem 1rem;box-shadow:0 1px 4px rgba(0,0,0,.08)}\n'
        '.controls label{font-size:.82rem;color:#555;font-weight:600}\n'
        '.controls input{padding:.3rem .5rem;border:1px solid #ccc;border-radius:5px;font-size:.82rem;color:#333}\n'
        '.controls input[type=text]{min-width:200px}\n'
        '.sep{width:1px;height:1.5rem;background:#ddd}\n'
        '.btn{display:inline-flex;align-items:center;gap:.3rem;padding:.38rem .85rem;border-radius:6px;font-size:.8rem;font-weight:600;border:none;cursor:pointer;text-decoration:none;white-space:nowrap;transition:opacity .15s}\n'
        '.btn:hover{opacity:.82}\n'
        '.btn-blue{background:#1565C0;color:#fff}\n'
        '.btn-green{background:#2e7d32;color:#fff}\n'
        '.btn-pdf{background:#E3F2FD;color:#1565C0}\n'
        '.btn-draft{background:#E8F5E9;color:#2e7d32}\n'
        '.btn-drafted{background:#c8e6c9;color:#1b5e20}\n'
        '.btn-pay{background:#fff3e0;color:#e65100;font-size:.75rem}\n'
        '.btn-copy{background:#f3e5f5;color:#6a1b9a;font-size:.75rem}\n'
        '.btn-copied{background:#e1bee7;color:#4a148c;font-size:.75rem}\n'
        '.card{background:#fff;border-radius:12px;box-shadow:0 2px 8px rgba(0,0,0,.08);overflow:hidden;margin-top:.5rem}\n'
        'table{width:100%;border-collapse:collapse}\n'
        'thead tr{background:#1565C0;color:#fff}\n'
        'th{padding:.68rem .8rem;font-size:.74rem;font-weight:600;letter-spacing:.04em;text-transform:uppercase;white-space:nowrap}\n'
        'th.r{text-align:right}\n'
        'tbody tr.customer-row{border-bottom:1px solid #e8eef4;transition:background .1s;cursor:pointer}\n'
        'tbody tr.customer-row:hover{background:#f0f7ff}\n'
        'tbody tr.customer-row.expanded{background:#e8f0fe;border-bottom:none}\n'
        'td{padding:.6rem .8rem;font-size:.86rem;vertical-align:middle}\n'
        '.amt{text-align:right;font-weight:700;color:#1565C0}\n'
        '.aamt{text-align:right;color:#333}\n'
        '.azero{text-align:right;color:#ccc}\n'
        '.awarn{text-align:right;color:#b71c1c;font-weight:600}\n'
        '.actions{display:flex;gap:.4rem;flex-wrap:wrap}\n'
        '.chevron{display:inline-block;transition:transform .2s;margin-right:.4rem;color:#1565C0;font-size:.8rem}\n'
        '.expanded .chevron{transform:rotate(90deg)}\n'
        'tr.detail-row{display:none;background:#f7faff}\n'
        'tr.detail-row.open{display:table-row}\n'
        'tr.detail-row>td{padding:.5rem 1rem 1rem 2.5rem;border-bottom:2px solid #BBDEFB}\n'
        '.inv-table{width:100%;border-collapse:collapse;font-size:.82rem;margin-top:.5rem}\n'
        '.inv-table th{background:#BBDEFB;color:#1565C0;padding:.4rem .6rem;text-align:left;font-size:.72rem;text-transform:uppercase;letter-spacing:.04em}\n'
        '.inv-table th.r{text-align:right}\n'
        '.inv-table td{padding:.4rem .6rem;border-bottom:1px solid #e3f2fd;color:#333}\n'
        '.inv-table td.r{text-align:right}\n'
        '.inv-table tr.inv-row{cursor:pointer;transition:background .1s}\n'
        '.inv-table tr.inv-row:hover{background:#e8f0fe}\n'
        '.inv-table tr.inv-row.inv-expanded{background:#dceeff}\n'
        '.inv-table tr.inv-total td{font-weight:700;background:#E3F2FD;color:#1565C0;border-bottom:none}\n'
        '.li-row{display:none;background:#eef5ff}\n'
        '.li-row.open{display:table-row}\n'
        '.li-row td{padding:.3rem .6rem .3rem 2rem;border-bottom:1px solid #dce8fb}\n'
        '.li-table{width:100%;border-collapse:collapse;font-size:.78rem}\n'
        '.li-table th{background:#dce8fb;color:#1565C0;padding:.3rem .5rem;text-align:left;font-size:.68rem;text-transform:uppercase}\n'
        '.li-table th.r{text-align:right}\n'
        '.li-table td{padding:.3rem .5rem;border-bottom:1px solid #eaf1fc;color:#444}\n'
        '.li-table td.r{text-align:right}\n'
        '.li-table tr:last-child td{border-bottom:none}\n'
        'tfoot tr{background:#E3F2FD}\n'
        'tfoot td{font-weight:700;font-size:.88rem;border-top:2px solid #1565C0}\n'
        '.updated{font-size:.72rem;color:#999;margin-top:1.5rem;text-align:right}\n'
        '</style>\n</head>\n<body>\n'
        f'<h1>HRH Account Statements &mdash; {month_year}</h1>\n'
        f'<div class="sub">Generated {gen_date} &bull; {len(results)} customers &bull; {total_inv} outstanding invoices &bull; Click a row to expand</div>\n\n'
        '<div class="summary-bar">\n'
        '  <div class="scard active" id="card-all" onclick="toggleBucket(\'all\')">\n'
        f'    <div class="lbl">Total AR</div><div class="val">${grand_total:,.0f}</div><div class="hint">showing all</div></div>\n'
        '  <div class="scard" id="card-b0" onclick="toggleBucket(\'b0\')">\n'
        f'    <div class="lbl">0&ndash;30 Days</div><div class="val" style="color:#2e7d32">${grand_b0:,.0f}</div><div class="hint">click to filter</div></div>\n'
        '  <div class="scard" id="card-b1" onclick="toggleBucket(\'b1\')">\n'
        f'    <div class="lbl">31&ndash;60 Days</div><div class="val" style="color:#f57f17">${grand_b1:,.0f}</div><div class="hint">click to filter</div></div>\n'
        '  <div class="scard" id="card-b2" onclick="toggleBucket(\'b2\')">\n'
        f'    <div class="lbl">61&ndash;90 Days</div><div class="val" style="color:#e65100">${grand_b2:,.0f}</div><div class="hint">click to filter</div></div>\n'
        '  <div class="scard" id="card-b3" onclick="toggleBucket(\'b3\')">\n'
        f'    <div class="lbl">90+ Days</div><div class="val" style="color:#b71c1c">${grand_b3:,.0f}</div><div class="hint">click to filter</div></div>\n'
        '</div>\n\n'
        '<div class="controls">\n'
        '  <label>Customer:</label>\n'
        '  <input type="text" id="cust-filter" placeholder="Search name or company..." oninput="applyFilter()">\n'
        '  <div class="sep"></div>\n'
        '  <label>From:</label>\n'
        f'  <input type="date" id="date-from" value="{min_date}">\n'
        '  <label>To:</label>\n'
        f'  <input type="date" id="date-to" value="{today_iso}">\n'
        '  <button class="btn btn-blue" onclick="applyFilter()">&#x21bb; Filter</button>\n'
        '  <div class="sep"></div>\n'
        '  <button class="btn btn-green" onclick="draftAll()">&#x2709; Draft All Emails</button>\n'
        '</div>\n\n'
        '<div class="card"><table>\n'
        '<thead><tr>\n'
        '  <th>#</th><th>Company</th><th>Contact</th><th class="r">Invoices</th>\n'
        '  <th class="r">0-30d</th><th class="r">31-60d</th><th class="r">61-90d</th><th class="r">90+d</th>\n'
        '  <th class="r">Total Due</th><th>Actions</th>\n'
        '</tr></thead>\n'
        '<tbody id="tbl-body"></tbody>\n'
        '<tfoot><tr>\n'
        '  <td colspan="3">TOTALS (visible)</td>\n'
        '  <td class="amt" id="ft-inv"></td>\n'
        '  <td class="amt" id="ft-b0"></td><td class="amt" id="ft-b1"></td>\n'
        '  <td class="amt" id="ft-b2"></td><td class="amt" id="ft-b3"></td>\n'
        '  <td class="amt" id="ft-total"></td><td></td>\n'
        '</tr></tfoot>\n'
        '</table></div>\n'
        f'<div class="updated">Data last refreshed: {gen_date} &mdash; auto-updates daily at 7am ET</div>\n\n'
        '<script>\n'
        f'const DATA = {data_json};\n'
        "const fmt = v => '$' + v.toFixed(2).replace(/\\B(?=(\\d{3})+(?!\\d))/g, ',');\n"
        "const fmtDate = d => d ? d.slice(5,7)+'/'+d.slice(8,10)+'/'+d.slice(0,4) : '';\n"
        "const stripZ = s => s ? (s.replace(/^0+/,'') || s) : s;\n"
        'function copyNums(btn,nums){\n'
        '  navigator.clipboard.writeText(nums).then(()=>{\n'
        '    btn.textContent="✓ Copied!";btn.className="btn btn-copied";\n'
        '    setTimeout(()=>{btn.textContent="📋 Copy #s";btn.className="btn btn-copy";},2000);\n'
        '  });\n'
        '}\n'
        'const drafted = {};\n'
        'let activeBucket = null;\n'
        'const BUCKET_FIELD = {b0:"b0_30",b1:"b31_60",b2:"b61_90",b3:"b90plus"};\n\n'
        'function toggleBucket(key){\n'
        '  ["all","b0","b1","b2","b3"].forEach(k=>document.getElementById("card-"+k).className="scard");\n'
        '  if(key==="all"||key===activeBucket){activeBucket=null;document.getElementById("card-all").classList.add("active");}\n'
        '  else{activeBucket=key;document.getElementById("card-"+key).classList.add("active");}\n'
        '  applyFilter();\n'
        '}\n\n'
        'function amtCell(v){\n'
        '  if(v===0)return\'<td class="azero">-</td>\';\n'
        '  if(v>500)return\'<td class="awarn">\'+fmt(v)+\'</td>\';\n'
        '  return\'<td class="aamt">\'+fmt(v)+\'</td>\';\n'
        '}\n\n'
        'function toggleCust(idx){\n'
        '  const cr=document.getElementById("crow-"+idx);\n'
        '  const dr=document.getElementById("drow-"+idx);\n'
        '  const open=dr.classList.contains("open");\n'
        '  cr.classList.toggle("expanded",!open);\n'
        '  dr.classList.toggle("open",!open);\n'
        '}\n\n'
        'function toggleInv(custIdx,invIdx){\n'
        '  const ir=document.getElementById("irow-"+custIdx+"-"+invIdx);\n'
        '  const lr=document.getElementById("lirow-"+custIdx+"-"+invIdx);\n'
        '  if(!lr)return;\n'
        '  const open=lr.classList.contains("open");\n'
        '  ir.classList.toggle("inv-expanded",!open);\n'
        '  lr.classList.toggle("open",!open);\n'
        '}\n\n'
        'function buildLineItems(items){\n'
        '  if(!items||!items.length)return\'<em style="color:#aaa;font-size:.78rem">No line item detail available</em>\';\n'
        '  let rows="";\n'
        '  items.forEach(li=>{\n'
        '    rows+=\'<tr><td>\'+li.name+\'</td><td class="r">\'+li.quantity+\'</td><td class="r">\'+fmt(li.unit_price)+\'</td><td class="r">\'+fmt(li.total)+\'</td></tr>\';\n'
        '  });\n'
        '  return \'<table class="li-table"><thead><tr><th>Item</th><th class="r">Qty</th><th class="r">Unit Price</th><th class="r">Total</th></tr></thead><tbody>\'+rows+\'</tbody></table>\';\n'
        '}\n\n'
        'function buildInvTable(invoices,custIdx){\n'
        '  const today=new Date();today.setHours(0,0,0,0);\n'
        '  let rows="",total=0;\n'
        '  invoices.forEach((inv,invIdx)=>{\n'
        '    total+=inv.amount;\n'
        '    const age=Math.floor((today-new Date(inv.date+"T00:00:00"))/86400000);\n'
        '    const ageCls=age<=30?"color:#2e7d32":age<=60?"color:#f57f17":age<=90?"color:#e65100":"color:#b71c1c;font-weight:700";\n'
        '    const payBtn=inv.url?\'<a class="btn btn-pay" href="\'+inv.url+\'" target="_blank" onclick="event.stopPropagation()">Pay Here</a>\':\'-\';\n'
        '    const hasLi=inv.line_items&&inv.line_items.length;\n'
        '    const liHint=hasLi?\'<span style="font-size:.68rem;color:#999;margin-left:.3rem">(click for items)</span>\':\'\' ;\n'
        '    rows+=\'<tr class="inv-row" id="irow-\'+custIdx+\'-\'+invIdx+\'" onclick="toggleInv(\'+custIdx+\',\'+invIdx+\')">\';\n'
        '    rows+=\'<td><span class="chevron" style="font-size:.65rem">&#9654;</span>\'+fmtDate(inv.date)+liHint+\'</td>\';\n'
        '    rows+=\'<td>\'+stripZ(inv.id)+\'</td><td>\'+( inv.email||\'—\')+\'</td><td class="r">\'+fmt(inv.amount)+\'</td>\';\n'
        '    rows+=\'<td class="r"><span style="\'+ageCls+\'">\'+age+\' days</span></td><td>\'+payBtn+\'</td></tr>\';\n'
        '    rows+=\'<tr class="li-row" id="lirow-\'+custIdx+\'-\'+invIdx+\'"><td colspan="6">\'+buildLineItems(inv.line_items)+\'</td></tr>\';\n'
        '  });\n'
        '  rows+=\'<tr class="inv-total"><td colspan="3">Total</td><td class="r">\'+fmt(total)+\'</td><td></td><td></td></tr>\';\n'
        '  return \'<table class="inv-table"><thead><tr><th>Invoice Date</th><th>Invoice #</th><th>Email</th><th class="r">Amount</th><th class="r">Age</th><th>Pay</th></tr></thead><tbody>\'+rows+\'</tbody></table>\';\n'
        '}\n\n'
        'function renderTable(rows){\n'
        '  let html="",tInv=0,tB0=0,tB1=0,tB2=0,tB3=0,tTot=0;\n'
        '  rows.forEach((r,idx)=>{\n'
        '    tInv+=r.invoice_count;tB0+=r.b0_30;tB1+=r.b31_60;tB2+=r.b61_90;tB3+=r.b90plus;tTot+=r.total;\n'
        '    const pdfBtn=r.pdf_url?\'<a class="btn btn-pdf" href="\'+r.pdf_url+\'" target="_blank" onclick="event.stopPropagation()">&#x1F4C4; PDF</a>\':\'\';\n'
        '    const draftBtn=r.gmail_url?(drafted[r.cust_id]?\'<button class="btn btn-drafted" onclick="event.stopPropagation()">&#x2713; Drafted</button>\':\'<button class="btn btn-draft" onclick="event.stopPropagation();openDraft(this,\'+JSON.stringify(r.gmail_url)+\',\'+JSON.stringify(r.cust_id)+\')">&#x2709; Draft Email</button>\'):\'\';\n'
        '    const invNums=r.invoices.map(i=>stripZ(i.id)).join(\', \');\n'
        '    const copyBtn=\'<button class="btn btn-copy" onclick="event.stopPropagation();copyNums(this,\'+JSON.stringify(invNums)+\')">&#x1F4CB; Copy #s</button>\';\n'
        '    html+=\'<tr class="customer-row" id="crow-\'+idx+\'" onclick="toggleCust(\'+idx+\')">\';\n'
        '    html+=\'<td><span class="chevron">&#9654;</span>\'+r.stmt_no+\'</td>\';\n'
        '    html+=\'<td><b>\'+r.company_name+\'</b></td><td>\'+r.name+\'</td><td class="aamt">\'+r.invoice_count+\'</td>\';\n'
        '    html+=amtCell(r.b0_30)+amtCell(r.b31_60)+amtCell(r.b61_90)+amtCell(r.b90plus);\n'
        '    html+=\'<td class="amt">\'+fmt(r.total)+\'</td><td><div class="actions">\'+pdfBtn+draftBtn+copyBtn+\'</div></td></tr>\';\n'
        '    html+=\'<tr class="detail-row" id="drow-\'+idx+\'"><td colspan="10">\'+buildInvTable(r.invoices,idx)+\'</td></tr>\';\n'
        '  });\n'
        '  document.getElementById("tbl-body").innerHTML=html;\n'
        '  document.getElementById("ft-inv").textContent=tInv;\n'
        '  document.getElementById("ft-b0").textContent=fmt(tB0);\n'
        '  document.getElementById("ft-b1").textContent=fmt(tB1);\n'
        '  document.getElementById("ft-b2").textContent=fmt(tB2);\n'
        '  document.getElementById("ft-b3").textContent=fmt(tB3);\n'
        '  document.getElementById("ft-total").textContent=fmt(tTot);\n'
        '}\n\n'
        'function applyFilter(){\n'
        '  const from=document.getElementById("date-from").value;\n'
        '  const to=document.getElementById("date-to").value;\n'
        '  const q=document.getElementById("cust-filter").value.toLowerCase();\n'
        '  const today=new Date();today.setHours(0,0,0,0);\n'
        '  let rows=DATA.map(r=>{\n'
        '    const invs=r.invoices.filter(i=>(!from||i.date>=from)&&(!to||i.date<=to));\n'
        '    if(!invs.length)return null;\n'
        '    let b0=0,b1=0,b2=0,b3=0;\n'
        '    invs.forEach(i=>{const age=Math.floor((today-new Date(i.date+"T00:00:00"))/86400000);\n'
        '      if(age<=30)b0+=i.amount;else if(age<=60)b1+=i.amount;else if(age<=90)b2+=i.amount;else b3+=i.amount;});\n'
        '    return Object.assign({},r,{invoices:invs,invoice_count:invs.length,total:invs.reduce((s,i)=>s+i.amount,0),b0_30:b0,b31_60:b1,b61_90:b2,b90plus:b3});\n'
        '  }).filter(Boolean);\n'
        '  if(activeBucket){const f=BUCKET_FIELD[activeBucket];rows=rows.filter(r=>r[f]>0);}\n'
        '  if(q)rows=rows.filter(r=>r.name.toLowerCase().includes(q)||r.company_name.toLowerCase().includes(q));\n'
        '  renderTable(rows);\n'
        '}\n\n'
        'function openDraft(btn,url,cid){\n'
        '  if(!confirm("Open Gmail compose for "+btn.closest("tr").querySelector("b").textContent+"?"))return;\n'
        '  window.open(url,"_blank");drafted[cid]=true;\n'
        '  btn.textContent="Drafted";btn.className="btn btn-drafted";btn.onclick=null;\n'
        '}\n'
        'function draftAll(){const btns=Array.from(document.querySelectorAll("#tbl-body .btn-draft"));'
        'if(!btns.length){alert("No email buttons available.");return;}'
        'if(!confirm("Open "+btns.length+" Gmail compose window(s)?"))return;btns.forEach(b=>b.click());}\n'
        'applyFilter();\n'
        '</script>\n</body>\n</html>\n'
    )

    import os
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w") as f:
        f.write(html)
    print(f"Dashboard → {output_path}")
