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
ss.setdefault("invoice_text", "")
ss.setdefault("show_upload", False)

# -------------------------------------------------
# CSS + JS
# -------------------------------------------------
st.markdown("""
<style>
.block-container { max-width: 800px; padding-top: .1rem; }
h1,h2,h3 { text-align:center; margin-bottom:.2rem; }
.mobile-table { width:100%; border-collapse:collapse; margin-top:10px; }
.mobile-table th, .mobile-table td {
  border:1px solid #ddd; text-align:center; padding:6px;
  font-size:15px;
}
.mobile-table input {
  font-size:15px; width:60px; text-align:center; border:1px solid #aaa;
  border-radius:6px; padding:3px; background:#fafafa;
}
.stButton>button {
  background:#6c5ce7 !important; color:white !important;
  border-radius:8px !important; padding:6px 12px !important;
  font-weight:600 !important; font-size:14px !important;
}
.proj-buttons { text-align:center; margin-bottom:6px; margin-top:2px; }
.proj-buttons button {
  margin:0 5px; padding:5px 12px; border:none; border-radius:6px;
  background:#6c5ce7; color:white; font-weight:600; font-size:14px;
  cursor:pointer;
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
    const p1 = Math.max(0, d1 - val);
    const p3 = Math.max(0, d3 - val);
    const p5 = Math.max(0, d5 - val);
    document.getElementById("p1-"+idx).innerText = p1;
    document.getElementById("p3-"+idx).innerText = p3;
    document.getElementById("p5-"+idx).innerText = p5;
  }
});
</script>
""", unsafe_allow_html=True)

# -------------------------------------------------
# HELPERS
# -------------------------------------------------
@st.cache_data
def parse_excel(uploaded_file) -> dict:
    """Parse Excel into dict of sheets with product rows"""
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

def build_invoice_text(vendor, branch, items, period):
    lines = [
        f"*Vendor Demand ({period} Projection)*",
        f"*Vendor:* {vendor}",
        f"*Branch:* {branch}",
        f"*Date:* {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}","",
        "*ITEMS:*"
    ]
    total = 0
    for p, q in items:
        q = int(q)
        total += q
        lines.append(f"- {p}: {q}")
    lines += ["", f"*TOTAL ITEMS:* {len(items)}", f"*TOTAL QTY:* {total}"]
    return "\n".join(lines)

def redirect_to_whatsapp(text):
    wa_url = f"https://api.whatsapp.com/send?text={urllib.parse.quote(text)}"
    js = f"<script>window.open('{wa_url}', '_blank');</script>"
    components.html(js, height=0)

# -------------------------------------------------
# HEADER
# -------------------------------------------------
col1, col2 = st.columns([1, 6])
with col1:
    logo_candidates = ["fresh_basket_logo.png", "fresh basket logo.jfif"]
    logo_path = next((p for p in logo_candidates if os.path.exists(p)), None)
    if logo_path:
        st.image(logo_path, width=90)
with col2:
    st.markdown("<h2 style='margin-top:-5px;'>Vendors Demand</h2>", unsafe_allow_html=True)

# -------------------------------------------------
# PROJECTION BUTTONS (Top)
# -------------------------------------------------
c1, c2, c3 = st.columns(3)
with c1:
    btn_1d = st.button("1D")
with c2:
    btn_3d = st.button("3D")
with c3:
    btn_5d = st.button("5D")

# -------------------------------------------------
# UPLOAD
# -------------------------------------------------
if not ss.vendor_data:
    uploaded = st.file_uploader("📑 Upload Excel File", type=["xlsx", "xls"])
    if uploaded:
        ss.vendor_data = parse_excel(uploaded)
        st.success(f"✅ Loaded {len(ss.vendor_data)} vendors")
else:
    c1, c2 = st.columns([2, 1])
    with c1:
        st.success(f"✅ Dataset: {len(ss.vendor_data)} vendors")
    with c2:
        if st.button("📤 Upload Excel File"):
            ss.vendor_data.clear()
            ss.current_vendor = None
            ss.invoice_text = ""
            ss.show_upload = True
    if ss.show_upload:
        new_file = st.file_uploader("Upload Excel File", type=["xlsx", "xls"], key="replace_upload")
        if new_file:
            ss.vendor_data = parse_excel(new_file)
            ss.show_upload = False
            st.success("✅ Dataset updated successfully!")

# -------------------------------------------------
# MAIN UI
# -------------------------------------------------
if ss.vendor_data:
    vendors = list(ss.vendor_data.keys())
    vendor = st.selectbox("🔍 Select Vendor", vendors)
    branch = st.selectbox("🏬 Select Branch",
        ["Shahbaz", "Clifton", "Badar", "DHA Ecom", "BHD Ecom", "BHD", "Head Office"])
    ss.current_vendor = vendor
    rows = ss.vendor_data[vendor]
    df = pd.DataFrame(rows, columns=["Product", "1 Day", "3 Day", "5 Day"])
    df.insert(1, "On Hand", 0)

    # --- Build Table ---
    html = """
    <table class="mobile-table">
    <tr><th>Product</th><th>On Hand</th><th>1 Day</th><th>3 Day</th><th>5 Day</th></tr>
    """
    for i, r in df.iterrows():
        html += f"""
        <tr>
          <td>{r['Product']}</td>
          <td><input class='onhand-input' data-idx='{i}' type='number'
                inputmode='numeric' maxlength='5'
                data-day1='{r['1 Day']}' data-day3='{r['3 Day']}' data-day5='{r['5 Day']}'></td>
          <td id='p1-{i}'>{r['1 Day']}</td>
          <td id='p3-{i}'>{r['3 Day']}</td>
          <td id='p5-{i}'>{r['5 Day']}</td>
        </tr>
        """
    html += "</table>"
    components.html(html, height=min(1500, 100 + len(df)*40), scrolling=False)

    # --- Button Logic ---
    def generate_and_send(period_label):
        day_map = {"1D": "1 Day", "3D": "3 Day", "5D": "5 Day"}
        day_col = day_map[period_label]
        items = [[r["Product"], max(0, int(r[day_col]) - 0)] for _, r in df.iterrows()]
        ss.invoice_text = build_invoice_text(vendor, branch, items, period_label)
        redirect_to_whatsapp(ss.invoice_text)

    if btn_1d: generate_and_send("1D")
    if btn_3d: generate_and_send("3D")
    if btn_5d: generate_and_send("5D")
