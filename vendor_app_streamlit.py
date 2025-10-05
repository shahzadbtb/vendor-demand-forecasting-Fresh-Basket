import os
import json
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

# -------------------------------------------------
# CONFIG
# -------------------------------------------------
st.set_page_config(page_title="Vendors Demand", page_icon="📦", layout="centered")

ss = st.session_state
ss.setdefault("vendor_data", {})
ss.setdefault("current_vendor", None)
ss.setdefault("current_branch", None)

# -------------------------------------------------
# CSS + JS (mobile-first, safe)
# -------------------------------------------------
st.markdown("""
<style>
/* Layout + compact top */
.block-container { max-width: 800px; padding-top: .10rem; }

/* Small header */
h1#vendors-demand-title{
  text-align:center; margin: 4px 0 4px 0; font-size: 1.38rem; font-weight: 800;
}

/* Small horizontal buttons directly below the header */
.action-row{
  display:flex; justify-content:center; gap:10px; margin: 6px 0 10px 0;
}
.action-row button{
  background:#6c5ce7; color:#fff; border:none; border-radius:999px;
  padding:4px 10px; font-size:12.5px; font-weight:700; cursor:pointer;
}
.action-row button:hover{ background:#5548d9; }
.action-row button:active{ transform:translateY(1px); }

/* Table: product wider, on-hand extra narrow, no inner scroll */
.mobile-table{
  width:100%; border-collapse:collapse; table-layout:fixed; margin-top:4px;
}
.mobile-table th, .mobile-table td{
  border:1px solid #e5e5e5; text-align:center; padding:6px; font-size:15px;
}
.mobile-table colgroup col:nth-child(1){ width:62%; } /* Product (wider) */
.mobile-table colgroup col:nth-child(2){ width:10%; } /* On Hand (extra small) */
.mobile-table colgroup col:nth-child(3){ width:9%; }  /* 1 Day */
.mobile-table colgroup col:nth-child(4){ width:9%; }  /* 3 Day */
.mobile-table colgroup col:nth-child(5){ width:10%; } /* 5 Day */

/* Extra-small On-Hand input (~5 digits) */
.mobile-table input{
  width:46px; max-width:46px; font-size:15px; text-align:center;
  border:1px solid #aaa; border-radius:4px; padding:2px; background:#fafafa;
}
</style>

<script>
// Live projection using per-day avg (data-avg):
// 1D = max(0, avg*1 - onHand), 3D = max(0, avg*3 - onHand), 5D = max(0, avg*5 - onHand)
document.addEventListener("input", function(e){
  if(e.target && e.target.classList.contains("onhand-input")){
    var idx = e.target.getAttribute("data-idx");
    var onh = parseInt(e.target.value || "0"); if(isNaN(onh)) onh = 0;
    var avg = parseFloat(e.target.getAttribute("data-avg") || "0"); if(isNaN(avg)) avg = 0;

    var p1 = Math.max(0, Math.round(avg*1 - onh));
    var p3 = Math.max(0, Math.round(avg*3 - onh));
    var p5 = Math.max(0, Math.round(avg*5 - onh));

    var c1 = document.getElementById("p1-"+idx);
    var c3 = document.getElementById("p3-"+idx);
    var c5 = document.getElementById("p5-"+idx);
    if(c1) c1.innerText = p1;
    if(c3) c3.innerText = p3;
    if(c5) c5.innerText = p5;
  }
});
</script>
""", unsafe_allow_html=True)

# -------------------------------------------------
# HELPERS
# -------------------------------------------------
@st.cache_data
def parse_excel(uploaded_file) -> dict:
    """
    Reads the workbook. Assumes each sheet has:
      Col0: Product, Col1: Month-1 total, Col2: Month-2 total, Col3: Month-3 total
    We'll compute per-day avg = (m1+m2+m3) / 92  (30 + 31 + 31).
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
            def f(v):
                try: return float(v)
                except: return 0.0
            rows.append([name, f(r.iloc[1]), f(r.iloc[2]), f(r.iloc[3])])
        if rows:
            data[sheet] = rows
    return data

def build_component(rows: list, vendor: str, branch: str):
    """
    Renders:
      - tiny horizontal buttons right under title
      - table with live-projected columns based on avg from 3 months
      - buttons generate WhatsApp invoice from current (live) projections, only non-zero items
    """
    # Build HTML rows with data-avg and initial projected values (OnHand defaults to 0)
    # per-day avg from 3 months:
    html_rows = []
    for i, r in enumerate(rows):
        product, m1, m2, m3 = r[0], float(r[1]), float(r[2]), float(r[3])
        avg = (m1 + m2 + m3) / 92.0  # 30 + 31 + 31
        p1 = max(0, round(avg*1))
        p3 = max(0, round(avg*3))
        p5 = max(0, round(avg*5))
        html_rows.append(
            '<tr>'
            f'<td id="prod-{i}">{product}</td>'
            f'<td><input class="onhand-input" type="number" inputmode="numeric" pattern="[0-9]*" '
            f'data-idx="{i}" data-avg="{avg}"></td>'
            f'<td id="p1-{i}">{p1}</td>'
            f'<td id="p3-{i}">{p3}</td>'
            f'<td id="p5-{i}">{p5}</td>'
            '</tr>'
        )
    body = "".join(html_rows)

    vendor_js = json.dumps(vendor or "")
    branch_js = json.dumps(branch or "")

    html = (
        '<div class="action-row">'
        '<button onclick="sendWA(1)">1D</button>'
        '<button onclick="sendWA(3)">3D</button>'
        '<button onclick="sendWA(5)">5D</button>'
        '</div>'
        '<table class="mobile-table">'
        '<colgroup><col><col><col><col><col></colgroup>'
        '<tr><th>Product</th><th>On Hand</th><th>1 Day</th><th>3 Day</th><th>5 Day</th></tr>'
        + body +
        '</table>'
        '<script>'
        'var VENDOR=' + vendor_js + ';'
        'var BRANCH=' + branch_js + ';'
        'function nowString(){var d=new Date();function pad(n){n=("0"+n).slice(-2);return n;}'
        'return d.getFullYear()+"-"+pad(d.getMonth()+1)+"-"+pad(d.getDate())+" "+'
        'pad(d.getHours())+":"+pad(d.getMinutes())+":"+pad(d.getSeconds());}'
        'function buildInvoice(period){'
        ' var pref = (period===1)?"p1-":(period===3)?"p3-":"p5-";'
        ' var table = document.querySelector(".mobile-table");'
        ' var trs = table.querySelectorAll("tr");'
        ' var lines = [];'
        ' lines.push("*Vendor Demand Invoice*");'
        ' lines.push("*Vendor:* "+VENDOR);'
        ' lines.push("*Branch:* "+BRANCH);'
        ' lines.push("*Projection:* "+period+" Day");'
        ' lines.push("*Date:* "+nowString());'
        ' lines.push("");'
        ' lines.push("*ITEMS:*");'
        ' var totalQty=0, totalItems=0;'
        ' for(var i=1;i<trs.length;i++){'  # skip header
        '   var prod = document.getElementById("prod-"+(i-1));'
        '   var qtyC = document.getElementById(pref+(i-1));'
        '   if(!prod || !qtyC) continue;'
        '   var name = (prod.innerText||"").trim();'
        '   var qty  = parseInt(qtyC.innerText||"0"); if(isNaN(qty)) qty = 0;'
        '   if(qty>0){ totalQty += qty; totalItems += 1; lines.push("- "+name+": "+qty); }'
        ' }'
        ' lines.push("");'
        ' lines.push("*TOTAL ITEMS:* "+totalItems);'
        ' lines.push("*TOTAL QTY:* "+totalQty);'
        ' return lines.join("\\n");'
        '}'
        'function sendWA(period){'
        ' var text = buildInvoice(period);'
        ' var url  = "https://api.whatsapp.com/send?text=" + encodeURIComponent(text);'
        ' var a=document.createElement("a"); a.href=url; a.target="_blank"; a.rel="noopener";'
        ' document.body.appendChild(a); a.click(); a.remove();'
        '}'
        '</script>'
    )

    height = 130 + len(rows) * 44  # scale so table shows fully (no inner scroll)
    components.html(html, height=height, scrolling=False)

# -------------------------------------------------
# HEADER (title first, buttons will render inside component just under this)
# -------------------------------------------------
st.markdown('<h1 id="vendors-demand-title">Vendors Demand</h1>', unsafe_allow_html=True)

# -------------------------------------------------
# UPLOAD
# -------------------------------------------------
if not ss.vendor_data:
    uploaded = st.file_uploader("📤 Upload Excel File", type=["xlsx", "xls"])
    if uploaded:
        ss.vendor_data = parse_excel(uploaded)
        st.success(f"✅ Loaded {len(ss.vendor_data)} vendors")
else:
    c1, c2 = st.columns([2,1])
    with c1:
        st.success(f"✅ Loaded {len(ss.vendor_data)} vendors")
    with c2:
        if st.button("📤 Upload Excel File"):
            ss.vendor_data = {}
            st.rerun()

# -------------------------------------------------
# MAIN
# -------------------------------------------------
if ss.vendor_data:
    vendors = list(ss.vendor_data.keys())
    # Use session state so buttons (rendered above) always use the latest selection after rerun
    default_vendor = ss.get("current_vendor") or vendors[0]
    default_branch = ss.get("current_branch") or "Shahbaz"

    # Build component (buttons + table) right under header (using current defaults)
    rows = ss.vendor_data[default_vendor]
    build_component(rows, default_vendor, default_branch)

    # Then show the selectors (when user changes, Streamlit reruns and re-renders above with new values)
    ss.current_vendor = st.selectbox("🔍 Select Vendor", vendors, index=vendors.index(default_vendor), key="current_vendor")
    ss.current_branch = st.selectbox("🏬 Select Branch",
                                     ["Shahbaz","Clifton","Badar","DHA Ecom","BHD Ecom","BHD","Head Office"],
                                     index=["Shahbaz","Clifton","Badar","DHA Ecom","BHD Ecom","BHD","Head Office"].index(default_branch),
                                     key="current_branch")
