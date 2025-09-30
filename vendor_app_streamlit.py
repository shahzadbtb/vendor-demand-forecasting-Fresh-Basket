import os
import datetime
import urllib.parse
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

# ------------------------------
# CONFIG
# ------------------------------
st.set_page_config(
    page_title="Vendor Demand Forecasting - Fresh Basket",
    page_icon="📦",
    layout="centered"
)

# ------------------------------
# STATE
# ------------------------------
ss = st.session_state
ss.setdefault("vendor_data", {})
ss.setdefault("current_vendor", None)
ss.setdefault("projection", None)
ss.setdefault("proj_df", None)
ss.setdefault("show_upload", False)
ss.setdefault("invoice_text", "")

# ------------------------------
# GLOBAL CSS (extra small widths)
# ------------------------------
st.markdown("""
<style>
.block-container { max-width: 800px; padding-top: 0.5rem; }

/* Hide headers for Product Data table */
div[data-testid="stDataEditor"] thead tr { display: none !important; }

/* Product Data table widths (mobile friendly & compact) */
div[data-testid="stDataEditor"] td:nth-child(1) { width: 20% !important; }  /* Product */
div[data-testid="stDataEditor"] td:nth-child(2) { width: 16% !important; }  /* On Hand */
div[data-testid="stDataEditor"] td:nth-child(3),
div[data-testid="stDataEditor"] td:nth-child(4),
div[data-testid="stDataEditor"] td:nth-child(5) { width: 16% !important; }  /* Days */

/* Projection table widths */
div[data-testid="stDataFrame"] td:nth-child(1) { width: 60% !important; }
div[data-testid="stDataFrame"] td:nth-child(2) { width: 40% !important; text-align: left !important; }

/* Invoice textarea */
textarea {
  width: 100% !important;
  font-size: 16px !important;
  font-weight: 500 !important;
  line-height: 1.5 !important;
  padding: 8px !important;
  resize: none !important;
}
</style>
""", unsafe_allow_html=True)

# ------------------------------
# HELPERS
# ------------------------------
def parse_excel(uploaded_file) -> dict:
    excel_file = pd.ExcelFile(uploaded_file)
    data = {}
    for sheet in excel_file.sheet_names:
        raw = pd.read_excel(uploaded_file, sheet_name=sheet, header=None).iloc[:, :4]
        rows = []
        for _, r in raw.iterrows():
            name = "" if pd.isna(r.iloc[0]) else str(r.iloc[0]).strip()
            if not name:
                continue
            def num(x): 
                try: return int(float(x))
                except: return 0
            rows.append([name, num(r.iloc[1]), num(r.iloc[2]), num(r.iloc[3])])
        if rows:
            data[sheet] = rows
    return data

def build_invoice_text(vendor: str, branch: str, items: list[list]) -> str:
    lines = [
        "*Vendor Demand Invoice*",
        f"*Vendor:* {vendor}",
        f"*Branch:* {branch}",
        f"*Date:* {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        "*ITEMS:*",
    ]
    total = 0
    for product, qty in items:
        q = int(qty)
        total += q
        lines.append(f"- {product}: {q}")
    lines += ["", f"*TOTAL ITEMS:* {len(items)}", f"*TOTAL QTY:* {total}"]
    return "\n".join(lines)

def copy_button(label: str, text_to_copy: str, key: str):
    safe = (text_to_copy
            .replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))
    html = f"""
    <div>
      <button id="btn-{key}" style="
        background:#6c5ce7;color:white;border:none;border-radius:8px;
        padding:10px 16px;cursor:pointer;font-weight:700;">{label}</button>
      <textarea id="txt-{key}" style="position:absolute;left:-9999px;top:-9999px;">{safe}</textarea>
    </div>
    <script>
      const btn = document.getElementById("btn-{key}");
      const txt = document.getElementById("txt-{key}");
      btn.onclick = async () => {{
        try {{
          await navigator.clipboard.writeText(txt.value);
          const old = btn.innerText; btn.innerText = "Copied!";
          setTimeout(()=>btn.innerText = old, 1200);
        }} catch(e) {{ alert("Copy failed."); }}
      }};
    </script>
    """
    components.html(html, height=50)

def whatsapp_url(text: str) -> str:
    """Always open normal WhatsApp (not Business)."""
    return f"https://api.whatsapp.com/send?text={urllib.parse.quote(text)}"

def table_height(n_rows: int) -> int:
    return min(1600, 50 + n_rows * 42)

# ------------------------------
# HEADER
# ------------------------------
col1, col2 = st.columns([1, 6])
with col1:
    logo_candidates = ["fresh_basket_logo.png", "fresh basket logo.jfif"]
    logo_path = next((p for p in logo_candidates if os.path.exists(p)), None)
    if logo_path:
        st.image(logo_path, width=240)   # doubled logo size
with col2:
    st.title("Vendors Demand Forecasting")
st.caption("Powered by Fresh Basket • Mobile Friendly • Fast & Dynamic")

# ------------------------------
# UPLOAD
# ------------------------------
if not ss.vendor_data:
    uploaded = st.file_uploader("📑 Upload Excel File", type=["xlsx", "xls"], key="first_upload")
    if uploaded:
        ss.vendor_data = parse_excel(uploaded)
        if ss.vendor_data:
            st.success(f"✅ Loaded {len(ss.vendor_data)} vendors")
            ss.show_upload = False
        else:
            st.error("No valid rows found. Please check your Excel file.")
else:
    c1, c2 = st.columns([1, 1])
    with c1: st.success(f"✅ Current dataset loaded: **{len(ss.vendor_data)} vendors**")
    with c2:
        if st.button("📤 Upload New Excel File"): ss.show_upload = True
    if ss.show_upload:
        new_file = st.file_uploader("Upload New Excel File", type=["xlsx", "xls"], key="replace_upload")
        if new_file:
            ss.vendor_data = parse_excel(new_file)
            ss.current_vendor = None; ss.projection = None; ss.proj_df = None; ss.show_upload = False
            if ss.vendor_data: st.success(f"✅ Replaced dataset. Loaded {len(ss.vendor_data)} vendors.")
            else: st.error("No valid rows found in the new file.")

# ------------------------------
# MAIN UI
# ------------------------------
if ss.vendor_data:
    vendors = list(ss.vendor_data.keys())
    vendor = st.selectbox("🔍 Select Vendor", vendors, index=0 if ss.current_vendor is None else vendors.index(ss.current_vendor))
    branch = st.selectbox("🏬 Select Branch", ["Shahbaz","Clifton","Badar","DHA Ecom","BHD Ecom","BHD","Head Office"])

    ss.current_vendor = vendor
    rows = ss.vendor_data[vendor]

    df = pd.DataFrame(rows, columns=["Product", "1 Day", "2 Days", "5 Days"])
    df = df[df["Product"].notna() & (df["Product"].str.strip() != "")]
    df.insert(1, "On Hand", 0)

    st.markdown("### 📋 Product Data (enter On Hand only)")
    edited = st.data_editor(df, use_container_width=True, hide_index=True, height=table_height(len(df)),
        column_config={
            "Product": st.column_config.Column(disabled=True),
            "On Hand": st.column_config.NumberColumn(format="%d", min_value=0, step=1),
            "1 Day": st.column_config.NumberColumn(format="%d", disabled=True),
            "2 Days": st.column_config.NumberColumn(format="%d", disabled=True),
            "5 Days": st.column_config.NumberColumn(format="%d", disabled=True),
        },
        disabled=["Product", "1 Day", "2 Days", "5 Days"],
    )

    st.divider()
    st.markdown("### 📊 Choose Projection")

    # Projection buttons row
    pc1, pc2, pc3, pc4 = st.columns([1,1,1,2])
    with pc1: 
        if st.button("1 Day"): ss.projection = "1"
    with pc2: 
        if st.button("2 Days"): ss.projection = "2"
    with pc3: 
        if st.button("5 Days"): ss.projection = "5"
    with pc4:
        # FIX: now linked to projection table instead of dummy
        if ss.proj_df is not None:
            header = ss.proj_df.columns[-1]
            use = ss.proj_df[["Product", header]]
            use = use[use[header] > 0]
            if not use.empty:
                text = build_invoice_text(vendor, branch, use.values.tolist())
                st.markdown(f"[📲 Send via WhatsApp]({whatsapp_url(text)})", unsafe_allow_html=True)

    if ss.projection:
        base_col = {"1": "1 Day", "2": "2 Days", "5": "5 Days"}[ss.projection]
        header = {"1": "1 Day Projection", "2": "2 Days Projection", "5": "5 Days Projection"}[ss.projection]

        tmp = edited.fillna(0).copy()
        for c in ["1 Day", "2 Days", "5 Days", "On Hand"]:
            tmp[c] = tmp[c].apply(lambda x: int(x) if pd.notna(x) else 0)
        tmp[header] = tmp.apply(lambda r: max(0, int(r[base_col]) - int(r["On Hand"])), axis=1)

        ss.proj_df = tmp
        show = tmp[["Product", header]].copy()
        st.success(f"✅ Showing {header}")
        st.dataframe(show, use_container_width=True, height=table_height(len(show)), hide_index=True)

        st.markdown("### 🧾 Invoice")
        c1, c2 = st.columns([1,1])
        with c1:
            if st.button("💾 Save & Show Invoice"):
                use = show[show[header] > 0]
                if not use.empty:
                    ss.invoice_text = build_invoice_text(vendor, branch, use.values.tolist())
        with c2:
            if ss.invoice_text:
                st.markdown(f"[📲 Send via WhatsApp]({whatsapp_url(ss.invoice_text)})", unsafe_allow_html=True)

        if ss.invoice_text:
            st.text_area("Invoice Preview", ss.invoice_text, height=table_height(len(show)), key="invoice_edit")
            ic1, ic2 = st.columns(2)
            with ic1: st.markdown(f"[📲 Send via WhatsApp]({whatsapp_url(ss.invoice_text)})", unsafe_allow_html=True)
            with ic2: copy_button("📋 Copy Invoice", ss.invoice_text, key="inv1")
