import os
import json
import pandas as pd
import streamlit as st
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
if 'projection_days' not in st.session_state:
    st.session_state.projection_days = 1
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

/* Custom table styling */
.custom-table {
    width: 100%;
    border-collapse: collapse;
    font-family: Arial, sans-serif;
    font-size: 14px;
}
.custom-table th {
    background-color: #f8f9fa;
    border: 1px solid #dee2e6;
    padding: 10px 8px;
    font-weight: bold;
    text-align: center;
    position: sticky;
    top: 0;
}
.custom-table td {
    border: 1px solid #dee2e6;
    padding: 8px 6px;
}
.custom-table tr:nth-child(even) {
    background-color: #f8f9fa;
}
.custom-table tr:hover {
    background-color: #e9ecef;
}

/* Column widths */
.col-product {
    width: 70%;
    text-align: left;
}
.col-onhand {
    width: 15%;
    text-align: center;
}
.col-projection {
    width: 15%;
    text-align: center;
    font-weight: 600;
    background-color: #e7f3ff;
}

/* Input styling */
.onhand-input {
    width: 80px;
    text-align: center;
    border: 1px solid #007bff;
    border-radius: 4px;
    padding: 6px 4px;
    font-size: 14px;
}
.onhand-input:focus {
    outline: none;
    border-color: #0056b3;
    box-shadow: 0 0 0 2px rgba(0,123,255,0.25);
}

/* Button styling */
.action-btn {
    width: 100%;
    margin: 2px 0;
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

def calculate_projection(base_demand, onhand_value, days):
    """Calculate projection based on base demand, on-hand value, and days"""
    try:
        onhand = int(onhand_value) if onhand_value != "" else 0
    except:
        onhand = 0
    return max(0, (base_demand * days) - onhand)

def get_export_data(rows, vendor, branch, days):
    """Get data for export in both WhatsApp and CSV formats"""
    export_rows = []
    total_qty = 0
    
    for i, (product, base_demand) in enumerate(rows):
        key = f"{vendor}_{i}"
        onhand_value = st.session_state.onhand_values.get(key, "")
        projected_qty = calculate_projection(base_demand, onhand_value, days)
        
        export_rows.append({
            'product': product,
            'qty': projected_qty
        })
        total_qty += projected_qty
    
    return export_rows, total_qty

def export_to_whatsapp(export_rows, vendor, branch, days, total_qty):
    """Generate WhatsApp export text"""
    lines = []
    lines.append("🏪 *Vendor Demand Invoice*")
    lines.append("👤 *Vendor:* " + (vendor or ""))
    lines.append("🏬 *Branch:* " + (branch or ""))
    lines.append("📊 *Projection:* " + str(days) + " Day" + ("s" if days > 1 else ""))
    lines.append("📅 *Date:* " + pd.Timestamp.now().strftime('%Y-%m-%d %H:%M'))
    lines.append("")
    lines.append("📦 *ITEMS:*")

    for row in export_rows:
        lines.append("• " + row['product'] + ": " + str(row['qty']))

    lines.append("")
    lines.append("📋 *TOTAL ITEMS:* " + str(len(export_rows)))
    lines.append("📦 *TOTAL QTY:* " + str(total_qty))
    lines.append("")
    lines.append("Thank you! 🚀")

    return "\n".join(lines)

def export_to_csv(export_rows, vendor, days):
    """Generate CSV export data"""
    csv_lines = ["Product,Projected Qty"]
    for row in export_rows:
        safe_name = '"' + row['product'].replace('"', '""') + '"'
        csv_lines.append(f"{safe_name},{row['qty']}")
    return "\r\n".join(csv_lines)

# ------------------------------ MAIN UI ------------------------------

# Always show the title
st.markdown('<h1 id="vendors-demand-title">Vendors Demand</h1>', unsafe_allow_html=True)

# Create main containers
header_container = st.container()
upload_container = st.container()
controls_container = st.container()
table_container = st.container()
export_container = st.container()
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
            st.rerun()

# Main application logic when data exists
if st.session_state.vendor_data:
    if st.session_state.current_vendor is None or st.session_state.current_vendor not in st.session_state.vendor_data:
        st.session_state.current_vendor = list(st.session_state.vendor_data.keys())[0]
    
    rows = st.session_state.vendor_data[st.session_state.current_vendor]
    
    with controls_container:
        # Control buttons row
        col1, col2, col3 = st.columns([1, 2, 1])
        
        with col1:
            st.session_state.projection_days = st.selectbox(
                "**Projection Days:**",
                options=[1, 2, 3, 4, 5, 6, 7],
                index=0,
                key="days_select"
            )
        
        with col2:
            col2a, col2b = st.columns(2)
            with col2a:
                if st.button("📱 Export to WhatsApp", use_container_width=True, key="wa_btn"):
                    # This will be handled after the table
                    pass
            with col2b:
                if st.button("📥 Export to Excel (CSV)", use_container_width=True, key="csv_btn"):
                    # This will be handled after the table
                    pass
        
        with col3:
            if st.button("🗑️ Clear On Hand", use_container_width=True, key="clear_btn"):
                # Clear all on-hand values for current vendor
                for i in range(len(rows)):
                    key = f"{st.session_state.current_vendor}_{i}"
                    if key in st.session_state.onhand_values:
                        del st.session_state.onhand_values[key]
                st.rerun()

    with table_container:
        # Create the table using Streamlit components
        st.markdown("### Products List")
        
        # Create table header
        col1, col2, col3 = st.columns([7, 1.5, 1.5])
        with col1:
            st.markdown("**Product**")
        with col2:
            st.markdown("**On Hand**")
        with col3:
            st.markdown("**Projection**")
        
        st.markdown("---")
        
        # Create rows with inputs
        for i, (product, base_demand) in enumerate(rows):
            key = f"{st.session_state.current_vendor}_{i}"
            
            # Get current onhand value
            current_onhand = st.session_state.onhand_values.get(key, "")
            
            # Calculate projection
            projected = calculate_projection(base_demand, current_onhand, st.session_state.projection_days)
            
            # Create columns for this row
            col1, col2, col3 = st.columns([7, 1.5, 1.5])
            
            with col1:
                st.write(product)
            
            with col2:
                new_onhand = st.text_input(
                    "",
                    value=current_onhand,
                    key=f"onhand_{key}",
                    label_visibility="collapsed",
                    placeholder="0"
                )
                # Update session state if value changed
                if new_onhand != current_onhand:
                    if new_onhand == "":
                        if key in st.session_state.onhand_values:
                            del st.session_state.onhand_values[key]
                    else:
                        st.session_state.onhand_values[key] = new_onhand
            
            with col3:
                st.markdown(f"**{projected}**")

    with export_container:
        # Handle exports after the table is rendered
        col1, col2 = st.columns(2)
        
        with col1:
            if st.session_state.get('wa_btn_clicked', False):
                export_rows, total_qty = get_export_data(
                    rows, 
                    st.session_state.current_vendor, 
                    st.session_state.current_branch, 
                    st.session_state.projection_days
                )
                whatsapp_text = export_to_whatsapp(
                    export_rows, 
                    st.session_state.current_vendor, 
                    st.session_state.current_branch, 
                    st.session_state.projection_days, 
                    total_qty
                )
                
                whatsapp_url = f"https://api.whatsapp.com/send?text={whatsapp_text}"
                st.markdown(f'<a href="{whatsapp_url}" target="_blank"><button style="width:100%">📱 Open WhatsApp with Data</button></a>', unsafe_allow_html=True)
                
                # Reset the flag
                st.session_state.wa_btn_clicked = False
        
        with col2:
            if st.session_state.get('csv_btn_clicked', False):
                export_rows, total_qty = get_export_data(
                    rows, 
                    st.session_state.current_vendor, 
                    st.session_state.current_branch, 
                    st.session_state.projection_days
                )
                csv_data = export_to_csv(export_rows, st.session_state.current_vendor, st.session_state.projection_days)
                
                st.download_button(
                    label="📥 Download CSV File",
                    data=csv_data,
                    file_name=f"demand_{st.session_state.projection_days}D_{st.session_state.current_vendor.replace(' ', '_')}.csv",
                    mime="text/csv",
                    use_container_width=True
                )
                
                # Reset the flag
                st.session_state.csv_btn_clicked = False

    # Handle button clicks
    if st.session_state.get('wa_btn', False):
        st.session_state.wa_btn_clicked = True
        st.session_state.csv_btn_clicked = False
        st.rerun()
    
    if st.session_state.get('csv_btn', False):
        st.session_state.csv_btn_clicked = True
        st.session_state.wa_btn_clicked = False
        st.rerun()

    with status_container:
        st.success(f"✅ Vendor: {st.session_state.current_vendor} | Branch: {st.session_state.current_branch} | Projection Days: {st.session_state.projection_days}")

# ------------------------------ FOOTER ------------------------------
st.markdown(
    """
    <div class="footer">
        Software Developed by M Shahzad | Contact: 0345-2227512
    </div>
    """,
    unsafe_allow_html=True
)