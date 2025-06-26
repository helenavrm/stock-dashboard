# app.py

import streamlit as st
import pandas as pd
import plotly.express as px
import logging
from io import BytesIO
from datetime import datetime, timedelta

# ───────────────────────────────────────────────────────────────
# Set up basic logging
# ───────────────────────────────────────────────────────────────
logging.basicConfig(
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
    level=logging.INFO
)
logger = logging.getLogger("stock_dashboard")
logger.info("Starting Streamlit app")

# ───────────────────────────────────────────────────────────────
# Import utility modules
# ───────────────────────────────────────────────────────────────
from io_utils import load_stock_data
from stock_utils import summarize_stock, categorize_fg_codes

# ───────────────────────────────────────────────────────────────
# Caching wrappers
# ───────────────────────────────────────────────────────────────
@st.cache_data(show_spinner=False)
def cached_load_stock_data(file_buffer: BytesIO, sheet_name: str) -> pd.DataFrame:
    logger.info("Loading stock data")
    df = load_stock_data(file_buffer, sheet_name=sheet_name)
    logger.info(f"Loaded {len(df)} stock entries")
    return df

@st.cache_data(show_spinner=False)
def cached_summarize_stock(df: pd.DataFrame) -> dict:
    logger.info("Summarizing stock quantities")
    summary = summarize_stock(df)
    logger.info("Stock summary computed")
    return summary

@st.cache_data(show_spinner=False)
def cached_categorize_fg_codes(df: pd.DataFrame, warehouse: str, stock_type: str) -> dict:
    logger.info(f"Categorizing FG codes for {warehouse}, {stock_type}")
    categories = categorize_fg_codes(df, warehouse, stock_type)
    logger.info(f"Categorized FG codes for {warehouse}, {stock_type}")
    return categories

# ───────────────────────────────────────────────────────────────
# PAGE CONFIG, TITLE, and Embedded CSS/Theming
# ───────────────────────────────────────────────────────────────
st.set_page_config(page_title="Warehouse Stock Dashboard", layout="wide")
st.markdown(
    """
    <style>
      /* Change primary button color */
      .stButton>button {
        background-color: #4CAF50;
        color: white;
        padding: 8px 16px;
        border: none;
        border-radius: 4px;
      }
      /* Dark mode adjustments */
      .dark-mode .stApp {
        background-color: #2E2E2E;
        color: #F0F0F0;
      }
      /* Table styling */
      .stDataFrame {
        font-size: 0.9em;
      }
    </style>
    """,
    unsafe_allow_html=True
)
st.title("📦 Warehouse Stock Dashboard")

# ───────────────────────────────────────────────────────────────
# Dark Mode Toggle
# ───────────────────────────────────────────────────────────────
dark_mode = st.sidebar.checkbox("🌙 Dark Mode")
if dark_mode:
    st.markdown(
        "<script>document.body.classList.add('dark-mode');</script>",
        unsafe_allow_html=True
    )

# ───────────────────────────────────────────────────────────────
# Sidebar: File upload
# ───────────────────────────────────────────────────────────────
st.sidebar.header("Upload Stock Data")
stock_file = st.sidebar.file_uploader(
    "Stock Data file (.xlsx, .xls [Excel 97-2003], .csv, .parquet)",
    type=["xlsx", "xls", "csv", "parquet"]
)

# ───────────────────────────────────────────────────────────────
# MAIN LOGIC: only if file is uploaded
# ───────────────────────────────────────────────────────────────
if stock_file is not None:
    load_successful = True
    error_msg = ""

    with st.spinner("Loading & processing..."):
        try:
            # Load stock data
            df_stock = cached_load_stock_data(stock_file, sheet_name="Sheet1")
            # Check for invalid GR Dates
            if df_stock["GR Date Invalid"].any():
                invalid_count = df_stock["GR Date Invalid"].sum()
                invalid_examples = df_stock[df_stock["GR Date Invalid"]]["GR Date"].head(5).tolist()
                st.warning(
                    f"⚠️ Found {invalid_count} rows with invalid GR Date values. Examples: {invalid_examples}. "
                    "These rows are included but may not appear in Current/Yesterday's/Previous Stock."
                )
            # Filter for CROD
            df_stock = df_stock[df_stock["Storage BIN"] == "CROD"].copy()
            # Summarize stock quantities
            stock_summary = cached_summarize_stock(df_stock)
        except ValueError as ve:
            load_successful = False
            error_msg = f"❌ Data error: {ve}"
            logger.error(error_msg)
        except Exception as ex:
            load_successful = False
            error_msg = f"Error: {str(ex)}"
            logger.error(error_msg)

    if not load_successful:
        st.error(error_msg)
        st.stop()
    else:
        st.success("✅ Data loaded successfully")

        # ───────────────────────────────────────────────────────────────
        # KPI HEADER BAR: Current, Yesterday's, and Previous Stock for CHKO and CHKI
        # ───────────────────────────────────────────────────────────────
        current_date = datetime.now().date()
        yesterday_date = current_date - timedelta(days=1)
        current_date_str = current_date.strftime("%B %d, %Y")  # e.g., "June 24, 2025"
        yesterday_date_str = yesterday_date.strftime("%B %d, %Y")  # e.g., "June 23, 2025"
        st.markdown(
            f"""
            <div style="display:flex; gap:20px; margin-bottom:20px; flex-wrap: wrap;">
              <div style="flex:1; background:#fafafa; padding:15px; border-radius:8px; box-shadow:2px 2px 5px rgba(0,0,0,0.1); min-width:200px;">
                <h3>CHKO Current Stock (CROD, {current_date_str})</h3><p style="font-size:1.5em;">{stock_summary['CHKO']['current']:.2f} NOS</p>
              </div>
              <div style="flex:1; background:#fafafa; padding:15px; border-radius:8px; box-shadow:2px 2px 5px rgba(0,0,0,0.1); min-width:200px;">
                <h3>CHKO Yesterday's Stock (CROD, {yesterday_date_str})</h3><p style="font-size:1.5em;">{stock_summary['CHKO']['yesterday']:.2f} NOS</p>
              </div>
              <div style="flex:1; background:#fafafa; padding:15px; border-radius:8px; box-shadow:2px 2px 5px rgba(0,0,0,0.1); min-width:200px;">
                <h3>CHKO Previous Stock (CROD)</h3><p style="font-size:1.5em;">{stock_summary['CHKO']['previous']:.2f} NOS</p>
              </div>
              <div style="flex:1; background:#fafafa; padding:15px; border-radius:8px; box-shadow:2px 2px 5px rgba(0,0,0,0.1); min-width:200px;">
                <h3>CHKI Current Stock (CROD, {current_date_str})</h3><p style="font-size:1.5em;">{stock_summary['CHKI']['current']:.2f} NOS</p>
              </div>
              <div style="flex:1; background:#fafafa; padding:15px; border-radius:8px; box-shadow:2px 2px 5px rgba(0,0,0,0.1); min-width:200px;">
                <h3>CHKI Yesterday's Stock (CROD, {yesterday_date_str})</h3><p style="font-size:1.5em;">{stock_summary['CHKI']['yesterday']:.2f} NOS</p>
              </div>
              <div style="flex:1; background:#fafafa; padding:15px; border-radius:8px; box-shadow:2px 2px 5px rgba(0,0,0,0.1); min-width:200px;">
                <h3>CHKI Previous Stock (CROD)</h3><p style="font-size:1.5em;">{stock_summary['CHKI']['previous']:.2f} NOS</p>
              </div>
            </div>
            """,
            unsafe_allow_html=True
        )

        # ───────────────────────────────────────────────────────────────
        # Drill-Down Tabs for CHKO and CHKI
        # ───────────────────────────────────────────────────────────────
        st.subheader("📊 Stock Details by Warehouse")
        tabs = st.tabs(["CHKO", "CHKI"])

        for tab, warehouse in zip(tabs, ["CHKO", "CHKI"]):
            with tab:
                st.markdown(f"**Stock Status for {warehouse}**")
                sub_tabs = st.tabs(["Current Stock", "Yesterday's Stock", "Previous Stock"])

                for sub_tab, stock_type in zip(sub_tabs, ["current", "yesterday", "previous"]):
                    with sub_tab:
                        if stock_type == "current":
                            title = f"Current Stock ({current_date_str})"
                        elif stock_type == "yesterday":
                            title = f"Yesterday's Stock ({yesterday_date_str})"
                        else:
                            title = f"Previous Stock (Before {yesterday_date_str})"
                        st.markdown(f"**{title}**")
                        categories = cached_categorize_fg_codes(df_stock, warehouse, stock_type)

                        # Display summary counts
                        st.markdown(
                            f"""
                            - **Ready to Dispatch**: {categories['ready_count']} FG codes ({categories['ready_qty']:.2f} NOS)
                            - **Quality**: {categories['quality_count']} FG codes ({categories['quality_qty']:.2f} NOS)
                            - **Blocked**: {categories['blocked_count']} FG codes ({categories['blocked_qty']:.2f} NOS)
                            """
                        )

                        # Stock details table
                        df_display = categories["full_df"][["Product", "Material Description", "Available Qty", "Handling Unit", "GR Date"]].copy()
                        df_display = df_display.sort_values("GR Date", ascending=False)
                        df_display.columns = ["FG Code", "Material Description", "Quantity", "Handling Number", "GR Date"]
                        st.markdown(f"**Stock Details (Sorted by GR Date)**")
                        st.dataframe(df_display, use_container_width=True)

                        # Bar chart for FG code quantities by category
                        if not categories["summary_df"].empty:
                            fig = px.bar(
                                categories["summary_df"],
                                x="Product",
                                y="Available Qty",
                                color="Category",
                                title=f"FG Codes by Status in {warehouse} ({stock_type.capitalize()})",
                                labels={"Product": "FG Code", "Available Qty": "Quantity (NOS)"},
                                color_discrete_map={
                                    "Ready to Dispatch": "#00cc00",
                                    "Quality": "#ff9900",
                                    "Blocked": "#ff0000"
                                }
                            )
                            fig.update_layout(
                                xaxis_title="FG Code",
                                yaxis_title="Quantity (NOS)",
                                legend_title="Status",
                                margin=dict(t=40, l=0, r=0, b=0)
                            )
                            st.plotly_chart(fig, use_container_width=True)

                        # Detailed tables by status
                        with st.expander("Show Detailed FG Codes by Status", expanded=False):
                            for category in ["Ready to Dispatch", "Quality", "Blocked"]:
                                df_key = f"{category.lower().replace(' to dispatch', '')}_df"
                                df = categories.get(df_key, pd.DataFrame())
                                if not df.empty:
                                    st.markdown(f"**{category} FG Codes**")
                                    df_status = df[["Product", "Material Description", "Available Qty", "Stock Type", "GR Date"]].copy()
                                    df_status = df_status.sort_values("GR Date", ascending=False)
                                    df_status.columns = ["FG Code", "Material Description", "Quantity", "Stock Type", "GR Date"]
                                    st.dataframe(df_status, use_container_width=True)
                                else:
                                    st.write(f"No {category} FG codes in {warehouse} for {stock_type} stock.")
else:
    st.info("Upload the Stock Data file to proceed.")