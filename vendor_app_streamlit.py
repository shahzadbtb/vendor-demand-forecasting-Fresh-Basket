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

# ------------------------------ CSS + JS ------------------------------
st.markdown("""
<style>
.block-container{ padding-top:1rem; }

/* compact title */
h1#vendors-demand-title{
  text-align:center; margin:4px 0 6px 0; font-size:1.36rem; font-weight:800;
}

/* Projection buttons - TOP PROMINENT */
.projection-buttons-container {
    display: flex;
    justify-content: center;
    gap: 15px;
    width: 100%;
    margin: 20px 0;
    padding: 15px;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    border-radius: 12px;
    box-shadow: 0 4px 15px rgba(0,0,0,0.1);
}

.projection-button {
    background: white !important;
    color: #6c5ce7 !important;
    border: none !important;
    border-radius: 10px !important;
    padding: 12px 20px !important;
    font-size: 16px !important;
    font-weight: 800 !important;
    cursor: pointer !important;
    min-width: 80px !important;
    transition: all 0.3s ease !important;
    box-shadow: 0 2px 10px rgba(0,0,0,0.1) !important;
}

.projection-button:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 4px 15px rgba(0,0,0,0.2) !important;
    background: #f8f9fa !important;
}

.projection-button:active {
    transform: translateY(0px) !important;
}

/* Clear button specific styling */
.clear-button {
    background: #ff6b6b !important;
    color: white !important;
    border: none !important;
    border-radius: 10px !important;
    padding: 12px 20px !important;
    font-size: 16px !important;
    font-weight: 800 !important;
    cursor: pointer !important;
    min-width: 80px !important;
    transition: all 0.3s ease !important;
    box-shadow: 0 2px 10px rgba(255, 107, 107, 0.3) !important;
}

.clear-button:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 4px 15px rgba(255, 107, 107, 0.4) !important;
    background: #ff5252 !important;
}

.clear-button:active {
    transform: translateY(0px) !important;
}

/* Export button specific styling */
.export-button {
    background: #00b894 !important;
    color: white !important;
    border: none !important;
    border-radius: 10px !important;
    padding: 12px 20px !important;
    font-size: 16px !important;
    font-weight: 800 !important;
    cursor: pointer !important;
    min-width: 80px !important;
    transition: all 0.3s ease !important;
    box-shadow: 0 2px 10px rgba(0, 184, 148, 0.3) !important;
}

.export-button:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 4px 15px rgba(0, 184, 148, 0.4) !important;
    background: #00a085 !important;
}

.export-button:active {
    transform: translateY(0px) !important;
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
    .projection-buttons-container {
        gap: 10px;
        padding: 12px;
        flex-wrap: wrap;
    }
    
    .projection-button, .clear-button, .export-button {
        padding: 10px 15px !important;
        font-size: 14px !important;
        min-width: 70px !important;
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

// Clear all input fields - FIXED VERSION
function clearAllData() {
    var inputs = document.querySelectorAll('.onhand-input');
    inputs.forEach(function(input) {
        input.value = '';
    });
    
    // Trigger live update to reset projections to original values
    inputs.forEach(function(input) {
        var idx = input.getAttribute("data-idx");
        var b1 = parseInt(input.getAttribute("data-day1") || "0");
        var b3 = parseInt(input.getAttribute("data-day3") || "0");
        var b5 = parseInt(input.getAttribute("data-day5") || "0");
        
        document.getElementById("p1-"+idx).textContent = b1;
        document.getElementById("p3-"+idx).textContent = b3;
        document.getElementById("p5-"+idx).textContent = b5;
    });
    
    // Show confirmation message
    alert('All On Hand data has been cleared! Projections reset to original values.');
}

// Export to CSV function
function exportToCSV(period) {
    var pref = (period === 1) ? "p1-" : (period === 3) ? "p3-" : "p5-";
    var trs = document.querySelectorAll(".excel-table tbody tr");
    var csvData = [];
    
    // Add headers
    csvData.push(["Product", "Projected Qty"]);
    
    // Add all rows (including zero quantities)
    for(var i = 0; i < trs.length; i++) {
        var prod = trs[i].querySelector(".product-cell");
        var qtyC = document.getElementById(pref + i);
        if(!prod || !qtyC) continue;
        
        var name = (prod.textContent || "").trim();
        var qty = parseInt(qtyC.textContent || "0"); 
        if(isNaN(qty)) qty = 0;
        
        csvData.push([name, qty]);
    }
    
    // Convert to CSV string
    var csvContent = "data:text/csv;charset=utf-8,";
    csvData.forEach(function(row) {
        csvContent += row.map(function(field) {
            return '"' + String(field).replace(/"/g, '""') + '"';
        }).join(",") + "\\r\\n";
    });
    
    // Create download link
    var encodedUri = encodeURI(csvContent);
    var link = document.createElement("a");
    link.setAttribute("href", encodedUri);
    link.setAttribute("download", "vendor_demand_" + period + "day.csv");
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
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
    Excel-style table with prominent buttons at TOP including Clear and Export buttons
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
        <!-- PROMINENT BUTTONS AT TOP -->
        <div class="projection-buttons-container">
            <button class="projection-button" onclick="sendWA(1)">1 Day</button>
            <button class="projection-button" onclick="sendWA(3)">3 Day</button>
            <button class="projection-button" onclick="sendWA(5)">5 Day</button>
            <button class="clear-button" onclick="clearAllData()">Clear</button>
            <button class="export-button" onclick="exportToCSV(1)">Export 1D</button>
            <button class="export-button" onclick="exportToCSV(3)">Export 3D</button>
            <button class="export-button" onclick="exportToCSV(5)">Export 5D</button>
        </div>

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
    height = 200 + len(rows) * 50
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

# 4) Status (removed the upload button from bottom)
if ss.vendor_data:
    st.success(f"✅ Loaded vendor: {ss.current_vendor} | Branch: {ss.current_branch}")