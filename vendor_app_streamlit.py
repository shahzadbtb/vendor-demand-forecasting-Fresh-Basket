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

# ------------------------------ CSS + JS ------------------------------
st.markdown("""
<style>
/* Page width & compact top spacing */
.block-container { max-width: 800px; padding-top: .10rem; }

/* Compact title */
h1#vendors-demand-title{
  text-align:center;
  margin: 4px 0 8px 0;
  font-size: 1.42rem;
  font-weight: 800;
}

/* Small horizontal buttons just below the title */
.action-row{ display:flex; justify-content:center; gap:8px; margin: 6px 0 10px; }
.action-row button{
  background:#6c5ce7; color:#fff; border:none; border-radius:999px;
  padding:4px 10px; font-size:12.5px; font-weight:700; cursor:pointer;
}
.action-row button:hover{ background:#5548d9; }
.action-row button:active{ transform:translateY(1px); }

/* Table look */
.mobile-table{ width:100%; border-collapse:collapse; table-layout:fixed; }
.mobile-table th, .mobile-table td{
  border:1px solid #e5e5e5; text-align:center; padding:6px; font-size:15px;
}

/* Column sizing (Product wider, On Hand very narrow) */
.mobile-table colgroup col:nth-child(1){ width:56%; } /* Product */
.mobile-table colgroup col:nth-child(2){ width:12%; } /* On Hand */
.mobile-table colgroup col:nth-child(3){ width:10%; } /* 1 Day */
.mobile-table colgroup col:nth-child(4){ width:10%; } /* 3 Day */
.mobile-table colgroup col:nth-child(5){ width:12%; } /* 5 Day */

/* Extra-small On-Hand input (~5 digits) */
.mobile-table input{
  width:52px; max-width:52px; font-size:15px; text-align:center;
  border:1px solid #aaa; border-radius:4px; padding:2px; background:#fafafa;
}
</style>

<script>
// Live projection: use per-day avg carried in data-avg.
// Projections: 1D = max(0, avg*1 - onHand), 3D = max(0, avg*3 - onHand), 5D = max(0, avg*5 - onHand)
document.addEventListener("input", function(e){
  if(e.target && e.target.classList.contains("onhand-input")){
    var idx = e.target.getAttribute("data-idx");
    var onh = parseInt(e.target.value || "0"); if(isNaN(onh)) onh = 0;
    var avg = parseFloat(e.target.getAttribute("data-avg") || "0"); if(isNaN(avg)) avg = 0;
    var p1 = Math.max(0, Math.round(avg*1 - onh));
    var p3 = Math.max(0, Math.round(avg*3 - onh));
    var p5 = Math.max(0, Math.round(avg*5 - onh));
    document.getElementById("p1-"+idx).innerText = p1;
    document.getElementById("p3-"+idx).innerText = p3;
    document.getElementById("p5-"+idx).innerText = p5;
  }
});
</script>
""", unsafe_allow_html=True)

# ------------------------------ HELPERS ------------------------------
@st.cache_data
def parse_excel(uploaded_file) -> dict:
    # Your original shape: first col product, next 3 are numeric
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
                try: return float(v)
                except: return 0.0
            rows.append([name, num(r.iloc[1]), num(r.iloc[2]), num(r.iloc[3])])
        if rows:
            data[sheet] = rows
    return data

def build_html_table(df: pd.DataFrame, vendor: str, branch: str):
    """
    Renders:
      - micro action buttons (1D/3D/5D) below the header
      - a table where '1 Day' is treated as AvgPerDay (if exists).
        If you actually import AvgPerDay explicitly in the future, just rename column to 'Per Day'
        and this will still work unchanged.
      - On typing On-Hand, projections update live on screen.
      - Buttons build invoice (non-zero items only) and open WhatsApp.
    """
    # Decide AvgPerDay for each row:
    # Prefer a 'Per Day' / 'Avg' column if ever added; otherwise treat existing '1 Day' as AvgPerDay.
    avg_col = None
    for cand in ["Per Day", "Avg", "Average", "Avg/Day", "1 Day"]:
        if cand in df.columns: avg_col = cand; break
    if avg_col is None:
        # Fallback: if your files are as before (3 numeric cols), use first numeric as avg
        avg_col = "1 Day"

    # Build table rows with data-avg and initial projected values (OnHand default = 0)
    rows = []
    for i, r in df.iterrows():
        avg = float(r[avg_col]) if pd.notna(r[avg_col]) else 0.0
        p1 = max(0, round(avg*1 - 0))
        p3 = max(0, round(avg*3 - 0))
        p5 = max(0, round(avg*5 - 0))
        rows.append(
            '<tr>'
            f'<td id="prod-{i}">{r["Product"]}</td>'
            f'<td><input class="onhand-input" type="number" inputmode="numeric" pattern="[0-9]*" '
            f'data-idx="{i}" data-avg="{avg}"></td>'
            f'<td id="p1-{i}">{p1}</td>'
            f'<td id="p3-{i}">{p3}</td>'
            f'<td id="p5-{i}">{p5}</td>'
            '</tr>'
        )
    rows_html = "".join(rows)

    vendor_js = json.dumps(vendor)
    branch_js = json.dumps(branch)

    html = (
        '<div class="action-row">'
        '<button onclick="sendWA(1)">1D</button>'
        '<button onclick="sendWA(3)">3D</button>'
        '<button onclick="sendWA(5)">5D</button>'
        '</div>'
        '<table class="mobile-table">'
        '<colgroup><col><col><col><col><col></colgroup>'
        '<tr><th>Product</th><th>On Hand</th><th>1 Day</th><th>3 Day</th><th>5 Day</th></tr>'
        + rows_html +
        '</table>'
        '<script>'
        'var VENDOR=' + vendor_js + ';'
        'var BRANCH=' + branch_js + ';'
        'function nowString(){var d=new Date();function pad(n){n=("0"+n).slice(-2);return n;}'
        'return d.getFullYear()+"-"+pad(d.getMonth()+1)+"-"+pad(d.getDate())+" "+'
        'pad(d.getHours())+":"+pad(d.getMinutes())+":"+pad(d.getSeconds());}'
        'function buildInvoice(period){'
        'var pref=(period===1)?"p1-":(period===3)?"p3-":"p5-";'
        'var table=document.querySelector(".mobile-table");'
        'var trs=table.querySelectorAll("tr");'
        'var lines=[];'
        'lines.push("*Vendor Demand Invoice*");'
        'lines.push("*Vendor:* "+VENDOR);'
        'lines.push("*Branch:* "+BRANCH);'
        'lines.push("*Projection:* "+period+" Day");'
        'lines.push("*Date:* "+nowString());'
        'lines.push("");'
        'lines.push("*ITEMS:*");'
        'var totalQty=0,totalItems=0;'
        'for(var i=1;i<trs.length;i++){'
        '  var prod=document.getElementById("prod-"+(i-1));'
        '  var qtyC=document.getElementById(pref+(i-1));'
        '  if(!prod||!qtyC) continue;'
        '  var name=(prod.innerText||"").trim();'
        '  var qty=parseInt(qtyC.innerText||"0");if(isNaN(qty)) qty=0;'
        '  if(qty>0){ totalQty+=qty; totalItems+=1; lines.push("- "+name+": "+qty); }'
        '}'
        'lines.push("");'
        'lines.push("*TOTAL ITEMS:* "+totalItems);'
        'lines.push("*TOTAL QTY:* "+totalQty);'
        'return lines.join("\\n");'
        '}'
        'function sendWA(period){'
        'var text=buildInvoice(period);'
        'var url="https://api.whatsapp.com/send?text="+encodeURIComponent(text);'
        'var a=document.createElement("a");a.href=url;a.target="_blank";a.rel="noopener";'
        'document.body.appendChild(a);a.click();a.remove();'
        '}'
        '</script>'
    )

    height = 130 + len(df) * 42  # show full table (no inner scroll)
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
    c1, c2 = st.columns([2,1])
    with c1:
        st.success(f"✅ Loaded {len(ss.vendor_data)} vendors")
    with c2:
        if st.button("📤 Upload Excel File"):
            ss.vendor_data = {}
            st.rerun()

# ------------------------------ MAIN ------------------------------
if ss.vendor_data:
    vendors = list(ss.vendor_data.keys())
    vendor = st.selectbox("🔍 Select Vendor", vendors)
    branch = st.selectbox("🏬 Select Branch",
                          ["Shahbaz","Clifton","Badar","DHA Ecom","BHD Ecom","BHD","Head Office"])

    # Expect your 3 numeric columns; name them explicitly:
    # We'll treat "1 Day" as AvgPerDay if there's no dedicated per-day column.
    df = pd.DataFrame(ss.vendor_data[vendor], columns=["Product","1 Day","3 Day","5 Day"])
    render_html = build_html_table(df, vendor, branch)
