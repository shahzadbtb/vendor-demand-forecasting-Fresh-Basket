import os
import json
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
from io import BytesIO
import urllib.parse

# ------------------------------ CONFIG ------------------------------
st.set_page_config(page_title="Vendors Demand", page_icon="📦", layout="wide")

# Initialize session state
if 'vendor_data' not in st.session_state:
    st.session_state.vendor_data = {}
if 'current_vendor' not in st.session_state:
    st.session_state.current_vendor = None
if 'current_branch' not in st.session_state:
    st.session_state.current_branch = "Shahbaz"
if 'component_loaded' not in st.session_state:
    st.session_state.component_loaded = False
if 'onhand_values' not in st.session_state:
    st.session_state.onhand_values = {}
if 'projection_days' not in st.session_state:
    st.session_state.projection_days = 1

# ------------------------------ CSS (GLOBAL) ------------------------------
st.markdown("""
<style>
.block-container{ padding-top:1rem; }

/* compact title */
h1#vendors-demand-title{
  text-align:center; margin:4px 0 6px 0; font-size:1.36rem; font-weight:800;
}

/* Footer styling */
.footer {
    text-align: center;
    font-size: 0.8rem;
    color: #666;
    margin-top: 2rem;
    padding: 1rem;
    border-top: 1px solid #e0e0e0;
}

/* Prevent unnecessary reruns */
.stApp {
    overflow: visible !important;
}

/* Sticky header for controls */
.sticky-header {
    position: sticky;
    top: 0;
    background: white;
    z-index: 999;
    padding: 1rem 0;
    margin: -1rem 0 1rem 0;
    border-bottom: 1px solid #e0e0e0;
}

/* Button styling */
.custom-button {
    border: none;
    padding: 8px 14px;
    border-radius: 6px;
    font-size: 13px;
    cursor: pointer;
    font-weight: 600;
    display: inline-flex;
    align-items: center;
    gap: 4px;
    width: 100%;
    justify-content: center;
    margin: 2px 0;
    text-decoration: none;
    color: white !important;
}
.wa-button {
    background: #25D366;
    color: #fff;
}
.wa-button:hover {
    background: #128C7E;
    color: white !important;
}
.csv-button {
    background: #007bff;
    color: #fff;
}
.csv-button:hover {
    background: #0056b3;
}
.clear-button {
    background: #6c757d;
    color: #fff;
}
.clear-button:hover {
    background: #5a6268;
}

/* Remove default Streamlit button styling */
.stDownloadButton > button {
    width: 100% !important;
}
</style>
""", unsafe_allow_html=True)

# ------------------------------ HELPERS ------------------------------
@st.cache_data
def parse_excel(uploaded_file) -> dict:
    """
    Expect each sheet: A=Product, B=1 Day, C=3 Day, D=5 Day (integers).
    We'll use the 1 Day column as base demand.
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
                try:
                    return int(round(float(v)))
                except:
                    return 0

            # Use 1 Day column as base demand
            base_demand = num(r.iloc[1])
            rows.append([name, base_demand])
        if rows:
            data[sheet] = rows
    return data

def component_table(rows, vendor: str, branch: str):
    """
    Excel-style table only - buttons moved outside
    """
    # Build table rows HTML with saved onhand values
    trs = []
    for i, (prod, base_demand) in enumerate(rows):
        # Get saved onhand value from session state - default to empty
        saved_value = st.session_state.onhand_values.get(f"{vendor}_{i}", "")
        
        # Calculate initial projection based on saved onhand value
        if saved_value and saved_value != "":
            try:
                onhand_val = int(saved_value)
                current_projection = max(0, (base_demand * st.session_state.projection_days) - onhand_val)
            except:
                current_projection = max(0, base_demand * st.session_state.projection_days)
        else:
            current_projection = max(0, base_demand * st.session_state.projection_days)

        trs.append(
            '<tr>'
            f'<td class="product-cell col-product">{prod}</td>'
            f'<td style="text-align: center;" class="col-onhand">'
            f'<input class="onhand-input" type="number" inputmode="numeric" placeholder="0" '
            f'value="{saved_value}" data-idx="{i}" data-basedemand="{base_demand}" data-product="{prod}">'
            f'</td>'
            f'<td class="projection-cell col-projection" id="projection-{i}" style="text-align: center;">{current_projection}</td>'
            '</tr>'
        )
    body = "".join(trs)

    vendor_js = json.dumps(vendor or "")
    branch_js = json.dumps(branch or "")
    days_js = json.dumps(st.session_state.projection_days)

    html = f"""
    <style>
    .vd-container {{
        margin-top: 10px;
        font-family: Arial, sans-serif;
    }}

    /* Removed scroll from table wrapper */
    .table-wrapper {{
        border: 1px solid #dee2e6;
        border-radius: 8px;
    }}

    /* Excel-style table */
    .excel-table {{
        width: 100%;
        border-collapse: collapse;
        table-layout: fixed;
        font-family: Arial, sans-serif;
        font-size: 13px;
    }}
    .excel-table th {{
        background-color: #f8f9fa;
        border: 1px solid #dee2e6;
        padding: 8px 4px;
        font-weight: bold;
        text-align: center;
    }}
    .excel-table td {{
        border: 1px solid #dee2e6;
        padding: 6px 4px;
        text-align: left;
    }}
    .excel-table tr:nth-child(even) {{
        background-color: #f8f9fa;
    }}
    .excel-table tr:hover {{
        background-color: #e9ecef;
    }}

    /* Column widths */
    .col-product {{
        width: 75%;
    }}
    .col-onhand {{
        width: 10%;
        text-align: center;
    }}
    .col-projection {{
        width: 15%;
        text-align: center;
    }}

    /* Product column wider */
    .product-cell {{
        padding: 6px 8px;
        font-weight: 500;
    }}

    /* On-Hand input: ~half inch width */
    .onhand-input {{
        width: 45px;
        max-width: 45px;
        font-size: 13px;
        text-align: center;
        border: 1px solid #007bff;
        border-radius: 4px;
        padding: 4px 2px;
        background: white;
        font-family: Arial, sans-serif;
    }}
    .onhand-input:focus {{
        outline: none;
        border-color: #0056b3;
        box-shadow: 0 0 0 2px rgba(0,123,255,0.25);
    }}

    .onhand-input::-webkit-outer-spin-button,
    .onhand-input::-webkit-inner-spin-button {{
        -webkit-appearance: none;
        margin: 0;
    }}
    .onhand-input {{
        -moz-appearance: textfield;
        -webkit-appearance: none;
        appearance: none;
    }}

    .projection-cell {{
        text-align: center;
        font-weight: 600;
        background-color: #e7f3ff;
    }}
    </style>

    <div class="vd-container">
        <div class="table-wrapper">
            <table class="excel-table">
                <colgroup>
                    <col class="col-product">
                    <col class="col-onhand">
                    <col class="col-projection">
                </colgroup>
                <thead>
                    <tr>
                        <th class="col-product">Product</th>
                        <th class="col-onhand">On Hand</th>
                        <th class="col-projection">Projection</th>
                    </tr>
                </thead>
                <tbody>
                    {body}
                </tbody>
            </table>
        </div>
    </div>

    <script>
    (function() {{
        const VENDOR = {vendor_js};
        const BRANCH = {branch_js};
        const CURRENT_DAYS = {days_js};

        function getDays() {{
            return CURRENT_DAYS;
        }}

        function recalcRow(input) {{
            if (!input) return;
            const idx = input.getAttribute('data-idx');
            let baseDemand = parseInt(input.getAttribute('data-basedemand') || "0");
            if (isNaN(baseDemand)) baseDemand = 0;
            const days = getDays();
            let onHand = parseInt(input.value || "0");
            if (isNaN(onHand)) onHand = 0;

            // PROJECTION = (baseDemand * days) - onHand
            const projected = Math.max(0, (baseDemand * days) - onHand);

            const cell = document.getElementById('projection-' + idx);
            if (cell) cell.textContent = projected;
        }}

        function recalcAll() {{
            document.querySelectorAll('.onhand-input').forEach(inp => recalcRow(inp));
        }}

        // Live recalc on input
        document.addEventListener('input', function(e) {{
            if (e.target && e.target.classList.contains('onhand-input')) {{
                recalcRow(e.target);
                // Save the value to prevent loss during rerun
                const idx = e.target.getAttribute('data-idx');
                const value = e.target.value;
                const product = e.target.getAttribute('data-product');
                
                // Store in session storage as backup
                sessionStorage.setItem(`onhand_${{VENDOR}}_${{idx}}`, value);
            }}
        }});

        // Excel-like keyboard navigation
        document.addEventListener('keydown', function(e) {{
            const target = e.target;
            if (!target || !target.classList.contains('onhand-input')) return;

            const inputs = Array.from(document.querySelectorAll('.onhand-input'));
            const idx = inputs.indexOf(target);
            if (idx === -1) return;

            let next = null;
            if (e.key === 'Enter' || e.key === 'ArrowDown') {{
                e.preventDefault();
                next = inputs[idx + 1];
            }} else if (e.key === 'ArrowUp') {{
                e.preventDefault();
                next = inputs[idx - 1];
            }} else if (e.key === 'Tab') {{
                e.preventDefault();
                next = e.shiftKey ? inputs[idx - 1] : inputs[idx + 1];
            }}
            if (next) {{
                next.focus();
                if (next.select) next.select();
            }}
        }});

        function getExportRows() {{
            const days = getDays();
            const rows = [];
            const trs = document.querySelectorAll('.excel-table tbody tr');
            trs.forEach(tr => {{
                const prodCell = tr.querySelector('.product-cell');
                const input = tr.querySelector('.onhand-input');
                const projectionCell = tr.querySelector('.projection-cell');
                
                if (!prodCell || !input) return;

                const name = (prodCell.textContent || '').trim();
                
                // Use the ACTUAL PROJECTION VALUE from the projection cell, not recalculating
                let projected = 0;
                if (projectionCell) {{
                    projected = parseInt(projectionCell.textContent || "0");
                    if (isNaN(projected)) projected = 0;
                }}

                // Include ALL products even if projected quantity is 0
                rows.push({{ name: name, qty: projected }});
            }});
            return rows;
        }}

        // Clear On Hand function - clears both display and session storage
        window.clearOnHand = function() {{
            document.querySelectorAll('.onhand-input').forEach(inp => {{
                inp.value = "";
                const idx = inp.getAttribute('data-idx');
                sessionStorage.setItem(`onhand_${{VENDOR}}_${{idx}}`, "");
                recalcRow(inp);
            }});
        }};

        // Expose getExportRows to window for external access
        window.getExportRows = getExportRows;

        // Restore values from session storage on load
        document.addEventListener('DOMContentLoaded', function() {{
            document.querySelectorAll('.onhand-input').forEach(inp => {{
                const idx = inp.getAttribute('data-idx');
                const saved = sessionStorage.getItem(`onhand_${{VENDOR}}_${{idx}}`);
                if (saved !== null) {{
                    inp.value = saved;
                }}
                recalcRow(inp);
            }});
        }});

        // Initial recalculation
        recalcAll();
    }})();
    </script>
    """

    # Height for component
    height = 120 + len(rows) * 30
    components.html(html, height=height, scrolling=False)

def export_to_whatsapp(rows, vendor, branch, days):
    """Export data to WhatsApp format"""
    lines = []
    lines.append("🏪 *Vendor Demand Invoice*")
    lines.append("👤 *Vendor:* " + (vendor or ""))
    lines.append("🏬 *Branch:* " + (branch or ""))
    lines.append("📊 *Projection:* " + str(days) + " Day" + ("s" if days > 1 else ""))
    lines.append("📅 *Date:* " + pd.Timestamp.now().strftime("%Y-%m-%d %H:%M"))
    lines.append("")
    lines.append("📦 *ITEMS:*")

    total_qty = 0
    for row in rows:
        total_qty += row['qty']
        if row['qty'] > 0:  # Only include items with quantity > 0
            lines.append("• " + row['name'] + ": " + str(row['qty']))

    lines.append("")
    lines.append("📋 *TOTAL ITEMS:* " + str(len([r for r in rows if r['qty'] > 0])))
    lines.append("📦 *TOTAL QTY:* " + str(total_qty))
    lines.append("")
    lines.append("Thank you! 🚀")

    text = "\n".join(lines)
    return text

def export_to_csv(rows, vendor, days):
    """Export data to CSV format"""
    import csv
    from io import StringIO
    
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(["Product", "Projected Qty"])
    
    for row in rows:
        if row['qty'] > 0:  # Only include items with quantity > 0
            writer.writerow([row['name'], row['qty']])
    
    csv_content = output.getvalue()
    output.close()
    return csv_content

def get_whatsapp_url(text):
    """Create WhatsApp URL with encoded text"""
    encoded_text = urllib.parse.quote(text)
    return f"https://api.whatsapp.com/send?text={encoded_text}"

def get_export_data_from_table():
    """Get export data directly from the table using JavaScript"""
    js_code = """
    <script>
    if (typeof getExportRows === 'function') {
        const rows = getExportRows();
        // Send data back to Streamlit
        window.parent.postMessage({
            type: 'EXPORT_DATA',
            data: rows
        }, '*');
    }
    </script>
    """
    
    # We'll use a different approach - get data from session state
    return None

def get_export_data(vendor, projection_days):
    """Get export data for current vendor - FIXED VERSION"""
    rows = st.session_state.vendor_data[vendor]
    export_data = []
    for i, (prod, base_demand) in enumerate(rows):
        saved_value = st.session_state.onhand_values.get(f"{vendor}_{i}", "")
        onhand_val = int(saved_value) if saved_value and saved_value != "" else 0
        # CORRECT CALCULATION: (base_demand * days) - onhand_val
        projected = max(0, (base_demand * projection_days) - onhand_val)
        export_data.append({'name': prod, 'qty': projected})
    return export_data

# ------------------------------ MAIN UI ------------------------------

# Always show the title
st.markdown('<h1 id="vendors-demand-title">Vendors Demand</h1>', unsafe_allow_html=True)

# Create containers for better organization
header_container = st.container()
upload_container = st.container()
controls_container = st.container()
table_container = st.container()
status_container = st.container()

with header_container:
    # 1) VENDOR & BRANCH SELECTION (top)
    if st.session_state.vendor_data:
        vendors = list(st.session_state.vendor_data.keys())
        col1, col2 = st.columns(2)

        with col1:
            new_vendor = st.selectbox(
                "🔍 Select Vendor",
                vendors,
                index=vendors.index(st.session_state.current_vendor) if st.session_state.current_vendor in vendors else 0,
                key="vendor_select_top"
            )
            if new_vendor != st.session_state.current_vendor:
                st.session_state.current_vendor = new_vendor

        with col2:
            new_branch = st.selectbox(
                "🏬 Select Branch",
                ["Shahbaz", "Clifton", "Badar", "DHA Ecom", "BHD Ecom", "BHD", "Head Office"],
                index=["Shahbaz", "Clifton", "Badar", "DHA Ecom", "BHD Ecom", "BHD", "Head Office"].index(
                    st.session_state.current_branch
                ),
                key="branch_select_top"
            )
            if new_branch != st.session_state.current_branch:
                st.session_state.current_branch = new_branch

with upload_container:
    # 2) UPLOAD (first time)
    if not st.session_state.vendor_data:
        uploaded = st.file_uploader("📤 Upload Excel File", type=["xlsx", "xls"])
        if uploaded:
            st.session_state.vendor_data = parse_excel(uploaded)
            st.session_state.current_vendor = list(st.session_state.vendor_data.keys())[0]
            # Clear any existing onhand values when new file is uploaded
            st.session_state.onhand_values = {}
            st.rerun()

# Sticky controls section
st.markdown('<div class="sticky-header">', unsafe_allow_html=True)
with controls_container:
    # 3) CONTROLS (Projection Days and Buttons) - ALWAYS VISIBLE
    if st.session_state.vendor_data:
        col1, col2, col3, col4 = st.columns([1.2, 1, 1, 1])
        
        with col1:
            st.session_state.projection_days = st.selectbox(
                "📅 Projection Days",
                [1, 2, 3, 4, 5, 6, 7],
                index=[1, 2, 3, 4, 5, 6, 7].index(st.session_state.projection_days),
                key="days_select"
            )
        
        with col2:
            # WhatsApp Export Button
            if st.session_state.vendor_data:
                # Use the CORRECT calculation for export data
                export_data = get_export_data(st.session_state.current_vendor, st.session_state.projection_days)
                text = export_to_whatsapp(export_data, st.session_state.current_vendor, st.session_state.current_branch, st.session_state.projection_days)
                whatsapp_url = get_whatsapp_url(text)
                
                st.markdown(
                    f'<a href="{whatsapp_url}" target="_blank" class="custom-button wa-button">📱 Export to WhatsApp</a>',
                    unsafe_allow_html=True
                )
        
        with col3:
            # CSV Export Button
            if st.session_state.vendor_data:
                # Use the CORRECT calculation for export data
                export_data = get_export_data(st.session_state.current_vendor, st.session_state.projection_days)
                csv_content = export_to_csv(export_data, st.session_state.current_vendor, st.session_state.projection_days)
                safe_vendor = str(st.session_state.current_vendor or "vendor").replace('/', '_').replace('\\', '_')
                
                st.download_button(
                    label="📥 Export to Excel (CSV)",
                    data=csv_content,
                    file_name=f"demand_{st.session_state.projection_days}D_{safe_vendor}.csv",
                    mime="text/csv",
                    key="download_csv",
                    use_container_width=True
                )
        
        with col4:
            # Clear On Hand Button - This will clear the values immediately
            if st.button("🗑️ Clear On Hand", key="clear_btn", use_container_width=True, type="secondary"):
                # Clear all onhand values for current vendor from session state
                vendor_key = st.session_state.current_vendor
                for i in range(len(st.session_state.vendor_data[vendor_key])):
                    st.session_state.onhand_values[f"{vendor_key}_{i}"] = ""
                
                # Also clear from session storage using JavaScript
                js_code = f"""
                <script>
                if (typeof clearOnHand === 'function') {{
                    clearOnHand();
                }}
                // Also clear session storage
                const vendor = "{vendor_key}";
                const inputs = document.querySelectorAll('.onhand-input');
                inputs.forEach(inp => {{
                    const idx = inp.getAttribute('data-idx');
                    sessionStorage.setItem(`onhand_${{vendor}}_${{idx}}`, "");
                    inp.value = "";
                    // Trigger recalculation
                    const baseDemand = parseInt(inp.getAttribute('data-basedemand') || "0");
                    const days = {st.session_state.projection_days};
                    const projected = Math.max(0, (baseDemand * days));
                    const cell = document.getElementById('projection-' + idx);
                    if (cell) cell.textContent = projected;
                }});
                </script>
                """
                components.html(js_code, height=0)
                
                # Show success message
                st.success("On Hand values cleared successfully!")
                # Rerun to refresh the display
                st.rerun()

st.markdown('</div>', unsafe_allow_html=True)

with table_container:
    # 4) TABLE ONLY - buttons are now outside
    if st.session_state.vendor_data:
        if st.session_state.current_vendor is None or st.session_state.current_vendor not in st.session_state.vendor_data:
            st.session_state.current_vendor = list(st.session_state.vendor_data.keys())[0]
        
        rows = st.session_state.vendor_data[st.session_state.current_vendor]
        component_table(rows, st.session_state.current_vendor, st.session_state.current_branch)

with status_container:
    if st.session_state.vendor_data:
        st.success(f"✅ Vendor: {st.session_state.current_vendor} | Branch: {st.session_state.current_branch} | Days: {st.session_state.projection_days}")

# ------------------------------ FOOTER ------------------------------
st.markdown(
    """
    <div class="footer">
        Software Developed by M Shahzad | Contact: 0345-2227512
    </div>
    """,
    unsafe_allow_html=True
)