import streamlit as st
import pandas as pd
import datetime
import urllib.parse
import streamlit.components.v1 as components

# ------------------------------
# CONFIG
# ------------------------------
st.set_page_config(
    page_title="Vendor Demand Forecasting - Fresh Basket",
    page_icon="📦",
    layout="wide"
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
                try:
                    return int(float(x))
                except Exception:
                    return 0
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
    safe = text_to_copy.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    html = f"""
    <div>
      <button id="btn-{key}" style="
        background:#6c5ce7;color:white;border:none;border-radius:8px;
        padding:14px 20px;cursor:pointer;font-weight:600;font-size:18px;
        width:100%;">{label}</button>
      <textarea id="txt-{key}" style="position:absolute;left:-9999px;top:-9999px;">{safe}</textarea>
    </div>
    <script>
      const btn = document.getElementById("btn-{key}");
      const txt = document.getElementById("txt-{key}");
      btn.onclick = async () => {{
        try {{
          await navigator.clipboard.writeText(txt.value);
          const old = btn.innerText;
          btn.innerText = "Copied!";
          setTimeout(()=>btn.innerText = old, 1500);
        }} catch(e) {{
          alert("Copy failed. Please copy manually.");
        }}
      }};
    </script>
    """
    components.html(html, height=70)

# ------------------------------
# CUSTOM CSS FOR MOBILE
# ------------------------------
st.markdown("""
<style>
/* Center all table cells and headers */
table, th, td {
    text-align: center !important;
    vertical-align: middle !important;
}
/* Make dropdowns & inputs bigger on mobile */
.stSelectbox, .stTextInput, .stFileUploader {
    font-size: 18px !important;
}
/* Responsive tweaks */
@media (max-width: 768px) {
    .stButton>button {
        width: 100% !important;
        font-size: 20px !important;
        padding: 14px !important;
    }
    .stSelectbox, .stTextInput, .stFileUploader {
        font-size: 20px !important;
    }
    textarea {
        font-size: 20px !important;
        padding: 12px !important;
    }
    table, th, td {
        font-size: 18px !important;
    }
}
</style>
""", unsafe_allow_html=True)

# ------------------------------
# HEADER
# ------------------------------
st.title("📦 Vendor Demand Forecasting")
st.caption("Powered by Fresh Basket • Mobile Friendly • Fast & Dynamic")

# ------------------------------
# UPLOAD OPTION
# ------------------------------
if not ss.vendor_data:
    uploaded = st.file_uploader("📑 Upload Excel File", type=["xlsx", "xls"])
    if uploaded:
        ss.vendor_data = parse_excel(uploaded)
        st.success(f"✅ Loaded {len(ss.vendor_data)} vendors")
else:
    cols = st.columns([1, 1])
    with cols[0]:
        st.success(f"✅ Current dataset loaded: **{len(ss.vendor_data)} vendors**")
    with cols[1]:
        if st.button("📤 Upload New Excel File"):
            ss.show_upload = True

    if ss.show_upload:
        new_file = st.file_uploader("Upload New Excel File", type=["xlsx", "xls"])
        if new_file:
            ss.vendor_data = parse_excel(new_file)
            ss.current_vendor = None
            ss.projection = None
            ss.proj_df = None
            ss.show_upload = False
            if ss.vendor_data:
                st.success(f"✅ Replaced dataset. Loaded {len(ss.vendor_data)} vendors.")
            else:
                st.error("No valid rows found in the new file.")

# ------------------------------
# MAIN UI
# ------------------------------
if ss.vendor_data:
    vendors = list(ss.vendor_data.keys())
    vendor = st.selectbox("🔍 Select Vendor", vendors, index=0 if ss.current_vendor is None else vendors.index(ss.current_vendor))
    branch = st.selectbox("🏬 Select Branch", ["Shahbaz", "Clifton", "BHD", "Badar", "DHA E-Comm"])

    ss.current_vendor = vendor
    rows = ss.vendor_data[vendor]

    # Base DataFrame
    df = pd.DataFrame(rows, columns=["Product", "1 Day", "2 Days", "5 Days"])
    df["On Hand"] = 0

    st.markdown("### 📋 Product Data (enter On Hand only)")
    edited = st.data_editor(
        df,
        use_container_width=True,
        hide_index=True,
        height=len(df) * 45 + 60,   # dynamic height
        column_config={
            "Product": st.column_config.Column(disabled=True, width="large"),
            "1 Day": st.column_config.NumberColumn(format="%d", disabled=True, width="small"),
            "2 Days": st.column_config.NumberColumn(format="%d", disabled=True, width="small"),
            "5 Days": st.column_config.NumberColumn(format="%d", disabled=True, width="small"),
            "On Hand": st.column_config.NumberColumn(format="%d", min_value=0, step=1),
        }
    )

    st.divider()
    st.markdown("### 📊 Choose Projection")
    c1, c2, c3 = st.columns(3)
    with c1:
        if st.button("1 Day"):
            ss.projection = "1"
    with c2:
        if st.button("2 Days"):
            ss.projection = "2"
    with c3:
        if st.button("5 Days"):
            ss.projection = "5"

    if ss.projection:
        base_col = {"1": "1 Day", "2": "2 Days", "5": "5 Days"}[ss.projection]
        header = {"1": "1 Day Projection", "2": "2 Days Projection", "5": "5 Days Projection"}[ss.projection]

        tmp = edited.fillna(0).copy()
        for col in ["1 Day", "2 Days", "5 Days", "On Hand"]:
            tmp[col] = tmp[col].apply(lambda x: int(x) if pd.notna(x) else 0)

        tmp[header] = tmp.apply(lambda r: max(0, int(r[base_col]) - int(r["On Hand"])), axis=1)
        ss.proj_df = tmp

        if not any(tmp["On Hand"] > 0):
            st.warning("⚠️ Please enter On Hand for at least one product before saving.")
        else:
            st.success(f"✅ Showing {header}")
            show = tmp[["Product", "1 Day", "2 Days", "5 Days", "On Hand", header]].copy()
            show = show[show["Product"].str.strip() != ""]  # remove blanks

            styled = show.style.set_properties(**{
                'text-align': 'center',
                'font-size': '22px'
            }).set_table_styles([{
                'selector': 'th',
                'props': [('text-align', 'center'), ('font-size', '22px')]
            }])

            st.dataframe(styled, use_container_width=True, height=len(show) * 45 + 60)

            st.markdown("### 🧾 Invoice")
            if st.button("💾 Save & Show Invoice"):
                use = show[["Product", header]]
                use = use[use[header] > 0]
                if use.empty:
                    st.warning("⚠️ No demand > 0 in the selected projection.")
                else:
                    items = use.values.tolist()
                    invoice_text = build_invoice_text(vendor, branch, items)

                    st.text_area(
                        "Invoice Preview",
                        invoice_text,
                        height=len(invoice_text.splitlines()) * 32,
                        key="invoice_edit"
                    )

                    quoted = urllib.parse.quote(invoice_text)
                    wa_url = f"https://wa.me/?text={quoted}"
                    st.markdown(f"[📲 Send via WhatsApp]({wa_url})", unsafe_allow_html=True)
                    copy_button("📋 Copy Invoice", invoice_text, key="inv1")
