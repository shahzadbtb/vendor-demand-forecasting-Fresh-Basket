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

/* projection buttons directly under the title */
.action-row{
  display:flex; justify-content:center; gap:15px; margin: 6px 0 10px;
}
.action-row button{
  background:#6c5ce7; color:#fff; border:none; border-radius:8px;
  padding:8px 20px; font-size:16px; font-weight:700; cursor:pointer;
  min-width: 60px;
}
.action-row button:hover{ background:#5548d9; }
.action-row button:active{ transform:translateY(1px); }

/* table: product wider, on-hand ultra narrow */
.mobile-table{ 
    width:100%; 
    border-collapse:collapse; 
    table-layout:fixed; 
    margin-top:4px; 
}
.mobile-table th,
.mobile-table td{ 
    border:1px solid #e5e5e5; 
    text-align:center; 
    padding:6px; 
    font-size:15px; 
}
.mobile-table colgroup col:nth-child(1){ width:75%; } /* Product (wider) */
.mobile-table colgroup col:nth-child(2){ width:10%; }  /* On Hand (very small) */
.mobile-table colgroup col:nth-child(3){ width:15%; }  /* Projection */

/* On-Hand input - remove spinner buttons and improve navigation */
.mobile-table input{
  width:80px; max-width:80px; font-size:15px; text-align:center;
  border:1px solid #aaa; border-radius:4px; padding:2px; background:#fafafa;
}

/* Remove spinner buttons from number input */
.mobile-table input[type=number]::-webkit-outer-spin-button,
.mobile-table input[type=number]::-webkit-inner-spin-button {
  -webkit-appearance: none;
  margin: 0;
}
.mobile-table input[type=number] {
  -moz-appearance: textfield;
}
</style>

<script>
// --- live subtraction & robust mobile events ---
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

// Enhanced keyboard navigation for Excel-like behavior
function handleKeyNavigation(e) {
  if(!e.target.classList.contains("onhand-input")) return;
  
  var currentInput = e.target;
  var currentIndex = parseInt(currentInput.getAttribute("data-idx"));
  var allInputs = document.querySelectorAll('.onhand-input');
  var totalInputs = allInputs.length;
  
  if (e.key === 'Enter' || e.key === 'ArrowDown') {
    e.preventDefault();
    var nextIndex = (currentIndex + 1) % totalInputs;
    allInputs[nextIndex].focus();
    allInputs[nextIndex].select();
  } else if (e.key === 'ArrowUp') {
    e.preventDefault();
    var prevIndex = (currentIndex - 1 + totalInputs) % totalInputs;
    allInputs[prevIndex].focus();
    allInputs[prevIndex].select();
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
    var header = document.querySelector('.mobile-table th:nth-child(3)');
    if(header) {
        header.textContent = days + ' Day Projection';
    }
}

document.addEventListener("input",  liveUpdate, true);
document.addEventListener("keyup",  liveUpdate, true);
document.addEventListener("change", liveUpdate, true);
document.addEventListener("keydown", handleKeyNavigation, true);
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
    """Export data to CSV with Product and Projected Qty columns (WITH on-hand subtraction)"""
    export_data = []
    
    for i, (prod, base_demand) in enumerate(rows):
        on_hand = ss.onhand_values.get(f"{ss.current_vendor}_{i}", 0)
        # Subtract on-hand from projected demand for export
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
    SINGLE component on the page with working WhatsApp buttons
    """
    trs = []
    for i, (prod, base_demand) in enumerate(rows):
        # Get current on-hand value from session state
        current_value = ss.onhand_values.get(f"{vendor}_{i}", "")
        
        # Calculate current projection
        current_projection = calculate_projection(base_demand, ss.current_projection, current_value)
        
        trs.append(
            '<tr>'
            f'<td id="prod-{i}">{prod}</td>'
            f'<td><input class="onhand-input" type="number" inputmode="numeric" '
            f'value="{current_value}" '
            f'data-idx="{i}" data-basedemand="{base_demand}" data-days="{ss.current_projection}"></td>'
            f'<td id="projection-{i}">{current_projection}</td>'
            '</tr>'
        )
    body = "".join(trs)

    vendor_js = json.dumps(vendor or "")
    branch_js = json.dumps(branch or "")

    html = (
        # buttons under header - WhatsApp buttons
        '<div class="action-row">'
        '<button onclick="sendWA(1)">1 Day</button>'
        '<button onclick="sendWA(2)">2 Day</button>'
        '<button onclick="sendWA(3)">3 Day</button>'
        '<button onclick="sendWA(4)">4 Day</button>'
        '<button onclick="sendWA(5)">5 Day</button>'
        '<button onclick="sendWA(6)">6 Day</button>'
        '<button onclick="sendWA(7)">7 Day</button>'
        '</div>'

        # table
        '<table class="mobile-table">'
        '<colgroup><col><col><col></colgroup>'
        '<tr><th>Product</th><th>On Hand</th><th>' + str(ss.current_projection) + ' Day Projection</th></tr>'
        + body +
        '</table>'

        # invoice / WA - USING WORKING CODE FROM OLD VERSION
        '<script>'
        'var VENDOR=' + vendor_js + ';'
        'var BRANCH=' + branch_js + ';'
        'function nowString(){var d=new Date();function pad(n){n=("0"+n).slice(-2);return n;}'
        'return d.getFullYear()+"-"+pad(d.getMonth()+1)+"-"+pad(d.getDate())+" "+'
        'pad(d.getHours())+":"+pad(d.getMinutes())+":"+pad(d.getSeconds());}'
        
        'function buildInvoice(period){'
        ' var trs=document.querySelectorAll(".mobile-table tr");'
        ' var lines=[];'
        ' lines.push("🏪 *Vendor Demand Invoice*");'
        ' lines.push("👤 *Vendor:* "+VENDOR);'
        ' lines.push("🏬 *Branch:* "+BRANCH);'
        ' lines.push("📊 *Projection:* "+period+" Day");'
        ' lines.push("📅 *Date:* "+nowString());'
        ' lines.push("");'
        ' lines.push("📦 *ITEMS:*");'
        ' var totalQty=0,totalItems=0;'
        ' for(var i=1;i<trs.length;i++){'  # skip header row
        '   var prod=document.getElementById("prod-"+(i-1));'
        '   var qtyC=document.getElementById("projection-"+(i-1));'
        '   if(!prod||!qtyC) continue;'
        '   var name=(prod.textContent||"").trim();'
        '   var qty=parseInt(qtyC.textContent||"0"); if(isNaN(qty)) qty=0;'
        '   if(qty>0){ totalQty+=qty; totalItems+=1; lines.push("• "+name+": "+qty); }'
        ' }'
        ' lines.push("");'
        ' lines.push("📋 *TOTAL ITEMS:* "+totalItems);'
        ' lines.push("📦 *TOTAL QTY:* "+totalQty);'
        ' lines.push("");'
        ' lines.push("Thank you! 🚀");'
        ' return lines.join("\\n");'
        '}'
        
        'function sendWA(period){'
        ' // First update projection to selected days'
        ' var inputs=document.querySelectorAll(".onhand-input");'
        ' inputs.forEach(function(input){'
        '   input.setAttribute("data-days", period);'
        '   var event=new Event("input",{bubbles:true});'
        '   input.dispatchEvent(event);'
        ' });'
        ' '
        ' // Update header'
        ' var header=document.querySelector(".mobile-table th:nth-child(3)");'
        ' if(header){header.textContent=period+" Day Projection";}'
        ' '
        ' // Wait a bit then send'
        ' setTimeout(function(){'
        '   var text=buildInvoice(period);'
        '   var url="https://api.whatsapp.com/send?text="+encodeURIComponent(text);'
        '   var a=document.createElement("a"); a.href=url; a.target="_blank"; a.rel="noopener";'
        '   document.body.appendChild(a); a.click(); a.remove();'
        ' }, 200);'
        '}'
        '</script>'
    )

    # height so whole table shows (no inner scroll)
    height = 130 + len(rows) * 44
    components.html(html, height=height, scrolling=False)

# ------------------------------ UI ------------------------------
st.markdown('<h1 id="vendors-demand-title">Vendors Demand</h1>', unsafe_allow_html=True)

# 1) VENDOR SELECTION (top)
if ss.vendor_data:
    vendors = list(ss.vendor_data.keys())
    c1, c2 = st.columns(2)
    with c1:
        new_vendor = st.selectbox("🔍 Select Vendor", vendors, 
                                index=vendors.index(ss.current_vendor) if ss.current_vendor in vendors else 0,
                                key="vendor_select")
        if new_vendor != ss.current_vendor:
            ss.current_vendor = new_vendor
            st.rerun()
    
    with c2:
        new_branch = st.selectbox(
            "🏬 Select Branch",
            ["Shahbaz","Clifton","Badar","DHA Ecom","BHD Ecom","BHD","Head Office"],
            index=["Shahbaz","Clifton","Badar","DHA Ecom","BHD Ecom","BHD","Head Office"].index(ss.current_branch),
            key="branch_select"
        )
        if new_branch != ss.current_branch:
            ss.current_branch = new_branch
            st.rerun()

# 2) UPLOAD (first time or re-upload)
if not ss.vendor_data:
    uploaded = st.file_uploader("📤 Upload Excel File", type=["xlsx", "xls"])
    if uploaded:
        ss.vendor_data = parse_excel(uploaded)
        ss.current_vendor = list(ss.vendor_data.keys())[0]
        st.rerun()

# 3) ACTION BUTTONS - Clear and Export
if ss.vendor_data:
    st.markdown("### 🛠️ Actions")
    cols = st.columns(4)
    
    with cols[0]:
        if st.button("🗑️ Clear All Data", use_container_width=True, type="secondary"):
            clear_all_data()
    
    with cols[1]:
        export_option = st.selectbox(
            "Export Days",
            [1, 2, 3, 4, 5, 6, 7],
            index=0,
            key="export_select"
        )
    
    with cols[2]:
        csv_data = export_to_csv(ss.vendor_data[ss.current_vendor], export_option)
        st.download_button(
            label=f"📥 Export {export_option}D CSV",
            data=csv_data,
            file_name=f"demand_{export_option}day_{ss.current_vendor}.csv",
            mime="text/csv",
            use_container_width=True,
            key="export_btn"
        )

# 4) WHEN DATA EXISTS — render component with WhatsApp buttons
if ss.vendor_data:
    if ss.current_vendor is None or ss.current_vendor not in ss.vendor_data:
        ss.current_vendor = list(ss.vendor_data.keys())[0]
    rows = ss.vendor_data[ss.current_vendor]
    component_table(rows, ss.current_vendor, ss.current_branch)

# 5) Status
if ss.vendor_data:
    st.success(f"✅ Loaded vendor: {ss.current_vendor} | Branch: {ss.current_branch}")
    
    if st.button("📤 Upload New Excel File"):
        ss.vendor_data = {}
        ss.current_vendor = None
        st.rerun()