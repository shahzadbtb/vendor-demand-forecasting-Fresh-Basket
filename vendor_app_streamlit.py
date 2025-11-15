import os
import json
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
from io import BytesIO

# ------------------------------ CONFIG ------------------------------
st.set_page_config(page_title="Vendors Demand", page_icon="📦", layout="wide")

ss = st.session_state
ss.setdefault("vendor_data", {})
ss.setdefault("current_vendor", None)
ss.setdefault("current_branch", "Shahbaz")

# ------------------------------ CSS (GLOBAL) ------------------------------
st.markdown("""
<style>
.block-container{ padding-top:1rem; }

/* compact title */
h1#vendors-demand-title{
  text-align:center; margin:4px 0 6px 0; font-size:1.36rem; font-weight:800;
}
</style>
""", unsafe_allow_html=True)

# ------------------------------ HELPERS ------------------------------
@st.cache_data
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
                    return int(round(float(v)))
                except:
                    return 0

            base_demand = num(r.iloc[1])
            rows.append([name, base_demand])
        if rows:
            data[sheet] = rows
    return data


def component_table(rows, vendor: str, branch: str):

    trs = []
    for i, (prod, base_demand) in enumerate(rows):
        current_projection = max(0, base_demand)
        trs.append(
            '<tr>'
            f'<td class="product-cell col-product">{prod}</td>'
            f'<td style="text-align: center;" class="col-onhand">'
            f'<input class="onhand-input" type="number" inputmode="numeric" placeholder="0" '
            f'value="" data-idx="{i}" data-basedemand="{base_demand}">'
            f'</td>'
            f'<td class="projection-cell col-projection" id="projection-{i}">{current_projection}</td>'
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

    /* REMOVED SCROLLBAR */
    .table-wrapper {{
        overflow: visible !important;
        height: auto !important;
        max-height: none !important;
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

    /* UPDATED COLUMN WIDTHS */
    .col-product {{
        width: 60% !important;   /* Reduced from 75% */
    }}
    .col-onhand {{
        width: 10%;
        text-align: center;
    }}
    .col-projection {{
        width: 30%;
        text-align: center;
    }}

    .product-cell {{
        padding: 6px 8px;
        font-weight: 500;
    }}

    .onhand-input {{
        width: 45px;
        max-width: 45px;
        font-size: 13px;
        text-align: center;
        border: 1px solid #007bff;
        border-radius: 4px;
        padding: 4px 2px;
        background: white;
    }}

    .projection-cell {{
        text-align: center;
        font-weight: 600;
        background-color: #e7f3ff;
    }}
    </style>

    <div class="vd-container">
        <div class="vd-button-bar">
            <div>
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

            <button id="wa-btn" class="vd-btn">📱 Export to WhatsApp</button>
            <button id="csv-btn" class="vd-btn">📥 Export to Excel (CSV)</button>
            <button id="clear-btn" class="vd-btn">🗑️ Clear On Hand</button>
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

    <!-- JS CODE REMAINS SAME (NO MODIFICATIONS NEEDED) -->
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
            const projected = Math.max(0, (baseDemand * days) - onHand);
            const cell = document.getElementById('projection-' + idx);
            if (cell) cell.textContent = projected;
        }}

        function recalcAll() {{
            document.querySelectorAll('.onhand-input').forEach(inp => recalcRow(inp));
        }}

        document.addEventListener('input', function(e) {{
            if (e.target && e.target.classList.contains('onhand-input')) {{
                recalcRow(e.target);
            }}
        }});

        const daysSelect = document.getElementById('days-select');
        if (daysSelect) {{
            daysSelect.addEventListener('change', recalcAll);
        }}

        function getExportRows() {{
            const days = getDays();
            const rows = [];
            document.querySelectorAll('.excel-table tbody tr').forEach(tr => {{
                const prodCell = tr.querySelector('.product-cell');
                const input = tr.querySelector('.onhand-input');
                if (!prodCell || !input) return;

                const name = (prodCell.textContent || '').trim();
                let baseDemand = parseInt(input.getAttribute('data-basedemand') || "0");
                let onHand = parseInt(input.value || "0");
                if (isNaN(onHand)) onHand = 0;

                const projected = Math.max(0, (baseDemand * days) - onHand);
                if (projected > 0) rows.push({{ name: name, qty: projected }});
            }});
            return rows;
        }}

        const waBtn = document.getElementById('wa-btn');
        if (waBtn) {{
            waBtn.addEventListener('click', function() {{
                const rows = getExportRows();
                const days = getDays();
                let lines = [];
                lines.push("🏪 *Vendor Demand Invoice*");
                lines.push("👤 Vendor: " + VENDOR);
                lines.push("🏬 Branch: " + BRANCH);
                lines.push("📊 Days: " + days);
                lines.push("");

                rows.forEach(r => {{
                    lines.push("• " + r.name + ": " + r.qty);
                }});

                const text = lines.join("\\n");
                const url = "https://api.whatsapp.com/send?text=" + encodeURIComponent(text);
                window.open(url, '_blank');
            }});
        }}

        const csvBtn = document.getElementById('csv-btn');
        if (csvBtn) {{
            csvBtn.addEventListener('click', function() {{
                const rows = getExportRows();
                let csv = "Product,Projected Qty\\n";
                rows.forEach(r => {{
                    csv += '"' + r.name.replace(/"/g,'""') + '",' + r.qty + "\\n";
                }});
                const blob = new Blob([csv], {{type:"text/csv"}});
                const url = URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = "demand.csv";
                a.click();
                URL.revokeObjectURL(url);
            }});
        }}

        document.getElementById('clear-btn').addEventListener('click', function() {{
            document.querySelectorAll('.onhand-input').forEach(i => i.value = "");
            recalcAll();
        }});

    }})();
    </script>
    """

    height = 200 + len(rows) * 42
    components.html(html, height=height, scrolling=False)


# ------------------------------ UI ------------------------------
st.markdown('<h1 id="vendors-demand-title">Vendors Demand</h1>', unsafe_allow_html=True)

if ss.vendor_data:
    vendors = list(ss.vendor_data.keys())
    col1, col2 = st.columns(2)

    with col1:
        new_vendor = st.selectbox(
            "🔍 Select Vendor",
            vendors,
            index=vendors.index(ss.current_vendor) if ss.current_vendor in vendors else 0,
        )
        if new_vendor != ss.current_vendor:
            ss.current_vendor = new_vendor
            st.rerun()

    with col2:
        new_branch = st.selectbox(
            "🏬 Select Branch",
            ["Shahbaz","Clifton","Badar","DHA Ecom","BHD Ecom","BHD","Head Office"],
            index=["Shahbaz","Clifton","Badar","DHA Ecom","BHD Ecom","BHD","Head Office"].index(
                ss.current_branch
            )
        )
        if new_branch != ss.current_branch:
            ss.current_branch = new_branch
            st.rerun()

if not ss.vendor_data:
    uploaded = st.file_uploader("📤 Upload Excel File", type=["xlsx","xls"])
    if uploaded:
        ss.vendor_data = parse_excel(uploaded)
        ss.current_vendor = list(ss.vendor_data.keys())[0]
        st.rerun()

if ss.vendor_data:
    rows = ss.vendor_data[ss.current_vendor]
    component_table(rows, ss.current_vendor, ss.current_branch)
    st.success(f"Vendor: {ss.current_vendor} | Branch: {ss.current_branch}")
