import os
import datetime
import urllib.parse
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

# ----------------------------------------
# PAGE CONFIG
# ----------------------------------------
st.set_page_config(
    page_title="Vendor Demand Forecasting - Fresh Basket",
    page_icon="📦",
    layout="centered",
)

# ----------------------------------------
# SESSION STATE
# ----------------------------------------
ss = st.session_state
ss.setdefault("vendor_data", {})
ss.setdefault("current_vendor", None)
ss.setdefault("projection", None)
ss.setdefault("proj_df", None)
ss.setdefault("show_df", None)
ss.setdefault("invoice_text", "")
ss.setdefault("show_invoice", False)
ss.setdefault("show_upload", False)

# ----------------------------------------
# GLOBAL CSS (Mobile Optimized)
# ----------------------------------------
st.markdown("""
<style>
.block-container { max-width: 750px; padding-top: .3rem; }

h1, h2, h3, h4 { text-align:center; margin-bottom:0.5rem !important; }
img { display:block; margin-left:auto; margin-right:auto; }

div[data-testid="stDataEditor"] thead tr { display:none !important; }

div[data-testid="stDataEditor"] td:nth-child(1){ width:38% !important; } /* Product */
div[data-testid="stDataEditor"] td:nth-child(2){ width:10% !important; } /* On Hand */
div[data-testid="stDataEditor"] td:nth-child(3){ width:18% !important; } /* 1 Day */
div[data-testid="stDataEditor"] td:nth-child(4){ width:18% !important; } /* 3 Day */
div[data-testid="stDataEditor"] td:nth-child(5){ width:18% !important; } /* 5 Day */

div[data-testid="stDataFrame"] td:nth-child(1){ width:55% !important; }
div[data-testid="stDataFrame"] td:nth-child(2){
  width:45% !important; text-align:center !important;
}

div[data-testid="stDataFrame"] th, div[data-testid="stDataFrame"] td,
div[data-testid="stDataEditor"] th, div[data-testid="stDataEditor"] td {
  text-align:center !important;
  vertical-align:middle !important;
  font-size:14px !important;
  padding:4px !important;
  white-space:normal !important;
  word-break:break-word !important;
}

button[kind="primary"] { width:100%; }
textarea{
  width:100% !important; font-size:16px !important;
  font-weight:500 !important; line-height:1.4 !important;
  resize:none !important; overflow:hidden !important;
}
</style>
""", unsafe_allow_html=True)

# ----------------------------------------
# HELPERS
# ----------------------------------------
@st.cache_data
def parse_excel(uploaded_file) -> dict:
    """Read Excel into {sheet: [[Product, Day1, Day3, Day5]]}"""
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
                try:
                    return int(float(v))
                except Exception:
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
        "*ITEMS:*",
    ]
    total = 0
    for p, q in items:
        q = int(q)
        total += q
        lines.append(f"- {p}: {q}")
    lines += ["", f"*TOTAL ITEMS:* {len(items)}", f"*TOTAL QTY:* {total}"]
    return "\n".join(lines)


def copy_button(label, text, key):
    safe = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    html = f"""
    <div>
      <button id="btn-{key}" style="
        background:#6c5ce7;color:#fff;border:none;border-radius:8px;
        padding:8px 12px;cursor:pointer;font-weight:600;">{label}</button>
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
      }}catch(e){{ alert("Copy failed."); }}
    }};
    </script>
    """
    components.html(html, height=45)


def table_height(n): return 55 + n * 40

# ----------------------------------------
# HEADER
# ----------------------------------------
col1, col2 = st.columns([1, 4])
with col1:
    logo_candidates = ["fresh_basket_logo.png", "fresh_basket_logo.png.jfif", "fresh basket logo.jfif"]
    logo_path = next((p for p in logo_candidates if os.path.exists(p)), None)
    if logo_path:
        st.image(logo_path, width=80)
with col2:
    st.markdown("<h3>Vendor Demand Forecasting</h3>", unsafe_allow_html=True)

# ----------------------------------------
# FILE UPLOAD
# ----------------------------------------
if not ss.vendor_data:
    uploaded = st.file_uploader("📤 Upload Excel File", type=["xlsx", "xls"])
    if uploaded:
        ss.vendor_data = parse_excel(uploaded)
        if ss.vendor_data:
            st.success(f"✅ Loaded {len(ss.vendor_data)} vendors")
        else:
            st.error("No valid rows found.")
else:
    top1, top2 = st.columns([2, 1])
    with top1:
        st.success(f"✅ Dataset: {len(ss.vendor_data)} vendors")
    with top2:
        if st.button("📤 Upload Excel File"):
            ss.vendor_data.clear()
            ss.current_vendor = None
            ss.projection = None
            ss.proj_df = None
            ss.show_df = None
            ss.invoice_text = ""
            ss.show_invoice = False
            ss.show_upload = True

# ----------------------------------------
# MAIN LOGIC
# ----------------------------------------
if ss.vendor_data:
    vendors = list(ss.vendor_data.keys())
    vendor = st.selectbox("🔍 Select Vendor", vendors, index=0 if ss.current_vendor is None else vendors.index(ss.current_vendor))
    branch = st.selectbox("🏬 Select Branch", ["Shahbaz", "Clifton", "Badar", "DHA Ecom", "BHD Ecom", "BHD", "Head Office"])

    ss.current_vendor = vendor
    rows = ss.vendor_data[vendor]
    df = pd.DataFrame(rows, columns=["Product", "1 Day", "3 Day", "5 Day"])
    df.insert(1, "On Hand", 0)
    df = df[df["Product"].notna() & (df["Product"].str.strip() != "")]

    st.markdown("### 🧮 Enter On-Hand Stock")
    edited = st.data_editor(
        df,
        use_container_width=True,
        hide_index=True,
        height=table_height(len(df)),
        column_config={
            "Product": st.column_config.Column(disabled=True),
            "On Hand": st.column_config.NumberColumn(format="%d", min_value=0, step=1),
            "1 Day": st.column_config.NumberColumn(format="%d", disabled=True),
            "3 Day": st.column_config.NumberColumn(format="%d", disabled=True),
            "5 Day": st.column_config.NumberColumn(format="%d", disabled=True),
        },
        disabled=["Product", "1 Day", "3 Day", "5 Day"],
    )

    # --- Projection & Invoice Buttons Row ---
    st.markdown("### 📊 Projection Options")
    b1, b2, b3, b4, b5, b6 = st.columns(6)
    with b1:
        if st.button("1 Day"):
            ss.projection = "1"
    with b2:
        if st.button("3 Day"):
            ss.projection = "3"
    with b3:
        if st.button("5 Day"):
            ss.projection = "5"
    with b4:
        if st.button("🧾 Show Invoice"):
            ss.show_invoice = True
    with b5:
        if st.button("📲 WhatsApp"):
            ss.show_invoice = True
    with b6:
        copy_button("📋 Copy", ss.invoice_text or "No invoice yet", key="copy")

    if ss.projection:
        base_col = {"1": "1 Day", "3": "3 Day", "5": "5 Day"}[ss.projection]
        header = {"1": "1 Day Projection", "3": "3 Day Projection", "5": "5 Day Projection"}[ss.projection]

        tmp = edited.fillna(0).copy()
        for c in ["1 Day", "3 Day", "5 Day", "On Hand"]:
            tmp[c] = tmp[c].apply(lambda x: int(x) if pd.notna(x) else 0)

        tmp[header] = tmp.apply(lambda r: max(0, int(r[base_col]) - int(r["On Hand"])), axis=1)
        ss.proj_df = tmp
        ss.show_df = tmp[["Product", header]]

        items = ss.show_df.values.tolist()
        ss.invoice_text = build_invoice_text(vendor, branch, items)
        wa_url = f"https://api.whatsapp.com/send?text={urllib.parse.quote(ss.invoice_text)}"

        st.dataframe(ss.show_df, use_container_width=True, height=table_height(len(ss.show_df)), hide_index=True)
        st.success(f"✅ Showing {header}")

        if ss.show_invoice:
            n_lines = ss.invoice_text.count("\n") + 1
            st.text_area("Invoice Preview", ss.invoice_text, height=min(600, 40 * n_lines))
            st.markdown(f"[📲 Send via WhatsApp]({wa_url})", unsafe_allow_html=True)
