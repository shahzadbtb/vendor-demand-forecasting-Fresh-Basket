import os
import json
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

# ------------------------------ CONFIG ------------------------------
st.set_page_config(page_title="Vendors Demand", page_icon="📦", layout="centered")

ss = st.session_state
ss.setdefault("vendor_data", {})
ss.setdefault("current_vendor", None)
ss.setdefault("current_branch", "Shahbaz")

# ------------------------------ CSS + JS ------------------------------
st.markdown("""
<style>
.block-container{ max-width:800px; padding-top:.10rem; }

/* compact title */
h1#vendors-demand-title{
  text-align:center; margin:4px 0 6px 0; font-size:1.36rem; font-weight:800;
}

/* projection buttons directly under the title */
.action-row{
  display:flex; justify-content:center; gap:10px; margin: 6px 0 10px;
}
.action-row button{
  background:#6c5ce7; color:#fff; border:none; border-radius:999px;
  padding:4px 10px; font-size:12.5px; font-weight:700; cursor:pointer;
}
.action-row button:hover{ background:#5548d9; }
.action-row button:active{ transform:translateY(1px); }

/* table: product wider, on-hand ultra narrow */
.mobile-table{ width:100%; border-collapse:collapse; table-layout:fixed; margin-top:4px; }
.mobile-table th,.mobile-table td{ border:1px solid #e5e5e5; text-align:center; padding:6px; font-size:15px; }
.mobile-table colgroup col:nth-child(1){ width:67%; } /* Product (wider) */
.mobile-table colgroup col:nth-child(2){ width:8%; }  /* On Hand (very small) */
.mobile-table colgroup col:nth-child(3){ width:8.5%; }/* 1 Day */
.mobile-table colgroup col:nth-child(4){ width:8.5%; }/* 3 Day */
.mobile-table colgroup col:nth-child(5){ width:8%; }  /* 5 Day */

/* On-Hand input ≈ 5 digits */
.mobile-table input{
  width:40px; max-width:40px; font-size:15px; text-align:center;
  border:1px solid #aaa; border-radius:4px; padding:2px; background:#fafafa;
}
</style>

<script>
// --- live subtraction & robust mobile events ---
function liveUpdate(e){
  if(!e || !e.target) return;
  if(!e.target.classList.contains("onhand-input")) return;
  var idx = e.target.getAttribute("data-idx");
  var x   = parseInt(e.target.value || "0"); if(isNaN(x)) x = 0;

  var b1  = parseInt(e.target.getAttribute("data-day1") || "0"); if(isNaN(b1)) b1 = 0;
  var b3  = parseInt(e.target.getAttribute("data-day3") || "0"); if(isNaN(b3)) b3 = 0;
  var b5  = parseInt(e.target.getAttribute("data-day5") || "0"); if(isNaN(b5)) b5 = 0;

  var p1  = Math.max(0, b1 - x);
  var p3  = Math.max(0, b3 - x);
  var p5  = Math.max(0, b5 - x);

  var c1 = document.getElementById("p1-"+idx);
  var c3 = document.getElementById("p3-"+idx);
  var c5 = document.getElementById("p5-"+idx);
  if(c1) c1.textContent = p1;
  if(c3) c3.textContent = p3;
  if(c5) c5.textContent = p5;
}

document.addEventListener("input",  liveUpdate, true);
document.addEventListener("keyup",  liveUpdate, true);
document.addEventListener("change", liveUpdate, true);
</script>
""", unsafe_allow_html=True)

# ------------------------------ HELPERS ------------------------------
@st.cache_data
def parse_excel(uploaded_file) -> dict:
    """
    Expect each sheet: A=Product, B=1 Day, C=3 Day, D=5 Day (integers).
    """
    x = pd.ExcelFile(uploaded_file)
    data = {}
    for sheet in x.sheet_names:
        raw = pd.read_excel(uploaded_file, sheet_name=sheet, header=None).iloc[:, :4]
        rows = []
        for _, r in raw.iterrows():
            name = "" if pd.isna(r.iloc[0]) else str(r.iloc[0]).strip()
            if not name:
                continue
            def num(v):
                try: return int(round(float(v)))
                except: return 0
            rows.append([name, num(r.iloc[1]), num(r.iloc[2]), num(r.iloc[3])])
        if rows:
            data[sheet] = rows
    return data

def component_table(rows, vendor: str, branch: str):
    """
    SINGLE component on the page:
     - tiny 1D/3D/5D buttons right under the title
     - table using B/C/D as base values
     - On-Hand live subtracts from all three columns
     - Button -> builds invoice (non-zero only) from the CURRENT displayed values and opens WhatsApp
    """
    trs = []
    for i, (prod, d1, d3, d5) in enumerate(rows):
        trs.append(
            '<tr>'
            f'<td id="prod-{i}">{prod}</td>'
            f'<td><input class="onhand-input" type="number" inputmode="numeric" pattern="[0-9]*" '
            f'data-idx="{i}" data-day1="{d1}" data-day3="{d3}" data-day5="{d5}"></td>'
            f'<td id="p1-{i}">{d1}</td>'
            f'<td id="p3-{i}">{d3}</td>'
            f'<td id="p5-{i}">{d5}</td>'
            '</tr>'
        )
    body = "".join(trs)

    vendor_js = json.dumps(vendor or "")
    branch_js = json.dumps(branch or "")

    html = (
        # buttons under header
        '<div class="action-row">'
        '<button onclick="sendWA(1)">1D</button>'
        '<button onclick="sendWA(3)">3D</button>'
        '<button onclick="sendWA(5)">5D</button>'
        '</div>'

        # table
        '<table class="mobile-table">'
        '<colgroup><col><col><col><col><col></colgroup>'
        '<tr><th>Product</th><th>On Hand</th><th>1 Day</th><th>3 Day</th><th>5 Day</th></tr>'
        + body +
        '</table>'

        # invoice / WA
        '<script>'
        'var VENDOR=' + vendor_js + ';'
        'var BRANCH=' + branch_js + ';'
        'function nowString(){var d=new Date();function pad(n){n=("0"+n).slice(-2);return n;}'
        'return d.getFullYear()+"-"+pad(d.getMonth()+1)+"-"+pad(d.getDate())+" "+'
        'pad(d.getHours())+":"+pad(d.getMinutes())+":"+pad(d.getSeconds());}'
        'function buildInvoice(period){'
        ' var pref=(period===1)?"p1-":(period===3)?"p3-":"p5-";'
        ' var trs=document.querySelectorAll(".mobile-table tr");'
        ' var lines=[];'
        ' lines.push("*Vendor Demand Invoice*");'
        ' lines.push("*Vendor:* "+VENDOR);'
        ' lines.push("*Branch:* "+BRANCH);'
        ' lines.push("*Projection:* "+period+" Day");'
        ' lines.push("*Date:* "+nowString());'
        ' lines.push("");'
        ' lines.push("*ITEMS:*");'
        ' var totalQty=0,totalItems=0;'
        ' for(var i=1;i<trs.length;i++){'  # skip header row
        '   var prod=document.getElementById("prod-"+(i-1));'
        '   var qtyC=document.getElementById(pref+(i-1));'
        '   if(!prod||!qtyC) continue;'
        '   var name=(prod.textContent||"").trim();'
        '   var qty=parseInt(qtyC.textContent||"0"); if(isNaN(qty)) qty=0;'
        '   if(qty>0){ totalQty+=qty; totalItems+=1; lines.push("- "+name+": "+qty); }'
        ' }'
        ' lines.push("");'
        ' lines.push("*TOTAL ITEMS:* "+totalItems);'
        ' lines.push("*TOTAL QTY:* "+totalQty);'
        ' return lines.join("\\n");'
        '}'
        'function sendWA(period){'
        ' var text=buildInvoice(period);'
        ' var url="https://api.whatsapp.com/send?text="+encodeURIComponent(text);'
        ' var a=document.createElement("a"); a.href=url; a.target="_blank"; a.rel="noopener";'
        ' document.body.appendChild(a); a.click(); a.remove();'
        '}'
        '</script>'
    )

    # height so whole table shows (no inner scroll)
    height = 130 + len(rows) * 44
    components.html(html, height=height, scrolling=False)

# ------------------------------ UI ------------------------------
st.markdown('<h1 id="vendors-demand-title">Vendors Demand</h1>', unsafe_allow_html=True)

# 1) UPLOAD (first time)
if not ss.vendor_data:
    uploaded = st.file_uploader("📤 Upload Excel File", type=["xlsx", "xls"])
    if uploaded:
        ss.vendor_data = parse_excel(uploaded)
        ss.current_vendor = list(ss.vendor_data.keys())[0]
        st.rerun()

# 2) WHEN DATA EXISTS — render ONE component directly under header (no duplicates)
if ss.vendor_data:
    if ss.current_vendor is None or ss.current_vendor not in ss.vendor_data:
        ss.current_vendor = list(ss.vendor_data.keys())[0]
    rows = ss.vendor_data[ss.current_vendor]
    component_table(rows, ss.current_vendor, ss.current_branch)

# 3) Controls BELOW the table (changing them triggers rerun and the single component above re-renders)
if ss.vendor_data:
    c1, c2, c3 = st.columns([2,2,1])
    with c1:
        st.success(f"✅ Loaded {len(ss.vendor_data)} vendors")
    with c2:
        vendors = list(ss.vendor_data.keys())
        new_vendor = st.selectbox("🔍 Select Vendor", vendors, index=vendors.index(ss.current_vendor))
        if new_vendor != ss.current_vendor:
            ss.current_vendor = new_vendor
            st.rerun()
    with c3:
        if st.button("📤 Upload Excel File"):
            ss.vendor_data = {}
            ss.current_vendor = None
            st.rerun()

    new_branch = st.selectbox(
        "🏬 Select Branch",
        ["Shahbaz","Clifton","Badar","DHA Ecom","BHD Ecom","BHD","Head Office"],
        index=["Shahbaz","Clifton","Badar","DHA Ecom","BHD Ecom","BHD","Head Office"].index(ss.current_branch)
    )
    if new_branch != ss.current_branch:
        ss.current_branch = new_branch
        st.rerun()
