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
ss.setdefault("onhand_values", {})  # Store on-hand values
ss.setdefault("current_projection", 1)  # Default to 1 day projection

# ------------------------------ CSS + JS ------------------------------
st.markdown("""
<style>
.block-container{ padding-top:1rem; }

/* compact title */
h1#vendors-demand-title{
  text-align:center; margin:4px 0 6px 0; font-size:1.36rem; font-weight:800;
}

/* Button container */
.button-container {
    display: flex;
    justify-content: center;
    gap: 10px;
    width: 100%;
    margin: 20px 0;
    padding: 15px;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    border-radius: 12px;
    box-shadow: 0 4px 15px rgba(0,0,0,0.1);
    flex-wrap: wrap;
}

/* Excel-style table */
.excel-table { 
    width: 100%; 
    border-collapse: collapse; 
    margin: 20px 0;
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

/* Product column - wider */
.product-cell {
    padding: 8px 16px !important;
    font-weight: 500;
}

/* On-Hand input - Excel style */
.onhand-input {
    width: 100% !important;
    max-width: 100px !important;
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

/* Projection column */
.projection-cell {
    text-align: center !important;
    font-weight: 600;
    background-color: #e7f3ff !important;
    font-size: 16px !important;
}

/* Responsive design */
@media (max-width: 768px) {
    .button-container {
        gap: 8px;
        padding: 10px;
    }
    
    .excel-table {
        font-size: 12px;
    }
}
</style>

<script>
// Live calculation function for single projection column
function liveUpdate(e){
    if(!e || !e.target) return;
    if(!e.target.classList.contains("onhand-input")) return;
    
    var idx = e.target.getAttribute("data-idx");
    var x = parseInt(e.target.value || "0"); 
    if(isNaN(x)) x = 0;

    var baseDemand = parseInt(e.target.getAttribute("data-basedemand") || "0"); 
    if(isNaN(baseDemand)) baseDemand = 0;
    
    var days = parseInt(e.target.getAttribute("data-days") || "1"); 
    if(isNaN(days)) days = 1;

    // Calculate projected demand: (baseDemand * days) - onHand
    var projected = Math.max(0, (baseDemand * days) - x);

    var projectionCell = document.getElementById("projection-"+idx);
    if(projectionCell) projectionCell.textContent = projected;
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

// Function to change projection days
function changeProjection(days) {
    var inputs = document.querySelectorAll('.onhand-input');
    inputs.forEach(function(input) {
        input.setAttribute('data-days', days);
        // Trigger update
        var event = new Event('input', { bubbles: true });
        input.dispatchEvent(event);
    });
    
    // Update the projection column header
    var header = document.querySelector('.excel-table th:nth-child(3)');
    if(header) {
        header.textContent = days + ' Day Projection';
    }
}

// WhatsApp function
function sendWA(days) {
    var trs = document.querySelectorAll(".excel-table tbody tr");
    var lines = [];
    
    lines.push("🏪 *Vendor Demand Invoice*");
    lines.push("👤 *Vendor:* " + (window.VENDOR || ""));
    lines.push("🏬 *Branch:* " + (window.BRANCH || ""));
    lines.push("📊 *Projection:* " + days + " Day");
    lines.push("📅 *Date:* " + new Date().toLocaleString());
    lines.push("");
    lines.push("📦 *ITEMS:*");
    
    var totalQty = 0, totalItems = 0;
    for(var i = 0; i < trs.length; i++){
        var prod = trs[i].querySelector(".product-cell");
        var qtyCell = document.getElementById("projection-" + i);
        if(!prod || !qtyCell) continue;
        
        var name = (prod.textContent || "").trim();
        var qty = parseInt(qtyCell.textContent || "0"); 
        if(isNaN(qty)) qty = 0;
        
        if(qty > 0){
            totalQty += qty; 
            totalItems += 1; 
            lines.push("• " + name + ": " + qty);
        }
    }
    
    lines.push("");
    lines.push("📋 *TOTAL ITEMS:* " + totalItems);
    lines.push("📦 *TOTAL QTY:* " + totalQty);
    lines.push("");
    lines.push("Thank you! 🚀");
    
    var text = lines.join("\\n");
    var url = "https://api.whatsapp.com/send?text=" + encodeURIComponent(text);
    window.open(url, '_blank');
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
                try: return int(round(float(v)))
                except: return 0
            # Use 1 Day column as base demand
            base_demand = num(r.iloc[1])
            rows.append([name, base_demand])
        if rows:
            data[sheet] = rows
    return data

def calculate_projection(base_demand, days, on_hand):
    """Calculate projection: (base_demand * days) - on_hand"""
    on_hand_int = int(on_hand or 0)
    return max(0, (base_demand * days) - on_hand_int)

def export_to_csv(rows, days):
    """Export data to CSV with Product and Projected Qty columns"""
    export_data = []
    
    for i, (prod, base_demand) in enumerate(rows):
        on_hand = ss.onhand_values.get(f"{ss.current_vendor}_{i}", 0)
        projected_qty = calculate_projection(base_demand, days, on_hand)
        export_data.append([prod, projected_qty])
    
    # Create DataFrame
    df = pd.DataFrame(export_data, columns=['Product', 'Projected Qty'])
    
    # Convert to CSV
    csv = df.to_csv(index=False)
    return csv

def clear_all_data():
    """Clear all on-hand values"""
    ss.onhand_values = {}
    st.rerun()

def component_table(rows, vendor: str, branch: str):
    """
    Excel-style table with single projection column
    """
    trs = []
    for i, (prod, base_demand) in enumerate(rows):
        # Get current on-hand value from session state
        current_value = ss.onhand_values.get(f"{vendor}_{i}", "")
        
        # Calculate current projection
        current_projection = calculate_projection(base_demand, ss.current_projection, current_value)
        
        trs.append(
            '<tr>'
            f'<td class="product-cell">{prod}</td>'
            f'<td style="text-align: center;">'
            f'<input class="onhand-input" type="number" inputmode="numeric" placeholder="0" '
            f'value="{current_value}" '
            f'data-idx="{i}" data-basedemand="{base_demand}" data-days="{ss.current_projection}">'
            f'</td>'
            f'<td class="projection-cell" id="projection-{i}">{current_projection}</td>'
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
                        <th style="width: 70%;">Product</th>
                        <th style="width: 15%;">On Hand</th>
                        <th style="width: 15%;">{ss.current_projection} Day Projection</th>
                    </tr>
                </thead>
                <tbody>
                    {body}
                </tbody>
            </table>
        </div>

        <script>
        window.VENDOR = {vendor_js};
        window.BRANCH = {branch_js};
        
        // Initialize with current projection
        setTimeout(function() {{
            changeProjection({ss.current_projection});
        }}, 100);
        </script>
    """

    # Calculate height based on rows
    height = 150 + len(rows) * 45
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

# 3) ACTION BUTTONS - Demand Calculation
if ss.vendor_data:
    st.markdown('<div class="button-container">', unsafe_allow_html=True)
    
    # Create 7 columns for buttons
    cols = st.columns(7)
    
    demand_buttons = [
        ("1 Day", 1),
        ("2 Day", 2), 
        ("3 Day", 3),
        ("4 Day", 4),
        ("5 Day", 5),
        ("6 Day", 6),
        ("7 Day", 7)
    ]
    
    for i, (label, days) in enumerate(demand_buttons):
        with cols[i]:
            if st.button(f"📱 {label}", use_container_width=True, type="primary" if days == ss.current_projection else "secondary"):
                ss.current_projection = days
                st.rerun()
    
    st.markdown('</div>', unsafe_allow_html=True)

# 4) ACTION BUTTONS - Clear and Export
if ss.vendor_data:
    st.markdown('<div class="button-container">', unsafe_allow_html=True)
    
    col1, col2, col3, col4, col5, col6, col7 = st.columns(7)
    
    with col1:
        if st.button("🗑️ Clear All", use_container_width=True, type="secondary"):
            clear_all_data()
    
    # Export buttons for different days
    export_days = [1, 2, 3, 4, 5, 6, 7]
    for i, days in enumerate(export_days):
        with [col2, col3, col4, col5, col6, col7][i]:
            csv_data = export_to_csv(ss.vendor_data[ss.current_vendor], days)
            st.download_button(
                label=f"📥 Export {days}D",
                data=csv_data,
                file_name=f"vendor_demand_{days}day_{ss.current_vendor}.csv",
                mime="text/csv",
                use_container_width=True
            )
    
    st.markdown('</div>', unsafe_allow_html=True)

# 5) WHEN DATA EXISTS — render Excel-style table
if ss.vendor_data:
    if ss.current_vendor is None or ss.current_vendor not in ss.vendor_data:
        ss.current_vendor = list(ss.vendor_data.keys())[0]
    rows = ss.vendor_data[ss.current_vendor]
    component_table(rows, ss.current_vendor, ss.current_branch)

# 6) Status
if ss.vendor_data:
    st.success(f"✅ Loaded vendor: {ss.current_vendor} | Branch: {ss.current_branch} | Current Projection: {ss.current_projection} Day(s)")