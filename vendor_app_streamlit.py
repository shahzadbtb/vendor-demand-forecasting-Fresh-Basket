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
ss.setdefault("projection", None)          # "1" | "3" | "5"
ss.setdefault("proj_df", None)
ss.setdefault("show_df", None)
ss.setdefault("invoice_text", "")
ss.setdefault("show_upload", False)
ss.setdefault("show_invoice", False)

# ------------------------------
# GLOBAL CSS
# ------------------------------
st.markdown("""
<style>
.block-container { max-width: 800px; padding-top: .5rem; }

/* Hide header row ONLY for st.data_editor (Product data) */
div[data-testid="stDataEditor"] thead tr { display:none !important; }

/* Make editor columns compact on mobile */
div[data-testid="stDataEditor"] td:nth-child(1){ width:36% !important; } /* Product */
div[data-testid="stDataEditor"] td:nth-child(2){ width:10% !important; } /* On Hand */
div[data-testid="stDataEditor"] td:nth-child(3){ width:18% !important; } /* 1 Day */
div[data-testid="stDataEditor"] td:nth-child(4){ width:18% !important; } /* 3 Day */
div[data-testid="stDataEditor"] td:nth-child(5){ width:18% !important; } /* 5 Day */

/* Projection table */
div[data-testid="stDataFrame"] td:nth-child(1){ width:55% !important; }
div[data-testid="stDataFrame"] td:nth-child(2){
  width:45% !important; text-align:left !important;
}

/* General cell look */
div[data-testid="stDataFrame"] th, div[data-testid="stDataFrame"] td,
div[data-testid="stDataEditor"] th, div[data-testid="stDataEditor"] td {
  text-align:center !important;
  vertical-align:middle !important;
  font-size:13px !important;
  white-space:normal !important;
  word-break:break-word !important;
  padding:3px !important;
}

/* Textarea (invoice): no scroll */
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


# ---- FIXED FUNCTION (no f-string syntax error) ----
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
    btn.onclick=async () => {{
      try {{
        await navigator.clipboard.writeText(txt.value);
        const old=btn.innerText; btn.innerText="Copied!";
        setTimeout(() => btn.innerText=old,1200);
      }} catch(e) {{
        alert("Copy failed.");
      }}
    }};
    </script>
    """
    components.html(html, height=50)
# ---------------------------------------------------


def table_height(n_rows:int)->int:
    return 60 + n_rows * 42


def whatsapp_url_from_items(items:list[list], vendor:str, branch:str)->str:
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

    df = pd.DataFrame(rows, columns=["Product", "1 Day", "3 Day", "5 Day"])
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
            "3 Day": st.column_config.NumberColumn(format="%d", disabled=True),
            "5 Day": st.column_config.NumberColumn(format="%d", disabled=True),
        },
        disabled=["Product", "1 Day", "3 Day", "5 Day"],
    )

    st.divider()
    st.markdown("### 📊 Choose Projection")

    b1, b2, b3 = st.columns(3)
    with b1:
        if st.button("1 Day"):
            ss.projection = "1"; ss.show_invoice = False
    with b2:
        if st.button("3 Day"):
            ss.projection = "3"; ss.show_invoice = False
    with b3:
        if st.button("5 Day"):
            ss.projection = "5"; ss.show_invoice = False

    if ss.projection:
        base_col = {"1": "1 Day", "3": "3 Day", "5": "5 Day"}[ss.projection]
        header = {
            "1": "1 Day Projection",
            "3": "3 Day Projection",
            "5": "5 Day Projection"
        }[ss.projection]

        tmp = edited.fillna(0).copy()
        for c in ["1 Day", "3 Day", "5 Day", "On Hand"]:
            tmp[c] = tmp[c].apply(lambda x: int(x) if pd.notna(x) else 0)

        tmp[header] = tmp.apply(lambda r: max(0, int(r[base_col]) - int(r["On Hand"])), axis=1)
        ss.proj_df = tmp

        show = pd.DataFrame({
            "Product": tmp["Product"],
            header: tmp[header].astype(int)
        })
        show = show[show["Product"].notna() & (show["Product"].str.strip() != "")]
        ss.show_df = show

        items = show[["Product", header]].values.tolist()
        ss.invoice_text = build_invoice_text(vendor, branch, items)

        st.success(f"✅ Showing {header}")

        wa_row = st.columns([3, 1])
        with wa_row[1]:
            wa_url = f"https://api.whatsapp.com/send?text={urllib.parse.quote(ss.invoice_text)}"
            st.markdown(f"[📲 Send via WhatsApp]({wa_url})", unsafe_allow_html=True)

        st.dataframe(
            ss.show_df,
            use_container_width=True,
            height=table_height(len(ss.show_df)),
            hide_index=True
        )

        st.markdown("### 🧾 Invoice")
        top_left, top_right = st.columns([1, 1])
        with top_left:
            if st.button("💾 Save & Show Invoice"):
                ss.show_invoice = True
        with top_right:
            wa_url = f"https://api.whatsapp.com/send?text={urllib.parse.quote(ss.invoice_text)}"
            st.markdown(f"[📲 Send via WhatsApp]({wa_url})", unsafe_allow_html=True)

        if ss.show_invoice:
            n_lines = ss.invoice_text.count("\n") + 1
            st.text_area("Invoice Preview", ss.invoice_text, height=40 * n_lines, key="invoice_edit")

            bottom_left, bottom_right = st.columns(2)
            with bottom_left:
                wa_url = f"https://api.whatsapp.com/send?text={urllib.parse.quote(ss.invoice_text)}"
                st.markdown(f"[📲 Send via WhatsApp]({wa_url})", unsafe_allow_html=True)
            with bottom_right:
                copy_button("📋 Copy Invoice", ss.invoice_text, key="inv1")
import os
import json
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

# ------------------------------ CONFIG ------------------------------
st.set_page_config(page_title="Vendors Demand", page_icon="📦", layout="wide")

ss = st.session_state
ss.setdefault("vendor_data", {})
ss.setdefault("current_vendor", None)
ss.setdefault("current_branch", "Shahbaz")

# ------------------------------ CSS + JS ------------------------------
st.markdown("""
<style>
.block-container{ padding-top:1rem; }

/* compact title */
h1#vendors-demand-title{
  text-align:center; margin:4px 0 6px 0; font-size:1.36rem; font-weight:800;
}

/* projection buttons at bottom - prominent and separated */
.action-row{
  display:flex; justify-content:center; gap:25px; margin: 20px 0 10px;
  width: 100%;
}
.action-row button{
  background:#6c5ce7; color:#fff; border:none; border-radius:8px;
  padding:15px 35px; font-size:20px; font-weight:700; cursor:pointer;
  min-width: 100px;
}
.action-row button:hover{ background:#5548d9; }
.action-row button:active{ transform:translateY(1px); }

/* Excel-style table */
.excel-table { 
  width: 100%; 
  border-collapse: collapse; 
  margin: 10px 0;
  font-family: Arial, sans-serif;
  box-shadow: 0 1px 3px rgba(0,0,0,0.1);
}
.excel-table th {
  background-color: #f8f9fa;
  border: 1px solid #dee2e6;
  padding: 12px 8px;
  font-weight: bold;
  text-align: center;
  font-size: 14px;
}
.excel-table td {
  border: 1px solid #dee2e6;
  padding: 8px;
  text-align: left;
  font-size: 14px;
}
.excel-table tr:nth-child(even) {
  background-color: #f8f9fa;
}
.excel-table tr:hover {
  background-color: #e9ecef;
}

/* Product column */
.product-cell {
  padding: 8px 12px !important;
  font-weight: 500;
}

/* On-Hand input - Excel style */
.onhand-input {
  width: 100% !important;
  max-width: 120px !important;
  font-size: 14px !important;
  text-align: center !important;
  border: 2px solid #007bff !important;
  border-radius: 4px !important;
  padding: 6px 8px !important;
  background: white !important;
  font-family: Arial, sans-serif !important;
}
.onhand-input:focus {
  border-color: #0056b3 !important;
  outline: none !important;
  box-shadow: 0 0 0 2px rgba(0,123,255,0.25) !important;
}

/* Remove spinner buttons from number input */
.onhand-input::-webkit-outer-spin-button,
.onhand-input::-webkit-inner-spin-button {
  -webkit-appearance: none;
  margin: 0;
}
.onhand-input {
  -moz-appearance: textfield;
  -webkit-appearance: none;
  appearance: none;
}

/* Projection columns */
.projection-cell {
  text-align: center !important;
  font-weight: 600;
  background-color: #e7f3ff !important;
}

/* Responsive design */
@media (max-width: 768px) {
  .action-row {
    gap: 15px;
  }
  .action-row button {
    padding: 12px 25px;
    font-size: 18px;
    min-width: 80px;
  }
}
</style>

<script>
// Live calculation function
function liveUpdate(e){
  if(!e || !e.target) return;
  if(!e.target.classList.contains("onhand-input")) return;
  
  var idx = e.target.getAttribute("data-idx");
  var x = parseInt(e.target.value || "0"); 
  if(isNaN(x)) x = 0;

  var b1 = parseInt(e.target.getAttribute("data-day1") || "0"); 
  if(isNaN(b1)) b1 = 0;
  var b3 = parseInt(e.target.getAttribute("data-day3") || "0"); 
  if(isNaN(b3)) b3 = 0;
  var b5 = parseInt(e.target.getAttribute("data-day5") || "0"); 
  if(isNaN(b5)) b5 = 0;

  var p1 = Math.max(0, b1 - x);
  var p3 = Math.max(0, b3 - x);
  var p5 = Math.max(0, b5 - x);

  var c1 = document.getElementById("p1-"+idx);
  var c3 = document.getElementById("p3-"+idx);
  var c5 = document.getElementById("p5-"+idx);
  
  if(c1) c1.textContent = p1;
  if(c3) c3.textContent = p3;
  if(c5) c5.textContent = p5;
}

// Enhanced Excel-like keyboard navigation
function handleKeyNavigation(e) {
  if(!e.target.classList.contains("onhand-input")) return;
  
  var currentInput = e.target;
  var currentIndex = parseInt(currentInput.getAttribute("data-idx"));
  var allInputs = Array.from(document.querySelectorAll('.onhand-input'));
  var totalInputs = allInputs.length;
  
  if (e.key === 'Enter' || e.key === 'ArrowDown') {
    e.preventDefault();
    var nextIndex = (currentIndex + 1);
    if (nextIndex < totalInputs) {
      allInputs[nextIndex].focus();
      allInputs[nextIndex].select();
    }
  } else if (e.key === 'ArrowUp') {
    e.preventDefault();
    var prevIndex = (currentIndex - 1);
    if (prevIndex >= 0) {
      allInputs[prevIndex].focus();
      allInputs[prevIndex].select();
    }
  } else if (e.key === 'Tab') {
    e.preventDefault();
    if (e.shiftKey) {
      // Shift+Tab - move up/left
      var prevIndex = (currentIndex - 1);
      if (prevIndex >= 0) {
        allInputs[prevIndex].focus();
        allInputs[prevIndex].select();
      }
    } else {
      // Tab - move down/right
      var nextIndex = (currentIndex + 1);
      if (nextIndex < totalInputs) {
        allInputs[nextIndex].focus();
        allInputs[nextIndex].select();
      }
    }
  }
}

// Initialize event listeners
function initEventListeners() {
  document.addEventListener("input", liveUpdate, true);
  document.addEventListener("keyup", liveUpdate, true);
  document.addEventListener("change", liveUpdate, true);
  document.addEventListener("keydown", handleKeyNavigation, true);
}

// Initialize when page loads
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initEventListeners);
} else {
  initEventListeners();
}
</script>
""", unsafe_allow_html=True)

# ------------------------------ HELPERS ------------------------------
@st.cache_data
def parse_excel(uploaded_file) -> dict:
    """
    Expect each sheet: A=Product, B=1 Day, C=3 Day, D=5 Day (integers).
    """
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
                try: return int(round(float(v)))
                except: return 0
            rows.append([name, num(r.iloc[1]), num(r.iloc[2]), num(r.iloc[3])])
        if rows:
            data[sheet] = rows
    return data

def component_table(rows, vendor: str, branch: str):
    """
    Excel-style table with prominent buttons at bottom
    """
    trs = []
    for i, (prod, d1, d3, d5) in enumerate(rows):
        trs.append(
            '<tr>'
            f'<td class="product-cell">{prod}</td>'
            f'<td style="text-align: center;">'
            f'<input class="onhand-input" type="number" inputmode="numeric" placeholder="0" '
            f'data-idx="{i}" data-day1="{d1}" data-day3="{d3}" data-day5="{d5}">'
            f'</td>'
            f'<td class="projection-cell" id="p1-{i}">{d1}</td>'
            f'<td class="projection-cell" id="p3-{i}">{d3}</td>'
            f'<td class="projection-cell" id="p5-{i}">{d5}</td>'
            '</tr>'
        )
    body = "".join(trs)

    vendor_js = json.dumps(vendor or "")
    branch_js = json.dumps(branch or "")

    html = f"""
        <!-- Excel-style table -->
        <div style="overflow-x: auto;">
            <table class="excel-table">
                <thead>
                    <tr>
                        <th style="width: 60%;">Product</th>
                        <th style="width: 10%;">On Hand</th>
                        <th style="width: 10%;">1 Day</th>
                        <th style="width: 10%;">3 Day</th>
                        <th style="width: 10%;">5 Day</th>
                    </tr>
                </thead>
                <tbody>
                    {body}
                </tbody>
            </table>
        </div>

        <!-- Prominent buttons at bottom -->
        <div class="action-row">
            <button onclick="sendWA(1)">1D</button>
            <button onclick="sendWA(3)">3D</button>
            <button onclick="sendWA(5)">5D</button>
        </div>

        <!-- WhatsApp functionality -->
        <script>
        var VENDOR = {vendor_js};
        var BRANCH = {branch_js};
        
        function nowString(){{
            var d = new Date();
            function pad(n){{ return ("0" + n).slice(-2); }}
            return d.getFullYear() + "-" + pad(d.getMonth()+1) + "-" + pad(d.getDate()) + " " +
                   pad(d.getHours()) + ":" + pad(d.getMinutes()) + ":" + pad(d.getSeconds());
        }}
        
        function buildInvoice(period){{
            var pref = (period === 1) ? "p1-" : (period === 3) ? "p3-" : "p5-";
            var trs = document.querySelectorAll(".excel-table tbody tr");
            var lines = [];
            
            lines.push("🏪 *Vendor Demand Invoice*");
            lines.push("👤 *Vendor:* " + VENDOR);
            lines.push("🏬 *Branch:* " + BRANCH);
            lines.push("📊 *Projection:* " + period + " Day");
            lines.push("📅 *Date:* " + nowString());
            lines.push("");
            lines.push("📦 *ITEMS:*");
            
            var totalQty = 0, totalItems = 0;
            for(var i = 0; i < trs.length; i++){{
                var prod = trs[i].querySelector(".product-cell");
                var qtyC = document.getElementById(pref + i);
                if(!prod || !qtyC) continue;
                
                var name = (prod.textContent || "").trim();
                var qty = parseInt(qtyC.textContent || "0"); 
                if(isNaN(qty)) qty = 0;
                
                if(qty > 0){{
                    totalQty += qty; 
                    totalItems += 1; 
                    lines.push("• " + name + ": " + qty);
                }}
            }}
            
            lines.push("");
            lines.push("📋 *TOTAL ITEMS:* " + totalItems);
            lines.push("📦 *TOTAL QTY:* " + totalQty);
            lines.push("");
            lines.push("Thank you! 🚀");
            
            return lines.join("\\n");
        }}
        
        function sendWA(period){{
            var text = buildInvoice(period);
            var url = "https://api.whatsapp.com/send?text=" + encodeURIComponent(text);
            window.open(url, '_blank');
        }}
        
        // Initialize event listeners
        document.addEventListener('DOMContentLoaded', function() {{
            document.addEventListener("input", liveUpdate, true);
            document.addEventListener("keyup", liveUpdate, true);
            document.addEventListener("change", liveUpdate, true);
            document.addEventListener("keydown", handleKeyNavigation, true);
        }});
        </script>
    """

    # Calculate height based on rows
    height = 250 + len(rows) * 50
    components.html(html, height=height, scrolling=False)

# ------------------------------ UI ------------------------------
st.markdown('<h1 id="vendors-demand-title">Vendors Demand</h1>', unsafe_allow_html=True)

# 1) VENDOR & BRANCH SELECTION (top)
if ss.vendor_data:
    vendors = list(ss.vendor_data.keys())
    col1, col2 = st.columns(2)
    
    with col1:
        new_vendor = st.selectbox(
            "🔍 Select Vendor", 
            vendors, 
            index=vendors.index(ss.current_vendor) if ss.current_vendor in vendors else 0,
            key="vendor_select_top"
        )
        if new_vendor != ss.current_vendor:
            ss.current_vendor = new_vendor
            st.rerun()
    
    with col2:
        new_branch = st.selectbox(
            "🏬 Select Branch",
            ["Shahbaz", "Clifton", "Badar", "DHA Ecom", "BHD Ecom", "BHD", "Head Office"],
            index=["Shahbaz", "Clifton", "Badar", "DHA Ecom", "BHD Ecom", "BHD", "Head Office"].index(ss.current_branch),
            key="branch_select_top"
        )
        if new_branch != ss.current_branch:
            ss.current_branch = new_branch
            st.rerun()

# 2) UPLOAD (first time)
if not ss.vendor_data:
    uploaded = st.file_uploader("📤 Upload Excel File", type=["xlsx", "xls"])
    if uploaded:
        ss.vendor_data = parse_excel(uploaded)
        ss.current_vendor = list(ss.vendor_data.keys())[0]
        st.rerun()

# 3) WHEN DATA EXISTS — render Excel-style table
if ss.vendor_data:
    if ss.current_vendor is None or ss.current_vendor not in ss.vendor_data:
        ss.current_vendor = list(ss.vendor_data.keys())[0]
    rows = ss.vendor_data[ss.current_vendor]
    component_table(rows, ss.current_vendor, ss.current_branch)

# 4) Status and re-upload option
if ss.vendor_data:
    st.success(f"✅ Loaded vendor: {ss.current_vendor} | Branch: {ss.current_branch}")
    
    if st.button("🔄 Upload New Excel File", type="secondary"):
        ss.vendor_data = {}
        ss.current_vendor = None
        st.rerun()