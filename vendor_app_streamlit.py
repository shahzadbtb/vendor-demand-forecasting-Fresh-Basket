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
    layout="centered",
)

# ------------------------------
# STATE
# ------------------------------
ss = st.session_state
ss.setdefault("vendor_data", {})
ss.setdefault("current_vendor", None)
ss.setdefault("projection", None)          # "1" | "2" | "5"
ss.setdefault("proj_df", None)             # full dataframe with computed projection column
ss.setdefault("show_df", None)             # ONLY [Product, <Projection>] in correct order
ss.setdefault("invoice_text", "")
ss.setdefault("show_upload", False)
ss.setdefault("show_invoice", False)

# ------------------------------
# GLOBAL CSS (mobile-first, no header for editor, narrow columns)
# ------------------------------
st.markdown("""
<style>
.block-container { max-width: 800px; padding-top: .5rem; }

/* Hide the header row ONLY for st.data_editor (Product data) */
div[data-testid="stDataEditor"] thead tr { display:none !important; }

/* Make the editor columns very compact on mobile */
div[data-testid="stDataEditor"] td:nth-child(1){ width:36% !important; } /* Product */
div[data-testid="stDataEditor"] td:nth-child(2){ width:10% !important; } /* On Hand */
div[data-testid="stDataEditor"] td:nth-child(3){ width:18% !important; } /* 1 Day */
div[data-testid="stDataEditor"] td:nth-child(4){ width:18% !important; } /* 2 Days */
div[data-testid="stDataEditor"] td:nth-child(5){ width:18% !important; } /* 5 Days */

/* Projection table: Product left, Projection right, tight fit, left-align numbers */
div[data-testid="stDataFrame"] td:nth-child(1){ width:55% !important; }
div[data-testid="stDataFrame"] td:nth-child(2){
  width:45% !important; text-align:left !important;
}

/* General cell look (both tables) */
div[data-testid="stDataFrame"] th, div[data-testid="stDataFrame"] td,
div[data-testid="stDataEditor"] th, div[data-testid="stDataEditor"] td {
  text-align:center !important;
  vertical-align:middle !important;
  font-size:13px !important;
  white-space:normal !important;
  word-break:break-word !important;
  padding:3px !important;
}

/* Textarea (invoice): no internal scroll, auto-height feel */
textarea{
  width:100% !important; font-size:18px !important; font-weight:500 !important;
  line-height:1.5 !important; padding:10px !important; resize:none !important;
  overflow:hidden !important;
}
</style>
""", unsafe_allow_html=True)

# ------------------------------
# HELPERS
# ------------------------------
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
                try:
                    return int(float(v))
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
    safe = (text_to_copy.replace("&", "&amp;")
                        .replace("<", "&lt;")
                        .replace(">", "&gt;"))
    html = f"""
    <div>
      <button id="btn-{key}" style="
        background:#6c5ce7;color:#fff;border:none;border-radius:8px;
        padding:10px 16px;cursor:pointer;font-weight:700;">{label}</button>
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
    components.html(html, height=50)


def table_height(n_rows:int)->int:
    # Tall enough to avoid internal scrolling
    return 60 + n_rows * 42


def whatsapp_url_from_items(items:list[list], vendor:str, branch:str)->str:
    """
    All 'Send via WhatsApp' buttons must use *the same* text built from the
    CURRENT projection table (Product, Projection>0).
    Use api.whatsapp.com to prefer regular WhatsApp over Business.
    """
    text = build_invoice_text(vendor, branch, items)
    return f"https://api.whatsapp.com/send?text={urllib.parse.quote(text)}"


# ------------------------------
# HEADER
# ------------------------------
col1, col2 = st.columns([1, 6])
with col1:
    logo_candidates = ["fresh_basket_logo.png", "fresh basket logo.jfif"]
    logo_path = next((p for p in logo_candidates if os.path.exists(p)), None)
    if logo_path:
        st.image(logo_path, width=160)
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
    up1, up2 = st.columns([1, 1])
    with up1:
        st.success(f"✅ Current dataset loaded: **{len(ss.vendor_data)} vendors**")
    with up2:
        if st.button("📤 Upload New Excel File"):
            ss.show_upload = True

    if ss.show_upload:
        new_file = st.file_uploader("Upload New Excel File", type=["xlsx", "xls"], key="replace_upload")
        if new_file:
            ss.vendor_data = parse_excel(new_file)
            ss.current_vendor = None
            ss.projection = None
            ss.proj_df = None
            ss.show_df = None
            ss.invoice_text = ""
            ss.show_invoice = False
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

    # Build editor dataframe
    df = pd.DataFrame(rows, columns=["Product", "1 Day", "2 Days", "5 Days"])
    df = df[df["Product"].notna() & (df["Product"].str.strip() != "")]
    df.insert(1, "On Hand", 0)

    st.markdown("### 📋 Product Data (enter On Hand only)")
    edited = st.data_editor(
        df,
        use_container_width=True,
        hide_index=True,
        height=table_height(len(df)),
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

    # --- Projection buttons (row) ---
    b1, b2, b3 = st.columns(3)
    with b1:
        if st.button("1 Day"):
            ss.projection = "1"
            ss.show_invoice = False
    with b2:
        if st.button("2 Days"):
            ss.projection = "2"
            ss.show_invoice = False
    with b3:
        if st.button("5 Days"):
            ss.projection = "5"
            ss.show_invoice = False

    # --- Compute projection, show table, and prep WhatsApp text ---
    if ss.projection:
        base_col = {"1": "1 Day", "2": "2 Days", "5": "5 Days"}[ss.projection]
        header = {"1": "1 Day Projection", "2": "2 Days Projection", "5": "5 Days Projection"}[ss.projection]

        tmp = edited.fillna(0).copy()
        for c in ["1 Day", "2 Days", "5 Days", "On Hand"]:
            tmp[c] = tmp[c].apply(lambda x: int(x) if pd.notna(x) else 0)

        # Projection math (non-negative)
        tmp[header] = tmp.apply(lambda r: max(0, int(r[base_col]) - int(r["On Hand"])), axis=1)
        ss.proj_df = tmp

        # Build *ordered* view: [Product, Projection]
        show = pd.DataFrame({
            "Product": tmp["Product"],
            header: tmp[header].astype(int)
        })
        # drop blanks; keep order fixed
        show = show[show["Product"].notna() & (show["Product"].str.strip() != "")]
        ss.show_df = show

        # Build shared WhatsApp text from CURRENT projection table (>0 only)
        use = show[show[header] > 0][["Product", header]]
        items = use.values.tolist()
        ss.invoice_text = build_invoice_text(vendor, branch, items)

        st.success(f"✅ Showing {header}")

        # Small row with WhatsApp link (always same text as other buttons)
        wa_row = st.columns([3, 1])
        with wa_row[1]:
            wa_url = f"https://api.whatsapp.com/send?text={urllib.parse.quote(ss.invoice_text)}"
            st.markdown(f"[📲 Send via WhatsApp]({wa_url})", unsafe_allow_html=True)

        # Projection table (no scroll)
        st.dataframe(
            ss.show_df,
            use_container_width=True,
            height=table_height(len(ss.show_df)),
            hide_index=True
        )

        # ---------------- INVOICE AREA ----------------
        st.markdown("### 🧾 Invoice")

        top_left, top_right = st.columns([1, 1])
        with top_left:
            if st.button("💾 Save & Show Invoice"):
                ss.show_invoice = True
        with top_right:
            wa_url = f"https://api.whatsapp.com/send?text={urllib.parse.quote(ss.invoice_text)}"
            st.markdown(f"[📲 Send via WhatsApp]({wa_url})", unsafe_allow_html=True)

        if ss.show_invoice:
            # Full invoice (no internal scroll)
            n_lines = ss.invoice_text.count("\n") + 1
            st.text_area("Invoice Preview", ss.invoice_text, height=40 * n_lines, key="invoice_edit")

            bottom_left, bottom_right = st.columns(2)
            with bottom_left:
                wa_url = f"https://api.whatsapp.com/send?text={urllib.parse.quote(ss.invoice_text)}"
                st.markdown(f"[📲 Send via WhatsApp]({wa_url})", unsafe_allow_html=True)
            with bottom_right:
                copy_button("📋 Copy Invoice", ss.invoice_text, key="inv1")
