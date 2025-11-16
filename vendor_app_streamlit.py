import os
import json
import pandas as pd
import streamlit as st
from io import BytesIO

# ------------------------------ CONFIG ------------------------------
st.set_page_config(page_title="Vendors Demand", page_icon="📦", layout="wide")

ss = st.session_state
ss.setdefault("vendor_data", {})
ss.setdefault("current_vendor", None)
ss.setdefault("current_branch", "Shahbaz")
ss.setdefault("onhand_values", {})

# ------------------------------ GLOBAL CSS ------------------------------
st.markdown("""
<style>

.block-container { padding-top: 1rem; }

/* Fix full table styling */
.dataframe { font-size: 14px; }

/* Column Alignment */
.dataframe td, .dataframe th {
    text-align: center !important;
    vertical-align: middle !important;
    padding: 6px !important;
}

/* Product column left */
.dataframe td:first-child, .dataframe th:first-child {
    text-align: left !important;
}

/* Fix Projection Column */
.dataframe th:nth-child(3), .dataframe td:nth-child(3) {
    min-width: 120px !important;
    text-align: center !important;
}

/* On-hand */
.dataframe th:nth-child(2), .dataframe td:nth-child(2) {
    min-width: 80px !important;
    text-align: center !important;
}

/* Buttons row gap */
.button-row .stButton {
    margin-right: 10px !important;
}

/* Footer */
.footer {
    margin-top: 40px;
    text-align: center;
    padding: 10px;
    color: #444;
    font-size: 14px;
}
</style>
""", unsafe_allow_html=True)


# ------------------------------ HELPER ------------------------------
@st.cache_data
def parse_excel(uploaded_file) -> dict:
    """Reads Excel with multiple sheets"""
    x = pd.ExcelFile(uploaded_file)
    sheets = {}
    for sheet in x.sheet_names:
        df = x.parse(sheet)
        df.columns = ["Product", "1 Day", "3 Day", "5 Day"]
        sheets[sheet] = df
    return sheets


# ------------------------------ HEADER ------------------------------
st.title("Vendors Demand")

# Upload File
vendor_file = st.file_uploader("📂 Upload Vendor Excel", type=["xlsx"])

if vendor_file:
    ss["vendor_data"] = parse_excel(vendor_file)

vendor_list = list(ss["vendor_data"].keys())

vendor = st.selectbox("🔍 Select Vendor", vendor_list)
ss["current_vendor"] = vendor

branch = st.selectbox("🏬 Select Branch",
                      ["Shahbaz", "Badar", "Clifton", "BHD", "E-Commerce"])
ss["current_branch"] = branch


# ------------------------------ ROW 1 (Days + Clear Button) ------------------------------
colA, colB = st.columns([1, 1])

with colA:
    projection_day = st.selectbox("Projection Days:",
                                  ["1 Day", "3 Day", "5 Day"])

with colB:
    if st.button("🧹 Clear On-Hand Values"):
        ss["onhand_values"] = {}


# ------------------------------ ROW 2 (WhatsApp + Excel Buttons Same Row) ------------------------------
col1, col2 = st.columns([1, 1])

with col1:
    wa_btn = st.button("💬 Export to WhatsApp")

with col2:
    export_btn = st.button("📄 Export to Excel (CSV)")


# ------------------------------ BUILD TABLE ------------------------------
if vendor:
    df = ss["vendor_data"][vendor][["Product", projection_day]]

    df["On Hand"] = df["Product"].apply(lambda x: ss["onhand_values"].get(x, 0))
    df = df.rename(columns={projection_day: "Projection"})

    st.dataframe(df, use_container_width=True)

    # Save user inputs
    for i, row in df.iterrows():
        key = f"onhand_{i}"
        val = st.number_input(
            f"{row['Product']} On-Hand",
            value=int(row["On Hand"]),
            min_value=0,
            key=key
        )
        ss["onhand_values"][row["Product"]] = val


# ------------------------------ EXPORT WHATSAPP ------------------------------
if wa_btn:
    txt = f"Vendor Demand – {vendor}\nBranch: {branch}\n\n"
    for i, row in df.iterrows():
        txt += f"{row['Product']} – Need {row['Projection']}\n"

    url = "https://wa.me/?text=" + txt.replace(" ", "%20")
    st.markdown(f"### 👉 [Click here to Open WhatsApp]({url})")


# ------------------------------ EXPORT CSV ------------------------------
if export_btn:
    out = df.to_csv(index=False).encode()
    st.download_button("Download CSV File", out, "vendor_demand.csv", "text/csv")


# ------------------------------ FOOTER ------------------------------
st.markdown("""
<div class="footer">
<b>This software is developed by M. Shahzad</b><br>
📞 Contact: 0345227512
</div>
""", unsafe_allow_html=True)
