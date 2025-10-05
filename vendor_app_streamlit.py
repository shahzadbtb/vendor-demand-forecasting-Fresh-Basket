import os
import datetime
import urllib.parse
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

# -------------------------------------------------
# CONFIG
# -------------------------------------------------
st.set_page_config(page_title="Vendor Demand Forecasting - Fresh Basket", page_icon="📦", layout="centered")

ss = st.session_state
ss.setdefault("vendor_data", {})
ss.setdefault("current_vendor", None)
ss.setdefault("projection", None)
ss.setdefault("invoice_text", "")
ss.setdefault("show_upload", False)
ss.setdefault("show_invoice", False)

# -------------------------------------------------
# CSS
# -------------------------------------------------
st.markdown("""
<style>
.block-container { max-width: 800px; padding-top: .3rem; }
h1, h2, h3, h4, h5 { text-align:center; }
input[type=number] {
    font-size:18px !important;
    width:100%;
    text-align:center;
    padding:8px;
    border-radius:8px;
    border:1px solid #aaa;
}
label {font-weight:600;}
tr, td, th { text-align:center; }
.mobile-table td { padding:6px; }
button, .stButton>button {
    background-color:#6c5ce7 !important;
    color:white !important;
    border-radius:8px !important;
    padding:10px 18px !important;
    font-weight:600 !important;
}
textarea{
    width:100% !important; font-size:18px !important;
    font-weight:500 !important; line-height:1.4 !important;
    padding:10px !important; resize:none !important;
}
</style>
""", unsafe_allow_html=True)

# -------------------------------------------------
# HELPERS
# -------------------------------------------------
def parse_excel(uploaded_file) -> dict:
    x = pd.ExcelFile(uploaded_file)
    data = {}
    for sheet in x.sheet_names:
        raw = pd.read_excel(uploaded_file, sheet_name=sheet, header=None).iloc[:, :4]
        rows = []
        for _, r in raw.iterrows():
            name = "" if pd.isna(r.iloc[0]) else str(r.iloc[0]).strip()
            if not name: continue
            def num(v): 
                try: return int(float(v))
                except: return 0
            rows.append([name, num(r.iloc[1]), num(r.iloc[2]), num(r.iloc[3])])
        if rows: data[sheet] = rows
    return data

def build_invoice_text(vendor, branch, items):
    lines = [
        "*Vendor Demand Invoice*",
        f"*Vendor:* {vendor}",
        f"*Branch:* {branch}",
        f"*Date:* {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "", "*ITEMS:*"
    ]
    total = 0
    for p, q in items:
        q = int(q)
        total += q
        lines.append(f"- {p}: {q}")
    lines += ["", f"*TOTAL ITEMS:* {len(items)}", f"*TOTAL QTY:* {total}"]
    return "\n".join(lines)

def copy_button(label, text_to_copy, key):
    safe = text_to_copy.replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")
    html = f"""
    <div>
      <button id="btn-{key}">{label}</button>
      <textarea id="txt-{key}" style="position:absolute;left:-9999px;top:-9999px;">{safe}</textarea>
    </div>
    <script>
    const btn=document.getElementById("btn-{key}");
    const txt=document.getElementById("txt-{key}");
    btn.onclick=async ()=>{{
        try{{
          await navigator.clipboard.writeText(txt.value);
          const old=btn.innerText; btn.innerText="Copied!";
          setTimeout(()=>btn.innerText=old,1200);
        }}catch(e){{alert("Copy failed.");}}
    }};
    </script>
    """
    components.html(html, height=50)

# -------------------------------------------------
# HEADER
# -------------------------------------------------
col1, col2 = st.columns([1,6])
with col1:
    logo_candidates = ["fresh_basket_logo.png","fresh basket logo.jfif"]
    logo_path = next((p for p in logo_candidates if os.path.exists(p)), None)
    if logo_path: st.image(logo_path, width=140)
with col2:
    st.title("Vendors Demand Forecasting")
st.caption("Fast, Mobile-Optimized • Fresh Basket")

# -------------------------------------------------
# UPLOAD
# -------------------------------------------------
if not ss.vendor_data:
    uploaded = st.file_uploader("📑 Upload Excel File", type=["xlsx","xls"], key="first_upload")
    if uploaded:
        ss.vendor_data = parse_excel(uploaded)
        st.success(f"✅ Loaded {len(ss.vendor_data)} vendors")
else:
    cols = st.columns([1,1])
    with cols[0]:
        st.success(f"✅ {len(ss.vendor_data)} vendors loaded")
    with cols[1]:
        if st.button("📤 Upload New File"):
            ss.show_upload = True
    if ss.show_upload:
        new_file = st.file_uploader("Upload New Excel File", type=["xlsx","xls"], key="replace_upload")
        if new_file:
            ss.vendor_data = parse_excel(new_file)
            ss.show_upload = False
            st.success("✅ File replaced successfully.")

# -------------------------------------------------
# MAIN UI
# -------------------------------------------------
if ss.vendor_data:
    vendors = list(ss.vendor_data.keys())
    vendor = st.selectbox("🔍 Select Vendor", vendors)
    branch = st.selectbox("🏬 Select Branch", ["Shahbaz","Clifton","Badar","DHA Ecom","BHD Ecom","BHD","Head Office"])
    ss.current_vendor = vendor
    rows = ss.vendor_data[vendor]

    df = pd.DataFrame(rows, columns=["Product","1 Day","3 Day","5 Day"])
    df.insert(1,"On Hand",0)

    st.markdown("### 🧮 Enter On-Hand Stock (Quick Input Mode)")
    # --- Build mobile-friendly HTML input table ---
    html = """
    <table class="mobile-table" width="100%">
    <tr><th>Product</th><th>On Hand</th><th>1D</th><th>3D</th><th>5D</th></tr>
    """
    for i, r in df.iterrows():
        html += f"""
        <tr>
          <td>{r['Product']}</td>
          <td><input type='number' id='onhand{i}' name='onhand{i}' 
                inputmode='numeric' pattern='[0-9]*' placeholder='0'></td>
          <td>{r['1 Day']}</td>
          <td>{r['3 Day']}</td>
          <td>{r['5 Day']}</td>
        </tr>
        """
    html += "</table>"
    components.html(html, height=min(600,100+len(df)*45), scrolling=True)

    st.divider()
    st.markdown("### 📊 Choose Projection")
    c1,c2,c3 = st.columns(3)
    if c1.button("1 Day"): ss.projection="1"
    if c2.button("3 Day"): ss.projection="3"
    if c3.button("5 Day"): ss.projection="5"

    if ss.projection:
        base_col = {"1":"1 Day","3":"3 Day","5":"5 Day"}[ss.projection]
        header = {"1":"1 Day Projection","3":"3 Day Projection","5":"5 Day Projection"}[ss.projection]
        show = df[["Product", base_col]].copy()
        show.rename(columns={base_col:header}, inplace=True)
        items = show.values.tolist()
        ss.invoice_text = build_invoice_text(vendor, branch, items)
        st.success(f"✅ Showing {header}")
        st.dataframe(show, use_container_width=True, hide_index=True)

        st.markdown("### 🧾 Invoice")
        if st.button("💾 Generate Invoice"):
            ss.show_invoice=True

        if ss.show_invoice:
            n_lines = ss.invoice_text.count("\n")+1
            st.text_area("Invoice Preview", ss.invoice_text, height=40*n_lines, key="invoice_edit")
            b1,b2 = st.columns(2)
            with b1:
                wa_url = f"https://api.whatsapp.com/send?text={urllib.parse.quote(ss.invoice_text)}"
                st.markdown(f"[📲 Send via WhatsApp]({wa_url})", unsafe_allow_html=True)
            with b2:
                copy_button("📋 Copy Invoice", ss.invoice_text, key="inv1")
