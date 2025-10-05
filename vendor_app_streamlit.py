import os
import json
import datetime
import urllib.parse
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

# ------------------------------ CONFIG ------------------------------
st.set_page_config(page_title="Vendors Demand", page_icon="📦", layout="centered")

ss = st.session_state
ss.setdefault("vendor_data", {})
ss.setdefault("current_vendor", None)

# ------------------------------ CSS + JS (safe) ------------------------------
st.markdown("""
<style>
.block-container { max-width: 800px; padding-top: .12rem; }

/* compact title */
h1#vendors-demand-title {
  text-align: center;
  margin: 2px 0 8px 0;
  font-size: 1.45rem;
  font-weight: 800;
}

/* small horizontal buttons */
.btn-row { display:flex; justify-content:center; gap:8px; margin: 4px 0 8px; }
.btn-row button{
  background:#6c5ce7; color:#fff; border:none; border-radius:6px;
  padding:4px 10px; font-size:12.5px; font-weight:700; cursor:pointer;
}
.btn-row button:hover{ background:#5548d9; }
.btn-row button:active{ transform:translateY(1px); }

/* table */
.mobile-table { width:100%; border-collapse:collapse; }
.mobile-table th, .mobile-table td{
  border:1px solid #e5e5e5; text-align:center; padding:6px; font-size:15px;
  word-break:break-word;
}

/* extra small input (~5 digits) */
.mobile-table input{
  width:52px; max-width:52px; font-size:15px; text-align:center;
  border:1px solid #aaa; border-radius:4px; padding:2px; background:#fafafa;
}

/* keep any Streamlit buttons compact (if shown) */
.stButton>button{
  background:#6c5ce7 !important; color:#fff !important; border-radius:8px !important;
  padding:6px 12px !important; font-size:14px !important; font-weight:700 !important;
}
</style>

<script>
// Live subtraction when user types On-Hand
document.addEventListener("input", function(e){
  if(e.target && e.target.classList.contains("onhand-input")){
    var idx = e.target.getAttribute("data-idx");
    var val = parseInt(e.target.value || "0");
    var d1  = parseInt(e.target.getAttribute("data-day1"));
    var d3  = parseInt(e.target.getAttribute("data-day3"));
    var d5  = parseInt(e.target.getAttribute("data-day5"));
    if(isNaN(val)) val = 0;
    document.getElementById("p1-"+idx).innerText = Math.max(0, d1 - val);
    document.getElementById("p3-"+idx).innerText = Math.max(0, d3 - val);
    document.getElementById("p5-"+idx).innerText = Math.max(0, d5 - val);
  }
});
</script>
""", unsafe_allow_html=True)

# ------------------------------ HELPERS ------------------------------
@st.cache_data
def parse_excel(uploaded_file) -> dict:
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
                try: return int(float(v))
                except: return 0
            rows.append([name, num(r.iloc[1]), num(r.iloc[2]), num(r.iloc[3])])
        if rows:
            data[sheet] = rows
    return data

def render_buttons_and_table(df: pd.DataFrame, vendor: str, branch: str):
    """HTML buttons (1D/3D/5D) + table. JS builds WhatsApp text after subtraction."""
    # Build table rows
    rows_html_list = []
    for i, r in df.iterrows():
        rows_html_list.append(
            '<tr>'
            f'<td id="prod-{i}">{r["Product"]}</td>'
            f'<td><input class="onhand-input" type="number" inputmode="numeric" pattern="[0-9]*" '
            f'data-idx="{i}" data-day1="{r["1 Day"]}" data-day3="{r["3 Day"]}" data-day5="{r["5 Day"]}"></td>'
            f'<td id="p1-{i}">{r["1 Day"]}</td>'
            f'<td id="p3-{i}">{r["3 Day"]}</td>'
            f'<td id="p5-{i}">{r["5 Day"]}</td>'
            '</tr>'
        )
    rows_html = "".join(rows_html_list)

    vendor_js = json.dumps(vendor)
    branch_js = json.dumps(branch)

    # Build HTML without f-string braces issues (concatenate strings)
    html = (
        '<div class="btn-row">'
        '<button onclick="sendWA(1)">1D</button>'
        '<button onclick="sendWA(3)">3D</button>'
        '<button onclick="sendWA(5)">5D</button>'
        '</div>'
        '<table class="mobile-table"><tr>'
        '<th>Product</th><th>On Hand</th><th>1 Day</th><th>3 Day</th><th>5 Day</th>'
        '</tr>' + rows_html + '</table>'
        '<script>'
        'var VENDOR = ' + vendor_js + ';'
        'var BRANCH = ' + branch_js + ';'
        'function nowString(){'
        ' var d=new Date();'
        ' function pad(n){ n=("0"+n).slice(-2); return n; }'
        ' return d.getFullYear()+"-"+pad(d.getMonth()+1)+"-"+pad(d.getDate())+" "+'
        '        pad(d.getHours())+":"+pad(d.getMinutes())+":"+pad(d.getSeconds());'
        '}'
        'function buildInvoice(period){'
        ' var pref = (period===1) ? "p1-" : (period===3 ? "p3-" : "p5-");'
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
        '   var qty  = parseInt(qtyC.innerText||"0");'
        '   if(isNaN(qty)) qty=0;'
        '   totalQty += qty;'
        '   totalItems += 1;'
        '   lines.push("- "+name+": "+qty);'
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

    # Height so table shows fully (no inner scroll)
    height = 120 + len(df) * 42
    components.html(html, height=height, scrolling=False)

# ------------------------------ HEADER ------------------------------
st.markdown('<h1 id="vendors-demand-title">Vendors Demand</h1>', unsafe_allow_html=True)

# ------------------------------ UPLOAD ------------------------------
if not ss.vendor_data:
    uploaded = st.file_uploader("📤 Upload Excel File", type=["xlsx", "xls"])
    if uploaded:
        ss.vendor_data = parse_excel(uploaded)
        st.success(f"✅ Loaded {len(ss.vendor_data)} vendors")
else:
    col_ok, col_btn = st.columns([2,1])
    with col_ok:
        st.success(f"✅ Loaded {len(ss.vendor_data)} vendors")
    with col_btn:
        if st.button("📤 Upload Excel File"):
            ss.vendor_data = {}
            st.rerun()

# ------------------------------ MAIN ------------------------------
if ss.vendor_data:
    vendors = list(ss.vendor_data.keys())
    vendor = st.selectbox("🔍 Select Vendor", vendors)
    branch = st.selectbox("🏬 Select Branch",
                          ["Shahbaz","Clifton","Badar","DHA Ecom","BHD Ecom","BHD","Head Office"])

    base_df = pd.DataFrame(ss.vendor_data[vendor], columns=["Product","1 Day","3 Day","5 Day"])
    render_buttons_and_table(base_df, vendor, branch)
