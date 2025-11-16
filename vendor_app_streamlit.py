import os
import json
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
from io import BytesIO

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
    Excel-style table + Days dropdown + WhatsApp + CSV export.
    All logic is inside one HTML component so JS works 100%.
    """

    # Build table rows HTML with saved onhand values
    trs = []
    for i, (prod, base_demand) in enumerate(rows):
        # Get saved onhand value from session state
        saved_value = st.session_state.onhand_values.get(f"{vendor}_{i}", "")
        
        # Calculate initial projection based on saved onhand value
        if saved_value and saved_value != "":
            try:
                onhand_val = int(saved_value)
                current_projection = max(0, base_demand - onhand_val)
            except:
                current_projection = max(0, base_demand)
        else:
            current_projection = max(0, base_demand)

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

    html = f"""
    <style>
    .vd-container {{
        margin-top: 10px;
        font-family: Arial, sans-serif;
    }}
    .vd-button-bar {{
        display: flex;
        flex-wrap: wrap;
        gap: 10px;
        align-items: center;
        margin-bottom: 10px;
    }}
    .vd-button-bar label {{
        font-size: 14px;
        font-weight: 600;
    }}
    .vd-button-bar select {{
        margin-left: 6px;
        padding: 4px 6px;
        border-radius: 4px;
        border: 1px solid #ced4da;
        font-size: 13px;
    }}
    .vd-btn {{
        border: none;
        padding: 8px 14px;
        border-radius: 6px;
        font-size: 13px;
        cursor: pointer;
        font-weight: 600;
        display: inline-flex;
        align-items: center;
        gap: 4px;
        flex: 1;
        min-width: 0;
        justify-content: center;
    }}
    .vd-btn-group {{
        display: flex;
        gap: 10px;
        flex: 2;
        min-width: 0;
    }}
    .vd-btn-group .vd-btn {{
        flex: 1;
    }}
    #wa-btn {{
        background: #25D366;
        color: #fff;
    }}
    #wa-btn:hover {{
        background: #128C7E;
    }}
    #csv-btn {{
        background: #007bff;
        color: #fff;
    }}
    #csv-btn:hover {{
        background: #0056b3;
    }}
    #clear-btn {{
        background: #6c757d;
        color: #fff;
    }}
    #clear-btn:hover {{
        background: #5a6268;
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
        width: 45px;              /* very narrow (~0.5 inch) */
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
        <div class="vd-button-bar">
            <div style="flex: 1; display: flex; align-items: center;">
                <label>Projection Days:
                    <select id="days-select">
                        <option value="1" selected>1 Day</option>
                        <option value="2">2 Days</option>
                        <option value="3">3 Days</option>
                        <option value="4">4 Days</option>
                        <option value="5">5 Days</option>
                        <option value="6">6 Days</option>
                        <option value="7">7 Days</option>
                    </select>
                </label>
            </div>
            <div class="vd-btn-group">
                <button id="wa-btn" class="vd-btn">📱 Export to WhatsApp</button>
                <button id="csv-btn" class="vd-btn">📥 Export to Excel (CSV)</button>
            </div>
            <div style="flex: 1;">
                <button id="clear-btn" class="vd-btn">🗑️ Clear On Hand</button>
            </div>
        </div>

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

        function getDays() {{
            const sel = document.getElementById('days-select');
            if (!sel) return 1;
            const v = parseInt(sel.value || "1");
            return isNaN(v) ? 1 : v;
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

        // Recalculate when days changed
        const daysSelect = document.getElementById('days-select');
        if (daysSelect) {{
            daysSelect.addEventListener('change', recalcAll);
        }}

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
                if (!prodCell || !input) return;

                const name = (prodCell.textContent || '').trim();
                let baseDemand = parseInt(input.getAttribute('data-basedemand') || "0");
                if (isNaN(baseDemand)) baseDemand = 0;
                let onHand = parseInt(input.value || "0");
                if (isNaN(onHand)) onHand = 0;

                // FINAL QTY = (baseDemand * days) - onHand
                const projected = Math.max(0, (baseDemand * days) - onHand);

                // Include ALL products even if projected quantity is 0
                rows.push({{ name: name, qty: projected }});
            }});
            return rows;
        }}

        // WhatsApp Export
        const waBtn = document.getElementById('wa-btn');
        if (waBtn) {{
            waBtn.addEventListener('click', function() {{
                const days = getDays();
                const rows = getExportRows();

                let lines = [];
                lines.push("🏪 *Vendor Demand Invoice*");
                lines.push("👤 *Vendor:* " + (VENDOR || ""));
                lines.push("🏬 *Branch:* " + (BRANCH || ""));
                lines.push("📊 *Projection:* " + days + " Day" + (days > 1 ? "s" : ""));
                lines.push("📅 *Date:* " + new Date().toLocaleString());
                lines.push("");
                lines.push("📦 *ITEMS:*");

                let totalQty = 0;
                rows.forEach(r => {{
                    totalQty += r.qty;
                    lines.push("• " + r.name + ": " + r.qty);
                }});

                lines.push("");
                lines.push("📋 *TOTAL ITEMS:* " + rows.length);
                lines.push("📦 *TOTAL QTY:* " + totalQty);
                lines.push("");
                lines.push("Thank you! 🚀");

                const text = lines.join("\\n");
                const url = "https://api.whatsapp.com/send?text=" + encodeURIComponent(text);
                window.open(url, '_blank', 'noopener,noreferrer');
            }});
        }}

        // CSV Export (for Excel)
        const csvBtn = document.getElementById('csv-btn');
        if (csvBtn) {{
            csvBtn.addEventListener('click', function() {{
                const days = getDays();
                const rows = getExportRows();
                
                // Export ALL products even if no items with projected quantity
                const header = "Product,Projected Qty";
                const csvLines = [header];

                rows.forEach(r => {{
                    const safeName = '"' + (r.name || "").replace(/"/g, '""') + '"';
                    csvLines.push(safeName + "," + r.qty);
                }});

                const csvContent = csvLines.join("\\r\\n");
                const blob = new Blob([csvContent], {{ type: 'text/csv;charset=utf-8;' }});
                const url = URL.createObjectURL(blob);
                const a = document.createElement('a');
                const safeVendor = (VENDOR || "vendor").toString().replace(/[^a-z0-9]/gi, '_');
                a.href = url;
                a.download = "demand_" + days + "D_" + safeVendor + ".csv";
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
                URL.revokeObjectURL(url);
            }});
        }}

        // Clear On Hand
        const clearBtn = document.getElementById('clear-btn');
        if (clearBtn) {{
            clearBtn.addEventListener('click', function() {{
                document.querySelectorAll('.onhand-input').forEach(inp => {{
                    inp.value = "";
                    const idx = inp.getAttribute('data-idx');
                    sessionStorage.setItem(`onhand_${{VENDOR}}_${{idx}}`, "");
                }});
                recalcAll();
            }});
        }}

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

    # Height for component (no scroll inside table, so adjust height accordingly)
    height = 220 + len(rows) * 30
    components.html(html, height=height, scrolling=False)

# ------------------------------ MAIN UI ------------------------------

# Always show the title
st.markdown('<h1 id="vendors-demand-title">Vendors Demand</h1>', unsafe_allow_html=True)

# Create containers for better organization
header_container = st.container()
upload_container = st.container()
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
                # Don't rerun immediately, let the rest of the script complete

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
                # Don't rerun immediately, let the rest of the script complete

with upload_container:
    # 2) UPLOAD (first time)
    if not st.session_state.vendor_data:
        uploaded = st.file_uploader("📤 Upload Excel File", type=["xlsx", "xls"])
        if uploaded:
            st.session_state.vendor_data = parse_excel(uploaded)
            st.session_state.current_vendor = list(st.session_state.vendor_data.keys())[0]
            st.rerun()

with table_container:
    # 3) WHEN DATA EXISTS — render Excel-style table + export controls
    if st.session_state.vendor_data:
        if st.session_state.current_vendor is None or st.session_state.current_vendor not in st.session_state.vendor_data:
            st.session_state.current_vendor = list(st.session_state.vendor_data.keys())[0]
        
        rows = st.session_state.vendor_data[st.session_state.current_vendor]
        component_table(rows, st.session_state.current_vendor, st.session_state.current_branch)

with status_container:
    if st.session_state.vendor_data:
        st.success(f"✅ Vendor: {st.session_state.current_vendor} | Branch: {st.session_state.current_branch}")

# ------------------------------ FOOTER ------------------------------
st.markdown(
    """
    <div class="footer">
        Software Developed by M Shahzad | Contact: 0345-2227512
    </div>
    """,
    unsafe_allow_html=True
)