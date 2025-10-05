import os
import datetime
import urllib.parse
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

# -------------------------------------------------
# CSS
# -------------------------------------------------
st.markdown("""
<style>
.block-container { max-width:800px; padding-top:.3rem; }
h1 { text-align:center; margin-bottom:.2rem; font-size:1.8rem; font-weight:700; }
h3 { text-align:center; margin-top:.5rem; font-size:1rem; }
.stButton>button {
  background:#6c5ce7 !important;
  color:white !important;
  border-radius:8px !important;
  padding:6px 14px !important;
  font-size:14px !important;
  font-weight:600 !important;
  margin:2px !important;
}
.mobile-table { width:100%; border-collapse:collapse; margin-top:.3rem; }
.mobile-table th, .mobile-table td {
  border:1px solid #ddd; text-align:center; padding:6px;
  font-size:15px;
}
.mobile-table input {
  font-size:15px; width:60px; text-align:center;
  border:1px solid #aaa; border-radius:4px; padding:2px;
}
</style>

<script>
document.addEventListener("input", e => {
  if(e.target && e.target.classList.contains("onhand-input")) {
    let idx = e.target.dataset.idx;
    const val = parseInt(e.target.value || "0");
    const d1 = parseInt(e.target.dataset.day1);
    const d3 = parseInt(e.target.dataset.day3);
    const d5 = parseInt(e.target.dataset.day5);
    document.getElementById("p1-"+idx).innerText = Math.max(0, d1 - val);
    document.getElementById("p3-"+idx).innerText = Math.max(0, d3 - val);
    document.getElementById("p5-"+idx).innerText = Math.max(0, d5 - val);
  }
});
</script>
""", unsafe_allow_html=True)

# -------------------------------------------------
# HELPER FUNCTIONS
# -------------------------------------------------
@st.cache_data
def parse_excel(uploaded_file):
    x = pd.ExcelFile(uploaded_file)
    data = {}
    for sheet in x.sheet_names:
        raw = pd.read_excel(uploaded_file, sheet_name=sheet, header=None).iloc[:, :4]
        rows = []
        for _, r in raw.iterrows():
            name = str(r.iloc[0]).strip() if pd.notna(r.iloc[0]) else ""
            if not name:
                continue
            def num(v):
                try:
                    return int(float(v))
                except:
                    return 0
            rows.append([name, num(r.iloc[1]), num(r.iloc[2]), num(r.iloc[3])])
        if rows:
            data[sheet] = rows
    return data

def build_invoice_text(vendor, branch, items):
    lines = [
        "*Vendor Demand Invoice*",
        f"*Vendor:* {vendor}",
        f"*Branch:* {branch}",
        f"*Date:* {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        "*ITEMS:*"
    ]
    total = 0
    for p, q in items:
        q = int(q)
        total += q
        lines.append(f"- {p}: {q}")
    lines += ["", f"*TOTAL ITEMS:* {len(items)}", f"*TOTAL QTY:* {total}"]
    return "\n".join(lines)

def open_whatsapp(invoice_text):
    wa_url = f"https://api.whatsapp.com/send?text={urllib.parse.quote(invoice_text)}"
    js = f"<script>window.open('{wa_url}', '_blank');</script>"
    components.html(js, height=0, width=0)

# -------------------------------------------------
# HEADER
# -------------------------------------------------
st.markdown("<h1>Vendors Demand</h1>", unsafe_allow_html=True)

# Inline 1D, 3D, 5D buttons
colA, colB, colC = st.columns(3)
with colA:
    one_day = st.button("1D")
with colB:
    three_day = st.button("3D")
with colC:
    five_day = st.button("5D")

# -------------------------------------------------
# UPLOAD
# -------------------------------------------------
if not ss.vendor_data:
    uploaded = st.file_uploader("📤 Upload Excel File", type=["xlsx", "xls"])
    if uploaded:
        ss.vendor_data = parse_excel(uploaded)
        st.success(f"✅ Loaded {len(ss.vendor_data)} vendors")
else:
    st.success(f"✅ Dataset: {len(ss.vendor_data)} vendors")
    if st.button("📤 Upload New File"):
        ss.vendor_data = {}

# -------------------------------------------------
# MAIN UI
# -------------------------------------------------
if ss.vendor_data:
    vendors = list(ss.vendor_data.keys())
    vendor = st.selectbox("🔍 Select Vendor", vendors)
    branch = st.selectbox("🏬 Select Branch", ["Shahbaz", "Clifton", "Badar", "DHA Ecom", "BHD Ecom", "BHD", "Head Office"])
    rows = ss.vendor_data[vendor]

    df = pd.DataFrame(rows, columns=["Product", "1 Day", "3 Day", "5 Day"])
    df.insert(1, "On Hand", 0)

    html = """
    <table class="mobile-table">
    <tr><th>Product</th><th>On Hand</th><th>1 Day</th><th>3 Day</th><th>5 Day</th></tr>
    """
    for i, r in df.iterrows():
        html += f"""
        <tr>
          <td>{r['Product']}</td>
          <td><input class='onhand-input' data-idx='{i}' type='number'
                inputmode='numeric' pattern='[0-9]*'
                data-day1='{r['1 Day']}' data-day3='{r['3 Day']}' data-day5='{r['5 Day']}'></td>
          <td id='p1-{i}'>{r['1 Day']}</td>
          <td id='p3-{i}'>{r['3 Day']}</td>
          <td id='p5-{i}'>{r['5 Day']}</td>
        </tr>
        """
    html += "</table>"
    components.html(html, height=min(800, 100 + len(df) * 40), scrolling=False)

    # -------------------------------------------------
    # PROJECTION BUTTON ACTIONS
    # -------------------------------------------------
    def handle_projection(days):
        items = df[["Product", f"{days} Day"]].values.tolist()
        text = build_invoice_text(vendor, branch, items)
        open_whatsapp(text)

    if one_day:
        handle_projection("1")
    elif three_day:
        handle_projection("3")
    elif five_day:
        handle_projection("5")
