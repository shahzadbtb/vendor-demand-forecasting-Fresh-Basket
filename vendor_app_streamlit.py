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

# ------------------------------
# GLOBAL CSS
# ------------------------------
st.markdown("""
<style>
/* Container adjustments */
.block-container {
  max-width: 800px;
  padding-top: 0.5rem;
}
@media (max-width: 768px) {
  .block-container {
    max-width: 100%;
    padding-left: 0.2rem;
    padding-right: 0.2rem;
  }
}

/* Force tighter table layout */
div[data-testid="stDataFrame"] table,
div[data-testid="stDataEditor"] table {
  table-layout: fixed !important;
  width: 100% !important;
}

/* Hide 3-dot column menu */
div[data-testid="stDataEditor"] div[role="button"],
div[data-testid="stDataFrame"] div[role="button"] {
  display: none !important;
}

/* Column alignment */
div[data-testid="stDataFrame"] th,
div[data-testid="stDataFrame"] td,
div[data-testid="stDataEditor"] th,
div[data-testid="stDataEditor"] td {
  text-align: center !important;
  vertical-align: middle !important;
  font-size: 14px !important;
  white-space: normal !important;
  word-break: break-word !important;
  padding: 3px !important;
}

/* Product Data table widths */
div[data-testid="stDataEditor"] th:nth-child(1),
div[data-testid="stDataEditor"] td:nth-child(1) {
  width: 45% !important;   /* Product */
}
div[data-testid="stDataEditor"] th:nth-child(2),
div[data-testid="stDataEditor"] td:nth-child(2) {
  width: 12% !important;   /* On Hand */
}
div[data-testid="stDataEditor"] th:nth-child(n+3),
div[data-testid="stDataEditor"] td:nth-child(n+3) {
  width: 11% !important;   /* Day columns */
}

/* Projection table widths */
div[data-testid="stDataFrame"] th:nth-child(1),
div[data-testid="stDataFrame"] td:nth-child(1) {
  width: 35% !important;
}
div[data-testid="stDataFrame"] th:nth-child(n+2),
div[data-testid="stDataFrame"] td:nth-child(n+2) {
  width: 13% !important;
}

/* Invoice textarea */
textarea {
  width: 100% !important;
  min-height: 480px !important;
  font-size: 18px !important;
  font-weight: 500 !important;
  line-height: 1.5 !important;
  padding: 10px !important;
}
</style>
""", unsafe_allow_html=True)

# ------------------------------
# HELPERS
# ------------------------------
def parse_excel(uploaded_file) -> dict:
    """Return {sheet_name: [[Product, 1d, 2d, 5d], ...]}, skipping blank rows."""
    excel_file = pd.ExcelFile(uploaded_file)
    data = {}
    for sheet in excel_file.sheet_names:
        raw = pd.read_excel(uploaded_file, sheet_name=sheet, header=None).iloc[:, :4]
        rows = []
        for _, r in raw.iterrows():
            name = "" if pd.isna(r.iloc[0]) else str(r.iloc[0]).strip()
            if not name:  # skip blanks
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
    safe = (text_to_copy
            .replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))
    html = f"""
    <div>
      <button id="btn-{key}" style="
        background:#6c5ce7;color:white;border:none;border-radius:8px;
        padding:12px 18px;cursor:pointer;font-weight:700;">{label}</button>
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
        }} catch(e) {{ alert("Copy failed. Please copy manually."); }}
      }};
    </script>
    """
    components.html(html, height=60)

def table_height(n_rows: int) -> int:
    row_h = 42
    header_h = 52
    return min(1600, header_h + n_rows * row_h)

# ------------------------------
# HEADER
# ------------------------------
col1, col2 = st.columns([1, 6], vertical_alignment="center")
with col1:
    logo_candidates = ["fresh_basket_logo.png", "fresh basket logo.jfif"]
    logo_path = next((p for p in logo_candidates if os.path.exists(p)), None)
    if logo_path:
        st.image(logo_path, width=140)
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
    with c1:
        st.success(f"✅ Current dataset loaded: **{len(ss.vendor_data)} vendors**")
    with c2:
        if st.button("📤 Upload New Excel File"):
            ss.show_upload = True

    if ss.show_upload:
        new_file = st.file_uploader("Upload New Excel File", type=["xlsx", "xls"], key="replace_upload")
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
    vendor = st.selectbox(
        "🔍 Select Vendor",
        vendors,
        index=0 if ss.current_vendor is None else vendors.index(ss.current_vendor),
    )

    branch = st.selectbox(
        "🏬 Select Branch",
        ["Shahbaz", "Clifton", "Badar", "DHA Ecom", "BHD Ecom", "BHD", "Head Office"]
    )

    ss.current_vendor = vendor
    rows = ss.vendor_data[vendor]

    # Keep "On Hand" fixed after Product
    df = pd.DataFrame(rows, columns=["Product", "1 Day", "2 Days", "5 Days"])
    df = df[df["Product"].notna() & (df["Product"].str.strip() != "")]
    df.insert(1, "On Hand", 0)  # insert right after Product

    st.markdown("### 📋 Product Data (enter On Hand only)")
    edited = st.data_editor(
        df,
        use_container_width=True,
        hide_index=True,
        height=table_height(len(df)),
        column_config={
            "Product": st.column_config.Column(disabled=True, width="large"),
            "On Hand": st.column_config.NumberColumn(format="%d", min_value=0, step=1, width="x-small"),
            "1 Day": st.column_config.NumberColumn(format="%d", disabled=True, width="x-small"),
            "2 Days": st.column_config.NumberColumn(format="%d", disabled=True, width="x-small"),
            "5 Days": st.column_config.NumberColumn(format="%d", disabled=True, width="x-small"),
        },
        disabled=["Product", "1 Day", "2 Days", "5 Days"],  # lock those columns fully
    )

    st.divider()
    st.markdown("### 📊 Choose Projection")
    pc1, pc2, pc3 = st.columns(3)
    with pc1:
        if st.button("1 Day"): ss.projection = "1"
    with pc2:
        if st.button("2 Days"): ss.projection = "2"
    with pc3:
        if st.button("5 Days"): ss.projection = "5"

    if ss.projection:
        base_col = {"1": "1 Day", "2": "2 Days", "5": "5 Days"}[ss.projection]
        header = {"1": "1 Day Projection", "2": "2 Days Projection", "5": "5 Days Projection"}[ss.projection]

        tmp = edited.fillna(0).copy()
        for c in ["1 Day", "2 Days", "5 Days", "On Hand"]:
            tmp[c] = tmp[c].apply(lambda x: int(x) if pd.notna(x) else 0)

        tmp[header] = tmp.apply(lambda r: max(0, int(r[base_col]) - int(r["On Hand"])), axis=1)
        ss.proj_df = tmp

        if not any(tmp["On Hand"] > 0):
            st.warning("⚠️ Please enter On Hand for at least one product before saving.")
        else:
            st.success(f"✅ Showing {header}")
            show = tmp[["Product", "On Hand", "1 Day", "2 Days", "5 Days", header]].copy()
            show = show[show["Product"].notna() & (show["Product"].str.strip() != "")]
            for c in ["1 Day", "2 Days", "5 Days", "On Hand", header]:
                show[c] = show[c].astype(int)

            st.dataframe(show, use_container_width=True, height=table_height(len(show)), hide_index=True)

            st.markdown("### 🧾 Invoice")
            if st.button("💾 Save & Show Invoice"):
                use = show[["Product", header]]
                use = use[use[header] > 0]
                if use.empty:
                    st.warning("⚠️ No demand > 0 in the selected projection.")
                else:
                    items = use.values.tolist()
                    invoice_text = build_invoice_text(vendor, branch, items)

                    n_lines = invoice_text.count("\n") + 1
                    ta_height = min(1600, max(520, 28 * n_lines + 80))
                    st.text_area("Invoice Preview", invoice_text, height=ta_height, key="invoice_edit")

                    quoted = urllib.parse.quote(invoice_text)
                    wa_url = f"https://wa.me/?text={quoted}"

                    ic1, ic2 = st.columns(2)
                    with ic1: st.markdown(f"[📲 Send via WhatsApp]({wa_url})", unsafe_allow_html=True)
                    with ic2: copy_button("📋 Copy Invoice", invoice_text, key="inv1")
